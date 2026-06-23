import sys
import json
import re
import logging
import os
import random
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .input_event import *
from .utg import UTG

MAX_NUM_RESTARTS = 5
MAX_NUM_STEPS_OUTSIDE = 5
MAX_NUM_STEPS_OUTSIDE_KILL = 10
MAX_REPLY_TRIES = 5
MAX_NUM_QUERY_LLM = 15

EVENT_FLAG_STARTED = "+started"
EVENT_FLAG_START_APP = "+start_app"
EVENT_FLAG_STOP_APP = "+stop_app"
EVENT_FLAG_EXPLORE = "+explore"
EVENT_FLAG_NAVIGATE = "+navigate"
EVENT_FLAG_TOUCH = "+touch"

POLICY_NAIVE_DFS = "dfs_naive"
POLICY_GREEDY_DFS = "dfs_greedy"
POLICY_NAIVE_BFS = "bfs_naive"
POLICY_GREEDY_BFS = "bfs_greedy"
POLICY_REPLAY = "replay"
POLICY_MANUAL = "manual"
POLICY_MONKEY = "monkey"
POLICY_TASK = "task"
POLICY_NONE = "none"
POLICY_HYBIRD = "hybird"
POLICY_RANDOM = "random"


@dataclass
class TarpitContext:
    ref_screenshot: str       # screenshot path of s_tarpit_ref (S[N-k])
    entered_at_step: int
    escaped_at_step: Optional[int] = None


class InputInterruptedException(Exception):
    pass


