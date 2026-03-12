import requests
import json


def call_deepseek(prompt: str, api_key: str) -> list:
    """
    调用DeepSeek API，支持返回多个函数调用指令（列表形式）
    支持的函数：create_file / rename / delete_file / copy_file / move_file / create_dir / delete_dir
    :param prompt: 用户输入字符串（语音识别结果）
    :param api_key: DeepSeek API Key
    :return: 解析后的指令列表（每个元素为一个函数调用字典）/ 空列表 / 错误列表
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}"
    }

    # 核心改造：System指令要求拆分多步骤并返回JSON数组
    system_prompt = """
你必须严格遵守以下规则生成JSON，无任何例外：
1. 分析用户指令，拆分为多个独立的文件操作步骤（按执行顺序排列），每个步骤对应一个函数调用；
2. 输出格式必须是JSON数组，数组中每个元素是一个对象，包含：
   - "function_call"：对象，包含：
     - "name"：函数名（仅允许：create_file、rename、delete_file、copy_file、move_file、create_dir、delete_dir）；
     - "parameters"：函数参数（字典格式，根据函数需求定义）；
3. 参数默认值规则：
   - 桌面的path是"C:/Users/32302/Desktop/"
   - 未说明src_path则默认为"./"；
   - create_file的content未说明则默认为空字符串；
   - delete_file/delete_dir的to_recycle未说明则默认为true；
   - copy_file/move_file的overwrite未说明则默认为false；
   - move_file的create_dst_dir未说明则默认为true；
   - create_dir的exist_ok未说明则默认为true；
   - delete_dir的recursive未说明则默认为false；
   - 函数中不存在的参数自动忽略，不加入JSON；
   - 布尔值参数必须使用JSON原生的true/false，禁止使用字符串"True"/"False"；
   - 路径参数优先使用绝对路径，无绝对路径时使用相对路径（./开头）；
4. 非文件操作指令返回空数组[]；
5. 禁止添加任何额外文字、注释、解释，仅返回纯JSON字符串；
6. 函数参数详细说明：
   - create_file：必选filename；可选src_path（默认./）、content（默认""）
   - rename：必选old_name、new_name；可选src_path（默认./）
   - delete_file：必选file_path；可选to_recycle（默认true）
   - copy_file：必选src_path、dst_path；可选overwrite（默认false）
   - move_file：必选src_path、dst_path；可选overwrite（默认false）、create_dst_dir（默认true）
   - create_dir：必选dir_path；可选exist_ok（默认true）
   - delete_dir：必选dir_path；可选recursive（默认false）、to_recycle（默认true）
7. 多步骤示例：
   - 用户说"帮我在桌面创建一个名为测试的文件夹，文件夹里创建一个名为测试的文件，文件内容是测试" → 
     返回：
     [
       {"function_call":{"name":"create_dir","parameters":{"dir_path":"C:/Users/32302/Desktop/测试","exist_ok":true}}},
       {"function_call":{"name":"create_file","parameters":{"filename":"测试.txt","src_path":"C:/Users/32302/Desktop/测试","content":"测试"}}}
     ]
   - 用户说"删除桌面的file.txt文件，然后在桌面创建一个新的test.txt文件" →
     返回：
     [
       {"function_call":{"name":"delete_file","parameters":{"file_path":"C:/Users/32302/Desktop/file.txt","to_recycle":true}}},
       {"function_call":{"name":"create_file","parameters":{"filename":"test.txt","src_path":"C:/Users/32302/Desktop/","content":""}}}
     ]
   - 用户说"你好" → 返回：[]
