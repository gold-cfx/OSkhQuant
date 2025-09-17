# encoding:gbk
import datetime
import re

import pandas as pd

# ======================== 可修改区域 ========================

ACCOUNT = "27113139"


# ===========================================================
def get_klines(C, code_list: list, n: int = 365, start_time=None):
    """取最近 n 个交易日的收盘价序列"""
    if not start_time:
        now = datetime.datetime.now()
        # 计算n天前的日期
        target_date = now - datetime.timedelta(days=n)
        # 格式化为 YYYYMMDD 格式
        start_time = target_date.strftime("%Y%m%d")
    else:
        start_time = start_time.strftime("%Y%m%d")

    print(f"===开始下载历史数据， start_time = {start_time}")

    data = C.get_market_data_ex([], code_list, period='1d', start_time=start_time, end_time='',
                                dividend_type="front", fill_data=True, subscribe=True)
    result = {}
    for stock_code, stock_data in data.items():
        # 处理时间列
        if 'time' in stock_data.columns:
            # 转换时间列
            stock_data['time'] = pd.to_datetime(stock_data['time'].astype(float), unit='ms') + pd.Timedelta(hours=8)

            mask = stock_data['time'].dt.date < datetime.datetime.now().date()

            stock_data = stock_data[mask]

            # 按时间排序
            stock_data = stock_data.sort_values('time').reset_index(drop=True)
        result[stock_code] = stock_data

    return result


def is_stock(code):
    code = code[:6]
    pattern = r'^(600|601|603|605|688|000|001|002|003|300|301|836|920)\d{3}$'
    return bool(re.match(pattern, str(code)))


def calc_large_money(C, code, df, fast=5, slow=60, x=1.5):
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
        detail = C.get_instrument_detail(code)
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
    ma_slow = df['close'].rolling(window=slow).mean().values[-1]
    df['fast_cash_flow_power'] = df['fast_day_cash_flow'] / df['float_vol'] * df['close']
    df['slow_cash_flow_power'] = df['slow_day_cash_flow'] / df['float_vol'] * ma_slow
    df['ma_fast_cash_flow_power'] = df['fast_cash_flow_power'].abs().rolling(window=slow).mean()
    # 计算条件
    df['is_ok'] = (df['slow_day_cash_flow'] > 0) & (df['fast_day_cash_flow'] < 0) & (
            df['fast_cash_flow_power'].abs() > df['ma_fast_cash_flow_power'] * x)
    return df, df['is_ok'].values[-1]


def calc_large_money_and_sell(C, code, df, fast=5, slow=60, x=1.5, n=34):
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
    df, _ = calc_large_money(C, code, df, fast, slow, x)
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


def write_stocks(file_path, list_stocks):
    with open(file_path, 'a') as f:
        for stock_code in list_stocks:
            f.write(f"{stock_code}\r\n")


def run_once_successfully(func):
    """
    装饰器：确保函数成功执行一次
    如果执行失败（抛出异常），则下次调用时继续执行
    """
    memo = {}  # 存储函数执行结果或异常状态

    def wrapper(*args, **kwargs):
        if func in memo:
            # 如果已经成功执行过，直接返回结果
            if not isinstance(memo[func], Exception):
                return memo[func]
            # 如果之前执行失败，继续执行函数

        try:
            result = func(*args, **kwargs)
            memo[func] = result  # 存储成功结果
            return result
        except Exception as e:
            memo[func] = e  # 存储异常，下次调用继续尝试
            raise  # 抛出异常，但不会阻止下次调用

    return wrapper


@run_once_successfully
def calc_today_police(C):
    print("开始执行股票筛选")
    position_list: pd.DataFrame = get_trade_detail_data(ACCOUNT, 'STOCK', 'position')
    all_stocks = {f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list}
    print(f"查到所有持仓信息：{all_stocks}")
    position_info = {
        f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list if
        is_stock(o.m_strInstrumentID) and o.m_nVolume > 100
    }
    print("股票持仓信息：", position_info)
    C.position_info = position_info
    C.stock_list = C.get_stock_list_in_sector("沪深300")  # 获取沪深300股票列表
    all_stock_list = list(position_info.keys()) + C.stock_list
    C.history_data = get_klines(C, all_stock_list)

    print("开始计算指标")
    buy_list, sell_list = [], []
    for stock_code, df in C.history_data.items():
        _, is_ok, is_sell, is_warn, limit_sell = calc_large_money_and_sell(C, stock_code, df, x=1.5, n=35)
        if is_ok and stock_code not in position_list:
            buy_list.append(stock_code)
        elif stock_code in position_list and (is_sell or is_warn or limit_sell) and not is_ok:
            sell_list.append(stock_code)
    print("开始写入数据 buy_list: ", buy_list)
    write_stocks(C.need_buy_file, buy_list)
    print("开始写入数据 sell_list: ", sell_list)
    write_stocks(C.need_sell_file, sell_list)


def init(C):
    C.account = ACCOUNT
    C.need_buy_file = r'C:\Users\Farmar\Desktop\需持有股票.txt'
    C.need_sell_file = r'C:\Users\Farmar\Desktop\需卖出股票.txt'
    C.run_time("my_handlebar", "3nSecond", "2023-06-20 13:20:00")


def my_handlebar(C):
    calc_today_police(C)
