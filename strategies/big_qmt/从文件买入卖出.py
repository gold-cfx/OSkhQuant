# encoding:gbk
# ���ı��еĹ�Ʊ�������룬�ֲֹ�Ʊ��������ı��еĻ���������������ع�����
import datetime


# ȫ�����ò���
class Config:
    """����������"""
    EPS = 0.0000001
    ACCOUNT_ID = '27113139'
    STOCK_CODE_SH = '204001.SH'
    STOCK_CODE_SZ = '131810.SZ'
    USE_REVERSE_REPO = True
    KEEP_MONEY = 0
    BUY_MONEY_PER_STOCK = 50000
    MAX_BUY_ATTEMPTS = 5

    # �ļ�·������
    ORDER_CACHE_FILE = r'C:\Users\Farmar\Desktop\������¼.txt'
    BUY_STOCK_FILE = r'C:\Users\Farmar\Desktop\����й�Ʊ.txt'
    SELL_STOCK_FILE = r'C:\Users\Farmar\Desktop\��������Ʊ.txt'

    # ����ʱ������
    TRADING_SCHEDULES = [
        ('092440', '092457', '���Ͼ���'),
        ('092500', '092957', '���ϳɽ�'),
        ('093000', '150000', '����ʱ��'),
    ]

    # ��ع�ʱ�䷶Χ
    REVERSE_REPO_TIME = ('151500', '153000')


class TradingStatus:
    """����״̬������"""
    # ί��״̬
    ENTRUST_REPORTED = 50  # �ѱ����ѱ�������̨�����ɽ���

    # ��Ʊ״̬
    STOCK_SKIP = "����"
    STOCK_AVAILABLE = "����"
    STOCK_IN_ORDER = "ί����"
    STOCK_IN_POSITION = "�ֲ���"

    # ��������
    ORDER_BUY = 23
    ORDER_SELL = 24


class TradingContext:
    """���������Ĺ�����"""

    def __init__(self):
        self.buy_stocks = []  # �����Ʊ�б�
        self.sell_stocks = []  # ������Ʊ�б�
        self.stock_info = {}  # ��Ʊ��Ϣ�ֵ�
        self.stock_status = []  # ��Ʊ״̬�б�
        self.buy_attempts = []  # ���볢�Դ���
        self.cancelled_orders = set()  # ��ȡ����������
        self.account = Config.ACCOUNT_ID

    def reset(self):
        """������������"""
        self.buy_stocks.clear()
        self.sell_stocks.clear()
        self.stock_info.clear()
        self.stock_status.clear()
        self.buy_attempts.clear()

    def is_stock_available(self, index):
        """����Ʊ�Ƿ������"""
        return (index < len(self.stock_status) and
                self.stock_status[index] == TradingStatus.STOCK_AVAILABLE)

    def set_stock_status(self, stock_code, status):
        """���ù�Ʊ״̬"""
        if stock_code in self.stock_info:
            index = self.stock_info[stock_code]['index']
            if index < len(self.stock_status):
                self.stock_status[index] = status


class StockUtils:
    """��Ʊ������"""

    @staticmethod
    def is_st_stock(stock_code, stock_name):
        """�ж��Ƿ�ΪST��Ʊ"""
        return "st" in stock_name.lower() if stock_name else False

    @staticmethod
    def is_sci_board(stock_code):
        """�ж��Ƿ�Ϊ�ƴ����Ʊ"""
        return len(stock_code) >= 3 and str(stock_code).startswith('688')

    @staticmethod
    def get_min_volume(stock_code):
        """��ȡ��С������"""
        return 200 if StockUtils.is_sci_board(stock_code) else 100


