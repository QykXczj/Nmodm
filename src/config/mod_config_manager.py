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
        
        # 备注存储
        self.package_comments: Dict[str, str] = {}  # {mod_id: comment}
        self.native_comments: Dict[str, str] = {}   # {dll_path: comment}

        # 加载外部mod配置
        self.load_external_config()

    def load_external_config(self):
        """加载外部mod配置"""
        try:
            if self.external_config_file.exists():
                import json
                with open(self.external_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.external_packages = data.get('packages', {})
                    self.external_natives = data.get('natives', {})
                    self.package_comments = data.get('package_comments', {})
                    self.native_comments = data.get('native_comments', {})
        except Exception as e:
            print(f"加载外部mod配置失败: {e}")
            self.external_packages = {}
            self.external_natives = {}
            self.package_comments = {}
            self.native_comments = {}

    def save_external_config(self):
        """保存外部mod配置"""
        try:
            import json
            data = {
                'packages': self.external_packages,
                'natives': self.external_natives,
                'package_comments': self.package_comments,
                'native_comments': self.native_comments
            }
            with open(self.external_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存外部mod配置失败: {e}")
            return False

    def detect_mod_type(self, mod_path: Path) -> str:
        """检测mod类型
        
        Args:
            mod_path: mod路径
            
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
            typical_folders = ["msg", "param", "chr", "script", "sfx", "map", "parts"]
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

            # 检查是否包含DLL文件
            dll_files = list(mod_path.glob("*.dll"))
            if dll_files:
                has_dll = True

            # 根据检测结果分类
            if has_regulation or has_typical_folders or has_mod_files:
                if has_dll:
                    return "mixed"  # 混合型：既有mod文件又有DLL
                else:
                    return "folder"  # 文件夹型mod
            elif has_dll:
                return "dll"  # DLL型mod
            else:
                return "unknown"  # 未知类型

        except Exception as e:
            print(f"检测mod类型失败: {e}")
            return "unknown"

    def scan_mods(self) -> bool:
        """扫描Mods目录"""
        try:
            self.packages.clear()
            self.natives.clear()
            
            if not self.mods_dir.exists():
                return True
            
            # 扫描内部mods
            for item in self.mods_dir.iterdir():
                if item.is_dir() and item.name not in ['__pycache__', '.git']:
                    self._scan_mod_directory(item, is_external=False)
            
            # 添加外部mods
            self._add_external_mods()
            
            return True
        except Exception as e:
            print(f"扫描mods失败: {e}")
            return False

    def _scan_mod_directory(self, mod_path: Path, is_external: bool = False):
        """扫描单个mod目录"""
        try:
            mod_type = self.detect_mod_type(mod_path)
            
            if mod_type == "folder":
                # 文件夹型mod
                package = ModPackage(
                    id=mod_path.name,
                    source=f"{mod_path.name}/" if not is_external else str(mod_path),
                    is_external=is_external,
                    comment=self.package_comments.get(mod_path.name, "")
                )
                self.packages.append(package)
                
            elif mod_type == "dll":
                # DLL型mod - 每个DLL文件作为独立的native
                for dll_file in mod_path.glob("*.dll"):
                    relative_path = f"{mod_path.name}/{dll_file.name}" if not is_external else str(dll_file)
                    native = ModNative(
                        path=relative_path,
                        is_external=is_external,
                        comment=self.native_comments.get(relative_path, "")
                    )
                    self.natives.append(native)
                    
            elif mod_type == "mixed":
                # 混合型mod - 既添加为package又添加DLL
                # 添加为package
                package = ModPackage(
                    id=mod_path.name,
                    source=f"{mod_path.name}/" if not is_external else str(mod_path),
                    is_external=is_external,
                    comment=self.package_comments.get(mod_path.name, "")
                )
                self.packages.append(package)
                
                # 添加DLL文件
                for dll_file in mod_path.glob("*.dll"):
                    relative_path = f"{mod_path.name}/{dll_file.name}" if not is_external else str(dll_file)
                    native = ModNative(
                        path=relative_path,
                        is_external=is_external,
                        comment=self.native_comments.get(relative_path, "")
                    )
                    self.natives.append(native)
                    
        except Exception as e:
            print(f"扫描mod目录失败 {mod_path}: {e}")

    def _add_external_mods(self):
        """添加外部mods到配置"""
        # 添加外部packages
        for mod_name, mod_path in self.external_packages.items():
            path_obj = Path(mod_path)
            if path_obj.exists():
                if path_obj.is_dir():
                    # 外部文件夹mod
                    package = ModPackage(
                        id=mod_name,
                        source=str(path_obj),
                        is_external=True,
                        comment=self.package_comments.get(mod_name, "")
                    )
                    self.packages.append(package)
                else:
                    # 外部文件mod（如regulation.bin）
                    package = ModPackage(
                        id=mod_name,
                        source=str(path_obj),
                        is_external=True,
                        comment=self.package_comments.get(mod_name, "")
                    )
                    self.packages.append(package)
            else:
                # 文件不存在，从外部配置中移除
                print(f"外部mod不存在，已自动移除: {mod_path}")
                del self.external_packages[mod_name]
                if mod_name in self.package_comments:
                    del self.package_comments[mod_name]

        # 添加外部natives
        for dll_name, dll_path in self.external_natives.items():
            path_obj = Path(dll_path)
            if path_obj.exists():
                native = ModNative(
                    path=str(path_obj),
                    is_external=True,
                    comment=self.native_comments.get(dll_path, "")
                )
                self.natives.append(native)
            else:
                # 文件不存在，从外部配置中移除
                print(f"外部DLL不存在，已自动移除: {dll_path}")
                del self.external_natives[dll_name]
                if dll_path in self.native_comments:
                    del self.native_comments[dll_path]

        # 保存清理后的外部配置
        self.save_external_config()

    def save_config(self, config_path: Optional[str] = None) -> bool:
        """保存配置到ME3文件"""
        try:
            config_file = Path(config_path) if config_path else self.config_file
            
            # 构建配置数据
            config_data = {
                'profileVersion': self.profile_version
            }
            
            # 添加packages
            if self.packages:
                config_data['packages'] = []
                for package in self.packages:
                    if package.enabled:
                        pkg_dict = {
                            'id': package.id,
                            'source': package.source
                        }
                        # 添加依赖关系
                        if package.load_after:
                            pkg_dict['load_after'] = package.load_after
                        if package.load_before:
                            pkg_dict['load_before'] = package.load_before
                        config_data['packages'].append(pkg_dict)
            
            # 添加natives
            if self.natives:
                config_data['natives'] = []
                for native in self.natives:
                    if native.enabled:
                        native_dict = {
                            'path': native.path
                        }
                        if native.optional:
                            native_dict['optional'] = native.optional
                        if native.initializer:
                            native_dict['initializer'] = native.initializer
                        if native.finalizer:
                            native_dict['finalizer'] = native.finalizer
                        # 添加依赖关系
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

    def load_config(self, config_path: Optional[str] = None) -> bool:
        """从ME3文件加载配置"""
        try:
            config_file = Path(config_path) if config_path else self.config_file
            
            if not config_file.exists():
                return True
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = toml.load(f)
            
            # 清空当前配置
            self.packages.clear()
            self.natives.clear()
            
            # 加载packages
            if 'packages' in config_data:
                for pkg_data in config_data['packages']:
                    package = ModPackage(
                        id=pkg_data['id'],
                        source=pkg_data['source'],
                        load_after=pkg_data.get('load_after'),
                        load_before=pkg_data.get('load_before'),
                        enabled=True
                    )
                    self.packages.append(package)
            
            # 加载natives
            if 'natives' in config_data:
                for native_data in config_data['natives']:
                    native = ModNative(
                        path=native_data['path'],
                        optional=native_data.get('optional', False),
                        initializer=native_data.get('initializer'),
                        finalizer=native_data.get('finalizer'),
                        load_after=native_data.get('load_after'),
                        load_before=native_data.get('load_before'),
                        enabled=True
                    )
                    self.natives.append(native)
            
            return True
        except Exception as e:
            print(f"加载配置失败: {e}")
            return False

    def add_external_package(self, mod_name: str, mod_path: str) -> bool:
        """添加外部mod包"""
        try:
            # 检查路径是否存在
            path_obj = Path(mod_path)
            if not path_obj.exists():
                print(f"路径不存在: {mod_path}")
                return False
            
            # 检查是否与内部mod路径冲突
            if self._is_internal_path(mod_path):
                print(f"路径与内部Mods目录冲突: {mod_path}")
                return False
            
            # 检查是否已存在相同路径
            if mod_path in self.external_packages.values():
                print(f"路径已存在: {mod_path}")
                return False
            
            # 添加到外部配置
            self.external_packages[mod_name] = mod_path
            self.save_external_config()
            return True
        except Exception as e:
            print(f"添加外部mod包失败: {e}")
            return False

    def add_external_native(self, dll_name: str, dll_path: str) -> bool:
        """添加外部DLL"""
        try:
            # 检查路径是否存在
            path_obj = Path(dll_path)
            if not path_obj.exists():
                print(f"DLL文件不存在: {dll_path}")
                return False
            
            # 检查是否与内部mod路径冲突
            if self._is_internal_path(dll_path):
                print(f"路径与内部Mods目录冲突: {dll_path}")
                return False
            
            # 检查DLL重名冲突
            if self._has_dll_name_conflict(dll_name):
                print(f"DLL名称冲突: {dll_name}")
                return False
            
            # 添加到外部配置
            self.external_natives[dll_name] = dll_path
            self.save_external_config()
            return True
        except Exception as e:
            print(f"添加外部DLL失败: {e}")
            return False

    def _is_internal_path(self, path: str) -> bool:
        """检查路径是否在内部Mods目录内"""
        try:
            path_obj = Path(path).resolve()
            mods_dir_resolved = self.mods_dir.resolve()
            return str(path_obj).startswith(str(mods_dir_resolved))
        except Exception:
            return False

    def _has_dll_name_conflict(self, dll_name: str) -> bool:
        """检查DLL名称是否冲突"""
        # 检查与现有外部DLL的冲突
        for existing_name in self.external_natives.keys():
            if existing_name == dll_name:
                return True
        
        # 检查与内部DLL的冲突
        for native in self.natives:
            if not native.is_external:
                existing_dll_name = Path(native.path).name
                if existing_dll_name == dll_name:
                    return True
        
        return False

    def remove_external_package(self, mod_name: str) -> bool:
        """移除外部mod包"""
        try:
            if mod_name in self.external_packages:
                del self.external_packages[mod_name]
                # 同时移除备注
                if mod_name in self.package_comments:
                    del self.package_comments[mod_name]
                self.save_external_config()
                return True
            return False
        except Exception as e:
            print(f"移除外部mod包失败: {e}")
            return False

    def remove_external_native(self, dll_name: str) -> bool:
        """移除外部DLL"""
        try:
            if dll_name in self.external_natives:
                dll_path = self.external_natives[dll_name]
                del self.external_natives[dll_name]
                # 同时移除备注
                if dll_path in self.native_comments:
                    del self.native_comments[dll_path]
                self.save_external_config()
                return True
            return False
        except Exception as e:
            print(f"移除外部DLL失败: {e}")
            return False

    def remove_package(self, package_id: str):
        """从当前配置中移除包"""
        self.packages = [pkg for pkg in self.packages if pkg.id != package_id]

    def remove_native(self, native_path: str):
        """从当前配置中移除native"""
        self.natives = [native for native in self.natives if native.path != native_path]

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
    
    def get_me3_executable_path(self) -> Optional[str]:
        """获取ME3可执行文件路径"""
        me3_path = self.root_dir / "me3p" / "bin" / "me3.exe"
        return str(me3_path) if me3_path.exists() else None

    def set_package_comment(self, package_id: str, comment: str):
        """设置包备注"""
        self.package_comments[package_id] = comment
        # 同时更新当前配置中的备注
        for package in self.packages:
            if package.id == package_id:
                package.comment = comment
                break
        self.save_external_config()

    def get_package_comment(self, package_id: str) -> str:
        """获取包备注"""
        return self.package_comments.get(package_id, "")

    def set_native_comment(self, dll_path: str, comment: str):
        """设置DLL备注"""
        self.native_comments[dll_path] = comment
        # 同时更新当前配置中的备注
        for native in self.natives:
            if native.path == dll_path:
                native.comment = comment
                break
        self.save_external_config()

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
        
        # 如果load_after包含所有其他启用的mod，则认为是强制最后加载
        return other_enabled_mods.issubset(load_after_ids)
    
    def _write_custom_toml(self, config_data: Dict[str, Any], file_handle):
        """自定义TOML写入方法，确保正确的格式"""
        # 写入profileVersion
        file_handle.write(f'profileVersion = "{config_data.get("profileVersion", "v1")}"\n\n')
        
        # 写入packages
        if 'packages' in config_data:
            for package in config_data['packages']:
                file_handle.write('[[packages]]\n')
                file_handle.write(f'id = "{package["id"]}"\n')
                file_handle.write(f'source = "{package["source"]}"\n')
                
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
                file_handle.write(f'path = "{native["path"]}"\n')
                
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