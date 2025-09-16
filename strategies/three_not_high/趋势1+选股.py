from utils.other import detect_sideways_breakout
from utils.three_not_high import *

my_stocks = []


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    """
    """
    pass  # 占位


def khPreMarket(data: Dict) -> List[Dict]:
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = khGet(data, "stocks")
    global my_stocks
    my_stocks = []
    for sc in ss:
        hit = khHistory(sc, ["close", "high", "low", "open", "volume"], 40, "1d", dn, fq="pre", force_download=False)
        signal = detect_sideways_breakout(hit[sc])
        if sum(list(signal[-20:])):
            my_stocks.append(sc)
    return []


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = max(0.1, 1 / len(my_stocks)) if my_stocks else 1.0
    for sc in my_stocks:  # 遍历股票池
        try:
            TRAND_N = 5
            D = 253
            hist = khHistory(sc, ["close", "high", "low", "open"], D, "1d", dn, fq="pre", force_download=False)

            c = hist[sc]['close']
            h = hist[sc]['high']
            l = hist[sc]['low']
            o = hist[sc]['open']

            pre_c = c.values[-1]
            pre_h = h.values[-1]
            pre_l = l.values[-1]
            pre_o = o.values[-1]

            up_rate = (pre_c - pre_o) / pre_o * 100

            up, down = calc_three_high_low(c, h, l)
            up_trend, down_trend, shake_trend = calc_trend(up, down, c, n=TRAND_N)

            ma5_now = float(MA(c, 5)[-1])  # 当日MA5
            ma20_now = float(MA(c, 20)[-1])  # 当日MA20

            av = calc_annual_volatility(c.values)
            l_p = ma5_now * (1 - av / 4)
            h_p = ma5_now * (1 + av / 4)

            n_p = khPrice(data, sc, "open")  # 当日开盘价

            def buy():
                if khHas(data, sc):
                    return False
                elif ma5_now <= ma20_now:
                    if pre_l <= l_p:
                        return True
                    else:
                        return False
                else:
                    if pre_l <= l_p:
                        return True
                    if up_trend.values[-1] and not up_trend.values[-2]:
                        return True
                    return False

            def sell():
                if not khHas(data, sc):
                    return False
                else:
                    if pre_h >= h_p and pre_c < pre_o:
                        return True
                    if down_trend.values[-1]:
                        return True
                    if shake_trend.values[-1] and down.values[-1]:
                        return True
                    return False

            if buy():
                signals.extend(generate_signal(data, sc, n_p, ss, "buy", f"{sc[:6]} 趋势"))

            if sell():
                signals.extend(generate_signal(data, sc, n_p, 1.0, "sell", f"{sc[:6]} 趋势"))

        except Exception as e:
            logging.error(f"=cfx= {sc} 执行策略失败: {str(e)}")
            continue
    return signals  # 返回信号
