# ai_assistant/core/webcam_handler.py
import cv2
import time
import io
import threading
from PIL import Image
from datetime import datetime
import logging
import oss2

# 从我们自己的包里导入所需模块
from ai_assistant.core.api_clients import qwen_client, oss_bucket
from ai_assistant.utils.helpers import extract_behavior_type, extract_emotion_type
from ai_assistant.ui.camera_window import CameraWindow
from ai_assistant.utils import config

class WebcamHandler:
    """
    处理摄像头捕获、图像分析和与主应用通信的核心类。
    它作为一个独立的引擎，通过回调函数与主应用解耦。
    """
    def __init__(self, app):
        """
        初始化WebcamHandler。
        Args:
            app: 主应用的实例。它必须实现 handle_analysis_result 和 update_status 方法。
        """
        self.app = app
        self.running = False
        self.paused = False
        self.processing = False
        self.cap = None
        self.webcam_thread = None
        self.last_webcam_image = None
        self.camera_window = None

    def start(self) -> bool:
        """启动摄像头捕获进程，并开始后台分析循环。"""
        if self.running:
            return True
        try:
            # 尝试打开默认摄像头 (ID=0)
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.app.update_status("错误: 无法打开摄像头")
                return False
            
            self.running = True
            self.create_camera_window()
            
            # 启动一个后台守护线程来持续读取摄像头帧
            self.webcam_thread = threading.Thread(target=self._process_webcam_frames)
            self.webcam_thread.daemon = True
            self.webcam_thread.start()
            
            # 延迟2秒后，启动第一次图像分析
            self.app.after(2000, self.trigger_next_capture)
            return True
        except Exception as e:
            self.app.update_status(f"启动摄像头出错: {e}")
            return False

    def stop(self):
        """安全地停止所有线程和摄像头硬件。"""
        self.running = False
        if self.webcam_thread and self.webcam_thread.is_alive():
            self.webcam_thread.join(timeout=1.0) # 等待线程结束
        if self.cap:
            self.cap.release() # 释放摄像头资源
        if self.camera_window and self.camera_window.winfo_exists():
            self.camera_window.destroy()
        self.camera_window = None
        print("WebcamHandler 已成功停止。")

    def _process_webcam_frames(self):
        """[后台线程] 持续从摄像头读取帧并更新UI窗口。"""
        last_ui_update_time = 0
        ui_update_interval = 0.05  # 20 FPS

        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                # 转换颜色格式 (OpenCV: BGR -> PIL: RGB)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                self.last_webcam_image = img # 缓存最新一帧
                
                # 控制UI更新频率，避免过度消耗资源
                current_time = time.time()
                if self.camera_window and not self.camera_window.is_closed and \
                   (current_time - last_ui_update_time) >= ui_update_interval:
                    self.camera_window.update_frame(img)
                    last_ui_update_time = current_time
                
                time.sleep(0.01) # 稍微让出CPU
            except Exception as e:
                print(f"摄像头处理循环错误: {e}")
                time.sleep(1)

    def trigger_next_capture(self):
        """
        [主线程调用] 触发下一次图像分析的入口点。
        检查所有状态标志，确保不会重复或在不当的时机执行分析。
        """
        if self.running and not self.paused and not self.processing:
            print(f"[{time.strftime('%H:%M:%S')}] 触发新一轮图像分析")
            
            # 将耗时的分析任务放入一个新线程，以防阻塞UI
            analysis_thread = threading.Thread(target=self._capture_and_analyze_pipeline)
            analysis_thread.daemon = True
            analysis_thread.start()

    def _capture_and_analyze_pipeline(self):
        """[分析线程] 执行完整的“捕获->上传->分析->回调”流程。"""
        self.processing = True
        try:
            self.app.update_status("正在捕捉图像...")
            screenshots, current_screenshot = self._capture_screenshots()
            if not screenshots:
                raise ValueError("未能捕获有效截图")
                
            self.app.update_status("正在上传图像...")
            screenshot_urls = self._upload_screenshots(screenshots)
            if not screenshot_urls:
                raise ValueError("上传截图失败")

            self.app.update_status("正在分析图像...")
            analysis_text = self._get_image_analysis(screenshot_urls)
            if not analysis_text:
                raise ValueError("图像分析返回空结果")

            # 从分析结果中提取结构化数据
            behavior_num, behavior_desc = extract_behavior_type(analysis_text)
            emotion = extract_emotion_type(analysis_text)
            
            # 记录到日志文件
            timestamp = datetime.now()
            log_message = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - BEHAVIOR: {behavior_desc} ({behavior_num}) - EMOTION: {emotion} - DETAIL: {analysis_text}"
            logging.info(log_message)
            
            # *** 关键一步：通过回调函数将结果传递给主应用 ***
            # WebcamHandler不关心结果如何被使用，它只负责产生结果。~！！！！！！！！！！！！！！

            self.app.handle_analysis_result(
                timestamp, analysis_text, behavior_num, behavior_desc, 
                emotion, current_screenshot
            )

        except Exception as e:
            error_msg = f"捕获与分析流程出错: {e}"
            print(error_msg)
            self.app.update_status(error_msg)
        finally:
            # 无论成功或失败，都必须重置processing状态并安排下一次捕获
            self.processing = False
            # 使用 self.app.after 在主线程中安全地调度下一次任务
            # 10000毫秒 = 10秒，控制API调用频率
            # 将秒转换为毫秒给 after 方法使用
            delay_ms = int(config.ANALYSIS_INTERVAL_SECONDS * 1000)
            self.app.after(delay_ms, self.trigger_next_capture)








    def _capture_screenshots(self, num_shots=4, interval=0.1) -> tuple:
        """[分析线程] 从摄像头捕获多张连续截图以模拟动态信息。"""
        screenshots = []
        # --- 关键修正：直接从摄像头硬件读取，确保每一帧都是新的 ---
        for _ in range(num_shots):
            if not self.cap or not self.cap.isOpened():
                break # 如果摄像头关闭了，则停止捕获
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                screenshots.append(Image.fromarray(frame_rgb))
            time.sleep(interval)
        
        return screenshots, self.last_webcam_image

    def _upload_screenshots(self, screenshots: list) -> list:
        """[分析线程] 将截图列表上传到OSS并返回URLs。"""
        oss_urls = []
        for i, img in enumerate(screenshots):
            # 将PIL Image对象转换为内存中的JPEG字节流
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            buffer.seek(0)
            
            object_key = f"screenshots/{int(time.time())}_{i}.jpg"
            result = oss_bucket.put_object(object_key, buffer)
            
            if result.status == 200:
                url = f"https://{config.OSS_BUCKET}.{config.OSS_ENDPOINT}/{object_key}"
                oss_urls.append(url)
        return oss_urls


