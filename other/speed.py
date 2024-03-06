import cv2
from detector import Detector
import tracker

import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

# 定义一些常量，根据你的摄像头和区域情况进行调整
# 区域的像素宽度，单位为像素
PIXEL_WIDTH = 80


# 区域的实际宽度和像素宽度的函数关系，单位为米
# 这里假设是一个线性函数，你可以根据你的实际情况进行修改
def REAL_WIDTH(pixel_width):
    return 0.01 * pixel_width + 0.5


# 帧率，单位为帧/秒
FPS = 30


# 定义一个函数，根据车辆的边界框，判断车辆是否进入或离开了区域
def is_in_area(bbox, area):
    # bbox是一个四元组，表示车辆的左上角和右下角的坐标，格式为(x1, y1, x2, y2)
    # area是一个二元组，表示区域的左右边界的横坐标，格式为(x_left, x_right)
    # 计算车辆的中心点横坐标
    # cx = (bbox[0] + bbox[2]) / 2
    cx = (bbox[1] + bbox[3]) / 2
    # 如果车辆的中心点在区域内，返回True，否则返回False
    return area[0] <= cx <= area[1]


# 定义一个函数，根据车辆的进入和离开的时间，以及区域的实际宽度，计算车辆的当前车速
def get_speed(time_in, time_out, real_width):
    # time_in是车辆进入区域的时间，单位为秒
    # time_out是车辆离开区域的时间，单位为秒
    # real_width是区域的实际宽度，单位为米
    # 计算车辆在区域内的时间，单位为秒
    time = time_out - time_in
    # 计算车辆的速度，单位为米/秒
    speed = real_width / time
    # 返回速度
    return speed


# 定义一个函数，测试上述函数的效果
def test():
    # 读取一段视频
    cap = cv2.VideoCapture('./video/2023-1.mp4')
    # 定义一个字典，存储每辆车的ID和进入区域的时间
    enter_times = {}
    # 定义一个列表，存储每辆车的ID和离开区域的时间
    exit_times = []
    # 定义一个区域，格式为(x_left, x_right)，单位为像素
    area = (530, 550)
    # 初始化 yolov5
    detector = Detector()
    # 循环处理每一帧
    while cap.isOpened():
        # 读取一帧
        ret, frame = cap.read()
        if frame is None:
            break
        # 缩小尺寸，1920x1080->960x540
        frame = cv2.resize(frame, (960, 540))

        list_bboxs = []
        # 如果读取成功
        if ret:
            # 使用yolov5和deepsort进行车辆检测和跟踪，得到车辆的边界框和ID
            # 这里省略了具体的代码，你可以参考你的项目中的代码
            bboxes = detector.detect(frame)
            # 如果画面中 有bbox
            if len(bboxes) > 0:
                list_bboxs = tracker.update(bboxes, frame)
                # 画框
                # 撞线检测点，(x1，y1)，y方向偏移比例 0.0~1.0
                output_image_frame = tracker.draw_bboxes(frame, list_bboxs, line_thickness=None)
                pass
            else:
                # 如果画面中 没有bbox
                output_image_frame = frame
            pass

            # bboxes, ids = detect_and_track(frame)

            # 遍历每个边界框和ID
            for item_bbox in bboxes:
                x1, y1, x2, y2, label, tracker_id = item_bbox
                bbox = (x1, y1, x2, y2)
                print(tracker_id)
                # id = track_id
                # print(id)
                # for bbox, id in zip(bboxes, ids):
                # 判断车辆是否在区域内
                in_area = is_in_area(bbox, area)
                # 如果车辆在区域内，且之前没有记录进入时间
                if in_area and tracker_id not in enter_times:
                    # 记录车辆的ID和进入时间
                    enter_times[tracker_id] = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                # 如果车辆不在区域内，且之前有记录进入时间
                elif not in_area and tracker_id in enter_times:
                    # 记录车辆的ID和离开时间
                    exit_times.append((tracker_id, cap.get(cv2.CAP_PROP_POS_MSEC) / 1000))
                    # 删除车辆的进入时间
                    del enter_times[tracker_id]
            # 遍历每个离开时间
            for tracker_id, time_out in exit_times:
                # 获取车辆的进入时间
                time_in = enter_times[tracker_id]
                # 计算区域的实际宽度
                real_width = REAL_WIDTH(PIXEL_WIDTH)
                # 计算车辆的速度
                speed = get_speed(time_in, time_out, real_width)
                # 输出车辆的ID和速度
                print(f"Vehicle {tracker_id} speed: {speed:.2f} m/s")

            # 输出图片
            cv2.imshow('demo', output_image_frame)
            # 等待按键
            key = cv2.waitKey(1)
            # 如果按下ESC键，退出循环
            if key == 27:
                break
        # 如果读取失败，退出循环
        else:
            break
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


# 调用测试函数
REAL_WIDTH(1)
