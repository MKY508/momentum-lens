"""
Trade Frequency Controller
交易频率控制器 - 防止过度交易
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path
from loguru import logger


@dataclass
class TradeRecord:
    """交易记录"""
    etf_code: str
    etf_name: str
    action: str  # BUY/SELL/ROTATE
    timestamp: datetime
    old_score: Optional[float] = None
    new_score: Optional[float] = None
    reason: str = ""


class TradeFrequencyController:
    """交易频率控制器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化交易频率控制器
        
        Args:
            config_path: 配置文件路径
        """
        # 从配置文件或默认值加载参数
        self.min_score_improvement = 0.02  # 最小分数改善2%
        self.max_weekly_rotations = 2      # 每周最大轮换2次
        self.cooldown_days = 7             # 冷却期7天
        self.min_holding_before_rotation = 14  # 轮换前最短持有14天
        
        # 交易记录存储
        self.trade_history: List[TradeRecord] = []
        self.rotation_count_this_week = 0
        self.last_rotation_date: Optional[datetime] = None
        self.holdings_entry_dates: Dict[str, datetime] = {}
        
        # 加载历史记录
        self._load_history()
    
    def can_rotate(self, 
                  current_holding: str,
                  new_candidate: str,
                  current_score: float,
                  new_score: float) -> Tuple[bool, str]:
        """
        检查是否可以进行轮换
        
        Args:
            current_holding: 当前持仓ETF代码
            new_candidate: 新候选ETF代码
            current_score: 当前持仓动量得分
            new_score: 新候选动量得分
            
        Returns:
            (是否可以轮换, 原因说明)
        """
        reasons = []
        can_proceed = True
        
        # 1. 检查分数改善幅度
        score_improvement = (new_score - current_score) / abs(current_score) if current_score != 0 else float('inf')
        if score_improvement < self.min_score_improvement:
            can_proceed = False
            reasons.append(f"分数改善不足: {score_improvement:.1%} < {self.min_score_improvement:.1%}")
        
        # 2. 检查本周轮换次数
        if self._get_weekly_rotation_count() >= self.max_weekly_rotations:
            can_proceed = False
            reasons.append(f"本周已轮换{self.rotation_count_this_week}次，达到上限")
        
        # 3. 检查冷却期
        if self.last_rotation_date:
            days_since_last = (datetime.now() - self.last_rotation_date).days
            if days_since_last < self.cooldown_days:
                can_proceed = False
                reasons.append(f"距上次轮换仅{days_since_last}天，需等待{self.cooldown_days - days_since_last}天")
        
        # 4. 检查最短持有期
        if current_holding in self.holdings_entry_dates:
            holding_days = (datetime.now() - self.holdings_entry_dates[current_holding]).days
            if holding_days < self.min_holding_before_rotation:
                can_proceed = False
                reasons.append(f"持有期仅{holding_days}天，未满足最短{self.min_holding_before_rotation}天要求")
        
        # 5. 检查是否为同类ETF（避免同质化轮换）
        if self._are_similar_etfs(current_holding, new_candidate):
            can_proceed = False
            reasons.append("候选ETF与当前持仓过于相似，不建议轮换")
        
        if can_proceed:
            return True, f"可以轮换: 分数改善{score_improvement:.1%}"
        else:
            return False, " | ".join(reasons)
    
    def record_trade(self, trade_record: TradeRecord):
        """记录交易"""
        self.trade_history.append(trade_record)
        
        if trade_record.action in ['ROTATE', 'SELL']:
            self.last_rotation_date = trade_record.timestamp
            self.rotation_count_this_week = self._get_weekly_rotation_count() + 1
            
            # 移除旧持仓记录
            if trade_record.etf_code in self.holdings_entry_dates:
                del self.holdings_entry_dates[trade_record.etf_code]
        
        if trade_record.action in ['BUY', 'ROTATE']:
            # 记录新持仓入场时间
            self.holdings_entry_dates[trade_record.etf_code] = trade_record.timestamp
        
        # 保存历史记录
        self._save_history()
    
    def get_rotation_stats(self) -> Dict:
        """获取轮换统计信息"""
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_rotations = [
            t for t in self.trade_history 
            if t.action == 'ROTATE' and t.timestamp >= week_start
        ]
        
        return {
            'weekly_rotations': len(week_rotations),
            'weekly_limit': self.max_weekly_rotations,
            'rotations_remaining': max(0, self.max_weekly_rotations - len(week_rotations)),
            'last_rotation': self.last_rotation_date.isoformat() if self.last_rotation_date else None,
            'days_since_rotation': (datetime.now() - self.last_rotation_date).days if self.last_rotation_date else None,
            'cooldown_remaining': max(0, self.cooldown_days - ((datetime.now() - self.last_rotation_date).days if self.last_rotation_date else self.cooldown_days))
        }
    
    def suggest_rotation_timing(self, candidates: List[Dict]) -> Dict:
        """
        建议轮换时机
        
        Args:
            candidates: 候选ETF列表，包含code, name, score等信息
            
        Returns:
            轮换建议
        """
        suggestions = {
            'immediate': [],    # 立即可执行
            'pending': [],      # 等待条件满足
            'blocked': []       # 被阻止
        }
        
        for candidate in candidates:
            # 检查每个候选是否可以轮换当前持仓
            for holding_code, entry_date in self.holdings_entry_dates.items():
                can_rotate, reason = self.can_rotate(
                    holding_code,
                    candidate['code'],
                    candidate.get('current_score', 0),
                    candidate['score']
                )
                
                if can_rotate:
                    suggestions['immediate'].append({
                        'from': holding_code,
                        'to': candidate['code'],
                        'score_improvement': candidate['score'] - candidate.get('current_score', 0),
                        'reason': reason
                    })
                else:
                    # 分析何时可以轮换
                    holding_days = (datetime.now() - entry_date).days
                    wait_days = max(0, self.min_holding_before_rotation - holding_days)
                    
                    if wait_days > 0:
                        suggestions['pending'].append({
                            'from': holding_code,
                            'to': candidate['code'],
                            'wait_days': wait_days,
                            'available_date': (datetime.now() + timedelta(days=wait_days)).date().isoformat(),
                            'reason': f"需再持有{wait_days}天"
                        })
                    else:
                        suggestions['blocked'].append({
                            'from': holding_code,
                            'to': candidate['code'],
                            'reason': reason
                        })
        
        return suggestions
    
    def _get_weekly_rotation_count(self) -> int:
        """获取本周轮换次数"""
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_rotations = [
            t for t in self.trade_history 
            if t.action == 'ROTATE' and t.timestamp >= week_start
        ]
        return len(week_rotations)
    
    def _are_similar_etfs(self, etf1: str, etf2: str) -> bool:
        """
        判断两个ETF是否过于相似
        简单规则：同行业或高相关性
        """
        # 半导体相关
        semiconductor_etfs = ['512760', '512480', '159801']
        # 新能源相关
        new_energy_etfs = ['516160', '515790', '515030', '588000']
        # 科技相关
        tech_etfs = ['512720', '515000', '159939']
        
        etf_groups = [semiconductor_etfs, new_energy_etfs, tech_etfs]
        
        for group in etf_groups:
            if etf1 in group and etf2 in group:
                return True
        
        return False
    
    def _load_history(self):
        """加载历史交易记录"""
        history_file = Path("data/trade_history.json")
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    # 恢复交易记录
                    for record_data in data.get('trades', []):
                        self.trade_history.append(TradeRecord(
                            etf_code=record_data['etf_code'],
                            etf_name=record_data['etf_name'],
                            action=record_data['action'],
                            timestamp=datetime.fromisoformat(record_data['timestamp']),
                            old_score=record_data.get('old_score'),
                            new_score=record_data.get('new_score'),
                            reason=record_data.get('reason', '')
                        ))
                    
                    # 恢复持仓入场时间
                    for code, date_str in data.get('holdings_dates', {}).items():
                        self.holdings_entry_dates[code] = datetime.fromisoformat(date_str)
                    
                    # 恢复最后轮换时间
                    if data.get('last_rotation_date'):
                        self.last_rotation_date = datetime.fromisoformat(data['last_rotation_date'])
                        
            except Exception as e:
                logger.error(f"Failed to load trade history: {e}")
    
    def _save_history(self):
        """保存历史交易记录"""
        history_file = Path("data/trade_history.json")
        history_file.parent.mkdir(exist_ok=True)
        
        try:
            data = {
                'trades': [
                    {
                        'etf_code': t.etf_code,
                        'etf_name': t.etf_name,
                        'action': t.action,
                        'timestamp': t.timestamp.isoformat(),
                        'old_score': t.old_score,
                        'new_score': t.new_score,
                        'reason': t.reason
                    }
                    for t in self.trade_history[-100:]  # 只保留最近100条
                ],
                'holdings_dates': {
                    code: date.isoformat() 
                    for code, date in self.holdings_entry_dates.items()
                },
                'last_rotation_date': self.last_rotation_date.isoformat() if self.last_rotation_date else None
            }
            
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save trade history: {e}")