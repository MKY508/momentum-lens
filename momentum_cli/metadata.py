"""ETF 元数据，例如中文名称映射。"""

from __future__ import annotations

from typing import Dict

ETF_LABELS: Dict[str, str] = {
    # 核心仓
    "510300.XSHG": "沪深300ETF",
    "510880.XSHG": "红利ETF",
    "511360.XSHG": "短融ETF",
    "511020.XSHG": "国债ETF5-10年",
    "518880.XSHG": "黄金ETF",
    "513500.XSHG": "标普500ETF",
    # 卫星仓
    "159915.XSHE": "创业板ETF",
    "159949.XSHE": "创业板50ETF",
    "512400.XSHG": "有色金属ETF",
    "516010.XSHG": "游戏动漫ETF",
    "159842.XSHE": "券商ETF",
    "512800.XSHG": "银行ETF",
    "515030.XSHG": "新能源汽车ETF",
    "516160.XSHG": "新能源ETF",
    "515790.XSHG": "光伏ETF",
    "512720.XSHG": "计算机ETF",
    "512760.XSHG": "芯片ETF",
    "588000.XSHG": "科创50ETF",
    "159796.XSHE": "电池50ETF",
    "515050.XSHG": "5G通信ETF",
    "516510.XSHG": "中证云计算ETF",
    "159611.XSHE": "电力ETF",
    "516780.XSHG": "稀土ETF",
    "513180.XSHG": "恒生科技指数ETF",
    "159792.XSHE": "港股通互联网ETF",
    "512690.XSHG": "酒ETF",
    "159840.XSHE": "锂电池ETF（工银瑞信）",
}


def get_label(order_book_id: str) -> str:
    return ETF_LABELS.get(order_book_id.upper(), order_book_id.upper())
