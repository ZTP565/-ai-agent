import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# 导入项目模块
import save_pcm
import recongnize
import deepseek
import tool
import json

# DeepSeek API Key
DEEPSEEK_API_KEY = "sk-d46115c9e435433fb9febfec8d05bed4"


class TTSPlayer:
    """ pyttsx3 语音播报封装 """

    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # 设置语速
            self.engine.setProperty('rate', 150)
            # 设置音量
            self.engine.setProperty('volume', 1.0)
            # 获取可用声音（尝试选择中文）
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            self.available = True
        except Exception as e:
            print(f"TTS 初始化失败：{e}")
            self.available = False

    def speak(self, text):
        """语音播报文本"""
        if self.available:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"TTS 播报失败：{e}")
        else:
            print(f"[语音播报] {text}")


class WorkerThread(QThread):
    """后台工作线程，执行录音 + 识别 + AI 分析 + 执行的完整流程"""

    status_signal = pyqtSignal(str)  # 状态更新信号
    finished_signal = pyqtSignal(bool)  # 完成信号（是否成功）

    def __init__(self):
        super().__init__()
        self.tts = TTSPlayer()
        self.file_tool = tool.Tool()

        # 函数映射
        self.func_map = {
            "create_file": self.file_tool.create_file,
            "rename": self.file_tool.rename,
            "delete_file": self.file_tool.delete_file,
            "copy_file": self.file_tool.copy_file,
            "move_file": self.file_tool.move_file,
            "create_dir": self.file_tool.create_dir,
            "delete_dir": self.file_tool.delete_dir
        }

    def run(self):
        """执行完整流程"""
        try:
            # 步骤 1: 录音已完成，直接读取 PCM 文件
            self.status_signal.emit("正在识别语音...")
            self.tts.speak("正在识别语音")

            if not os.path.exists(save_pcm.PCM_SAVE_PATH):
                raise Exception("PCM 文件不存在")

            # 步骤 2: 语音识别
            recognize_text = recongnize.recognize_audio()
            print(f"识别结果：{recognize_text}")

            # 保存识别结果
            with open("recognize_result.txt", "w", encoding='utf-8') as f:
                f.write(recognize_text)

            self.status_signal.emit(f"识别成功：{recognize_text}")
            self.tts.speak(f"识别成功，{recognize_text}")

            # 步骤 3: AI 分析
            self.status_signal.emit("AI 正在分析指令...")
            self.tts.speak("AI 正在分析指令")

            ai_commands = deepseek.call_deepseek(recognize_text, DEEPSEEK_API_KEY)
            print(f"AI 拆分的指令数：{len(ai_commands)}")

            # 处理 API 错误
            if ai_commands and "error" in ai_commands[0]:
                self.status_signal.emit("AI 调用失败，使用离线模式")
                self.tts.speak("AI 调用失败，使用离线模式")

                ai_commands = [
                    {"function_call": {"name": "create_dir",
                                       "parameters": {"dir_path": "C:/Users/32302/Desktop/测试", "exist_ok": True}}},
                    {"function_call": {"name": "create_file",
                                       "parameters": {"filename": "测试.txt", "src_path": "C:/Users/32302/Desktop/测试",
                                                      "content": "测试"}}}
                ]

            # 步骤 4: 批量执行指令
            if ai_commands and "error" not in ai_commands[0]:
                self.status_signal.emit(f"开始执行{len(ai_commands)}个操作...")
                self.tts.speak(f"开始执行{len(ai_commands)}个操作")

                for idx, cmd in enumerate(ai_commands, 1):
                    func_info = cmd["function_call"]
                    func_name = func_info.get("name")
                    params = func_info.get("parameters", {})

                    print(f"\n--- 执行第{idx}步：{func_name} ---")
                    self.status_signal.emit(f"执行第{idx}步：{func_name}")

                    if func_name in self.func_map:
                        exec_result = self.func_map[func_name](**params)
                        print(f"结果：{json.dumps(exec_result, ensure_ascii=False, indent=2)}")

                        # 保存执行结果
                        with open("operation_result.txt", "a", encoding='utf-8') as f:
                            f.write(f"\n=== 第{idx}步：{func_name} ===\n")
                            f.write(json.dumps(exec_result, ensure_ascii=False, indent=2))
                    else:
                        print(f"不支持的函数：{func_name}")

                self.status_signal.emit("所有操作执行完成！")
                self.tts.speak("所有操作执行完成")
                self.finished_signal.emit(True)
            else:
                self.status_signal.emit("没有需要执行的操作")
                self.tts.speak("没有需要执行的操作")
                self.finished_signal.emit(False)

        except recongnize.RecognizeError as e:
            error_msg = f"语音识别失败：{e}"
            self.status_signal.emit(error_msg)
            self.tts.speak(error_msg)
            self.finished_signal.emit(False)
        except Exception as e:
            error_msg = f"程序运行出错：{e}"
            self.status_signal.emit(error_msg)
            self.tts.speak(error_msg)
            print(f"\n❌ 程序运行出错：{e}")
            import traceback
            traceback.print_exc()
            self.finished_signal.emit(False)


