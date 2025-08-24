"""
核心逻辑单元测试
测试动量评分、CHOP判定、年线解锁等关键功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 假设这些是实际的导入路径
from backend.core.decision_engine import DecisionEngine
from backend.core.risk_manager import RiskManager
from backend.core.portfolio_manager import PortfolioManager


class TestMomentumScore:
    """动量评分测试"""
    
    @pytest.fixture
    def engine(self):
        return DecisionEngine()
    
    def test_momentum_score_formula_consistency(self, engine):
        """测试动量评分公式的一致性"""
        # 测试标准情况
        r60, r120 = 10.0, 20.0
        expected = 0.6 * r60 + 0.4 * r120  # 6 + 8 = 14
        actual = engine.calculate_momentum_score(r60, r120)
        assert actual == pytest.approx(expected, rel=1e-5)
        
    def test_momentum_score_negative_returns(self, engine):
        """测试负收益情况下的动量评分"""
        r60, r120 = -5.0, -10.0
        expected = 0.6 * (-5) + 0.4 * (-10)  # -3 + -4 = -7
        actual = engine.calculate_momentum_score(r60, r120)
        assert actual == pytest.approx(expected, rel=1e-5)
        
    def test_momentum_score_mixed_returns(self, engine):
        """测试正负混合收益的动量评分"""
        r60, r120 = 15.0, -8.0
        expected = 0.6 * 15 + 0.4 * (-8)  # 9 + -3.2 = 5.8
        actual = engine.calculate_momentum_score(r60, r120)
        assert actual == pytest.approx(expected, rel=1e-5)


class TestCHOPLogic:
    """CHOP震荡层判定测试"""
    
    @pytest.fixture
    def market_data(self):
        """创建模拟市场数据"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'close': np.random.randn(100).cumsum() + 3000,
            'ma200': np.full(100, 3000)
        })
    
    def test_chop_three_choose_two_logic(self):
        """测试CHOP的3选2逻辑"""
        from backend.core.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        # 模拟满足2个条件的情况
        mock_data = {
            'band_days': 11,  # 满足条件1: ≥10天在带内
            'atr_ratio': 0.04,  # 满足条件2: ≥3.5%
            'ma_slope': 0.003,  # 满足条件2: ≤±0.5%
            'dispersion_t1_t3': 0.05,  # 不满足条件3: >3%
            'dispersion_t1_t5': 0.10   # 不满足条件3: >8%
        }
        
        with patch.object(analyzer, '_calculate_metrics', return_value=mock_data):
            status = analyzer.assess_chop_status(None, None, None, None)
            
            assert status.is_chop == True
            assert status.conditions_met == 2
            assert len(status.reasons) == 2
    
    def test_chop_all_conditions_met(self):
        """测试所有CHOP条件都满足的情况"""
        from backend.core.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        mock_data = {
            'band_days': 15,  # 满足条件1
            'atr_ratio': 0.04,  # 满足条件2
            'ma_slope': 0.002,  # 满足条件2
            'dispersion_t1_t3': 0.02,  # 满足条件3
            'dispersion_t1_t5': 0.05   # 满足条件3
        }
        
        with patch.object(analyzer, '_calculate_metrics', return_value=mock_data):
            status = analyzer.assess_chop_status(None, None, None, None)
            
            assert status.is_chop == True
            assert status.conditions_met == 3


class TestYearlineUnlock:
    """年线解锁逻辑测试"""
    
    @pytest.fixture
    def monitor(self):
        from backend.core.yearline_monitor import YearlineMonitor
        return YearlineMonitor()
    
    def test_consecutive_days_requirement(self, monitor):
        """测试连续5日站上年线的要求"""
        ma200 = 3000
        
        # 前4天站上年线
        for i in range(4):
            price = ma200 * 1.005  # 站上0.5%
            assert monitor.check_yearline_unlock(price, ma200) == False
            
        # 第5天站上年线且涨幅≥1%
        price = ma200 * 1.011
        assert monitor.check_yearline_unlock(price, ma200) == True
        assert monitor.unlock_status == True
    
    def test_yearline_break_resets_count(self, monitor):
        """测试跌破年线重置计数"""
        ma200 = 3000
        
        # 前3天站上年线
        for i in range(3):
            monitor.check_yearline_unlock(ma200 * 1.005, ma200)
        assert monitor.above_yearline_count == 3
        
        # 第4天跌破年线
        monitor.check_yearline_unlock(ma200 * 0.995, ma200)
        assert monitor.above_yearline_count == 0
        assert monitor.unlock_status == False
    
    def test_yearline_fallback_within_3days(self, monitor):
        """测试解锁后3日内回落检测"""
        ma200 = 3000
        
        # 先完成解锁
        for i in range(5):
            monitor.check_yearline_unlock(ma200 * 1.011, ma200)
        assert monitor.unlock_status == True
        
        # 模拟第2天跌破-1%
        monitor.unlock_date = datetime.now() - timedelta(days=2)
        fallback = monitor.check_yearline_fallback(ma200 * 0.985, ma200)
        
        assert fallback == True
        assert monitor.unlock_status == False


