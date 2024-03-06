"""串口的配置"""
import serial
import queue
import threading
import datetime
import binascii


# 线程类
class Uart_Recv_Data_Thread(threading.Thread):
    """串口接收数据的线程"""

    def __init__(self, cur_self, main_self):
        super(Uart_Recv_Data_Thread, self).__init__()
        self.cur_self = cur_self
        self.thread = threading.Event()
        self.main_self = main_self
        self.flag = 1

    def stop(self):
        """将event标志位设置为true"""
        self.thread.set()

    def stopped(self):
        """判断event标志位是否为true"""
        return self.thread.is_set()

    def run(self):
        while True:
            time = ''
            if self.stopped():
                break
            try:
                if not self.cur_self.recv_queue.empty():
                    show_data = ''
                    data = self.cur_self.recv_queue.get()
                    data_num = len(data)
                    if self.cur_self.uart_time_stamp_flag == 1:  # 时间戳开关打开
                        # 显示的时间的格式
                        time = datetime.datetime.now().strftime('[%Y-%m-%d %H:%M:%S:%f]\r\n')

                    # 勾选hex的情况
                    if self.cur_self.uart_rec_hex_lock == 1:
                        data_list = []
                        data_bytes = bytes(data, encoding='utf-8')
                        for i in range(len(data_bytes)):
                            data_list.append(hex(data_bytes[i])[2:].zfill(2))
                        send_text_to_hex = ' '.join(data_list)
                        show_data += send_text_to_hex

                        # out_s = ''
                        # for i in range(0, len(data)):
                        #     out_s = out_s + '{:02X}'.format(data[i]) + ' '
                        #
                        # show_data = out_s

                    else:
                        show_data = data

                    # 发送显示接收数据的信号
                    self.main_self.uart_recv_updata_show_data_signal.emit(time + show_data + '\r\n')

                    # 统计接收字符的数量
                    self.main_self.uart_updata_recv_num_signal.emit(data_num)

                nums = self.cur_self.serial.inWaiting()
                if (nums > 0):
                    recv_msg = self.cur_self.serial.read(nums)
                else:
                    continue
                if self.cur_self.recv_queue.full():
                    self.cur_self.recv_queue.get()
                self.cur_self.recv_queue.put(recv_msg.decode())


            except Exception as e:
                print(e)
                continue


class Uart_Send_Data_Thread(threading.Thread):
    """串口发送数据的线程"""

    def __init__(self, cur_self, main_self):
        super(Uart_Send_Data_Thread, self).__init__()
        self.cur_self = cur_self
        self.main_self = main_self
        self.thread = threading.Event()

    def stop(self):
        self.thread.set()

    def stopped(self):
        return self.thread.is_set()

    def run(self):
        while True:
            if self.stopped():
                break
            try:
                # 如果发送队列不为空
                if not self.cur_self.send_queue.empty():
                    # 待发送的数据为queue.get()，block=false
                    send_data = self.cur_self.send_queue.get(False)
                    data_num = len(send_data)
                    # 统计发送字符的数量
                    self.main_self.uart_updata_send_num_signal.emit(data_num)
                    # ascii 发送
                    self.cur_self.serial.write(send_data)
                else:
                    continue
            except queue.Empty:
                continue


class Uart(object):
    def __init__(self, parent):
        self.err = 0
        self.parent = parent

        # 发送队列和接收队列
        self.recv_queue = queue.Queue(1000)
        self.send_queue = queue.Queue(1000)
        self.uart_time_stamp_flag = 0
        self.uart_rec_hex_lock = 0

    # 初始化波特率、停止位、数据位、校验位等数据
    def uart_init(self, port, baud, stopbit, databit, checkbit):
        try:
            checkbitlist = {'None': 'N', 'Odd': 'O', 'Even': 'E'}
            stopbitlist = {'1': 'serial.STOPBITS_ONE', '1.5': 'serial.STOPBITS_ONE', '2': 'serial.STOPBITS_ONE'}
            # 传入参数，初始化串口
            self.serial = serial.Serial(port.split()[0], baud, int(databit), checkbitlist[checkbit],
                                        serial.STOPBITS_ONE)
            # 创建线程
            self.recv_thread = Uart_Recv_Data_Thread(self, self.parent)
            self.send_thread = Uart_Send_Data_Thread(self, self.parent)
            self.err = 0
        except Exception as e:
            print(e)
            self.err = -1

    def open_uart_thread(self):
        """打开发送和接收线程"""
        self.recv_thread.start()
        self.send_thread.start()

    def close_uart_thread(self):
        """关闭发送和接收线程"""
        self.recv_thread.stop()
        self.send_thread.stop()
        self.serial.close()

    def uart_send_func(self, data):
        """将data放入队列"""
        self.send_queue.put(data)

    def uart_time_stamp(self, flag):
        self.uart_time_stamp_flag = flag

    def uart_set_rec_hex_lock(self, flag):
        self.uart_rec_hex_lock = flag
