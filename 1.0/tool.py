# tool.py 完整代码（仅保留核心修复部分）
import os
import json
import shutil


class Tool:
    """文件操作工具类，封装所有文件/目录操作方法"""

    def __init__(self):
        self.default_dir = "./"
        os.makedirs(self.default_dir, exist_ok=True)

    def create_file(
            self,
            filename: str,
            src_path: str = "./",
            content: str = "",
            encoding: str = "utf-8"
    ) -> dict:
        """创建文件（新增详细日志，定位文件未生成问题）"""
        # 1. 参数校验
        if not filename or not isinstance(filename, str):
            return {"status": "failed", "message": "文件名不能为空且必须为字符串"}
        if not isinstance(src_path, str):
            src_path = "./"

        # 2. 拼接路径（新增日志打印）
        full_path = os.path.join(src_path, filename)
        full_path = os.path.normpath(full_path)
        abs_path = os.path.abspath(full_path)
        print(f"[创建文件日志] 目标路径：{abs_path}")  # 关键：打印最终绝对路径

        # 3. 检查文件是否已存在
        if os.path.exists(abs_path):
            return {"status": "failed", "message": f"文件已存在：{abs_path}"}

        # 4. 创建文件（新增逐步骤日志）
        try:
            file_dir = os.path.dirname(abs_path)
            print(f"[创建文件日志] 自动创建目录：{file_dir}")
            os.makedirs(file_dir, exist_ok=True)

            print(f"[创建文件日志] 写入内容：{content[:20]}..." if content else "[创建文件日志] 写入空内容")
            with open(abs_path, "w", encoding=encoding) as f:
                f.write(content)

            # 校验文件是否真的生成
            if os.path.exists(abs_path):
                file_size = os.path.getsize(abs_path)
                return {
                    "status": "success",
                    "message": f"文件创建成功（大小：{file_size} 字节）",
                    "file_path": abs_path
                }
            else:
                return {"status": "failed", "message": f"文件创建后消失：{abs_path}"}

        except PermissionError:
            return {"status": "failed", "message": f"权限不足：{abs_path}（请检查文件夹写权限）"}
        except Exception as e:
            return {"status": "failed", "message": f"创建失败：{str(e)} | 目标路径：{abs_path}"}

    def rename(
            self,
            old_name: str,
            new_name: str,
            src_path: str = "./",
            overwrite: bool = False
    ) -> dict:
        """重命名文件（保持原有逻辑）"""
        if not old_name or not isinstance(old_name, str):
            return {"status": "failed", "message": "原文件名不能为空且必须为字符串"}
        if not new_name or not isinstance(new_name, str):
            return {"status": "failed", "message": "新文件名不能为空且必须为字符串"}
        if not isinstance(src_path, str):
            src_path = "./"

        old_full_path = os.path.normpath(os.path.join(src_path, old_name))
        new_full_path = os.path.normpath(os.path.join(src_path, new_name))
        old_abs_path = os.path.abspath(old_full_path)
        new_abs_path = os.path.abspath(new_full_path)

        if not os.path.exists(old_abs_path):
            return {"status": "failed", "message": f"原文件不存在：{old_abs_path}"}
        if not os.path.isfile(old_abs_path):
            return {"status": "failed", "message": f"指定路径不是文件：{old_abs_path}"}
        if os.path.exists(new_abs_path) and not overwrite:
            return {"status": "failed", "message": f"新文件已存在（禁止覆盖）：{new_abs_path}"}

        try:
            if os.path.exists(new_abs_path) and overwrite:
                os.remove(new_abs_path)
            os.rename(old_abs_path, new_abs_path)

            return {
                "status": "success",
                "message": "文件重命名成功",
                "old_path": old_abs_path,
                "new_path": new_abs_path
            }
        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法重命名：{old_abs_path}"}
        except Exception as e:
            return {"status": "failed", "message": f"重命名失败：{str(e)}"}

    def delete_file(
            self,
            file_path: str,
            to_recycle: bool = True
    ) -> dict:
        """
        删除文件（支持移到回收站/永久删除，适配DeepSeek参数规则）
        :param file_path: 文件完整路径（必选，如 "./test_rename/old_test.txt" 或 "C:/test.txt"）
        :param to_recycle: 是否移到系统回收站（True=移回收站，False=永久删除），默认True（更安全）
        :return: 执行结果字典
                 成功：{"status": "success", "message": "删除成功", "file_path": 文件路径, "delete_type": "回收站/永久删除"}
                 失败：{"status": "failed", "message": "失败原因"}
        """
        # ========== 1. 参数校验 ==========
        if not file_path or not isinstance(file_path, str):
            return {"status": "failed", "message": "文件路径不能为空且必须为字符串"}

        # 转为绝对路径，避免解析异常
        abs_file_path = os.path.abspath(file_path)
        print(f"[删除文件日志] 目标文件：{abs_file_path}")

        # ========== 2. 前置检查 ==========
        # 检查文件是否存在
        if not os.path.exists(abs_file_path):
            return {"status": "failed", "message": f"文件不存在：{abs_file_path}"}
        # 检查是否是文件（不是目录）
        if not os.path.isfile(abs_file_path):
            return {"status": "failed", "message": f"指定路径不是文件：{abs_file_path}"}

        # ========== 3. 执行删除 ==========
        try:
            if to_recycle:
                # 移到系统回收站（需安装 send2trash 库：pip install send2trash）
                try:
                    from send2trash import send2trash
                    send2trash(abs_file_path)
                    delete_type = "回收站"
                except ImportError:
                    # 未安装send2trash则降级为永久删除，并提示
                    os.remove(abs_file_path)
                    delete_type = "永久删除（未安装send2trash库）"
                except Exception as e:
                    # 移回收站失败则降级为永久删除
                    os.remove(abs_file_path)
                    delete_type = f"永久删除（移回收站失败：{str(e)}）"
            else:
                # 直接永久删除
                os.remove(abs_file_path)
                delete_type = "永久删除"

            return {
                "status": "success",
                "message": f"文件已{delete_type}",
                "file_path": abs_file_path,
                "delete_type": delete_type
            }
        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法删除：{abs_file_path}"}
        except Exception as e:
            return {"status": "failed", "message": f"删除文件失败：{str(e)} | 文件路径：{abs_file_path}"}

    def copy_file(
            self,
            src_path: str,
            dst_path: str,
            overwrite: bool = False
    ) -> dict:
        """
        复制文件（适配DeepSeek参数规则，支持文件/目录级复制）
        :param src_path: 源文件完整路径（必选，如 "./test_rename/old_test.txt"）
        :param dst_path: 目标路径（必选，支持2种场景：1.目标文件路径 2.目标目录路径）
        :param overwrite: 目标文件已存在时是否覆盖，默认False（避免误删）
        :return: 执行结果字典
                 成功：{"status": "success", "message": "复制成功", "src_path": 源路径, "dst_path": 目标路径}
                 失败：{"status": "failed", "message": "失败原因"}
        """
        # ========== 1. 参数校验 ==========
        if not src_path or not isinstance(src_path, str):
            return {"status": "failed", "message": "源文件路径不能为空且必须为字符串"}
        if not dst_path or not isinstance(dst_path, str):
            return {"status": "failed", "message": "目标路径不能为空且必须为字符串"}

        # 转为绝对路径，避免解析异常
        src_abs_path = os.path.abspath(src_path)
        dst_abs_path = os.path.abspath(dst_path)
        print(f"[复制文件日志] 源文件：{src_abs_path} | 目标路径：{dst_abs_path}")

        # ========== 2. 前置检查 ==========
        # 检查源文件是否存在且是文件
        if not os.path.exists(src_abs_path):
            return {"status": "failed", "message": f"源文件不存在：{src_abs_path}"}
        if not os.path.isfile(src_abs_path):
            return {"status": "failed", "message": f"源路径不是文件：{src_abs_path}"}

        # 处理目标路径（区分「目标文件」和「目标目录」）
        final_dst_path = dst_abs_path
        if os.path.isdir(dst_abs_path):
            # 目标是目录：拼接源文件名，复制到该目录下
            src_filename = os.path.basename(src_abs_path)
            final_dst_path = os.path.normpath(os.path.join(dst_abs_path, src_filename))
            print(f"[复制文件日志] 目标是目录，自动拼接文件名：{final_dst_path}")

        # 检查目标文件是否已存在（且不允许覆盖）
        if os.path.exists(final_dst_path) and not overwrite:
            return {"status": "failed", "message": f"目标文件已存在（禁止覆盖）：{final_dst_path}"}

        # ========== 3. 执行复制 ==========
        try:
            # 自动创建目标目录（如果不存在）
            dst_dir = os.path.dirname(final_dst_path)
            os.makedirs(dst_dir, exist_ok=True)

            # 执行复制（覆盖/新建）
            if os.path.exists(final_dst_path) and overwrite:
                os.remove(final_dst_path)  # 先删除旧文件再复制
            shutil.copy2(src_abs_path, final_dst_path)  # copy2保留文件元数据（更完整）

            # 校验复制结果
            if os.path.exists(final_dst_path):
                src_size = os.path.getsize(src_abs_path)
                dst_size = os.path.getsize(final_dst_path)
                if src_size == dst_size:
                    return {
                        "status": "success",
                        "message": f"文件复制成功（大小：{dst_size} 字节）",
                        "src_path": src_abs_path,
                        "dst_path": final_dst_path
                    }
                else:
                    return {"status": "failed", "message": f"复制文件大小不一致：源{src_size}字节 ≠ 目标{dst_size}字节"}
            else:
                return {"status": "failed", "message": f"复制后目标文件消失：{final_dst_path}"}

        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法复制：{final_dst_path}（请检查目标目录写权限）"}
        except Exception as e:
            return {"status": "failed", "message": f"复制文件失败：{str(e)} | 源：{src_abs_path} | 目标：{final_dst_path}"}

    def move_file(
            self,
            src_path: str,
            dst_path: str,
            overwrite: bool = False,
            create_dst_dir: bool = True
    ) -> dict:
        """
        移动文件（剪切+粘贴，适配DeepSeek参数规则，支持文件/目录级移动）
        :param src_path: 源文件完整路径（必选，如 "./test_rename/source.txt"）
        :param dst_path: 目标路径（必选，支持2种场景：1.目标文件路径 2.目标目录路径）
        :param overwrite: 目标文件已存在时是否覆盖，默认False（避免误删）
        :param create_dst_dir: 目标目录不存在时是否自动创建，默认True
        :return: 执行结果字典
                 成功：{"status": "success", "message": "移动成功", "src_path": 源路径, "dst_path": 目标路径}
                 失败：{"status": "failed", "message": "失败原因"}
        """
        # ========== 1. 参数校验 ==========
        if not src_path or not isinstance(src_path, str):
            return {"status": "failed", "message": "源文件路径不能为空且必须为字符串"}
        if not dst_path or not isinstance(dst_path, str):
            return {"status": "failed", "message": "目标路径不能为空且必须为字符串"}
        if not isinstance(create_dst_dir, bool):
            create_dst_dir = True  # 非布尔值默认自动创建目录

        # 转为绝对路径，避免解析异常
        src_abs_path = os.path.abspath(src_path)
        dst_abs_path = os.path.abspath(dst_path)
        print(f"[移动文件日志] 源文件：{src_abs_path} | 目标路径：{dst_abs_path}")

        # ========== 2. 前置检查 ==========
        # 检查源文件是否存在且是文件
        if not os.path.exists(src_abs_path):
            return {"status": "failed", "message": f"源文件不存在：{src_abs_path}"}
        if not os.path.isfile(src_abs_path):
            return {"status": "failed", "message": f"源路径不是文件：{src_abs_path}"}

        # 处理目标路径（区分「目标文件」和「目标目录」）
        final_dst_path = dst_abs_path
        if os.path.isdir(dst_abs_path):
            # 目标是目录：拼接源文件名，移动到该目录下
            src_filename = os.path.basename(src_abs_path)
            final_dst_path = os.path.normpath(os.path.join(dst_abs_path, src_filename))
            print(f"[移动文件日志] 目标是目录，自动拼接文件名：{final_dst_path}")

        # 检查目标文件是否已存在（且不允许覆盖）
        if os.path.exists(final_dst_path) and not overwrite:
            return {"status": "failed", "message": f"目标文件已存在（禁止覆盖）：{final_dst_path}"}

        # ========== 3. 执行移动 ==========
        try:
            # 自动创建目标目录（如果开启且目录不存在）
            dst_dir = os.path.dirname(final_dst_path)
            if create_dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
                print(f"[移动文件日志] 自动创建目标目录：{dst_dir}")

            # 处理覆盖逻辑：先删除旧文件再移动
            if os.path.exists(final_dst_path) and overwrite:
                os.remove(final_dst_path)
                print(f"[移动文件日志] 已删除已存在的目标文件：{final_dst_path}")

            # 执行移动（跨磁盘时shutil.move会自动复制后删除源文件）
            shutil.move(src_abs_path, final_dst_path)

            # 校验移动结果：源文件消失 + 目标文件存在
            if not os.path.exists(src_abs_path) and os.path.exists(final_dst_path):
                return {
                    "status": "success",
                    "message": "文件移动成功",
                    "src_path": src_abs_path,
                    "dst_path": final_dst_path
                }
            elif os.path.exists(src_abs_path):
                return {"status": "failed", "message": f"源文件未删除，移动失败：{src_abs_path}"}
            else:
                return {"status": "failed", "message": f"移动后目标文件消失：{final_dst_path}"}

        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法移动：{final_dst_path}（请检查目标目录写权限）"}
        except Exception as e:
            return {"status": "failed", "message": f"移动文件失败：{str(e)} | 源：{src_abs_path} | 目标：{final_dst_path}"}

    def create_dir(
        self,
        dir_path: str,
        exist_ok: bool = True
    ) -> dict:
        """
        创建目录（支持多级目录，适配DeepSeek参数规则）
        :param dir_path: 要创建的目录路径（必选，如 "./test_dir/2026/03"）
        :param exist_ok: 目录已存在时是否忽略错误，默认True（避免重复创建报错）
        :return: 执行结果字典
                 成功：{"status": "success", "message": "目录创建成功", "dir_path": 目录绝对路径}
                 失败：{"status": "failed", "message": "失败原因"}
        """
        # ========== 1. 参数校验 ==========
        if not dir_path or not isinstance(dir_path, str):
            return {"status": "failed", "message": "目录路径不能为空且必须为字符串"}
        if not isinstance(exist_ok, bool):
            exist_ok = True  # 非布尔值默认忽略已存在错误

        # 转为绝对路径，避免解析异常
        dir_abs_path = os.path.abspath(dir_path)
        print(f"[创建目录日志] 目标目录：{dir_abs_path}")

        # ========== 2. 前置检查 ==========
        # 检查目录是否已存在（且不允许忽略）
        if os.path.exists(dir_abs_path) and not exist_ok:
            return {"status": "failed", "message": f"目录已存在（禁止忽略）：{dir_abs_path}"}
        # 检查路径是否是文件（避免覆盖文件）
        if os.path.exists(dir_abs_path) and os.path.isfile(dir_abs_path):
            return {"status": "failed", "message": f"指定路径是文件，无法创建目录：{dir_abs_path}"}

        # ========== 3. 执行创建 ==========
        try:
            # 创建多级目录（exist_ok=True时，已存在则不报错）
            os.makedirs(dir_abs_path, exist_ok=exist_ok)

            # 校验创建结果
            if os.path.exists(dir_abs_path) and os.path.isdir(dir_abs_path):
                return {
                    "status": "success",
                    "message": "目录创建成功" if not os.path.exists(dir_abs_path) else "目录已存在（忽略错误）",
                    "dir_path": dir_abs_path
                }
            else:
                return {"status": "failed", "message": f"目录创建后不存在：{dir_abs_path}"}

        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法创建目录：{dir_abs_path}（请检查父目录写权限）"}
        except Exception as e:
            return {"status": "failed", "message": f"创建目录失败：{str(e)} | 目标路径：{dir_abs_path}"}

    def delete_dir(
        self,
        dir_path: str,
        recursive: bool = False,
        to_recycle: bool = True
    ) -> dict:
        """
        删除目录（适配DeepSeek参数规则，支持空目录/非空目录、回收站/永久删除）
        :param dir_path: 要删除的目录路径（必选，如 "./test_dir/2026/03"）
        :param recursive: 是否递归删除非空目录（默认False，仅删除空目录，更安全）
        :param to_recycle: 是否移到系统回收站（True=移回收站，False=永久删除），默认True（仅Windows支持）
        :return: 执行结果字典
                 成功：{"status": "success", "message": "目录删除成功", "dir_path": 目录绝对路径, "delete_type": "回收站/永久删除"}
                 失败：{"status": "failed", "message": "失败原因"}
        """
        # ========== 1. 参数校验 ==========
        if not dir_path or not isinstance(dir_path, str):
            return {"status": "failed", "message": "目录路径不能为空且必须为字符串"}
        if not isinstance(recursive, bool):
            recursive = False  # 非布尔值默认仅删除空目录
        if not isinstance(to_recycle, bool):
            to_recycle = True  # 非布尔值默认移到回收站

        # 转为绝对路径，避免解析异常
        dir_abs_path = os.path.abspath(dir_path)
        print(f"[删除目录日志] 目标目录：{dir_abs_path} | 递归删除：{recursive} | 移回收站：{to_recycle}")

        # ========== 2. 前置检查 ==========
        # 检查目录是否存在
        if not os.path.exists(dir_abs_path):
            return {"status": "failed", "message": f"目录不存在：{dir_abs_path}"}
        # 检查路径是否是目录（不是文件）
        if not os.path.isdir(dir_abs_path):
            return {"status": "failed", "message": f"指定路径不是目录：{dir_abs_path}"}
        # 检查目录是否非空（且未开启递归删除）
        if not recursive and len(os.listdir(dir_abs_path)) > 0:
            return {"status": "failed", "message": f"目录非空（禁止递归删除）：{dir_abs_path} | 请设置recursive=True"}

        # ========== 3. 执行删除 ==========
        try:
            delete_type = ""
            if to_recycle:
                # 移到系统回收站（需安装 send2trash 库：pip install send2trash）
                try:
                    from send2trash import send2trash
                    send2trash(dir_abs_path)
                    delete_type = "回收站"
                except ImportError:
                    # 未安装send2trash则降级为永久删除
                    if recursive:
                        shutil.rmtree(dir_abs_path)
                    else:
                        os.rmdir(dir_abs_path)
                    delete_type = "永久删除（未安装send2trash库）"
                except Exception as e:
                    # 移回收站失败则降级为永久删除
                    if recursive:
                        shutil.rmtree(dir_abs_path)
                    else:
                        os.rmdir(dir_abs_path)
                    delete_type = f"永久删除（移回收站失败：{str(e)}）"
            else:
                # 直接永久删除
                if recursive:
                    shutil.rmtree(dir_abs_path)  # 删除非空目录
                else:
                    os.rmdir(dir_abs_path)       # 仅删除空目录
                delete_type = "永久删除"

            # 校验删除结果
            if not os.path.exists(dir_abs_path):
                return {
                    "status": "success",
                    "message": f"目录已{delete_type}",
                    "dir_path": dir_abs_path,
                    "delete_type": delete_type
                }
            else:
                return {"status": "failed", "message": f"目录删除后仍存在：{dir_abs_path}"}

        except PermissionError:
            return {"status": "failed", "message": f"权限不足，无法删除目录：{dir_abs_path}（请关闭目录相关程序）"}
        except Exception as e:
            return {"status": "failed", "message": f"删除目录失败：{str(e)} | 目标路径：{dir_abs_path}"}


