from xtquant import xtdata

from MyTT import *


def calc_large_money(code, df, fast=5, slow=60, x=1.5):
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

    df['fast_cash_flow_power'] = df['fast_day_cash_flow'] / df['float_vol'] * df['close']
    df['slow_cash_flow_power'] = df['slow_day_cash_flow'] / df['float_vol'] * MA(df['close'], slow)[-1]
    df['ma_fast_cash_flow_power'] = df['fast_cash_flow_power'].abs().rolling(window=slow).mean()
    # 计算条件
    df['is_ok'] = (df['slow_day_cash_flow'] > 0) & (df['fast_day_cash_flow'] < 0) & (
            df['fast_cash_flow_power'].abs() > df['ma_fast_cash_flow_power'] * x)
    return df, df['is_ok'].values[-1]


def calc_large_money_and_sell(code, df, fast=5, slow=60, x=1.5, n=34):
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
    df["is_sell"] = (df['slow_day_cash_flow'] < 0) & (df['fast_day_cash_flow'] > 0) & (
            df['fast_cash_flow_power'].abs() > df['ma_fast_cash_flow_power'] * x)
    df["is_warn"] = (df['slow_day_cash_flow'] < df['ma_slow_day_cash_flow']) & (df['slow_day_cash_flow'] > 0) & (
            df['fast_day_cash_flow'] > 0) & (df['fast_cash_flow_power'].abs() > df['ma_fast_cash_flow_power'] * x)

    df['is_add'] = (df['slow_day_cash_flow'] < 0) & (df['fast_day_cash_flow'] < 0) & (
            df['fast_cash_flow_power'].abs() > df['ma_fast_cash_flow_power'] * x)

    df['limit_sell'] = False
    len_df = len(df)
    for i in range(len_df):
        if df.at[i, 'is_ok']:
            # 检查其后的 N 行数据
            subsequent_rows = df.iloc[i + 1:i + 1 + n]

            # 检查是否有 is_sell 或 is_warn 为 true
            if not subsequent_rows['is_sell'].any() and not subsequent_rows['is_warn'].any():
                # 如果没有，则在第 N+1 行数据中设置 limit_sell 为 true
                # 且n增加is_ok出现的次数
                add_day = subsequent_rows['is_ok'].sum()
                if i + 1 + n + add_day < len_df:
                    df.at[i + 1 + n, 'limit_sell'] = True

    return df, df['is_ok'].values[-1], df['is_sell'].values[-1], df['is_warn'].values[-1], df['limit_sell'].values[-1]
