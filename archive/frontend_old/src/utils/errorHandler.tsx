/**
 * Centralized Error Handler
 * 统一错误处理中心 - 提供一致的错误管理
 */

import axios, { AxiosError } from 'axios';

/**
 * 应用错误类
 */
export class AppError extends Error {
  constructor(
    public message: string,
    public code: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'AppError';
    
    // 保持原型链
    Object.setPrototypeOf(this, AppError.prototype);
  }
  
  /**
   * 是否为网络错误
   */
  isNetworkError(): boolean {
    return this.code === 'NETWORK_ERROR';
  }
  
  /**
   * 是否为认证错误
   */
  isAuthError(): boolean {
    return this.statusCode === 401 || this.code === 'AUTH_ERROR';
  }
  
  /**
   * 是否为权限错误
   */
  isPermissionError(): boolean {
    return this.statusCode === 403 || this.code === 'PERMISSION_ERROR';
  }
  
  /**
   * 是否为验证错误
   */
  isValidationError(): boolean {
    return this.statusCode === 400 || this.code === 'VALIDATION_ERROR';
  }
  
  /**
   * 是否为服务器错误
   */
  isServerError(): boolean {
    return (this.statusCode && this.statusCode >= 500) || 
           this.code === 'SERVER_ERROR';
  }
}

/**
 * 错误代码映射
 */
export const ErrorCodes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  AUTH_ERROR: 'AUTH_ERROR',
  PERMISSION_ERROR: 'PERMISSION_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
  RATE_LIMIT_ERROR: 'RATE_LIMIT_ERROR',
  NOT_FOUND_ERROR: 'NOT_FOUND_ERROR',
} as const;

/**
 * 错误消息映射
 */
const ErrorMessages: Record<string, string> = {
  [ErrorCodes.NETWORK_ERROR]: '网络连接失败，请检查您的网络设置',
  [ErrorCodes.AUTH_ERROR]: '认证失败，请重新登录',
  [ErrorCodes.PERMISSION_ERROR]: '您没有权限执行此操作',
  [ErrorCodes.VALIDATION_ERROR]: '输入数据验证失败',
  [ErrorCodes.SERVER_ERROR]: '服务器错误，请稍后重试',
  [ErrorCodes.TIMEOUT_ERROR]: '请求超时，请重试',
  [ErrorCodes.RATE_LIMIT_ERROR]: '请求过于频繁，请稍后再试',
  [ErrorCodes.NOT_FOUND_ERROR]: '请求的资源不存在',
  [ErrorCodes.UNKNOWN_ERROR]: '发生未知错误',
};

/**
 * 错误处理器类
 */
export class ErrorHandler {
  private static instance: ErrorHandler;
  private errorListeners: Array<(error: AppError) => void> = [];
  private errorLog: AppError[] = [];
  private maxLogSize = 100;
  
  private constructor() {}
  
