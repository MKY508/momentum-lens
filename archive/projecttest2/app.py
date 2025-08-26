"""
ETF动量策略系统 - Streamlit UI
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yaml
import os

from decision_engine import DecisionEngine
from data_adapter import DataAdapter
from indicators import IndicatorCalculator

# 页面配置
st.set_page_config(
    page_title="ETF动量策略系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载配置
@st.cache_resource
def load_config():
    with open("config.yaml", 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 初始化组件
@st.cache_resource
def init_components():
    engine = DecisionEngine()
    adapter = DataAdapter()
    calculator = IndicatorCalculator()
    return engine, adapter, calculator

def main():
    st.title("📈 ETF动量核心卫星策略系统")
    st.markdown("---")
    
    # 初始化
    config = load_config()
    engine, adapter, calculator = init_components()
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 市场状态
        market_state = engine.analyze_market_state()
        state_color = {
            "BULLISH": "🟢",
            "BEARISH": "🔴", 
            "SIDEWAYS": "🟡",
            "UNKNOWN": "⚪"
        }
        st.metric(
            "市场状态",
            f"{state_color.get(market_state, '⚪')} {market_state}",
            help="基于沪深300与MA200的关系判断"
        )
        
        st.markdown("---")
        
        # 功能选择
        page = st.selectbox(
            "功能选择",
            ["🎯 决策面板", "📊 动量排名", "💰 可转债筛选", 
             "📋 订单生成", "⚙️ 参数设置", "📈 回测分析"]
        )
    
    # 主界面
    if page == "🎯 决策面板":
        show_decision_panel(engine, adapter)
    elif page == "📊 动量排名":
        show_momentum_ranking(engine)
    elif page == "💰 可转债筛选":
        show_convertible_bonds(engine)
    elif page == "📋 订单生成":
        show_order_generation(engine, config)
    elif page == "⚙️ 参数设置":
        show_settings(config)
    elif page == "📈 回测分析":
        show_backtest()

def show_decision_panel(engine, adapter):
    """决策面板"""
    st.header("🎯 投资决策面板")
    
    # 生成信号
    with st.spinner("正在分析市场数据..."):
        signals = engine.generate_signals()
    
    if not signals:
        st.warning("暂无交易信号")
        return
    
    # 按模块分组显示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏛️ Core资产 (40%)")
        core_signals = [s for s in signals if s.module == "CORE"]
        for signal in core_signals:
            st.info(f"""
            **{signal.name}** ({signal.code})  
            权重: {signal.weight:.1%}  
            操作: {signal.action}  
            原因: {signal.reason}
            """)
    
    with col2:
        st.subheader("🚀 卫星资产 (30%)")
        satellite_signals = [s for s in signals if s.module == "SATELLITE"]
        for signal in satellite_signals:
            st.success(f"""
            **{signal.name}** ({signal.code})  
            权重: {signal.weight:.1%}  
            操作: {signal.action}  
            原因: {signal.reason}
            """)
    
    with col3:
        st.subheader("🔄 可转债 (10%)")
        cb_signals = [s for s in signals if s.module == "CB"]
        for signal in cb_signals:
            st.warning(f"""
            **{signal.name}** ({signal.code})  
            权重: {signal.weight:.1%}  
            操作: {signal.action}  
            原因: {signal.reason}
            """)
    
    # 资产配置饼图
    st.markdown("---")
    st.subheader("📊 资产配置分布")
    
    # 准备数据
    allocation_data = []
    for signal in signals:
        allocation_data.append({
            'asset': f"{signal.name}",
            'weight': signal.weight,
            'module': signal.module
        })
    
    # 添加现金
    cash_weight = 1 - sum(s.weight for s in signals)
    allocation_data.append({
        'asset': '现金',
        'weight': cash_weight,
        'module': 'CASH'
    })
    
    df_allocation = pd.DataFrame(allocation_data)
    
    # 绘制饼图
    fig = px.pie(
        df_allocation,
        values='weight',
        names='asset',
        color='module',
        color_discrete_map={
            'CORE': '#3498db',
            'SATELLITE': '#2ecc71',
            'CB': '#f39c12',
            'CASH': '#95a5a6'
        }
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def show_momentum_ranking(engine):
    """动量排名"""
    st.header("📊 ETF动量排名")
    
    with st.spinner("正在计算动量得分..."):
        scores = engine.score_etfs()
    
    if not scores:
        st.warning("暂无数据")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame([
        {
            '代码': s.code,
            '名称': s.name,
            '动量得分': s.momentum_score,
            '3月收益': s.r60,
            '6月收益': s.r120,
            'MA200状态': s.ma200_state,
            '成交额(亿)': s.turnover / 100000000,
            '合格': '✅' if s.qualified else '❌'
        }
        for s in scores[:20]  # 显示前20
    ])
    
    # 设置样式（移除background_gradient避免matplotlib依赖）
    st.dataframe(
        df.style.format({
            '动量得分': '{:.2f}',
            '3月收益': '{:.2f}%',
            '6月收益': '{:.2f}%',
            '成交额(亿)': '{:.2f}'
        }),
        use_container_width=True
    )
    
    # 动量散点图
    st.subheader("📈 动量分布图")
    
    fig = px.scatter(
        df,
        x='3月收益',
        y='6月收益',
        size='成交额(亿)',
        color='动量得分',
        hover_data=['代码', '名称'],
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(
        xaxis_title="3月收益率 (%)",
        yaxis_title="6月收益率 (%)"
    )
    st.plotly_chart(fig, use_container_width=True)

def show_convertible_bonds(engine):
    """可转债筛选"""
    st.header("💰 可转债筛选")
    
    with st.spinner("正在获取可转债数据..."):
        cb_scores = engine.score_convertible_bonds()
    
    if cb_scores.empty:
        st.warning("暂无可转债数据")
        return
    
    # 显示表格（移除background_gradient避免matplotlib依赖）
    st.dataframe(
        cb_scores.style.format({
            'total_score': '{:.2f}',
            'size_score': '{:.2f}',
            'premium_score': '{:.2f}',
            'maturity_score': '{:.2f}',
            'rating_score': '{:.2f}'
        }),
        use_container_width=True
    )

def show_order_generation(engine, config):
    """订单生成"""
    st.header("📋 订单生成器")
    
    # 选择交易时间
    col1, col2 = st.columns(2)
    with col1:
        trade_day = st.selectbox("交易日", ["周二", "周三", "周四", "周五"])
    with col2:
        trade_time = st.selectbox("交易时间", ["10:30", "14:00", "14:30"])
    
    # 资金设置
    total_capital = st.number_input(
        "总资金 (元)", 
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000
    )
    
    if st.button("生成订单", type="primary"):
        with st.spinner("正在生成订单..."):
            signals = engine.generate_signals()
            
        if not signals:
            st.warning("暂无交易信号")
            return
        
        # 生成订单表
        orders = []
        for signal in signals:
            if signal.action == "BUY":
                amount = total_capital * signal.weight
                orders.append({
                    '代码': signal.code,
                    '名称': signal.name,
                    '方向': '买入',
                    '金额': amount,
                    '模块': signal.module,
                    '原因': signal.reason,
                    '止损价': signal.stop_loss if signal.stop_loss else '-'
                })
        
        df_orders = pd.DataFrame(orders)
        
        # 显示订单
        st.subheader("📄 订单详情")
        st.dataframe(
            df_orders.style.format({
                '金额': '¥{:,.0f}',
                '止损价': '{:.3f}'
            }),
            use_container_width=True
        )
        
        # 下载按钮
        csv = df_orders.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载CSV",
            data=csv,
            file_name=f"orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # 生成条件单脚本
        st.subheader("🤖 半自动下单脚本")
        st.code(f"""
