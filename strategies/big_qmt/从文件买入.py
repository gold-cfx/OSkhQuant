# encoding:gbk
# �����ı��еĹ�Ʊ������ֲֹ�Ʊû���ı��������������̺������ծ��ع�
import datetime
from enum import Enum

eps = 0.0000001
accID = '27113139'
stock_code_sh = '204001.SH'
stock_code_sz = '131810.SZ'
flag_use_reverse_repo = True  # �����Ƿ�ʹ����ع�
want_keep_money = 0  # ��Ҫ�����ģ�����ڶ���ȡ��
ORDER_CACHE = r'C:\\Users\\Farmar\\Desktop\\������¼.txt'


class EntrustStatus(Enum):
    """
    ί��״̬ö���ࣨ��Ӧ enum_EEntrustStatus��
    """
    ENTRUST_STATUS_WAIT_REPORTING = 49  # ����
    ENTRUST_STATUS_REPORTED = 50  # �ѱ����ѱ�������̨�����ɽ���
    ENTRUST_STATUS_REPORTED_CANCEL = 51  # �ѱ����������ѱ�״̬��ί�г������ȴ���̨����������
    ENTRUST_STATUS_PARTSUCC_CANCEL = 52  # ���ɴ������Ѳ��ֳɽ���ʣ�ಿ�ֳ���������
    ENTRUST_STATUS_PART_CANCEL = 53  # ���������ֳɽ��󳷵���
    ENTRUST_STATUS_CANCELED = 54  # �ѳ�����ȫ������
    ENTRUST_STATUS_PART_SUCC = 55  # ���ɣ����ֳɽ���
    ENTRUST_STATUS_SUCCEEDED = 56  # �ѳɣ���ȫ�ɽ���
    ENTRUST_STATUS_JUNK = 57  # �ϵ���ί����Ч��ԭ����ϵ�ԭ���ֶΣ�


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
    C.need_buy_file = r'C:\Users\Farmar\Desktop\����й�Ʊ.txt'


def init(C):
    print('start')
    init_data(C)

    # �ʽ��˺�
    C.account = accID
    C.set_account(C.account)
    C.keep_money = want_keep_money  # �������������ʱ�򣬾Ͳ����н�����
    C.buy_one_stock_money = 50000  # ��һ����Ʊ�ĵ���������ֵ
    C.cancelled_orders = set()

    print("init finished")
    C.run_time("myHandlebar", "3nSecond", "2023-06-20 13:20:00")


def is_st_stock(tscode, tsname):
    print(tscode, tsname)
    cond = ["st" in tsname, "ST" in tsname]
    return any(cond)


def is_sci_board(tscode):  # �ж������Ʊ�ı���ǲ��ǿƴ���
    if len(tscode) < 3:
        return False
    return str(tscode).startswith('688')


def update_user_stock_status(C):
    for i in range(0, C.today_stock_list_len):
        if C.stock_status[i] == StockStatus.ST_STOCK.value:
            continue
        C.stock_status[i] = StockStatus.INIT.value
    # ��ͨ�˺�ί��
    order_list = get_trade_detail_data(C.account, 'stock', 'order')
    for order in order_list:
        order_code = order.m_strInstrumentID + '.' + order.m_strExchangeID  # ��ȡί�е���֤ȯ����

        if order.m_nOrderStatus != EntrustStatus.ENTRUST_STATUS_REPORTED.value:
            continue
        if order_code not in C.stock_dict:
            continue
        stock_index = C.stock_dict[order_code]['index']
        if C.stock_status[stock_index] == StockStatus.INIT.value:
            C.stock_status[stock_index] = StockStatus.IN_OLD_ORDER.value
    # ��ͨ�˺ųֲ�
    positions = get_trade_detail_data(C.account, 'stock', 'position')
    for dt in positions:
        stock_id = dt.m_strInstrumentID + '.' + dt.m_strExchangeID
        # print('��ǰ�гֲ�',stock_id)
        if stock_id not in C.stock_dict:
            continue
        stock_index = C.stock_dict[stock_id]['index']
        if C.stock_status[stock_index] == StockStatus.INIT.value:
            C.stock_status[stock_index] = StockStatus.IN_POSITIONS.value

    for i in range(0, C.today_stock_list_len):
        if C.stock_status[i] == StockStatus.INIT.value:
            if C.stock_buy_cnt[i] > 5:
                C.stock_status[i] = StockStatus.TOO_MANY_COUNT.value  # �µ�����̫���״̬


