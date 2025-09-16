# encoding:gbk
# 买入文本中的股票，如果持仓股票没在文本中则卖出，收盘后买入国债逆回购
import datetime
from enum import Enum

eps = 0.0000001
accID = '27113139'
stock_code_sh = '204001.SH'
stock_code_sz = '131810.SZ'
flag_use_reverse_repo = True  # 控制是否使用逆回购
want_keep_money = 0  # 想要保留的，方便第二天取出
ORDER_CACHE = r'C:\\Users\\Farmar\\Desktop\\订单记录.txt'


class EntrustStatus(Enum):
    """
    委托状态枚举类（对应 enum_EEntrustStatus）
    """
    ENTRUST_STATUS_WAIT_REPORTING = 49  # 待报
    ENTRUST_STATUS_REPORTED = 50  # 已报（已报出到柜台，待成交）
    ENTRUST_STATUS_REPORTED_CANCEL = 51  # 已报待撤（对已报状态的委托撤单，等待柜台处理撤单请求）
    ENTRUST_STATUS_PARTSUCC_CANCEL = 52  # 部成待撤（已部分成交，剩余部分撤单待处理）
    ENTRUST_STATUS_PART_CANCEL = 53  # 部撤（部分成交后撤单）
    ENTRUST_STATUS_CANCELED = 54  # 已撤（完全撤单）
    ENTRUST_STATUS_PART_SUCC = 55  # 部成（部分成交）
    ENTRUST_STATUS_SUCCEEDED = 56  # 已成（完全成交）
    ENTRUST_STATUS_JUNK = 57  # 废单（委托无效，原因见废单原因字段）


class StockStatus(Enum):
    TOO_MANY_COUNT = -2
    ST_STOCK = -1
    INIT = 0
    IN_OLD_ORDER = 3
    IN_POSITIONS = 4


class OrderTType(Enum):
    ji_he_jing_jia = "t1"
    ji_he_cheng_jiao = "t2"
    jiao_yi = "t3"


def init_data(C):
    C.today_stock_list = []
    C.today_stock_list_len = 0
    C.stock_dict = {}
    C.stock_status = []
    C.stock_buy_cnt = []
    C.need_buy_file = r'C:\Users\Farmar\Desktop\需持有股票.txt'


def init(C):
    print('start')
    init_data(C)

    # 资金账号
    C.account = accID
    C.set_account(C.account)
    C.keep_money = want_keep_money  # 当少于这个金额的时候，就不进行交易了
    C.buy_one_stock_money = 50000  # 买一个股票的单笔期望数值
    C.cancelled_orders = set()

    print("init finished")
    C.run_time("myHandlebar", "3nSecond", "2023-06-20 13:20:00")


def is_st_stock(tscode, tsname):
    print(tscode, tsname)
    cond = ["st" in tsname, "ST" in tsname]
    return any(cond)


def is_sci_board(tscode):  # 判断这个股票的编号是不是科创版
    if len(tscode) < 3:
        return False
    return str(tscode).startswith('688')


def update_user_stock_status(C):
    for i in range(0, C.today_stock_list_len):
        if C.stock_status[i] == StockStatus.ST_STOCK.value:
            continue
        C.stock_status[i] = StockStatus.INIT.value
    # 普通账号委托
    order_list = get_trade_detail_data(C.account, 'stock', 'order')
    for order in order_list:
        order_code = order.m_strInstrumentID + '.' + order.m_strExchangeID  # 获取委托单的证券代码

        if order.m_nOrderStatus != EntrustStatus.ENTRUST_STATUS_REPORTED.value:
            continue
        if order_code not in C.stock_dict:
            continue
        stock_index = C.stock_dict[order_code]['index']
        if C.stock_status[stock_index] == StockStatus.INIT.value:
            C.stock_status[stock_index] = StockStatus.IN_OLD_ORDER.value
    # 普通账号持仓
    positions = get_trade_detail_data(C.account, 'stock', 'position')
    for dt in positions:
        stock_id = dt.m_strInstrumentID + '.' + dt.m_strExchangeID
        # print('当前有持仓',stock_id)
        if stock_id not in C.stock_dict:
            continue
        stock_index = C.stock_dict[stock_id]['index']
        if C.stock_status[stock_index] == StockStatus.INIT.value:
            C.stock_status[stock_index] = StockStatus.IN_POSITIONS.value

    for i in range(0, C.today_stock_list_len):
        if C.stock_status[i] == StockStatus.INIT.value:
            if C.stock_buy_cnt[i] > 5:
                C.stock_status[i] = StockStatus.TOO_MANY_COUNT.value  # 下单次数太多的状态


