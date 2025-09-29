# ai_assistant/core/api_clients.py


# 你以为的过程: 手动建立HTTP连接 -> 设置请求头(Header) -> 把API Key放进去 -> 把图片URL和Prompt打包成JSON格式 -> 发送请求 -> 等待服务器响应 -> 解析返回的JSON数据 -> 处理可能出现的网络错误...
# 实际的过程: completion = qwen_client.chat.completions.create(...)

#SDK大哥：
# qwen_client.chat.completions.create(...) 这一步又做了什么？
# 当你调用这个.create()方法时，SDK在“幕后”为你做了所有的事情：
# 它根据你传入的model和messages参数，自动构建一个符合API规范的HTTP POST请求。
# 它自动把你的api_key添加到请求头里进行身份验证。
# 它通过底层的网络库（如requests或httpx）把这个请求发送到你配置的base_url。
# 它同步等待服务器处理并返回结果。
# 收到服务器返回的JSON数据后，它会将其解析成一个方便你使用的Python对象（所以你可以用.choices[0].message.content来访问）。
# 如果网络出错了或者API返回了错误码，它还会抛出异常，方便你捕获。

import os
import httpx
from openai import OpenAI
import oss2
import dashscope
from funasr import AutoModel

# --- 关键修正：在程序启动时，从根源上禁用系统代理 ---
# 这几行代码会清除掉所有可能影响网络请求的代理环境变量。
# 这样，后续的所有库（openai, httpx等）在运行时，
# 都会认为“本机没有代理”，从而直接进行网络连接。
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''

# 从我们自己的配置模块导入所有配置信息
from ai_assistant.utils import config

# --- OpenAI-Compatible API Clients ---
# 现在，我们不再需要任何复杂的http_client参数，
# 因为代理问题已经在上面被彻底解决了。
# 我们恢复使用最标准、最干净的初始化方式。

# DeepSeek Client (用于语言模型对话)
deepseek_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

# Qwen-VL Client (用于视觉语言模型分析图像)
qwen_client = OpenAI(
    api_key=config.QWEN_API_KEY,
    base_url=config.QWEN_BASE_URL,
)

# --- Alibaba Cloud Services ---

# TTS (文本转语音) API Key
dashscope.api_key = config.QWEN_API_KEY

# OSS (对象存储服务)
# 修正：oss2.Bucket的第一个参数应该是auth对象
auth = oss2.Auth(config.OSS_ACCESS_KEY_ID, config.OSS_ACCESS_KEY_SECRET)
oss_bucket = oss2.Bucket(auth, config.OSS_ENDPOINT, config.OSS_BUCKET)


# --- Local AI Models ---

# ASR (自动语音识别) Model from FunASR
asr_model = None
try:
    # 确保FunASR也不会受到代理影响
    os.environ['NO_PROXY'] = '*'
    asr_model = AutoModel(
        model=config.ASR_MODEL_DIR,
        trust_remote_code=True,
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": 30000},
        device="cuda:0", # 如果你没有NVIDIA显卡，请改为 "cpu"
    )
    print("ASR模型加载成功。")
except Exception as e:
    print(f"警告：ASR模型加载失败，语音识别功能将不可用。错误: {e}")
    asr_model = None
finally:
    # 恢复环境变量，避免影响其他可能的进程
    os.environ.pop('NO_PROXY', None)