# url = f"https://{config.OSS_BUCKET}.{config.OSS_ENDPOINT}/{object_key}"
# 这是在做什么？
# 这行代码是根据OSS的规则，拼接出一个完整的、可以通过互联网访问的公开URL地址。

    def _get_image_analysis(self, image_urls: list) -> str:
        """[分析线程] 调用Qwen-VL API分析图像，同时获取行为和情感。"""
        system_prompt = (
            "详细观察这个人的行为和面部情感和表情。行为需判断为：1.认真专注工作, 2.吃东西, "
            "3.用杯子喝水, 4.喝饮料, 5.玩手机, 6.睡觉, 7.其他。情感需判断为：开心、"
            "沮丧、专注、疲惫、生气、平静等常见情绪,其中重点要检测用户的负面情绪。分析时结合表情（如皱眉、微笑）、"
            "姿势和环境，用中文明确指出行为类型（带编号）和情感类型。"
        )
        user_prompt = "这个人正在做什么？情绪又是如何的？请详细描述观察内容，并明确给出行为编号和情感结果。"
        
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {
                "role": "user", 
                "content": [
                    {"type": "video", "video": image_urls},
                    {"type": "text", "text": user_prompt}
                ]
            }
        ]
        
        completion = qwen_client.chat.completions.create(
            model="qwen-vl-max",
            messages=messages,
        )
        return completion.choices[0].message.content

    def toggle_pause(self):
        """[主线程调用] 切换分析循环的暂停/恢复状态。"""
        self.paused = not self.paused
        status = "已暂停分析" if self.paused else "已恢复分析"
        self.app.update_status(status)
        # 如果是恢复，则立即尝试触发一次分析
        if not self.paused:
            self.app.after(500, self.trigger_next_capture)
            




    def toggle_camera_window(self):
        """[主线程调用] 显示或隐藏摄像头窗口。"""
        if self.camera_window and not self.camera_window.is_closed:
            self.camera_window.on_closing()
        else:
            self.create_camera_window()

    def create_camera_window(self):
        """[主线程调用] 创建或显示摄像头窗口。"""
        if not self.camera_window or self.camera_window.is_closed:
            self.camera_window = CameraWindow(self.app)
            self.camera_window.is_closed = False
        else:
            self.camera_window.deiconify() # Toplevel窗口隐藏后用deiconify来显示

        # 将窗口定位在主窗口下方，增加一些偏移以防重叠
        self.app.update() # 确保主窗口位置信息是最新的
        main_x = self.app.winfo_x()
        main_y = self.app.winfo_y()
        main_height = self.app.winfo_height()
        self.camera_window.geometry(f"640x480+{main_x}+{main_y + main_height + 40}")
        
