import inspect
import re
import sys
import threading

import pymavlink
from pymavlink import mavutil
from pymavlink.dialects.v20.ardupilotmega import *

sys.path.append('D:/Program Files/anaconda3/envs/V2C/Lib/site-packages/pymavlink/dialects/v20')


class mavlink_recv_thread(threading.Thread):
    def __init__(self, cur_self, main_self):
        super(mavlink_recv_thread, self).__init__()
        self.cur_self = cur_self
        self.main_self = main_self
        self.thread = threading.Event()
        # self.setDaemon(True)

    def stop(self):
        """将event标志位设置为true"""
        self.thread.set()

    def stopped(self):
        """判断event标志位是否为true"""
        return self.thread.is_set()

    def run(self):
        while True:
            if self.stopped():
                print("进程终止")
                break
            # msg = self.cur_self.connect.recv_match(type='VFR_HUD', blocking=True)
            # msg = self.cur_self.connect.recv_match(type=['VFR_HUD', 'ATTITUDE'], blocking=True)
            msg = self.cur_self.connect.recv_match(blocking=True)
            print(msg)
            if type(msg) == MAVLink_vfr_hud_message:
                try:
                    groundspeed = str(msg.groundspeed)[0:5]
                    alt = str(msg.alt)[0:5]
                    self.main_self.ground_speed = msg.groundspeed
                    self.main_self.alt = msg.alt
                    vfr_hud = {"ground_speed": groundspeed, "alt": alt}
                    self.main_self.mavlink_updata_vfr_hud_signal.emit(vfr_hud)
                except Exception as e:
                    print(e)
                    continue
            # if type(msg) == MAVLink_attitude_message:
            # try:
            #     print(msg)
            #     pitch = str(msg.pitch)[0:5]
            #     roll = str(msg.roll)[0:5]
            #     yaw = str(msg.yaw)[0:5]
            #     attitude = {"pitch": pitch, "roll": roll, "yaw": yaw}
            #     self.main_self.mavlink_updata_attitude_signal.emit(attitude)
            # except Exception as e:
            #     print(e)
            #     continue

            # self.main_self.mavlink_updata_lat_signal.emit(str(msg.lat))
            # self.main_self.mavlink_updata_lon_signal.emit(str(msg.lon))
            # print(msg)
            # print(type(msg))
            # print(msg.get_type())
            # print(msg.get_fieldnames())
            # print(type(msg))
            # print(msg.time_boot_ms)
            # print("******")
            # print(msg.lat)
            # print(msg.lon)
            # print(msg.alt)
            # print(type(msg.alt))
            # print(msg.relative_alt)
            # print("-------")
            # print(msg.vx)
            # print(msg.vy)
            # print(msg.vz)
            # print(msg.hdg)


class mavlink(object):
    def __init__(self, COM, parent):
        self.connect = mavutil.mavlink_connection(COM, source_system=1, source_component=2, baud=57600)
        self.parent = parent
        self.target_system = self.connect.target_system
        self.target_component = self.connect.target_component
        self.recv_thread = mavlink_recv_thread(self, self.parent)

    def open_mavlink_thread(self):
        """打开发送和接收线程"""
        self.recv_thread.start()

    def close_mavlink_thread(self):
        """关闭发送和接收线程"""
        self.recv_thread.stop()
        self.connect.close()


if __name__ == "__main__":
    test = mavlink('COM6')
    test.open_mavlink_thread()
    # pass
