"""
Rate Limiting Middleware
限流中间件 - 防止API滥用
"""

from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import time
import os
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from loguru import logger


class RateLimiter:
    """基于内存的限流器"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        enable: bool = True
    ):
        """
        初始化限流器
        
        Args:
            requests_per_minute: 每分钟请求限制
            requests_per_hour: 每小时请求限制
            enable: 是否启用限流
        """
        self.requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", requests_per_minute))
        self.requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", requests_per_hour))
        self.enable = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true" and enable
        
        # 存储请求记录 {client_id: [(timestamp, path), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        
        # 清理任务
        self._cleanup_task = None
        
        logger.info(
            f"Rate limiter initialized: "
            f"{self.requests_per_minute}/min, "
            f"{self.requests_per_hour}/hour, "
            f"enabled={self.enable}"
        )
    
    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            客户端标识字符串
        """
        # 优先使用认证用户ID
        if hasattr(request.state, "user"):
            return f"user:{request.state.user.get('user_id')}"
        
        # 使用IP地址
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def _clean_old_requests(self, client_id: str, current_time: float):
        """
        清理过期的请求记录
        
        Args:
            client_id: 客户端标识
            current_time: 当前时间戳
        """
        # 只保留最近一小时的记录
        cutoff_time = current_time - 3600
        
        if client_id in self.requests:
            self.requests[client_id] = [
                (ts, path) for ts, path in self.requests[client_id]
                if ts > cutoff_time
            ]
            
            # 如果没有记录了，删除键
            if not self.requests[client_id]:
                del self.requests[client_id]
    
    async def check_rate_limit(self, request: Request) -> bool:
        """
        检查是否超过限流
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            是否允许请求
            
        Raises:
            HTTPException: 超过限流时
        """
        if not self.enable:
            return True
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # 清理旧记录
        self._clean_old_requests(client_id, current_time)
        
        # 获取客户端的请求记录
        client_requests = self.requests[client_id]
        
        # 计算最近一分钟的请求数
        one_minute_ago = current_time - 60
        recent_minute_requests = sum(
            1 for ts, _ in client_requests 
            if ts > one_minute_ago
        )
        
        # 计算最近一小时的请求数
        one_hour_ago = current_time - 3600
        recent_hour_requests = sum(
            1 for ts, _ in client_requests 
            if ts > one_hour_ago
        )
        
        # 检查是否超过限制
        if recent_minute_requests >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_id}: "
                f"{recent_minute_requests}/min"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 60))
                }
            )
        
        if recent_hour_requests >= self.requests_per_hour:
            logger.warning(
                f"Hourly rate limit exceeded for {client_id}: "
                f"{recent_hour_requests}/hour"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 3600))
                }
            )
        
        # 记录这次请求
        client_requests.append((current_time, str(request.url.path)))
        
        # 设置响应头
        if hasattr(request, "state"):
            request.state.rate_limit_headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(
                    self.requests_per_minute - recent_minute_requests - 1
                ),
                "X-RateLimit-Reset": str(int(current_time + 60))
            }
        
        return True
    
    async def periodic_cleanup(self):
        """定期清理过期记录的后台任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                current_time = time.time()
                clients_to_clean = list(self.requests.keys())
                
                for client_id in clients_to_clean:
                    self._clean_old_requests(client_id, current_time)
                
                logger.debug(
                    f"Rate limiter cleanup: "
                    f"{len(self.requests)} active clients"
                )
                
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")


# 创建默认限流器实例
default_rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI中间件函数
    
    Args:
        request: 请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        响应对象
    """
    # 检查限流
    await default_rate_limiter.check_rate_limit(request)
    
    # 处理请求
    response = await call_next(request)
    
    # 添加限流响应头
    if hasattr(request.state, "rate_limit_headers"):
        for header, value in request.state.rate_limit_headers.items():
            response.headers[header] = value
    
    return response