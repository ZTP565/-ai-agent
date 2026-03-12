import pyaudio
import os
import recongnize
import deepseek
import save_pcm
import tool
import json

# 配置
DEEPSEEK_API_KEY = "sk-d46115c9e435433fb9febfec8d05bed4"


def main():
    """完整的语音识别 + AI多指令分析 + 批量文件操作执行流程"""
    try:
        # 初始化文件操作工具类
        file_tool = tool.Tool()

        # 函数映射：DeepSeek函数名 → Tool类方法
        func_map = {
            "create_file": file_tool.create_file,
            "rename": file_tool.rename,
            "delete_file": file_tool.delete_file,
            "copy_file": file_tool.copy_file,
            "move_file": file_tool.move_file,
            "create_dir": file_tool.create_dir,
            "delete_dir": file_tool.delete_dir
        }

        # 确保 PCM 文件保存目录存在
        pcm_dir = os.path.dirname(save_pcm.PCM_SAVE_PATH)
        if not os.path.exists(pcm_dir):
            os.makedirs(pcm_dir)
            print(f"已创建目录：{pcm_dir}")

        # 录制语音并保存为 PCM 文件
        print("\n=== 开始录音 ===")
        pcm_path = save_pcm.record_to_pcm()
        if not pcm_path:
            print("录音失败，程序终止")
            return
        print(f"录音完成，文件保存至：{pcm_path}")

        # 调用百度语音识别
        print("\n=== 语音识别中 ===")
        recognize_text = recongnize.recognize_audio()
        print(f"识别结果：{recognize_text}")

        # 保存识别结果到文件
        with open("recognize_result.txt", "w", encoding='utf-8') as f:
            f.write(recognize_text)
        print(f"识别结果已保存到：recognize_result.txt")

        # 调用 DeepSeek AI 分析识别结果（返回多指令列表）
        print("\n=== AI 分析中（多指令拆分）===")
        ai_commands = deepseek.call_deepseek(recognize_text, DEEPSEEK_API_KEY)
        print(f"AI 拆分的指令数：{len(ai_commands)}")
        print(f"AI 分析结果：{json.dumps(ai_commands, ensure_ascii=False, indent=2)}")

        # 处理API调用错误
        if ai_commands and "error" in ai_commands[0]:
            print(f"\n❌ AI 调用出错：{ai_commands[0]['error']}")
            # 离线模拟多指令（测试用）
            print("\n=== 启用离线模拟模式 ===")
            ai_commands = [
                {"function_call": {"name": "create_dir",
                                   "parameters": {"dir_path": "C:/Users/32302/Desktop/测试", "exist_ok": true}}},
                {"function_call": {"name": "create_file",
                                   "parameters": {"filename": "测试.txt", "src_path": "C:/Users/32302/Desktop/测试",
                                                  "content": "测试"}}}
            ]
            print(f"模拟多指令：{json.dumps(ai_commands, ensure_ascii=False, indent=2)}")

        # 批量执行多指令
        if ai_commands and "error" not in ai_commands[0]:
            print("\n=== 批量执行文件操作 ===")
            # 按顺序执行每个指令
            for idx, cmd in enumerate(ai_commands, 1):
                func_info = cmd["function_call"]
                func_name = func_info.get("name")
                params = func_info.get("parameters", {})

                print(f"\n--- 执行第{idx}步：{func_name} ---")
                print(f"参数：{json.dumps(params, ensure_ascii=False, indent=2)}")

                if func_name in func_map:
                    try:
                        exec_result = func_map[func_name](**params)
                        print(f"结果：{json.dumps(exec_result, ensure_ascii=False, indent=2)}")

                        # 保存执行结果
                        with open("operation_result.txt", "a", encoding='utf-8') as f:
                            f.write(f"\n=== 第{idx}步：{func_name} ===\n")
                            f.write(json.dumps(exec_result, ensure_ascii=False, indent=2))
                    except Exception as e:
                        print(f"❌ 执行失败：{str(e)}")
                else:
                    print(f"❌ 不支持的函数：{func_name}")
        else:
            print("\nℹ️ 无有效文件操作指令")

    except recongnize.RecognizeError as e:
        print(f"\n❌ 语音识别失败：{e}")
    except Exception as e:
        print(f"\n❌ 程序运行出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("===== 语音控制多步骤文件操作程序 =====")
    main()
    # 帮我在桌面创建名为工作文档的文件夹，里面再创建2026年的子文件夹
    # 2026年文件夹里再创建项目复盘的子文件夹
    # 然后在项目复盘文件夹里创建名为第一季度总结的文本文档
    # 内容写第一季度项目完成率百分之八十五
    # 最后把这个第一季度总结的文件改名为2026第一季度项目复盘