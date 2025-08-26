"""风险监控模块"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskAlert:
    """风险警报"""
    level: RiskLevel
    category: str  # 'market', 'position', 'data', 'system'
    code: Optional[str]
    message: str
    metrics: Dict
    suggested_action: str
    timestamp: datetime


class RiskMonitor:
    """风险监控器"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # 风险阈值
        self.thresholds = {
            'portfolio_drawdown': -0.10,  # 组合回撤
            'position_stop_loss': config.get('satellite_rules', {}).get('stop_loss', -0.12),
            'correlation_max': config.get('satellite_rules', {}).get('corr_max', 0.8),
            'iopv_premium_domestic': config.get('satellite_rules', {}).get('iopv_premium_max_domestic', 0.005),
            'iopv_premium_qdii': config.get('satellite_rules', {}).get('iopv_premium_max_qdii', 0.02),
            'concentration_max': 0.30,  # 单一持仓最大占比
            'turnover_rate_max': 2.0,   # 年化换手率
            'data_quality_min': 0.95,   # 数据质量最低要求
        }
        
        # 模式切换阈值
        self.mode_thresholds = {
            'chop_high': 61,  # CHOP震荡阈值
            'chop_low': 38,   # CHOP趋势阈值
            'ma200_buffer': 0.01,  # 年线缓冲带
        }
        
        self.alerts: List[RiskAlert] = []
        self.risk_metrics: Dict = {}
        
    def check_all_risks(self, market_data: Dict, portfolio: Dict, 
                       data_quality: Dict) -> List[RiskAlert]:
        """全面风险检查"""
        self.alerts = []
        
        # 1. 市场风险
        self._check_market_risk(market_data)
        
        # 2. 持仓风险
        self._check_position_risk(portfolio, market_data)
        
        # 3. 相关性风险
        self._check_correlation_risk(portfolio)
        
        # 4. 流动性风险
        self._check_liquidity_risk(portfolio, market_data)
        
        # 5. 数据质量风险
        self._check_data_quality(data_quality)
        
        # 6. 系统性风险
        self._check_system_risk(portfolio, market_data)
        
        return self.alerts
    
    def _check_market_risk(self, market_data: Dict):
        """检查市场风险"""
        hs300_data = market_data.get('hs300', {})
        
        # 年线状态
        ma200_ratio = hs300_data.get('ma200_ratio', 1.0)
        if ma200_ratio < 1.0:
            self.alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category='market',
                code='HS300',
                message=f"沪深300跌破年线，当前比率: {ma200_ratio:.3f}",
                metrics={'ma200_ratio': ma200_ratio},
                suggested_action="减少卫星仓位，保持防御性配置",
                timestamp=datetime.now()
            ))
        
        # CHOP震荡指数
        chop = hs300_data.get('chop', 50)
        if chop >= self.mode_thresholds['chop_high']:
            self.alerts.append(RiskAlert(
                level=RiskLevel.LOW,
                category='market',
                code='CHOP',
                message=f"市场进入震荡模式，CHOP={chop:.1f}",
                metrics={'chop': chop},
                suggested_action="降低持仓频率，扩大止损空间至-15%",
                timestamp=datetime.now()
            ))
        
        # ATR波动率
        atr_pct = hs300_data.get('atr_pct', 0.02)
        if atr_pct > 0.03:
            self.alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category='market',
                code='ATR',
                message=f"市场波动加大，ATR={atr_pct*100:.1f}%",
                metrics={'atr_pct': atr_pct},
                suggested_action="减少仓位或增加对冲",
                timestamp=datetime.now()
            ))
    
    def _check_position_risk(self, portfolio: Dict, market_data: Dict):
        """检查持仓风险"""
        positions = portfolio.get('positions', [])
        total_value = portfolio.get('total_value', 0)
        
        for position in positions:
            code = position['code']
            weight = position['weight']
            pnl_pct = position.get('pnl_pct', 0)
            
            # 止损检查
            stop_loss = self.thresholds['position_stop_loss']
            if position.get('category') == 'satellite':
                # 根据市场模式调整止损
                if market_data.get('mode') == 'CHOP':
                    stop_loss = -0.15
                elif market_data.get('mode') == 'TREND':
                    stop_loss = -0.10
            
            if pnl_pct <= stop_loss:
                self.alerts.append(RiskAlert(
                    level=RiskLevel.HIGH,
                    category='position',
                    code=code,
                    message=f"{position['name']} 触及止损线 {pnl_pct*100:.1f}%",
                    metrics={'pnl_pct': pnl_pct, 'stop_loss': stop_loss},
                    suggested_action="立即平仓止损",
                    timestamp=datetime.now()
                ))
            elif pnl_pct <= stop_loss * 0.8:  # 接近止损
                self.alerts.append(RiskAlert(
                    level=RiskLevel.MEDIUM,
                    category='position',
                    code=code,
                    message=f"{position['name']} 接近止损线 {pnl_pct*100:.1f}%",
                    metrics={'pnl_pct': pnl_pct, 'stop_loss': stop_loss},
                    suggested_action="密切关注，准备止损",
                    timestamp=datetime.now()
                ))
            
            # 集中度检查
            if weight > self.thresholds['concentration_max']:
                self.alerts.append(RiskAlert(
                    level=RiskLevel.MEDIUM,
                    category='position',
                    code=code,
                    message=f"{position['name']} 仓位过重 {weight*100:.1f}%",
                    metrics={'weight': weight, 'max': self.thresholds['concentration_max']},
                    suggested_action="减仓至30%以下",
                    timestamp=datetime.now()
                ))
            
            # QDII溢价检查
            if code.startswith('513'):  # QDII基金
                premium = position.get('iopv_premium', 0)
                if premium > self.thresholds['iopv_premium_qdii']:
                    self.alerts.append(RiskAlert(
                        level=RiskLevel.MEDIUM,
                        category='position',
                        code=code,
                        message=f"QDII {position['name']} 溢价过高 {premium*100:.1f}%",
                        metrics={'premium': premium},
                        suggested_action="暂停买入，考虑减仓",
                        timestamp=datetime.now()
                    ))
    
    def _check_correlation_risk(self, portfolio: Dict):
        """检查相关性风险"""
        satellite_positions = [p for p in portfolio.get('positions', []) 
                             if p.get('category') == 'satellite']
        
        if len(satellite_positions) >= 2:
            corr = portfolio.get('satellite_correlation', 0)
            if corr > self.thresholds['correlation_max']:
                self.alerts.append(RiskAlert(
                    level=RiskLevel.HIGH,
                    category='position',
                    code=None,
                    message=f"卫星两条腿相关性过高 ρ={corr:.2f}",
                    metrics={'correlation': corr},
                    suggested_action="更换其中一条腿，降低相关性",
                    timestamp=datetime.now()
                ))
    
    def _check_liquidity_risk(self, portfolio: Dict, market_data: Dict):
        """检查流动性风险"""
        for position in portfolio.get('positions', []):
            turnover = position.get('avg_turnover', 0)
            min_turnover = self.config.get('satellite_rules', {}).get('min_turnover', 5e7)
            
            if turnover < min_turnover:
                self.alerts.append(RiskAlert(
                    level=RiskLevel.MEDIUM,
                    category='position',
                    code=position['code'],
                    message=f"{position['name']} 流动性不足，日均成交{turnover/1e8:.1f}亿",
                    metrics={'turnover': turnover, 'min_required': min_turnover},
                    suggested_action="减少该标的配置或更换",
                    timestamp=datetime.now()
                ))
    
    def _check_data_quality(self, data_quality: Dict):
        """检查数据质量"""
        overall_quality = data_quality.get('overall', 1.0)
        
        if overall_quality < self.thresholds['data_quality_min']:
            self.alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                category='data',
                code=None,
                message=f"数据质量低于阈值: {overall_quality*100:.1f}%",
                metrics={'quality': overall_quality},
                suggested_action="检查数据源，暂停自动交易",
                timestamp=datetime.now()
            ))
        
        # 检查具体数据问题
        issues = data_quality.get('issues', [])
        for issue in issues:
            if issue['severity'] == 'critical':
                level = RiskLevel.CRITICAL
            elif issue['severity'] == 'high':
                level = RiskLevel.HIGH
            else:
                level = RiskLevel.MEDIUM
            
            self.alerts.append(RiskAlert(
                level=level,
                category='data',
                code=issue.get('code'),
                message=issue['message'],
                metrics=issue.get('metrics', {}),
                suggested_action=issue.get('action', '检查数据源'),
                timestamp=datetime.now()
            ))
    
    def _check_system_risk(self, portfolio: Dict, market_data: Dict):
        """检查系统性风险"""
        # 组合回撤
        drawdown = portfolio.get('drawdown', 0)
        if drawdown <= self.thresholds['portfolio_drawdown']:
            self.alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                category='system',
                code=None,
                message=f"组合回撤达到{drawdown*100:.1f}%",
                metrics={'drawdown': drawdown},
                suggested_action="进入防御模式，暂停加仓",
                timestamp=datetime.now()
            ))
        
        # 换手率
        turnover_rate = portfolio.get('annual_turnover_rate', 0)
        if turnover_rate > self.thresholds['turnover_rate_max']:
            self.alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category='system',
                code=None,
                message=f"年化换手率过高: {turnover_rate:.1f}",
                metrics={'turnover_rate': turnover_rate},
                suggested_action="延长最短持有期，提高换仓阈值",
                timestamp=datetime.now()
            ))
        
        # 连续亏损
        consecutive_losses = portfolio.get('consecutive_loss_days', 0)
        if consecutive_losses >= 5:
            self.alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                category='system',
                code=None,
                message=f"连续{consecutive_losses}天亏损",
                metrics={'loss_days': consecutive_losses},
                suggested_action="检查策略有效性，考虑暂停",
                timestamp=datetime.now()
            ))
    
    def should_stop_trading(self) -> bool:
        """判断是否应该停止交易"""
        critical_alerts = [a for a in self.alerts if a.level == RiskLevel.CRITICAL]
        high_alerts = [a for a in self.alerts if a.level == RiskLevel.HIGH]
        
        # 有严重警报或3个以上高风险警报时停止
        return len(critical_alerts) > 0 or len(high_alerts) >= 3
    
    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        alert_counts = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.MEDIUM: 0,
            RiskLevel.LOW: 0
        }
        
        for alert in self.alerts:
            alert_counts[alert.level] += 1
        
        return {
            'total_alerts': len(self.alerts),
            'critical': alert_counts[RiskLevel.CRITICAL],
            'high': alert_counts[RiskLevel.HIGH],
            'medium': alert_counts[RiskLevel.MEDIUM],
            'low': alert_counts[RiskLevel.LOW],
            'should_stop': self.should_stop_trading(),
            'alerts': [
                {
                    'level': alert.level.value,
                    'category': alert.category,
                    'message': alert.message,
                    'action': alert.suggested_action,
                    'time': alert.timestamp.isoformat()
                }
                for alert in self.alerts
            ]
        }
    
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算VaR (Value at Risk)"""
        if len(returns) < 20:
            return 0
        
        # 历史模拟法
        var = np.percentile(returns, (1 - confidence) * 100)
        return var
    
    def calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算CVaR (Conditional Value at Risk)"""
        var = self.calculate_var(returns, confidence)
        cvar = returns[returns <= var].mean()
        return cvar if not np.isnan(cvar) else var