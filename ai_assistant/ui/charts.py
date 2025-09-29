# ai_assistant/ui/charts.py

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import threading
import time

class BehaviorVisualizer:
    """
    一个UI组件，用于处理和显示行为数据的可视化图表。
    它在自己的后台线程中定期刷新，以避免阻塞主UI线程。
    """
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        # 定义行为及其对应的颜色，方便统一管理
        self.behavior_map = {
            "1": "专注工作", "2": "吃东西", "3": "喝水", "4": "喝饮料",
            "5": "玩手机", "6": "睡觉", "7": "其他", "0": "未识别"
        }
        self.behavior_colors = {
            "1": "#4CAF50", "2": "#FFC107", "3": "#2196F3", "4": "#9C27B0",
            "5": "#F44336", "6": "#607D8B", "7": "saddlebrown", "0": "#9E9E9E"
        }
        
        # 数据存储
        self.behavior_history = []  # 存储元组 (timestamp, behavior_num)
        self.behavior_counts = {key: 0 for key in self.behavior_map}
        self.data_lock = threading.Lock() # 线程锁，用于保护共享数据
        
        self._setup_charts_ui()
        
        # 启动后台更新线程
        self.running = True
        self.update_thread = threading.Thread(target=self._update_charts_loop)
        self.update_thread.daemon = True
        self.update_thread.start()

    def _setup_charts_ui(self):
        """创建并配置图表的UI元素。"""
        charts_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True)
        charts_frame.grid_columnconfigure(0, weight=3) # 折线图占3/4空间
        charts_frame.grid_columnconfigure(1, weight=1) # 饼图占1/4空间
        charts_frame.grid_rowconfigure(0, weight=1)

        # --- 折线图 ---
        self.line_fig = Figure(figsize=(7, 4), dpi=100)
        self.line_fig.patch.set_facecolor('#242424')
        self.line_ax = self.line_fig.add_subplot(111, facecolor='#242424')
        self.line_canvas = FigureCanvasTkAgg(self.line_fig, master=charts_frame)
        self.line_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

        # --- 饼图 ---
        self.pie_fig = Figure(figsize=(3.5, 4), dpi=100)
        self.pie_fig.patch.set_facecolor('#242424')
        self.pie_ax = self.pie_fig.add_subplot(111, facecolor='#242424')
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=charts_frame)
        self.pie_canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        
        # 初始绘制一次空图表
        self._redraw_charts()

    def add_behavior_data(self, timestamp: datetime, behavior_num: str):
        """
        [主线程调用] 添加新的行为数据点。
        使用线程锁来确保数据添加的线程安全。
        """
        with self.data_lock:
            if behavior_num not in self.behavior_map:
                behavior_num = "0" # 安全兜底
            self.behavior_history.append((timestamp, behavior_num))
            self.behavior_counts[behavior_num] += 1
            
            # 限制历史记录的长度，防止内存无限增长
            if len(self.behavior_history) > 100:
                self.behavior_history.pop(0)

    def _update_charts_loop(self):
        """[后台线程] 定期刷新图表。"""
        while self.running:
            time.sleep(5) # 每5秒刷新一次
            try:
                # 在主UI线程中安全地调用重绘函数
                self.parent_frame.after(0, self._redraw_charts)
            except Exception as e:
                print(f"图表更新线程调度错误: {e}")

    def _redraw_charts(self):
        """[主线程调用] 在主线程中重新绘制所有图表，确保UI操作的线程安全。"""
        with self.data_lock: # 读取数据时加锁
            self._update_line_chart(self.behavior_history)
            self._update_pie_chart(self.behavior_counts)

    def _update_line_chart(self, history):
        """用最新数据更新折线图。"""
        self.line_ax.clear()
        self.line_ax.set_title("行为随时间变化", color='white')
        self.line_ax.set_xlabel("时间", color='white')
        self.line_ax.tick_params(axis='x', colors='white', rotation=30)
        self.line_ax.tick_params(axis='y', colors='white')
        for spine in self.line_ax.spines.values():
            spine.set_edgecolor('gray')
        
        self.line_ax.set_yticks(range(1, 8))
        self.line_ax.set_yticklabels([self.behavior_map[str(i)] for i in range(1, 8)])
        self.line_ax.set_ylim(0.5, 7.5)

        if history:
            times, behaviors = zip(*history)
            behavior_ints = [int(b) for b in behaviors]
            
            self.line_ax.plot(times, behavior_ints, color='gray', linestyle='--', alpha=0.5, marker='o', markersize=4)
            self.line_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        
        self.line_ax.grid(True, linestyle='--', alpha=0.2, color='gray')
        self.line_fig.tight_layout()
        self.line_canvas.draw()

    def _update_pie_chart(self, counts):
        """用最新分布更新饼图。"""
        self.pie_ax.clear()
        self.pie_ax.set_title("行为分布", color='white')
        
        valid_sizes, valid_labels, valid_colors = [], [], []
        for num, count in counts.items():
            if count > 0 and num != "0": # 只显示有数据的、非"未识别"的行为
                valid_sizes.append(count)
                valid_labels.append(self.behavior_map[num])
                valid_colors.append(self.behavior_colors[num])

        if not valid_sizes:
            self.pie_ax.text(0.5, 0.5, "等待数据...", ha='center', va='center', color='white', transform=self.pie_ax.transAxes)
        else:
            wedges, texts, autotexts = self.pie_ax.pie(
                valid_sizes, autopct='%1.1f%%', colors=valid_colors,
                startangle=90, textprops={'color': 'white', 'fontsize': 9}
            )
            self.pie_ax.legend(wedges, valid_labels, title="行为类型",
                               loc="center left", bbox_to_anchor=(0.95, 0.5),
                               frameon=False, labelcolor='white', fontsize='small')
        
        self.pie_ax.axis('equal')
        self.pie_fig.tight_layout()
        self.pie_canvas.draw()

    def stop(self):
        """停止后台更新线程。"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
        print("BehaviorVisualizer 已成功停止。")