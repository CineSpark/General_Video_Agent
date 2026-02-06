"""
QwenASR - 通义千问语音识别服务封装

使用示例:
    asr = QwenASR(api_key="your_api_key")
    result = asr.transcribe("http://example.com/audio.mp3")
    print(result)
"""

import json
import time
import requests
import logging
import os
from typing import List, Optional, Dict, Any, Union
from urllib import request

from .base_asr import BaseASR, ASRResult


class QwenASR(BaseASR):
    """通义千问语音识别服务封装类"""
    
    def __init__(self, api_key: Optional[str] = None, region: str = "beijing"):
        """
        初始化QwenASR实例
        
        Args:
            api_key: API密钥，如果不提供则从环境变量DASHSCOPE_API_KEY获取
            region: 服务地域，可选 "beijing" 或 "singapore"，默认为 "beijing"
        """
        super().__init__(api_key)
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置api_key参数或DASHSCOPE_API_KEY环境变量")
        
        # 根据地域设置API URL
        if region.lower() == "singapore":
            self.base_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        else:
            self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        
        self.submit_url = f"{self.base_url}/services/audio/asr/transcription"
        self.query_url = f"{self.base_url}/tasks"
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def submit_task(self,
                   file_url: str,
                   model: str = "qwen3-asr-flash-filetrans",
                   language: Optional[str] = None,
                   enable_itn: bool = False,
                   enable_words: bool = False,
                   channel_id: Optional[List[int]] = None,
                   **kwargs) -> str:
        """
        提交识别任务
        
        Args:
            file_url: 音频文件URL
            model: 模型名称，默认为 "qwen3-asr-flash-filetrans"
            language: 音频语种，如 "zh"、"en" 等。若不确定或包含多语种，请勿指定
            enable_itn: 是否启用ITN（逆文本标准化），仅适用于中英文
            enable_words: 是否返回字级别时间戳。false返回句级，true返回字级
            channel_id: 指定需要识别的音轨索引列表，默认为 [0]（第一个音轨）
            **kwargs: 其他参数
            
        Returns:
            str: 任务ID
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        # 构建参数
        parameters = {
            "channel_id": channel_id or [0],
            "enable_itn": enable_itn,
            "enable_words": enable_words,
        }
        
        # 只有明确指定语言时才添加
        if language:
            parameters["language"] = language
        
        # 添加其他自定义参数
        parameters.update(kwargs)
        
        payload = {
            "model": model,
            "input": {
                "file_url": file_url
            },
            "parameters": parameters
        }
        
        self.logger.info(f"提交识别任务: {file_url}")
        response = requests.post(self.submit_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            if "output" in result and "task_id" in result["output"]:
                task_id = result["output"]["task_id"]
                self.logger.info(f"任务提交成功 - Task ID: {task_id}")
                return task_id
            else:
                error_msg = f"提交任务失败，响应: {result}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
        else:
            error_msg = f"提交任务失败，状态码: {response.status_code}，响应: {response.text}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def query_task(self, task_id: str) -> Dict[str, Any]:
        """
        查询识别任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            响应数据字典
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-DashScope-Async": "enable",
            "Content-Type": "application/json"
        }
        
        query_url = f"{self.query_url}/{task_id}"
        response = requests.get(query_url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"查询任务失败，状态码: {response.status_code}，响应: {response.text}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def transcribe(self,
                  file_urls: Union[str, List[str]],
                  language_hints: Optional[List[str]] = None,
                  **kwargs) -> List[Dict[str, Any]]:
        """
        对音频文件进行语音识别
        
        Args:
            file_urls: 音频文件URL，可以是单个URL字符串或URL列表
            language_hints: 语言提示列表，如 ['zh'] 表示中文。为空时自动识别多语种
            **kwargs: 其他参数，如enable_itn、enable_words等
            
        Returns:
            识别结果列表，每个元素包含文件URL和识别结果
        """
        # 统一处理为列表格式
        if isinstance(file_urls, str):
            file_urls = [file_urls]
        
        # 处理 language_hints 参数，取第一个语言提示
        language = None
        if language_hints and len(language_hints) > 0:
            language = language_hints[0]
            if 'language' not in kwargs:
                kwargs['language'] = language
        
        self.logger.info(f"开始识别 {len(file_urls)} 个音频文件")
        
        results = []
        for file_url in file_urls:
            try:
                # 提交识别任务
                task_id = self.submit_task(file_url, **kwargs)
                
                # 轮询查询任务状态
                while True:
                    query_response = self.query_task(task_id)
                    
                    # 检查任务状态
                    if "output" in query_response:
                        task_status = query_response["output"].get("task_status", "")
                        
                        if task_status == "SUCCEEDED":  # 任务完成
                            # 获取转写结果URL
                            result_info = query_response["output"].get("result", {})
                            transcription_url = result_info.get("transcription_url", "")
                            
                            if not transcription_url:
                                error_msg = "未找到 transcription_url"
                                results.append({
                                    'file_url': file_url,
                                    'status': 'failed',
                                    'error': error_msg
                                })
                                self.logger.error(f"文件 {file_url} 识别失败: {error_msg}")
                                break
                            
                            # 下载转写结果
                            self.logger.info(f"下载转写结果: {transcription_url}")
                            transcription_data = json.loads(request.urlopen(transcription_url).read().decode('utf8'))
                            
                            # 处理和简化结果
                            simplified_result = self._process_result(transcription_data, query_response, **kwargs)
                            results.append({
                                'file_url': file_url,
                                'status': 'success',
                                'transcription': simplified_result
                            })
                            self.logger.info(f"文件 {file_url} 识别成功")
                            break
                        elif task_status == "FAILED":  # 任务失败
                            error_data = query_response.get("output", {})
                            results.append({
                                'file_url': file_url,
                                'status': 'failed',
                                'error': error_data
                            })
                            self.logger.error(f"文件 {file_url} 识别失败: {error_data}")
                            break
                        elif task_status in ["PENDING", "RUNNING"]:
                            # 任务进行中，等待1秒后继续查询
                            time.sleep(1)
                        else:
                            # 未知状态
                            error_msg = f"未知任务状态: {task_status}"
                            results.append({
                                'file_url': file_url,
                                'status': 'failed',
                                'error': error_msg
                            })
                            self.logger.error(error_msg)
                            break
                    else:
                        error_msg = f"查询响应格式错误: {query_response}"
                        results.append({
                            'file_url': file_url,
                            'status': 'failed',
                            'error': error_msg
                        })
                        self.logger.error(error_msg)
                        break
                        
            except Exception as e:
                results.append({
                    'file_url': file_url,
                    'status': 'failed',
                    'error': str(e)
                })
                self.logger.error(f"处理文件 {file_url} 时出错: {str(e)}")
        
        return results
    
    def _process_result(self, transcription_data: Dict[str, Any], query_response: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        处理和简化原始识别结果
        
        Args:
            transcription_data: 从 transcription_url 下载的转写数据
            query_response: 任务查询的响应数据
            **kwargs: 其他参数
            
        Returns:
            简化后的结果
        """
        # 提取音频信息
        audio_info = {
            "file_url": transcription_data.get("file_url", ""),
            "audio_info": transcription_data.get("audio_info", {})
        }
        
        # 提取识别结果（transcripts 是数组，包含多个音轨的结果）
        transcripts = transcription_data.get("transcripts", [])
        
        # 合并所有音轨的文本
        full_text = ""
        all_sentences = []
        
        for transcript in transcripts:
            channel_id = transcript.get("channel_id", 0)
            text = transcript.get("text", "")
            sentences = transcript.get("sentences", [])
            
            # 拼接文本
            full_text += text
            
            # 保存句子信息（转换为统一格式）
            for sentence in sentences:
                all_sentences.append({
                    "channel_id": channel_id,
                    "sentence_id": sentence.get("sentence_id", 0),
                    "text": sentence.get("text", ""),
                    "begin_time": sentence.get("begin_time", 0),
                    "end_time": sentence.get("end_time", 0),
                    "language": sentence.get("language", ""),
                    "emotion": sentence.get("emotion", "neutral")
                })
        
        # 计算总时长（毫秒）
        total_duration_ms = 0
        if all_sentences:
            last_sentence = all_sentences[-1]
            total_duration_ms = last_sentence.get("end_time", 0)
        
        # 从查询响应中获取使用信息
        usage_info = query_response.get("usage", {})
        
        processed_result = {
            "audio_info": audio_info,
            "result": {
                "text": full_text,
                "sentences": all_sentences
            },
            "usage": {
                "model": kwargs.get("model", "qwen3-asr-flash-filetrans"),
                "total_duration_ms": total_duration_ms,
                "seconds": usage_info.get("seconds", 0)
            }
        }
        
        return processed_result
    
    def extract_text(self, transcription_result: Dict[str, Any]) -> str:
        """
        从识别结果中提取纯文本
        
        Args:
            transcription_result: transcribe方法返回的结果
            
        Returns:
            提取的文本字符串
        """
        if transcription_result['status'] != 'success':
            return ""
        
        transcription = transcription_result['transcription']
        
        # Qwen ASR的标准返回格式：result.text
        if 'result' in transcription and isinstance(transcription['result'], dict):
            return transcription['result'].get('text', '')
        
        return ""