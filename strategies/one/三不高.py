# coding: utf-8
# 策略说明：
# - 策略名称：三不高
# - 功能：
# 前收:=REF(C,1);
# 前高:=REF(H,1);
# 前低:=REF(L,1);
# 全小于:= C<前收 AND H<前高 AND L<前低;
# 全大于:= C>前收 AND H>前高 AND L>前低;
# 非全大于:= NOT(全大于);
# 非全小于:=NOT(全小于);
# DRAWICON(非全大于,O,4);
# DRAWICON(非全小于,O,1);
# - 指标来源：
from khQuantImport import *  # 导入统一工具与指标


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    pass  # 占位


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    for sc in khGet(data, "stocks"):  # 遍历股票池
        try:
            close_hist = khHistory(sc, ["close"], 60, "1d", dn, fq="pre", force_download=False)
            high_hist = khHistory(sc, ["high"], 3, "1d", dn, fq="pre", force_download=False)
            low_hist = khHistory(sc, ["low"], 3, "1d", dn, fq="pre", force_download=False)

            c = close_hist[sc]['close'].values
            h = high_hist[sc]['high'].values
            l = low_hist[sc]['low'].values

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

            p = khPrice(data, sc, "open")  # 当日开盘价
            if up and not down and not khHas(data, sc):  # 只有上涨信号，全部都大于
                if ma5_now >= ma20_now:
                    signals.extend(generate_signal(data, sc, p, 0.2, "buy", f"{sc[:6]} 三不高：全高"))  # 0.5仓
            if down and not up and khHas(data, sc):
                signals.extend(generate_signal(data, sc, p, 1.0, "sell", f"{sc[:6]} 三不高：全低"))  # 全部卖出
        except Exception as e:
            logging.error(f"=cfx= {sc} 执行策略失败: {str(e)}")
            continue
    return signals  # 返回信号