# ========== 测试函数（带路径校验） ==========
if __name__ == "__main__":
    tool = Tool()
    # 初始化测试目录（创建空目录+非空目录）
    import shutil
    base_test_dir = "./test_delete_dir"
    empty_dir = f"{base_test_dir}/empty_dir"
    non_empty_dir = f"{base_test_dir}/non_empty_dir"
    # 清空旧目录
    if os.path.exists(base_test_dir):
        shutil.rmtree(base_test_dir)
    # 创建测试目录和文件
    os.makedirs(empty_dir, exist_ok=True)
    os.makedirs(non_empty_dir, exist_ok=True)
    tool.create_file(filename="test_file.txt", src_path=non_empty_dir, content="用于测试的非空目录文件")
    print(f"[测试日志] 已创建测试目录：空目录={empty_dir} | 非空目录={non_empty_dir}")

    # 1. 测试场景1：删除空目录（移到回收站）
    delete_res1 = tool.delete_dir(
        dir_path=empty_dir,
        recursive=False,
        to_recycle=True
    )
    print("\n===== 删除空目录（移到回收站）结果 =====")
    print(json.dumps(delete_res1, ensure_ascii=False, indent=2))

    # 2. 测试场景2：删除非空目录（未开启递归，预期失败）
    delete_res2 = tool.delete_dir(
        dir_path=non_empty_dir,
        recursive=False,  # 仅删除空目录
        to_recycle=True
    )
    print("\n===== 删除非空目录（禁止递归）结果 =====")
    print(json.dumps(delete_res2, ensure_ascii=False, indent=2))

    # 3. 测试场景3：递归删除非空目录（永久删除）
    delete_res3 = tool.delete_dir(
        dir_path=non_empty_dir,
        recursive=True,   # 递归删除非空目录
        to_recycle=False  # 永久删除
    )
    print("\n===== 递归删除非空目录（永久删除）结果 =====")
    print(json.dumps(delete_res3, ensure_ascii=False, indent=2))

    # 4. 测试场景4：删除不存在的目录（异常场景）
    delete_res4 = tool.delete_dir(
        dir_path=f"{base_test_dir}/nonexist_dir",
        recursive=True
    )
    print("\n===== 删除不存在的目录结果 =====")
    print(json.dumps(delete_res4, ensure_ascii=False, indent=2))

    # 手动校验删除结果
    print("\n===== 手动校验删除结果 =====")
    for check_dir in [empty_dir, non_empty_dir]:
        if os.path.exists(check_dir):
            print(f"❌ 目录仍存在：{check_dir}")
        else:
            print(f"✅ 目录已删除：{check_dir}")