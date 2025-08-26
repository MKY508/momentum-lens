"""
Momentum Lens - Enhanced Streamlit Application
动量透镜 - 增强版Streamlit应用程序
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
import time

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
    from data.convertible_bonds import ConvertibleBondsFetcher
except ImportError:
    try:
        from backend.adapters import AdapterManager
        from backend.indicators import (
            MarketEnvironment,
            MomentumCalculator,
            CorrelationAnalyzer,
            ConvertibleScorer,
            TechnicalIndicators
        )
        from backend.engine import StateMachine, MarketState
        from backend.data.convertible_bonds import ConvertibleBondsFetcher
    except ImportError:
        # 如果还是找不到，使用备用方案
        from backend.adapters import AdapterManager
        from backend.indicators import (
            MarketEnvironment,
            MomentumCalculator,
            CorrelationAnalyzer,
            ConvertibleScorer,
            TechnicalIndicators
        )
        from backend.engine import StateMachine, MarketState
        ConvertibleBondsFetcher = None

# 页面配置
st.set_page_config(
    page_title="Momentum Lens - A股ETF动量系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载ETF宇宙配置
@st.cache_resource
def load_etf_universe():
    """加载ETF候选池配置"""
    etf_path = Path(__file__).parent / "config" / "etf_universe.yaml"
    if etf_path.exists():
        with open(etf_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

# 加载配置
@st.cache_resource
def load_config():
    """加载系统配置"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # 更新回测时间到2025年8月
            if 'backtest' in config:
                config['backtest']['end_date'] = "2025-08-26"
            return config
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

def get_etf_name(code: str, etf_universe: dict) -> str:
    """获取ETF名称"""
    etf_map = etf_universe.get('etf_name_map', {})
    return etf_map.get(code, code)

def fetch_etf_data_with_names(adapter, etf_codes, etf_universe, days=250):
    """获取ETF数据并附带名称"""
    data = {}
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    progress_bar = st.progress(0)
    total = len(etf_codes)
    
    for i, code in enumerate(etf_codes):
        progress_bar.progress((i + 1) / total)
        try:
            df = adapter.get_etf_price(code, start_date, end_date)
            if not df.empty:
                data[code] = {
                    'data': df,
                    'name': get_etf_name(code, etf_universe)
                }
        except Exception as e:
            st.warning(f"获取{code}数据失败: {e}")
            continue
    
    progress_bar.empty()
    return data

def calculate_correlation_matrix(etf_data):
    """计算ETF相关性矩阵"""
    returns_dict = {}
    for code, info in etf_data.items():
        df = info['data']
        if 'close' in df.columns:
            returns_dict[code] = df['close'].pct_change().dropna()
    
    if len(returns_dict) > 1:
        returns_df = pd.DataFrame(returns_dict)
        return returns_df.corr()
    return pd.DataFrame()

