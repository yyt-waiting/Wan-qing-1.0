# run_visualizer.py

# ===============================================================
# 行为监测与可视化系统 - 启动入口
# ===============================================================
#
# 如何运行:
# 1. 确保你已经通过 `pip install -r requirements.txt` 安装了所有依赖。
# 2. 在项目根目录下，从终端运行此文件:
#    python run_visualizer.py
#
# ===============================================================

import sys
import os

# 将项目根目录添加到Python的模块搜索路径中
# 这样做可以确保 `from ai_assistant...` 导入语句能够正确找到模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 从我们的包中导入主应用的入口函数
from ai_assistant.apps.behavior_visualizer_app import main

if __name__ == "__main__":
    print("=======================================")
    print("  正在启动 行为监测与可视化系统... ")
    print("=======================================")

    # 调用主函数，启动应用
    main()