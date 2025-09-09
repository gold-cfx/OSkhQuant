from khQuantImport import *  # 导入统一工具与指标
from utils.base import *


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    pass  # 占位


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    for sc in khGet(data, "stocks"):  # 遍历股票池
        try:
            close_hist = khHistory(sc, ["close"], 253, "1d", dn, fq="pre", force_download=False)
            high_hist = khHistory(sc, ["high"], 3, "1d", dn, fq="pre", force_download=False)
            low_hist = khHistory(sc, ["low"], 3, "1d", dn, fq="pre", force_download=False)

            c = close_hist[sc]['close'].values
            h = high_hist[sc]['high'].values
            l = low_hist[sc]['low'].values

            _, qs = determine_trend(c)

            ma5_now = float(MA(c, 5)[-1])  # 当日MA5
            ma20_now = float(MA(c, 20)[-1])  # 当日MA20

            now_c = c[-1]
            now_h = h[-1]
            now_l = l[-1]

            pre_c = c[-2]
            pre_h = h[-2]
            pre_l = l[-2]

            # 全小于:= C<前收 AND H<前高 AND L<前低;
            # 全大于:= C>前收 AND H>前高 AND L>前低;
            all_lt = now_c < pre_c and now_h < pre_h and now_l < pre_l
            all_gt = now_c > pre_c and now_h > pre_h and now_l > pre_l

            # 上涨：not all_lt
            up = not all_lt
            # 下跌：not all_gt
            down = not all_gt

            av = calc_annual_volatility(close_hist[sc]['close'].values)
            l_p = ma5_now * (1 - av / 4)
            h_p = ma5_now * (1 + av / 4)

            p = khPrice(data, sc, "open")  # 当日开盘价

            if qs == 0:
                # pass
                if now_c <= l_p and not khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 三不高：抄底"))
                if p >= ma5_now and khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 抄底：回20日"))

            elif qs == 1:
                if now_c <= l_p and not khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 三不高：抄底"))
                elif up and not down and not khHas(data, sc):  # 只有上涨信号，全部都大于
                    if ma5_now >= ma20_now:
                        signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 三不高：全高"))

                if now_c >= h_p and khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 三不高：逃顶"))
                elif down and not up and khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 三不高：全低"))
            elif qs == -1:
                if now_c <= l_p and not khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 三不高：抄底"))

                if p >= ma20_now and khHas(data, sc):
                    signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 抄底：回20日"))




        except Exception as e:
            logging.error(f"=cfx= {sc} 执行策略失败: {str(e)}")
            continue
    return signals  # 返回信号
