# ai_assistant/ui/camera_window.py

import customtkinter as ctk
from PIL import Image

class CameraWindow(ctk.CTkToplevel):
    """
    一个独立的、可重复使用的窗口，用于显示摄像头画面。
    CTkToplevel 是 customtkinter 中用于创建顶级子窗口的类。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("摄像头实时画面")
        self.geometry("640x480")
        # 当用户点击窗口的关闭按钮时，调用 self.on_closing 方法
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure(fg_color="#1a1a1a")

        # 创建一个框架来容纳摄像头标签，方便管理边距
        self.camera_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.camera_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 用于显示图像的标签
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="正在启动摄像头...", text_color="white")
        self.camera_label.pack(fill="both", expand=True)

        # 状态变量
        self.current_image = None  # 用于保持对CTkImage的引用，防止被垃圾回收
        self.is_closed = False

    def update_frame(self, img: Image.Image):
        """
        用新的图像帧更新窗口内容。
        这个方法会被高频调用（大约每秒20次）。
        """
        # 如果窗口不存在或已标记为关闭，则不执行任何操作
        if self.is_closed or not self.winfo_exists():
            return

        try:
            # 调整图像大小以适应窗口当前尺寸，保持宽高比
            img_resized = img.copy()
            img_resized.thumbnail((self.winfo_width(), self.winfo_height()))

            # 将PIL图像转换为CustomTkinter可以显示的CTkImage对象
            ctk_img = ctk.CTkImage(
                light_image=img_resized,
                dark_image=img_resized,
                size=img_resized.size
            )

            # 更新标签的图像，并清空文本
            self.camera_label.configure(image=ctk_img, text="")
            self.current_image = ctk_img  # 必须保存这个引用！
        except Exception as e:
            # 捕获可能在窗口关闭瞬间发生的UI更新错误
            print(f"更新摄像头帧时出错 (可能窗口已关闭): {e}")

    def on_closing(self):
        """
        处理窗口关闭事件。
        我们选择隐藏(withdraw)而不是销毁(destroy)，这样窗口可以被重新打开，
        而不需要重新创建实例，提高了效率。
        """
        self.is_closed = True
        self.withdraw()