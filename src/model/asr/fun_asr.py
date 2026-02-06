"""
FunASR - 阿里云通义语音识别服务封装
每个音频文件大小不超过2GB，且时长不超过12小时

使用示例:
    asr = FunASR(api_key="your_api_key")
    result = asr.transcribe(["http://example.com/audio.wav"], language_hints=['zh', 'en'])
    print(result)
"""

from http import HTTPStatus
from dashscope.audio.asr import Transcription
from urllib import request
import dashscope
import os
import json
import logging
from typing import List, Optional, Dict, Any, Union

from .base_asr import BaseASR, ASRResult


class FunASR(BaseASR):
    """阿里云FunASR语音识别服务封装类"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化FunASR实例
        
        Args:
            api_key: API密钥，如果不提供则从环境变量DASHSCOPE_API_KEY获取
        """
        super().__init__(api_key)
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置api_key参数或DASHSCOPE_API_KEY环境变量")
            
        dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
        dashscope.api_key = self.api_key
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def transcribe(self, 
                  file_urls: Union[str, List[str]], 
                  language_hints: Optional[List[str]] = None,
                  diarization_enabled: bool = False,
                  **kwargs) -> List[Dict[str, Any]]:
        """
        对音频文件进行语音识别
        
        Args:
            file_urls: 音频文件URL，可以是单个URL字符串或URL列表
            language_hints: 语言提示列表，如['zh', 'en']
            diarization_enabled: 是否启用说话人分离
            **kwargs: 其他参数
            
        Returns:
            识别结果列表，每个元素包含文件URL和识别结果
            
        Raises:
            Exception: 当识别失败时抛出异常
        """
        # 统一处理为列表格式
        if isinstance(file_urls, str):
            file_urls = [file_urls]
            
        self.logger.info(f"开始识别 {len(file_urls)} 个音频文件")
        
        try:
            # 提交识别任务
            task_response = Transcription.async_call(
                model='fun-asr',
                file_urls=file_urls,
                language_hints=language_hints or ['zh', 'en'],
                diarization_enabled=diarization_enabled,
                **kwargs
            )
            
            if not task_response or not task_response.output:
                raise Exception("提交识别任务失败")
                
            task_id = task_response.output.task_id
            self.logger.info(f"任务已提交，任务ID: {task_id}")
            
            # 等待识别完成
            transcription_response = Transcription.wait(task=task_id)
            
            if transcription_response.status_code == HTTPStatus.OK:
                results = []
                
                for i, transcription in enumerate(transcription_response.output['results']):
                    if transcription['subtask_status'] == 'SUCCEEDED':
                        url = transcription['transcription_url']
                        result = json.loads(request.urlopen(url).read().decode('utf8'))
                        
                        usage = {
                            "model": "fun-asr",
                            "total_duration_ms": result.get("properties", {}).get("original_duration_in_milliseconds", 0),
                        }
                        result["usage"] = usage
                        
                        results.append({
                            'file_url': file_urls[i],
                            'status': 'success',
                            'transcription': result
                        })
                        
                        self.logger.info(f"文件 {file_urls[i]} 识别成功")
                    else:
                        results.append({
                            'file_url': file_urls[i],
                            'status': 'failed',
                            'error': transcription
                        })
                        
                        self.logger.error(f"文件 {file_urls[i]} 识别失败: {transcription}")
                
                return results
            else:
                error_msg = f"识别任务失败: {transcription_response.output.message}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"ASR识别过程中出错: {str(e)}")
            raise
    
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
        
        if 'sentences' in transcription:
            sentences = transcription['sentences']
            return ' '.join([sentence.get('text', '') for sentence in sentences])
        elif 'text' in transcription:
            return transcription['text']
        else:
            return str(transcription)