def read_stocks_from_txt(C):
    # ����ļ���λ��
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
    print('������Ƽ���:', C.today_stock_list)
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
            ordercode = order.m_strInstrumentID + '.' + order.m_strExchangeID  # ��ȡί�е���֤ȯ����
            dt = order.m_strInsertDate + ' ' + order.m_strInsertTime  # ί������+ί��ʱ��
            dt = datetime.datetime.strptime(dt, '%Y%m%d %H%M%S')  # ί������ʱ���ַ�������������ʱ�����
            now = datetime.datetime.now()  # ��ȡ��ǰ����ʱ��
            second = (now - dt).seconds  # ��ǰ����ʱ��-ί������ʱ��,��ȡ����ʱ���
            if second > 10 and order.m_strOrderSysID not in C.cancelled_orders:
                cancel_order_stock(C.account, order.m_strOrderSysID)
                print(f'{model}-������ͬ���', order.m_strOrderSysID, '��Ʊ����', ordercode,
                      order.m_strInstrumentName,
                      order.m_strOptName)
                C.cancelled_orders.add(order.m_strOrderSysID)

    stock_info = C.get_full_tick(C.today_stock_list)
    print(model, stock_info)
    accounts = get_trade_detail_data(C.account, 'stock', 'account')
    print(accounts)
    for dt in accounts:
        print(
            f'{model}-���ʲ�: {dt.m_dBalance:.2f}, ���ʲ�: {dt.m_dAssureAsset:.2f}, ����ֵ: {dt.m_dInstrumentValue:.2f}',
            f'�ܸ�ծ: {dt.m_dTotalDebit:.2f}, ���ý��: {dt.m_dAvailable:.2f}, ӯ��: {dt.m_dPositionProfit:.2f}')
        account_estimate_money = dt.m_dAvailable
        for i in range(0, C.today_stock_list_len):
            stock = C.today_stock_list[i]
            if account_estimate_money < C.keep_money:
                print(f'{model}-ʣ��Ǯ̫��')
                continue
            if C.stock_status[i] != StockStatus.INIT.value:
                print(f'{model}-�ù�ΪST������ί�л�����')
                continue

            if stock not in stock_info:
                print(f'{model}-�ùɲ���������ƻ���')
                continue
            open_price = stock_info[stock]['open']  # ���̼�
            last_price = stock_info[stock]['lastPrice']  # ���¼�
            bid_price = stock_info[stock]['bidPrice'][0]  # ί���
            bid_vol = stock_info[stock]['bidVol'][0]  # ί����
            #  ��ȡ��Ʊ�ſ�
            info = C.get_instrumentdetail(stock)
            up_stop_price = info['UpStopPrice']  # ������ͣ��
            down_stop_price = info['DownStopPrice']  # DownStopPrice
            stock_name = info['InstrumentName']  # ����
            print(f'{model}-', stock, stock_name, '���¼�', last_price, '��1��', bid_price, '��1��', bid_vol,
                  '��ͣ��', up_stop_price, '��ͣ��', down_stop_price)
            if model == OrderTType.jiao_yi:
                if last_price > open_price + eps:  # ������ڵļ۸�ȿ��̼۸ߣ��򲻿���
                    print(f'{model}-�ȿ��̸��ˣ�������')
                    continue
            if abs(last_price) < eps:
                last_price = bid_price
            if abs(last_price - down_stop_price) < eps:  # ������ڵļ۸��ǵ�ͣ�۸�
                print(f'{model}-��Ϊ��ͣ�ۣ�������')
                continue
            if abs(last_price - up_stop_price) < eps:  # ������ڵļ۸�����ͣ�۸�
                print(f'{model}-��Ϊ��ͣ�ۣ�������')
                continue
            if model == 't1':
                buy_price = min(int(last_price * 1.07) / 100.0, up_stop_price)
            else:
                buy_price = last_price
            if abs(buy_price) < eps:
                print(f'{model}-�۸�Ϊ0')
                continue
            buy_num = min(C.buy_one_stock_money, account_estimate_money) / (buy_price * 1.0002)
            buy_num = int(buy_num / 100) * 100
            if buy_num < 100:
                print(f'{model}-�����̫��')
                continue
            if is_sci_board(stock) and buy_num < 200:
                print(f'{model}-�����̫��,�ƴ�������200��')
                continue
            if buy_num < bid_vol * 10:
                write_order_info(23, stock, buy_num, buy_price)
                passorder(23, 1101, C.account, stock, 11, buy_price, buy_num, 2, C)
                account_estimate_money -= buy_num * buy_price * 1.0002
                C.stock_status[i] = StockStatus.IN_OLD_ORDER.value
                C.stock_buy_cnt[i] += 1
                print(f'{model}-�µ�', stock, stock_name, '�µ���', buy_price, '�µ���', buy_num,
                      'Ԥ��ʣ��Ǯ', account_estimate_money)
            else:
                print(f'{model}-��1��̫��')


