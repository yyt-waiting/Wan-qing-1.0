# ai_assistant/core/audio_processing.py

import pyaudio
import wave
import threading
import queue
import time
import os
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
from dashscope.audio.tts_v2 import SpeechSynthesizer

# 从我们自己的包里导入模块
from ai_assistant.utils import config
from ai_assistant.utils.helpers import extract_language_emotion_content
from ai_assistant.core.api_clients import asr_model


# 如何替换TTS服务？(比如换成微软Azure)
# 安装新SDK: pip install azure-cognitiveservices-speech
# 修改config.py: 添加Azure的API Key和Region。
# 修改AudioPlayer类中的合成逻辑:



class AudioPlayer:
    """
    处理文本转语音（TTS）和音频播放的类。
    使用带优先级的队列来管理播放请求，确保重要回复（如用户提问）能插队。
    """
    def __init__(self, app):
        self.app = app
        self.playing = False
        self.play_thread = None
        self.skip_requested = False
        self.tts_queue = queue.PriorityQueue()
        self.tts_thread = None
        self.tts_running = False
        self.max_queue_size = 2 # 允许缓存少量消息

    def start_tts_thread(self):
        """启动后台TTS处理线程。"""
        if not self.tts_running:
            self.tts_running = True
            self.tts_thread = threading.Thread(target=self._process_tts_queue)
            self.tts_thread.daemon = True
            self.tts_thread.start()
            print("TTS处理线程已启动。")

    def _process_tts_queue(self):
        """[后台线程] 持续从队列中获取任务并处理。"""
        while self.tts_running:
            try:
                # 仅在当前没有音频播放时才获取新任务
                if not self.tts_queue.empty() and not self.playing:
                    priority, timestamp, text = self.tts_queue.get()
                    
                    # 忽略过时的低优先级消息 (例如超过15秒的图像分析反馈)
                    if priority > 1 and (time.time() - timestamp) > 15:
                        self.tts_queue.task_done()
                        continue
                    
                    self._synthesize_and_play(text)
                    self.tts_queue.task_done()
                time.sleep(0.1)
            except Exception as e:
                print(f"处理TTS队列时出错: {e}")

    def play_text(self, text: str, priority=2):
        """将文本添加到播放队列。priority=1为最高优先级。"""
        if not text or not text.strip():
            return
        # 如果是高优先级请求或队列已满，清理旧任务
        if priority == 1 or self.tts_queue.qsize() >= self.max_queue_size:
            self._clean_queue(priority)
        
        if not self.tts_running or not self.tts_thread or not self.tts_thread.is_alive():
            self.start_tts_thread()
            
        self.tts_queue.put((priority, time.time(), text))

    def _clean_queue(self, new_priority: int):
        """根据新消息的优先级清理队列。"""
        if self.tts_queue.empty():
            return
        # 最高优先级消息会清空整个队列
        if new_priority == 1:
            while not self.tts_queue.empty():
                try:
                    self.tts_queue.get_nowait()
                    self.tts_queue.task_done()
                except queue.Empty:
                    pass
        # 普通消息只会移除最旧的一个以腾出空间
        else:
             while self.tts_queue.qsize() >= self.max_queue_size:
                try:
                    self.tts_queue.get_nowait()
                    self.tts_queue.task_done()
                except queue.Empty:
                    break

    def _synthesize_and_play(self, text: str):
        """[TTS线程调用] 合成语音并调用内部播放器。"""
        self.app.update_status("正在合成语音...")
        # 标记正在播放，这会暂停VAD的语音检测
        self.app.is_playing_audio = True
        try:
            synthesizer = SpeechSynthesizer(model=config.TTS_MODEL, voice=config.TTS_VOICE)
            audio = synthesizer.call(text)
            
            if not audio:
                raise ValueError("TTS API返回了空音频数据")
            
            output_file = f'output_{int(time.time())}.mp3'
            with open(output_file, 'wb') as f:
                f.write(audio)
            
            self._play_audio_file_internal(output_file)
        except Exception as e:
            print(f"TTS错误: {e}")
            self.app.is_playing_audio = False # 合成失败，恢复VAD

    def _play_audio_file_internal(self, file_path: str):
        """准备并启动一个新线程来播放音频文件。"""
        if self.playing:
            self.skip_current() # 确保旧的播放任务被请求停止
            if self.play_thread and self.play_thread.is_alive():
                self.play_thread.join(timeout=1.0)
        
        self.skip_requested = False
        self.playing = True
        self.app.is_playing_audio = True
        
        self.play_thread = threading.Thread(target=self._play_audio_worker, args=(file_path,))
        self.play_thread.daemon = True
        self.play_thread.start()

    def _play_audio_worker(self, file_path: str):
        """[播放线程] 实际执行音频播放的线程，已修正为非阻塞。"""
        self.app.update_status("正在播放语音...")
        player_process = None
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                raise FileNotFoundError(f"音频文件无效或为空: {file_path}")

            sound = AudioSegment.from_file(file_path, format="mp3")

            # --- 关键修正：将阻塞的play()放入子线程 ---
            player_process = threading.Thread(target=play, args=(sound,), daemon=True)
            player_process.start()

            # 循环检查播放是否结束或是否被请求跳过
            while player_process.is_alive() and not self.skip_requested:
                time.sleep(0.1)
            
            if self.skip_requested:
                print("音频播放已被跳过。")
            else:
                print("音频播放自然结束。")
            # 注意：pydub的play没有直接的.stop()方法，我们通过不再等待线程来“跳过”。
            # --- 修正结束 ---

        except Exception as e:
            print(f"音频播放错误: {e}")
            self.app.update_status("音频播放失败")
        finally:
            self.playing = False
            self.app.is_playing_audio = False
            self.skip_requested = False # 重置跳过状态
            self.app.update_status("就绪")
            try:
                # 播放结束后清理临时文件
                if os.path.exists(file_path) and file_path.startswith('output_'):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除临时音频文件出错: {e}")

    def skip_current(self):
        """请求跳过当前正在播放的音频。"""
        if self.playing:
            print("已请求跳过当前音频。")
            self.skip_requested = True

    def stop(self):
        """停止所有音频活动。"""
        self.tts_running = False
        self.skip_current()
        self._clean_queue(new_priority=1) # 清空队列
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
        print("AudioPlayer 已成功停止。")


