from utils.large_money import calc_large_money_and_sell
from utils.three_not_high import *

my_stocks = []
my_sell = []
pos = {}


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    """
    """
    pass  # 占位


def khPreMarket(data: Dict) -> List[Dict]:
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = khGet(data, "stocks")
    global my_stocks, pos, my_sell
    if pos:
        for k, v in pos.items():
            pos[k] += 1
    my_stocks = []
    my_sell = []
    for sc in ss:
        hit = khHistory(sc, ["close", "high", "low", "open", "amount"], 120, "1d", dn, fq="pre", force_download=False)
        _, ok, sell, warn, limit_sell = calc_large_money_and_sell(sc, hit[sc], 5, 60, 1.8)
        if ok and not khHas(data, sc):
            my_stocks.append(sc)
        if (sell or warn or limit_sell) and not ok and khHas(data, sc):
            my_sell.append(sc)

    return []


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    for sc in my_stocks:  # 遍历股票池
        p = khPrice(data, sc, "open")  # 当日开盘价
        # 持有周期会根据信号的个数延长N天
        signals.extend(generate_signal(data, sc, p, 0.1, "buy", f"{sc[:6]} 资金流"))

    for sc in my_sell:
        p = khPrice(data, sc, "open")  # 当日开盘价
        signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 触发卖出"))
    return signals  # 返回信号