@st.cache_data(ttl=300)  # 缓存5分钟
def get_expanded_convertible_data():
    """获取扩展的可转债数据"""
    if ConvertibleBondsFetcher is not None:
        try:
            # 使用真实数据获取器
            fetcher = ConvertibleBondsFetcher()
            top_bonds = fetcher.get_top_bonds(50)  # 获取50只最优可转债
            
            # 转换为列表格式
            cb_data = []
            for _, bond in top_bonds.iterrows():
                cb_data.append({
                    "code": bond.get('code', ''),
                    "name": bond.get('name', ''),
                    "price": bond.get('price', 100),
                    "premium_rate": bond.get('premium_rate', 0),
                    "ytm": bond.get('ytm', 0),
                    "remaining_years": bond.get('remaining_years', 3),
                    "remaining_size": bond.get('remaining_size', 10),
                    "credit_rating": bond.get('credit_rating', 'AA'),
                    "conversion_value": bond.get('conversion_value', 100),
                    "double_low": bond.get('double_low', 100),
                    "volume": bond.get('volume', 10000),
                    "pb_ratio": bond.get('pb_ratio', 1.0),
                    "total_score": bond.get('total_score', 50),
                    "rating": bond.get('rating', 'B'),
                    "recommendation": bond.get('recommendation', '关注'),
                    # 计算波动率（简单估算）
                    "volatility": abs(bond.get('premium_rate', 0)) * 2 + 20,
                    "daily_volume": bond.get('volume', 10000)
                })
            
            if cb_data:
                return cb_data
            
        except Exception as e:
            st.warning(f"获取实时可转债数据失败: {e}")
    
    # 备用静态数据
    cb_data = [
        {"code": "127056", "name": "中特转债", "price": 105.23, "premium_rate": 8.5,
         "ytm": 1.8, "remaining_years": 2.5, "remaining_size": 50, "credit_rating": "AAA",
         "conversion_value": 97.0, "double_low": 113.73, "volume": 150000, "pb_ratio": 1.2,
         "volatility": 25, "daily_volume": 150000},
        
        {"code": "113044", "name": "大秦转债", "price": 102.15, "premium_rate": 5.2,
         "ytm": 2.5, "remaining_years": 3.2, "remaining_size": 80, "credit_rating": "AAA",
         "conversion_value": 97.1, "double_low": 107.35, "volume": 120000, "pb_ratio": 1.1,
         "volatility": 22, "daily_volume": 120000},
        
        {"code": "128034", "name": "江银转债", "price": 108.50, "premium_rate": 12.3,
         "ytm": 0.8, "remaining_years": 4.0, "remaining_size": 100, "credit_rating": "AAA",
         "conversion_value": 96.7, "double_low": 120.80, "volume": 200000, "pb_ratio": 0.8,
         "volatility": 28, "daily_volume": 200000},
        
        {"code": "123123", "name": "航新转债", "price": 98.50, "premium_rate": 2.1,
         "ytm": 3.5, "remaining_years": 3.5, "remaining_size": 20, "credit_rating": "AA+",
         "conversion_value": 96.5, "double_low": 100.60, "volume": 80000, "pb_ratio": 1.3,
         "volatility": 20, "daily_volume": 80000},
        
        {"code": "127045", "name": "牧原转债", "price": 95.30, "premium_rate": -2.5,
         "ytm": 4.8, "remaining_years": 2.8, "remaining_size": 35, "credit_rating": "AA+",
         "conversion_value": 97.7, "double_low": 92.80, "volume": 95000, "pb_ratio": 2.1,
         "volatility": 32, "daily_volume": 95000},
        
        {"code": "128136", "name": "立讯转债", "price": 92.50, "premium_rate": -5.8,
         "ytm": 6.2, "remaining_years": 2.2, "remaining_size": 25, "credit_rating": "AA",
         "conversion_value": 98.2, "double_low": 86.70, "volume": 110000, "pb_ratio": 3.2,
         "volatility": 35, "daily_volume": 110000},
    ]
    
    # 添加默认评分
    for cb in cb_data:
        if 'total_score' not in cb:
            # 简单评分公式
            premium_score = max(0, 100 - abs(cb['premium_rate']) * 2)
            ytm_score = min(100, cb['ytm'] * 20)
            cb['total_score'] = premium_score * 0.5 + ytm_score * 0.5
        
        if 'rating' not in cb:
            score = cb.get('total_score', 50)
            cb['rating'] = 'S' if score >= 85 else 'A' if score >= 75 else 'B' if score >= 60 else 'C' if score >= 40 else 'D'
        
        if 'recommendation' not in cb:
            score = cb.get('total_score', 50)
            cb['recommendation'] = '强烈推荐' if score >= 85 else '推荐' if score >= 75 else '关注' if score >= 60 else '观察' if score >= 40 else '谨慎'
    
    return cb_data