class VoiceActivityDetector:
    """使用能量阈值进行连续语音活动检测 (VAD)。"""
    def __init__(self, app):
        self.app = app
        self.running = False
        self.listening_thread = None
        
        # VAD 参数
        self.energy_threshold = 100.0  # 初始阈值，将在校准后更新
        self.silence_duration_threshold = 0.8  # 超过0.8秒的静默则认为一句话结束
        self.min_speech_duration = 0.3 # 短于0.3秒的语音被忽略
        
        # 状态变量
        self.is_speaking = False
        self.speech_start_time = 0
        self.silence_start_time = 0
        self.speech_frames = []
        
        # PyAudio对象
        self.audio = None
        self.stream = None
        
        # 校准参数
        self.is_calibrating = True
        self.calibration_duration = 2.0 # 2秒校准时间

    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.listening_thread = threading.Thread(target=self._monitor_audio_loop)
            self.listening_thread.daemon = True
            self.listening_thread.start()
            print("语音活动检测已启动。")

    def stop_monitoring(self):
        self.running = False
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=1.0)
        self._close_stream()
        print("语音活动检测已停止。")

    def _close_stream(self):
        """安全地关闭PyAudio流和实例。"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
        except Exception as e:
            print(f"关闭音频流时出错: {e}")
        finally:
            self.stream, self.audio = None, None

    def _calculate_energy(self, audio_data: bytes) -> float:
        """计算音频块的能量（均方根）。"""
        data = np.frombuffer(audio_data, dtype=np.int16)
        return np.sqrt(np.mean(np.square(data.astype(np.float64)))) if data.size > 0 else 0

    def _monitor_audio_loop(self):
        """[后台线程] VAD的主循环。"""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16, channels=config.AUDIO_CHANNELS,
                rate=config.AUDIO_RATE, input=True,
                frames_per_buffer=config.AUDIO_CHUNK
            )
            self._calibrate_microphone()
        except Exception as e:
            print(f"初始化PyAudio失败: {e}")
            self.app.update_status("错误: 麦克风初始化失败")
            return

        while self.running:
            try:
                # 如果系统正在播放音频，则暂停检测
                if self.app.is_playing_audio:
                    time.sleep(0.1)
                    continue

                audio_data = self.stream.read(config.AUDIO_CHUNK, exception_on_overflow=False)
                energy = self._calculate_energy(audio_data)

                is_speech = energy > self.energy_threshold

                if is_speech: # 检测到语音
                    if not self.is_speaking:
                        self.is_speaking = True
                        self.speech_start_time = time.time()
                        self.speech_frames = []
                        self.app.update_status("检测到语音输入...")
                    self.silence_start_time = 0
                    self.speech_frames.append(audio_data)
                
                elif self.is_speaking: # 语音后的静默
                    if self.silence_start_time == 0:
                        self.silence_start_time = time.time()
                    
                    if (time.time() - self.silence_start_time) > self.silence_duration_threshold:
                        self._process_detected_speech()

            except IOError as e:
                # 忽略输入溢出错误，但打印提示
                if e.errno == -9981:
                    print("警告: 音频输入溢出，忽略一帧。")
                else:
                    print(f"音频监测IO错误: {e}")
                    time.sleep(0.5)
            except Exception as e:
                print(f"音频监测循环未知错误: {e}")
                time.sleep(0.5)
        self._close_stream()

    def _calibrate_microphone(self):
        """在开始时测量环境噪音以设定动态阈值。"""
        self.app.update_status("校准麦克风中，请保持安静...")
        noise_levels = []
        start_time = time.time()
        while time.time() - start_time < self.calibration_duration:
            try:
                audio_data = self.stream.read(config.AUDIO_CHUNK)
                noise_levels.append(self._calculate_energy(audio_data))
            except IOError: # 忽略校准期间的溢出
                pass
        
        if noise_levels:
            avg_noise = np.mean(noise_levels)
            # 阈值设置为平均噪音的3倍，但至少为50
            self.energy_threshold = max(50.0, avg_noise * 3.0)
            status_msg = f"语音监测已启动 (阈值: {self.energy_threshold:.1f})"
            print(status_msg)
            self.app.update_status(status_msg)
        else:
             self.app.update_status("语音监测启动 (校准失败)")
        self.is_calibrating = False

    def _process_detected_speech(self):
        """处理检测到的一段完整语音。"""
        speech_duration = time.time() - self.speech_start_time
        if speech_duration >= self.min_speech_duration and self.speech_frames:
            frames_copy = self.speech_frames.copy()
            # 在新线程中保存和转录，以防阻塞VAD循环
            threading.Thread(target=self._save_and_request_transcription, args=(frames_copy,), daemon=True).start()

        # 重置状态，准备下一次检测
        self.is_speaking = False
        self.silence_start_time = 0
        self.speech_frames = []
        if not self.app.is_playing_audio: self.app.update_status("就绪")

    def _save_and_request_transcription(self, frames: list):
        """将音频帧保存到WAV文件，并回调主应用来处理转录。"""
        temp_filename = f"speech_{int(time.time())}.wav"
        
        try:
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(config.AUDIO_CHANNELS)
                # pyaudio.get_sample_size() 需要一个PyAudio实例
                pa = pyaudio.PyAudio()
                wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
                pa.terminate()
                wf.setframerate(config.AUDIO_RATE)
                wf.writeframes(b''.join(frames))
            
            # 回调主应用，让它决定如何处理这个音频文件
            self.app.transcribe_audio(temp_filename)
        except Exception as e:
            print(f"保存WAV文件时出错: {e}")

class AudioTranscriber:
    """