class FloatingWindow(QWidget):
    """悬浮窗类"""

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.worker_thread = None
        self.tts = TTSPlayer()

        self.init_ui()
        self.init_style()

    def init_ui(self):
        """初始化界面"""
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 设置窗口大小和位置
        self.setGeometry(100, 100, 150, 150)

        # 创建主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 创建按钮
        self.record_btn = QPushButton("🎤\n点击录音", self)
        self.record_btn.setFixedSize(130, 130)
        self.record_btn.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.clicked.connect(self.on_record_click)

        layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 创建状态标签
        self.status_label = QLabel("准备就绪", self)
        self.status_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; padding: 5px;")

        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def init_style(self):
        """初始化样式"""
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border-radius: 65px;
                color: white;
                border: 3px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
                border: 3px solid #3d8b40;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 10px;
                padding: 5px;
            }
        """)

    def on_record_click(self):
        """点击录音按钮"""
        if not self.is_recording:
            # 开始录音
            self.start_recording()
        else:
            # 停止录音并执行流程
            self.stop_recording_and_execute()

    def start_recording(self):
        """开始录音"""
        self.is_recording = True
        self.record_btn.setText("⏹️\n点击停止")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                border-radius: 65px;
                color: white;
                border: 3px solid #da190b;
            }
            QPushButton:hover {
                background-color: #da190b;
                border: 3px solid #c2170b;
            }
            QPushButton:pressed {
                background-color: #c2170b;
            }
        """)

        self.status_label.setText("录音中...")
        self.update_status_style("recording")

        # 调用录音
        is_rec, _ = save_pcm.toggle_recording()

        self.tts.speak("开始录音")
        print("🎤 开始录音...")

    def stop_recording_and_execute(self):
        """停止录音并执行后续流程"""
        self.is_recording = False
        self.record_btn.setText("⏳\n处理中...")
        self.record_btn.setEnabled(False)

        self.status_label.setText("正在处理...")
        self.update_status_style("processing")

        # 停止录音
        save_pcm.toggle_recording()

        self.tts.speak("录音结束，正在处理")
        print("⏹️ 录音结束，开始处理...")

        # 启动后台线程执行完整流程
        self.worker_thread = WorkerThread()
        self.worker_thread.status_signal.connect(self.update_status)
        self.worker_thread.finished_signal.connect(self.on_task_finished)
        self.worker_thread.start()

    def update_status(self, status_text):
        """更新状态文本"""
        self.status_label.setText(status_text[:20])  # 限制显示长度

    def update_status_style(self, status_type):
        """根据状态类型更新样式"""
        if status_type == "recording":
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(244, 67, 54, 200);
                    border-radius: 10px;
                    padding: 5px;
                    color: white;
                }
            """)
        elif status_type == "processing":
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 152, 0, 200);
                    border-radius: 10px;
                    padding: 5px;
                    color: white;
                }
            """)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 200);
                    border-radius: 10px;
                    padding: 5px;
                    color: #666;
                }
            """)

    def on_task_finished(self, success):
        """任务完成回调"""
        self.record_btn.setText("🎤\n点击录音")
        self.record_btn.setEnabled(True)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border-radius: 65px;
                color: white;
                border: 3px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
                border: 3px solid #3d8b40;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

        self.status_label.setText("准备就绪")
        self.update_status_style("ready")

    def mousePressEvent(self, event):
        """鼠标按下事件（实现拖动）"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖动窗口）"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 创建悬浮窗
    window = FloatingWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
