from utils.anysise import calc_sell_future_return
from utils.large_money import calc_large_money_and_sell, calc_large_money_and_sell_and_limit
from utils.three_not_high import *


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    """
    """
    pass  # 占位


def khPreMarket(data: Dict) -> List[Dict]:
    pass


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = khGet(data, "stocks")

    my_stocks = []
    my_sell = []
    for sc in ss:
        hit = khHistory(sc, ["close", "high", "low", "open", "amount"], 120, "1d", dn, fq="pre", force_download=False)
        dfs = calc_large_money_and_sell(sc, hit[sc], 5, 60, 1.5)
        dfs = calc_large_money_and_sell_and_limit(sc, dfs[0], 32)
        df, buy, sell = calc_sell_future_return(dfs[0])
        p = df['close'].values[-1]
        if buy and not khHas(data, sc):
            my_stocks.append((sc, p))
        if sell and khHas(data, sc):
            my_sell.append(sc)
    topn = list(sorted(my_stocks, key=lambda x: x[1])[:10])
    my_stocks = []
    for n, _ in topn:
        my_stocks.append(n)

    signals = []  # 信号列表
    for sc in my_sell:
        p = khPrice(data, sc, "open")  # 当日开盘价
        signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 触发卖出"))
    for sc in my_stocks:  # 遍历股票池
        p = khPrice(data, sc, "open")  # 当日开盘价
        signals.extend(generate_signal(data, sc, p, 0.1, "buy", f"{sc[:6]} 资金流"))
    return signals  # 返回信号