class TestDataSourceFailover:
    """数据源容错测试"""
    
    @pytest.fixture
    def fetcher(self):
        from backend.core.data_fetcher_enhanced import EnhancedDataFetcher
        return EnhancedDataFetcher()
    
    @pytest.mark.asyncio
    async def test_primary_source_failure_triggers_backup(self, fetcher):
        """测试主数据源失败时启用备用源"""
        symbol = '510300'
        
        # 模拟主数据源失败
        fetcher.primary_source.fetch = Mock(side_effect=Exception("Network error"))
        
        # 模拟第一个备用源也失败
        fetcher.backup_sources[0].fetch = Mock(side_effect=Exception("Timeout"))
        
        # 模拟第二个备用源成功
        expected_data = pd.DataFrame({'close': [100, 101, 102]})
        fetcher.backup_sources[1].fetch = Mock(return_value=expected_data)
        
        # 执行获取
        result = await fetcher.fetch_with_fallback(symbol, 'daily')
        
        # 验证结果
        assert result.equals(expected_data)
        assert fetcher.primary_source.fetch.called
        assert fetcher.backup_sources[0].fetch.called
        assert fetcher.backup_sources[1].fetch.called
    
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_api_call(self, fetcher):
        """测试缓存命中避免API调用"""
        symbol = '510300'
        cached_data = pd.DataFrame({'close': [100, 101, 102]})
        
        # 设置缓存
        await fetcher.cache.set(f"{symbol}:daily", cached_data)
        
        # Mock API调用
        fetcher.primary_source.fetch = Mock()
        
        # 执行获取
        result = await fetcher.fetch_with_fallback(symbol, 'daily')
        
        # 验证没有调用API
        assert fetcher.primary_source.fetch.called == False
        assert result.equals(cached_data)


class TestRiskManagement:
    """风险管理测试"""
    
    @pytest.fixture
    def risk_manager(self):
        return RiskManager()
    
    def test_stop_loss_levels(self, risk_manager):
        """测试不同市场环境下的止损水平"""
        # 默认止损：-12%
        assert risk_manager.get_stop_loss('balanced') == -0.12
        
        # 强趋势止损：-10%
        assert risk_manager.get_stop_loss('aggressive') == -0.10
        
        # 震荡市止损：-15%
        assert risk_manager.get_stop_loss('conservative') == -0.15
    
    def test_correlation_threshold(self, risk_manager):
        """测试相关性阈值检查"""
        # 相关性≤0.8合格
        assert risk_manager.check_correlation(0.75) == True
        assert risk_manager.check_correlation(0.80) == True
        assert risk_manager.check_correlation(0.81) == False
    
    def test_min_holding_period_enforcement(self, risk_manager):
        """测试最短持有期强制执行"""
        entry_date = datetime.now() - timedelta(days=10)
        
        # 默认最短持有期14天
        can_exit = risk_manager.check_min_holding_period(
            entry_date, 
            min_days=14
        )
        assert can_exit == False
        
        # 已持有15天
        entry_date = datetime.now() - timedelta(days=15)
        can_exit = risk_manager.check_min_holding_period(
            entry_date,
            min_days=14
        )
        assert can_exit == True


class TestIntegration:
    """集成测试"""
    
    def test_full_decision_flow(self):
        """测试完整的决策流程"""
        engine = DecisionEngine()
        risk_manager = RiskManager()
        portfolio_manager = PortfolioManager()
        
        # 1. 生成交易信号
        market_data = self._create_test_market_data()
        signals = engine.generate_signals(market_data)
        
        # 2. 风险检查
        approved_signals = risk_manager.check_signals(signals)
        
        # 3. 生成订单
        orders = portfolio_manager.create_orders(approved_signals)
        
        # 验证流程
        assert len(signals) > 0
        assert len(approved_signals) <= len(signals)
        assert all(order.iopv_band is not None for order in orders)
    
    def _create_test_market_data(self):
        """创建测试用市场数据"""
        return {
            'hs300': {'close': 3100, 'ma200': 3000},
            'etfs': [
                {'code': '510300', 'r60': 10, 'r120': 15},
                {'code': '510880', 'r60': 8, 'r120': 12},
                {'code': '588000', 'r60': 20, 'r120': 25},
            ]
        }


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=backend', '--cov-report=html'])