  /**
   * 获取单例实例
   */
  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }
  
  /**
   * 处理错误
   */
  handle(error: unknown): AppError {
    const appError = this.normalize(error);
    
    // 记录错误
    this.log(appError);
    
    // 通知监听器
    this.notify(appError);
    
    // 特殊处理
    this.handleSpecialCases(appError);
    
    return appError;
  }
  
  /**
   * 标准化错误
   */
  private normalize(error: unknown): AppError {
    // 已经是AppError
    if (error instanceof AppError) {
      return error;
    }
    
    // Axios错误
    if (axios.isAxiosError(error)) {
      return this.handleAxiosError(error);
    }
    
    // 标准Error
    if (error instanceof Error) {
      return new AppError(
        error.message,
        ErrorCodes.UNKNOWN_ERROR,
        undefined,
        { originalError: error }
      );
    }
    
    // 字符串错误
    if (typeof error === 'string') {
      return new AppError(
        error,
        ErrorCodes.UNKNOWN_ERROR
      );
    }
    
    // 未知错误
    return new AppError(
      ErrorMessages[ErrorCodes.UNKNOWN_ERROR],
      ErrorCodes.UNKNOWN_ERROR,
      undefined,
      { originalError: error }
    );
  }
  
  /**
   * 处理Axios错误
   */
  private handleAxiosError(error: AxiosError): AppError {
    const response = error.response;
    const request = error.request;
    
    // 服务器响应错误
    if (response) {
      const { status, data } = response;
      
      // 提取错误信息
      const message = (data as any)?.message || 
                     (data as any)?.detail || 
                     this.getMessageByStatus(status);
      
      const code = this.getCodeByStatus(status);
      
      return new AppError(message, code, status, data);
    }
    
    // 请求发出但无响应
    if (request) {
      if (error.code === 'ECONNABORTED') {
        return new AppError(
          ErrorMessages[ErrorCodes.TIMEOUT_ERROR],
          ErrorCodes.TIMEOUT_ERROR
        );
      }
      
      return new AppError(
        ErrorMessages[ErrorCodes.NETWORK_ERROR],
        ErrorCodes.NETWORK_ERROR
      );
    }
    
    // 请求配置错误
    return new AppError(
      error.message || ErrorMessages[ErrorCodes.UNKNOWN_ERROR],
      ErrorCodes.UNKNOWN_ERROR
    );
  }
  
  /**
   * 根据状态码获取错误代码
   */
  private getCodeByStatus(status: number): string {
    switch (status) {
      case 400:
        return ErrorCodes.VALIDATION_ERROR;
      case 401:
        return ErrorCodes.AUTH_ERROR;
      case 403:
        return ErrorCodes.PERMISSION_ERROR;
      case 404:
        return ErrorCodes.NOT_FOUND_ERROR;
      case 429:
        return ErrorCodes.RATE_LIMIT_ERROR;
      default:
        if (status >= 500) {
          return ErrorCodes.SERVER_ERROR;
        }
        return ErrorCodes.UNKNOWN_ERROR;
    }
  }
  
  /**
   * 根据状态码获取错误消息
   */
  private getMessageByStatus(status: number): string {
    const code = this.getCodeByStatus(status);
    return ErrorMessages[code] || ErrorMessages[ErrorCodes.UNKNOWN_ERROR];
  }
  
  /**
   * 记录错误
   */
  private log(error: AppError): void {
    // 添加时间戳
    (error as any).timestamp = new Date().toISOString();
    
    // 添加到日志
    this.errorLog.push(error);
    
    // 限制日志大小
    if (this.errorLog.length > this.maxLogSize) {
      this.errorLog.shift();
    }
    
    // 控制台输出（开发环境）
    if (process.env.NODE_ENV === 'development') {
      console.error('[ErrorHandler]', error);
    }
    
    // TODO: 发送到错误监控服务（如Sentry）
  }
  
  /**
   * 通知错误监听器
   */
  private notify(error: AppError): void {
    this.errorListeners.forEach(listener => {
      try {
        listener(error);
      } catch (e) {
        console.error('Error in error listener:', e);
      }
    });
  }
  
  /**
   * 处理特殊情况
   */
  private handleSpecialCases(error: AppError): void {
    // 认证错误 - 清除token并跳转登录
    if (error.isAuthError()) {
      localStorage.removeItem('auth_token');
      // 触发登录跳转
      window.dispatchEvent(new CustomEvent('auth:required'));
    }
    
    // 限流错误 - 显示特殊提示
    if (error.code === ErrorCodes.RATE_LIMIT_ERROR) {
      const retryAfter = error.details?.headers?.['x-ratelimit-reset'];
      if (retryAfter) {
        const waitTime = new Date(retryAfter * 1000).getTime() - Date.now();
        error.message += ` (请等待 ${Math.ceil(waitTime / 1000)} 秒)`;
      }
    }
  }
  
  /**
   * 添加错误监听器
   */
  addListener(listener: (error: AppError) => void): () => void {
    this.errorListeners.push(listener);
    
    // 返回取消订阅函数
    return () => {
      const index = this.errorListeners.indexOf(listener);
      if (index > -1) {
        this.errorListeners.splice(index, 1);
      }
    };
  }
  
  /**
   * 获取错误日志
   */
  getErrorLog(): AppError[] {
    return [...this.errorLog];
  }
  
  /**
   * 清除错误日志
   */
  clearErrorLog(): void {
    this.errorLog = [];
  }
  
  /**
   * 获取最近的错误
   */
  getRecentErrors(count: number = 10): AppError[] {
    return this.errorLog.slice(-count);
  }
}

// 导出单例实例
export const errorHandler = ErrorHandler.getInstance();

// 导出便捷函数
export const handleError = (error: unknown): AppError => {
  return errorHandler.handle(error);
};

/**
 * React错误边界组件
 */
import React, { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: React.ErrorInfo) => ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }
  
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // 记录错误
    errorHandler.handle(error);
    
    // 调用回调
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // 更新状态
    this.setState({ errorInfo });
  }
  
  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(
          this.state.error,
          this.state.errorInfo!
        );
      }
      
      // 默认错误UI
      return (
        <div style={{ 
          padding: '20px', 
          background: '#f5f5f5', 
          border: '1px solid #ddd',
          borderRadius: '4px',
          margin: '20px'
        }}>
          <h2 style={{ color: '#d32f2f' }}>出错了</h2>
          <p>{this.state.error.message}</p>
          {process.env.NODE_ENV === 'development' && (
            <details style={{ marginTop: '10px' }}>
              <summary>错误详情</summary>
              <pre style={{ 
                background: '#fff', 
                padding: '10px',
                overflow: 'auto'
              }}>
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }
    
    return this.props.children;
  }
}