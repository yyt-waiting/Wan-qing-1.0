# run_assistant.py

# ===============================================================
# 多模态AI助手 (帆哥监督器) - 启动入口
# ===============================================================
#
# 如何运行:
# 1. 确保你已经通过 `pip install -r requirements.txt` 安装了所有依赖。
# 2. 在项目根目录下，从终端运行此文件:
#    python run_assistant.py
#
# ===============================================================

import sys
import os

# 将项目根目录添加到Python的模块搜索路径中
# 这样做可以确保 `from ai_assistant...` 导入语句能够正确找到模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 从我们的包中导入主应用的入口函数
from ai_assistant.apps.multimedia_assistant import main

if __name__ == "__main__":
    print("===================================")
    print("  正在启动 多模态AI助手... ")
    print("===================================")
    
    # 调用主函数，启动应用
    main()