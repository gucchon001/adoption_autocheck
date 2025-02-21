from functools import wraps
import time
from typing import Callable, Any
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

def retry_on_exception(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    リトライデコレータ
    
    Args:
        retries (int): 最大リトライ回数
        delay (float): 初期待機時間（秒）
        backoff (float): 待機時間の増加倍率
        exceptions (tuple): リトライ対象の例外タプル
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_delay = delay
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries - 1:
                        logger.error(f"最大リトライ回数({retries})に到達: {str(e)}")
                        raise
                    
                    logger.warning(f"処理失敗 (試行 {attempt + 1}/{retries}): {str(e)}")
                    logger.info(f"{retry_delay}秒後にリトライします")
                    time.sleep(retry_delay)
                    retry_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator