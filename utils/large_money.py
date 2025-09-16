from xtquant import xtdata

from MyTT import *


def calc_large_money(code, df, fast=5, slow=60, x=1.3):
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
