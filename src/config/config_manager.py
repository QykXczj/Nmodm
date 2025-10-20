"""
配置管理器
负责游戏路径配置、破解文件管理等功能
"""
import os
import sys
import shutil
import struct
from pathlib import Path
from typing import Optional, Dict, Any
from src.i18n import t


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        # 处理打包后的路径问题
        if getattr(sys, 'frozen', False):
            # 打包后的环境：可执行文件所在目录
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境：源代码目录
            self.root_dir = Path(__file__).parent.parent.parent
        self.onlinefix_dir = self.root_dir / "OnlineFix"
        self.config_file = self.onlinefix_dir / "gconfig.ini"
        
    def get_game_path(self) -> Optional[str]:
        """获取游戏路径"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    path = f.read().strip().strip('"')
                    return path if path else None
            return None
        except Exception as e:
            print(f"读取游戏路径失败: {e}")
            return None
    
    def set_game_path(self, game_path: str) -> bool:
        """设置游戏路径"""
        try:
            # 验证路径是否存在
            if not os.path.exists(game_path):
                return False
            
            # 验证是否为nightreign.exe
            if not game_path.lower().endswith('nightreign.exe'):
                return False
            
            # 保存路径到配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f'"{game_path}"\n')
            
            return True
        except Exception as e:
            print(f"保存游戏路径失败: {e}")
            return False
    
    def validate_game_path(self, game_path: str = None) -> bool:
        """验证游戏路径有效性"""
        if game_path is None:
            game_path = self.get_game_path()
        
        if not game_path:
            return False
        
        return (os.path.exists(game_path) and 
                game_path.lower().endswith('nightreign.exe'))
    
    def get_game_directory(self) -> Optional[str]:
        """获取游戏目录"""
        game_path = self.get_game_path()
        if game_path and self.validate_game_path(game_path):
            return os.path.dirname(game_path)
        return None

    def ensure_onlinefix_available(self) -> bool:
        """确保OnlineFix文件可用"""
        try:
            # 检查关键的破解文件是否存在
            required_files = [
                "OnlineFix.ini",
                "OnlineFix64.dll",
                "dlllist.txt",
                "winmm.dll"
            ]

            missing_files = []
            for filename in required_files:
                file_path = self.onlinefix_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if not missing_files:
                print("✅ OnlineFix文件完整")
                return True

            print(f"⚠️ 发现缺失的OnlineFix文件: {', '.join(missing_files)}")

            # 检查OnlineFix.zip是否存在
            onlinefix_zip = self.onlinefix_dir / "OnlineFix.zip"
            if onlinefix_zip.exists():
                print("📦 发现OnlineFix.zip，尝试解压...")
                if self.extract_onlinefix_zip():
                    # 重新检查文件完整性
                    missing_files = []
                    for filename in required_files:
                        file_path = self.onlinefix_dir / filename
                        if not file_path.exists():
                            missing_files.append(filename)

                    if not missing_files:
                        print("✅ OnlineFix文件解压完成")
                        return True
                    else:
                        print(f"❌ 解压后仍缺失文件: {', '.join(missing_files)}")
                        return False
                else:
                    print("❌ OnlineFix.zip解压失败")
                    return False
            else:
                # OnlineFix.zip也不存在，无法继续
                print("❌ OnlineFix.zip不存在，无法修复破解文件")
                return False

        except Exception as e:
            print(f"❌ 检查OnlineFix可用性失败: {e}")
            return False

    def extract_onlinefix_zip(self) -> bool:
        """解压OnlineFix.zip文件"""
        try:
            import zipfile
            import time

            onlinefix_zip = self.onlinefix_dir / "OnlineFix.zip"
            if not onlinefix_zip.exists():
                return False

            print(f"📦 开始解压OnlineFix.zip")

            with zipfile.ZipFile(onlinefix_zip, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.is_dir():
                        continue

                    filename = Path(file_info.filename).name
                    target_path = self.onlinefix_dir / filename

                    if target_path.exists():
                        target_path.unlink()

                    with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)

                    print(f"✅ 解压完成: {filename}")

            # 创建解压完成标志
            extracted_flag = self.onlinefix_dir / ".onlinefix_extracted"
            extracted_flag.write_text(f"OnlineFix extracted at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("🎉 OnlineFix解压完成")
            return True

        except Exception as e:
            print(f"❌ OnlineFix解压失败: {e}")
            return False



    def apply_crack(self) -> bool:
        """应用破解文件"""
        try:
            # 首先确保OnlineFix文件可用
            if not self.ensure_onlinefix_available():
                print("❌ OnlineFix文件不可用，无法应用破解")
                return False

            game_dir = self.get_game_directory()
            if not game_dir:
                print("❌ 无法获取游戏目录")
                return False

            # 检查游戏目录写入权限
            game_dir_path = Path(game_dir)
            if not os.access(game_dir_path, os.W_OK):
                print(f"❌ 游戏目录无写入权限: {game_dir}")
                return False

            # 定义需要复制的破解文件（白名单模式）
            required_crack_files = {
                "OnlineFix.ini",    # 破解配置文件
                "OnlineFix64.dll",  # 主破解DLL
                "dlllist.txt",      # DLL列表文件
                "winmm.dll"         # Windows多媒体API钩子
            }

            # 记录操作结果
            success_files = []
            failed_files = []

            # 只复制白名单中的破解文件到游戏目录
            for crack_filename in required_crack_files:
                file_path = self.onlinefix_dir / crack_filename
                if file_path.exists() and file_path.is_file():
                    try:
                        dest_path = Path(game_dir) / crack_filename
                        shutil.copy2(file_path, dest_path)

                        # 验证文件是否成功复制
                        if dest_path.exists() and dest_path.stat().st_size == file_path.stat().st_size:
                            success_files.append(crack_filename)
                            print(f"✅ 应用破解文件: {crack_filename}")
                        else:
                            failed_files.append(crack_filename)
                            print(f"❌ 文件复制验证失败: {crack_filename}")
                    except Exception as e:
                        failed_files.append(crack_filename)
                        print(f"❌ 复制文件失败 {crack_filename}: {e}")
                else:
                    failed_files.append(crack_filename)
                    print(f"❌ 源文件不存在: {crack_filename}")

            # 检查操作结果
            if failed_files:
                print(f"❌ 部分文件应用失败: {', '.join(failed_files)}")
                return False

            if not success_files:
                print("❌ 没有找到需要应用的破解文件")
                return False

            # 最终验证：检查破解状态
            if self.is_crack_applied():
                print(f"✅ 破解应用成功，共处理 {len(success_files)} 个文件")
                return True
            else:
                print("❌ 破解应用后验证失败")
                return False

        except Exception as e:
            print(f"应用破解失败: {e}")
            return False
    
    def remove_crack(self) -> bool:
        """移除破解文件"""
        try:
            # 移除破解时不需要检查OnlineFix可用性，因为我们只是删除文件
            game_dir = self.get_game_directory()
            if not game_dir:
                print("❌ 无法获取游戏目录")
                return False

            # 检查游戏目录写入权限
            game_dir_path = Path(game_dir)
            if not os.access(game_dir_path, os.W_OK):
                print(f"❌ 游戏目录无写入权限: {game_dir}")
                return False

            # 定义需要移除的破解文件（与apply_crack保持一致）
            required_crack_files = {
                "OnlineFix.ini",    # 破解配置文件
                "OnlineFix64.dll",  # 主破解DLL
                "dlllist.txt",      # DLL列表文件
                "winmm.dll"         # Windows多媒体API钩子
            }

            # 记录操作结果
            success_files = []
            failed_files = []

            # 删除游戏目录中的破解文件
            for crack_filename in required_crack_files:
                crack_file = Path(game_dir) / crack_filename
                if crack_file.exists():
                    try:
                        crack_file.unlink()

                        # 验证文件是否成功删除
                        if not crack_file.exists():
                            success_files.append(crack_filename)
                            print(f"✅ 移除破解文件: {crack_filename}")
                        else:
                            failed_files.append(crack_filename)
                            print(f"❌ 文件删除验证失败: {crack_filename}")
                    except Exception as e:
                        failed_files.append(crack_filename)
                        print(f"❌ 删除文件失败 {crack_filename}: {e}")

            # 检查操作结果
            if failed_files:
                print(f"❌ 部分文件移除失败: {', '.join(failed_files)}")
                return False

            # 最终验证：检查破解状态
            if not self.is_crack_applied():
                if success_files:
                    print(f"✅ 破解移除成功，共处理 {len(success_files)} 个文件")
                else:
                    print("✅ 破解文件已不存在，无需移除")
                return True
            else:
                print("❌ 破解移除后验证失败，仍检测到破解文件")
                return False

        except Exception as e:
            print(f"移除破解失败: {e}")
            return False
    
    def is_crack_applied(self) -> bool:
        """检查是否已应用破解"""
        try:
            game_dir = self.get_game_directory()
            if not game_dir:
                return False

            # 定义必需的破解补丁文件（所有文件都必须存在）
            required_crack_files = {
                "dlllist.txt",      # DLL列表文件
                "OnlineFix.ini",    # 破解配置文件
                "OnlineFix64.dll",  # 主破解DLL
                "winmm.dll"         # Windows多媒体API钩子
            }

            # 检查所有必需的破解文件是否都存在
            missing_files = []
            for crack_filename in required_crack_files:
                crack_file = Path(game_dir) / crack_filename
                if not crack_file.exists():
                    missing_files.append(crack_filename)

            # 如果有文件缺失，返回False（UI会显示详细信息）
            if missing_files:
                return False

            # 所有必需文件都存在才认为已应用破解
            return True
        except Exception as e:
            print(f"检查破解状态失败: {e}")
            return False

    def get_crack_status_info(self) -> tuple[bool, str]:
        """获取破解状态和详细信息"""
        try:
            game_dir = self.get_game_directory()
            if not game_dir:
                return False, t("config_manager.error.cannot_get_dir")

            # 定义必需的破解补丁文件
            required_crack_files = {
                "dlllist.txt",      # DLL列表文件
                "OnlineFix.ini",    # 破解配置文件
                "OnlineFix64.dll",  # 主破解DLL
                "winmm.dll"         # Windows多媒体API钩子
            }

            # 检查所有必需的破解文件是否都存在
            missing_files = []
            for crack_filename in required_crack_files:
                crack_file = Path(game_dir) / crack_filename
                if not crack_file.exists():
                    missing_files.append(crack_filename)

            # 返回状态和详细信息
            if missing_files:
                missing_info = t("config_manager.error.missing_files").format(files=', '.join(missing_files))
                return False, missing_info
            else:
                return True, t("config_manager.status.files_complete")

        except Exception as e:
            return False, t("config_manager.error.check_failed").format(error=str(e))

    def get_nightreign_version(self) -> Optional[str]:
        """获取nightreign.exe的版本信息"""
        try:
            game_path = self.get_game_path()
            if not game_path or not os.path.exists(game_path):
                return None

            # 方法1: 使用Windows API获取文件版本信息
            version = self._get_version_with_win32api(game_path)
            if version:
                return version

            # 方法2: 使用pefile库解析PE文件
            version = self._get_version_with_pefile(game_path)
            if version:
                return version

            # 方法3: 使用文件属性作为备用方案
            return self._get_version_from_file_info(game_path)

        except Exception as e:
            print(f"获取nightreign.exe版本失败: {e}")
            return None

    def _get_version_with_win32api(self, file_path: str) -> Optional[str]:
        """使用Windows API获取版本信息"""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(file_path, "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            # 移除末尾的.0
            version = version.rstrip('.0')
            return version if version != "0.0.0" else None
        except (ImportError, Exception):
            return None

    def _get_version_with_pefile(self, file_path: str) -> Optional[str]:
        """使用pefile库获取版本信息"""
        try:
            import pefile
            pe = pefile.PE(file_path)

            if hasattr(pe, 'VS_VERSIONINFO'):
                for file_info in pe.FileInfo[0]:
                    if file_info.Key.decode() == 'StringFileInfo':
                        for st in file_info.StringTable:
                            for entry in st.entries.items():
                                if entry[0].decode() in ['FileVersion', 'ProductVersion']:
                                    version = entry[1].decode().strip()
                                    if version and version != "0.0.0.0":
                                        return version.rstrip('.0')
            return None
        except (ImportError, Exception):
            return None

    def _get_version_from_file_info(self, file_path: str) -> Optional[str]:
        """从文件信息获取版本标识（备用方法）"""
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size

            # 使用文件大小和修改时间生成版本标识
            import time
            import hashlib

            # 创建基于文件属性的版本标识
            file_info = f"{file_size}_{int(stat.st_mtime)}"
            version_hash = hashlib.md5(file_info.encode()).hexdigest()[:8]

            # 格式化为版本号样式
            modification_time = time.strftime("%Y.%m.%d", time.localtime(stat.st_mtime))
            return f"{modification_time}.{version_hash}"

        except Exception as e:
            print(f"从文件信息获取版本失败: {e}")
            return None

    def get_nightreign_file_info(self) -> Dict[str, Any]:
        """获取nightreign.exe的详细文件信息"""
        try:
            game_path = self.get_game_path()
            if not game_path or not os.path.exists(game_path):
                return {"error": t("config_manager.error.file_not_exist")}

            stat = os.stat(game_path)
            import time

            return {
                "file_path": game_path,
                "file_size": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "creation_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
                "modification_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "access_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_atime)),
                "version": self.get_nightreign_version()
            }

        except Exception as e:
            return {"error": t("config_manager.error.get_file_info_failed").format(error=str(e))}

    def get_steam_api_size(self) -> Optional[int]:
        """获取steam_api64.dll的文件大小（字节）"""
        try:
            game_path = self.get_game_path()
            if not game_path or not os.path.exists(game_path):
                return None

            # 获取游戏目录
            game_dir = os.path.dirname(game_path)
            steam_dll_path = os.path.join(game_dir, "steam_api64.dll")

            if os.path.exists(steam_dll_path):
                return os.path.getsize(steam_dll_path)
            else:
                return None

        except Exception as e:
            print(f"获取steam_api64.dll大小失败: {e}")
            return None

    def get_desteam_api_size(self) -> Optional[int]:
        """获取desteam_api64.dll的文件大小（字节）- 保持向后兼容"""
        return self.get_steam_api_size()

    def get_game_info(self) -> Dict[str, Any]:
        """获取游戏相关信息的综合方法"""
        try:
            game_path = self.get_game_path()
            if not game_path:
                return {
                    "game_path": None,
                    "game_exists": False,
                    "nightreign_version": None,
                    "steam_api_size": None,
                    "steam_api_exists": False,
                    "steam_api_size_mb": None,
                    # 保持向后兼容
                    "desteam_api_size": None,
                    "desteam_api_exists": False,
                    "desteam_api_size_mb": None,
                    "error": t("config_manager.error.path_not_set")
                }

            game_exists = os.path.exists(game_path)
            if not game_exists:
                return {
                    "game_path": game_path,
                    "game_exists": False,
                    "nightreign_version": None,
                    "steam_api_size": None,
                    "steam_api_exists": False,
                    "steam_api_size_mb": None,
                    # 保持向后兼容
                    "desteam_api_size": None,
                    "desteam_api_exists": False,
                    "desteam_api_size_mb": None,
                    "error": t("config_manager.error.file_not_exist")
                }

            # 获取版本信息
            version = self.get_nightreign_version()

            # 获取steam_api64.dll信息
            steam_api_size = self.get_steam_api_size()
            steam_api_exists = steam_api_size is not None

            return {
                "game_path": game_path,
                "game_exists": True,
                "nightreign_version": version,
                "steam_api_size": steam_api_size,
                "steam_api_exists": steam_api_exists,
                "steam_api_size_mb": round(steam_api_size / (1024 * 1024), 2) if steam_api_size else None,
                # 保持向后兼容的字段名
                "desteam_api_size": steam_api_size,
                "desteam_api_exists": steam_api_exists,
                "desteam_api_size_mb": round(steam_api_size / (1024 * 1024), 2) if steam_api_size else None,
                "error": None
            }

        except Exception as e:
            return {
                "game_path": None,
                "game_exists": False,
                "nightreign_version": None,
                "steam_api_size": None,
                "steam_api_exists": False,
                "steam_api_size_mb": None,
                # 保持向后兼容
                "desteam_api_size": None,
                "desteam_api_exists": False,
                "desteam_api_size_mb": None,
                "error": t("config_manager.error.get_info_failed").format(error=str(e))
            }

    def check_nmodm_path_chinese(self) -> Dict[str, Any]:
        """检测Nmodm软件本身路径是否包含中文字符"""
        try:
            # 获取Nmodm软件的根目录路径
            nmodm_path = str(self.root_dir)

            # 检测是否包含中文字符
            has_chinese = self._contains_chinese(nmodm_path)

            # 如果包含中文，提取中文字符
            chinese_chars = []
            if has_chinese:
                chinese_chars = self._extract_chinese_chars(nmodm_path)

            return {
                "nmodm_path": nmodm_path,
                "has_chinese": has_chinese,
                "chinese_characters": chinese_chars,
                "is_safe": not has_chinese,
                "warning": t("config_manager.warning.chinese_path") if has_chinese else None,
                "recommendation": t("config_manager.recommendation.move_to_english") if has_chinese else t("config_manager.status.path_safe"),
                "error": None
            }

        except Exception as e:
            return {
                "nmodm_path": None,
                "has_chinese": None,
                "chinese_characters": [],
                "is_safe": None,
                "warning": None,
                "recommendation": None,
                "error": t("config_manager.error.check_path_failed").format(error=str(e))
            }

    def _contains_chinese(self, text: str) -> bool:
        """检测文本是否包含中文字符"""
        try:
            for char in text:
                # 检测中文字符范围
                if '\u4e00' <= char <= '\u9fff':  # 基本中文字符
                    return True
                elif '\u3400' <= char <= '\u4dbf':  # 扩展A
                    return True
                elif '\u20000' <= char <= '\u2a6df':  # 扩展B
                    return True
                elif '\u2a700' <= char <= '\u2b73f':  # 扩展C
                    return True
                elif '\u2b740' <= char <= '\u2b81f':  # 扩展D
                    return True
                elif '\u2b820' <= char <= '\u2ceaf':  # 扩展E
                    return True
            return False
        except Exception:
            return False

    def _extract_chinese_chars(self, text: str) -> list:
        """提取文本中的中文字符"""
        try:
            chinese_chars = []
            for char in text:
                if '\u4e00' <= char <= '\u9fff':  # 基本中文字符
                    if char not in chinese_chars:
                        chinese_chars.append(char)
                elif '\u3400' <= char <= '\u4dbf':  # 扩展A
                    if char not in chinese_chars:
                        chinese_chars.append(char)
                elif '\u20000' <= char <= '\u2a6df':  # 扩展B
                    if char not in chinese_chars:
                        chinese_chars.append(char)
                elif '\u2b740' <= char <= '\u2b81f':  # 扩展D
                    if char not in chinese_chars:
                        chinese_chars.append(char)
                elif '\u2b820' <= char <= '\u2ceaf':  # 扩展E
                    if char not in chinese_chars:
                        chinese_chars.append(char)
            return chinese_chars
        except Exception:
            return []

    def get_nmodm_info(self) -> Dict[str, Any]:
        """获取Nmodm软件的完整信息"""
        try:
            # 基本路径信息
            nmodm_path = str(self.root_dir)
            path_info = self.check_nmodm_path_chinese()

            # 获取路径统计信息
            import time
            try:
                stat = os.stat(nmodm_path)
                creation_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime))
                modification_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            except:
                creation_time = t("config_manager.status.unknown")
                modification_time = t("config_manager.status.unknown")

            # 检测是否为打包环境
            is_frozen = getattr(sys, 'frozen', False)

            # 检测是否在桌面
            desktop_info = self.check_nmodm_on_desktop()

            # 综合安全性评估
            overall_safe = path_info["is_safe"] and desktop_info["is_safe"]

            # 综合警告信息
            warnings = []
            if path_info["warning"]:
                warnings.append(path_info["warning"])
            if desktop_info["warning"]:
                warnings.append(desktop_info["warning"])

            # 综合建议信息
            recommendations = []
            if path_info["recommendation"] and "建议" in path_info["recommendation"]:
                recommendations.append(path_info["recommendation"])
            if desktop_info["recommendation"] and "建议" in desktop_info["recommendation"]:
                recommendations.append(desktop_info["recommendation"])

            return {
                "nmodm_path": nmodm_path,
                "is_frozen": is_frozen,
                "environment": t("config_manager.status.packaged") if is_frozen else t("config_manager.status.development"),
                "creation_time": creation_time,
                "modification_time": modification_time,
                "path_length": len(nmodm_path),
                # 中文路径相关
                "has_chinese": path_info["has_chinese"],
                "chinese_characters": path_info["chinese_characters"],
                "is_path_safe": path_info["is_safe"],
                "path_warning": path_info["warning"],
                "path_recommendation": path_info["recommendation"],
                # 桌面位置相关
                "is_on_desktop": desktop_info["is_on_desktop"],
                "matched_desktop_path": desktop_info["matched_desktop_path"],
                "is_desktop_safe": desktop_info["is_safe"],
                "desktop_warning": desktop_info["warning"],
                "desktop_recommendation": desktop_info["recommendation"],
                # 综合评估
                "overall_safe": overall_safe,
                "all_warnings": warnings,
                "all_recommendations": recommendations,
                "error": None
            }

        except Exception as e:
            return {
                "nmodm_path": None,
                "is_frozen": None,
                "environment": None,
                "creation_time": None,
                "modification_time": None,
                "path_length": None,
                "has_chinese": None,
                "chinese_characters": [],
                "is_path_safe": None,
                "path_warning": None,
                "path_recommendation": None,
                "error": t("config_manager.error.get_nmodm_info_failed").format(error=str(e))
            }

    def check_nmodm_on_desktop(self) -> Dict[str, Any]:
        """检测Nmodm是否在桌面上"""
        try:
            nmodm_path = str(self.root_dir).lower()

            # 获取桌面路径的多种可能位置
            desktop_paths = self._get_desktop_paths()

            # 检查是否在任何桌面路径下
            is_on_desktop = False
            matched_desktop_path = None

            for desktop_path in desktop_paths:
                if desktop_path and nmodm_path.startswith(desktop_path.lower()):
                    is_on_desktop = True
                    matched_desktop_path = desktop_path
                    break

            return {
                "nmodm_path": str(self.root_dir),
                "is_on_desktop": is_on_desktop,
                "matched_desktop_path": matched_desktop_path,
                "desktop_paths_checked": desktop_paths,
                "is_safe": not is_on_desktop,  # 桌面通常不是最佳位置
                "warning": t("config_manager.warning.on_desktop") if is_on_desktop else None,
                "recommendation": t("config_manager.recommendation.move_to_program") if is_on_desktop else t("config_manager.status.location_good"),
                "error": None
            }

        except Exception as e:
            return {
                "nmodm_path": None,
                "is_on_desktop": None,
                "matched_desktop_path": None,
                "desktop_paths_checked": [],
                "is_safe": None,
                "warning": None,
                "recommendation": None,
                "error": t("config_manager.error.check_desktop_failed").format(error=str(e))
            }

    def _get_desktop_paths(self) -> list:
        """获取可能的桌面路径"""
        desktop_paths = []

        try:
            # 方法1: 使用环境变量
            userprofile = os.environ.get('USERPROFILE')
            if userprofile:
                desktop_paths.append(os.path.join(userprofile, 'Desktop'))
                desktop_paths.append(os.path.join(userprofile, '桌面'))  # 中文系统

            # 方法2: 使用公共桌面
            public = os.environ.get('PUBLIC')
            if public:
                desktop_paths.append(os.path.join(public, 'Desktop'))
                desktop_paths.append(os.path.join(public, '桌面'))

            # 方法3: 使用Windows Shell API（如果可用）
            try:
                import winreg
                # 从注册表获取桌面路径
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                  r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                    desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
                    if desktop_path:
                        desktop_paths.append(desktop_path)
            except:
                pass

            # 方法4: 常见的桌面路径
            common_paths = [
                "C:\\Users\\Public\\Desktop",
                "C:\\Users\\Public\\桌面",
            ]

            # 添加当前用户的常见路径
            username = os.environ.get('USERNAME')
            if username:
                common_paths.extend([
                    f"C:\\Users\\{username}\\Desktop",
                    f"C:\\Users\\{username}\\桌面",
                ])

            desktop_paths.extend(common_paths)

            # 去重并过滤存在的路径
            unique_paths = []
            for path in desktop_paths:
                if path and path not in unique_paths:
                    unique_paths.append(path)

            # 只返回实际存在的路径
            existing_paths = []
            for path in unique_paths:
                try:
                    if os.path.exists(path):
                        existing_paths.append(path)
                except:
                    continue

            return existing_paths

        except Exception as e:
            print(f"获取桌面路径失败: {e}")
            return []
