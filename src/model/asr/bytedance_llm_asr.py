"""
ByteDanceASR - 字节跳动火山引擎语音识别服务封装

使用示例:
    asr = ByteDanceASR(app_id="your_app_id", access_token="your_token")
    result = asr.transcribe("http://example.com/audio.mp3")
    print(result)
"""

import json
import time
import uuid
import requests
import logging
import os
from typing import List, Optional, Dict, Any, Union

from .base_asr import BaseASR, ASRResult


class ByteDanceASR(BaseASR):
    """字节跳动火山引擎ASR语音识别服务封装类"""
    
    def __init__(self, app_id: Optional[str] = None, access_token: Optional[str] = None):
        """
        初始化ByteDanceASR实例
        
        Args:
            app_id: 应用ID，如果不提供则从环境变量BYTEDANCE_APP_ID获取
            access_token: 访问令牌，如果不提供则从环境变量BYTEDANCE_ACCESS_TOKEN获取
        """
        super().__init__(access_token)
        
        self.app_id = app_id or os.getenv("BYTEDANCE_APP_ID")
        self.access_token = access_token or os.getenv("BYTEDANCE_ACCESS_TOKEN")
        
        if not self.app_id:
            raise ValueError("APP ID未提供，请设置app_id参数或BYTEDANCE_APP_ID环境变量")
        if not self.access_token:
            raise ValueError("Access Token未提供，请设置access_token参数或BYTEDANCE_ACCESS_TOKEN环境变量")
            
        # API URLs
        self.submit_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit"
        self.query_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query"
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def submit_task(self, 
                   file_url: str,
                   language: Optional[str] = None,
                   enable_channel_split: bool = True,
                   enable_ddc: bool = True,
                   enable_speaker_info: bool = True,
                   enable_punc: bool = True,
                   enable_itn: bool = True,
                   include_words: bool = False,
                   **kwargs) -> tuple[str, str]:
        """
        提交识别任务
        
        Args:
            file_url: 音频文件URL
            language: 语言设置，如 "en-US" 表示英语。为空时支持中英文、上海话、闽南语、四川话、陕西话、粤语识别
            enable_channel_split: 是否启用声道分离
            enable_ddc: 是否启用DDD
            enable_speaker_info: 是否启用说话人信息
            enable_punc: 是否启用标点符号
            enable_itn: 是否启用ITN。文本规范化 (ITN) 如，"一九七零年"->"1970年"和"一百二十三美元"->"$123"。
            include_words: 是否包含单词级别的信息
            **kwargs: 其他参数
            
        Returns:
            tuple: (task_id, x_tt_logid)
        """
        task_id = str(uuid.uuid4())
        
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": "volc.bigasr.auc",
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1"
        }
        
        audio_config = {
            "url": file_url,
        }
        
        # 如果指定了语言，添加到 audio 配置中
        if language:
            audio_config["language"] = language
        
        request_data = {
            "user": {
                "uid": "fake_uid"
            },
            "audio": audio_config,
            "request": {
                "model_name": "bigmodel",
                "enable_channel_split": enable_channel_split,
                "enable_ddc": enable_ddc,
                "enable_speaker_info": enable_speaker_info,
                "enable_punc": enable_punc,
                "enable_itn": enable_itn,
                "show_utterances": True,  # 总是启用utterances
                "corpus": {
                    "correct_table_name": "",
                    "context": ""
                }
            }
        }
        
        # 添加其他自定义参数
        request_data["request"].update(kwargs)
        
        self.logger.info(f"提交任务ID: {task_id}")
        response = requests.post(self.submit_url, data=json.dumps(request_data), headers=headers)
        
        if 'X-Api-Status-Code' in response.headers and response.headers["X-Api-Status-Code"] == "20000000":
            x_tt_logid = response.headers.get("X-Tt-Logid", "")
            self.logger.info(f"任务提交成功 - Status: {response.headers['X-Api-Status-Code']}")
            self.logger.info(f"X-Tt-Logid: {x_tt_logid}")
            return task_id, x_tt_logid
        else:
            error_msg = f"提交任务失败，响应头: {response.headers}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def query_task(self, task_id: str, x_tt_logid: str) -> requests.Response:
        """
        查询识别任务状态
        
        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID
            
        Returns:
            响应对象
        """
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": "volc.bigasr.auc",
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": x_tt_logid
        }
        
        response = requests.post(self.query_url, data=json.dumps({}), headers=headers)
        
        if 'X-Api-Status-Code' in response.headers:
            self.logger.debug(f"查询任务状态 - Status: {response.headers['X-Api-Status-Code']}")
        else:
            error_msg = f"查询任务失败，响应头: {response.headers}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
            
        return response
    
    def transcribe(self, 
                  file_urls: Union[str, List[str]], 
                  language_hints: Optional[List[str]] = None,
                  **kwargs) -> List[Dict[str, Any]]:
        """
        对音频文件进行语音识别
        
        Args:
            file_urls: 音频文件URL，可以是单个URL字符串或URL列表
            language_hints: 语言提示列表，如 ['en-US'] 表示英语。为空时支持中英文、上海话、闽南语、四川话、陕西话、粤语识别
            **kwargs: 其他参数，如enable_channel_split等
            
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
                task_id, x_tt_logid = self.submit_task(file_url, **kwargs)
                
                # 轮询查询任务状态
                while True:
                    query_response = self.query_task(task_id, x_tt_logid)
                    status_code = query_response.headers.get('X-Api-Status-Code', "")
                    
                    if status_code == '20000000':  # 任务完成
                        result_data = query_response.json()
                        # 处理和简化结果
                        simplified_result = self._process_result(result_data, **kwargs)
                        results.append({
                            'file_url': file_url,
                            'status': 'success',
                            'transcription': simplified_result
                        })
                        self.logger.info(f"文件 {file_url} 识别成功")
                        break
                    elif status_code != '20000001' and status_code != '20000002':  # 任务失败
                        error_data = query_response.json() if query_response.text else {}
                        results.append({
                            'file_url': file_url,
                            'status': 'failed',
                            'error': error_data
                        })
                        self.logger.error(f"文件 {file_url} 识别失败: {error_data}")
                        break
                    else:
                        # 任务进行中，等待1秒后继续查询
                        time.sleep(1)
                        
            except Exception as e:
                results.append({
                    'file_url': file_url,
                    'status': 'failed',
                    'error': str(e)
                })
                self.logger.error(f"处理文件 {file_url} 时出错: {str(e)}")
        
        return results
    
    def _process_result(self, raw_result: Dict[str, Any], include_words: bool = False, **kwargs) -> Dict[str, Any]:
        """
        处理和简化原始识别结果
        
        Args:
            raw_result: 原始识别结果
            include_words: 是否包含单词级别的信息
            **kwargs: 其他参数
            
        Returns:
            简化后的结果
        """
        processed_result = {
            "audio_info": raw_result.get("audio_info", {}),
            "result": {}
        }
        
        if "result" in raw_result:
            original_result = raw_result["result"]
            processed_result["result"]["text"] = original_result.get("text", "")
            
            # 处理utterances，移除definite字段，根据参数决定是否包含words
            if "utterances" in original_result:
                processed_utterances = []
                for utterance in original_result["utterances"]:
                    processed_utterance = {
                        "text": utterance.get("text", ""),
                        "start_time": utterance.get("start_time", 0),
                        "end_time": utterance.get("end_time", 0)
                    }
                    
                    # 只有在include_words为True时才包含words信息
                    if include_words and "words" in utterance:
                        processed_utterance["words"] = utterance["words"]
                    
                    processed_utterances.append(processed_utterance)
                
                processed_result["result"]["utterances"] = processed_utterances
        
        usage = {
            "model": "bytedance-big-model-asr",
            "total_duration_ms": processed_result["audio_info"].get("duration", 0),
        }
        processed_result["usage"] = usage
        
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
        
        # 字节跳动火山引擎的标准返回格式：result.text
        if 'result' in transcription and isinstance(transcription['result'], dict):
            return transcription['result'].get('text', '')
        
        return ""