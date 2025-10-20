"""
Mod配置管理器
负责ME3配置文件的生成、读取和管理
"""
import os
import sys
import toml
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ModPackage:
    """Mod包配置"""
    id: str
    source: str
    load_after: Optional[List[Dict[str, Any]]] = None
    load_before: Optional[List[Dict[str, Any]]] = None
    enabled: bool = True
    is_external: bool = False  # 标记是否为外部mod
    comment: str = ""  # 用户备注


@dataclass
class ModNative:
    """Native DLL配置"""
    path: str
    optional: bool = False
    enabled: bool = True
    initializer: Optional[str] = None
    finalizer: Optional[str] = None
    load_after: Optional[List[Dict[str, Any]]] = None
    load_before: Optional[List[Dict[str, Any]]] = None
    is_external: bool = False  # 标记是否为外部DLL
    comment: str = ""  # 用户备注


class ModConfigManager:
    """Mod配置管理器"""
    
    def __init__(self):
        # 处理打包后的路径问题
        if getattr(sys, 'frozen', False):
            # 打包后的环境：可执行文件所在目录
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境：源代码目录
            self.root_dir = Path(__file__).parent.parent.parent
        self.mods_dir = self.root_dir / "Mods"
        self.config_file = self.mods_dir / "current.me3"
        self.external_config_file = self.mods_dir / "external_mods.json"
        self.profile_version = "v1"

        # 确保Mods目录存在
        self.mods_dir.mkdir(exist_ok=True)

        # 当前配置
        self.packages: List[ModPackage] = []
        self.natives: List[ModNative] = []

        # 外部mod路径存储
        self.external_packages: Dict[str, str] = {}  # {mod_name: full_path}
        self.external_natives: Dict[str, str] = {}   # {dll_name: full_path}

        # mod备注存储
        self.mod_comments: Dict[str, str] = {}  # {mod_id: comment}
        self.native_comments: Dict[str, str] = {}  # {dll_path: comment}

        # 加载外部mod配置
        self.load_external_mods()
    
    def scan_mods_directory(self) -> Dict[str, List[str]]:
        """扫描Mods目录和外部mod，返回可用的mod包和DLL"""
        packages = []
        natives = []

        # 扫描Mods目录
        if self.mods_dir.exists():
            for item in self.mods_dir.iterdir():
                if item.is_dir() and item.name not in ["__pycache__", ".git"]:
                    # 智能检测mod类型
                    mod_type = self._detect_mod_type(item)

                    if mod_type == "folder":
                        # 文件夹型mod：包含regulation.bin或典型mod结构的mod包
                        packages.append(item.name)
                    elif mod_type == "dll":
                        # DLL型mod：扫描文件夹内的所有DLL文件
                        dll_files = self._scan_dll_files(item)
                        for dll_file in dll_files:
                            # dll_file已经包含完整的相对路径
                            natives.append(dll_file)
                    elif mod_type == "mixed":
                        # 混合型mod：既作为mod包又包含DLL文件
                        packages.append(item.name)
                        dll_files = self._scan_dll_files(item)
                        for dll_file in dll_files:
                            # dll_file已经包含完整的相对路径
                            natives.append(dll_file)
                elif item.is_file() and item.suffix.lower() == ".dll":
                    # 直接在Mods目录下的DLL文件（保持兼容性）
                    # 排除非mod DLL文件
                    excluded_dlls = {
                        'libzstd.dll',
                        'oo2core_9_win64.dll',
                        'steam_api64.dll'
                    }
                    if item.name.lower() not in excluded_dlls:
                        natives.append(item.name)

        # 添加外部mod包
        for mod_name, mod_path in self.external_packages.items():
            if Path(mod_path).exists() and mod_name not in packages:
                packages.append(f"{mod_name} (外部)")

        # 添加外部DLL
        for dll_name, dll_path in self.external_natives.items():
            if Path(dll_path).exists() and dll_name not in natives:
                natives.append(f"{dll_name} (外部)")

        return {"packages": packages, "natives": natives}

    def _detect_mod_type(self, mod_path: Path) -> str:
        """智能检测mod类型

        Args:
            mod_path: mod文件夹路径

        Returns:
            str: "folder" (文件夹型mod), "dll" (DLL型mod), "mixed" (混合型mod), "unknown" (未知类型)
        """
        try:
            has_regulation = False
            has_dll = False
            has_typical_folders = False

            # 检查是否包含regulation.bin文件
            regulation_file = mod_path / "regulation.bin"
            if regulation_file.exists():
                has_regulation = True

            # 检查是否包含典型的mod文件夹结构
            typical_folders = ["msg", "param", "chr", "script", "sfx", "map", "parts", "menu", "movie", "sd"]
            for folder_name in typical_folders:
                if (mod_path / folder_name).exists():
                    has_typical_folders = True
                    break

            # 检查是否包含其他mod特征文件
            mod_files = [
                "mod.ini", "config.ini", "settings.ini",
                "*.pak", "*.bnd", "*.bhd", "*.bdt"
            ]
            has_mod_files = False
            for pattern in mod_files:
                if list(mod_path.glob(pattern)):
                    has_mod_files = True
                    break

            # 检查是否包含DLL文件（排除非mod DLL）
            excluded_dlls = {
                'libzstd.dll',
                'oo2core_9_win64.dll',
                'steam_api64.dll'
            }

            dll_files = [dll for dll in mod_path.glob("*.dll")
                        if dll.name.lower() not in excluded_dlls]
            if dll_files:
                has_dll = True

            # 递归检查子目录中的DLL文件（深度限制为1层）
            if not has_dll:
                for subdir in mod_path.iterdir():
                    if subdir.is_dir():
                        dll_files = [dll for dll in subdir.glob("*.dll")
                                   if dll.name.lower() not in excluded_dlls]
                        if dll_files:
                            has_dll = True
                            break

            # 智能分类逻辑
            if has_regulation or has_typical_folders or has_mod_files:
                if has_dll:
                    return "mixed"  # 混合型：既有文件夹特征又有DLL
                else:
                    return "folder"  # 纯文件夹型
            elif has_dll:
                return "dll"  # 纯DLL型
            else:
                return "unknown"  # 未知类型

        except (OSError, PermissionError):
            return "unknown"

    def _scan_dll_files(self, mod_path: Path) -> List[str]:
        """扫描mod文件夹中的所有DLL文件

        Args:
            mod_path: mod文件夹路径

        Returns:
            List[str]: DLL文件相对路径列表（相对于mod文件夹）
        """
        dll_files = []

        # 排除的非mod DLL文件
        excluded_dlls = {
            'libzstd.dll',
            'oo2core_9_win64.dll',
            'steam_api64.dll'
        }

        try:
            # 扫描根目录的DLL文件
            for dll_file in mod_path.glob("*.dll"):
                if dll_file.name.lower() not in excluded_dlls:
                    # 对于根目录的DLL，使用 mod文件夹名/dll文件名 格式
                    dll_path = f"{mod_path.name}/{dll_file.name}"
                    dll_files.append(dll_path)

            # 扫描子目录的DLL文件（深度限制为1层）
            for subdir in mod_path.iterdir():
                if subdir.is_dir():
                    for dll_file in subdir.glob("*.dll"):
                        if dll_file.name.lower() not in excluded_dlls:
                            # 对于子目录的DLL，使用 mod文件夹名/子目录名/dll文件名 格式
                            dll_path = f"{mod_path.name}/{subdir.name}/{dll_file.name}"
                            dll_files.append(dll_path)
        except (OSError, PermissionError):
            pass

        return dll_files

    def _is_mod_package(self, path: Path) -> bool:
        """检查目录是否为有效的mod包（保持向后兼容）"""
        # 使用新的智能检测方法
        mod_type = self._detect_mod_type(path)
        return mod_type in ["folder", "dll", "mixed"]
    
    def load_config(self, config_path: Optional[str] = None) -> bool:
        """加载配置文件"""
        try:
            if config_path:
                config_file = Path(config_path)
            else:
                config_file = self.config_file
            
            if not config_file.exists():
                # 如果配置文件不存在，创建默认配置
                self.packages = []
                self.natives = []
                return True
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
            
            # 解析packages
            self.packages = []
            for pkg_data in config_data.get('packages', []):
                pkg_id = pkg_data['id']
                pkg_source = pkg_data.get('source', pkg_data.get('path', ''))

                # 判断是否为外部mod
                is_external = pkg_id in self.external_packages

                package = ModPackage(
                    id=pkg_id,
                    source=pkg_source,
                    load_after=pkg_data.get('load_after'),
                    load_before=pkg_data.get('load_before'),
                    enabled=pkg_data.get('enabled', True),
                    is_external=is_external
                )
                self.packages.append(package)
            
            # 解析natives
            self.natives = []
            for native_data in config_data.get('natives', []):
                native_path = native_data['path']

                # 判断是否为外部DLL
                # 检查路径是否在外部DLL列表中，或者DLL名称是否在外部列表中
                is_external = False
                dll_name = Path(native_path).name

                # 检查完整路径匹配
                if native_path in self.external_natives.values():
                    is_external = True
                # 检查DLL名称匹配
                elif dll_name in self.external_natives:
                    is_external = True

                native = ModNative(
                    path=native_path,
                    optional=native_data.get('optional', False),
                    enabled=native_data.get('enabled', True),
                    initializer=native_data.get('initializer'),
                    finalizer=native_data.get('finalizer'),
                    load_after=native_data.get('load_after'),
                    load_before=native_data.get('load_before'),
                    is_external=is_external
                )
                self.natives.append(native)
            
            return True
        except Exception as e:
            print(f"加载配置失败: {e}")
            return False
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """保存配置文件"""
        try:
            if config_path:
                config_file = Path(config_path)
            else:
                config_file = self.config_file
            
            # 构建配置数据
            config_data = {
                'profileVersion': self.profile_version
            }
            
            # 添加packages
            if self.packages:
                config_data['packages'] = []
                for package in self.packages:
                    if package.enabled:  # 只保存启用的包
                        pkg_dict = {
                            'id': package.id,
                            'source': package.source
                        }
                        if package.load_after:
                            pkg_dict['load_after'] = package.load_after
                        if package.load_before:
                            pkg_dict['load_before'] = package.load_before
                        config_data['packages'].append(pkg_dict)
            
            # 添加natives
            if self.natives:
                config_data['natives'] = []
                for native in self.natives:
                    if native.enabled:  # 只保存启用的DLL
                        native_dict = {
                            'path': native.path
                        }
                        if native.optional:
                            native_dict['optional'] = native.optional
                        if native.initializer:
                            native_dict['initializer'] = native.initializer
                        if native.finalizer:
                            native_dict['finalizer'] = native.finalizer
                        if native.load_after:
                            native_dict['load_after'] = native.load_after
                        if native.load_before:
                            native_dict['load_before'] = native.load_before
                        config_data['natives'].append(native_dict)
            
            # 保存到文件 - 使用自定义格式化以确保正确的TOML格式
            with open(config_file, 'w', encoding='utf-8') as f:
                self._write_custom_toml(config_data, f)
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def add_package(self, package_id: str, source_path: str, enabled: bool = True) -> bool:
        """添加mod包"""
        # 处理外部mod标识
        is_external = package_id.endswith(" (外部)")
        clean_id = package_id.replace(" (外部)", "") if is_external else package_id

        # 检查ID是否已存在
        for pkg in self.packages:
            if pkg.id == clean_id:
                return False

        # 确定源路径
        if is_external and clean_id in self.external_packages:
            actual_source = self.external_packages[clean_id]
        else:
            actual_source = source_path

        package = ModPackage(id=clean_id, source=actual_source, enabled=enabled, is_external=is_external)
        self.packages.append(package)
        return True
    
    def remove_package(self, package_id: str) -> bool:
        """移除mod包"""
        # 处理外部mod标识
        clean_id = package_id.replace(" (外部)", "")

        for i, pkg in enumerate(self.packages):
            if pkg.id == clean_id:
                del self.packages[i]
                return True
        return False
    
    def toggle_package(self, package_id: str) -> bool:
        """切换mod包启用状态"""
        # 处理外部mod标识
        clean_id = package_id.replace(" (外部)", "")

        for pkg in self.packages:
            if pkg.id == clean_id:
                pkg.enabled = not pkg.enabled
                return True
        return False
    
    def add_native(self, dll_path: str, optional: bool = False, enabled: bool = True) -> bool:
        """添加native DLL"""
        # 处理外部DLL标识
        is_external = dll_path.endswith(" (外部)")
        clean_path = dll_path.replace(" (外部)", "") if is_external else dll_path

        # 检查路径是否已存在
        for native in self.natives:
            if native.path == clean_path:
                return False

        # 确定实际路径
        if is_external and clean_path in self.external_natives:
            actual_path = self.external_natives[clean_path]
        else:
            # 对于内部DLL，使用传入的路径（已经包含正确的相对路径）
            actual_path = clean_path

        native = ModNative(path=actual_path, optional=optional, enabled=enabled, is_external=is_external)
        self.natives.append(native)
        return True
    
    def remove_native(self, dll_path: str) -> bool:
        """移除native DLL"""
        # 处理外部DLL标识
        clean_path = dll_path.replace(" (外部)", "")

        for i, native in enumerate(self.natives):
            # 匹配条件：
            # 1. 直接路径匹配
            # 2. DLL名称匹配（对于外部DLL）
            # 3. 路径结尾匹配（处理完整路径vs文件名的情况）
            if (native.path == clean_path or
                native.path == dll_path or
                native.path.endswith(clean_path) or
                (native.is_external and Path(native.path).name == clean_path)):
                del self.natives[i]
                return True
        return False
    
    def toggle_native(self, dll_path: str) -> bool:
        """切换native DLL启用状态"""
        # 处理外部DLL标识
        clean_path = dll_path.replace(" (外部)", "")

        for native in self.natives:
            # 匹配条件：
            # 1. 直接路径匹配
            # 2. DLL名称匹配（对于外部DLL）
            # 3. 路径结尾匹配（处理完整路径vs文件名的情况）
            if (native.path == clean_path or
                native.path == dll_path or
                native.path.endswith(clean_path) or
                (native.is_external and Path(native.path).name == clean_path)):
                native.enabled = not native.enabled
                return True
        return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        enabled_packages = [pkg for pkg in self.packages if pkg.enabled]
        enabled_natives = [native for native in self.natives if native.enabled]
        
        return {
            "total_packages": len(self.packages),
            "enabled_packages": len(enabled_packages),
            "total_natives": len(self.natives),
            "enabled_natives": len(enabled_natives),
            "packages": enabled_packages,
            "natives": enabled_natives
        }
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，返回 1(v1>v2), 0(相等), -1(v1<v2)"""
        if not v1 or not v2:
            return 0 if not v1 and not v2 else (1 if v1 else -1)

        # 移除v前缀，分割版本号
        v1_clean = v1.lstrip('v').split('.')
        v2_clean = v2.lstrip('v').split('.')

        # 补齐长度
        max_len = max(len(v1_clean), len(v2_clean))
        v1_clean.extend(['0'] * (max_len - len(v1_clean)))
        v2_clean.extend(['0'] * (max_len - len(v2_clean)))

        # 逐段比较
        for i in range(max_len):
            try:
                n1, n2 = int(v1_clean[i]), int(v2_clean[i])
                if n1 > n2:
                    return 1
                elif n1 < n2:
                    return -1
            except ValueError:
                continue
        return 0

    def get_me3_executable_path(self) -> Optional[str]:
        """获取ME3可执行文件路径（基于版本号智能选择）"""
        # 1. 获取安装版信息
        full_available = False
        full_version = None
        try:
            import subprocess
            env = self._get_system_env()
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(['me3', '-V'],
                                  capture_output=True, text=True, timeout=5,
                                  env=env, creationflags=creation_flags)
            if result.returncode == 0:
                full_available = True
                # 解析版本号
                import re
                output = result.stdout.strip()
                version_match = re.search(r'v?(\d+\.\d+\.\d+)', output)
                if version_match:
                    full_version = f"v{version_match.group(1)}"
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # 2. 获取便携版信息
        portable_available = False
        portable_version = None
        me3_path = self.root_dir / "me3p" / "bin" / "me3.exe"
        if me3_path.exists():
            portable_available = True
            # 获取便携版版本
            try:
                import subprocess
                import sys
                creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                result = subprocess.run([str(me3_path), '-V'],
                                      capture_output=True, text=True, timeout=5,
                                      creationflags=creation_flags)
                if result.returncode == 0:
                    import re
                    output = result.stdout.strip()
                    version_match = re.search(r'v?(\d+\.\d+\.\d+)', output)
                    if version_match:
                        portable_version = f"v{version_match.group(1)}"
            except Exception:
                pass

        # 3. 智能版本选择决策
        if full_available and portable_available:
            # 两个都有，比较版本
            if portable_version and full_version:
                comparison = self._compare_versions(portable_version, full_version)
                if comparison > 0:
                    return str(me3_path)  # 便携版更新
                elif comparison < 0:
                    return "me3"  # 安装版更新
                else:
                    return "me3"  # 同版本优先安装版
            elif portable_version:
                return str(me3_path)  # 只有便携版有版本信息
            elif full_version:
                return "me3"  # 只有安装版有版本信息
            else:
                return "me3"  # 都没有版本信息，优先安装版
        elif full_available:
            return "me3"  # 只有安装版
        elif portable_available:
            return str(me3_path)  # 只有便携版
        else:
            return None  # 都没有

    def _get_system_env(self):
        """获取系统环境变量（排除虚拟环境）"""
        import os
        env = os.environ.copy()

        # 如果在虚拟环境中，过滤掉虚拟环境的PATH
        if 'VIRTUAL_ENV' in env:
            # 获取虚拟环境路径
            venv_path = env['VIRTUAL_ENV']

            # 过滤PATH中的虚拟环境路径
            path_parts = env.get('PATH', '').split(os.pathsep)
            filtered_parts = []

            for part in path_parts:
                # 跳过虚拟环境相关的路径
                if not part.startswith(venv_path):
                    filtered_parts.append(part)

            # 重新构造PATH
            new_path = os.pathsep.join(filtered_parts)
            env['PATH'] = new_path

            # 移除虚拟环境变量
            del env['VIRTUAL_ENV']
            if 'PYTHONHOME' in env:
                del env['PYTHONHOME']

        return env

    def load_external_mods(self):
        """加载外部mod配置"""
        import json

        if not self.external_config_file.exists():
            return

        try:
            with open(self.external_config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.external_packages = data.get('packages', {})
                self.external_natives = data.get('natives', {})
                self.mod_comments = data.get('mod_comments', {})
                self.native_comments = data.get('native_comments', {})
        except Exception as e:
            print(f"加载外部mod配置失败: {e}")
            self.external_packages = {}
            self.external_natives = {}
            self.mod_comments = {}
            self.native_comments = {}

    def save_external_mods(self):
        """保存外部mod配置"""
        import json

        data = {
            'packages': self.external_packages,
            'natives': self.external_natives,
            'mod_comments': self.mod_comments,
            'native_comments': self.native_comments
        }

        try:
            with open(self.external_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存外部mod配置失败: {e}")
            return False

    def add_external_package(self, mod_path: str) -> tuple[bool, str]:
        """添加外部mod包

        Returns:
            tuple[bool, str]: (成功状态, 错误信息)
        """
        mod_path = Path(mod_path)

        if not mod_path.exists() or not mod_path.is_dir():
            return False, "文件夹不存在或不是有效目录"

        # 检查是否在内部Mods目录内
        try:
            # 使用resolve()获取绝对路径，然后检查是否为Mods目录的子路径
            mod_path_resolved = mod_path.resolve()
            mods_dir_resolved = self.mods_dir.resolve()

            # 检查mod_path是否在mods_dir内部
            if mod_path_resolved == mods_dir_resolved or mods_dir_resolved in mod_path_resolved.parents:
                return False, "不能添加内部Mods目录内的文件夹"
        except (OSError, ValueError):
            # 路径解析失败，为安全起见拒绝添加
            return False, "路径解析失败"

        # 检查是否已存在相同路径的外部mod
        mod_path_str = str(mod_path_resolved)
        for existing_name, existing_path in self.external_packages.items():
            try:
                if Path(existing_path).resolve() == mod_path_resolved:
                    return False, f"该路径已作为外部mod '{existing_name}' 添加"
            except (OSError, ValueError):
                # 如果现有路径无法解析，继续检查其他路径
                continue

        mod_name = mod_path.name

        # 检查是否已存在同名的外部mod（但路径不同）
        if mod_name in self.external_packages:
            existing_path = self.external_packages[mod_name]
            if existing_path != mod_path_str:
                return False, f"已存在同名外部mod '{mod_name}'，但路径不同"

        self.external_packages[mod_name] = mod_path_str
        if self.save_external_mods():
            return True, "添加成功"
        else:
            return False, "保存配置失败"

    def get_all_dll_names(self) -> set[str]:
        """获取所有DLL名称（内部和外部）

        Returns:
            set[str]: 所有DLL文件名的集合
        """
        dll_names = set()

        # 获取内部DLL名称
        if self.mods_dir.exists():
            for item in self.mods_dir.iterdir():
                if item.is_dir() and item.name not in ["__pycache__", ".git"]:
                    # 检查DLL型mod
                    mod_type = self._detect_mod_type(item)
                    if mod_type == "dll":
                        dll_files = self._scan_dll_files(item)
                        dll_names.update(dll_files)
                elif item.is_file() and item.suffix.lower() == ".dll":
                    # 直接在Mods目录下的DLL文件
                    dll_names.add(item.name)

        # 获取外部DLL名称
        dll_names.update(self.external_natives.keys())

        return dll_names

    def add_external_native(self, dll_path: str) -> tuple[bool, str]:
        """添加外部DLL

        Returns:
            tuple[bool, str]: (成功状态, 错误信息)
        """
        dll_path = Path(dll_path)

        if not dll_path.exists() or not dll_path.is_file():
            return False, "文件不存在或不是有效文件"

        if dll_path.suffix.lower() != '.dll':
            return False, "文件不是DLL格式"

        # 检查是否在内部Mods目录内
        try:
            # 使用resolve()获取绝对路径，然后检查是否为Mods目录的子路径
            dll_path_resolved = dll_path.resolve()
            mods_dir_resolved = self.mods_dir.resolve()

            # 检查dll_path是否在mods_dir内部
            if mods_dir_resolved in dll_path_resolved.parents:
                return False, "不能添加内部Mods目录内的DLL文件"
        except (OSError, ValueError):
            # 路径解析失败，为安全起见拒绝添加
            return False, "路径解析失败"

        # 检查是否已存在相同路径的外部DLL
        dll_path_str = str(dll_path_resolved)
        for existing_name, existing_path in self.external_natives.items():
            try:
                if Path(existing_path).resolve() == dll_path_resolved:
                    return False, f"该路径已作为外部DLL '{existing_name}' 添加"
            except (OSError, ValueError):
                # 如果现有路径无法解析，继续检查其他路径
                continue

        dll_name = dll_path.name

        # 检查DLL名称重复（包括内部和外部DLL）
        existing_dll_names = self.get_all_dll_names()
        if dll_name in existing_dll_names:
            # 检查是否是同一个外部DLL的重复添加
            if dll_name in self.external_natives:
                existing_path = self.external_natives[dll_name]
                if existing_path != dll_path_str:
                    return False, f"已存在同名外部DLL '{dll_name}'，但路径不同"
                else:
                    return False, f"该DLL '{dll_name}' 已经添加过了"
            else:
                # 与内部DLL重复
                return False, f"已存在同名DLL '{dll_name}'，不能添加重复的DLL文件"

        self.external_natives[dll_name] = dll_path_str
        if self.save_external_mods():
            return True, "添加成功"
        else:
            return False, "保存配置失败"

    def remove_external_package(self, mod_name: str) -> bool:
        """移除外部mod包"""
        if mod_name in self.external_packages:
            del self.external_packages[mod_name]
            # 同时移除相关的备注
            if mod_name in self.mod_comments:
                del self.mod_comments[mod_name]
            return self.save_external_mods()
        return False

    def remove_external_native(self, dll_name: str) -> bool:
        """移除外部DLL"""
        if dll_name in self.external_natives:
            del self.external_natives[dll_name]
            # 同时移除相关的备注
            if dll_name in self.native_comments:
                del self.native_comments[dll_name]
            return self.save_external_mods()
        return False

    def set_mod_comment(self, mod_id: str, comment: str):
        """设置mod备注"""
        if comment.strip():
            self.mod_comments[mod_id] = comment.strip()
        elif mod_id in self.mod_comments:
            del self.mod_comments[mod_id]
        self.save_external_mods()

    def get_mod_comment(self, mod_id: str) -> str:
        """获取mod备注"""
        return self.mod_comments.get(mod_id, "")

    def set_native_comment(self, dll_path: str, comment: str):
        """设置DLL备注"""
        if comment.strip():
            self.native_comments[dll_path] = comment.strip()
        elif dll_path in self.native_comments:
            del self.native_comments[dll_path]
        self.save_external_mods()

    def get_native_comment(self, dll_path: str) -> str:
        """获取DLL备注"""
        return self.native_comments.get(dll_path, "")

    def set_force_load_last(self, mod_id: str) -> bool:
        """设置mod强制最后加载

        Args:
            mod_id: mod的ID

        Returns:
            bool: 设置是否成功
        """
        # 处理外部mod标识
        clean_id = mod_id.replace(" (外部)", "")

        # 找到目标mod
        target_package = None
        for pkg in self.packages:
            if pkg.id == clean_id:
                target_package = pkg
                break

        if not target_package:
            return False

        # 清除所有其他mod的强制最后加载设置，确保只有一个mod可以强制最后加载
        for other_pkg in self.packages:
            if other_pkg != target_package:
                # 清除所有其他mod的load_after设置
                other_pkg.load_after = None

        # 获取所有其他启用的mod ID列表（排除目标mod）
        other_enabled_mods = []
        for pkg in self.packages:
            if pkg.enabled and pkg.id != clean_id:
                other_enabled_mods.append(pkg.id)

        # 如果没有其他mod，无需设置依赖
        if not other_enabled_mods:
            target_package.load_after = None
            return True

        # 设置load_after依赖，让目标mod在所有其他mod之后加载
        target_package.load_after = [
            {"id": mod_id, "optional": True} for mod_id in other_enabled_mods
        ]

        return True

    def clear_force_load_last(self, mod_id: str) -> bool:
        """清除mod的强制最后加载设置

        Args:
            mod_id: mod的ID

        Returns:
            bool: 清除是否成功
        """
        # 处理外部mod标识
        clean_id = mod_id.replace(" (外部)", "")

        # 找到目标mod
        for pkg in self.packages:
            if pkg.id == clean_id:
                pkg.load_after = None
                return True

        return False

    def is_force_load_last(self, mod_id: str) -> bool:
        """检查mod是否设置为强制最后加载

        Args:
            mod_id: mod的ID

        Returns:
            bool: 是否设置为强制最后加载
        """
        # 处理外部mod标识
        clean_id = mod_id.replace(" (外部)", "")

        # 找到目标mod
        target_package = None
        for pkg in self.packages:
            if pkg.id == clean_id:
                target_package = pkg
                break

        if not target_package or not target_package.load_after:
            return False

        # 获取所有其他启用的mod ID列表（排除目标mod）
        other_enabled_mods = set()
        for pkg in self.packages:
            if pkg.enabled and pkg.id != clean_id:
                other_enabled_mods.add(pkg.id)

        # 检查load_after是否包含所有其他启用的mod
        load_after_ids = set()
        for dep in target_package.load_after:
            if isinstance(dep, dict) and 'id' in dep:
                load_after_ids.add(dep['id'])

        # 如果load_after包含大部分其他启用的mod，则认为是强制最后加载
        if len(other_enabled_mods) == 0:
            return False

        # 计算交集
        intersection_count = len(load_after_ids.intersection(other_enabled_mods))

        # 如果总mod数量较少（<=3），只要包含至少一个就认为是强制最后加载
        # 如果总mod数量较多，需要包含至少50%
        if len(other_enabled_mods) <= 3:
            return intersection_count >= 1
        else:
            return intersection_count >= len(other_enabled_mods) * 0.5

    def get_native_load_before(self, dll_name: str) -> Optional[List[Dict[str, Any]]]:
        """获取DLL的前置加载设置"""
        clean_name = dll_name.replace(" (外部)", "")

        for native in self.natives:
            # 匹配DLL名称或路径
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                return native.load_before

        return None

    def set_native_load_before(self, dll_name: str, target_dlls: List[str], optional: bool = True) -> bool:
        """设置DLL前置加载

        Args:
            dll_name: 要设置的DLL名称
            target_dlls: 需要在此DLL之前加载的DLL列表
            optional: 是否设置为可选依赖

        Returns:
            bool: 设置是否成功
        """
        clean_name = dll_name.replace(" (外部)", "")

        # 找到目标DLL
        target_native = None
        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                target_native = native
                break

        if not target_native:
            return False

        # 设置load_before依赖
        if target_dlls:
            target_native.load_before = [
                {"id": dll_name, "optional": optional} for dll_name in target_dlls
            ]
        else:
            target_native.load_before = None

        return True

    def clear_native_load_before(self, dll_name: str) -> bool:
        """清除DLL前置加载设置"""
        clean_name = dll_name.replace(" (外部)", "")

        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                native.load_before = None
                return True

        return False

    def is_force_load_first_native(self, dll_name: str) -> bool:
        """检查DLL是否设置为强制优先加载"""
        clean_name = dll_name.replace(" (外部)", "")

        for native in self.natives:
            # 匹配DLL名称或路径
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                # 检查是否有load_before设置，且包含所有其他启用的DLL
                if native.load_before:
                    # 获取所有其他启用的DLL
                    other_dlls = set()
                    for other_native in self.natives:
                        if (other_native.enabled and
                            other_native != native):
                            other_dll_name = Path(other_native.path).name
                            other_dlls.add(other_dll_name)

                    # 检查load_before是否包含所有其他DLL
                    load_before_ids = set()
                    for item in native.load_before:
                        load_before_ids.add(item.get('id', ''))

                    # 如果load_before包含所有其他启用的DLL，则认为是强制优先加载
                    return other_dlls.issubset(load_before_ids)

        return False

    def set_force_load_first_native(self, dll_name: str) -> bool:
        """设置DLL强制优先加载"""
        clean_name = dll_name.replace(" (外部)", "")

        # 找到目标DLL
        target_native = None
        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                target_native = native
                break

        if not target_native:
            return False

        # 清除所有其他DLL的强制优先加载设置，但保留特定顺序设置
        for other_native in self.natives:
            if other_native != target_native:
                # 检查是否有特定顺序设置需要保留
                if other_native.load_before and self._has_only_specific_order_deps(other_native):
                    # 保留特定顺序设置
                    continue
                else:
                    # 清除强制优先加载设置
                    other_native.load_before = None

        # 获取所有其他启用的DLL（排除已设置强制优先加载的）
        other_dlls = []
        for other_native in self.natives:
            if (other_native.enabled and
                other_native != target_native):
                other_dll_name = Path(other_native.path).name
                other_dlls.append(other_dll_name)

        # 设置load_before为所有其他启用的DLL（必需依赖）
        if other_dlls:
            target_native.load_before = [
                {"id": dll, "optional": False} for dll in other_dlls
            ]
        else:
            target_native.load_before = None

        # 确保特定的DLL顺序
        self.ensure_specific_dll_orders()

        # 优化强制优先加载的依赖
        target_dll_name = Path(target_native.path).name
        self._optimize_force_load_dependencies(target_dll_name)

        return True

    def _is_force_load_first_config(self, native) -> bool:
        """检查native是否是强制优先加载配置"""
        if not native.load_before:
            return False

        # 获取所有其他启用的DLL
        other_enabled_dlls = set()
        for other_native in self.natives:
            if (other_native.enabled and other_native != native):
                other_dll_name = Path(other_native.path).name
                other_enabled_dlls.add(other_dll_name)

        # 检查load_before是否包含所有其他启用的DLL
        load_before_ids = set()
        for item in native.load_before:
            load_before_ids.add(item.get('id', ''))

        # 如果load_before包含大部分其他启用的DLL，认为是强制优先加载
        if len(other_enabled_dlls) == 0:
            return False

        return len(load_before_ids.intersection(other_enabled_dlls)) >= max(1, len(other_enabled_dlls) * 0.6)

    def clear_force_load_first_native(self, dll_name: str) -> bool:
        """清除DLL强制优先加载"""
        clean_name = dll_name.replace(" (外部)", "")

        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                native.load_before = None
                return True

        return False

    def _has_only_specific_order_deps(self, native) -> bool:
        """检查native是否只有特定顺序依赖"""
        if not native.load_before:
            return False

        dll_name = Path(native.path).name

        # 检查所有依赖是否都是特定顺序要求
        specific_orders = [
            ("nighter.dll", "nrsc.dll"),  # nighter.dll必须在nrsc.dll之前
        ]

        for dep in native.load_before:
            dep_id = dep.get('id', '')
            is_specific_order = False

            for first, second in specific_orders:
                if dll_name == first and dep_id == second:
                    is_specific_order = True
                    break

            if not is_specific_order:
                return False

        return True

    def set_specific_dll_order(self, first_dll: str, second_dll: str) -> bool:
        """设置特定DLL的加载顺序（first_dll在second_dll之前加载）"""
        first_clean = first_dll.replace(" (外部)", "")
        second_clean = second_dll.replace(" (外部)", "")

        # 找到两个DLL
        first_native = None
        second_native = None

        for native in self.natives:
            dll_name = Path(native.path).name
            if (dll_name == first_clean or
                native.path == first_clean or
                native.path.endswith(first_clean)):
                first_native = native
            elif (dll_name == second_clean or
                  native.path == second_clean or
                  native.path.endswith(second_clean)):
                second_native = native

        if not first_native or not second_native:
            return False

        # 确保两个DLL都启用
        if not first_native.enabled or not second_native.enabled:
            return False

        # 检查是否会创建循环依赖
        second_dll_name = Path(second_native.path).name
        first_dll_name = Path(first_native.path).name

        if self._would_create_circular_dependency(first_dll_name, second_dll_name):
            # 如果会创建循环依赖，先清除反向依赖
            self._remove_reverse_dependency(second_dll_name, first_dll_name)

        # 设置first_dll的load_before包含second_dll
        if not first_native.load_before:
            first_native.load_before = []

        # 检查是否已经存在这个依赖
        already_exists = any(dep.get('id') == second_dll_name for dep in first_native.load_before)

        if not already_exists:
            first_native.load_before.append({"id": second_dll_name, "optional": False})

        return True

    def _would_create_circular_dependency(self, first_dll: str, second_dll: str) -> bool:
        """检查设置first_dll -> second_dll是否会创建循环依赖"""
        # 检查second_dll是否已经依赖first_dll
        for native in self.natives:
            if (native.enabled and
                Path(native.path).name == second_dll and
                native.load_before):
                for dep in native.load_before:
                    if dep.get('id') == first_dll:
                        return True
        return False

    def _remove_reverse_dependency(self, from_dll: str, to_dll: str):
        """移除from_dll对to_dll的依赖"""
        for native in self.natives:
            if (native.enabled and
                Path(native.path).name == from_dll and
                native.load_before):
                # 移除对to_dll的依赖
                native.load_before = [
                    dep for dep in native.load_before
                    if dep.get('id') != to_dll
                ]
                # 如果load_before为空，设置为None
                if not native.load_before:
                    native.load_before = None

    def remove_specific_dll_order(self, first_dll: str, second_dll: str) -> bool:
        """移除特定DLL的加载顺序"""
        first_clean = first_dll.replace(" (外部)", "")
        second_clean = second_dll.replace(" (外部)", "")

        # 找到第一个DLL
        first_native = None
        for native in self.natives:
            dll_name = Path(native.path).name
            if (dll_name == first_clean or
                native.path == first_clean or
                native.path.endswith(first_clean)):
                first_native = native
                break

        if not first_native or not first_native.load_before:
            return False

        # 移除对second_dll的依赖
        second_dll_name = Path(second_clean).name if '/' in second_clean else second_clean
        first_native.load_before = [
            dep for dep in first_native.load_before
            if dep.get('id') != second_dll_name
        ]

        # 如果load_before为空，设置为None
        if not first_native.load_before:
            first_native.load_before = None

        return True

    def ensure_specific_dll_orders(self):
        """确保特定的DLL加载顺序"""
        # 定义特定的DLL顺序要求
        specific_orders = [
            ("nighter.dll", "nrsc.dll"),  # nighter.dll必须在nrsc.dll之前
        ]

        for first_dll, second_dll in specific_orders:
            # 检查两个DLL是否都启用
            first_enabled = False
            second_enabled = False

            for native in self.natives:
                dll_name = Path(native.path).name
                if dll_name == first_dll and native.enabled:
                    first_enabled = True
                elif dll_name == second_dll and native.enabled:
                    second_enabled = True

            # 如果两个DLL都启用，确保顺序正确
            if first_enabled and second_enabled:
                self.set_specific_dll_order(first_dll, second_dll)

    def update_load_dependencies(self):
        """更新所有load_before和load_after依赖，移除未启用的mod"""
        # 获取所有启用的mod ID
        enabled_package_ids = set()
        for pkg in self.packages:
            if pkg.enabled:
                enabled_package_ids.add(pkg.id)

        # 获取所有启用的native DLL名称
        enabled_native_ids = set()
        for native in self.natives:
            if native.enabled:
                dll_name = Path(native.path).name
                enabled_native_ids.add(dll_name)

        # 更新packages的load_after依赖
        for pkg in self.packages:
            if pkg.load_after:
                # 过滤掉未启用的依赖
                updated_load_after = []
                for dep in pkg.load_after:
                    dep_id = dep.get('id', '')
                    if dep_id in enabled_package_ids:
                        updated_load_after.append(dep)

                pkg.load_after = updated_load_after if updated_load_after else None

        # 更新natives的load_before依赖
        for native in self.natives:
            if native.load_before:
                # 过滤掉未启用的依赖
                updated_load_before = []
                for dep in native.load_before:
                    dep_id = dep.get('id', '')
                    if dep_id in enabled_native_ids:
                        updated_load_before.append(dep)

                native.load_before = updated_load_before if updated_load_before else None

            if native.load_after:
                # 过滤掉未启用的依赖
                updated_load_after = []
                for dep in native.load_after:
                    dep_id = dep.get('id', '')
                    if dep_id in enabled_native_ids:
                        updated_load_after.append(dep)

                native.load_after = updated_load_after if updated_load_after else None

        # 确保特定的DLL顺序
        self.ensure_specific_dll_orders()

    def add_to_load_dependencies(self, newly_enabled_id: str, is_native: bool = False):
        """当mod被启用时，将其添加到相关的load依赖中"""
        if is_native:
            # 处理native DLL
            # 找到设置了强制优先加载的DLL，重新构建其完整的依赖列表
            for native in self.natives:
                if (native.enabled and
                    native.load_before and
                    self._is_force_load_first_config(native)):
                    # 重新构建完整的依赖列表
                    target_dll_name = Path(native.path).name
                    self._rebuild_force_load_first_dependencies(target_dll_name)
                    break

            # 确保特定的DLL顺序（无论是否有强制优先加载）
            self.ensure_specific_dll_orders()
        else:
            # 处理package mod
            # 找到设置了强制最后加载的mod，重新构建其完整的依赖列表
            for pkg in self.packages:
                if (pkg.enabled and
                    pkg.load_after and
                    self.is_force_load_last(pkg.id)):
                    # 重新构建完整的依赖列表
                    self._rebuild_force_load_last_dependencies(pkg.id)
                    break

    def _rebuild_force_load_first_dependencies(self, dll_name: str):
        """重新构建DLL强制优先加载的完整依赖列表，智能处理特定DLL顺序"""
        clean_name = dll_name.replace(" (外部)", "")

        # 找到目标DLL
        target_native = None
        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                target_native = native
                break

        if not target_native:
            return

        # 获取所有其他启用的DLL，但智能处理特定顺序
        other_dlls = []
        target_dll_name = Path(target_native.path).name

        for other_native in self.natives:
            if (other_native.enabled and
                other_native != target_native):
                other_dll_name = Path(other_native.path).name

                # 检查是否存在特定顺序关系
                if self._has_specific_order_dependency(other_dll_name, target_dll_name):
                    # 如果other_dll应该在target_dll之前，则target_dll不应该依赖other_dll
                    continue

                # 检查是否可以通过链式依赖间接满足顺序要求
                if self._can_reach_through_chain(target_dll_name, other_dll_name):
                    # 如果可以通过链式依赖到达，则不需要直接依赖
                    continue

                other_dlls.append(other_dll_name)

        # 重新设置优化后的load_before依赖
        if other_dlls:
            target_native.load_before = [
                {"id": dll, "optional": False} for dll in other_dlls
            ]
        else:
            target_native.load_before = None

        # 确保特定的DLL顺序
        self.ensure_specific_dll_orders()

        # 在确保特定顺序后，重新优化强制优先加载的依赖
        self._optimize_force_load_dependencies(target_dll_name)

    def _has_specific_order_dependency(self, first_dll: str, second_dll: str) -> bool:
        """检查两个DLL之间是否存在特定的顺序依赖关系"""
        # 定义特定的DLL顺序要求
        specific_orders = [
            ("nighter.dll", "nrsc.dll"),  # nighter.dll必须在nrsc.dll之前
        ]

        for first, second in specific_orders:
            if first == first_dll and second == second_dll:
                return True

        return False

    def _can_reach_through_chain(self, from_dll: str, to_dll: str) -> bool:
        """检查是否可以通过链式依赖从from_dll到达to_dll"""
        # 定义特定的DLL顺序要求
        specific_orders = [
            ("nighter.dll", "nrsc.dll"),  # nighter.dll必须在nrsc.dll之前
        ]

        # 检查是否存在链式路径：from_dll -> intermediate_dll -> to_dll
        for first, second in specific_orders:
            if to_dll == second:
                # 目标是second，检查是否可以通过first到达
                # 如果from_dll会依赖first，且first会依赖second，则可以通过链式到达

                # 检查first是否存在且启用
                first_exists = any(
                    native.enabled and Path(native.path).name == first
                    for native in self.natives
                )

                if first_exists and from_dll != first and from_dll != second:
                    # from_dll -> first -> second 的链式关系
                    return True

        return False

    def _optimize_force_load_dependencies(self, dll_name: str):
        """优化强制优先加载的依赖，移除可以通过链式依赖到达的DLL"""
        clean_name = dll_name.replace(" (外部)", "")

        # 找到目标DLL
        target_native = None
        for native in self.natives:
            if (Path(native.path).name == clean_name or
                native.path == clean_name or
                native.path.endswith(clean_name)):
                target_native = native
                break

        if not target_native or not target_native.load_before:
            return

        # 检查每个依赖是否可以通过链式依赖到达
        optimized_deps = []

        for dep in target_native.load_before:
            dep_id = dep.get('id', '')

            # 检查是否可以通过其他依赖链式到达这个DLL
            can_reach_through_chain = False

            for other_dep in target_native.load_before:
                other_dep_id = other_dep.get('id', '')
                if other_dep_id != dep_id:
                    # 检查other_dep是否会依赖dep_id
                    if self._dll_depends_on(other_dep_id, dep_id):
                        can_reach_through_chain = True
                        break

            # 如果不能通过链式到达，则保留这个直接依赖
            if not can_reach_through_chain:
                optimized_deps.append(dep)

        # 更新优化后的依赖
        target_native.load_before = optimized_deps if optimized_deps else None

    def _dll_depends_on(self, dll_name: str, target_dll: str) -> bool:
        """检查dll_name是否依赖target_dll"""
        for native in self.natives:
            if (native.enabled and
                Path(native.path).name == dll_name and
                native.load_before):
                # 检查load_before中是否包含target_dll
                for dep in native.load_before:
                    if dep.get('id') == target_dll:
                        return True
        return False

    def _rebuild_force_load_last_dependencies(self, mod_id: str):
        """重新构建mod强制最后加载的完整依赖列表"""
        clean_id = mod_id.replace(" (外部)", "")

        # 找到目标mod
        target_package = None
        for pkg in self.packages:
            if pkg.id == clean_id:
                target_package = pkg
                break

        if not target_package:
            return

        # 获取所有其他启用的mod ID列表（排除目标mod）
        other_enabled_mods = []
        for pkg in self.packages:
            if pkg.enabled and pkg.id != clean_id:
                other_enabled_mods.append(pkg.id)

        # 重新设置完整的load_after依赖
        if other_enabled_mods:
            target_package.load_after = [
                {"id": other_mod_id, "optional": True} for other_mod_id in other_enabled_mods
            ]
        else:
            target_package.load_after = None

    def _write_custom_toml(self, config_data: Dict[str, Any], file_handle):
        """自定义TOML写入方法，确保正确的格式"""
        # 写入profileVersion
        file_handle.write(f'profileVersion = "{config_data.get("profileVersion", "v1")}"\n\n')

        # 写入supports部分
        file_handle.write('[[supports]]\n')
        file_handle.write('game = "nightreign"\n\n')

        # 写入packages
        if 'packages' in config_data:
            for package in config_data['packages']:
                file_handle.write('[[packages]]\n')
                file_handle.write(f'id = "{package["id"]}"\n')
                # 正确转义Windows路径中的反斜杠
                source_path = package["source"].replace("\\", "\\\\")
                file_handle.write(f'source = "{source_path}"\n')

                # 处理load_after字段
                if 'load_after' in package and package['load_after']:
                    load_after_str = self._format_load_after(package['load_after'])
                    file_handle.write(f'load_after = {load_after_str}\n')

                # 处理load_before字段
                if 'load_before' in package and package['load_before']:
                    load_before_str = self._format_load_after(package['load_before'])
                    file_handle.write(f'load_before = {load_before_str}\n')

                file_handle.write('\n')

        # 写入natives
        if 'natives' in config_data:
            for native in config_data['natives']:
                file_handle.write('[[natives]]\n')
                # 正确转义Windows路径中的反斜杠
                native_path = native["path"].replace("\\", "\\\\")
                file_handle.write(f'path = "{native_path}"\n')

                if 'optional' in native and native['optional']:
                    file_handle.write(f'optional = {str(native["optional"]).lower()}\n')

                if 'initializer' in native and native['initializer']:
                    file_handle.write(f'initializer = "{native["initializer"]}"\n')

                if 'finalizer' in native and native['finalizer']:
                    file_handle.write(f'finalizer = "{native["finalizer"]}"\n')

                # 处理load_after字段
                if 'load_after' in native and native['load_after']:
                    load_after_str = self._format_load_after(native['load_after'])
                    file_handle.write(f'load_after = {load_after_str}\n')

                # 处理load_before字段
                if 'load_before' in native and native['load_before']:
                    load_before_str = self._format_load_after(native['load_before'])
                    file_handle.write(f'load_before = {load_before_str}\n')

                file_handle.write('\n')

    def _format_load_after(self, dependencies: List[Dict[str, Any]]) -> str:
        """格式化load_after/load_before依赖列表为正确的TOML格式"""
        if not dependencies:
            return "[]"

        formatted_deps = []
        for dep in dependencies:
            dep_str = "{"
            dep_parts = []

            if 'id' in dep:
                dep_parts.append(f"id = \"{dep['id']}\"")

            if 'optional' in dep:
                dep_parts.append(f"optional = {str(dep['optional']).lower()}")

            dep_str += ", ".join(dep_parts) + "}"
            formatted_deps.append(dep_str)

        return "[" + ", ".join(formatted_deps) + "]"

    def check_external_mods_existence(self) -> Dict[str, Dict[str, bool]]:
        """检查外部mod的存在性

        Returns:
            Dict[str, Dict[str, bool]]: {
                'packages': {mod_name: exists},
                'natives': {dll_name: exists}
            }
        """
        result = {
            'packages': {},
            'natives': {}
        }

        # 检查外部mod包
        for mod_name, mod_path in self.external_packages.items():
            try:
                result['packages'][mod_name] = Path(mod_path).exists()
            except (OSError, ValueError):
                result['packages'][mod_name] = False

        # 检查外部DLL
        for dll_name, dll_path in self.external_natives.items():
            try:
                result['natives'][dll_name] = Path(dll_path).exists()
            except (OSError, ValueError):
                result['natives'][dll_name] = False

        return result

    def get_missing_external_mods(self) -> Dict[str, List[str]]:
        """获取缺失的外部mod列表

        Returns:
            Dict[str, List[str]]: {
                'packages': [missing_mod_names],
                'natives': [missing_dll_names]
            }
        """
        existence = self.check_external_mods_existence()

        missing_packages = [name for name, exists in existence['packages'].items() if not exists]
        missing_natives = [name for name, exists in existence['natives'].items() if not exists]

        return {
            'packages': missing_packages,
            'natives': missing_natives
        }

    def cleanup_missing_external_mods(self) -> Dict[str, List[str]]:
        """清理缺失的外部mod

        Returns:
            Dict[str, List[str]]: 被清理的mod列表
        """
        missing = self.get_missing_external_mods()
        cleaned = {
            'packages': [],
            'natives': []
        }

        # 清理缺失的外部mod包
        for mod_name in missing['packages']:
            if self.remove_external_package(mod_name):
                cleaned['packages'].append(mod_name)

        # 清理缺失的外部DLL
        for dll_name in missing['natives']:
            if self.remove_external_native(dll_name):
                cleaned['natives'].append(dll_name)

        return cleaned

    def cleanup_internal_mods_from_external_list(self) -> Dict[str, List[str]]:
        """清理外部mod列表中错误的内部mod条目

        Returns:
            Dict[str, List[str]]: 被清理的mod列表
        """
        cleaned = {
            'packages': [],
            'natives': []
        }

        # 检查外部mod包中的内部路径
        packages_to_remove = []
        for mod_name, mod_path in self.external_packages.items():
            try:
                mod_path_resolved = Path(mod_path).resolve()
                mods_dir_resolved = self.mods_dir.resolve()

                # 如果外部mod路径实际上在内部Mods目录内，标记为需要移除
                if mod_path_resolved == mods_dir_resolved or mods_dir_resolved in mod_path_resolved.parents:
                    packages_to_remove.append(mod_name)
            except (OSError, ValueError):
                # 路径解析失败，也标记为需要移除
                packages_to_remove.append(mod_name)

        # 移除错误的外部mod包
        for mod_name in packages_to_remove:
            if self.remove_external_package(mod_name):
                cleaned['packages'].append(mod_name)

        # 检查外部DLL中的内部路径
        natives_to_remove = []
        for dll_name, dll_path in self.external_natives.items():
            try:
                dll_path_resolved = Path(dll_path).resolve()
                mods_dir_resolved = self.mods_dir.resolve()

                # 如果外部DLL路径实际上在内部Mods目录内，标记为需要移除
                if mods_dir_resolved in dll_path_resolved.parents:
                    natives_to_remove.append(dll_name)
            except (OSError, ValueError):
                # 路径解析失败，也标记为需要移除
                natives_to_remove.append(dll_name)

        # 移除错误的外部DLL
        for dll_name in natives_to_remove:
            if self.remove_external_native(dll_name):
                cleaned['natives'].append(dll_name)

        return cleaned


