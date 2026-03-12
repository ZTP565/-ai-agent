# coding=utf-8
import sys
import json
import base64
import time
import os


# ========== 1. 定义异常类（方便外部捕获） ==========
class RecognizeError(Exception):
    """语音识别异常类"""
    pass


# ========== 2. 基础配置（集中管理） ==========
IS_PY3 = sys.version_info.major == 3
API_KEY = 'HAc2ZisLRv9pQAbPeOe7uehg'
SECRET_KEY = 'BJWW0TJYtiui1jmUDBk7HlOXi7AVZIRH'
AUDIO_FILE = 'wait_identify/voice_input.pcm'
CUID = '123456PYTHON'
RATE = 16000
DEV_PID = 1537
ASR_URL = 'http://vop.baidu.com/server_api'
TOKEN_URL = 'http://aip.baidubce.com/oauth/2.0/token'
SCOPE = 'audio_voice_assistant_get'

# ========== 3. Python3兼容处理 ==========
if IS_PY3:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    from urllib.parse import urlencode

    timer = time.perf_counter
else:
    from urllib2 import urlopen, Request, URLError
    from urllib import urlencode

    timer = time.clock if sys.platform == "win32" else time.time


# ========== 4. 封装Token获取函数（内部使用） ==========
def _fetch_token():
    """内部函数：获取百度语音识别Token"""
    params = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': SECRET_KEY
    }
    post_data = urlencode(params)
    if IS_PY3:
        post_data = post_data.encode('utf-8')

    req = Request(TOKEN_URL, post_data)
    try:
        f = urlopen(req, timeout=10)
        result_str = f.read()
    except URLError as err:
        raise RecognizeError(f'Token请求失败，HTTP状态码: {err.code if hasattr(err, "code") else "未知"}')

    if IS_PY3:
        result_str = result_str.decode('utf-8')

    result = json.loads(result_str)
    if 'access_token' in result and 'scope' in result:
        if SCOPE and SCOPE not in result['scope'].split(' '):
            raise RecognizeError('应用未开通语音识别权限，请在百度控制台勾选scope')
        return result['access_token']
    else:
        error_msg = result.get('error_description', '未知错误')
        raise RecognizeError(f'密钥错误或权限不足：{error_msg}')


# ========== 5. 封装核心识别函数（对外暴露） ==========
def recognize_audio(audio_file: str = None) -> str:
    """
    百度语音识别核心函数（对外暴露）
    :param audio_file: 可选，指定音频文件路径（默认使用配置的AUDIO_FILE）
    :return: 识别出的纯文本结果
    :raise RecognizeError: 识别过程中出现任何错误都会抛出该异常
    """
    # 1. 确定音频文件路径
    audio_path = audio_file or AUDIO_FILE

    # 2. 检查文件是否存在
    if not os.path.exists(audio_path):
        raise RecognizeError(f'音频文件不存在：{audio_path}')

    # 3. 读取音频文件
    with open(audio_path, 'rb') as speech_file:
        speech_data = speech_file.read()
    if len(speech_data) == 0:
        raise RecognizeError(f'音频文件为空：{audio_path}')

    # 4. 获取Token
    token = _fetch_token()

    # 5. 编码音频数据
    speech = base64.b64encode(speech_data)
    if IS_PY3:
        speech = speech.decode('utf-8')
    format = audio_path[-3:]  # 获取文件格式（pcm/wav/amr）

    # 6. 构建识别请求参数
    params = {
        'dev_pid': DEV_PID,
        'format': format,
        'rate': RATE,
        'token': token,
        'cuid': CUID,
        'channel': 1,
        'speech': speech,
        'len': len(speech_data)
    }
    post_data = json.dumps(params, sort_keys=False).encode('utf-8')

    # 7. 发送识别请求
    req = Request(ASR_URL, post_data)
    req.add_header('Content-Type', 'application/json')
    try:
        begin = timer()
        f = urlopen(req, timeout=20)
        result_str = f.read().decode('utf-8') if IS_PY3 else f.read()
        print(f"识别请求耗时：{timer() - begin:.2f}秒")
    except URLError as err:
        raise RecognizeError(f'识别请求失败，HTTP状态码: {err.code if hasattr(err, "code") else "未知"}')

    # 8. 解析识别结果
    result_json = json.loads(result_str)
    if result_json['err_no'] != 0:
        raise RecognizeError(f'识别失败：{result_json["err_msg"]}')

    # 9. 提取纯文本并返回
    recognize_text = result_json['result'][0].strip()
    return recognize_text

# 读取recognize_result.txt的核心代码
def read_recognize_result(file_path: str = "recognize_result.txt") -> str:
    """
    读取语音识别结果文件
    :param file_path: 文件路径（默认是recognize_result.txt）
    :return: 文件中的识别文本（空字符串表示文件不存在/读取失败）
    """
    try:
        # 关键：指定encoding='utf-8'，避免中文乱码
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()  # strip()去除首尾空格/换行
        return content
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        return ""
    except Exception as e:
        print(f"读取文件失败：{e}")
        return ""


# ========== 6. 原main逻辑（保留，方便单独测试） ==========
if __name__ == '__main__':
    try:
        # 测试调用识别函数
        text = recognize_audio()
        print(f"识别结果：{text}")
        # 保存结果到文件（可选）
        with open("recognize_result.txt", "w", encoding='utf-8') as f:
            f.write(text)
    except RecognizeError as e:
        print(f"识别出错：{e}")