处理音频文件转录的专用类。
ASR (语音转文字): asr_model = AutoModel(...)
这是本地模型。funasr这个库非常强大。当你执行这行代码时，它做了：
加载模型文件: 它会去你指定的config.ASR_MODEL_DIR目录下，找到所有巨大的模型文件（通常几百MB甚至更大）。
构建神经网络: 它在内存（或GPU显存，因为你设置了device="cuda:0"）中构建起一个复杂的深度学习模型结构。
初始化组件: 它还加载了辅助模型，比如用于断句的VAD模型(fsmn-vad)。
所以，这行代码的背后是大量的本地计算和资源加载。一旦加载完成，asr_model就是一个功能完备的本地语音识别引擎，
调用它的.generate()方法就可以直接处理音频文件，完全不需要网络。
    """

    def __init__(self, app):
        self.app = app

    def transcribe(self, audio_file: str, high_priority: bool):
        """将指定的音频文件发送给ASR模型进行转录。"""
        if not asr_model:
            self.app.update_status("错误: ASR模型未加载")
            if os.path.exists(audio_file): os.remove(audio_file)
            return
        
        self.app.update_status("正在转录语音...")
        try:
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
                raise FileNotFoundError(f"音频文件无效: {audio_file}")
                
            res = asr_model.generate(input=audio_file, cache={})
            
            if res and "text" in res[0]:
                raw_text = res[0]["text"]
                extracted_text = extract_language_emotion_content(raw_text)
                
                if extracted_text and len(extracted_text.strip()) > 1:
                    # 将结果回调给主应用处理
                    self.app.handle_transcription_result(extracted_text, high_priority)
                else:
                    self.app.update_status("检测到噪音或无意义语音，已忽略")
            else:
                self.app.update_status("未检测到有效语音")

        except Exception as e:
            print(f"转录时发生错误: {e}")
            self.app.update_status("转录失败")
        finally:
            # 确保临时文件被删除
            if os.path.exists(audio_file) and audio_file.startswith("speech_"):
                try:
                    os.remove(audio_file)
                except Exception as e:
                    print(f"删除临时语音文件时出错: {e}")