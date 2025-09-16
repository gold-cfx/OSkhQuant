# encoding:gbk
import datetime as dt
import json
import os
import re
from collections import deque
from enum import Enum

import numpy as np  # ← NumPy 核心库
import pandas as pd

# ======================== 可修改区域 ========================
VOL_HALF_CACHE = r'C:\\Users\\Farmar\\Desktop\\近1年波动率的四分之一.json'
ORDER_CACHE = r'C:\\Users\\Farmar\\Desktop\\订单记录.txt'
ACCOUNT = "27113139"


# ===========================================================
def get_klines(C, code: str, n: int = 365, start_time=None) -> pd.Series:
    """取最近 n 个交易日的收盘价序列"""
    if not start_time:
        now = dt.datetime.now()
        # 计算n天前的日期
        target_date = now - dt.timedelta(days=n)
        # 格式化为 YYYYMMDD 格式
        start_time = target_date.strftime("%Y%m%d")
    else:
        start_time = start_time.strftime("%Y%m%d")
    k = C.get_market_data_ex([], [code], period='1d', start_time=start_time, end_time='')
    k = k[code]
    if k is None:
        raise RuntimeError(f'{code} 本地 K 线不足')
    return pd.Series(k['close'].values, index=pd.to_datetime(k['time'], unit='ms'))


def calc_vol_half(close: pd.Series) -> float:
    """
    给定收盘价序列，返回年化波动率的一半
    每一步都用 NumPy，下面逐行拆解：
    """

    # 1) np.log —— 对收盘价做对数收益率
    #    close / close.shift(1) 得到 1 日价格相对变动
    #    再取自然对数 ln(x)，使得分布更接近正态，方差更稳定
    log_ret = np.log(np.array(close) / np.array(close.shift(1)))

    # 2) .dropna() 去掉首行 NaN（shift 导致的）
    log_ret = log_ret[~np.isnan(log_ret)]

    # 3) np.std —— 计算样本标准差
    #    ddof=1 表示除以 n-1（样本标准差，更贴近真实波动）
    daily_vol = np.std(log_ret, ddof=1)

    # 4) 年化波动率 = 日波动 * sqrt(252)
    #    250 是一年的交易日近似值
    annual_vol = daily_vol * np.sqrt(250)

    # 5) 取一半
    return annual_vol / 4


def load_vol_half(C, code: str) -> float:
    """先读缓存，没有再算并写入缓存"""
    cache = {}
    today = dt.date.today().isoformat()
    if os.path.exists(VOL_HALF_CACHE):
        with open(VOL_HALF_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        if cache.get(today) and code in cache[today]:
            return float(cache[today][code])

    # 缓存失效，重新计算
    print("开始计算")
    close = get_klines(C, code)
    vol_half = calc_vol_half(close)
    if today in cache and type(cache[today]) == dict:
        cache[today][code] = vol_half
    else:
        cache = {today: {code: vol_half}}
    print(cache)
    with open(VOL_HALF_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f)
    return vol_half


def is_stock(code):
    code = code[:6]
    pattern = r'^(600|601|603|605|688|000|001|002|003|300|301|836|920)\d{3}$'
    return bool(re.match(pattern, str(code)))


def get_order_time(C, code):
    order_info = get_latest_order_info(23, code)
    if order_info:
        return order_info['timestamp'], order_info['price']
    print(f"{code}-没找到最新成交记录")
    return None, None


def should_sell(C, code: str, vol_half: float) -> bool:
    """True → 立即平仓"""
    tick = C.get_full_tick([code])
    if not tick:
        print("没查到最新tick数据")
        return False, None

    tick = tick[code]
    last_price = tick['lastPrice']
    order_time, order_price = get_order_time(C, code)
    if not order_time or not order_price:
        return False, None
    print(f"{code} 查到订单信息，order_time：{order_time}， {order_price}")
    # 1) 取买入后最高价：用 NumPy 的 max 计算
    klines = get_klines(C, code, 30, order_time)
    #    如果记录了买入日期，可改成 .loc[买入日期:]，这里简化为全部
    high_since_buy = np.max(klines.values)
    if order_time:
        print(f"{code} 从{order_time}至今最高价为：{high_since_buy}, 成本价为：{order_price}， 最新价为：{last_price}")
    else:
        print(f"{code} 近30天最高价为：{high_since_buy}， 成本价为：{order_price}， 最新价为：{last_price}")
    # 2) 回撤计算：NumPy 标量运算即可
    drawdown = (high_since_buy - last_price) / high_since_buy

    # 3) 亏损计算：同样用 NumPy 标量
    loss = (order_price - last_price) / order_price
    # print(drawdown, vol_half, loss)
    # 4) 任一满足即卖出
    if np.logical_or(drawdown >= vol_half, loss >= 0.05):
        print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] "
              f"{code} 触发卖出：回撤={drawdown:.2%} 亏损={loss:.2%}")
        return True, last_price
    else:
        print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] "
              f"{code} 盈利信息：回撤={drawdown:.2%} 盈利={abs(loss):.2%}")
    return False, None