class InputPolicy(object):
    """
    Generates events to stimulate app behaviour.
    Supports Tarpit-Region Exit experiment (condition A vs B).
    """

    def __init__(self, device, app,
                 condition="A",
                 theta_exit=0.85,
                 c_max=5,
                 disable_llm=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.action_count = 0
        self.master = None
        self.last_event = None
        self.last_state = None
        self.current_state = None
        self.__action_history = []
        self.__activity_history = set()
        self.__all_action_history = set()
        self.llm_event = []
        self.reuse_event = []
        # experiment parameters
        self.condition = condition        # "A": immediate handoff; "B": extend until exit region
        self.theta_exit = theta_exit      # similarity threshold for "left tarpit region"
        self.c_max = c_max                # safety cap on continuation steps
        self.disable_llm = disable_llm

    def start(self, input_manager):
        tarpit_name = None
        _prev_in_tarpit = False
        tarpit_ctx: Optional[TarpitContext] = None

        while input_manager.enabled and self.action_count < input_manager.event_count:
            try:
                self.current_state = self.device.get_current_state(self.action_count)

                if self.action_count == 0 and self.master is None:
                    event = KeyEvent(name="HOME")
                elif self.action_count == 1 and self.master is None:
                    event = IntentEvent(self.app.get_start_intent())
                else:
                    currently_in_tarpit = (
                        False
                        if self.disable_llm
                        else input_manager.sim_calculator.detected_ui_tarpit(input_manager)
                    )

                    just_escaped = _prev_in_tarpit and not currently_in_tarpit
                    _prev_in_tarpit = currently_in_tarpit

                    if currently_in_tarpit:
                        # Record tarpit context on first detection
                        if tarpit_ctx is None:
                            ws = input_manager.sim_calculator.window_start_state
                            ref_screenshot = (
                                ws.get_state_screen()
                                if ws is not None
                                else self.current_state.get_state_screen()
                            )
                            tarpit_ctx = TarpitContext(
                                ref_screenshot=ref_screenshot,
                                entered_at_step=self.action_count,
                            )

                        current_state_screen = self.current_state.get_state_screen()
                        is_known_tarpit, tarpit_name = input_manager.sim_calculator.check_or_add_new_trap(
                            current_state_screen, self.action_count,
                            structure_str=self.current_state.structure_str)

                        if is_known_tarpit and random.random() < 0.5:
                            tarpit_actions = input_manager.sim_calculator.get_tarpit_actions_by_name(tarpit_name)
                            if len(tarpit_actions) > 0:
                                self.execute_tarpit_actions(tarpit_actions, input_manager,
                                                            self.llm_event, self.reuse_event)
                                continue

                        if input_manager.sim_calculator.sim_count > MAX_NUM_QUERY_LLM:
                            self.logger.info('query too much. go back!')
                            event = KeyEvent(name="BACK")
                            self.clear_action_history()
                            input_manager.sim_calculator.sim_count = 0
                        else:
                            llm_policy = HybirdPolicy(
                                self.device, self.app, input_manager.random_input,
                                self.action_count, self.__activity_history,
                                self.__action_history, self.current_state)
                            event = llm_policy.generate_event()
                            self.llm_event.append(int(self.action_count))

                        input_manager.sim_calculator.update_tarpit_actions(tarpit_name, event)

                    else:
                        if just_escaped:
                            tarpit_ctx.escaped_at_step = self.action_count
                            if self.condition == "B":
                                self._extend_until_exit_region(input_manager, tarpit_ctx, tarpit_name)
                            # Start diversity window from this point (handoff to random)
                            if input_manager.metrics_logger:
                                input_manager.metrics_logger.on_escape(
                                    self.action_count, self.current_state, tarpit_name)
                            tarpit_ctx = None

                        tarpit_name = None
                        event = self.generate_event()

                if input_manager.metrics_logger:
                    input_manager.metrics_logger.on_event(
                        event, self.current_state, self.action_count)

                self.last_event = event
                self.last_state = self.current_state
                self.__activity_history.add(self.current_state.foreground_activity)
                self.current_state.save2dir(input_manager.img_output, event)
                input_manager.add_event(event)
                self.action_count += 1

            except KeyboardInterrupt:
                break
            except InputInterruptedException as e:
                self.logger.warning("stop sending events: %s" % e)
                break
            except AttributeError as e:
                self.logger.error("AttributeError: %s" % e)
                continue
            except Exception as e:
                self.logger.warning("exception during sending events: %s" % e)
                import traceback
                traceback.print_exc()
                continue

    def _extend_until_exit_region(self, input_manager, tarpit_ctx: TarpitContext, tarpit_name):
        """
        Condition B: after hasTarpit goes False, continue LLM control until the current state's
        perceptual similarity to tarpit_ctx.ref_screenshot drops below theta_exit, or c_max steps.
        """
        from .similarity import UITarpitDetector
        steps_extended = 0

        while steps_extended < self.c_max:
            current_screenshot = self.current_state.get_state_screen()
            sim = UITarpitDetector.calculate_similarity(current_screenshot, tarpit_ctx.ref_screenshot)
            if sim < self.theta_exit:
                self._log_continuation_event(
                    input_manager, tarpit_ctx, steps_extended, "exited_region")
                return

            llm_policy = HybirdPolicy(
                self.device, self.app, input_manager.random_input,
                self.action_count, self.__activity_history,
                self.__action_history, self.current_state)
            event = llm_policy.generate_event()
            self.llm_event.append(int(self.action_count))

            self.last_event = event
            self.last_state = self.current_state
            self.__activity_history.add(self.current_state.foreground_activity)
            self.current_state.save2dir(input_manager.img_output, event)
            input_manager.add_event(event)
            self.action_count += 1

            self.current_state = self.device.get_current_state(self.action_count)
            steps_extended += 1

        self._log_continuation_event(
            input_manager, tarpit_ctx, steps_extended, "c_max_reached")

    def _log_continuation_event(self, input_manager, tarpit_ctx: TarpitContext,
                                 steps_extended: int, reason: str):
        record = {
            "tarpit_entered_at": tarpit_ctx.entered_at_step,
            "tarpit_escaped_at": tarpit_ctx.escaped_at_step,
            "continuation_steps": steps_extended,
            "stop_reason": reason,
            "ref_screenshot": tarpit_ctx.ref_screenshot,
        }
        log_path = os.path.join(self.device.output_dir, "continuation_log.jsonl")
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        self.logger.info(
            f"[condition-B] continuation done: steps={steps_extended}, reason={reason}")

    def get_last_state(self):
        return self.last_state

    def get_current_state(self):
        return self.current_state

    def clear_action_history(self):
        self.__action_history = []

    def execute_tarpit_actions(self, actions, input_manager, llm_event, reuse_event):
        self.logger.info('executing reuse actions...')
        for event in actions:
            self.current_state = self.device.get_current_state(self.action_count)
            self.last_state = self.current_state
            self.last_event = event
            self.reuse_event.append(int(self.action_count))
            self.current_state.save2dir(input_manager.img_output, event)
            input_manager.add_event(event)
            self.action_count += 1
            if not input_manager.sim_calculator.detected_ui_tarpit(input_manager):
                break
        self.logger.info('ending reuse actions...')

    @abstractmethod
    def generate_event(self):
        pass


class HybirdPolicy(InputPolicy):
    def __init__(self, device, app, random_input, action_count,
                 activity_history, action_history, current_state):
        super(HybirdPolicy, self).__init__(device, app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = (
            "You are an expert in App GUI testing. Please guide the testing tool to enhance "
            "the coverage of functional scenarios in testing the App based on your extensive "
            "App testing experience. "
        )
        self.random_input = random_input
        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = random_input
        self.__action_history = action_history
        self.__all_action_history = set()
        self.__activity_history = activity_history
        self.action_count = action_count
        self.current_state = current_state

    def generate_event(self):
        if self.current_state is None:
            time.sleep(5)
            return KeyEvent(name="BACK")
        event = self.generate_event_based_on_utg()
        self.last_state = self.current_state
        self.last_event = event
        return event

    def generate_event_based_on_utg(self):
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            start_app_intent = self.app.get_start_intent()
            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    self.logger.info("Too many restarts. Entering random mode.")
                    self.__random_explore = True
                else:
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    self.__action_history = [f'- start the app {self.app.app_name}']
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            self.__num_steps_outside += 1
            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                self.__action_history.append('- go back')
                return go_back_event
        else:
            self.__num_steps_outside = 0

        action, candidate_actions, action_id = self._get_action_with_LLM(
            current_state, self.__action_history, self.__activity_history, self.__all_action_history)

        if action is not None:
            action_str = f"{current_state.get_action_desc(action)} ({action_id})"
            self.__action_history.append(action_str)
            self.__all_action_history.add(action_str)
            return action

        if self.__random_explore:
            self.logger.info("Trying random event...")
            action = random.choice(candidate_actions)
            self.__action_history.append(current_state.get_action_desc(action))
            self.__all_action_history.add(current_state.get_action_desc(action))
            return action

        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__action_history.append('- stop the app')
        self.__all_action_history.add('- stop the app')
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)

    def _query_llm(self, prompt, model_name='gpt-3.5-turbo'):
        # TODO: replace with your own LLM
        from openai import OpenAI
        gpt_url = ''
        gpt_key = ''
        client = OpenAI(base_url=gpt_url, api_key=gpt_key)
        messages = [{"role": "user", "content": prompt}]
        completion = client.chat.completions.create(
            messages=messages, model=model_name, timeout=30)
        return completion.choices[0].message.content

    def _get_action_with_LLM(self, current_state, action_history, activity_history, all_action_history):
        activity = current_state.foreground_activity
        task_prompt = (
            self.task +
            f"Currently, the App is stuck on the {activity} page, unable to explore more features. "
            f"Your task is to select an action based on the current GUI information to perform next "
            f"and help the app escape the UI tarpit."
        )
        history_prompt = (
            f'I have already tried the following steps with action id in parentheses '
            f'which should not be selected anymore: \n ' + ';\n '.join(action_history)
        )
        state_prompt, candidate_actions = current_state.get_described_actions()
        question = (
            'Which action should I choose next?\n'
            'Return the action id (integer). If no more action is needed, return -1.'
        )
        prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
        print(prompt)
        response = self._query_llm(prompt)
        print(f'response: {response}')

        lines = response.strip().split('\n')
        match = re.search(r'-?\d+', lines[0])
        if not match:
            return None, candidate_actions, None

        idx = int(match.group(0))
        if idx < 0 or idx >= len(candidate_actions):
            return None, candidate_actions, None

        selected_action = candidate_actions[idx]
        if isinstance(selected_action, SetTextEvent):
            view_text = current_state.get_view_desc(selected_action.view)
            text_question = (
                f'What text should I enter to the {view_text}? '
                f'Just return the text and nothing else.')
            text_prompt = f'{task_prompt}\n{state_prompt}\n{text_question}'
            print(text_prompt)
            text_response = self._query_llm(text_prompt)
            print(f'response: {text_response}')
            selected_action.text = text_response.replace('"', '')
            if len(selected_action.text) > 30:
                selected_action.text = ''

        return selected_action, candidate_actions, idx


class UtgRandomPolicy(InputPolicy):
    """
    Random input policy based on UTG, with tarpit detection and LLM escape.
    """

    def __init__(self, device, app, random_input=True,
                 number_of_events_that_restart_app=100,
                 clear_and_restart_app_data_after_100_events=False,
                 condition="A",
                 theta_exit=0.85,
                 c_max=5,
                 disable_llm=False):
        super(UtgRandomPolicy, self).__init__(
            device, app,
            condition=condition,
            theta_exit=theta_exit,
            c_max=c_max,
            disable_llm=disable_llm,
        )
        self.number_of_events_that_restart_app = number_of_events_that_restart_app
        self.clear_and_restart_app_data_after_100_events = clear_and_restart_app_data_after_100_events
        self.logger = logging.getLogger(self.__class__.__name__)
        self.random_input = random_input
        self.preferred_buttons = [
            "yes", "ok", "activate", "detail", "more", "access",
            "allow", "check", "agree", "try", "go", "next",
        ]
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.last_rotate_events = KEY_RotateDeviceNeutralEvent

    def generate_event(self):
        if self.current_state is None:
            time.sleep(5)
            return KeyEvent(name="BACK")

        event = None
        if self.action_count % self.number_of_events_that_restart_app == 0 \
                and self.clear_and_restart_app_data_after_100_events:
            self.logger.info("clear and restart app after %s events"
                             % self.number_of_events_that_restart_app)
            return ReInstallAppEvent(self.app)

        if event is None:
            event = self.generate_event_based_on_utg()

        if isinstance(event, RotateDevice):
            if self.last_rotate_events == KEY_RotateDeviceNeutralEvent:
                self.last_rotate_events = KEY_RotateDeviceRightEvent
                event = RotateDeviceRightEvent()
            else:
                self.last_rotate_events = KEY_RotateDeviceNeutralEvent
                event = RotateDeviceNeutralEvent()

        self.last_state = self.current_state
        self.last_event = event
        return event

    def generate_event_based_on_utg(self):
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            start_app_intent = self.app.get_start_intent()
            if self.__event_trace.endswith(
                EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP
            ) or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    self.logger.info("Too many restarts. Entering random mode.")
                else:
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            self.__num_steps_outside += 1
            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            self.__num_steps_outside = 0

        possible_events = current_state.get_possible_input()
        if self.random_input:
            random.shuffle(possible_events)
        possible_events.append(KeyEvent(name="BACK"))
        possible_events.append(RotateDevice())

        self.__event_trace += EVENT_FLAG_EXPLORE
        event = random.choice(possible_events)
        return event
