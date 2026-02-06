"""
ASR (Automatic Speech Recognition) 基类定义
定义了语音识别服务的通用接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union


class BaseASR(ABC):
    """语音识别服务基类"""
    
    def __init__(self, *args, **kwargs):
        """
        初始化ASR实例
        
        不同的ASR服务有不同的认证参数：
        - FunASR: api_key
        - ByteDanceASR: app_id, access_token
        
        子类应该根据各自的服务要求实现具体的初始化逻辑
        """
        pass
    
    @abstractmethod
    def transcribe(self, 
                  file_urls: Union[str, List[str]], 
                  language_hints: Optional[List[str]] = None,
                  **kwargs) -> List[Dict[str, Any]]:
        """
        对音频文件进行语音识别
        
        Args:
            file_urls: 音频文件URL，可以是单个URL字符串或URL列表
            language_hints: 语言提示列表，如['zh', 'en']
            **kwargs: 其他参数
            
        Returns:
            识别结果列表，每个元素包含文件URL和识别结果
        """
        pass
    
    def extract_text(self, transcription_result: Dict[str, Any]) -> str:
        """
        从识别结果中提取纯文本
        
        Args:
            transcription_result: transcribe方法返回的结果
            
        Returns:
            提取的文本字符串
        """
        if transcription_result.get('status') != 'success':
            return ""
            
        # 默认的文本提取逻辑，子类可以重写
        transcription = transcription_result.get('transcription', {})
        
        if isinstance(transcription, str):
            return transcription
        elif isinstance(transcription, dict):
            # 尝试从常见的字段中提取文本
            for text_field in ['text', 'content', 'result']:
                if text_field in transcription:
                    return str(transcription[text_field])
        
        return str(transcription)


class ASRResult:
    """ASR识别结果数据类"""
    
    def __init__(self, file_url: str, status: str, transcription: Any = None, error: Any = None):
        """
        初始化ASR结果
        
        Args:
            file_url: 音频文件URL
            status: 识别状态 ('success', 'failed', 'pending')
            transcription: 识别结果数据
            error: 错误信息
        """
        self.file_url = file_url
        self.status = status
        self.transcription = transcription
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'file_url': self.file_url,
            'status': self.status
        }
        
        if self.transcription is not None:
            result['transcription'] = self.transcription
        
        if self.error is not None:
            result['error'] = self.error
            
        return result
    
    def is_success(self) -> bool:
        """检查识别是否成功"""
        return self.status == 'success'
    
    def get_text(self) -> str:
        """获取识别的文本内容"""
        if not self.is_success() or not self.transcription:
            return ""
        
        # 根据不同的数据结构提取文本
        if isinstance(self.transcription, str):
            return self.transcription
        elif isinstance(self.transcription, dict):
            # 尝试从常见的字段中提取
            for field in ['text', 'content', 'result']:
                if field in self.transcription:
                    return str(self.transcription[field])
        
        return str(self.transcription)
