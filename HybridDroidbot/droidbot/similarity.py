
import json
import pickle
import logging
import os
import cv2
from droidbot import utils
from droidbot.input_event import KeyEvent
from droidbot.input_policy import HybirdPolicy, EVENT_FLAG_EXPLORE

DEFAULT_THREGHOLD = 0.95
REUSE_THREGHOLD = 0.99

class UITarpitDetector(object):
    def __init__(self, sim_k, device) -> None:
        self.sim_k = sim_k
        self.sim_count = 0
        self.device = device
        self.logger = logging.getLogger('UITarpitDetector')
        self.tarpit_save_dir = os.path.join(self.device.output_dir, "ui_tarpits")
        if not os.path.exists(self.tarpit_save_dir):
            os.makedirs(self.tarpit_save_dir)
        self.tarpits = {}
        self.to_save_tarpits = {}
    
    def is_similar_page(self,input_manager,current_state=None):
        """
        start calculate similarity between last state screen and current screen
        """
        # 读取当前和上一个状态截图
        # 计算两张截图的相似度
        last_state = input_manager.policy.get_last_state()
        last_state_screen = last_state.get_state_screen()
        if not current_state:
            current_state = input_manager.policy.get_current_state()
        current_state_screen = current_state.get_state_screen()
        sim_score = self.calculate_similarity(last_state_screen,current_state_screen)
        self.logger.info(f'similarity score:{sim_score}')
        if sim_score < DEFAULT_THREGHOLD :
            self.logger.info(f'different page!')  
            return False
        return True  

    def detected_ui_tarpit(self,input_manager):
        """
        detect ui tarpit
        """    
        if not self.is_similar_page(input_manager):
            self.sim_count = 0
            input_manager.policy.clear_action_history()
        else:
            self.sim_count += 1   
        if self.sim_count >= self.sim_k :
            return True
        return False  
    
    # def load_ui_tarpits(self):
    #     """加载保存的UI陷阱"""
    #     try:
    #         with open(os.path.join(self.trap_save_dir, 'UITarpits.pkl'), 'rb') as f:
    #             traps = pickle.load(f)
    #         return traps
    #     except FileNotFoundError:
    #         return {}

    def load_ui_tarpits(self):
        """加载保存的UI陷阱"""
        try:
            with open(os.path.join(self.tarpit_save_dir, 'UITarpits.json'), 'r') as f:
                traps = json.load(f)  # 使用 json.load() 加载 JSON 数据
            self.logger.info("UI traps loaded successfully.")
            return traps
        except FileNotFoundError:
            self.logger.warning("No saved UI traps found. Returning an empty dictionary.")
            return {}
        except json.JSONDecodeError:
            self.logger.error("Error decoding JSON. Returning an empty dictionary.")
            return {}
        
    # def save_ui_tarpits(self):
    #     """保存UI陷阱"""
    #     with open(os.path.join(self.trap_save_dir, 'UITarpits.pkl'), 'wb') as f:
    #         pickle.dump(self.traps, f)

    def to_dict(self):
        pass

    def save_ui_tarpits(self):
        """保存UI陷阱为JSON格式"""
        try:
            with open(os.path.join(self.tarpit_save_dir, 'UITarpits.json'), 'w') as f:
                json.dump(self.to_save_tarpits, f, indent=4)  # 使用 indent=4 使 JSON 更易读
            self.logger.info("UI traps saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving UI traps: {e}")

    def print_ui_tarpits(self):
        for tarpit_name, tarpit_info in self.tarpits.items():
            print(f'tarpit name:{tarpit_name}, info: {tarpit_info}')
        print(f'total tarpits:{len(self.tarpits)}')
    
    def check_or_add_new_trap(self, screenshot,tag):
        """检查或添加新的UI陷阱"""
        # 检查是否已有相似的陷阱
        for tarpit_name, tarpit_info in self.tarpits.items():
            tarpit_img = tarpit_info['screen_shoot']
            similarity = self.calculate_similarity(screenshot, tarpit_img)
            if similarity >= REUSE_THREGHOLD:
                self.logger.info(f"Visiting known tarpit: {tarpit_name}")
                self.tarpits[tarpit_name]['count'] = int(self.tarpits[tarpit_name]['count']) + 1 # 增加count并保存
                return True, tarpit_name
        # add a new tarpit
        new_tarpit_name = f"trap_{len(self.tarpits) + 1}"
        # dest_screenshot_path = "%s/screen_%s.png" % (self.tarpit_save_dir,tag)
        # if screenshot != dest_screenshot_path:
        #         import shutil
        #         shutil.copyfile(screenshot, dest_screenshot_path)
        self.tarpits[new_tarpit_name] = {'screen_shoot': screenshot, 'count': 1, 'actions':[]}
        # self.to_save_tarpits[new_tarpit_name] = {'screen_shoot': screenshot, 'count': 1, 'actions':[]}
        # self.save_ui_tarpits()
        self.logger.info(f"New UI tarpit saved: {new_tarpit_name}")
        return False, new_tarpit_name

    def update_tarpit_actions(self, tarpit_name, event):
        self.tarpits[tarpit_name]['actions'].append(event)
        # self.to_save_tarpits[tarpit_name]['actions'].append(event.get_event_name())
        # self.save_ui_tarpits()
        self.logger.info(f"UI tarpit updated: {tarpit_name}, add event:{event.get_event_name()}")
    
    def clear_tarpit_actions(self, tarpit_name):
        self.tarpits[tarpit_name]['actions'].clear()

    def get_tarpit_by_name(self, tarpit_name):
        return self.tarpits.get(tarpit_name)
    
    def get_tarpit_actions_by_name(self, tarpit_name):
        return self.tarpits[tarpit_name]['actions']
    
    @staticmethod
    def dhash(image, hash_size=8):
        # 转换为灰度并缩放图像
        resized = cv2.resize(image, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # 计算差异值
        diff = gray[:, 1:] > gray[:, :-1]

        # 将布尔数组转换为哈希值
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    @staticmethod
    def hamming_distance(hash1, hash2):
        # 计算两个哈希值之间的汉明距离
        return bin(hash1 ^ hash2).count("1")

    @staticmethod
    def calculate_similarity(fileA, fileB):
        imgA = cv2.imread(fileA)
        imgB = cv2.imread(fileB)
        hashA = UITarpitDetector.dhash(imgA)
        hashB = UITarpitDetector.dhash(imgB)
        # 计算汉明距离相似度分数
        similarity_score = 1 - UITarpitDetector.hamming_distance(hashA, hashB) / 64.0  # 64是dhash算法哈希位数
        return similarity_score     