def order_in_ni_hui_gou(C):
    # �����ع�����ʱ�䳤�ˣ���û�����򳷵�
    now = datetime.datetime.now()
    if '150100' <= now.strftime('%H%M%S') < '153000':
        order_list = get_trade_detail_data(C.account, 'stock', 'order')
        for order in order_list:
            if can_cancel_order(order.m_strOrderSysID, C.account, 'STOCK'):
                order_code = order.m_strInstrumentID + '.' + order.m_strExchangeID  # ��ȡί�е���֤ȯ����
                dt = order.m_strInsertDate + ' ' + order.m_strInsertTime  # ί������+ί��ʱ��
                dt = datetime.datetime.strptime(dt, '%Y%m%d %H%M%S')  # ί������ʱ���ַ�������������ʱ�����
                now = datetime.datetime.now()  # ��ȡ��ǰ����ʱ��
                second = (now - dt).seconds  # ��ǰ����ʱ��-ί������ʱ��,��ȡ����ʱ���
                if second > 10 and order.m_strOrderSysID not in C.cancelled_orders:
                    cancel_order_stock(C.account, order.m_strOrderSysID)
                    print('t3������ͬ���', order.m_strOrderSysID, '��Ʊ����', order_code, order.m_strInstrumentName,
                          order.m_strOptName)
                    C.cancelled_orders.add(order.m_strOrderSysID)
    if '151500' <= now.strftime('%H%M%S') < '153000':
        # ������ʽ�
        available_funds = get_trade_detail_data(accID, 'stock', 'account')[0].m_dAvailable
        available_funds = available_funds - C.keep_money * 1.0
        volume = int(available_funds / 1000) * 10
        if volume < 0:
            volume = 0
        print('������', available_funds)
        print('�ɽ�����ع�������', volume)
        if volume >= 10:
            # if True:
            # ����ع��۸�
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

            # �µ������µ���ʽ���˺š���Ĵ��롢�۸����͡��µ��۸��µ��������������ơ��Ƿ������ٷ��µ���ί��id��C
            write_order_info(24, stock_code, volume, buy5_price)
            passorder(24, 1101, accID, stock_code, 11, buy5_price * 0.9, volume, '', 2, '', C)
        else:
            print('�����ʽ��㣬������')


def myHandlebar(C):
    now_date = timetag_to_datetime(C.get_bar_timetag(C.barpos), '%Y-%m-%d %H:%M:%S')
    print(now_date)
    now = datetime.datetime.now()
    iso_weekday = datetime.datetime.now().isoweekday()
    if iso_weekday > 5:
        print('����ĩ', iso_weekday)
        # return
    print('��ǰʱ��', now.strftime('%H:%M:%S'))

    if '091500' <= now.strftime('%H%M%S') < '091510':
        init_data(C)
        print("data already clear")

    if not C.today_stock_list:
        # ���ĵ��ж������Ҫ���
        read_stocks_from_txt(C)

    # ���¹�Ʊ״̬
    update_user_stock_status(C)
    # ���̼��Ͼ��۽׶�
    if '092440' <= now.strftime('%H%M%S') <= '092457':
        order_in(C, OrderTType.ji_he_jing_jia)
    if '092500' < now.strftime('%H%M%S') < '092957':
        order_in(C, OrderTType.ji_he_cheng_jiao)
    if '093000' <= now.strftime('%H%M%S') < '094000':
        order_in(C, OrderTType.jiao_yi)
    # ��ع�
    if flag_use_reverse_repo:
        order_in_ni_hui_gou(C)
