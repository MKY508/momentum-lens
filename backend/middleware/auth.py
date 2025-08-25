"""
JWT Authentication Middleware
JWT认证中间件 - 提供安全的API访问控制
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from loguru import logger

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token认证
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """JWT认证中间件"""
    
    def __init__(self):
        # 从环境变量获取配置，提供默认值用于开发
        self.secret_key = os.getenv(
            "JWT_SECRET_KEY", 
            "development-secret-key-change-in-production"
        )
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
        
        # 警告：使用默认密钥
        if self.secret_key == "development-secret-key-change-in-production":
            logger.warning(
                "⚠️  Using default JWT secret key. "
                "Please set JWT_SECRET_KEY in production!"
            )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌
        
        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量
            
        Returns:
            JWT token字符串
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )
        
        return encoded_jwt
    
    async def verify_token(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """
        验证JWT token
        
        Args:
            credentials: Bearer token认证凭据
            
        Returns:
            解码后的token payload
            
        Raises:
            HTTPException: 认证失败时
        """
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = credentials.credentials
        
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # 检查token是否过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_current_user(
        self,
        token_payload: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
        """
        获取当前用户信息
        
        Args:
            token_payload: JWT token解码后的数据
            
        Returns:
            用户信息字典
        """
        user_id = token_payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # 这里可以从数据库获取完整用户信息
        # 暂时返回token中的信息
        return {
            "user_id": user_id,
            "username": token_payload.get("username"),
            "email": token_payload.get("email"),
            "roles": token_payload.get("roles", [])
        }
    
    def require_roles(self, required_roles: list):
        """
        创建角色验证依赖
        
        Args:
            required_roles: 需要的角色列表
            
        Returns:
            FastAPI依赖函数
        """
        async def role_checker(
            current_user: Dict = Depends(self.get_current_user)
        ):
            user_roles = current_user.get("roles", [])
            
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return current_user
        
        return role_checker


# 创建全局认证实例
auth_middleware = AuthMiddleware()

# 导出常用函数
verify_token = auth_middleware.verify_token
get_current_user = auth_middleware.get_current_user
create_access_token = auth_middleware.create_access_token
verify_password = auth_middleware.verify_password
get_password_hash = auth_middleware.get_password_hash