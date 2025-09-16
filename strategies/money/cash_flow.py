from utils.large_money import calc_large_money
from utils.three_not_high import *

my_stocks = []
pos = {}


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    """
    """
    pass  # 占位


def khPreMarket(data: Dict) -> List[Dict]:
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = khGet(data, "stocks")
    global my_stocks, pos
    if pos:
        for k, v in pos.items():
            pos[k] += 1
    my_stocks = []
    for sc in ss:
        hit = khHistory(sc, ["close", "high", "low", "open", "amount"], 120, "1d", dn, fq="pre", force_download=False)
        _, ok = calc_large_money(sc, hit[sc], 5, 60, 1.3)
        if ok:
            my_stocks.append(sc)
    return []


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    ss = max(0.1, 1 / len(my_stocks)) if my_stocks else 1.0
    for sc in my_stocks:  # 遍历股票池
        p = khPrice(data, sc, "open")  # 当日开盘价
        pos[sc] = 0
        signals.extend(generate_signal(data, sc, p, ss, "buy", f"{sc[:6]} 资金流"))
    pos_copy = pos.copy()  # 创建字典的浅拷贝
    for sc, v in pos_copy.items():
        if v >= 5:
            del pos[sc]
            p = khPrice(data, sc, "open")  # 当日开盘价
            signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 资金流到期"))
    return signals  # 返回信号