def init(C):
    position_list: pd.DataFrame = get_trade_detail_data(ACCOUNT, 'STOCK', 'position')
    all_stocks = {f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list}
    print(f"查到所有持仓信息：{all_stocks}")
    position_info = {
        f"{o.m_strInstrumentID}.{o.m_strExchangeID}": o.m_nVolume for o in position_list if
        is_stock(o.m_strInstrumentID) and o.m_nVolume > 100
    }
    print("股票持仓信息：", position_info)
    C.position_info = position_info
    C.account = ACCOUNT
    C.run_time("my_handlebar", "3nSecond", "2023-06-20 13:20:00")


class OrderTType(Enum):
    success = "success"
    cancel = "cancel"
    wait = "wait"
    notfound = "notfound"


def check_order(C, stock_code):
    order_list = get_trade_detail_data(C.account, 'stock', 'order')
    for order in order_list:
        ordercode = order.m_strInstrumentID + '.' + order.m_strExchangeID  # 获取委托单的证券代码
        if ordercode == stock_code:
            dt_time = order.m_strInsertDate + ' ' + order.m_strInsertTime  # 委托日期+委托时间
            dt_time = dt.datetime.strptime(dt_time, '%Y%m%d %H%M%S')  # 委托日期时间字符串解析成日期时间对象
            now = dt.datetime.now()  # 获取当前日期时间
            second = (now - dt_time).seconds  # 当前日期时间-委托日期时间,获取秒数时间差
            if order.m_nVolumeTraded >= 0:
                return OrderTType.success.value
            if not can_cancel_order(order.m_strOrderSysID, C.account, 'STOCK'):
                return OrderTType.success.value
            if second > 10:
                cancel_order_stock(C.account, order.m_strOrderSysID)
                print(f'撤单合同编号', order.m_strOrderSysID, '股票代码', ordercode,
                      order.m_strInstrumentName,
                      order.m_strOptName)
                return OrderTType.cancel.value
            else:
                return OrderTType.wait.value
        continue
    return OrderTType.notfound.value


def write_order(text):
    with open(ORDER_CACHE, 'a') as f:
        f.write(f"{text}\r\n")


def write_order_info(order_type, code, volume, price):
    now = dt.datetime.now()
    write_order(f"{now.strftime('%Y%m%d-%H%M%S')} {order_type} {code} {volume} {price}")


def read_file_backwards(file_name, max_line=1000):
    with open(file_name, 'r', encoding='utf-8') as file:
        lines = deque(file, max_line)  # 1000是缓冲区大小，可以根据需要调整
        lines.reverse()
        return lines


def get_latest_order_info(order_type, code):
    if not os.path.exists(ORDER_CACHE):
        return {}
    lines = read_file_backwards(ORDER_CACHE)
    for line in lines:
        if f'{order_type} {code}' in line:
            order_info = parse_log_line(line)
            return order_info
    return {}


def parse_log_line(line):
    parts = line.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid log line format: {line}")

    # 解析时间部分
    time_str = parts[0]
    try:
        timestamp = dt.datetime.strptime(time_str, "%Y%m%d-%H%M%S")
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {time_str}") from e

    order_type = parts[1]
    code = parts[2]
    volume = int(parts[3])
    price = float(parts[4])

    return {
        "timestamp": timestamp,
        "order_type": order_type,
        "code": code,
        "volume": volume,
        "price": price
    }


def my_handlebar(C):
    for stock_code, vol in C.position_info.items():
        vol_half = load_vol_half(C, stock_code)
        if np.isnan(vol_half):
            continue
        print(f"{stock_code} 近一年波动率/4 = {vol_half:.2%}")
        now = dt.datetime.now()
        if '093000' <= now.strftime('%H%M%S') < '155900':
            sell, last_price = should_sell(C, stock_code, vol_half)
            if sell and last_price:
                check_order_type = check_order(C, stock_code)
                print(f"查询委托：check_order_type={check_order_type}")
                if check_order_type in [OrderTType.cancel.value, OrderTType.notfound.value]:
                    print(f"{stock_code} 触发卖出策略")
                    sell_vol = int(vol / 100) * 100
                    write_order_info(24, stock_code, sell_vol, last_price)
                    passorder(24, 1101, C.account, stock_code, 5, 0, sell_vol, 2, C)
                    print(f"{stock_code}卖出成功，sell_vol：{sell_vol}， last_price：{last_price}")
