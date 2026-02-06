"""
ASR (Automatic Speech Recognition) 统一接口模块

使用示例:
    from src.model.asr import ASR
    
    # 自动根据环境变量 ASR_PROVIDER 创建对应的ASR实例（默认 bytedance）
    asr = ASR()
    results = asr.transcribe(['url1', 'url2'], language_hints=['zh'])
    text = asr.extract_text(results[0])
    
    # 或显式指定provider
    asr = ASR(provider='funasr')
    asr = ASR(provider='bytedance')
    asr = ASR(provider='qwen')

环境变量配置:
    ASR_PROVIDER: 'funasr'、'bytedance' 或 'qwen' (默认: 'bytedance')
    
    FunASR 需要:
        DASHSCOPE_API_KEY
    
    ByteDanceASR 需要:
        BYTEDANCE_APP_ID
        BYTEDANCE_ACCESS_TOKEN
    
    QwenASR 需要:
        DASHSCOPE_API_KEY
"""

import os
import logging
from typing import Optional

from .base_asr import BaseASR
from .fun_asr import FunASR
from .bytedance_llm_asr import ByteDanceASR
from .qwen_asr import QwenASR


logger = logging.getLogger(__name__)


def ASR(provider: Optional[str] = None, **kwargs) -> BaseASR:
    """
    ASR统一接口 - 获取ASR实例
    
    Args:
        provider: ASR服务提供商，可选 'funasr'、'bytedance' 或 'qwen'
                 如果不提供，则从环境变量 ASR_PROVIDER 获取，默认为 'bytedance'
        **kwargs: 传递给具体ASR实现的参数
                 - FunASR: api_key
                 - ByteDanceASR: app_id, access_token
                 - QwenASR: api_key, region
    
    Returns:
        BaseASR: 配置好的ASR实例
    
    Raises:
        ValueError: 当provider不是支持的值时
        
    Examples:
        >>> # 使用环境变量指定的provider（默认bytedance）
        >>> asr = ASR()
        
        >>> # 显式指定provider
        >>> asr = ASR(provider='funasr')
        >>> asr = ASR(provider='bytedance')
        >>> asr = ASR(provider='qwen')
        
        >>> # 传递自定义参数
        >>> asr = ASR(provider='funasr', api_key='custom_key')
        >>> asr = ASR(provider='qwen', region='singapore')
    """
    # 从环境变量或参数获取provider
    if provider is None:
        provider = os.getenv('ASR_PROVIDER', 'bytedance').lower()
    else:
        provider = provider.lower()
    
    logger.info(f"初始化ASR服务: {provider}")
    
    # 根据provider创建对应的ASR实例
    if provider == 'funasr':
        return FunASR(**kwargs)
    elif provider == 'bytedance':
        return ByteDanceASR(**kwargs)
    elif provider == 'qwen':
        return QwenASR(**kwargs)
    else:
        raise ValueError(
            f"不支持的ASR服务提供商: {provider}. "
            f"支持的provider: 'funasr', 'bytedance', 'qwen'"
        )


# 导出公共接口
__all__ = [
    'ASR',
    'BaseASR',
    'FunASR',
    'ByteDanceASR',
    'QwenASR',
]
