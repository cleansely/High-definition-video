import glob
import os
import random
import sys
import time
from subprocess import Popen, PIPE

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtMultimedia import QMediaContent
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog

from ui import *


class CDialog(QMainWindow, Ui_MainWindow):
    str_file_name = ""

    def __init__(self, parent=None):
        super(CDialog, self).__init__(parent)
        self.setupUi(self)
        self.pushButton.clicked.connect(self.get_file_name)
        self.pushButton_2.clicked.connect(self.high_video)
        self.pushButton_3.clicked.connect(self.PlayVideo)
        # self.pushButton_4.clicked.connect(self.StopVideo)

    def PlayVideo(self):
        self.contrast_thread = Contrastthread(self)
        self.contrast_thread.start()

    def get_file_name(self):
        filename, _ = QFileDialog.getOpenFileName(self)
        self.str_file_name = filename
        self.lineEdit.setText(self.str_file_name)

    def high_video(self):
        self.str_file_name = self.lineEdit.text()
        # 检查文件是否存在
        filename = os.path.basename(self.str_file_name)
        if not os.path.exists(self.str_file_name):
            self.textBrowser.append(f"{filename}不存在")
            return
        # 检查文件后缀
        if not (filename.endswith("mp4") or filename.endswith("avi")):
            self.textBrowser.append(f"文件应是mp4或avi")
            return
        # 文件转图片集
        os.makedirs("input", exist_ok=True)
        os.makedirs("output", exist_ok=True)
        os.makedirs(f"input/{filename.split('.')[0]}", exist_ok=True)
        os.makedirs(f"output/{filename.split('.')[0]}", exist_ok=True)
        self.high_thread = Mythread(self)
        self.high_thread.breakSignal.connect(self.text_log)
        self.high_thread.start()

    def text_log(self, info):
        self.textBrowser.append(info)


class Contrastthread(QThread):
    def __init__(self, parent=None):
        self.parent = parent
        super(Contrastthread, self).__init__()

    def run(self):
        file_list = sorted(os.listdir(os.path.join("output", os.path.basename(self.parent.str_file_name).split(".")[0])),
                           key=lambda x: int(x[:-4]))
        self.parent.label.setScaledContents(True)
        for file in file_list:
            if not file.endswith(".png"):
                continue
            out_file = os.path.join("output", os.path.basename(self.parent.str_file_name).split(".")[0], file)
            input_file = out_file.replace("output", "input")

            img1 = cv2.imread(out_file)
            img2 = cv2.imread(input_file)
            shape = img1.shape
            y, x = shape[:2]
            img2 = cv2.resize(img2, (x, y))
            img1[:, int(x / 2):x] = img2[:, int(x / 2):x]
            img1[:, int(x / 2):int(x / 2) + 2] = [1, 1, 1]

            png = QImage(np.asanyarray(cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)).data, x, y, QImage.Format_RGB888)
            # self.parent.label.setStyleSheet("border: 2px solid red")
            self.parent.label.setPixmap(QPixmap(png))


class Mythread(QThread):
    # 定义信号,定义参数为str类型
    breakSignal = pyqtSignal(str)

    def __init__(self, parent=None):
        self.parent = parent
        super(Mythread, self).__init__()

    def run(self):
        ############### 视频拆分为图片 start
        self.breakSignal.emit("视频拆分为图片")
        filename = self.parent.str_file_name
        count = 0
        cap = cv2.VideoCapture(filename)
        while True:
            # get a frame
            ret, image = cap.read()
            if image is None:
                self.breakSignal.emit(f"视频拆分为图片结束,共{count}张")
                break
            # show a frame

            w = image.shape[1]
            h = image.shape[0]
            cv2.imwrite(os.path.join("input", os.path.basename(filename).split(".")[0], str(count) + '.png'),
                        image)  # 含中文路径，不可行
            count += 1
            self.breakSignal.emit(f"视频拆分为图片,第{count}张")
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.breakSignal.emit(f"视频拆分为图片结束,共{count}张")
                break
        cap.release()
        ###################### 视频拆分为图片 end
        ###################### 图片高清化 start
        self.breakSignal.emit("图片高清化开始")
        # cmd = [
        #     "../realesrgan-ncnn-vulkan.exe",
        #     "-i", f"input/{os.path.basename(filename).split('.')[0]}",
        #     "-o", f"output/{os.path.basename(filename).split('.')[0]}",
        #     "-n", "realesrgan-x4plus-anime",
        # ]
        cmd = [
            "realesrgan-ncnn-vulkan.exe",
            "-i", f"input/{os.path.basename(filename).split('.')[0]}",
            "-o", f"output/{os.path.basename(filename).split('.')[0]}",
            "-n", "realesrgan-x4plus-anime",
        ]
        r = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        flag = False
        while not flag:
            time.sleep(1)
            l_input = len(glob.glob(f"input/{os.path.basename(filename).split('.')[0]}/*.png"))
            l_output = len(glob.glob(f"output/{os.path.basename(filename).split('.')[0]}/*.png"))
            self.breakSignal.emit(f"图片高清化{l_output}/{l_input}")
            if l_input == l_output:
                flag = True
        self.breakSignal.emit("图片高清化结束")
        ###################### 图片高清化 end
        ###################### 图片转视频 start
        self.breakSignal.emit("图片转视频开始")
        png_list = sorted(os.listdir(os.path.join("output", os.path.basename(filename).split(".")[0])),
                          key=lambda x: int(x[:-4]))
        l_output = len(png_list)
        image = cv2.imread(os.path.join("output", os.path.basename(filename).split(".")[0], png_list[0]))
        image_info = image.shape
        height = image_info[0]
        width = image_info[1]
        fps = 30
        video = cv2.VideoWriter(f'{os.path.basename(filename).split(".")[0]}_result.mp4', cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                (width, height))

        for index, file_name in enumerate(png_list):
            image = cv2.imread(os.path.join("output", os.path.basename(filename).split(".")[0], file_name))
            video.write(image)
            self.breakSignal.emit(f"图片转视频 {index}/{l_output}")
        cv2.waitKey()
        self.breakSignal.emit("图片转视频结束")
        ###################### 图片转视频 end


def main():
    app = QApplication(sys.argv)
    widget = CDialog()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