# 条件单设置（以华泰证券为例）
# 交易时间: {trade_day} {trade_time}

import easytrader
import time

# 登录券商
user = easytrader.use('ht')  # 华泰
user.prepare('config.json')  # 配置文件

# 批量下单
orders = {df_orders.to_dict('records')}

for order in orders:
    user.buy(order['代码'], amount=order['金额'])
    time.sleep(1)  # 避免频繁交易
    
print("订单提交完成")
        """, language='python')

def show_settings(config):
    """参数设置"""
    st.header("⚙️ 策略参数设置")
    
    # 使用tabs组织设置
    tab1, tab2, tab3 = st.tabs(["策略参数", "风控参数", "数据配置"])
    
    with tab1:
        st.subheader("资产配置比例")
        col1, col2 = st.columns(2)
        with col1:
            core_ratio = st.slider("Core资产比例", 0.0, 1.0, 
                                  config['strategy']['core_ratio'], 0.05)
            satellite_ratio = st.slider("卫星资产比例", 0.0, 1.0,
                                       config['strategy']['satellite_ratio'], 0.05)
        with col2:
            cb_ratio = st.slider("可转债比例", 0.0, 1.0,
                                config['strategy']['cb_ratio'], 0.05)
            cash_ratio = st.slider("现金比例", 0.0, 1.0,
                                  config['strategy']['cash_ratio'], 0.05)
        
        # 检查总和
        total = core_ratio + satellite_ratio + cb_ratio + cash_ratio
        if abs(total - 1.0) > 0.01:
            st.error(f"配置比例总和必须为100% (当前: {total:.1%})")
        
        st.subheader("动量参数")
        r60_weight = st.slider("3月动量权重", 0.0, 1.0,
                              config['strategy']['momentum']['r60_weight'], 0.1)
        
    with tab2:
        st.subheader("止损设置")
        default_stop = st.number_input("默认止损 (%)", -30, 0,
                                      int(config['strategy']['risk']['default_stop_loss'] * 100))
        sideways_stop = st.number_input("震荡市止损 (%)", -30, 0,
                                       int(config['strategy']['risk']['sideways_stop_loss'] * 100))
        trending_stop = st.number_input("趋势市止损 (%)", -30, 0,
                                       int(config['strategy']['risk']['trending_stop_loss'] * 100))
        
        st.subheader("资格检查")
        min_turnover = st.number_input("最小成交额 (万元)", 1000, 100000,
                                       config['strategy']['qualification']['min_turnover'] // 10000)
        buffer_rate = st.slider("缓冲率", 0.01, 0.10,
                               config['strategy']['qualification']['buffer_rate'], 0.01)
    
    with tab3:
        st.subheader("数据源设置")
        cache_hours = st.number_input("缓存时间 (小时)", 1, 24,
                                     config['data']['cache_hours'])
        retry_times = st.number_input("重试次数", 1, 10,
                                     config['data']['retry_times'])
    
    # 保存按钮
    if st.button("💾 保存配置"):
        # 更新配置
        config['strategy']['core_ratio'] = core_ratio
        config['strategy']['satellite_ratio'] = satellite_ratio
        config['strategy']['cb_ratio'] = cb_ratio
        config['strategy']['cash_ratio'] = cash_ratio
        config['strategy']['momentum']['r60_weight'] = r60_weight
        config['strategy']['risk']['default_stop_loss'] = default_stop / 100
        config['strategy']['risk']['sideways_stop_loss'] = sideways_stop / 100
        config['strategy']['risk']['trending_stop_loss'] = trending_stop / 100
        config['strategy']['qualification']['min_turnover'] = min_turnover * 10000
        config['strategy']['qualification']['buffer_rate'] = buffer_rate
        config['data']['cache_hours'] = cache_hours
        config['data']['retry_times'] = retry_times
        
        # 保存到文件
        with open("config.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        
        st.success("✅ 配置已保存")

def show_backtest():
    """回测分析"""
    st.header("📈 策略回测分析")
    st.info("回测功能开发中...")
    
    # 这里可以集成Backtrader进行回测
    st.markdown("""
    ### 计划功能：
    - 历史回测
    - 收益曲线
    - 最大回撤
    - 夏普比率
    - 月度收益热力图
    """)

if __name__ == "__main__":
    main()