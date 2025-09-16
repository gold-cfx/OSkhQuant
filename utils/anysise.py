import os

import pandas as pd
import tqdm

from utils.base import find_strategy_signals


def scan_stocks(data_dir="data/1d", lookback=60):
    results = {}
    # 加个进度条
    for fname in tqdm(os.listdir(data_dir), desc="扫描股票数据"):
        if not fname.endswith(".feather"):
            continue
        code = fname.replace(".feather", "")
        df = pd.read_feather(os.path.join(data_dir, fname))
        df = hq.calc_limit_up_down(df, code)
        # 查找最近1年出现过信号的所有股票
        signals = find_strategy_signals(df, lookback)
        if signals:
            results[code] = signals
    return results


if __name__ == "__main__":
    # 下载数据
    hq.down_load_sector()
    hq.get_stock_pool()
    hq.download_his(perid='1d', incrementally=True)
    hq.data_to_feather(period='1d', start_time='20200101')

    # 开始选股 查找最近250个K线是否出现过这样的图形
    res = scan_stocks(r"data/1d", lookback=250)
    for code, sigs in res.items():
        for s in sigs:
            print(f"股票 {code} 出现信号， 突破日期: {s['date']}, 突破日收盘价: {s['signal_price']}")
