/**
 * Performance Optimization Hooks
 * 性能优化Hooks集合 - 提供memo化和缓存功能
 */

import { 
  useCallback, 
  useMemo, 
  useRef, 
  useEffect,
  DependencyList,
  MutableRefObject
} from 'react';
import { debounce, throttle } from 'lodash';

/**
 * 深度比较两个对象是否相等
 */
export function deepEqual(obj1: any, obj2: any): boolean {
  if (obj1 === obj2) return true;
  
  if (!obj1 || !obj2) return false;
  
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') {
    return obj1 === obj2;
  }
  
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);
  
  if (keys1.length !== keys2.length) return false;
  
  for (const key of keys1) {
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }
  
  return true;
}

/**
 * 使用深度比较的memo hook
 */
export function useDeepMemo<T>(
  factory: () => T,
  deps: DependencyList
): T {
  const ref = useRef<{ value: T; deps: DependencyList }>();
  
  if (!ref.current || !deepEqual(deps, ref.current.deps)) {
    ref.current = { value: factory(), deps };
  }
  
  return ref.current.value;
}

/**
 * 防抖Hook
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: DependencyList = []
): T {
  const callbackRef = useRef(callback);
  
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  
  return useMemo(
    () => debounce(
      (...args: Parameters<T>) => callbackRef.current(...args),
      delay
    ) as unknown as T,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [delay, ...deps]
  );
}

/**
 * 节流Hook
 */
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: DependencyList = []
): T {
  const callbackRef = useRef(callback);
  
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  
  return useMemo(
    () => throttle(
      (...args: Parameters<T>) => callbackRef.current(...args),
      delay
    ) as unknown as T,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [delay, ...deps]
  );
}

/**
 * 缓存异步结果的Hook
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export function useCachedAsync<T>(
  asyncFn: () => Promise<T>,
  deps: DependencyList,
  cacheTime: number = 60000 // 默认缓存1分钟
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
} {
  const cache = useRef<CacheEntry<T> | null>(null);
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: Error | null;
  }>({
    data: null,
    loading: false,
    error: null
  });
  
  const fetchData = useCallback(async (force: boolean = false) => {
    // 检查缓存
    if (!force && cache.current) {
      const now = Date.now();
      if (now - cache.current.timestamp < cacheTime) {
        setState({
          data: cache.current.data,
          loading: false,
          error: null
        });
        return;
      }
    }
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await asyncFn();
      cache.current = { data, timestamp: Date.now() };
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({ 
        data: null, 
        loading: false, 
        error: error as Error 
      });
    }
  }, [asyncFn, cacheTime]);
  
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  
  const refresh = useCallback(() => {
    fetchData(true);
  }, [fetchData]);
  
  return { ...state, refresh };
}

/**
 * 懒加载Hook - 延迟初始化昂贵的计算
 */
export function useLazyInitialization<T>(
  factory: () => T
): T {
  const ref = useRef<T>();
  
  if (ref.current === undefined) {
    ref.current = factory();
  }
  
  return ref.current;
}

/**
 * 组件挂载状态Hook - 防止内存泄漏
 */
export function useIsMounted(): MutableRefObject<boolean> {
  const isMounted = useRef(true);
  
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);
  
  return isMounted;
}

/**
 * 优化的状态更新Hook - 批量更新
 */
import { unstable_batchedUpdates } from 'react-dom';
import { useState } from 'react';

export function useBatchedState<T>(
  initialState: T
): [T, (updates: Partial<T> | ((prev: T) => Partial<T>)) => void] {
  const [state, setState] = useState<T>(initialState);
  
  const batchedSetState = useCallback((
    updates: Partial<T> | ((prev: T) => Partial<T>)
  ) => {
    unstable_batchedUpdates(() => {
      setState(prev => {
        const newUpdates = typeof updates === 'function' 
          ? updates(prev) 
          : updates;
        return { ...prev, ...newUpdates };
      });
    });
  }, []);
  
  return [state, batchedSetState];
}

/**
 * 虚拟滚动Hook - 处理大列表
 */
export function useVirtualScroll<T>(
  items: T[],
  itemHeight: number,
  containerHeight: number,
  overscan: number = 3
): {
  visibleItems: T[];
  totalHeight: number;
  startIndex: number;
  endIndex: number;
  scrollTop: number;
  setScrollTop: (scrollTop: number) => void;
} {
  const [scrollTop, setScrollTop] = useState(0);
  
  const calculations = useMemo(() => {
    const startIndex = Math.max(
      0,
      Math.floor(scrollTop / itemHeight) - overscan
    );
    
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );
    
    const visibleItems = items.slice(startIndex, endIndex + 1);
    const totalHeight = items.length * itemHeight;
    
    return { visibleItems, totalHeight, startIndex, endIndex };
  }, [items, itemHeight, containerHeight, scrollTop, overscan]);
  
  return {
    ...calculations,
    scrollTop,
    setScrollTop
  };
}