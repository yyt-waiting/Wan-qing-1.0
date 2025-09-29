HEAD
# Wan-qing-1.0
Wanqing's first version
# AI伙伴“婉晴”：多模态感知与主动关怀智能系统

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red.svg)]()

**AI伙伴“婉晴”** 是一个基于Python开发的PC端多模态AI助手。它利用计算机视觉和语音识别技术，实时感知用户的行为与情绪状态，并基于大型语言模型（LLM）提供主动、智能的陪伴与关怀。

本项目旨在探索AI在情感计算与个性化交互领域的应用，将一个强大的AI模型从云端带到用户桌面，成为一个有温度、懂关怀的智能伙伴。

---

## ✨ 核心功能

*   **多模态感知系统**:
    *   **👁️ 视觉感知**: 通过摄像头实时分析用户的**7种核心行为**（如工作、玩手机）和**6种核心情绪**（如开心、疲惫），由Qwen-VL大模型提供支持。
    *   **👂 语音感知**: 采用动态噪音校准的**语音活动检测(VAD)**技术，精准捕捉用户话语。使用**本地FunASR模型**进行语音识别，保证低延迟与隐私安全。

*   **智能决策与交互系统**:
    *   **🧠 人格化大脑**: 基于DeepSeek大语言模型，通过详细的系统级Prompt为“婉晴”注入了独特的人格与关怀逻辑。
    *   **❤️‍🩹 主动情绪关怀**: 新增核心功能！系统能够追踪用户的短期情绪变化，在检测到持续负面情绪时**主动发起安慰与关怀**。
    *   **🤫 选择性发言**: 独创的“守门员”逻辑，结合用户状态变化和时间冷却，使AI的介入时机更智能、不打扰。
    *   **🗣️ 流畅语音对话**: 采用**优先级队列**管理TTS（文本转语音）任务，确保关键对话能够“插队”打断常规播报，实现流畅自然的交互体验。

*   **长期记忆与反思能力**:
    *   **✍️ 长期记忆**: 所有的观察与交互都会被记录到本地日志文件中，形成AI的长期“日记”。
    *   **📅 每日总结**: 每日定时或通过快捷键手动触发，AI会“复盘”当天的日志，并生成一份充满洞察力与人情味的**每日总结报告**。

---

## 🚀 快速开始

### 1. 环境准备

*   Python 3.10.6
*   一个支持CUDA的NVIDIA显卡（用于本地ASR模型加速，可选）
*   麦克风和摄像头

### 2. 安装

a. **克隆或下载本项目到本地**

b. **创建并激活Python虚拟环境**
   ```bash
   # 创建虚拟环境
   python -m venv venv
   # 激活虚拟环境 (Windows)
   .\venv\Scripts\activate
   # 激活虚拟环境 (macOS/Linux)
   source venv/bin/activate
   ```

c. **安装依赖**
   本项目所有依赖都已锁定在`requirements.txt`中，以确保环境的稳定性。
   ```bash
   pip install -r requirements.txt
   ```

### 3. 配置

a. 找到项目根目录下的 `utils/config.py` 文件。

b. **填写你的API密钥**：
   ```python
   # Deepseek API 配置
   DEEPSEEK_API_KEY = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'

   # Qwen-VL (Dashscope) API配置
   QWEN_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"

   # OSS配置 (用于视觉分析)
   OSS_ACCESS_KEY_ID = 'LTAIxxxxxxxxxxxxxxxx'
   OSS_ACCESS_KEY_SECRET = 'xxxxxxxxxxxxxxxxxxxxxxxx'
   OSS_BUCKET = 'your-bucket-name'
   OSS_ENDPOINT = 'oss-cn-beijing.aliyuncs.com' # 根据你的OSS区域修改
   ```

c. **(可选) 调整行为参数**:
   你可以根据需要调整`config.py`中的行为参数，如分析频率、回应冷却时间等。

### 4. 运行

一切准备就绪后，运行主程序即可启动“婉晴”。
```bash
python run_assistant.py
```


## 🛠️ 技术栈

*   **核心框架**: CustomTkinter
*   **视觉处理**: OpenCV, Pillow, Qwen-VL API
*   **语音处理**: PyAudio, FunASR (本地), Dashscope TTS API
*   **AI大脑**: DeepSeek API
*   **异步处理**: `threading`, `queue`
*   **云存储**: Aliyun OSS

---

## 📜 版权声明

本项目版权归 **[阳溢涛带领的Book思议小组]** 所有，并保留一切权利。

未经版权持有人书面许可，任何人不得复制、修改、分发或用于商业目的。
>>>>>>> b3803ca (first commit)
