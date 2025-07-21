import sys
import json
import re
import logging
import random
from abc import abstractmethod


from .input_event import *
from .utg import UTG

# Max number of restarts
MAX_NUM_RESTARTS = 5
# Max number of steps outside the app
MAX_NUM_STEPS_OUTSIDE = 5
MAX_NUM_STEPS_OUTSIDE_KILL = 10
# Max number of replay tries
MAX_REPLY_TRIES = 5
# Max number of query llm
MAX_NUM_QUERY_LLM = 15

# Some input event flags
EVENT_FLAG_STARTED = "+started"
EVENT_FLAG_START_APP = "+start_app"
EVENT_FLAG_STOP_APP = "+stop_app"
EVENT_FLAG_EXPLORE = "+explore"
EVENT_FLAG_NAVIGATE = "+navigate"
EVENT_FLAG_TOUCH = "+touch"

# Policy taxanomy
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


class InputInterruptedException(Exception):
    pass


class InputPolicy(object):
    """
    This class is responsible for generating events to stimulate more app behaviour
    It should call AppEventManager.send_event method continuously
    """

    def __init__(self, device, app):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device = device
        self.app = app
        self.action_count = 0
        self.master = None
        self.last_event = None
        self.last_state = None
        self.current_state = None
        self.__action_history=[]
        self.__activity_history= set()
        self.__all_action_history=set()
        self.llm_event = []
        self.reuse_event = []

    def start(self, input_manager):
        """
        start producing events
        :param input_manager: instance of InputManager
        """
        tarpit_name = None
        while input_manager.enabled and self.action_count < input_manager.event_count:
            try:
                self.current_state = self.device.get_current_state(self.action_count)
                # make sure the first event is go to HOME screen
                # the second event is to start the app
                if self.action_count == 0 and self.master is None:
                    event = KeyEvent(name="HOME")
                elif self.action_count == 1 and self.master is None:
                    event = IntentEvent(self.app.get_start_intent())    
                else:
                    if input_manager.sim_calculator.detected_ui_tarpit(input_manager):
                        # if detected a ui tarpit, then stop random policy and start llm policy
                        current_state_screen = self.current_state.get_state_screen()
                        is_known_tarpit, tarpit_name = input_manager.sim_calculator.check_or_add_new_trap(current_state_screen,self.action_count)
                        if is_known_tarpit:
                            # if it is a known ui tarpit, randomly choose between llm policy and resue
                            if random.random() < 0.5:
                                tarpit_actions = input_manager.sim_calculator.get_tarpit_actions_by_name(tarpit_name)
                                if len(tarpit_actions) > 0:
                                    self.execute_tarpit_actions(tarpit_actions,input_manager,self.llm_event,self.reuse_event)
                                    continue
                        if input_manager.sim_calculator.sim_count > MAX_NUM_QUERY_LLM:
                            # if quey llm too much, then return back
                            self.logger.info(f'query too much. go back!')
                            event = KeyEvent(name="BACK")
                            self.clear_action_history()
                            input_manager.sim_calculator.sim_count = 0
                        else:
                            llm_policy = HybirdPolicy(self.device,self.app,input_manager.random_input,self.action_count, self.__activity_history, self.__action_history,self.current_state)
                            event = llm_policy.generate_event()
                            self.llm_event.append(int(self.action_count)) 
                        input_manager.sim_calculator.update_tarpit_actions(tarpit_name,event)
                    else:
                        tarpit_name = None
                        event = self.generate_event()
                self.last_event = event
                self.last_state = self.current_state
                self.__activity_history.add(self.current_state.foreground_activity)
                self.current_state.save2dir(input_manager.img_output, event)
                # execute event
                input_manager.add_event(event)
                # if tarpit_name and not input_manager.sim_calculator.is_similar_page(input_manager,self.device.get_current_state()):
                #     # after execute event, if it enter different ui page, then add valid trap action
                #     input_manager.sim_calculator.update_tarpit_actions(tarpit_name,event)
                self.action_count += 1
            except KeyboardInterrupt:
                break
            except InputInterruptedException as e:
                self.logger.warning("stop sending events: %s" % e)
                break
            except AttributeError as e:
                self.logger.error("AttributeError: %s" % e)
                continue  # 处理属性错误
            except Exception as e:
                self.logger.warning("exception during sending events: %s" % e)
                import traceback
                traceback.print_exc()
                continue

    def get_last_state(self):
        return self.last_state  
    
    def get_current_state(self):
        return self.current_state
    
    def clear_action_history(self):
        self.__action_history = []
    
    # def __update_utg(self):
    #     self.utg.add_transition(self.last_event, self.last_state, self.current_state) 

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
                # if escape current tarpit, skip
                break
        self.logger.info('ending reuse actions...')

    @abstractmethod
    def generate_event(self):
        """
        generate an event
        @return:
        """
        pass