class FileManager:
    """�ļ�������"""

    @staticmethod
    def read_stock_file(file_path, stock_type="��Ʊ"):
        """��ȡ��Ʊ�ļ�"""
        stocks = []
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                for line in f:
                    stock_code = line.strip().split()[0] if line.strip() else None
                    if stock_code:
                        stocks.append(stock_code)
            print(f"��ȡ{stock_type}�ļ��ɹ�: {len(stocks)}ֻ��Ʊ")
        except FileNotFoundError:
            print(f"{stock_type}�ļ�δ�ҵ�: {file_path}")
        except Exception as e:
            print(f"��ȡ{stock_type}�ļ�����: {e}")
        return stocks

    @staticmethod
    def write_order_log(order_type, stock_code, volume, price):
        """д�뽻����־"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            log_text = f"{timestamp} {order_type} {stock_code} {volume} {price}"
            with open(Config.ORDER_CACHE_FILE, 'a', encoding='gbk') as f:
                f.write(f"{log_text}\n")
        except Exception as e:
            print(f"д�뽻����־ʧ��: {e}")


def load_stock_data(C, my_context):
    """���ع�Ʊ����"""
    # ��ȡ�����������Ʊ�б�
    my_context.buy_stocks = FileManager.read_stock_file(Config.BUY_STOCK_FILE, "�����Ʊ")
    my_context.sell_stocks = FileManager.read_stock_file(Config.SELL_STOCK_FILE, "������Ʊ")

    print(f"�����Ʊ�б�: {my_context.buy_stocks}")
    print(f"������Ʊ�б�: {my_context.sell_stocks}")

    # ��ʼ�������Ʊ״̬
    for i, stock_code in enumerate(my_context.buy_stocks):
        # ���������ͻ���������Ȳ��ԣ�
        if stock_code in my_context.sell_stocks:
            my_context.stock_status.append(TradingStatus.STOCK_SKIP)
            my_context.buy_attempts.append(0)
            my_context.stock_info[stock_code] = {'index': i, 'name': f"��������-{stock_code}"}
            continue

        # ��ȡ��Ʊ���Ʋ����ST��Ʊ
        stock_name = C.get_stock_name(stock_code)
        if StockUtils.is_st_stock(stock_code, stock_name):
            my_context.stock_status.append(TradingStatus.STOCK_SKIP)
        else:
            my_context.stock_status.append(TradingStatus.STOCK_AVAILABLE)

        my_context.buy_attempts.append(0)
        my_context.stock_info[stock_code] = {'index': i, 'name': stock_name}


def refresh_stock_status(my_context: TradingContext):
    """ˢ�¹�Ʊ״̬"""
    # ���÷�����״̬�Ĺ�ƱΪ����״̬
    for i, status in enumerate(my_context.stock_status):
        if status != TradingStatus.STOCK_SKIP:
            my_context.stock_status[i] = TradingStatus.STOCK_AVAILABLE

    # ����ί��״̬
    try:
        print("��ʼ��ѯί��״̬")
        orders = get_trade_detail_data(my_context.account, 'stock', 'order')
        for order in orders:
            if order.m_nOrderStatus == TradingStatus.ENTRUST_REPORTED:
                stock_code = f"{order.m_strInstrumentID}.{order.m_strExchangeID}"
                my_context.set_stock_status(stock_code, TradingStatus.STOCK_IN_ORDER)
                print(f"{stock_code} ��ѯ��ί�ж���")
    except Exception as e:
        print(f"��ȡί����Ϣʧ��: {e}")

    # ���³ֲ�״̬
    try:
        print("��ʼ��ѯ�ֲ�״̬")
        positions = get_trade_detail_data(my_context.account, 'stock', 'position')
        for position in positions:
            stock_code = f"{position.m_strInstrumentID}.{position.m_strExchangeID}"
            my_context.set_stock_status(stock_code, TradingStatus.STOCK_IN_POSITION)
            print(f"{stock_code} ��ѯ���ֲֶ���")
    except Exception as e:
        print(f"��ȡ�ֲ���Ϣʧ��: {e}")

    # ��������������Ĺ�Ʊ
    for i, attempts in enumerate(my_context.buy_attempts):
        if attempts > Config.MAX_BUY_ATTEMPTS:
            my_context.stock_status[i] = TradingStatus.STOCK_SKIP
    print(f"ˢ�¹�Ʊ״̬��{my_context.stock_status}")


class OrderManager:
    """����������"""

    @staticmethod
    def cancel_timeout_orders(my_context: TradingContext, trading_phase):
        """ȡ����ʱ����"""
        if trading_phase != "����ʱ��":
            return

        try:
            print("��ʼ��ѯ��ʱ����")
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
                    print(f"ȡ����ʱ����: {order.m_strOrderSysID}")

        except Exception as e:
            print(f"ȡ������ʧ��: {e}")

    @staticmethod
    def calculate_buy_price(last_price, up_stop_price, trading_phase):
        """��������۸�"""
        if trading_phase == "���Ͼ���":
            return min(last_price * 1.07, up_stop_price)
        return last_price


class TradingValidator:
    """������֤��"""

    @staticmethod
    def validate_buy_condition(C, stock_code, stock_info, trading_phase):
        """��֤��������"""
        open_price = stock_info.get('open', 0)
        last_price = stock_info.get('lastPrice', 0)

        # �����۸���
        if abs(last_price) < Config.EPS:
            return False, "�۸��쳣"

        # ��ȡ�ǵ�ͣ�۸�
        try:
            instrument_info = C.get_instrumentdetail(stock_code)
            up_stop = instrument_info['UpStopPrice']
            down_stop = instrument_info['DownStopPrice']

            if abs(last_price - down_stop) < Config.EPS:
                return False, "��ͣ"
            if abs(last_price - up_stop) < Config.EPS:
                return False, "��ͣ"
        except:
            pass

        # ����ʱ��������֤
        if trading_phase == "����ʱ��" and last_price > open_price + Config.EPS:
            return False, "�߿�"

        return True, "��֤ͨ��"


def execute_buy_order(C, my_context, stock_code, stock_info, trading_phase, available_money):
    """ִ�����붩��"""
    try:
        last_price = stock_info['lastPrice']  # ���¼�
        bid_price = stock_info['bidPrice'][0]  # ί���
        bid_vol = stock_info['bidVol'][0]  # ί����
        ask_price = stock_info['askPrice'][0]  # ί����
        ask_vol = stock_info['askVol'][0]  # ί����

        if abs(last_price) < Config.EPS:
            last_price = bid_price

        info = C.get_instrumentdetail(stock_code)
        up_stop_price = info['UpStopPrice']
        buy_price = OrderManager.calculate_buy_price(last_price, up_stop_price, trading_phase)

        # ������������
        max_money = min(Config.BUY_MONEY_PER_STOCK, available_money)
        buy_num = int(max_money / (buy_price * 1.0002) / 100) * 100

        # �����С������
        min_volume = StockUtils.get_min_volume(stock_code)
        if buy_num < min_volume:
            return False, available_money, "����������"

        # ���ί����
        if buy_num >= ask_vol * 100 * 10:
            return False, available_money, f"ί��������: buy_num: {buy_num}, bid_vol: {bid_vol}"

        # ִ������
        FileManager.write_order_log(TradingStatus.ORDER_BUY, stock_code, buy_num, buy_price)
        passorder(TradingStatus.ORDER_BUY, 1101, my_context.account, stock_code, 11, buy_price, buy_num, 2, C)

        # ����״̬
        stock_index = my_context.stock_info[stock_code]['index']
        my_context.stock_status[stock_index] = TradingStatus.STOCK_IN_ORDER
        my_context.buy_attempts[stock_index] += 1

        new_available_money = available_money - buy_num * buy_price * 1.0002
        print(f"����ɹ�: {stock_code} �۸�:{buy_price} ����:{buy_num}")
        return True, new_available_money, "����ɹ�"

    except Exception as e:
        return False, available_money, f"����ʧ��: {e}"


def process_sell_orders(C, my_context):
    """������������������ִ�У�"""
    if not my_context.sell_stocks:
        return

    try:
        # ��ȡ��ǰ�ֲ�
        positions = get_trade_detail_data(my_context.account, 'stock', 'position')
        if not positions:
            print("û�гֲ���Ϣ����ͣ������")
            return

        print(f"��ʼ�������������������б�: {my_context.sell_stocks}")

        for position in positions:
            stock_code = f"{position.m_strInstrumentID}.{position.m_strExchangeID}"
            available_volume = position.m_nCanUseVolume  # ��������

            # ����Ƿ��������б���
            if stock_code in my_context.sell_stocks and available_volume > 0:
                try:
                    # ִ����������
                    FileManager.write_order_log(TradingStatus.ORDER_SELL, stock_code, available_volume, 0)
                    passorder(TradingStatus.ORDER_SELL, 1101, my_context.account, stock_code, 5, 0, available_volume, 2,
                              C)
                    print(f"�����ɹ�: {stock_code} ����: {available_volume}")

                except Exception as e:
                    print(f"����ʧ��: {stock_code} ����: {e}")

    except Exception as e:
        print(f"����������������: {e}")


def process_stock_orders(C, my_context, trading_phase):
    """�����Ʊ���붩��"""
    try:
        # ȡ���ɶ���
        OrderManager.cancel_timeout_orders(my_context, trading_phase)

        # ��ȡ��Ʊ��Ϣ���˻���Ϣ
        stock_info = C.get_full_tick(my_context.buy_stocks)
        accounts = get_trade_detail_data(my_context.account, 'stock', 'account')

        if not accounts:
            return

        available_money = accounts[0].m_dAvailable
        print(f"{trading_phase} - �����ʽ�: {available_money:.2f}")

        # ������Ʊ�б��������
        for i, stock_code in enumerate(my_context.buy_stocks):
            if available_money < Config.KEEP_MONEY:
                print(f"{trading_phase} - �ʽ���")
                break

            if not my_context.is_stock_available(i):
                print(f"{stock_code} ��Ʊ״̬�����ã���������")
                continue

            if stock_code not in stock_info:
                print(f"{stock_code} û�鵽�۸���Ϣ")
                continue

            # �����������
            print("��ʼ����")
            valid, reason = TradingValidator.validate_buy_condition(C, stock_code, stock_info[stock_code],
                                                                    trading_phase)
            if not valid:
                print(f"{trading_phase} - {stock_code} {reason}")
                continue

            # ִ������
            success, available_money, message = execute_buy_order(
                C, my_context, stock_code, stock_info[stock_code], trading_phase, available_money
            )
            print(f"{trading_phase} - {stock_code} {message}")

    except Exception as e:
        print(f"�����Ʊ��������: {e}")


def process_reverse_repo(C, my_context):
    """������ع�"""
    if not Config.USE_REVERSE_REPO:
        return

    current_time = datetime.datetime.now().strftime('%H%M%S')

    # ����ع�ʱ�䷶Χ��ִ��
    if Config.REVERSE_REPO_TIME[0] <= current_time < Config.REVERSE_REPO_TIME[1]:
        try:
            accounts = get_trade_detail_data(Config.ACCOUNT_ID, 'stock', 'account')
            if not accounts:
                return

            available_funds = accounts[0].m_dAvailable - Config.KEEP_MONEY
            volume = int(available_funds / 1000) * 10

            if volume >= 10:
                # ѡ�������ʸ��ߵ���ع�
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
                print(f"��ع��ɹ�: {stock_code} ����:{volume}")
        except Exception as e:
            print(f"��ع�����ʧ��: {e}")


def init(C):
    """ϵͳ��ʼ��"""
    print('��������')
    C.my_context = TradingContext()
    C.my_context.reset()
    C.set_account(C.my_context.account)
    print("��ʼ�����")
    C.run_time("myHandlebar", "3nSecond", "2023-06-20 13:20:00")


def myHandlebar(C):
    """��������"""
    now = datetime.datetime.now()
    current_time = now.strftime('%H%M%S')

    # ��ĩ������
    if now.isoweekday() > 5:
        return
    print("")
    print("*************************************")
    print(f'��ǰʱ��: {now.strftime("%H:%M:%S")}')

    # ÿ�����ݳ�ʼ��
    if '091500' <= current_time < '091510':
        if hasattr(C, 'my_context'):
            C.my_context.reset()
        print("����������")

    # ȷ���н���������
    if not hasattr(C, 'my_context'):
        C.my_context = TradingContext()

    # ��ȡ��Ʊ�б�ֻ�ڵ�һ�λ����ú�ִ�У�
    if not C.my_context.buy_stocks and not C.my_context.sell_stocks:
        print("��ʼ��ȡ��Ʊ����")
        load_stock_data(C, C.my_context)

    # ���¹�Ʊ״̬
    print("��ʼˢ�¹�Ʊ״̬")
    refresh_stock_status(C.my_context)

    # ����ִ�������߼����ڽ���ʱ���ڣ�
    if '093000' <= current_time <= '150000':
        print("��ʼ��������")
        process_sell_orders(C, C.my_context)

    # ����ʱ���ִ�в�ͬ�Ľ��ײ��ԣ����룩
    for start_time, end_time, trading_phase in Config.TRADING_SCHEDULES:
        if start_time <= current_time <= end_time:
            print(f"��ʼ���뽻�ף�{trading_phase}")
            process_stock_orders(C, C.my_context, trading_phase)
            break

    # ������ع�
    process_reverse_repo(C, C.my_context)
