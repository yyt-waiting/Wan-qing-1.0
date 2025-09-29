# ai_assistant/apps/behavior_visualizer_app.py

import customtkinter as ctk
from datetime import datetime
from PIL import Image

# 从我们自己的包里导入模块
from ai_assistant.core.webcam_handler import WebcamHandler
from ai_assistant.ui.charts import BehaviorVisualizer

class BehaviorVisualizationApp(ctk.CTk):
    """
    行为监测与可视化的主应用窗口。
    这个类负责整合核心逻辑(WebcamHandler)和UI展示(BehaviorVisualizer)。
    """
    
    def __init__(self):
        super().__init__()
        self.title("行为监测与可视化系统")
        self.geometry("1200x700") # 设置一个适合展示图表的尺寸
        self.configure(fg_color="#1a1a1a")

        self._setup_ui()
        
        # 初始化核心组件
        self.webcam_handler = WebcamHandler(self)
        
        # 延迟1秒后启动摄像头，给UI一点时间完全加载
        self.after(1000, self.webcam_handler.start)


    def _setup_ui(self):
        """配置主窗口的UI布局。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # 标题行 (固定高度)
        self.grid_rowconfigure(1, weight=1) # 图表行 (可拉伸)
        self.grid_rowconfigure(2, weight=0) # 状态行 (固定高度)

        # --- 标题 ---
        title_label = ctk.CTkLabel(self, text="行为监测与可视化系统", font=("Arial", 24, "bold"), text_color="white")
        title_label.grid(row=0, column=0, pady=15)

        # --- 可视化图表区域 ---
        # 创建一个框架来容纳图表
        main_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        # 将BehaviorVisualizer实例放入这个框架
        self.behavior_visualizer = BehaviorVisualizer(main_frame)
        
        # --- 状态与控制栏 ---
        status_frame = ctk.CTkFrame(self, fg_color="#2a2a2a", corner_radius=0)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.grid_columnconfigure(2, weight=1) # 让状态标签靠右

        # 控制按钮
        self.toggle_button = ctk.CTkButton(status_frame, text="暂停分析", command=self._toggle_analysis)
        self.toggle_button.grid(row=0, column=0, padx=15, pady=10)
        
        self.toggle_camera_button = ctk.CTkButton(status_frame, text="显示/隐藏摄像头", command=self._toggle_camera_window)
        self.toggle_camera_button.grid(row=0, column=1, padx=0, pady=10)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(status_frame, text="正在初始化...", text_color="white", anchor="e")
        self.status_label.grid(row=0, column=2, padx=15, pady=10, sticky="e")




    def handle_analysis_result(self, timestamp: datetime, analysis_text: str, 
                               behavior_num: str, behavior_desc: str, 
                               emotion: str, screenshot: Image.Image):
        """
        这是来自WebcamHandler的回调函数，用于处理分析结果。
        它是连接核心逻辑和UI的桥梁。
        """
        # 在主线程中安全地更新UI
        self.update_status(f"最新检测: {behavior_desc} (情绪: {emotion})")
        self.behavior_visualizer.add_behavior_data(timestamp, behavior_num)

    def update_status(self, text: str):
        """更新UI上的状态标签。"""
        self.status_label.configure(text=text)

    def _toggle_analysis(self):
        """切换分析的暂停/恢复状态。"""
        self.webcam_handler.toggle_pause()
        new_text = "恢复分析" if self.webcam_handler.paused else "暂停分析"
        self.toggle_button.configure(text=new_text)
        
    def _toggle_camera_window(self):
        """切换摄像头窗口的显示/隐藏。"""
        self.webcam_handler.toggle_camera_window()

    def on_closing(self):
        """
        处理窗口关闭事件，确保所有后台线程都安全停止。
        这是非常重要的一步，可以防止程序关闭后仍有进程残留。
        """
        print("正在关闭应用...")
        self.webcam_handler.stop()
        self.behavior_visualizer.stop()
        self.destroy()

def main():
    """应用的入口函数。"""
    app = BehaviorVisualizationApp()
    # 绑定窗口关闭事件到我们自定义的清理函数
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()