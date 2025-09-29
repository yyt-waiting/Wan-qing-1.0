# ai_assistant/utils/helpers.py

import re
from typing import Tuple
import json
from datetime import datetime

def extract_emotion_type(analysis_text: str) -> str:
    """
    从分析文本中提取情感类型（如开心、沮丧、专注等）。
    
    Args:
        analysis_text (str): AI模型返回的完整分析文本。

    Returns:
        str: 匹配到的情感类型字符串，未匹配到则返回 "未知"。
    """
    emotion_keywords = {
        "开心": ["开心", "微笑", "愉悦", "兴奋"],
        "沮丧": ["沮丧", "皱眉", "低落", "失落"],
        "专注": ["专注", "认真", "投入", "凝神"],
        "疲惫": ["疲惫", "困倦", "乏力", "打哈欠"],
        "生气": ["生气", "愤怒", "烦躁", "不满"],
        "平静": ["平静", "放松", "平和"]
    }
    for emotion, keywords in emotion_keywords.items():
        for kw in keywords:
            if kw in analysis_text:
                return emotion
    return "未知"

def extract_language_emotion_content(text: str) -> str:
    """
    从ASR（语音识别）的原始输出中提取干净的对话内容。
    使用正则表达式，比简单的字符串查找更健壮。
    
    Args:
        text (str): ASR模型返回的带标签的文本，例如 "<|zh|> <|Happy|> 你好世界。"

    Returns:
        str: 清理后的纯文本，例如 "你好世界。"
    """
    # 匹配最后一个 > 符号之后的所有非 > 字符
    match = re.search(r'>\s*([^>]*)$', text)
    if match:
        # group(1) 获取第一个捕获组的内容
        return match.group(1).strip()
    # 如果没有匹配到格式，则返回原始文本（做安全兜底）
    return text.strip()

def log_observation_to_file(observation: dict):
    """
    将单条观察记录以JSON格式追加到每日日志文件中。
    文件名会根据日期自动创建，例如 'observation_log_2023-10-27.jsonl'
    """
    # 将datetime对象转换为ISO格式的字符串，方便之后读取
    if 'timestamp' in observation and isinstance(observation['timestamp'], datetime):
        observation['timestamp'] = observation['timestamp'].isoformat()
        
    # 获取当天的日期作为文件名的一部分
    today_str = datetime.now().strftime('%Y-%m-%d')
    log_file_path = f'observation_log_{today_str}.jsonl'
    
    try:
        # 使用 'a' (append) 模式，将记录作为新的一行追加到文件末尾
        with open(log_file_path, 'a', encoding='utf-8') as f:
            # json.dumps将字典转换为JSON字符串
            # ensure_ascii=False 确保中文字符能被正确写入
            f.write(json.dumps(observation, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"写入观察日志文件时出错: {e}")



def extract_behavior_type(analysis_text: str) -> Tuple[str, str]:
    """
    从AI分析文本中提取行为类型编号和描述。
    
    Args:
        analysis_text (str): AI模型返回的完整分析文本。

    Returns:
        tuple[str, str]: 一个包含 (行为编号, 行为描述) 的元组。
                         未识别则返回 ("0", "未识别")。
    """
    # 优先模式: 匹配 "数字" + "可选分隔符" + "明确的行为描述"
    #正则表达式（Regular Expression） 来从文本中提取特定格式的信息
    pattern = r'(\d+)\s*[.、:]?\s*(认真专注工作|吃东西|用杯子喝水|喝饮料|玩手机|睡觉|其他)'
    match = re.search(pattern, analysis_text)
    
    if match:
        behavior_num = match.group(1)
        behavior_desc = match.group(2)
        return behavior_num, behavior_desc
    
    # 兜底模式: 如果上面的精确模式匹配失败，尝试只匹配行为关键词
    fallback_patterns = [
        ('认真专注工作', '1'),
        ('吃东西', '2'),
        ('用杯子喝水', '3'),
        ('喝饮料', '4'),
        ('玩手机', '5'),
        ('睡觉', '6'),
        ('其他', '7')
    ]
    
    for desc, num in fallback_patterns:
        if re.search(desc, analysis_text):
            return num, desc
            
    return "0", "未识别"



    