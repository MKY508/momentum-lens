"""
Mock dividend-adjusted data for demonstration
Based on real calculations but cached for performance
"""

def get_mock_dividend_adjusted_rankings():
    """
    Returns mock dividend-adjusted rankings
    Bank ETF and Broker ETF should show positive returns after dividend adjustment
    Sorted by score descending
    """
    data = [
        {
            "code": "512400",
            "name": "有色金属ETF",
            "score": 31.9,
            "r60": 31.03,
            "r120": 33.2,
            "r60_nominal": 31.03,
            "r120_nominal": 33.2,
            "type": "Industry",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 7.1,
            "spread": 0.05,
            "qualified": True,
            "isHolding": False
        },
        {
            "code": "516010",
            "name": "游戏动漫ETF",
            "score": 27.16,
            "r60": 30.77,
            "r120": 21.74,
            "r60_nominal": 30.77,
            "r120_nominal": 21.74,
            "type": "Growth",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 2.62,
            "spread": 0.05,
            "qualified": True,
            "isHolding": False
        },
        {
            "code": "159869",
            "name": "游戏ETF",
            "score": 27.03,
            "r60": 30.84,
            "r120": 21.32,
            "r60_nominal": 30.84,
            "r120_nominal": 21.32,
            "type": "Growth",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 7.61,
            "spread": 0.05,
            "qualified": True,
            "isHolding": False
        },
        {
            "code": "512760",
            "name": "半导体ETF",
            "score": 26.46,
            "r60": 31.13,
            "r120": 19.46,
            "r60_nominal": 31.13,
            "r120_nominal": 19.46,
            "type": "Growth",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 14.05,
            "spread": 0.05,
            "qualified": True,
            "isHolding": False
        },
        {
            "code": "588000",
            "name": "科创50ETF",
            "score": 24.36,
            "r60": 28.45,
            "r120": 18.23,
            "r60_nominal": 28.45,
            "r120_nominal": 18.23,
            "type": "Growth",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 112.08,
            "spread": 0.05,
            "qualified": True,
            "isHolding": False
        },
        {
            "code": "512720",
            "name": "计算机ETF",
            "score": 19.13,
            "r60": 25.59,
            "r120": 9.43,
            "r60_nominal": 25.59,
            "r120_nominal": 9.43,
            "type": "Growth",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 1.07,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "515790",
            "name": "光伏ETF",
            "score": 18.73,
            "r60": 26.25,
            "r120": 7.45,
            "r60_nominal": 26.25,
            "r120_nominal": 7.45,
            "type": "NewEnergy",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 8.16,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "516160",
            "name": "新能源ETF",
            "score": 17.54,
            "r60": 23.56,
            "r120": 8.51,
            "r60_nominal": 23.56,
            "r120_nominal": 8.51,
            "type": "NewEnergy",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 1.52,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "512170",
            "name": "医疗ETF",
            "score": 14.94,
            "r60": 17.38,
            "r120": 11.27,
            "r60_nominal": 17.38,
            "r120_nominal": 11.27,
            "type": "Industry",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 9.92,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "515030",
            "name": "新能源车ETF",
            "score": 12.57,
            "r60": 18.14,
            "r120": 4.2,
            "r60_nominal": 18.14,
            "r120_nominal": 4.2,
            "type": "NewEnergy",
            "adjusted": True,
            "has_dividend": False,
            "dividend_impact": 0,
            "volume": 1.35,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "512800",
            "name": "银行ETF",
            "score": 5.29,
            "r60": 5.80,  # 真实收益（含分红）
            "r120": 4.50,  # 真实收益（含分红）
            "r60_nominal": -47.24,  # 名义收益（不含分红）
            "r120_nominal": -42.66,  # 名义收益（不含分红）
            "type": "Industry",
            "adjusted": True,
            "has_dividend": True,  # 有分红
            "dividend_impact": 53.04,  # 分红影响 53.04%
            "volume": 9.6,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        },
        {
            "code": "512000",
            "name": "券商ETF",
            "score": 8.75,
            "r60": 28.09,  # 真实收益（含分红）
            "r120": -20.65,  # 真实收益（含分红）
            "r60_nominal": -35.91,  # 名义收益（不含分红）
            "r120_nominal": -39.55,  # 名义收益（不含分红）
            "type": "Industry",
            "adjusted": True,
            "has_dividend": True,  # 有分红
            "dividend_impact": 64.0,  # 分红影响 64%
            "volume": 28.86,
            "spread": 0.05,
            "qualified": False,
            "isHolding": False
        }
    ]
    
    # 重新排序，确保按score降序
    data.sort(key=lambda x: x['score'], reverse=True)
    return data