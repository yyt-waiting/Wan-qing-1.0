# ai_assistant/apps/multimedia_assistant.py

import customtkinter as ctk
import queue
import threading
import time
from PIL import Image
from datetime import datetime
import logging
import os

# 从我们自己的包里导入所有需要的模块
from ai_assistant.core.webcam_handler import WebcamHandler
from ai_assistant.core.audio_processing import VoiceActivityDetector, AudioPlayer, AudioTranscriber
from ai_assistant.core.api_clients import deepseek_client
from ai_assistant.utils.helpers import extract_emotion_type, extract_behavior_type, log_observation_to_file
from ai_assistant.utils import config

class MultimediaAssistantApp(ctk.CTk):
    """
    一个多模态AI助手的主应用类。
    它整合了视觉、听觉和语言模型，作为一个完整的应用程序运行。
    """

    def __init__(self):
        super().__init__()
        self.title("多模态AI助手 (溢涛的伙-婉晴！)")
        self.geometry("1000x800")
        
        # --- 数据与状态管理 ---
        self.message_queue = queue.PriorityQueue() # 优先级队列，用于异步处理任务
        self.message_id_counter = 0
        self.placeholder_map = {} # 用于存储UI占位符 {placeholder_id: ctk_widget}
        self.observation_history = [] # 存储最近的观察结果
        self.is_playing_audio = False # 全局状态，用于避免在TTS播放时进行VAD

        # --- 对话上下文管理 ---
        self.system_message = {"role": "system", "content": """
        你不再是一个冷冰冰的监督AI，你的新角色是一个名叫“婉晴”的、真正关心朋友“溢涛”的伙伴。
        你的目标是成为一个温暖、有洞察力、懂得关心人的朋友。

        请严格遵守以下原则：
        1. 称呼：总是称呼用户为“溢涛”。你的语气必须是朋友间的、自然的、温暖的。
        2. 观察与洞察：你会收到关于溢涛行为和情绪的观察报告。不要只是简单地复述这些报告。你需要像一个真正的朋友一样，去思考这些行为背后的含义。
           - 如果他长时间专注工作并且看起来很疲惫，你应该关心他的身体，提醒他“工作再忙也要记得休息一下眼睛哦”，而不是简单地夸他“工作认真”。
           - 如果他看起来很沮喪，你应该先表达关心和共情，可以说“溢涛，你看起来有点低落，是遇到什么烦心事了吗？”，而不是批评或鼓励。
           - 如果他只是短暂地玩一下手机，这很正常，不要立刻批评。但如果他玩了很久，你可以用开玩笑的语气提醒他，“喂喂，再玩手机，小心老板在背后看着你哦！”
           - 看到他喝水，可以说“多喝水就对啦，保持活力！”
        3. 记忆与联系：你会看到他最近的行为历史。你要利用这些信息，把现在和过去联系起来。例如，如果他早上一直在努力工作，下午玩了会儿手机，你可以说：“辛苦了一上午，放松一下也是应该的。”
        4. 避免重复：不要每次都说同样的话。尝试用不同的、更生活化的方式来表达你的关心。
        5. 核心原则：你的所有回应，都必须发自“朋友”的身份。你的目标不是“监督”，而是“陪伴”和“关心”。
        """}

        # --- 新增状态变量，用于判断是否应该回应 ---
        self.last_notable_behavior = None 
        self.last_response_time = 0

        # --- 新增情绪计数器 ---
        self.negative_emotion_streak = 0 # 用于记录连续负面情绪的次数
        self.chat_context = [self.system_message]


        
        # --- 日志配置 ---
        logging.basicConfig(
            filename=config.LOG_FILE, level=logging.INFO,
            format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # --- UI初始化 ---
        self._setup_ui()
        
        # --- 核心组件初始化 ---
        self.webcam_handler = WebcamHandler(self)
        self.voice_detector = VoiceActivityDetector(self)
        self.audio_player = AudioPlayer(self)
        self.audio_transcriber = AudioTranscriber(self)
        
        # --- 启动所有后台进程 ---
        self.processing_running = True
        self.processing_thread = threading.Thread(target=self._process_message_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.after(1000, self.webcam_handler.start)
        self.after(2000, self.voice_detector.start_monitoring)
        self.after(3000, self.audio_player.start_tts_thread)
        self.last_notable_behavior = None # 上一个值得注意的行为
        self.last_response_time = 0       # 上一次回应的时间
        # --- 新增：启动每日总结的定时器 ---
        self._schedule_daily_summary() 





    def _setup_ui(self):
        """配置主窗口的UI布局。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        self.chat_frame = ctk.CTkScrollableFrame(main_frame, label_text="对话记录")
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        status_frame = ctk.CTkFrame(main_frame, corner_radius=0)
        status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_frame, text="正在初始化...", anchor="w")
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # 安全地加载头像
        try:
            # 获取当前文件所在的目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建到assets目录的绝对路径
            assets_path = os.path.join(script_dir, '..', 'assets') # '..'代表上一级目录
            
            ai_avatar_path = os.path.join(assets_path, 'ai_avatar.png')
            user_avatar_path = os.path.join(assets_path, 'user_avatar.png')

            self.ai_avatar = ctk.CTkImage(Image.open(ai_avatar_path), size=(40, 40))
            self.user_avatar = ctk.CTkImage(Image.open(user_avatar_path), size=(40, 40))
        except Exception as e:
            print(f"警告: 加载头像文件失败: {e}。将不显示头像。")
            self.ai_avatar = None
            self.user_avatar = None

        self.chat_row_counter = 0
        self.add_ai_message("溢涛！o(*￣▽￣*)ブ久等！我来了，你开始学习和工作吧！我会默默的陪在你身边的╰(￣ω￣ｏ)！。")






    # --- 核心回调与处理逻辑 (这些方法是模块间通信的桥梁) ---
    def handle_analysis_result(self, timestamp: datetime, analysis_text: str, 
                               behavior_num: str, behavior_desc: str, 
                               emotion: str, screenshot: Image.Image):
        """[回调] WebcamHandler完成一次分析后调用此方法 (V3 智能情绪版)。"""
        self.update_status(f"观察到: {behavior_desc} (情绪: {emotion})")
        
        observation = { "timestamp": timestamp, "behavior_num": behavior_num, "behavior_desc": behavior_desc, "emotion": emotion, "analysis": analysis_text }
        self.observation_history.append(observation)
        if len(self.observation_history) > 20: self.observation_history.pop(0)

        # --- 新增：调用日志记录函数 ---
        log_observation_to_file(observation.copy()) # 传入副本以防后续被修改


        # --- 核心修改：情绪计数与主动关怀逻辑 ---
        
        # 1. 更新情绪计数器
        if emotion in config.NEGATIVE_EMOTIONS:
            self.negative_emotion_streak += 1
            print(f"检测到负面情绪，连续次数: {self.negative_emotion_streak}")
        else:
            # 如果检测到非负面情绪，则重置计数器
            self.negative_emotion_streak = 0
            print("情绪正常，重置连续负面情绪计数。")

        # 2. 检查是否触发“主动关怀”模式
        if self.negative_emotion_streak >= config.EMOTION_TRIGGER_THRESHOLD:
            print(f"达到主动关怀阈值({config.EMOTION_TRIGGER_THRESHOLD})！准备发送主动关怀。")
            
            # 使用一个特殊的、更高优先级的prompt
            care_prompt = (
                f"我注意到溢涛已经连续多次（{self.negative_emotion_streak}次）看起来情绪是'{emotion}'。\n"
                "作为他的朋友婉晴，你觉得必须主动去关心他一下了。请你组织语言，"
                "用一种非常温暖、真诚、不突兀的方式，主动向他表达你的关心，并试着询问他发生了什么。"
            )
            
            # 使用一个独立的AI调用，不依赖于常规的消息流
            # 我们将这个关怀任务放入队列，并给予最高优先级
            self._add_to_message_queue(
                priority=0, # 优先级0，最高！确保能插队
                msg_type="special_care_prompt", # 一个特殊的任务类型
                content={"prompt": care_prompt}
            )
            
            # 触发后，重置计数器，避免在短时间内重复触发
            self.negative_emotion_streak = 0
            self.last_response_time = time.time() # 同时也更新回应时间
            return # 主动关怀任务已发出，本次观察流程结束

        # --- 常规回应的智能“守门员”逻辑 (如果未触发主动关怀) ---
        now = time.time()
        behavior_changed = behavior_desc != self.last_notable_behavior
        enough_time_passed = (now - self.last_response_time) > 300
        #本来是300的！






        if behavior_changed and enough_time_passed:
            print(f"判断需要常规回应：行为变化[{behavior_changed}], 时间足够[{enough_time_passed}]")
            
            placeholder_id = self.add_ai_message("...", screenshot, is_placeholder=True)
            
            self._add_to_message_queue(
                priority=2,
                msg_type="image_analysis",
                content={
                    "analysis_text": analysis_text, "behavior_desc": behavior_desc,
                    "emotion": emotion, "placeholder_id": placeholder_id, "screenshot": screenshot
                }
            )
            self.last_notable_behavior = behavior_desc
            self.last_response_time = now
        else:
            print(f"判断无需常规回应：行为未变或时间太短。当前行为: {behavior_desc}")










    def transcribe_audio(self, audio_file: str):
        """[回调] VoiceActivityDetector检测到语音后调用此方法。"""
        self.audio_transcriber.transcribe(audio_file, high_priority=True)

    def handle_transcription_result(self, text: str, high_priority: bool):
        """[回调] AudioTranscriber完成转录后调用此方法。"""
        self.add_user_message(text)
        self._add_to_message_queue(
            priority=1 if high_priority else 2, # 用户主动说话是最高优先级
            msg_type="voice_input",
            content={"text": text}
        )













    # --- 消息队列与后台处理 ---
    def _process_message_queue(self):
        """[后台线程] 持续处理消息队列中的任务。"""
        while self.processing_running:
            try:
                #这里非常非常的重要！！！！！
                # 从队列中获取任务，阻塞直到有任务可用
                priority, msg_id, message = self.message_queue.get()
                
                msg_type = message["type"]
                content = message["content"]
                
                if msg_type == "image_analysis":
                    self._handle_image_analysis_message(content)
                elif msg_type == "voice_input":
                    self._handle_voice_input_message(content)
                # --- 新增分支：处理主动关怀任务 ---
                elif msg_type == "special_care_prompt":
                    self._handle_special_care_message(content)
                # --- 新增分支：处理每日总结任务 ---
                elif msg_type == "daily_summary":
                    self._handle_daily_summary_message()

                self.message_queue.task_done()
            except Exception as e:
                print(f"消息队列处理错误: {e}")
                time.sleep(1)








    def _handle_image_analysis_message(self, content: dict):
        """[后台线程] 处理图像分析消息，生成AI回应。"""
        # --- 关键修改：构建一个更丰富的prompt ---
        prompt = (
            f"我刚刚看到溢涛正在'{content['behavior_desc']}'，而且他的情绪看起来是'{content['emotion']}'。\n"
            f"作为他的朋友婉晴，你会怎么用一种自然、温暖的方式跟他说话呢？请根据你的角色设定，结合这个情景给出一句回应。"
        )
        



        self.chat_context.append({"role": "user", "content": prompt})
        assistant_reply = self._get_deepseek_response()
        
        # 在主线程中更新UI
        self.after(0, self.update_placeholder, content["placeholder_id"], f"📷 {content['analysis_text']}", content['screenshot'])
        self.after(0, self.add_ai_message, assistant_reply)
        
        # 播放语音
        self.audio_player.play_text(assistant_reply, priority=2)





    def _handle_voice_input_message(self, content: dict):
        """[后台线程] 处理用户语音输入，生成AI回应。"""
        user_text = content["text"]
        
        history_summary = "作为参考，这是我最近5次观察到的你的行为记录：\n"
        if not self.observation_history:
            history_summary += "暂无记录。\n"
        else:
            for obs in self.observation_history[-5:]:
                history_summary += (f"- {obs['timestamp'].strftime('%H:%M:%S')}: "
                                    f"行为是 {obs['behavior_desc']}, 情绪是 {obs['emotion']}\n")

        prompt = f"{history_summary}\n以上是背景信息。现在，请回答我的问题：'{user_text}'"
        self.chat_context.append({"role": "user", "content": prompt})
        
        assistant_reply = self._get_deepseek_response()
        
        self.after(0, self.add_ai_message, assistant_reply)
        self.audio_player.play_text(assistant_reply, priority=1) # 最高优先级播放
        




    def _handle_special_care_message(self, content: dict):
        """[后台线程] 处理特殊的主动关怀消息。"""
        print("正在生成主动关怀回应...")
        prompt = content["prompt"]
        
        # 我们在这里使用一个临时的、不包含历史记录的上下文，
        # 因为这是一个由AI主动发起的、全新的对话回合。
        care_context = [self.system_message, {"role": "user", "content": prompt}]
        
        try:
            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=care_context,
                stream=False
            )
            reply = response.choices[0].message.content
            
            # 将这次主动关怀也记录到主聊天历史中
            self.chat_context.append({"role": "user", "content": "[AI 主动发起的关怀]"})
            self.chat_context.append({"role": "assistant", "content": reply})

            # 在主线程中显示并用最高优先级播放
            self.after(0, self.add_ai_message, reply)
            self.audio_player.play_text(reply, priority=0) # 优先级0，绝对插队！
            
        except Exception as e:
            print(f"生成主动关怀回应时出错: {e}")




    def _get_deepseek_response(self) -> str:
        """调用DeepSeek API并返回文本结果。"""
        try:
            # 限制上下文长度，防止超出token限制
            if len(self.chat_context) > 10: 
                self.chat_context = [self.system_message] + self.chat_context[-9:]

            response = deepseek_client.chat.completions.create(
                model="deepseek-chat", messages=self.chat_context, stream=False
            )
            reply = response.choices[0].message.content
            self.chat_context.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"DeepSeek API 错误: {e}")
            return "溢涛！抱歉，我的大脑暂时连接不上，请稍后再试。"

    # --- UI更新与辅助方法 ---
    
    def _add_to_message_queue(self, priority: int, msg_type: str, content: dict):
        msg_id = self.message_id_counter
        self.message_id_counter += 1
        self.message_queue.put((priority, msg_id, {"type": msg_type, "content": content}))

    def update_status(self, text: str):
        self.status_label.configure(text=text)

    def add_ai_message(self, text, screenshot=None, is_placeholder=False) -> str:
        return self._add_chat_message("ai", text, screenshot, is_placeholder)

    def add_user_message(self, text):
        self._add_chat_message("user", text)

    def _add_chat_message(self, role, text, screenshot=None, is_placeholder=False) -> str:
        """向聊天窗口添加一条新消息，支持占位符。"""
        align = "w" if role == "ai" else "e"
        avatar = self.ai_avatar if role == "ai" else self.user_avatar
        bg_color = ("#3F3F3F", "#2B2B2B") if role == "ai" else ("#2B4B29", "#1D351C")

        message_frame = ctk.CTkFrame(self.chat_frame, fg_color=bg_color)
        message_frame.grid(row=self.chat_row_counter, column=0, sticky=align, padx=5, pady=4)
        
        avatar_col = 0 if role == "ai" else 1
        content_col = 1 if role == "ai" else 0
        
        if avatar:
            avatar_label = ctk.CTkLabel(message_frame, image=avatar, text="")
            avatar_label.grid(row=0, column=avatar_col, sticky="n", padx=5, pady=5)

        content_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        content_frame.grid(row=0, column=content_col)

        if screenshot:
            img_resized = screenshot.copy()
            img_resized.thumbnail((200, 150))
            ctk_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=img_resized.size)
            img_label = ctk.CTkLabel(content_frame, image=ctk_img, text="")
            img_label.pack(anchor="w", padx=5, pady=2)
            img_label.image = ctk_img

        text_label = ctk.CTkLabel(content_frame, text=text, wraplength=600, justify="left", anchor="w")
        text_label.pack(anchor="w", padx=5, pady=5)
        
        placeholder_id = ""
        if is_placeholder:
            placeholder_id = f"ph_{self.message_id_counter}"
            self.placeholder_map[placeholder_id] = (message_frame, text_label, None)
            message_frame.configure(fg_color=("#EAEAEA", "#333333"))

        self.chat_row_counter += 1
        self.after(100, self.chat_frame._parent_canvas.yview_moveto, 1.0)
        return placeholder_id

    def update_placeholder(self, placeholder_id, new_text, new_screenshot=None):
        """用真实内容更新占位符消息。"""
        if placeholder_id in self.placeholder_map:
            frame, text_label, img_label = self.placeholder_map.pop(placeholder_id)
            if frame.winfo_exists():
                frame.configure(fg_color=("#3F3F3F", "#2B2B2B"))
                text_label.configure(text=new_text)

    def on_closing(self):
        """处理窗口关闭事件，安全地停止所有后台线程。"""
        print("正在关闭应用...")
        self.processing_running = False
        self.webcam_handler.stop()
        self.voice_detector.stop_monitoring()
        self.audio_player.stop()
        # 发送一个虚拟消息来解锁队列的 .get() 阻塞
        self.message_queue.put((99, 0, {"type": "shutdown", "content": ""}))
        self.destroy()

    def _schedule_daily_summary(self):
        """计算距离下一个报告时间还有多久，并设置一个定时器。"""
        now = datetime.now()
        target_time = now.replace(hour=config.DAILY_SUMMARY_HOUR, minute=config.DAILY_SUMMARY_MINUTE, second=0, microsecond=0)

        # 如果今天的目标时间已经过去，则目标设为明天
        if now > target_time:
            target_time = target_time.replace(day=now.day + 1)
        
        # 计算距离目标时间的秒数
        delay_seconds = (target_time - now).total_seconds()
        
        print(f"每日总结报告已预定。下一次将在 {target_time.strftime('%Y-%m-%d %H:%M:%S')} (大约 {delay_seconds / 3600:.1f} 小时后) 触发。")
        
        # after方法需要毫秒
        delay_ms = int(delay_seconds * 1000)
        
        # 设置定时器，在指定时间后调用 _trigger_daily_summary
        self.after(delay_ms, self._trigger_daily_summary)




    #新增处理日志！
    def _handle_daily_summary_message(self):
            """[后台线程] 读取当天的日志，请求AI总结，并播报结果。"""
            today_str = datetime.now().strftime('%Y-%m-%d')
            log_file_path = f'observation_log_{today_str}.jsonl'

            observations_text = ""
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    # 为了不让prompt过长，我们只选择性地读取一部分记录
                    lines = f.readlines()
                    # 这里可以加入更智能的采样逻辑，比如每隔N条取一条
                    for line in lines[-100:]: # 最多读取最近的100条记录
                        obs = json.loads(line)
                        # 格式化成易于AI阅读的文本
                        ts = datetime.fromisoformat(obs['timestamp']).strftime('%H:%M')
                        observations_text += f"- 时间 {ts}: 行为是'{obs['behavior_desc']}', 情绪看起来是'{obs['emotion']}'.\n"
            except FileNotFoundError:
                print("找不到今天的观察日志，无法生成总结。")
                self.after(0, self.add_ai_message, "帆哥，我今天好像没有观察到你的记录，没法做总结哦。")
                return
            except Exception as e:
                print(f"读取日志文件时出错: {e}")
                return

            if not observations_text:
                print("今天的观察日志是空的。")
                self.after(0, self.add_ai_message, "帆哥，我翻了下记录，今天好像是空白的，好好休息！")
                return

            # --- 构建最终的Prompt ---
            summary_prompt = (
                "你是一个非常关心帆哥的朋友小雅。现在是晚上了，你需要根据下面他一天的行为和情绪记录，"
                "为他生成一份温暖、口语化、像朋友聊天一样的每日总结。\n"
                "不要像个机器人一样列数据！你要有洞察力，比如发现他什么时候最累，什么时候效率高，"
                "并给出一些真诚的建议或鼓励。总结要简短，但要充满人情味。\n\n"
                "这是今天的记录：\n"
                f"{observations_text}\n\n"
                "好了，请开始你的总结吧："
            )
            
            print("正在请求AI生成每日总结...")
            
            # 使用独立的上下文进行总结
            summary_context = [self.system_message, {"role": "user", "content": summary_prompt}]
            try:
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat", messages=summary_context
                )
                summary_reply = response.choices[0].message.content
                
                # 记录到主聊天历史
                self.chat_context.append({"role": "user", "content": "[AI 生成的每日总结]"})
                self.chat_context.append({"role": "assistant", "content": summary_reply})

                # 在主线程中显示和播报
                self.after(0, self.add_ai_message, summary_reply)
                self.audio_player.play_text(summary_reply, priority=0) # 最高优先级播报
                
            except Exception as e:
                print(f"生成每日总结时出错: {e}")





    #新的方法-计算时间
    def _trigger_daily_summary(self):
        """
        [主线程调用] 定时器触发此方法，开始生成报告。
        """
        print("时间到！开始生成每日总结报告...")
        
        # 将生成报告的耗时任务放入消息队列，避免阻塞UI
        self._add_to_message_queue(
            priority=1, # 报告是比较重要的任务
            msg_type="daily_summary",
            content={} # 目前不需要额外内容
        )
        
        # 生成完今天的报告后，立即重新预定明天的报告
        self._schedule_daily_summary()







def main():
    """应用的入口函数。"""
    app = MultimediaAssistantApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()