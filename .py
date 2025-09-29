import os

def create_directories(root, directories):
    """创建所有指定的目录"""
    for dir_path in directories:
        full_path = os.path.join(root, dir_path)
        try:
            os.makedirs(full_path, exist_ok=True)
            print(f"成功创建目录: {full_path}")
        except Exception as e:
            print(f"创建目录失败 {full_path}: {str(e)}")

def create_files(root, files):
    """创建所有指定的文件"""
    for file_path in files:
        full_path = os.path.join(root, file_path)
        try:
            # 确保文件所在目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # 创建空文件
            with open(full_path, 'w') as f:
                pass
            print(f"成功创建文件: {full_path}")
        except Exception as e:
            print(f"创建文件失败 {full_path}: {str(e)}")

def main():
    """主函数，创建项目结构"""
    # 项目根目录
    root = "behavior_monitoring_suite"
    
    # 定义需要创建的目录结构
    directories = [
        "ai_assistant/apps",
        "ai_assistant/core",
        "ai_assistant/ui",
        "ai_assistant/utils",
        "ai_assistant/assets"
    ]
    
    # 定义需要创建的文件
    files = [
        "run_assistant.py",
        "run_visualizer.py",
        "requirements.txt",
        "README.md",
        "ai_assistant/__init__.py",
        "ai_assistant/apps/__init__.py",
        "ai_assistant/apps/multimedia_assistant.py",
        "ai_assistant/apps/behavior_visualizer_app.py",
        "ai_assistant/core/__init__.py",
        "ai_assistant/core/webcam_handler.py",
        "ai_assistant/core/audio_processing.py",
        "ai_assistant/core/api_clients.py",
        "ai_assistant/ui/__init__.py",
        "ai_assistant/ui/camera_window.py",
        "ai_assistant/ui/charts.py",
        "ai_assistant/utils/__init__.py",
        "ai_assistant/utils/config.py",
        "ai_assistant/utils/helpers.py",
        "ai_assistant/assets/ai_avatar.png",
        "ai_assistant/assets/user_avatar.png"
    ]
    
    print(f"开始创建项目结构: {root}")
    
    # 创建根目录
    try:
        os.makedirs(root, exist_ok=True)
        print(f"成功创建根目录: {root}")
    except Exception as e:
        print(f"创建根目录失败: {str(e)}")
        return
    
    # 创建子目录
    create_directories(root, directories)
    
    # 创建文件
    create_files(root, files)
    
    print("项目结构创建完成!")

if __name__ == "__main__":
    main()