def read_stocks_from_txt(C):
    # 你的文件单位置
    with open(C.need_buy_file, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            line = line.strip()
            one_stock_info = line.split()
            C.today_stock_list.append(one_stock_info[0])

    C.today_stock_list_len = len(C.today_stock_list)
    for i in range(0, C.today_stock_list_len):
        C.stock_status.append(StockStatus.INIT.value)
        C.stock_buy_cnt.append(0)
        this_stock_name = C.get_stock_name(C.today_stock_list[i])
        C.stock_dict[C.today_stock_list[i]] = {'index': i, "name": this_stock_name}
        if is_st_stock(C.today_stock_list[i], this_stock_name):
            C.stock_status[i] = StockStatus.ST_STOCK.value

    update_user_stock_status(C)
    print('今天的推荐表:', C.today_stock_list)
    print(C.stock_status)


def write_order(text):
    with open(ORDER_CACHE, 'a') as f:
        f.write(f"{text}\n")


def write_order_info(order_type, code, volume, price):
    now = datetime.datetime.now()
    write_order(f"{now.strftime('%Y%m%d-%H%M%S')} {order_type} {code} {volume} {price}")


def order_in(C, model):
    if model == OrderTType.jiao_yi:
        order_list = get_trade_detail_data(C.account, 'stock', 'order')
        for order in order_list:
            if not can_cancel_order(order.m_strOrderSysID, C.account, 'STOCK'):
                continue
            ordercode = order.m_strInstrumentID + '.' + order.m_strExchangeID  # 获取委托单的证券代码
            dt = order.m_strInsertDate + ' ' + order.m_strInsertTime  # 委托日期+委托时间
            dt = datetime.datetime.strptime(dt, '%Y%m%d %H%M%S')  # 委托日期时间字符串解析成日期时间对象
            now = datetime.datetime.now()  # 获取当前日期时间
            second = (now - dt).seconds  # 当前日期时间-委托日期时间,获取秒数时间差
            if second > 10 and order.m_strOrderSysID not in C.cancelled_orders:
                cancel_order_stock(C.account, order.m_strOrderSysID)
                print(f'{model}-撤单合同编号', order.m_strOrderSysID, '股票代码', ordercode,
                      order.m_strInstrumentName,
                      order.m_strOptName)
                C.cancelled_orders.add(order.m_strOrderSysID)

    stock_info = C.get_full_tick(C.today_stock_list)
    print(model, stock_info)
    accounts = get_trade_detail_data(C.account, 'stock', 'account')
    print(accounts)
    for dt in accounts:
        print(
            f'{model}-总资产: {dt.m_dBalance:.2f}, 净资产: {dt.m_dAssureAsset:.2f}, 总市值: {dt.m_dInstrumentValue:.2f}',
            f'总负债: {dt.m_dTotalDebit:.2f}, 可用金额: {dt.m_dAvailable:.2f}, 盈亏: {dt.m_dPositionProfit:.2f}')
        account_estimate_money = dt.m_dAvailable
        for i in range(0, C.today_stock_list_len):
            stock = C.today_stock_list[i]
            if account_estimate_money < C.keep_money:
                print(f'{model}-剩余钱太少')
                continue
            if C.stock_status[i] != StockStatus.INIT.value:
                print(f'{model}-该股为ST或者已委托或买入')
                continue

            if stock not in stock_info:
                print(f'{model}-该股不存在买入计划表')
                continue
            open_price = stock_info[stock]['open']  # 开盘价
            last_price = stock_info[stock]['lastPrice']  # 最新价
            bid_price = stock_info[stock]['bidPrice'][0]  # 委买价
            bid_vol = stock_info[stock]['bidVol'][0]  # 委买量
            #  获取股票概况
            info = C.get_instrumentdetail(stock)
            up_stop_price = info['UpStopPrice']  # 当日涨停价
            down_stop_price = info['DownStopPrice']  # DownStopPrice
            stock_name = info['InstrumentName']  # 名称
            print(f'{model}-', stock, stock_name, '最新价', last_price, '买1价', bid_price, '买1量', bid_vol,
                  '涨停价', up_stop_price, '跌停价', down_stop_price)
            if model == OrderTType.jiao_yi:
                if last_price > open_price + eps:  # 如果现在的价格比开盘价高，则不考虑
                    print(f'{model}-比开盘高了，不考虑')
                    continue
            if abs(last_price) < eps:
                last_price = bid_price
            if abs(last_price - down_stop_price) < eps:  # 如果现在的价格是跌停价格
                print(f'{model}-现为跌停价，不考虑')
                continue
            if abs(last_price - up_stop_price) < eps:  # 如果现在的价格是涨停价格
                print(f'{model}-现为涨停价，不考虑')
                continue
            if model == 't1':
                buy_price = min(int(last_price * 1.07) / 100.0, up_stop_price)
            else:
                buy_price = last_price
            if abs(buy_price) < eps:
                print(f'{model}-价格为0')
                continue
            buy_num = min(C.buy_one_stock_money, account_estimate_money) / (buy_price * 1.0002)
            buy_num = int(buy_num / 100) * 100
            if buy_num < 100:
                print(f'{model}-能买的太少')
                continue
            if is_sci_board(stock) and buy_num < 200:
                print(f'{model}-能买的太少,科创板至少200股')
                continue
            if buy_num < bid_vol * 10:
                write_order_info(23, stock, buy_num, buy_price)
                passorder(23, 1101, C.account, stock, 11, buy_price, buy_num, 2, C)
                account_estimate_money -= buy_num * buy_price * 1.0002
                C.stock_status[i] = StockStatus.IN_OLD_ORDER.value
                C.stock_buy_cnt[i] += 1
                print(f'{model}-下单', stock, stock_name, '下单价', buy_price, '下单量', buy_num,
                      '预估剩余钱', account_estimate_money)
            else:
                print(f'{model}-买1量太少')


def order_in_ni_hui_gou(C):
    # 如果逆回购单子时间长了，还没处理，则撤单
    now = datetime.datetime.now()
    if '150100' <= now.strftime('%H%M%S') < '153000':
        order_list = get_trade_detail_data(C.account, 'stock', 'order')
        for order in order_list:
            if can_cancel_order(order.m_strOrderSysID, C.account, 'STOCK'):
                order_code = order.m_strInstrumentID + '.' + order.m_strExchangeID  # 获取委托单的证券代码
                dt = order.m_strInsertDate + ' ' + order.m_strInsertTime  # 委托日期+委托时间
                dt = datetime.datetime.strptime(dt, '%Y%m%d %H%M%S')  # 委托日期时间字符串解析成日期时间对象
                now = datetime.datetime.now()  # 获取当前日期时间
                second = (now - dt).seconds  # 当前日期时间-委托日期时间,获取秒数时间差
                if second > 10 and order.m_strOrderSysID not in C.cancelled_orders:
                    cancel_order_stock(C.account, order.m_strOrderSysID)
                    print('t3撤单合同编号', order.m_strOrderSysID, '股票代码', order_code, order.m_strInstrumentName,
                          order.m_strOptName)
                    C.cancelled_orders.add(order.m_strOrderSysID)
    if '151500' <= now.strftime('%H%M%S') < '153000':
        # 查可用资金
        available_funds = get_trade_detail_data(accID, 'stock', 'account')[0].m_dAvailable
        available_funds = available_funds - C.keep_money * 1.0
        volume = int(available_funds / 1000) * 10
        if volume < 0:
            volume = 0
        print('可用余额：', available_funds)
        print('可交易逆回购数量：', volume)
        if volume >= 10:
            # if True:
            # 查逆回购价格
            sh01_result = C.get_market_data_ex(['quoter'], stock_code=[stock_code_sh], start_time='',
                                               end_time='', period='tick', dividend_type='none')
            sh01_buy5_price = sh01_result['bidPrice'][-1]
            sh01_last_price = sh01_result['lastPrice']
            print(sh01_result, sh01_buy5_price, sh01_last_price)

            sz01_result = C.get_market_data_ex(['quoter'], stock_code=[stock_code_sz], start_time='',
                                               end_time='', period='tick', dividend_type='none')
            sz01_buy5_price = sz01_result['bidPrice'][-1]
            sz01_last_price = sz01_result['lastPrice']
            print(sz01_result, sz01_buy5_price, sz01_last_price)

            if sh01_last_price > sz01_last_price:
                stock_code = stock_code_sh
                buy5_price = sh01_buy5_price
                print('buy sh 01')
            else:
                stock_code = stock_code_sz
                buy5_price = sz01_buy5_price
                print('buy sz 01')

            # 下单方向、下单方式、账号、标的代码、价格类型、下单价格、下单数量、策略名称、是否立即促发下单、委托id、C
            write_order_info(24, stock_code, volume, buy5_price)
            passorder(24, 1101, accID, stock_code, 11, buy5_price * 0.9, volume, '', 2, '', C)
        else:
            print('可用资金不足，不交易')


def myHandlebar(C):
    now_date = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y-%m-%d %H:%M:%S')
    print(now_date)
    now = datetime.datetime.now()
    iso_weekday = datetime.datetime.now().isoweekday()
    if iso_weekday > 5:
        print('是周末', iso_weekday)
        # return
    print('当前时间', now.strftime('%H:%M:%S'))

    if '091500' <= now.strftime('%H%M%S') < '091510':
        init_data(C)
        print("data already clear")

    if not C.today_stock_list:
        # 从文档中读入今天要买的
        read_stocks_from_txt(C)

    # 更新股票状态
    update_user_stock_status(C)
    # 早盘集合竞价阶段
    if '092440' <= now.strftime('%H%M%S') <= '092457':
        order_in(C, OrderTType.ji_he_jing_jia)
    if '092500' < now.strftime('%H%M%S') < '092957':
        order_in(C, OrderTType.ji_he_cheng_jiao)
    if '093000' <= now.strftime('%H%M%S') < '094000':
        order_in(C, OrderTType.jiao_yi)
    # 逆回购
    if flag_use_reverse_repo:
        order_in_ni_hui_gou(C)
