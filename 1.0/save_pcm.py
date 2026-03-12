import pyaudio
import os
import threading
import time

# ====================== 核心配置（固定为百度/通用PCM标准） ======================
CHUNK = 1024  # 音频块大小（无需改）
FORMAT = pyaudio.paInt16  # 16位深度（PCM必选）
CHANNELS = 1  # 单声道（ASR通用）
RATE = 16000  # 16000采样率（主流ASR都支持）
MAX_RECORD_SECONDS = 30  # 最大录音时长（30秒自动结束）
PCM_SAVE_PATH = "wait_identify/voice_input.pcm"  # 保存的PCM文件路径

# 全局控制变量
is_recording = False  # 录音状态标记
record_frames = []  # 存储录音数据
record_thread = None  # 录音线程


def record_audio():
    """
    实际录音逻辑（后台线程执行）
    """
    global record_frames, is_recording
    record_frames = []  # 清空历史数据

    # 初始化音频录制
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"\n🎤 录音中（最长{MAX_RECORD_SECONDS}秒），按【回车键】结束录音...")

    # 循环录音，直到停止信号或超时
    start_time = time.time()
    while is_recording:
        # 检查是否超时
        if time.time() - start_time >= MAX_RECORD_SECONDS:
            print(f"\n⏰ 录音超时（{MAX_RECORD_SECONDS}秒），自动结束！")
            break

        # 读取音频数据
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            record_frames.append(data)
        except Exception as e:
            print(f"\n⚠️  音频读取异常：{e}")
            break

    # 停止录音
    stream.stop_stream()
    stream.close()
    p.terminate()

    # 保存录音文件
    if record_frames:
        try:
            # 确保保存目录存在
            pcm_dir = os.path.dirname(PCM_SAVE_PATH)
            if not os.path.exists(pcm_dir):
                os.makedirs(pcm_dir)

            # 写入PCM文件
            with open(PCM_SAVE_PATH, "wb") as f:
                f.write(b''.join(record_frames))

            abs_path = os.path.abspath(PCM_SAVE_PATH)
            print(f"\n✅ 录音完成！文件保存至：{abs_path}")
            return abs_path
        except Exception as e:
            print(f"\n❌ 保存PCM文件失败：{e}")
            return None
    else:
        print("\n❌ 未录制到任何音频数据！")
        return None


def start_recording():
    """
    启动录音（重置状态+启动线程）
    """
    global is_recording, record_thread
    if not is_recording:
        is_recording = True
        # 启动录音线程
        record_thread = threading.Thread(target=record_audio)
        record_thread.daemon = True  # 守护线程，主程序退出时自动结束
        record_thread.start()


def stop_recording():
    """
    停止录音
    """
    global is_recording
    if is_recording:
        is_recording = False
        # 等待录音线程结束
        if record_thread:
            record_thread.join()


def record_to_pcm():
    """
    交互式录音函数（按回车键启停）
    :return: 成功返回 PCM 文件绝对路径，失败返回 None
    """
    global is_recording

    print("=====================================")
    print("🎙️  语音录制工具")
    print("=====================================")
    print(f"提示：按【回车键】开始/结束录音（最长{MAX_RECORD_SECONDS}秒）")
    print("=====================================")

    while True:
        # 等待用户输入（仅响应回车键）
        input("请按回车键开始录音：")  # 直接捕获回车，无需判断输入内容

        if not is_recording:
            # 开始录音
            start_recording()
        else:
            # 停止录音
            stop_recording()
            # 退出循环，返回结果
            if os.path.exists(PCM_SAVE_PATH):
                return os.path.abspath(PCM_SAVE_PATH)
            else:
                return None


def toggle_recording():
    """
    切换录音状态（用于悬浮窗调用，返回当前状态和 PCM 路径）
    :return: (is_recording: bool, pcm_path: str or None)
             如果刚开始录音，返回 (True, None)
             如果停止录音，返回 (False, pcm_path)
    """
    global is_recording

    if not is_recording:
        # 开始录音
        start_recording()
        return True, None
    else:
        # 停止录音
        stop_recording()
        time.sleep(0.5)  # 等待保存完成
        pcm_path = os.path.abspath(PCM_SAVE_PATH) if os.path.exists(PCM_SAVE_PATH) else None
        return False, pcm_path


# 运行主函数
if __name__ == "__main__":
    record_to_pcm()