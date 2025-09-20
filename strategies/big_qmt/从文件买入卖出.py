# encoding:gbk
# 从文本中的股票代码买入，持仓股票如果不在文本中的话就卖掉，其他逆回购功能
import datetime


# 全局配置参数
class Config:
    """交易配置类"""
    EPS = 0.0000001
    ACCOUNT_ID = '27113139'
    STOCK_CODE_SH = '204001.SH'
    STOCK_CODE_SZ = '131810.SZ'
    USE_REVERSE_REPO = True
    KEEP_MONEY = 0
    BUY_MONEY_PER_STOCK = 50000
    MAX_BUY_ATTEMPTS = 5

    # 文件路径配置
    ORDER_CACHE_FILE = r'C:\Users\Farmar\Desktop\订单记录.txt'
    BUY_STOCK_FILE = r'C:\Users\Farmar\Desktop\需持有股票.txt'
    SELL_STOCK_FILE = r'C:\Users\Farmar\Desktop\需卖出股票.txt'

    # 交易时间配置
    TRADING_SCHEDULES = [
        ('092440', '092457', '集合竞价'),
        ('092500', '092957', '集合成交'),
        ('093000', '150000', '交易时段'),
    ]

    # 逆回购时间范围
    REVERSE_REPO_TIME = ('151500', '153000')


class TradingStatus:
    """交易状态常量类"""
    # 委托状态
    ENTRUST_REPORTED = 50  # 已报（已报出到柜台，待成交）

    # 股票状态
    STOCK_SKIP = "忽略"
    STOCK_AVAILABLE = "可用"
    STOCK_IN_ORDER = "委托中"
    STOCK_IN_POSITION = "持仓中"

    # 订单类型
    ORDER_BUY = 23
    ORDER_SELL = 24


class TradingContext:
    """交易上下文管理类"""

    def __init__(self):
        self.buy_stocks = []  # 买入股票列表
        self.sell_stocks = []  # 卖出股票列表
        self.stock_info = {}  # 股票信息字典
        self.stock_status = []  # 股票状态列表
        self.buy_attempts = []  # 买入尝试次数
        self.cancelled_orders = set()  # 已取消订单集合
        self.account = Config.ACCOUNT_ID

    def reset(self):
        """重置所有数据"""
        self.buy_stocks.clear()
        self.sell_stocks.clear()
        self.stock_info.clear()
        self.stock_status.clear()
        self.buy_attempts.clear()

    def is_stock_available(self, index):
        """检查股票是否可买入"""
        return (index < len(self.stock_status) and
                self.stock_status[index] == TradingStatus.STOCK_AVAILABLE)

    def set_stock_status(self, stock_code, status):
        """设置股票状态"""
        if stock_code in self.stock_info:
            index = self.stock_info[stock_code]['index']
            if index < len(self.stock_status):
                self.stock_status[index] = status


class StockUtils:
    """股票工具类"""

    @staticmethod
    def is_st_stock(stock_code, stock_name):
        """判断是否为ST股票"""
        return "st" in stock_name.lower() if stock_name else False

    @staticmethod
    def is_sci_board(stock_code):
        """判断是否为科创板股票"""
        return len(stock_code) >= 3 and str(stock_code).startswith('688')

    @staticmethod
    def get_min_volume(stock_code):
        """获取最小交易量"""
        return 200 if StockUtils.is_sci_board(stock_code) else 100