""".strip()

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 2048,  # 增大token上限，容纳多步骤
        "response_format": {"type": "json_object"},
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"[调试信息] HTTP状态码：{response.status_code}")
        print(f"[调试信息] 响应内容：{response.text}")

        response.raise_for_status()

        result = response.json()
        if not result or "choices" not in result or len(result["choices"]) == 0:
            return []

        message = result["choices"][0].get("message", {})
        json_str = message.get("content", "").strip()
        if not json_str:
            return []

        # 核心改造：解析JSON数组（支持多指令）
        reply_list = json.loads(json_str)
        if not isinstance(reply_list, list):
            return []

        # 二次校验：过滤非法指令，保留有效指令
        allowed_functions = ["create_file", "rename", "delete_file", "copy_file", "move_file", "create_dir",
                             "delete_dir"]
        valid_commands = []
        for cmd in reply_list:
            if "function_call" in cmd:
                func_name = cmd["function_call"].get("name", "")
                params = cmd["function_call"].get("parameters", {})
                # 校验函数名合法性
                if func_name in allowed_functions and isinstance(params, dict):
                    # 校验必选参数
                    required_params = {
                        "create_file": ["filename"],
                        "rename": ["old_name", "new_name"],
                        "delete_file": ["file_path"],
                        "copy_file": ["src_path", "dst_path"],
                        "move_file": ["src_path", "dst_path"],
                        "create_dir": ["dir_path"],
                        "delete_dir": ["dir_path"]
                    }
                    has_required = True
                    if func_name in required_params:
                        for param in required_params[func_name]:
                            if param not in params:
                                has_required = False
                                break
                    if has_required:
                        valid_commands.append(cmd)
        return valid_commands

    except requests.exceptions.RequestException as e:
        # 请求异常返回错误列表（保持返回类型统一）
        return [{"error": f"请求失败：{str(e)}"}]
    except json.JSONDecodeError:
        return []
    except KeyError as e:
        return []
    except Exception as e:
        return []


# ========== 测试函数（验证多指令生成+执行） ==========
if __name__ == "__main__":
    # 替换为你的DeepSeek API Key
    API_KEY = "sk-d46115c9e435433fb9febfec8d05bed4"
    # 初始化Tool类
    from tool import Tool

    tool = Tool()

    # 测试案例：多步骤指令（创建文件夹+创建文件）
    prompt = "帮我在桌面创建一个名为测试的文件夹，文件夹里创建一个名为测试的文件，文件内容是测试"
    # 调用DeepSeek获取多指令结果
    deepseek_results = call_deepseek(prompt, API_KEY)
    print("===== DeepSeek返回的多指令结果 =====")
    print(json.dumps(deepseek_results, ensure_ascii=False, indent=2))

    # 批量执行多指令
    if deepseek_results and "error" not in deepseek_results[0]:
        # 函数映射（对接Tool类）
        func_map = {
            "create_file": tool.create_file,
            "rename": tool.rename,
            "delete_file": tool.delete_file,
            "copy_file": tool.copy_file,
            "move_file": tool.move_file,
            "create_dir": tool.create_dir,
            "delete_dir": tool.delete_dir
        }

        # 按顺序执行每个指令
        for idx, cmd in enumerate(deepseek_results, 1):
            func_info = cmd["function_call"]
            func_name = func_info["name"]
            params = func_info["parameters"]

            print(f"\n===== 执行第{idx}个指令 =====")
            print(f"函数名：{func_name}")
            print(f"参数：{json.dumps(params, ensure_ascii=False, indent=2)}")

            if func_name in func_map:
                exec_result = func_map[func_name](**params)
                print(f"执行结果：{json.dumps(exec_result, ensure_ascii=False, indent=2)}")
    elif deepseek_results and "error" in deepseek_results[0]:
        print(f"\n❌ API调用错误：{deepseek_results[0]['error']}")
        # 离线模拟多指令（API调用失败时测试）
        print("\n===== 启用离线模拟模式 =====")
        mock_commands = [
            {"function_call": {"name": "create_dir",
                               "parameters": {"dir_path": "C:/Users/32302/Desktop/测试", "exist_ok": true}}},
            {"function_call": {"name": "create_file",
                               "parameters": {"filename": "测试.txt", "src_path": "C:/Users/32302/Desktop/测试",
                                              "content": "测试"}}}
        ]
        # 执行模拟指令
        for idx, cmd in enumerate(mock_commands, 1):
            func_info = cmd["function_call"]
            func_name = func_info["name"]
            params = func_info["parameters"]

            print(f"\n===== 执行模拟第{idx}个指令 =====")
            exec_result = func_map[func_name](**params)
            print(f"执行结果：{json.dumps(exec_result, ensure_ascii=False, indent=2)}")
    else:
        print("\nℹ️ 无有效指令需要执行")