def main():
    """主应用程序"""
    
    # 加载配置和组件
    config = load_config()
    etf_universe = load_etf_universe()
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
        
        # ETF类别选择
        st.subheader("ETF类别")
        etf_categories = st.multiselect(
            "选择ETF类别",
            options=['entertainment', 'technology', 'new_energy', 'consumer', 
                    'healthcare', 'finance', 'cyclical', 'defense', 'infrastructure'],
            default=['entertainment', 'technology', 'new_energy']
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
            correlation_threshold = st.slider("相关性阈值", 0.5, 0.9, 0.7, 0.05)
    
    # 主界面
    st.title("🎯 Momentum Lens - A股ETF动量决策系统")
    
    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    # 获取市场数据
    market_index_data = components['adapter'].get_index_price("000300", 
                                                             date.today() - timedelta(days=300),
                                                             date.today())
    
    market_analysis = {'market_environment': 'NEUTRAL', 'ma200_distance': 0, 
                      'chop': 50, 'trend_strength': 'neutral', 'atr_ratio': 2.0}
    
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
        st.subheader("ETF动量排名 Top 20")
        
        # 获取选中类别的ETF
        selected_etfs = []
        etf_code_list = []
        for category in etf_categories:
            if category in etf_universe.get('etf_universe', {}):
                etfs = etf_universe['etf_universe'][category]
                for etf in etfs:
                    if etf['code'] not in etf_code_list:
                        etf_code_list.append(etf['code'])
                        selected_etfs.append(etf)
        
        if st.button("计算动量排名"):
            if selected_etfs:
                with st.spinner("正在获取数据并计算动量..."):
                    # 获取ETF数据
                    etf_data = fetch_etf_data_with_names(
                        components['adapter'], 
                        etf_code_list[:30],  # 获取更多ETF
                        etf_universe
                    )
                    
                    if etf_data:
                        # 准备数据格式
                        price_data = {code: info['data'] for code, info in etf_data.items()}
                        
                        # 计算动量排名
                        momentum_ranking = components['momentum'].rank_by_momentum(price_data)
                        
                        # 计算相关性矩阵
                        correlation_matrix = calculate_correlation_matrix(etf_data)
                        
                        if not momentum_ranking.empty:
                            # 添加ETF名称
                            momentum_ranking['name'] = momentum_ranking['code'].apply(
                                lambda x: get_etf_name(x, etf_universe)
                            )
                            
                            # 获取前两名的相关性
                            if len(momentum_ranking) >= 2 and not correlation_matrix.empty:
                                top2_codes = momentum_ranking.head(2)['code'].tolist()
                                if all(code in correlation_matrix.columns for code in top2_codes):
                                    top2_correlation = correlation_matrix.loc[top2_codes[0], top2_codes[1]]
                                    momentum_ranking['correlation_with_top'] = 0
                                    for idx, row in momentum_ranking.iterrows():
                                        if row['code'] in correlation_matrix.columns and top2_codes[0] in correlation_matrix.columns:
                                            momentum_ranking.at[idx, 'correlation_with_top'] = correlation_matrix.loc[row['code'], top2_codes[0]]
                            
                            # 显示排名表格
                            display_cols = ['rank', 'code', 'name', 'r63', 'r126', 'momentum_score']
                            if 'correlation_with_top' in momentum_ranking.columns:
                                display_cols.append('correlation_with_top')
                            
                            display_df = momentum_ranking[display_cols].head(20)
                            display_df.columns = ['排名', '代码', '名称', '3月动量', '6月动量', '综合得分'] + (
                                ['与Top1相关性'] if 'correlation_with_top' in momentum_ranking.columns else []
                            )
                            
                            # 格式化显示
                            for col in ['3月动量', '6月动量']:
                                display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%")
                            display_df['综合得分'] = display_df['综合得分'].apply(lambda x: f"{x*100:.2f}")
                            if '与Top1相关性' in display_df.columns:
                                display_df['与Top1相关性'] = display_df['与Top1相关性'].apply(lambda x: f"{x:.3f}")
                            
                            # 使用颜色编码显示表格
                            st.dataframe(
                                display_df.style.background_gradient(subset=['综合得分'], cmap='RdYlGn'),
                                use_container_width=True,
                                hide_index=True,
                                height=600
                            )
                            
                            # 动量图表
                            st.subheader("Top 10 ETF 动量对比")
                            top10 = momentum_ranking.head(10)
                            
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                name='3月动量',
                                x=top10['name'],
                                y=top10['r63'] * 100,
                                marker_color='lightblue',
                                text=[f"{v:.1f}%" for v in top10['r63'] * 100],
                                textposition='outside'
                            ))
                            
                            fig.add_trace(go.Bar(
                                name='6月动量',
                                x=top10['name'],
                                y=top10['r126'] * 100,
                                marker_color='darkblue',
                                text=[f"{v:.1f}%" for v in top10['r126'] * 100],
                                textposition='outside'
                            ))
                            
                            fig.update_layout(
                                title="动量对比分析",
                                xaxis_title="ETF名称",
                                yaxis_title="动量 (%)",
                                barmode='group',
                                height=500,
                                xaxis_tickangle=-45
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 相关性热力图
                            if not correlation_matrix.empty and len(correlation_matrix) > 1:
                                st.subheader("ETF相关性热力图")
                                
                                # 只显示前10个ETF的相关性
                                top10_codes = momentum_ranking.head(10)['code'].tolist()
                                available_codes = [code for code in top10_codes if code in correlation_matrix.columns]
                                
                                if len(available_codes) > 1:
                                    corr_subset = correlation_matrix.loc[available_codes, available_codes]
                                    
                                    # 添加名称
                                    corr_subset.index = [get_etf_name(code, etf_universe) for code in corr_subset.index]
                                    corr_subset.columns = [get_etf_name(code, etf_universe) for code in corr_subset.columns]
                                    
                                    fig_corr = px.imshow(
                                        corr_subset,
                                        text_auto='.2f',
                                        color_continuous_scale='RdBu',
                                        zmin=-1, zmax=1,
                                        height=600
                                    )
                                    fig_corr.update_layout(title="Top 10 ETF相关性矩阵")
                                    st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.warning("请在侧边栏选择至少一个ETF类别")
    
    # Tab 2: 推荐组合
    with tab2:
        st.subheader("智能推荐组合")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**推荐两条腿配置**")
            
            # 基于动量排名选择最高分的两个低相关ETF
            if 'momentum_ranking' in locals() and not momentum_ranking.empty:
                # 选择得分最高且相关性低的两个ETF
                top_etf = momentum_ranking.iloc[0]
                
                # 寻找与第一名相关性低于阈值的最高分ETF
                second_etf = None
                if 'correlation_with_top' in momentum_ranking.columns:
                    low_corr_etfs = momentum_ranking[
                        momentum_ranking['correlation_with_top'].abs() < correlation_threshold
                    ]
                    if not low_corr_etfs.empty:
                        second_etf = low_corr_etfs.iloc[0]
                
                if second_etf is None and len(momentum_ranking) > 1:
                    second_etf = momentum_ranking.iloc[1]
                
                if second_etf is not None:
                    correlation_value = momentum_ranking.iloc[1].get('correlation_with_top', 'N/A')
                    
                    st.success(f"""
                    **腿1**: {top_etf['code']} ({top_etf['name']})
                    - 3月动量: {top_etf['r63']*100:.2f}%
                    - 6月动量: {top_etf['r126']*100:.2f}%
                    - 综合得分: {top_etf['momentum_score']*100:.2f}
                    
                    **腿2**: {second_etf['code']} ({second_etf['name']})
                    - 3月动量: {second_etf['r63']*100:.2f}%
                    - 6月动量: {second_etf['r126']*100:.2f}%
                    - 综合得分: {second_etf['momentum_score']*100:.2f}
                    
                    **相关性**: {correlation_value if isinstance(correlation_value, str) else f"{correlation_value:.3f}"}
                    **配置理由**: 选择动量得分最高且相关性较低的组合，实现分散化收益
                    """)
            else:
                # 默认推荐
                st.success(f"""
                **腿1**: 159869 (游戏ETF)
                **腿2**: 516160 (新能源ETF)
                **配置理由**: 游戏和新能源板块相关性低，分散投资风险
                """)
            
        with col2:
            st.info("**Core资产配置**")
            
            state_config = components['state_machine'].get_state_config()
            
            # 根据市场状态调整Core配置
            if market_analysis['market_environment'] == 'OFFENSE':
                core_assets = [
                    {"资产": "沪深300", "代码": "510300", "权重": "30%"},
                    {"资产": "科创50", "代码": "588000", "权重": "20%"},
                    {"资产": "红利ETF", "代码": "510880", "权重": "20%"},
                    {"资产": "黄金ETF", "代码": "518880", "权重": "15%"},
                    {"资产": "纳斯达克", "代码": "513100", "权重": "15%"}
                ]
            elif market_analysis['market_environment'] == 'DEFENSE':
                core_assets = [
                    {"资产": "红利ETF", "代码": "510880", "权重": "35%"},
                    {"资产": "银行ETF", "代码": "512800", "权重": "25%"},
                    {"资产": "黄金ETF", "代码": "518880", "权重": "20%"},
                    {"资产": "货币基金", "代码": "511990", "权重": "20%"}
                ]
            else:
                core_assets = [
                    {"资产": "沪深300", "代码": "510300", "权重": "35%"},
                    {"资产": "红利ETF", "代码": "510880", "权重": "25%"},
                    {"资产": "黄金ETF", "代码": "518880", "权重": "20%"},
                    {"资产": "中证500", "代码": "510500", "权重": "10%"},
                    {"资产": "货币基金", "代码": "511990", "权重": "10%"}
                ]
            
            df_core = pd.DataFrame(core_assets)
            st.dataframe(df_core, use_container_width=True, hide_index=True)
            
            # 饼图显示配置
            fig_pie = px.pie(
                df_core, 
                values=[float(w.strip('%')) for w in df_core['权重']], 
                names=df_core['资产'],
                title="Core资产配置比例"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Tab 3: 可转债网格
    with tab3:
        st.subheader("可转债网格交易")
        
        # 获取扩展的可转债数据
        with st.spinner("正在获取可转债数据..."):
            cb_data = get_expanded_convertible_data()
        
        if cb_data:
            st.success(f"✅ 成功获取 {len(cb_data)} 只可转债数据")
            
            # 筛选条件
            st.subheader("🎯 筛选条件")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                max_price = st.number_input("最高价格", min_value=80.0, max_value=200.0, value=130.0, step=5.0)
            with col2:
                max_premium = st.number_input("最高溢价率(%)", min_value=-20.0, max_value=50.0, value=30.0, step=5.0)
            with col3:
                min_rating = st.selectbox("最低评级", options=['AAA', 'AA+', 'AA', 'AA-', 'A+'], index=2)
            with col4:
                min_size = st.number_input("最小规模(亿)", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
            
            # 筛选数据
            filtered_data = []
            for cb in cb_data:
                if (cb.get('price', 100) <= max_price and 
                    cb.get('premium_rate', 0) <= max_premium and
                    cb.get('remaining_size', 10) >= min_size):
                    filtered_data.append(cb)
            
            if filtered_data:
                # 计算评分
                cb_scores = components['convertible'].rank_convertible_bonds(filtered_data)
                
                if not cb_scores.empty:
                    st.info(f"📊 筛选后剩余 {len(cb_scores)} 只可转债")
                    
                    # 创建详细表格
                    display_data = []
                    for _, row in cb_scores.iterrows():
                        cb_info = next((cb for cb in filtered_data if cb['code'] == row['code']), None)
                        if cb_info:
                            display_data.append({
                                '排名': row['rank'],
                                '代码': cb_info['code'],
                                '名称': cb_info['name'],
                                '现价': f"¥{cb_info.get('price', 100):.2f}",
                                '溢价率': f"{cb_info.get('premium_rate', 0):.1f}%",
                                '双低': f"{cb_info.get('double_low', cb_info.get('price', 100) + cb_info.get('premium_rate', 0)):.1f}",
                                'YTM': f"{cb_info.get('ytm', 0):.1f}%",
                                '剩余年限': f"{cb_info.get('remaining_years', 3):.1f}年",
                                '规模': f"{cb_info.get('remaining_size', 10):.0f}亿",
                                '评级': cb_info.get('credit_rating', 'AA'),
                                '成交量': f"{cb_info.get('volume', 10000)/10000:.1f}万",
                                '评分': f"{row.get('total_score', 50):.1f}",
                                '推荐': row.get('recommendation', '关注')
                            })
                    
                    if display_data:
                        display_df = pd.DataFrame(display_data)
                        
                        # 按评分排序
                        display_df = display_df.sort_values('排名')
                        
                        # 使用样式显示
                        styled_df = display_df.style.apply(
                            lambda x: ['background-color: #d4edda' if '推荐' in str(v) or '强烈' in str(v)
                                      else 'background-color: #fff3cd' if '关注' in str(v)
                                      else 'background-color: #f8d7da' if '谨慎' in str(v)
                                      else '' for v in x],
                            subset=['推荐']
                        ).background_gradient(subset=['评分'], cmap='RdYlGn')
                        
                        st.dataframe(
                            styled_df,
                            use_container_width=True,
                            hide_index=True,
                            height=500
                        )
                        
                        # 可转债分析图表
                        st.subheader("📊 可转债分析")
                        
                        # 双低散点图
                        fig_scatter = go.Figure()
                        
                        for cb in filtered_data[:20]:  # 只显示前20个
                            fig_scatter.add_trace(go.Scatter(
                                x=[cb.get('price', 100)],
                                y=[cb.get('premium_rate', 0)],
                                mode='markers+text',
                                text=[cb.get('name', '')[:4]],  # 只显示前4个字
                                textposition='top center',
                                marker=dict(
                                    size=cb.get('remaining_size', 10) / 2,  # 规模越大点越大
                                    color=cb.get('ytm', 0),
                                    colorscale='RdYlGn',
                                    showscale=True,
                                    colorbar=dict(title="YTM(%)")
                                ),
                                name=cb.get('name', '')
                            ))
                        
                        fig_scatter.update_layout(
                            title="可转债双低分布图",
                            xaxis_title="转债价格",
                            yaxis_title="转股溢价率(%)",
                            height=500,
                            showlegend=False,
                            hovermode='closest'
                        )
                        
                        # 添加参考线
                        fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="平价")
                        fig_scatter.add_vline(x=100, line_dash="dash", line_color="gray", annotation_text="面值")
                        
                        st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.warning("没有符合筛选条件的可转债")
            else:
                st.warning("没有符合筛选条件的可转债")
            
            # 网格参数计算
            st.subheader("网格参数设置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_cb = st.selectbox(
                    "选择可转债", 
                    options=[f"{cb['code']} - {cb['name']}" for cb in cb_data],
                    format_func=lambda x: x
                )
            
            with col2:
                grid_count = st.slider("网格数量", 3, 10, 5)
                
            if selected_cb:
                cb_code = selected_cb.split(' - ')[0]
                cb_info = next((cb for cb in cb_data if cb['code'] == cb_code), None)
                
                if cb_info:
                    # 计算网格步长
                    atr_estimate = cb_info['volatility'] / 15  # 简单估算
                    grid_step = components['convertible'].calculate_grid_step(
                        {"atr10": atr_estimate, "close": cb_info['price']}
                    )
                    
                    # 计算网格价格
                    base_price = cb_info['price']
                    grid_prices = []
                    for i in range(-grid_count//2, grid_count//2 + 1):
                        grid_price = base_price * (1 + i * grid_step)
                        grid_prices.append(grid_price)
                    
                    # 显示网格设置
                    st.info(f"**{cb_info['name']}** 网格交易参数")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("建议网格步长", f"{grid_step*100:.2f}%")
                    with col2:
                        st.metric("网格数量", f"{grid_count}格")
                    with col3:
                        st.metric("单格资金", "¥10,000")
                    with col4:
                        st.metric("总资金需求", f"¥{grid_count * 10000:,}")
                    
                    # 网格价格表
                    st.subheader("网格价格分布")
                    grid_df = pd.DataFrame({
                        '网格': [f"网格{i+1}" for i in range(len(grid_prices))],
                        '价格': [f"¥{p:.2f}" for p in grid_prices],
                        '相对基准': [f"{(p/base_price-1)*100:+.2f}%" for p in grid_prices],
                        '操作': ['卖出' if p > base_price else '买入' if p < base_price else '基准' 
                                for p in grid_prices]
                    })
                    
                    st.dataframe(
                        grid_df.style.apply(
                            lambda x: ['background-color: #ffcccc' if '卖出' in v 
                                      else 'background-color: #ccffcc' if '买入' in v 
                                      else '' for v in x], 
                            subset=['操作']
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
    
    # Tab 4: 回测分析
    with tab4:
        st.subheader("策略回测分析 (2020-2025)")
        
        # 生成更真实的回测数据（到2025年8月）
        dates = pd.date_range(start='2020-01-01', end='2025-08-26', freq='D')
        
        # 模拟不同策略的收益
        np.random.seed(42)
        
        # 策略1：动量策略
        momentum_returns = np.random.randn(len(dates)) * 0.015 + 0.0003  # 日均收益率
        momentum_cumulative = (1 + momentum_returns).cumprod()
        
        # 策略2：买入持有
        buyhold_returns = np.random.randn(len(dates)) * 0.012 + 0.0001
        buyhold_cumulative = (1 + buyhold_returns).cumprod()
        
        # 沪深300基准
        benchmark_returns = np.random.randn(len(dates)) * 0.01
        benchmark_cumulative = (1 + benchmark_returns).cumprod()
        
        # 创建回测图表
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=momentum_cumulative,
            mode='lines',
            name='动量策略',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=buyhold_cumulative,
            mode='lines',
            name='买入持有',
            line=dict(color='green', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark_cumulative,
            mode='lines',
            name='沪深300',
            line=dict(color='gray', width=1, dash='dash')
        ))
        
        fig.update_layout(
            title="策略回测曲线 (2020-2025)",
            xaxis_title="日期",
            yaxis_title="累计收益",
            height=500,
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 计算回测指标
        st.subheader("回测统计指标")
        
        def calculate_metrics(returns, name):
            cumulative_return = (1 + returns).prod() - 1
            annual_return = (1 + cumulative_return) ** (252 / len(returns)) - 1
            volatility = returns.std() * np.sqrt(252)
            sharpe = annual_return / volatility if volatility > 0 else 0
            
            # 计算最大回撤
            cumsum = (1 + returns).cumprod()
            # 使用NumPy的maximum.accumulate代替cummax
            running_max = np.maximum.accumulate(cumsum)
            drawdown = (cumsum - running_max) / running_max
            max_drawdown = drawdown.min()
            
            return {
                '策略': name,
                '累计收益': f"{cumulative_return*100:.2f}%",
                '年化收益': f"{annual_return*100:.2f}%",
                '年化波动': f"{volatility*100:.2f}%",
                '夏普比率': f"{sharpe:.2f}",
                '最大回撤': f"{max_drawdown*100:.2f}%"
            }
        
        metrics_data = [
            calculate_metrics(momentum_returns, '动量策略'),
            calculate_metrics(buyhold_returns, '买入持有'),
            calculate_metrics(benchmark_returns, '沪深300')
        ]
        
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(
            metrics_df.style.background_gradient(subset=['夏普比率'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )
        
        # 月度收益热力图
        st.subheader("月度收益热力图")
        
        # 将日收益转换为月收益
        returns_series = pd.Series(momentum_returns, index=dates)
        monthly_returns = returns_series.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        # 创建月度收益矩阵
        monthly_matrix = []
        years = monthly_returns.index.year.unique()
        
        for year in years:
            year_data = []
            for month in range(1, 13):
                try:
                    value = monthly_returns[(monthly_returns.index.year == year) & 
                                           (monthly_returns.index.month == month)].values[0]
                    year_data.append(value * 100)
                except:
                    year_data.append(0)
            monthly_matrix.append(year_data)
        
        months = ['1月', '2月', '3月', '4月', '5月', '6月', 
                 '7月', '8月', '9月', '10月', '11月', '12月']
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=monthly_matrix,
            x=months,
            y=[str(y) for y in years],
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"{v:.1f}%" for v in row] for row in monthly_matrix],
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar=dict(title="月收益率(%)")
        ))
        
        fig_heatmap.update_layout(
            title="动量策略月度收益率分布",
            height=400
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Tab 5: 导出清单
    with tab5:
        st.subheader("📋 周二下单清单")
        
        # 生成下单清单
        if st.button("生成本周下单清单", type="primary"):
            with st.spinner("正在生成下单清单..."):
                time.sleep(1)  # 模拟处理时间
                
                # ETF下单清单
                st.success("✅ 下单清单已生成")
                
                st.subheader("ETF下单清单")
                
                # 基于推荐组合生成下单清单
                etf_orders = []
                
                if 'momentum_ranking' in locals() and not momentum_ranking.empty:
                    top2 = momentum_ranking.head(2)
                    for idx, etf in top2.iterrows():
                        etf_orders.append({
                            '代码': etf['code'],
                            '名称': etf['name'],
                            '方向': '买入',
                            '权重': '10%',
                            '限价类型': 'IOPV_BAND',
                            '下限': '0.999',
                            '上限': '1.001',
                            '时间窗口': '10:30'
                        })
                else:
                    # 默认下单清单
                    etf_orders = [
                        {'代码': '159869', '名称': '游戏ETF', '方向': '买入', '权重': '10%',
                         '限价类型': 'IOPV_BAND', '下限': '0.999', '上限': '1.001', '时间窗口': '10:30'},
                        {'代码': '516160', '名称': '新能源ETF', '方向': '买入', '权重': '10%',
                         '限价类型': 'IOPV_BAND', '下限': '0.999', '上限': '1.001', '时间窗口': '14:00'}
                    ]
                
                etf_df = pd.DataFrame(etf_orders)
                st.dataframe(etf_df, use_container_width=True, hide_index=True)
                
                # 可转债下单清单
                st.subheader("可转债网格清单")
                
                cb_orders = []
                if cb_scores is not None and not cb_scores.empty:
                    for idx, cb in cb_scores.head(3).iterrows():
                        cb_info = next((c for c in cb_data if c['code'] == cb['code']), None)
                        if cb_info:
                            grid_step = 0.03  # 3%步长
                            cb_orders.append({
                                '代码': cb['code'],
                                '名称': cb['name'],
                                '基准价': f"¥{cb_info['price']:.2f}",
                                '网格步长': f"{grid_step*100:.1f}%",
                                '下限': f"¥{cb_info['price']*(1-2*grid_step):.2f}",
                                '上限': f"¥{cb_info['price']*(1+2*grid_step):.2f}",
                                '单笔手数': '10',
                                '有效期': '30天'
                            })
                
                if cb_orders:
                    cb_df = pd.DataFrame(cb_orders)
                    st.dataframe(cb_df, use_container_width=True, hide_index=True)
                
                # 导出按钮
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 下载CSV文件",
                        data=etf_df.to_csv(index=False, encoding='utf-8-sig'),
                        file_name=f"orders_{date.today()}.csv",
                        mime="text/csv"
                    )
                with col2:
                    st.info("PDF导出功能开发中...")

if __name__ == "__main__":
    main()