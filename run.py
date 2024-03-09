import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5.QtGui import *
import threading
from PyQt5.Qt import *
from PyQt5 import QtCore
from mainwindow import Ui_MainWindow
# from test_detect import camera
from detect import camera
from uart import Uart
import win32api
import win32con
import time
from mavlink import mavlink


# 注意：ui界面文件是个对话框，那么MyApp就必须继承 QDialog
# 类似的，若ui界面文件是个MainWindow，那么MyApp就必须继承 QMainWindow
# 修改完ui后记得更改My_ComBoBox
class MyApp(QMainWindow, Ui_MainWindow):
    uart_recv_updata_show_data_signal = pyqtSignal(str)
    uart_updata_recv_num_signal = pyqtSignal(int)
    uart_updata_send_num_signal = pyqtSignal(int)

    mavlink_updata_lat_signal = pyqtSignal(str)
    mavlink_updata_lon_signal = pyqtSignal(str)
    mavlink_updata_vfr_hud_signal = pyqtSignal(dict)
    mavlink_updata_attitude_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 设置界面
        # 创建识别对象
        self.camera = camera(self)
        # 创建串口对象
        self.uart = Uart(self)
        self.flag = 1

        self.mavlink_run_status = 0  # mavlink串口运行状态

        self.start_time = {}
        self.end_time = {}
        self.pass_time = {}

        self.ground_speed = 0.0
        self.alt = 0.0

        self.speed_limit = 60

        # ----------串口相关参数初始化----------
        self.uart_com_run_status = 0  # 串口运行状态
        self.uart_data_rec_count = 0  # 串口接收计数
        self.uart_data_send_count = 0  # 串口发送计数

        # 定时器
        self.uart_timer_num = 1000
        self.uart_timer_line_edit.setText('1000')
        self.uart_timer_send = QTimer()
        self.uart_timer_send.timeout.connect(self.uart_timer_send_cb)

        # 设定默认值
        self.baud_combo_box.setCurrentText(str(9600))
        self.stopbit_combo_box.setCurrentText(str(1))
        self.databit_combo_box.setCurrentText(str(8))
        self.checkbit_combo_box.setCurrentText(str(None))
        self.rec_hex_check_box.setChecked(0)
        self.send_hex_check_box.setChecked(0)
        self.uart_send_show.setFocusPolicy(QtCore.Qt.StrongFocus)
        # ----------串口相关参数初始化结束----------

        self.open_camera_Button.clicked.connect(self.open_camera)  # 绑定点击信号和槽函数
        self.strat_detect_Button.clicked.connect(self.start_detect)
        self.com_config_button.clicked.connect(self.page_change)
        self.page_back_button.clicked.connect(self.page_back)
        self.goback_button.clicked.connect(self.page_back)
        self.speed_limit_pushButton.clicked.connect(self.speed_limit_update)

        self.mavlink_connect_button.clicked.connect(self.mavlink_connect)
        self.mavlink_goto_button.clicked.connect(self.page_change2)

        # 绑定事件连接槽
        # 打开串口按钮按下事件
        self.uart_en_push_button.clicked.connect(self.uart_en_push_button_cb)
        # hex发送复选框勾选事件
        self.send_hex_check_box.toggled.connect(self.uart_hex_to_ascii_send_check_box_cb)
        # 发送按钮按下事件
        self.uart_send_push_button.clicked.connect(self.uart_send_push_button_cb)
        # hex接收按钮按下事件
        self.rec_hex_check_box.toggled.connect(self.uart_hex_to_ascii_rec_check_box_cb)
        # QIntValidator限制输入的范围
        self.uart_timer_line_edit.setValidator(QIntValidator(1, 1000000))
        # 定时时间输入框改变的事件
        self.uart_timer_line_edit.textChanged.connect(self.uart_set_send_time_line_edit_cb)
        # hex发送复选框勾选事件
        self.uart_timer_check_box.clicked.connect(self.uart_time_en_check_box_cb)
        # 清除发送按钮按下事件
        self.uart_send_clear_push_button.clicked.connect(self.uart_send_clear_push_button_cb)
        # 清除接收按钮按下事件
        self.uart_clear_rec_push_button.clicked.connect(self.uart_clear_rec_push_button_cb)
        self.uart_recv_updata_show_data_signal.connect(self.update_uart_recv_show_cb)
        self.uart_updata_recv_num_signal.connect(self.update_uart_recv_num_show_cb)
        self.uart_updata_send_num_signal.connect(self.update_uart_send_num_show_cb)

        self.mavlink_updata_lat_signal.connect(self.mavlink_update_lat_show_cb)
        self.mavlink_updata_lon_signal.connect(self.mavlink_update_lon_show_cb)
        self.mavlink_updata_attitude_signal.connect(self.mavlink_update_attitude_show_cb)
        self.mavlink_updata_vfr_hud_signal.connect(self.mavlink_update_vfr_hud_show_cb)

        self.stackedWidget.setCurrentIndex(0)
        print('ready')
        self.message_label.setText("初始化完成")

    def page_change(self):
        self.stackedWidget.setCurrentIndex(2)

    def page_change2(self):
        self.stackedWidget.setCurrentIndex(1)

    def page_back(self):
        self.stackedWidget.setCurrentIndex(0)

    # ----------摄像头、识别相关方法----------
    def open_camera(self):
        if not self.camera.detect_flag:
            if not self.camera.camera_open_flag:
                self.camera.camera_open_flag = True
                self.open_camera_Button.setText("关闭摄像头")
                label_size = self.img_label.size()
                # 初始化撞线和速度检测列表和参数
                self.camera.detect_init()
                for f in self.camera.camera_open():
                    self.frame = f
                    if not self.camera.detect_flag:
                        Qt_frame = self.cvToQImage(f)
                        # scaled_image = Qt_frame.scaled(label_size, aspectRatioMode=True)
                        scaled_image = Qt_frame.scaled(label_size)
                        self.img_label.setPixmap(QPixmap.fromImage(scaled_image))
                    elif self.camera.detect_flag:
                        frame1, up_cunt, down_cunt = self.camera.detect(self.frame)
                        Qt_frame = self.cvToQImage(frame1)
                        scaled_image = Qt_frame.scaled(label_size)
                        # scaled_image = Qt_frame.scaled(label_size, aspectRatioMode=True)
                        self.img_label.setPixmap(QPixmap.fromImage(scaled_image))
                        self.up_count_label.setText(str(up_cunt))
                        self.down_count_label.setText(str(down_cunt))
            elif self.camera.camera_open_flag:
                self.camera.camera_open_flag = False
                self.open_camera_Button.setText("打开摄像头")
                self.camera.cap.release()
                # self.img_label.setStyleSheet("background-color: CornflowerBlue")
        elif self.camera.detect_flag:
            self.message_label.setText("错误：请先停止检测")

    def start_detect(self):  # click对应的槽函数
        if self.camera.camera_open_flag:
            if not self.camera.detect_flag:
                self.camera.detect_flag = True
                # 点击开始按钮时获取当前时间
                localtime = time.localtime(time.time())
                self.start_time = {"hour": localtime[3], "minute": localtime[3], "second": localtime[5]}
                self.start_time_label.setText(str(self.start_time["hour"]) + ":" + str(self.start_time["minute"]) + ":"
                                              + str(self.start_time["second"]))
                self.end_time_label.setText("00:00:00")
                self.strat_detect_Button.setText("停止检测")

                self.timer = QTimer(self)
                # 一次刷新会调用一次showTime函数
                self.timer.timeout.connect(self.showTime)
                # 一秒钟更新一次
                self.timer.start(1000)
                # 小时，分钟，秒钟
                self.pass_time = {"hour": 0, "minute": 0, "second": 0}

                # self.time_part_hide()
            elif self.camera.detect_flag:
                self.camera.detect_flag = False
                localtime = time.localtime(time.time())
                self.end_time = {"hour": localtime[3], "minute": localtime[3], "second": localtime[5]}
                self.end_time_label.setText(str(self.end_time["hour"]) + ":" + str(self.end_time["minute"]) + ":"
                                            + str(self.end_time["second"]))
                self.strat_detect_Button.setText("开始检测")
                self.timer.stop()

                # 将速度和撞线检测的参数和列表重置
                self.camera.detect_init()
                self.up_count_label.setText("0")
                self.down_count_label.setText("0")
        elif not self.camera.camera_open_flag:
            self.message_label.setText("错误：请先打开摄像头")

    def cvToQImage(self, image):  # OpenCV图像 转换为 PyQt图像
        # 8-bits unsigned, NO. OF CHANNELS=1
        row, col, pix = image.shape[0], image.shape[1], image.strides[0]
        channels = 1 if len(image.shape) == 2 else image.shape[2]
        if channels == 3:  # CV_8UC3
            qImg = QImage(image.data, col, row, pix, QImage.Format_RGB888)
            return qImg.rgbSwapped()
        elif channels == 1:
            qImg = QImage(image.data, col, row, pix, QImage.Format_Indexed8)
            return qImg
        else:
            QtCore.qDebug("ERROR: numpy.ndarray could not be converted to QImage. Channels = %d" % image.shape[2])
            return QImage()

    # ----------摄像头、识别相关方法----------

    # ----------串口相关方法----------
    def uart_en_push_button_cb(self):
        """串口的打开和关闭回调函数"""
        # 判断串口运行状态
        # 如果串口处于关闭状态：
        if self.uart_com_run_status == 0:
            port = self.com_combo_box.currentText()
            # 如果未选择串口
            if port == '':
                # 弹出警告窗口
                win32api.MessageBox(0, "请选择串口", "警告", win32con.MB_ICONWARNING)
                return
            # 获取波特率、停止位、数据位、校验位等数据
            baud = self.baud_combo_box.currentText()
            stopbit = self.stopbit_combo_box.currentText()
            databit = self.databit_combo_box.currentText()
            checkbit = self.checkbit_combo_box.currentText()
            self.uart.uart_init(port, baud, stopbit, databit, checkbit)
            # 如果初始化错误
            if self.uart.err == -1:
                self.uart_com_run_status = 0
                win32api.MessageBox(0, port + "已被使用", "警告", win32con.MB_ICONWARNING)
            else:
                # 串口运行状态位置1
                self.uart_com_run_status = 1
                # 打开串口发送和接收线程
                self.uart.open_uart_thread()
                # 改变按钮文字
                self.uart_en_push_button.setText('关闭串口')
        # 如果串口处于打开状态：
        else:
            self.uart_com_run_status = 0
            self.uart.close_uart_thread()

            if self.uart_timer_send.isActive():  # 更改定时器运行时间时如果还开着定时器，则重新打开
                self.uart_timer_check_box.setChecked(False)
                self.uart_timer_send.stop()
            self.uart_en_push_button.setText('打开串口')

    def uart_hex_to_ascii_send_check_box_cb(self):
        """hex发送复选框勾选的回调函数"""
        # 如果复选框处于勾选的状态
        if self.send_hex_check_box.isChecked():
            # 将标志位置1
            self.uart_send_hex_lock = 1
            text_list = []
            send_text = bytes(self.uart_send_show.toPlainText(), encoding='utf-8')
            for i in range(len(send_text)):
                text_list.append(hex(send_text[i])[2:])
            send_text_to_hex = ' '.join(text_list)
            self.uart_send_show.clear()
            self.uart_send_show.setText(send_text_to_hex)
        # 如果复选框处于未勾选的状态
        else:
            # 将标志位置0,使用ascii发送
            self.uart_send_hex_lock = 0
            send_text = self.uart_send_show.toPlainText().replace(' ', '')
            self.uart_send_show.clear()
            hex_send_text = self.hex2bin(send_text)
            self.uart_send_show.setText(hex_send_text)

    def uart_hex_to_ascii_rec_check_box_cb(self):
        """hex接收复选框回调函数"""
        if self.rec_hex_check_box.isChecked():
            self.uart.uart_set_rec_hex_lock(1)
        else:
            self.uart.uart_set_rec_hex_lock(0)

    def update_uart_recv_show_cb(self, data):
        """hex接收复选框按下后改变接收区格式"""
        print(self.flag)
        self.flag = self.flag + 1
        self.uart_rec_show.insertPlainText(data)
        cursor = self.uart_rec_show.textCursor()
        self.uart_rec_show.moveCursor(cursor.End)

        # 16进制转2进制

    def hex2bin(self, str):
        bits = ''
        for x in range(0, len(str), 2):
            bits += chr(int(str[x:x + 2], 16))
        return bits

    def uart_send_push_button_cb(self):
        """发送按钮按下回调函数"""
        if self.uart_com_run_status == 0:
            return
        send_data = ''
        send_text = self.uart_send_show.toPlainText()
        if send_text == '':
            return
        if self.send_hex_check_box.isChecked():  # 十六进制发送
            hex_send_text = self.hex2bin(send_text.replace(' ', ''))
            send_data = bytes(hex_send_text, encoding='utf-8')
        else:
            send_data = send_text.encode()
        # 将发送文本框中的内容加入串口发送队列
        self.uart.uart_send_func(send_data)

    def uart_timer_send_cb(self):
        """计时器超时的回调函数"""
        # 调用发送按钮按下的回调函数
        self.uart_send_push_button_cb()

    def uart_time_en_check_box_cb(self):
        """定时器复选框勾选的回调函数"""
        # 如果串口未运行
        if self.uart_com_run_status == 0:
            self.uart_timer_check_box.setChecked(False)
            return None

        # 判断复选框是否处于勾选的状态
        # 如果复选框处于勾选状态
        if self.uart_timer_check_box.isChecked():
            # 启动定时器
            self.uart_timer_send.start(int(self.uart_timer_num))
        # 如果复选框未处于勾选状态
        else:
            # 停止定时器
            self.uart_timer_send.stop()

    def uart_set_send_time_line_edit_cb(self):
        """改变定时输入框内容事件的回调函数"""
        # 判断输入的时间是否合法
        # 若不合法，弹出警告
        if self.uart_timer_line_edit.text() == '0':
            self.uart_timer_line_edit.setText('1000')
            self.uart_timer_num = 1000
            win32api.MessageBox(0, "请输入1-1000000范围内的值", "警告", win32con.MB_ICONWARNING)
        # 如果输入合法则改变定时器的值
        else:
            self.uart_timer_num = self.uart_timer_line_edit.text()

        if self.uart_timer_send.isActive():  # 更改定时器运行时间时如果还开着定时器，则重新打开
            self.uart_timer_send.stop()
            self.uart_timer_send.start(int(self.uart_timer_num))

    def uart_send_clear_push_button_cb(self):
        """清除发送按钮按下回调函数"""
        # 清除发送计数
        self.uart_data_send_count = 0
        # 清除发送计数标签
        self.uart_tx_data_count_label.setText(str(self.uart_data_send_count))
        # 清除发送文本框
        self.uart_send_show.clear()

    def uart_clear_rec_push_button_cb(self):
        """清除接收按钮按下回调函数"""
        # 清除接收计数
        self.uart_data_rec_count = 0
        # 清除接收计数标签
        self.uart_rx_data_count_label.setText(str(self.uart_data_rec_count))
        # 清除接收文本框
        self.uart_rec_show.clear()

    def update_uart_recv_num_show_cb(self, data_num):
        """更新接收计数"""
        self.uart_data_rec_count += data_num
        self.uart_rx_data_count_label.setText(str(self.uart_data_rec_count))

    def update_uart_send_num_show_cb(self, data_num):
        """更新发送计数"""
        self.uart_data_send_count += data_num
        self.uart_tx_data_count_label.setText(str(self.uart_data_send_count))

    def speed_limit_update(self):
        str1 = self.speed_limit_lineEdit.text()
        self.speed_limit = int(str1)
        # print(self.speed_limit)

    # ----------串口相关方法结束----------

    def mavlink_connect(self):
        if self.mavlink_run_status == 0:
            # TODO:修改获取串口号的方式
            text = self.com_combobox2.currentText()
            com = text[0:5]
            # print(com)
            self.mavlink_object = mavlink(com, self)
            self.mavlink_object.open_mavlink_thread()
            self.mavlink_connect_button.setText("关闭")
            self.mavlink_run_status = 1
        elif self.mavlink_run_status == 1:
            self.mavlink_object.close_mavlink_thread()
            print("当前活动线程", threading.active_count())
            # self.mavlink_object.connect.close()
            self.mavlink_connect_button.setText("连接")
            self.mavlink_run_status = 0
            print("当前活动线程1", threading.active_count())

    def mavlink_update_lat_show_cb(self, lat):
        print("lat:" + lat)
        self.lat_label.setText(lat)

    def mavlink_update_lon_show_cb(self, lon):
        self.lon_label.setText(lon)

    def mavlink_update_attitude_show_cb(self, attitude):
        self.pitch_label.setText(attitude["pitch"])
        self.roll_label.setText(attitude["roll"])
        self.yaw_label.setText(attitude["yaw"])

    def mavlink_update_vfr_hud_show_cb(self, vfr_hud):
        self.alt_label.setText(vfr_hud["alt"])
        self.ground_speed_label.setText(vfr_hud["ground_speed"])

    def showTime(self):
        self.pass_time["second"] = self.pass_time["second"] + 1
        if self.pass_time["second"] == 60:
            self.pass_time["second"] = 0
            self.pass_time["minute"] = self.pass_time["minute"] + 1
        if self.pass_time["minute"] == 60:
            self.pass_time["minute"] = 0
            self.pass_time["hour"] = self.pass_time["hour"] + 1
        self.pass_time_label.setText(str(self.pass_time["hour"]) + ":" + str(self.pass_time["minute"]) + ":"
                                     + str(self.pass_time["second"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec_())
