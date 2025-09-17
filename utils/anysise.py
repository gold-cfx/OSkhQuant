import os

import matplotlib.pyplot as plt
import pandas as pd

from large_money import calc_large_money_and_sell


def scan_stocks(data_dir=r"C:\Farmar\data\khlh", fast=5, slow=60, x=1.5):
    results = {}
    # 加个进度条
    for fname in os.listdir(data_dir):
        if not fname.endswith(".csv"):
            continue
        code = fname[:9]
        df = pd.read_csv(os.path.join(data_dir, fname))
        df = calc_large_money_and_sell("", df, fast=fast, slow=slow, x=x)
        results[code] = df[0]
    return results


# 定义计算未来 N 天涨幅的函数
def calc_future_return(df, n):
    df = df.copy()
    df['future_close'] = df['close'].shift(-n)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']
    return df


# 定义最大回撤计算函数
def max_drawdown(series):
    cumulative = (1 + series).cumprod()
    peak = cumulative.expanding().max()
    drawdown = (peak - cumulative) / peak
    return drawdown.max()


def calc_sell_future_return(df, n):
    # 初始化新列
    df['future_date'] = None
    df['future_return'] = None
    df['sell_desc'] = None

    # 遍历数据
    len_df = len(df)
    for i in range(len_df):
        if df.at[i, 'is_ok']:
            # 检查后续数据中的卖出条件
            buy_index = i + 1
            for j in range(i + 1, min(i + n, len_df)):
                if df.at[j, 'is_sell'] or df.at[j, 'is_warn'] or df.at[j, 'limit_sell']:
                    sell_index = j + 1
                    if sell_index >= len_df:
                        break

                    df.at[i, 'future_date'] = df.at[sell_index, 'date']
                    df.at[i, 'future_return'] = (df.at[sell_index, 'open'] - df.at[buy_index, 'open']) / df.at[
                        buy_index, 'open']
                    df.at[i, 'sell_desc'] = "触发sell" if not df.at[j, 'limit_sell'] else "触发:limit"
                    break
                else:
                    # 如果损失超过5%也可以卖出
                    pass
    return df


def calc_large_money_arg(fast, slow, x):
    # 遍历每个 DataFrame
    dfs = scan_stocks(fast=fast, slow=slow, x=x)
    # 初始化结果存储
    fin_re = []
    for n in range(5, 61):
        result_records = []
        path = f"C:\\Farmar\\data\\cfx\\{n}_khlh"
        if not os.path.exists(path):
            os.mkdir(path)
        for stock_code, df in dfs.items():
            # df = calc_future_return(df, n=n)
            df = calc_sell_future_return(df, n=n)

            signal_df: pd.DataFrame = df[df['is_ok'] == True].copy()

            if signal_df.empty:
                continue  # 如果没有信号，跳过
            # signal_df.to_csv(f"C:\\Farmar\\data\\cfx\\{n}_khlh\\{stock_code}.csv")
            win_rate = (signal_df['future_return'] > 0).mean()

            signal_df['cumulative_return'] = (1 + signal_df['future_return']).cumprod()

            # 最终收益率
            final_return = signal_df['cumulative_return'].iloc[-1] - 1

            # 计算最大回撤
            cummax = signal_df['cumulative_return'].cummax()
            drawdown = (signal_df['cumulative_return'] - cummax) / cummax
            max_drawdown = drawdown.min()

            result_records.append({
                'stock_code': stock_code,
                'final_return': final_return * 100,
                'win_rate': win_rate * 100,
                'max_drawdown': max_drawdown * 100,
                'signal_count': len(signal_df)
            })

            # 转换为 DataFrame 查看汇总结果
        result_df = pd.DataFrame(result_records)
        # result_df.to_csv(f"C:\\Farmar\\data\\cfx\\{n}_khlh\\result_return_detail.csv")
        print()
        print(f"{n}_平均收益", result_df['final_return'].mean())
        print(f"{n}_平均成功率", result_df['win_rate'].mean())
        print(f"{n}_平均最大回撤", result_df['max_drawdown'].mean())
        fin_re.append({
            'day': n,
            "平均收益": result_df['final_return'].mean(),
            "平均成功率": result_df['win_rate'].mean(),
            "平均最大回撤": result_df['max_drawdown'].mean(),
        })

        # with open(f"C:\\Farmar\\data\\cfx\\{n}_khlh\\result.txt", 'w') as f:
        #     f.writelines(
        #         [
        #             f"{n}_平均收益: {result_df['final_return'].mean()}\n\r",
        #             f"{n}_平均成功率: {result_df['win_rate'].mean()}\n\r",
        #             f"{n}_平均最大回撤: {result_df['max_drawdown'].mean()}\n\r"
        #         ]
        #     )
    _df = pd.DataFrame(fin_re)
    test_file_path = rf"C:\Farmar\data\cfx\{fast}_{slow}_{x}_test_large_money.csv"
    _df.to_csv(test_file_path)
    show(test_file_path)


def show(file_path):
    # 读取上传的CSV文件
    df = pd.read_csv(file_path)

    # 显示数据的前几行以了解其结构
    df.head()
    # 绘制柱状图和折线图
    fig, ax1 = plt.subplots()

    # 柱状图：平均成功率和平均最大回撤
    ax1.bar(df['day'], df['平均成功率'], color='b', alpha=0.6, label='success_rate')
    ax1.bar(df['day'], df['平均最大回撤'], color='r', alpha=0.6, label='huiche_rate')

    # 设置图表标题和坐标轴标签
    ax1.set_title('策略表现随天数变化')
    ax1.set_xlabel('天数')
    ax1.set_ylabel('平均成功率和平均最大回撤')

    # 添加图例
    ax1.legend(loc='upper left')

    # 第二坐标轴：平均收益
    ax2 = ax1.twinx()
    ax2.plot(df['day'], df['平均收益'], color='g', marker='o', label='rate')
    ax2.set_ylabel('平均收益')

    # 添加图例
    ax2.legend(loc='upper right')

    # 显示图表
    plt.show()


if __name__ == '__main__':
    calc_large_money_arg(fast=5, slow=60, x=1.5)
