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
            c = close_hist[sc]['close'].values

            ma5_now = float(MA(c, 5)[-1])
            ma20_now = float(MA(c, 20)[-1])
            now_c = c[-1]

            av = calc_annual_volatility(close_hist[sc]['close'].values)
            l_p = ma5_now * (1 - av / 4)

            p = khPrice(data, sc, "open")  # 当日开盘价
            if now_c <= l_p and not khHas(data, sc):
                signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 抄底：超跌"))

            # =================

            if p >= ma20_now and khHas(data, sc):
                signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 抄底：回20日"))

        except Exception as e:
            logging.error(f"=cfx= {sc} 执行策略失败: {str(e)}")
            continue
    return signals  # 返回信号
