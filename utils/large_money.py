import numpy as np
from xtquant import xtdata

"""

{计算每日资金流}
每日资金流:=(CLOSE - OPEN) / (HIGH - LOW + 0.0001) * AMOUNT, COLORSTICK;

{计算N日累计资金流}
累计资金流S:=SUM(每日资金流, S);
累计资金流B:SUM(每日资金流, B), COLORWHITE, LINETHICK2;

{计算资金流强度（累计资金流 / 流通市值）}
强度S:累计资金流S / (FINANCE(7)*C / 10000),NODRAW;
强度S均值:MA(ABS(强度S),B),NODRAW;

强度B:=累计资金流B / (FINANCE(7)*MA(C,B) / 10000),NODRAW;

强度B均值:MA(ABS(强度B),S),NODRAW;
{0轴参考线}
0, COLORGRAY;

MMA2:=MA(累计资金流B,B);
强度S阈值:MAX(强度S均值*BV/100,MS),NODRAW;
OK:=累计资金流B>0 AND 强度B均值<= MB AND 累计资金流S<0 AND  ABS(强度S) >=强度S阈值;

DRAWICON(OK,累计资金流B, 1);




SLL:= 累计资金流B<0 AND 累计资金流S>0 AND  ABS(强度S) >=强度S阈值;



WAR:=累计资金流B<MMA2  AND 累计资金流S>0 AND  累计资金流B>0 AND ABS(强度S) >=强度S阈值;

ADD:=累计资金流B<0  AND 累计资金流S<0 AND ABS(强度S) >=强度S阈值;
DRAWICON(ADD,累计资金流B, 5);
DRAWICON(WAR,累计资金流B, 9);
DRAWICON(SLL,累计资金流B, 2);
"""


def calc_large_money(code, df, fast=5, slow=60, x=1.5, fast_power_t=250, slow_power_t=3000):
    """
    用2025年1.1-9.16全量数据测试（不考虑仓位、资金）
    如果选用5，60，1.3的参数，出现信号后买入
    持仓34-37天，收益290%，回撤3.7%，胜率33%
    持仓50-54天，收益420%，回撤2.6%，胜率25%

    如果选用5，60，1.5的参数，出现信号后买入
    持仓56天平，收益 10006%，回撤1.9%，胜率23%

    如果选用5，60，1.8的参数，出现信号后买入
    持仓56天平，收益 2540%，回撤1.6%，胜率22%

    """
    df['cash_flow'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 0.0001) * df['amount']
    df['fast_day_cash_flow'] = df['cash_flow'].rolling(window=fast).sum()
    df['slow_day_cash_flow'] = df['cash_flow'].rolling(window=slow).sum()
    if code:
        detail = xtdata.get_instrument_detail(code)
        if detail:
            float_vol1 = detail.get("FloatVolume")
            float_vol2 = detail.get("FloatVolumn")
            if float_vol1:
                df['float_vol'] = float_vol1
            elif float_vol2:
                df['float_vol'] = float_vol2
            else:
                # 默认十亿股
                df['float_vol'] = 100000000 * 10
        else:
            df['float_vol'] = 100000000 * 10
    else:
        df['float_vol'] = 100000000 * 10
    ma_slow_value = df['close'].rolling(window=slow).mean().values[-1]
    df['fast_cash_flow_power'] = df['fast_day_cash_flow'] / df['float_vol'] * df['close']
    df['slow_cash_flow_power'] = df['slow_day_cash_flow'] / df['float_vol'] * ma_slow_value
    df['ma_fast_cash_flow_power'] = df['fast_cash_flow_power'].abs().rolling(window=slow).mean()
    df['ma_slow_cash_flow_power'] = df['slow_cash_flow_power'].abs().rolling(window=fast).mean()
    # 计算条件
    df['slow_power_threshold'] = np.maximum(fast_power_t, df['ma_fast_cash_flow_power'] * x)

    cond1 = df['slow_day_cash_flow'] > 0
    cond2 = df['slow_cash_flow_power'] <= slow_power_t
    cond3 = df['fast_day_cash_flow'] < 0
    cond4 = df['fast_cash_flow_power'].abs() > df["slow_power_threshold"]

    df['is_ok'] = cond1 & cond2 & cond3 & cond4

    return df, df['is_ok'].values[-1]


def calc_large_money_and_sell(code, df, fast=5, slow=60, x=1.5):
    """
    用2025年1.1-9.16全量数据测试（不考虑仓位、资金）
    如果选用5，60，1.3的参数，出现信号后买入
    持仓34-36天，收益160%，回撤3.3%，胜率39%
    持仓58-60天，收益160%，回撤2.3%，胜率33%

    如果选用5，60，1.5的参数，出现信号后买入
    持仓36天，收益140%，回撤2.6%，胜率37%

    如果选用5，60，1.8的参数，出现信号后买入
    持仓55天，收益99%，回撤1.4%，胜率30%
    """
    df, _ = calc_large_money(code, df, fast, slow, x)
    df['ma_slow_day_cash_flow'] = df['slow_day_cash_flow'].rolling(window=slow).mean()
    cond1 = df['slow_day_cash_flow'] < 0
    cond2 = df['fast_day_cash_flow'] > 0
    cond3 = df['fast_cash_flow_power'].abs() > df["slow_power_threshold"]
    cond4 = df['slow_day_cash_flow'] < df['ma_slow_day_cash_flow']
    cond5 = df['slow_day_cash_flow'] > 0
    cond6 = df['fast_day_cash_flow'] < 0

    df["is_sell"] = cond1 & cond2 & cond3
    df["is_warn"] = cond4 & cond5 & cond3
    df['is_add'] = cond1 & cond6 & cond3

    return df, df['is_ok'].values[-1], df['is_sell'].values[-1], df['is_warn'].values[-1]


def calc_large_money_and_sell_and_limit(code, df, n):
    df['date'] = df['time'].dt.strftime('%y-%m-%d')
    df['limit_day'] = None
    queue = []  # 保存每个 is_ok 的到期索引
    len_df = len(df)
    for i in range(len_df):
        if df.at[i, 'is_ok']:
            # 检查其后的 N 行数据
            add_day = df.iloc[i + 1:i + n]['is_ok'].sum()
            expire = (i + n + add_day, df.at[i, 'date'])
            queue.append(expire)
    for item in queue:
        if item[0] >= len_df:
            continue
        df.at[item[0], 'limit_day'] = item[1]
    return df, df['is_ok'].values[-1], df['is_sell'].values[-1], df['is_warn'].values[-1], df['limit_day'].values[-1]
