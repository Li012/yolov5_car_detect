import tracker
from detector import Detector
import cv2
import numpy as np

import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


class camera(object):
    def __init__(self):
        # 帧率，单位为帧/秒
        self.FPS = 30
        # 摄像头打开标志位
        self.camera_open_flag = False
        # 视频检测标志位
        self.detect_flag = False
        # 初始化 yolov5
        self.detector = Detector()

    def camera_open(self):
        # 打开摄像头
        self.cap = cv2.VideoCapture(0)
        while self.cap.isOpened():
            # 开始用摄像头读数据，返回hx为true则表示读成功，frame为读的图像
            hx, frame = self.cap.read()
            # 如果hx为Flase表示开启摄像头失败，那么就输出"read vido error"并退出程序
            if hx is False:
                # 打印报错
                print('read video error')
                # 退出程序
                exit(0)
            cv2.waitKey(1)
            # # 监测键盘输入是否为q，为q则退出程序
            # if cv2.waitKey(1) & 0xFF == ord('q'):  # 按q退出
            #     break
            yield frame
        # 释放摄像头
        # self.cap.release()
        # # # 结束所有窗口
        # cv2.destroyAllWindows()

    # 区域的实际宽度和像素宽度的函数关系，单位为米
    # 这里假设是一个线性函数，你可以根据你的实际情况进行修改
    def REAL_WIDTH(self, pixel_width):
        real_width = pixel_width / (1354.2 * (85 ** (-0.989)))
        return real_width

    # 定义一个函数，根据车辆的边界框，判断车辆是否进入或离开了区域
    def is_in_area(self, bbox, area):
        # bbox是一个四元组，表示车辆的左上角和右下角的坐标，格式为(x1, y1, x2, y2)
        # area是一个二元组，表示区域的左右边界的横坐标，格式为(x_left, x_right)
        # 计算车辆的中心点横坐标
        # cx = (bbox[0] + bbox[2]) / 2
        cx = (bbox[1] + bbox[3]) / 2
        # 如果车辆的中心点在区域内，返回True，否则返回False
        return area[0] <= cx <= area[1]

    def detect_init(self):
        # 打开视频
        capture = cv2.VideoCapture('./video/2023-1.mp4')
        # capture = cv2.VideoCapture(0)
        # capture = cv2.VideoCapture('/mnt/datasets/datasets/towncentre/TownCentreXVID.avi')

        # 定义一个字典，存储每辆车的中点坐标
        self.last_pos = {}
        # 定义一个字典，存储每辆车的中点坐标
        self.pos = {}
        # 定义一个字典，存储每辆车的速度
        self.speed = {}
        # 定义一个区域，格式为(x_left, x_right)，单位为像素
        area = (200, 300)
        PIXEL_WIDTH = area[1] - area[0]
        # 计算速度帧间隔
        count = 0

        # 画碰撞线
        # 根据视频尺寸，填充一个polygon，供撞线计算使用
        mask_image_temp = np.zeros((1080, 1920), dtype=np.uint8)

        # 初始化2个撞线polygon
        list_pts_blue = [[0, 530], [1920, 530], [1920, 540], [0, 540]]
        ndarray_pts_blue = np.array(list_pts_blue, np.int32)
        polygon_blue_value_1 = cv2.fillPoly(mask_image_temp, [ndarray_pts_blue], color=1)
        polygon_blue_value_1 = polygon_blue_value_1[:, :, np.newaxis]

        # 填充第二个polygon
        mask_image_temp = np.zeros((1080, 1920), dtype=np.uint8)
        list_pts_yellow = [[0, 540], [1920, 540], [1920, 550], [0, 550]]
        ndarray_pts_yellow = np.array(list_pts_yellow, np.int32)
        polygon_yellow_value_2 = cv2.fillPoly(mask_image_temp, [ndarray_pts_yellow], color=2)
        polygon_yellow_value_2 = polygon_yellow_value_2[:, :, np.newaxis]

        # 撞线检测用mask，包含2个polygon，（值范围 0、1、2），供撞线计算使用
        polygon_mask_blue_and_yellow = polygon_blue_value_1 + polygon_yellow_value_2

        # 缩小尺寸，1920x1080->960x540
        self.polygon_mask_blue_and_yellow = cv2.resize(polygon_mask_blue_and_yellow, (960, 540))

        # 蓝 色盘 b,g,r
        blue_color_plate = [255, 0, 0]
        # 蓝 polygon图片
        blue_image = np.array(polygon_blue_value_1 * blue_color_plate, np.uint8)

        # 黄 色盘
        yellow_color_plate = [0, 255, 255]
        # 黄 polygon图片
        yellow_image = np.array(polygon_yellow_value_2 * yellow_color_plate, np.uint8)

        # 彩色图片（值范围 0-255）
        color_polygons_image = blue_image + yellow_image
        # 缩小尺寸，1920x1080->960x540
        self.color_polygons_image = cv2.resize(color_polygons_image, (960, 540))

        # list 与蓝色polygon重叠
        self.list_overlapping_blue_polygon = []

        # list 与黄色polygon重叠
        self.list_overlapping_yellow_polygon = []

        # 进入数量
        self.down_count = 0
        # 离开数量
        self.up_count = 0

        self.font_draw_number = cv2.FONT_HERSHEY_SIMPLEX
        self.draw_text_postion = (int(960 * 0.01), int(540 * 0.05))

    def detect(self, frame):
        # 缩小尺寸，1920x1080->960x540
        im = cv2.resize(frame, (960, 540))

        list_bboxs = []
        bboxes = self.detector.detect(im)

        # 如果画面中 有bbox
        if len(bboxes) > 0:
            list_bboxs = tracker.update(bboxes, im)
            # 画框
            # 撞线检测点，(x1，y1)，y方向偏移比例 0.0~1.0
            output_image_frame = tracker.draw_bboxes(im, list_bboxs, line_thickness=None)
            pass
        else:
            # 如果画面中 没有bbox
            output_image_frame = im
        pass

        output_image_frame = cv2.add(output_image_frame, self.color_polygons_image)

        if len(list_bboxs) > 0:
            for item_bbox in list_bboxs:
                x1, y1, x2, y2, label, track_id = item_bbox
                bbox = (x1, y1, x2, y2)

                # 撞线检测点，(x1，y1)，y方向偏移比例 0.0~1.0
                y1_offset = int(y1 + ((y2 - y1) * 0.6))

                # 撞线的点
                y = y1_offset
                x = x1

                if self.polygon_mask_blue_and_yellow[y, x] == 1:
                    # 如果撞 蓝polygon
                    if track_id not in self.list_overlapping_blue_polygon:
                        self.list_overlapping_blue_polygon.append(track_id)
                    pass

                    # 判断 黄polygon list 里是否有此 track_id
                    # 有此 track_id，则 认为是 外出方向
                    if track_id in self.list_overlapping_yellow_polygon:
                        # 外出+1
                        self.up_count += 1

                        print(
                            f'类别: {label} | id: {track_id} | 上行撞线 | 上行撞线总数: {self.up_count} | 上行id列表: {self.list_overlapping_yellow_polygon}')

                        # 删除 黄polygon list 中的此id
                        self.list_overlapping_yellow_polygon.remove(track_id)

                        pass
                    else:
                        # 无此 track_id，不做其他操作
                        pass

                elif self.polygon_mask_blue_and_yellow[y, x] == 2:
                    # 如果撞 黄polygon
                    if track_id not in self.list_overlapping_yellow_polygon:
                        self.list_overlapping_yellow_polygon.append(track_id)
                    pass

                    # 判断 蓝polygon list 里是否有此 track_id
                    # 有此 track_id，则 认为是 进入方向
                    if track_id in self.list_overlapping_blue_polygon:
                        # 进入+1
                        self.down_count += 1

                        print(
                            f'类别: {label} | id: {track_id} | 下行撞线 | 下行撞线总数: {self.down_count} | 下行id列表: {self.list_overlapping_blue_polygon}')

                        # 删除 蓝polygon list 中的此id
                        self.list_overlapping_blue_polygon.remove(track_id)

                        pass
                    else:
                        # 无此 track_id，不做其他操作
                        pass
                    pass
                else:
                    pass
                pass

                # ----------通过帧之间检测框中点位置变化求速度----------
                # 中点坐标
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                self.pos[track_id] = (center_x, center_y)
                if self.last_pos.get(track_id) is not None:
                    dis_pix = self.last_pos[track_id][1] - self.pos[track_id][1]
                    self.speed[track_id] = self.REAL_WIDTH(dis_pix) * self.FPS * 3.6
                    cv2.putText(output_image_frame, str(self.speed[track_id])[0:4], (x1, y1 + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 4)
                else:
                    pass

            # ----------------------清除无用id----------------------
            list_overlapping_all = self.list_overlapping_yellow_polygon + self.list_overlapping_blue_polygon
            for id1 in list_overlapping_all:
                is_found = False
                for _, _, _, _, _, bbox_id in list_bboxs:
                    if bbox_id == id1:
                        is_found = True
                        break
                    pass
                pass

                if not is_found:
                    # 如果没找到，删除id
                    if id1 in self.list_overlapping_yellow_polygon:
                        self.list_overlapping_yellow_polygon.remove(id1)
                    pass
                    if id1 in self.list_overlapping_blue_polygon:
                        self.list_overlapping_blue_polygon.remove(id1)
                    pass
                pass
            list_overlapping_all.clear()
            # 清空list
            list_bboxs.clear()

            self.last_pos = self.pos
            self.speed = {}
            self.pos = {}
        else:
            # 如果图像中没有任何的bbox，则清空list
            self.list_overlapping_blue_polygon.clear()
            self.list_overlapping_yellow_polygon.clear()

        text_draw = 'DOWN: ' + str(self.down_count) + \
                    ' , UP: ' + str(self.up_count)
        output_image_frame = cv2.putText(img=output_image_frame, text=text_draw,
                                         org=self.draw_text_postion,
                                         fontFace=self.font_draw_number,
                                         fontScale=1, color=(255, 255, 255), thickness=2)

        return output_image_frame, self.up_count, self.down_count
        # cv2.imshow('demo', output_image_frame)
        # cv2.waitKey(1)


if __name__ == "__main__":
    pass
    # Detect = start_detect()
    # for frame in Detect.detect():
    #     cv2.imshow('demo', frame)
