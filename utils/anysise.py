import os

import numpy as np
import pandas as pd

from large_money import calc_large_money


def scan_stocks(data_dir=r"C:\Farmar\data\khlh"):
    results = {}
    # 加个进度条
    for fname in os.listdir(data_dir):
        if not fname.endswith(".csv"):
            continue
        code = fname[:9]
        df = pd.read_csv(os.path.join(data_dir, fname))
        df, _ = calc_large_money("", df, fast=5, slow=60, x=1.3)
        results[code] = df
    return results


# 定义计算未来 N 天涨幅的函数
def calc_future_return(df, N=10):
    df = df.copy()
    df['future_close'] = df['close'].shift(-N)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']
    return df


# 定义最大回撤计算函数
def max_drawdown(series):
    cumulative = (1 + series).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (peak - cumulative) / peak
    return drawdown.max()


def calc_large_money_arg():
    # 遍历每个 DataFrame
    dfs = scan_stocks()
    # 初始化结果存储
    fin_re = []
    for n in range(5, 60):
        result_records = []
        path = f"C:\\Farmar\\data\\cfx\\{n}_khlh"
        if not os.path.exists(path):
            os.mkdir(path)
        for stock_code, df in dfs.items():
            df = calc_future_return(df, N=n)
            signal_df: pd.DataFrame = df[df['is_ok'] == True].copy()

            if signal_df.empty:
                continue  # 如果没有信号，跳过
            signal_df.to_csv(f"C:\\Farmar\\data\\cfx\\{n}_khlh\\{stock_code}.csv")
            avg_return = signal_df['future_return'].mean()
            win_rate = (signal_df['future_return'] > 0).mean()

            # 计算每个信号点后 N 天的最大回撤
            drawdowns = []
            for idx, row in signal_df.iterrows():
                end_idx = idx + n
                if end_idx >= len(df):
                    continue
                future_returns = df.loc[idx + 1:end_idx, 'future_return']
                drawdowns.append(max_drawdown(future_returns))

            avg_drawdown = np.mean(drawdowns) if drawdowns else np.nan

            result_records.append({
                'stock_code': stock_code,
                'avg_return': avg_return * 100,
                'win_rate': win_rate * 100,
                'avg_max_drawdown': avg_drawdown * 100,
                'signal_count': len(signal_df)
            })

        # 转换为 DataFrame 查看汇总结果
        result_df = pd.DataFrame(result_records)
        result_df.to_csv(f"C:\\Farmar\\data\\cfx\\{n}_khlh\\result_detail.csv")
        print()
        print(f"{n}_平均收益", result_df['avg_return'].mean())
        print(f"{n}_平均成功率", result_df['win_rate'].mean())
        print(f"{n}_平均最大回撤", result_df['avg_max_drawdown'].mean())
        fin_re.append({
            'day': n,
            **result_records
        })

        with open(f"C:\\Farmar\\data\\{n}_khlh\\result.txt", 'w') as f:
            f.writelines(
                [
                    f"{n}_平均收益: {result_df['avg_return'].mean()}\n\r",
                    f"{n}_平均成功率: {result_df['win_rate'].mean()}\n\r",
                    f"{n}_平均最大回撤: {result_df['avg_max_drawdown'].mean()}\n\r"
                ]
            )
    _df = pd.DataFrame(fin_re)
    _df.to_csv(r"C:\Farmar\data\cfx\5_60_1.3_test_large_money.csv")


if __name__ == '__main__':
    calc_large_money_arg()
