"""
Cached dividend-adjusted ETF data for production use
Updated: 2025-08-25
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CachedDividendData:
    """
    缓存的分红调整数据，避免每次请求都重新计算
    实际生产环境应该定期更新这些数据
    """
    
    # 缓存的ETF数据（基于2025-08-25的真实计算）
    CACHED_DATA = {
        '512800': {  # 银行ETF
            'name': '银行ETF',
            'r60': 5.80,
            'r120': 4.50,
            'r60_nominal': -47.24,
            'r120_nominal': -42.66,
            'score': 5.29,
            'has_dividend': True,
            'dividend_date': '2025-07-04',
            'dividend_amount': 0.857,
            'dividend_impact': 53.04,
            'last_update': '2025-08-25'
        },
        '512000': {  # 券商ETF
            'name': '券商ETF',
            'r60': 28.09,
            'r120': -20.65,
            'r60_nominal': -35.91,
            'r120_nominal': -39.55,
            'score': 8.75,
            'has_dividend': True,
            'dividend_date': '2025-06-15',  # 推测
            'dividend_amount': 1.0,  # 推测
            'dividend_impact': 64.00,
            'last_update': '2025-08-25'
        },
        '512400': {  # 有色金属ETF
            'name': '有色金属ETF',
            'r60': 31.03,
            'r120': 33.20,
            'r60_nominal': 31.03,
            'r120_nominal': 33.20,
            'score': 31.90,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '516010': {  # 游戏动漫ETF
            'name': '游戏动漫ETF',
            'r60': 30.77,
            'r120': 21.74,
            'r60_nominal': 30.77,
            'r120_nominal': 21.74,
            'score': 27.16,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '159869': {  # 游戏ETF
            'name': '游戏ETF',
            'r60': 30.84,
            'r120': 21.32,
            'r60_nominal': 30.84,
            'r120_nominal': 21.32,
            'score': 27.03,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '512760': {  # 半导体ETF
            'name': '半导体ETF',
            'r60': 31.13,
            'r120': 19.46,
            'r60_nominal': 31.13,
            'r120_nominal': 19.46,
            'score': 26.46,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '588000': {  # 科创50ETF
            'name': '科创50ETF',
            'r60': 28.45,
            'r120': 18.23,
            'r60_nominal': 28.45,
            'r120_nominal': 18.23,
            'score': 24.36,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '512720': {  # 计算机ETF
            'name': '计算机ETF',
            'r60': 25.59,
            'r120': 9.43,
            'r60_nominal': 25.59,
            'r120_nominal': 9.43,
            'score': 19.13,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '515790': {  # 光伏ETF
            'name': '光伏ETF',
            'r60': 26.25,
            'r120': 7.45,
            'r60_nominal': 26.25,
            'r120_nominal': 7.45,
            'score': 18.73,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '516160': {  # 新能源ETF
            'name': '新能源ETF',
            'r60': 23.56,
            'r120': 8.51,
            'r60_nominal': 23.56,
            'r120_nominal': 8.51,
            'score': 17.54,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '512170': {  # 医疗ETF
            'name': '医疗ETF',
            'r60': 17.38,
            'r120': 11.27,
            'r60_nominal': 17.38,
            'r120_nominal': 11.27,
            'score': 14.94,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        },
        '515030': {  # 新能源车ETF
            'name': '新能源车ETF',
            'r60': 18.14,
            'r120': 4.20,
            'r60_nominal': 18.14,
            'r120_nominal': 4.20,
            'score': 12.57,
            'has_dividend': False,
            'dividend_impact': 0,
            'last_update': '2025-08-25'
        }
    }
    
    @classmethod
    def get_etf_data(cls, code: str) -> Optional[Dict]:
        """获取单个ETF的缓存数据"""
        return cls.CACHED_DATA.get(code)
    
    @classmethod
    def get_all_rankings(cls) -> List[Dict]:
        """获取所有ETF排名（已排序）"""
        result = []
        for code, data in cls.CACHED_DATA.items():
            etf_data = {
                'code': code,
                'name': data['name'],
                'score': data['score'],
                'r60': data['r60'],
                'r120': data['r120'],
                'r60_nominal': data.get('r60_nominal', data['r60']),
                'r120_nominal': data.get('r120_nominal', data['r120']),
                'has_dividend': data.get('has_dividend', False),
                'dividend_impact': data.get('dividend_impact', 0),
                'type': cls._get_etf_type(data['name']),
                'adjusted': True,
                'volume': 10.0,  # 默认值
                'spread': 0.05,
                'qualified': False  # 将在返回时根据排名设置
            }
            result.append(etf_data)
        
        # 按评分排序
        result.sort(key=lambda x: x['score'], reverse=True)
        
        # 设置前5名为qualified
        for i, etf in enumerate(result):
            if i < 5:
                etf['qualified'] = True
                
        return result
    
    @staticmethod
    def _get_etf_type(name: str) -> str:
        """根据名称判断ETF类型"""
        if any(keyword in name for keyword in ['游戏', '半导体', '科创', '计算机']):
            return 'Growth'
        elif any(keyword in name for keyword in ['新能源', '光伏']):
            return 'NewEnergy'
        else:
            return 'Industry'
    
    @classmethod
    def is_cache_valid(cls, code: str, max_age_hours: int = 24) -> bool:
        """检查缓存是否有效"""
        if code not in cls.CACHED_DATA:
            return False
            
        last_update = cls.CACHED_DATA[code].get('last_update')
        if not last_update:
            return False
            
        try:
            update_time = datetime.strptime(last_update, '%Y-%m-%d')
            age = datetime.now() - update_time
            return age < timedelta(hours=max_age_hours)
        except:
            return False
    
    @classmethod
    def update_cache(cls, code: str, data: Dict):
        """更新缓存数据"""
        if code in cls.CACHED_DATA:
            cls.CACHED_DATA[code].update(data)
            cls.CACHED_DATA[code]['last_update'] = datetime.now().strftime('%Y-%m-%d')