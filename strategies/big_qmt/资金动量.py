# encoding:gbk
import datetime
import re

import numpy as np
import pandas as pd

# ======================== ���޸����� ========================

ACCOUNT = "27113139"


# ===========================================================
def get_klines(C, code_list: list, n: int = 365, start_time=None):
    """ȡ��� n �������յ����̼�����"""
    if not start_time:
        now = datetime.datetime.now()
        # ����n��ǰ������
        target_date = now - datetime.timedelta(days=n)
        # ��ʽ��Ϊ YYYYMMDD ��ʽ
        start_time = target_date.strftime("%Y%m%d")
    else:
        start_time = start_time.strftime("%Y%m%d")

    print(f"===��ʼ������ʷ���ݣ� start_time = {start_time}")

    data = C.get_market_data_ex([], code_list, period='1d', start_time=start_time, end_time='',
                                dividend_type="front", fill_data=True, subscribe=True)
    result = {}
    for stock_code, stock_data in data.items():
        # ����ʱ����
        if 'time' in stock_data.columns:
            # ת��ʱ����
            stock_data['time'] = pd.to_datetime(stock_data['time'].astype(float), unit='ms') + pd.Timedelta(hours=8)

            mask = stock_data['time'].dt.date < datetime.datetime.now().date()

            stock_data = stock_data[mask]

            # ��ʱ������
            stock_data = stock_data.sort_values('time').reset_index(drop=True)
        result[stock_code] = stock_data

    return result


def is_stock(code):
    code = code[:6]
    pattern = r'^(600|601|603|605|688|000|001|002|003|300|301|836|920)\d{3}$'
    return bool(re.match(pattern, str(code)))


def write_stocks(file_path, list_stocks):
    with open(file_path, 'a') as f:
        for stock_code in list_stocks:
            f.write(f"{stock_code}\r\n")


def run_once_successfully(func):
    """
    װ������ȷ�������ɹ�ִ��һ��
    ���ִ��ʧ�ܣ��׳��쳣�������´ε���ʱ����ִ��
    """
    memo = {}  # �洢����ִ�н�����쳣״̬

    def wrapper(*args, **kwargs):
        if func in memo:
            # ����Ѿ��ɹ�ִ�й���ֱ�ӷ��ؽ��
            if not isinstance(memo[func], Exception):
                return memo[func]
            # ���֮ǰִ��ʧ�ܣ�����ִ�к���

        try:
            result = func(*args, **kwargs)
            memo[func] = result  # �洢�ɹ����
            return result
        except Exception as e:
            memo[func] = e  # �洢�쳣���´ε��ü�������
            raise  # �׳��쳣����������ֹ�´ε���

    return wrapper


def calc_large_money(C, code, df, fast=5, slow=60, x=1.5, fast_power_t=250, slow_power_t=3000):
    """
    ��2025��1.1-9.16ȫ�����ݲ��ԣ������ǲ�λ���ʽ�
    ���ѡ��5��60��1.3�Ĳ����������źź�����
    �ֲ�34-37�죬����290%���س�3.7%��ʤ��33%
    �ֲ�50-54�죬����420%���س�2.6%��ʤ��25%

    ���ѡ��5��60��1.5�Ĳ����������źź�����
    �ֲ�56��ƽ������ 10006%���س�1.9%��ʤ��23%

    ���ѡ��5��60��1.8�Ĳ����������źź�����
    �ֲ�56��ƽ������ 2540%���س�1.6%��ʤ��22%

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
                # Ĭ��ʮ�ڹ�
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
    # ��������
    df['slow_power_threshold'] = np.maximum(fast_power_t, df['ma_fast_cash_flow_power'] * x)

    cond1 = df['slow_day_cash_flow'] > 0
    cond2 = df['slow_cash_flow_power'] <= slow_power_t
    cond3 = df['fast_day_cash_flow'] < 0
    cond4 = df['fast_cash_flow_power'].abs() > df["slow_power_threshold"]

    df['is_ok'] = cond1 & cond2 & cond3 & cond4

    return df, df['is_ok'].values[-1]


def calc_large_money_and_sell(C, code, df, fast=5, slow=60, x=1.5):
    """
    ��2025��1.1-9.16ȫ�����ݲ��ԣ������ǲ�λ���ʽ�
    ���ѡ��5��60��1.3�Ĳ����������źź�����
    �ֲ�34-36�죬����160%���س�3.3%��ʤ��39%
    �ֲ�58-60�죬����160%���س�2.3%��ʤ��33%

    ���ѡ��5��60��1.5�Ĳ����������źź�����
    �ֲ�36�죬����140%���س�2.6%��ʤ��37%

    ���ѡ��5��60��1.8�Ĳ����������źź�����
    �ֲ�55�죬����99%���س�1.4%��ʤ��30%
    """
    df, _ = calc_large_money(C, code, df, fast, slow, x)
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

    return df


def calc_large_money_and_sell_and_limit(C, code, df, fast=5, slow=60, x=1.5, n=34):
    df = calc_large_money_and_sell(C, code, df, fast=fast, slow=slow, x=x)
    df['date'] = df['time'].dt.strftime('%y-%m-%d')
    df['limit_day'] = None
    queue = []  # ����ÿ�� is_ok �ĵ�������
    len_df = len(df)
    for i in range(len_df):
        if df.at[i, 'is_ok']:
            # ������� N ������
            add_day = df.iloc[i + 1:i + n]['is_ok'].sum()
            expire = (i + n + add_day, df.at[i, 'date'])
            queue.append(expire)
    for item in queue:
        if item[0] >= len_df:
            continue
        df.at[item[0], 'limit_day'] = item[1]
    return df, df['is_ok'].values[-1], df['limit_day'].values[-1]


@run_once_successfully
def calc_today_police(C):
    print("��ʼִ�й�Ʊɸѡ")
    position_list: pd.DataFrame = get_trade_detail_data(ACCOUNT, 'STOCK', 'position')
    all_stocks = {f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list}
    print(f"�鵽���гֲ���Ϣ��{all_stocks}")
    position_info = {
        f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list if
        is_stock(o.m_strInstrumentID) and o.m_nVolume > 100
    }
    print("��Ʊ�ֲ���Ϣ��", position_info)
    C.position_info = position_info
    C.stock_list = C.get_stock_list_in_sector("����300")  # ��ȡ����300��Ʊ�б�
    all_stock_list = list(position_info.keys()) + C.stock_list
    C.history_data = get_klines(C, all_stock_list)

    print("��ʼ����ָ��")
    buy_list, sell_list = [], []
    for stock_code, df in C.history_data.items():
        _, buy, sell = calc_large_money_and_sell_and_limit(C, stock_code, df, x=1.5, n=35)
        if buy and stock_code not in position_list:
            buy_list.append(stock_code)
        elif stock_code in position_list and sell:
            sell_list.append(stock_code)
    print("��ʼд������ buy_list: ", buy_list)
    write_stocks(C.need_buy_file, buy_list)
    print("��ʼд������ sell_list: ", sell_list)
    write_stocks(C.need_sell_file, sell_list)


def init(C):
    C.account = ACCOUNT
    C.need_buy_file = r'C:\Users\Farmar\Desktop\����й�Ʊ.txt'
    C.need_sell_file = r'C:\Users\Farmar\Desktop\��������Ʊ.txt'
    C.run_time("my_handlebar", "3nSecond", "2023-06-20 13:20:00")


def my_handlebar(C):
    # todo ��Ʊ̫�࣬���Ը�����ֵ���۸���ѡ
    calc_today_police(C)
