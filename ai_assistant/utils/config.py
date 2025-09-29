# ai_assistant/utils/config.py

# --- 应用行为配置 ---
# 图像分析的频率（单位：秒）。
# 调低此值会让AI响应更频繁，但也会增加API调用成本。
#作用: 控制摄像头每隔多少秒进行一次图像分析。
ANALYSIS_INTERVAL_SECONDS = 35


# --- 情绪关怀配置 ---
# 定义哪些情绪被视为“负面”
NEGATIVE_EMOTIONS = ["沮丧", "生气", "疲惫"]

# 当连续检测到负面情绪的次数超过这个阈值时，触发主动关怀
EMOTION_TRIGGER_THRESHOLD = 6


# --- 每日总结报告配置 ---
# 触发每日总结的时间 (24小时制)
DAILY_SUMMARY_HOUR = 18  # 晚上6点
DAILY_SUMMARY_MINUTE = 0   # 0分



# --- 安全提示 ---
# 建议未来使用环境变量或 .env 文件来管理敏感信息，避免直接将密钥写入代码。

# --- OSS (对象存储) 配置 ---
OSS_ACCESS_KEY_ID = 'xxxxxxxxxxxxx'
OSS_ACCESS_KEY_SECRET = 'xxxxxxxxxxxxx'
OSS_ENDPOINT = 'oss-cn-beijing.aliyuncs.com'
OSS_BUCKET = 'camera-vedio-place'

# --- Deepseek API 配置 ---
DEEPSEEK_API_KEY = 'xxxxxxxxxxxxx'
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'

# --- Qwen-VL (通义千问视觉语言模型) API 配置 ---
QWEN_API_KEY = "xxxxxxxxxxxxx"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# --- TTS (文本转语音) 配置 ---
TTS_MODEL = "cosyvoice-v1"
TTS_VOICE = "longwan"

# --- SenseVoice ASR (语音识别) 配置 ---
ASR_MODEL_DIR = "iic/SenseVoiceSmall"

# --- 音频录制配置 ---
AUDIO_CHUNK = 1024
AUDIO_FORMAT = 16  # 对应 pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_RATE = 16000
AUDIO_WAVE_OUTPUT_FILENAME = "output.wav"

# --- 日志文件配置 ---
LOG_FILE = "behavior_log.txt"

# --- Matplotlib 中文字体配置 ---
# 尝试加载系统中的中文字体，以确保图表能正确显示中文。
try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import os

    # 常见中文字体列表
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'NSimSun', 'FangSong', 'KaiTi']
    chinese_font = None
    
    for font_name in chinese_fonts:
        try:
            # 查找字体路径
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            if os.path.exists(font_path):
                chinese_font = font_name
                break
        except:
            continue
    
    if chinese_font:
        plt.rcParams['font.sans-serif'] = [chinese_font, 'DejaVu Sans']
        print(f"成功加载中文字体: {chinese_font}")
    else:
        print("警告：未找到可用的中文字体，图表中的中文可能显示为方框。")
        
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"设置Matplotlib中文字体时出错: {e}")