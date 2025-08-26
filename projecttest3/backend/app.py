"""
Momentum Lens - Streamlit Application
动量透镜 - Streamlit 应用程序
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import yaml
import os
import sys
from pathlib import Path

# 设置Python路径
backend_root = Path(__file__).parent
project_root = backend_root.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入自定义模块
try:
    from adapters import AdapterManager
    from indicators import (
        MarketEnvironment,
        MomentumCalculator,
        CorrelationAnalyzer,
        ConvertibleScorer,
        TechnicalIndicators
    )
    from engine import StateMachine, MarketState
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from backend.adapters import AdapterManager
    from backend.indicators import (
        MarketEnvironment,
        MomentumCalculator,
        CorrelationAnalyzer,
        ConvertibleScorer,
        TechnicalIndicators
    )
    from backend.engine import StateMachine, MarketState

# 页面配置
st.set_page_config(
    page_title="Momentum Lens - A股ETF动量系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载配置
@st.cache_resource
def load_config():
    """加载系统配置"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

# 初始化组件
@st.cache_resource
def init_components():
    """初始化系统组件"""
    adapter_manager = AdapterManager()
    market_env = MarketEnvironment()
    momentum_calc = MomentumCalculator()
    correlation_analyzer = CorrelationAnalyzer()
    convertible_scorer = ConvertibleScorer()
    state_machine = StateMachine()
    tech_indicators = TechnicalIndicators()
    
    return {
        'adapter': adapter_manager,
        'market_env': market_env,
        'momentum': momentum_calc,
        'correlation': correlation_analyzer,
        'convertible': convertible_scorer,
        'state_machine': state_machine,
        'technical': tech_indicators
    }

def create_market_status_light(state: str) -> str:
    """创建市场状态灯"""
    colors = {
        'OFFENSE': '🟢',
        'NEUTRAL': '🟡', 
        'DEFENSE': '🔴'
    }
    return colors.get(state, '⚪')

def fetch_etf_data(adapter, etf_list, days=250):
    """获取ETF数据"""
    data = {}
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    progress_bar = st.progress(0)
    for i, etf in enumerate(etf_list):
        progress_bar.progress((i + 1) / len(etf_list))
        df = adapter.get_etf_price(etf['code'], start_date, end_date)
        if not df.empty:
            data[etf['code']] = df
    progress_bar.empty()
    
    return data

