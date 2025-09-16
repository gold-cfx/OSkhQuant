from khQuantImport import *  # 导入统一工具与指标
from utils.three_not_high import *


def init(stocks=None, data=None):  # 初始化（无需特殊处理）
    """策略初始化（本策略无需特殊初始化）"""
    """
R:=(C/REF(C,1))-1;
波动率:STD(R,S) * SQRT(252),NODRAW;
回撤率:波动率/4,NODRAW;

MA5:MA(C,5);
MAM:MA(C,M);

止损: MA5*(1-回撤率),COLORGREEN;
止盈: MA5*(1+回撤率),COLORMAGENTA;





前收:=REF(C,1);
前高:=REF(H,1);
前低:=REF(L,1);
全小于:= C<前收 AND H<前高 AND L<前低;
全大于:= C>前收 AND H>前高 AND L>前低;
非全大于:= NOT(全大于);
非全小于:=NOT(全小于);

{ 统计创新高和新低的次数 }
COUNT_HIGH:=COUNT(非全小于,N); 
COUNT_LOW:=COUNT(非全大于,N); 

{ 计算创新高/新低比例 }
RATIO_HIGH:=COUNT_HIGH/N;  
RATIO_LOW:=COUNT_LOW/N;  

{ 计算线性回归斜率（趋势方向） }
SLOPE1:=SLOPE(C,N);    { N天收盘价的线性回归斜率 }

{ 计算高低点的标准差（波动集中度） }
{ 趋势判断逻辑 }
UP_TREND:=RATIO_HIGH>U/10 AND SLOPE1>0;    { 上升趋势 }
DOWN_TREND:=RATIO_LOW>U/10 AND SLOPE1<0;    { 下降趋势 }
SHAKE_TREND:=NOT(UP_TREND)  AND NOT(DOWN_TREND);

{ 输出趋势判断结果 }
DRAWICON(UP_TREND,L,1);    { 上升趋势：在最低价位置画图标1 }
DRAWICON(DOWN_TREND,H,2);  { 下降趋势：在最高价位置画图标2 }
DRAWICON(SHAKE_TREND,(H+L)/2,3);    { 震荡趋势：在中间位置画图标3 };

DRAWICON(L<=止损,L,7);
DRAWICON(H >=止盈,H,8);
    """
    pass  # 占位


def khHandlebar(data: Dict) -> List[Dict]:  # 主策略函数
    signals = []  # 信号列表
    dn = khGet(data, "date_num")  # 当前日期(数值格式)
    ss = max(0.1, 1/len(khGet(data, "stocks")))
    for sc in khGet(data, "stocks"):  # 遍历股票池
        try:
            TRAND_N=5
            D=253
            hist = khHistory(sc, ["close", "high", "low", "open"], D, "1d", dn, fq="pre", force_download=False)

            c = hist[sc]['close']
            h = hist[sc]['high']
            l = hist[sc]['low']
            o = hist[sc]['open']

            pre_c = c.values[-1]
            pre_h = h.values[-1]
            pre_l = l.values[-1]
            pre_o = o.values[-1]

            up_rate = (pre_c - pre_o)/pre_o * 100

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