class FileManager:
    """文件管理类"""

    @staticmethod
    def read_stock_file(file_path, stock_type="股票"):
        """读取股票文件"""
        stocks = []
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                for line in f:
                    stock_code = line.strip().split()[0] if line.strip() else None
                    if stock_code:
                        stocks.append(stock_code)
            print(f"读取{stock_type}文件成功: {len(stocks)}只股票")
        except FileNotFoundError:
            print(f"{stock_type}文件未找到: {file_path}")
        except Exception as e:
            print(f"读取{stock_type}文件出错: {e}")
        return stocks

    @staticmethod
    def write_order_log(order_type, stock_code, volume, price):
        """写入交易日志"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            log_text = f"{timestamp} {order_type} {stock_code} {volume} {price}"
            with open(Config.ORDER_CACHE_FILE, 'a', encoding='gbk') as f:
                f.write(f"{log_text}\n")
        except Exception as e:
            print(f"写入交易日志失败: {e}")


def load_stock_data(C, my_context):
    """加载股票数据"""
    # 读取买入和卖出股票列表
    my_context.buy_stocks = FileManager.read_stock_file(Config.BUY_STOCK_FILE, "买入股票")
    my_context.sell_stocks = FileManager.read_stock_file(Config.SELL_STOCK_FILE, "卖出股票")

    print(f"买入股票列表: {my_context.buy_stocks}")
    print(f"卖出股票列表: {my_context.sell_stocks}")

    # 初始化买入股票状态
    for i, stock_code in enumerate(my_context.buy_stocks):
        # 检查买卖冲突（卖出优先策略）
        if stock_code in my_context.sell_stocks:
            my_context.stock_status.append(TradingStatus.STOCK_SKIP)
            my_context.buy_attempts.append(0)
            my_context.stock_info[stock_code] = {'index': i, 'name': f"卖出优先-{stock_code}"}
            continue

        # 获取股票名称并检查ST股票
        stock_name = C.get_stock_name(stock_code)
        if StockUtils.is_st_stock(stock_code, stock_name):
            my_context.stock_status.append(TradingStatus.STOCK_SKIP)
        else:
            my_context.stock_status.append(TradingStatus.STOCK_AVAILABLE)

        my_context.buy_attempts.append(0)
        my_context.stock_info[stock_code] = {'index': i, 'name': stock_name}


def refresh_stock_status(my_context: TradingContext):
    """刷新股票状态"""
    # 重置非跳过状态的股票为可用状态
    for i, status in enumerate(my_context.stock_status):
        if status != TradingStatus.STOCK_SKIP:
            my_context.stock_status[i] = TradingStatus.STOCK_AVAILABLE

    # 更新委托状态
    try:
        print("开始查询委托状态")
        orders = get_trade_detail_data(my_context.account, 'stock', 'order')
        for order in orders:
            if order.m_nOrderStatus == TradingStatus.ENTRUST_REPORTED:
                stock_code = f"{order.m_strInstrumentID}.{order.m_strExchangeID}"
                my_context.set_stock_status(stock_code, TradingStatus.STOCK_IN_ORDER)
                print(f"{stock_code} 查询到委托订单")
    except Exception as e:
        print(f"获取委托信息失败: {e}")

    # 更新持仓状态
    try:
        print("开始查询持仓状态")
        positions = get_trade_detail_data(my_context.account, 'stock', 'position')
        for position in positions:
            stock_code = f"{position.m_strInstrumentID}.{position.m_strExchangeID}"
            my_context.set_stock_status(stock_code, TradingStatus.STOCK_IN_POSITION)
            print(f"{stock_code} 查询到持仓订单")
    except Exception as e:
        print(f"获取持仓信息失败: {e}")

    # 标记买入次数过多的股票
    for i, attempts in enumerate(my_context.buy_attempts):
        if attempts > Config.MAX_BUY_ATTEMPTS:
            my_context.stock_status[i] = TradingStatus.STOCK_SKIP
    print(f"刷新股票状态：{my_context.stock_status}")


class OrderManager:
    """订单管理类"""

    @staticmethod
    def cancel_timeout_orders(my_context: TradingContext, trading_phase):
        """取消超时订单"""
        if trading_phase != "交易时段":
            return

        try:
            print("开始查询超时订单")
            orders = get_trade_detail_data(my_context.account, 'stock', 'order')
            current_time = datetime.datetime.now()

            for order in orders:
                if not can_cancel_order(order.m_strOrderSysID, my_context.account, 'STOCK'):
                    continue

                order_time = datetime.datetime.strptime(
                    f"{order.m_strInsertDate} {order.m_strInsertTime}", '%Y%m%d %H%M%S'
                )

                if ((current_time - order_time).seconds > 10 and
                        order.m_strOrderSysID not in my_context.cancelled_orders):
                    cancel_order_stock(my_context.account, order.m_strOrderSysID)
                    my_context.cancelled_orders.add(order.m_strOrderSysID)
                    print(f"取消超时订单: {order.m_strOrderSysID}")

        except Exception as e:
            print(f"取消订单失败: {e}")

    @staticmethod
    def calculate_buy_price(last_price, up_stop_price, trading_phase):
        """计算买入价格"""
        if trading_phase == "集合竞价":
            return min(last_price * 1.07, up_stop_price)
        return last_price


class TradingValidator:
    """交易验证类"""

    @staticmethod
    def validate_buy_condition(C, stock_code, stock_info, trading_phase):
        """验证买入条件"""
        open_price = stock_info.get('open', 0)
        last_price = stock_info.get('lastPrice', 0)

        # 基本价格检查
        if abs(last_price) < Config.EPS:
            return False, "价格异常"

        # 获取涨跌停价格
        try:
            instrument_info = C.get_instrumentdetail(stock_code)
            up_stop = instrument_info['UpStopPrice']
            down_stop = instrument_info['DownStopPrice']

            if abs(last_price - down_stop) < Config.EPS:
                return False, "跌停"
            if abs(last_price - up_stop) < Config.EPS:
                return False, "涨停"
        except:
            pass

        # 交易时段特殊验证
        if trading_phase == "交易时段" and last_price > open_price + Config.EPS:
            return False, "高开"

        return True, "验证通过"


def execute_buy_order(C, my_context, stock_code, stock_info, trading_phase, available_money):
    """执行买入订单"""
    try:
        last_price = stock_info['lastPrice']  # 最新价
        bid_price = stock_info['bidPrice'][0]  # 委买价
        bid_vol = stock_info['bidVol'][0]  # 委买量
        ask_price = stock_info['askPrice'][0]  # 委卖价
        ask_vol = stock_info['askVol'][0]  # 委卖价

        if abs(last_price) < Config.EPS:
            last_price = bid_price

        info = C.get_instrumentdetail(stock_code)
        up_stop_price = info['UpStopPrice']
        buy_price = OrderManager.calculate_buy_price(last_price, up_stop_price, trading_phase)

        # 计算买入数量
        max_money = min(Config.BUY_MONEY_PER_STOCK, available_money)
        buy_num = int(max_money / (buy_price * 1.0002) / 100) * 100

        # 检查最小买入量
        min_volume = StockUtils.get_min_volume(stock_code)
        if buy_num < min_volume:
            return False, available_money, "买入量不足"

        # 检查委托量
        if buy_num >= ask_vol * 100 * 10:
            return False, available_money, f"委托量过大: buy_num: {buy_num}, bid_vol: {bid_vol}"

        # 执行买入
        FileManager.write_order_log(TradingStatus.ORDER_BUY, stock_code, buy_num, buy_price)
        passorder(TradingStatus.ORDER_BUY, 1101, my_context.account, stock_code, 11, buy_price, buy_num, 2, C)

        # 更新状态
        stock_index = my_context.stock_info[stock_code]['index']
        my_context.stock_status[stock_index] = TradingStatus.STOCK_IN_ORDER
        my_context.buy_attempts[stock_index] += 1

        new_available_money = available_money - buy_num * buy_price * 1.0002
        print(f"买入成功: {stock_code} 价格:{buy_price} 数量:{buy_num}")
        return True, new_available_money, "买入成功"

    except Exception as e:
        return False, available_money, f"买入失败: {e}"


def process_sell_orders(C, my_context):
    """处理卖出订单（优先执行）"""
    if not my_context.sell_stocks:
        return

    try:
        # 获取当前持仓
        positions = get_trade_detail_data(my_context.account, 'stock', 'position')
        if not positions:
            print("没有持仓信息，暂停卖出！")
            return

        print(f"开始处理卖出订单，卖出列表: {my_context.sell_stocks}")

        for position in positions:
            stock_code = f"{position.m_strInstrumentID}.{position.m_strExchangeID}"
            available_volume = position.m_nCanUseVolume  # 可用数量

            # 检查是否在卖出列表中
            if stock_code in my_context.sell_stocks and available_volume > 0:
                try:
                    # 执行卖出订单
                    FileManager.write_order_log(TradingStatus.ORDER_SELL, stock_code, available_volume, 0)
                    passorder(TradingStatus.ORDER_SELL, 1101, my_context.account, stock_code, 5, 0, available_volume, 2,
                              C)
                    print(f"卖出成功: {stock_code} 数量: {available_volume}")

                except Exception as e:
                    print(f"卖出失败: {stock_code} 错误: {e}")

    except Exception as e:
        print(f"处理卖出订单出错: {e}")


def process_stock_orders(C, my_context, trading_phase):
    """处理股票买入订单"""
    try:
        # 取消旧订单
        OrderManager.cancel_timeout_orders(my_context, trading_phase)

        # 获取股票信息和账户信息
        stock_info = C.get_full_tick(my_context.buy_stocks)
        accounts = get_trade_detail_data(my_context.account, 'stock', 'account')

        if not accounts:
            return

        available_money = accounts[0].m_dAvailable
        print(f"{trading_phase} - 可用资金: {available_money:.2f}")

        # 遍历股票列表进行买入
        for i, stock_code in enumerate(my_context.buy_stocks):
            if available_money < Config.KEEP_MONEY:
                print(f"{trading_phase} - 资金不足")
                break

            if not my_context.is_stock_available(i):
                print(f"{stock_code} 股票状态不可用，跳过买入")
                continue

            if stock_code not in stock_info:
                print(f"{stock_code} 没查到价格信息")
                continue

            # 检查买入条件
            print("开始买入")
            valid, reason = TradingValidator.validate_buy_condition(C, stock_code, stock_info[stock_code],
                                                                    trading_phase)
            if not valid:
                print(f"{trading_phase} - {stock_code} {reason}")
                continue

            # 执行买入
            success, available_money, message = execute_buy_order(
                C, my_context, stock_code, stock_info[stock_code], trading_phase, available_money
            )
            print(f"{trading_phase} - {stock_code} {message}")

    except Exception as e:
        print(f"处理股票订单出错: {e}")


def process_reverse_repo(C, my_context):
    """处理逆回购"""
    if not Config.USE_REVERSE_REPO:
        return

    current_time = datetime.datetime.now().strftime('%H%M%S')

    # 在逆回购时间范围内执行
    if Config.REVERSE_REPO_TIME[0] <= current_time < Config.REVERSE_REPO_TIME[1]:
        try:
            accounts = get_trade_detail_data(Config.ACCOUNT_ID, 'stock', 'account')
            if not accounts:
                return

            available_funds = accounts[0].m_dAvailable - Config.KEEP_MONEY
            volume = int(available_funds / 1000) * 10

            if volume >= 10:
                # 选择收益率更高的逆回购
                sh_data = C.get_market_data_ex(['quoter'], stock_code=[Config.STOCK_CODE_SH],
                                               period='tick', dividend_type='none')
                sz_data = C.get_market_data_ex(['quoter'], stock_code=[Config.STOCK_CODE_SZ],
                                               period='tick', dividend_type='none')

                if sh_data['lastPrice'] > sz_data['lastPrice']:
                    stock_code = Config.STOCK_CODE_SH
                    buy_price = sh_data['bidPrice'][-1]
                else:
                    stock_code = Config.STOCK_CODE_SZ
                    buy_price = sz_data['bidPrice'][-1]

                FileManager.write_order_log(TradingStatus.ORDER_SELL, stock_code, volume, buy_price)
                passorder(TradingStatus.ORDER_SELL, 1101, Config.ACCOUNT_ID, stock_code, 11,
                          buy_price * 0.9, volume, '', 2, '', C)
                print(f"逆回购成功: {stock_code} 数量:{volume}")
        except Exception as e:
            print(f"逆回购处理失败: {e}")


def init(C):
    """系统初始化"""
    print('策略启动')
    C.my_context = TradingContext()
    C.my_context.reset()
    C.set_account(C.my_context.account)
    print("初始化完成")
    C.run_time("myHandlebar", "3nSecond", "2023-06-20 13:20:00")


def myHandlebar(C):
    """主处理函数"""
    now = datetime.datetime.now()
    current_time = now.strftime('%H%M%S')

    # 周末不交易
    if now.isoweekday() > 5:
        return
    print("")
    print("*************************************")
    print(f'当前时间: {now.strftime("%H:%M:%S")}')

    # 每日数据初始化
    if '091500' <= current_time < '091510':
        if hasattr(C, 'my_context'):
            C.my_context.reset()
        print("数据已重置")

    # 确保有交易上下文
    if not hasattr(C, 'my_context'):
        C.my_context = TradingContext()

    # 读取股票列表（只在第一次或重置后执行）
    if not C.my_context.buy_stocks and not C.my_context.sell_stocks:
        print("开始读取股票数据")
        load_stock_data(C, C.my_context)

    # 更新股票状态
    print("开始刷新股票状态")
    refresh_stock_status(C.my_context)

    # 优先执行卖出逻辑（在交易时间内）
    if '093000' <= current_time <= '150000':
        print("开始卖出交易")
        process_sell_orders(C, C.my_context)

    # 根据时间段执行不同的交易策略（买入）
    for start_time, end_time, trading_phase in Config.TRADING_SCHEDULES:
        if start_time <= current_time <= end_time:
            print(f"开始买入交易：{trading_phase}")
            process_stock_orders(C, C.my_context, trading_phase)
            break

    # 处理逆回购
    process_reverse_repo(C, C.my_context)