def main():
    """主应用程序"""
    
    # 加载配置和组件
    config = load_config()
    components = init_components()
    
    # 侧边栏
    with st.sidebar:
        st.title("📊 Momentum Lens")
        st.markdown("---")
        
        # 数据源选择
        st.subheader("数据源")
        data_source = st.selectbox(
            "选择数据源",
            options=components['adapter'].get_available_adapters(),
            index=0
        )
        
        # 预设模式选择
        st.subheader("策略模式")
        preset = st.selectbox(
            "选择预设",
            options=['进攻型', '均衡型', '保守型'],
            index=1
        )
        
        # 刷新按钮
        if st.button("🔄 刷新数据", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        
        # 参数设置
        with st.expander("⚙️ 高级设置"):
            momentum_window_short = st.slider("短期动量窗口", 20, 100, 63)
            momentum_window_long = st.slider("长期动量窗口", 100, 252, 126)
            correlation_window = st.slider("相关性窗口", 30, 120, 90)
    
    # 主界面
    st.title("🎯 Momentum Lens - A股ETF动量决策系统")
    
    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    # 获取市场数据
    market_index_data = components['adapter'].get_index_price("000300", 
                                                             date.today() - timedelta(days=300),
                                                             date.today())
    
    if not market_index_data.empty:
        # 分析市场环境
        market_analysis = components['market_env'].analyze_market_state(market_index_data)
        
        # 更新状态机
        new_state, changed = components['state_machine'].update_state(market_analysis)
        
        # 显示市场状态
        with col1:
            st.metric(
                "市场环境",
                f"{create_market_status_light(market_analysis['market_environment'])} {market_analysis['market_environment']}",
                f"MA200: {market_analysis['ma200_distance']:.2f}%"
            )
            
        with col2:
            st.metric(
                "CHOP指标",
                f"{market_analysis['chop']:.1f}",
                "震荡" if market_analysis['chop'] > 60 else "趋势"
            )
            
        with col3:
            trend = market_analysis['trend_strength']
            trend_emoji = "📈" if 'up' in trend else "📉" if 'down' in trend else "➡️"
            st.metric(
                "趋势强度",
                f"{trend_emoji} {trend}",
                f"ATR: {market_analysis['atr_ratio']:.2f}%"
            )
            
        with col4:
            state_config = components['state_machine'].get_state_config()
            st.metric(
                "建议配置",
                f"Core: {state_config['core_ratio']*100:.0f}%",
                f"Satellite: {state_config['satellite_ratio']*100:.0f}%"
            )
    
    st.markdown("---")
    
    # 主要内容区域 - 使用标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 动量排名", "🎯 推荐组合", "🔄 可转债网格", "📈 回测分析", "📋 导出清单"
    ])
    
    # Tab 1: 动量排名
    with tab1:
        st.subheader("ETF动量排名 Top 10")
        
        # 获取ETF候选池
        etf_universe = []
        for category in ['growth', 'energy', 'others']:
            if category in config.get('etf_universe', {}):
                etf_universe.extend(config['etf_universe'][category])
        
        if st.button("计算动量排名"):
            with st.spinner("正在获取数据..."):
                # 获取ETF数据
                etf_data = fetch_etf_data(components['adapter'], etf_universe[:10])
                
                if etf_data:
                    # 计算动量排名
                    momentum_ranking = components['momentum'].rank_by_momentum(etf_data)
                    
                    if not momentum_ranking.empty:
                        # 显示排名表格
                        display_df = momentum_ranking[['rank', 'code', 'r63', 'r126', 'momentum_score']].head(10)
                        display_df.columns = ['排名', '代码', '3月动量', '6月动量', '综合得分']
                        
                        # 格式化百分比
                        for col in ['3月动量', '6月动量']:
                            display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%")
                        display_df['综合得分'] = display_df['综合得分'].apply(lambda x: f"{x*100:.2f}")
                        
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 动量图表
                        fig = go.Figure()
                        
                        top5 = momentum_ranking.head(5)
                        fig.add_trace(go.Bar(
                            name='3月动量',
                            x=top5['code'],
                            y=top5['r63'] * 100,
                            marker_color='lightblue'
                        ))
                        
                        fig.add_trace(go.Bar(
                            name='6月动量',
                            x=top5['code'],
                            y=top5['r126'] * 100,
                            marker_color='darkblue'
                        ))
                        
                        fig.update_layout(
                            title="Top 5 ETF 动量对比",
                            xaxis_title="ETF代码",
                            yaxis_title="动量 (%)",
                            barmode='group',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: 推荐组合
    with tab2:
        st.subheader("智能推荐组合")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**推荐两条腿配置**")
            
            # 基于状态机配置生成推荐
            state_config = components['state_machine'].get_state_config()
            
            if market_analysis['market_environment'] == 'OFFENSE':
                leg1 = "512760 (国防军工)"
                leg2 = "516160 (新能源)"
                reason = "市场强势，选择高弹性成长板块"
            elif market_analysis['market_environment'] == 'DEFENSE':
                leg1 = "510880 (红利ETF)"
                leg2 = "512800 (银行ETF)"
                reason = "市场弱势，选择防守型资产"
            else:
                leg1 = "510300 (沪深300)"
                leg2 = "512760 (国防军工)"
                reason = "市场中性，均衡配置"
            
            st.success(f"""
            **腿1**: {leg1}  
            **腿2**: {leg2}  
            **配置理由**: {reason}
            """)
            
        with col2:
            st.info("**Core资产配置**")
            
            core_assets = [
                {"资产": "沪深300", "代码": "510300", "权重": "40%"},
                {"资产": "红利ETF", "代码": "510880", "权重": "30%"},
                {"资产": "黄金ETF", "代码": "518880", "权重": "20%"},
                {"资产": "货币基金", "代码": "511990", "权重": "10%"}
            ]
            
            df_core = pd.DataFrame(core_assets)
            st.dataframe(df_core, use_container_width=True, hide_index=True)
    
    # Tab 3: 可转债网格
    with tab3:
        st.subheader("可转债网格交易")
        
        # 模拟可转债数据
        cb_data = [
            {"code": "123001", "name": "蓝标转债", "price": 102.5, "premium_rate": 5.2, 
             "volatility": 25, "ytm": 2.8, "daily_volume": 5000, "credit_rating": "AA"},
            {"code": "123002", "name": "海兰转债", "price": 98.3, "premium_rate": -2.1,
             "volatility": 30, "ytm": 4.2, "daily_volume": 8000, "credit_rating": "AA+"},
            {"code": "123003", "name": "光电转债", "price": 105.8, "premium_rate": 12.5,
             "volatility": 35, "ytm": 1.5, "daily_volume": 3000, "credit_rating": "A+"}
        ]
        
        # 计算评分
        cb_scores = components['convertible'].rank_convertible_bonds(cb_data)
        
        if not cb_scores.empty:
            # 显示评分表格
            display_cols = ['rank', 'code', 'name', 'total_score', 'rating', 'recommendation']
            display_df = cb_scores[display_cols]
            display_df.columns = ['排名', '代码', '名称', '总分', '评级', '建议']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # 网格参数计算
            st.subheader("网格参数设置")
            
            selected_cb = st.selectbox("选择可转债", cb_scores['code'].tolist())
            
            if selected_cb:
                cb_info = next((cb for cb in cb_data if cb['code'] == selected_cb), None)
                if cb_info:
                    # 计算网格步长
                    grid_step = components['convertible'].calculate_grid_step(
                        {"atr10": 2.5, "close": cb_info['price']}
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("建议网格步长", f"{grid_step*100:.2f}%")
                    with col2:
                        st.metric("建议网格数量", "5-8格")
                    with col3:
                        st.metric("单格资金", "10000元")
    
    # Tab 4: 回测分析
    with tab4:
        st.subheader("策略回测分析")
        
        # 生成模拟回测数据
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
        returns = np.random.randn(len(dates)) * 0.02
        cumulative_returns = (1 + returns).cumprod()
        
        # 创建回测图表
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode='lines',
            name='策略收益',
            line=dict(color='blue', width=2)
        ))
        
        # 添加基准线
        benchmark = np.ones(len(dates)) * 1.08  # 8%年化
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark,
            mode='lines',
            name='基准收益',
            line=dict(color='gray', width=1, dash='dash')
        ))
        
        fig.update_layout(
            title="策略回测曲线",
            xaxis_title="日期",
            yaxis_title="累计收益",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 回测指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("年化收益", "12.5%", "4.5%")
        with col2:
            st.metric("夏普比率", "1.35", "0.25")
        with col3:
            st.metric("最大回撤", "-8.2%", "-2.1%")
        with col4:
            st.metric("胜率", "58%", "3%")
    
    # Tab 5: 导出清单
    with tab5:
        st.subheader("周二下单清单")
        
        # 生成订单数据
        orders = [
            {"类型": "买入", "代码": "512760", "名称": "国防军工", "数量": 1000, "价格": "市价"},
            {"类型": "卖出", "代码": "512800", "名称": "银行ETF", "数量": 500, "价格": "限价1.05"},
            {"类型": "买入", "代码": "123001", "名称": "蓝标转债", "数量": 10, "价格": "102.00"}
        ]
        
        df_orders = pd.DataFrame(orders)
        
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 导出CSV", use_container_width=True):
                csv = df_orders.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载CSV文件",
                    data=csv,
                    file_name=f"orders_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
        with col2:
            if st.button("📄 生成PDF", use_container_width=True):
                st.info("PDF生成功能开发中...")
                
        with col3:
            if st.button("📧 发送邮件", use_container_width=True):
                st.info("邮件发送功能开发中...")
    
    # 底部信息
    st.markdown("---")
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源: {data_source}")

if __name__ == "__main__":
    main()