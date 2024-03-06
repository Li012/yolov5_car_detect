import cv2


class camera(object):
    def __init__(self):
        # self.cap = cv2.VideoCapture(0)
        pass

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
        self.cap.release()
        # # # 结束所有窗口
        # cv2.destroyAllWindows()


if __name__ == "__main__":
    camera = camera()
    for f in camera.camera_open():
        cv2.imshow('video', f)