class HybirdPolicy(InputPolicy):
    def __init__(self, device, app, random_input, action_count, activity_history, action_history,current_state):
        super(HybirdPolicy, self).__init__(device, app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = "You are an expert in App GUI testing. Please guide the testing tool to enhance the coverage of functional scenarios in testing the App based on your extensive App testing experience. "
        self.random_input = random_input
        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = random_input
        self.__action_history=action_history
        self.__all_action_history=set()
        self.__activity_history = activity_history
        self.action_count = action_count
        self.current_state = current_state

    def generate_event(self):
        """
        generate an event
        @return:
        """

        # Get current device state
        # self.current_state = self.device.get_current_state(self.action_count)
        if self.current_state is None:
            import time
            time.sleep(5)
            return KeyEvent(name="BACK")

        event = self.generate_event_based_on_utg()

        self.last_state = self.current_state
        self.last_event = event
        return event

    def generate_event_based_on_utg(self):
        """
        generate an event based on current UTG
        @return: InputEvent
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    self.__action_history = [f'- start the app {self.app.app_name}']
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
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
            # If the app is in foreground
            self.__num_steps_outside = 0

        action, candidate_actions, action_id = self._get_action_with_LLM(current_state, self.__action_history,self.__activity_history,self.__all_action_history)
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

        # If couldn't find a exploration target, stop the app
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
        client = OpenAI(
            base_url=gpt_url,
            api_key=gpt_key
        )

        messages=[{"role": "user", "content": prompt}]
        completion = client.chat.completions.create(
            messages=messages,
            model=model_name,
            timeout=30
        )
        res = completion.choices[0].message.content
        return res

    def _get_action_with_LLM(self, current_state, action_history,activity_history,all_action_history):
        activity = current_state.foreground_activity
        task_prompt = self.task +f"Currently, the App is stuck on the {activity} page, unable to explore more features. You task is to select an action based on the current GUI Infomation to perform next and help the app escape the UI tarpit."
        # visisted_page_prompt = f'I have already visited the following activities: \n' + '\n'.join(activity_history)
        # all_history_prompt = f'I have already completed the following actions to explore the app: \n' + '\n'.join(all_action_history)
        history_prompt = f'I have already tried the following steps with action id in parentheses which should not be selected anymore: \n ' + ';\n '.join(action_history)
        state_prompt, candidate_actions = current_state.get_described_actions()
        question = 'Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.'
        prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
        print(prompt)
        response = self._query_llm(prompt)
        print(f'response: {response}')
        # if '-1' in response:
            # input(f"Seems the task is completed. Press Enter to continue...")

        match = re.search(r'\d+', response)
        if not match:
            return None, candidate_actions
        idx = int(match.group(0))
        selected_action = candidate_actions[idx]
        if isinstance(selected_action, SetTextEvent):
            view_text = current_state.get_view_desc(selected_action.view)
            question = f'What text should I enter to the {view_text}? Just return the text and nothing else.'
            prompt = f'{task_prompt}\n{state_prompt}\n{question}'
            print(prompt)
            response = self._query_llm(prompt)
            print(f'response: {response}')
            selected_action.text = response.replace('"', '')
            if len(selected_action.text) > 30:  # heuristically disable long text input
                selected_action.text = ''
        return selected_action, candidate_actions ,idx

    
class UtgRandomPolicy(InputPolicy):
    """
    random input policy based on UTG
    """

    def __init__(self, device, app, random_input=True, number_of_events_that_restart_app=100, clear_and_restart_app_data_after_100_events=False):
        super(UtgRandomPolicy, self).__init__(
            device, app
        )
        self.number_of_events_that_restart_app = number_of_events_that_restart_app
        self.clear_and_restart_app_data_after_100_events = clear_and_restart_app_data_after_100_events
        self.logger = logging.getLogger(self.__class__.__name__)
        self.random_input = random_input
        self.preferred_buttons = [
            "yes",
            "ok",
            "activate",
            "detail",
            "more",
            "access",
            "allow",
            "check",
            "agree",
            "try",
            "go",
            "next",
        ]
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.number_of_steps_outside_the_shortest_path = 0
        self.reached_state_on_the_shortest_path = []
        self.last_rotate_events = KEY_RotateDeviceNeutralEvent

    def get_action_history(self):
        return self.__action_history

    def get_all_action_history(self):
        return self.__all_action_history

    def get_activity_history(self):
        return self.__activity_history

    def generate_event(self):
        """
        generate an event
        @return:
        """
        
        # Get current device state
        # self.current_state = self.device.get_current_state(self.action_count)
        if self.current_state is None:
            import time
            time.sleep(5)
            return KeyEvent(name="BACK")

        # self.__update_utg()
        event = None

        if self.action_count % self.number_of_events_that_restart_app == 0 and self.clear_and_restart_app_data_after_100_events:
            self.logger.info("clear and restart app after %s events" % self.number_of_events_that_restart_app)
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
        """
        generate an event based on current UTG
        @return: InputEvent
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(
                EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP
            ) or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info(
                    "The app had been restarted %d times.", self.__num_restarts
                )
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        possible_events = current_state.get_possible_input()

        if self.random_input:
            random.shuffle(possible_events)
        possible_events.append(KeyEvent(name="BACK"))
        possible_events.append(RotateDevice())

        self.__event_trace += EVENT_FLAG_EXPLORE
        event = random.choice(possible_events)
        return event


