"""
下载管理器
负责ME3工具的下载和版本管理
"""
import os
import json
import zipfile
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from PySide6.QtCore import QObject, Signal, QThread


class DownloadWorker(QThread):
    """下载工作线程"""
    progress = Signal(int)  # 下载进度
    finished = Signal(bool, str)  # 完成信号(成功, 消息)

    def __init__(self, url: str, save_path: str):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._is_cancelled = False

    def cancel(self):
        """取消下载"""
        self._is_cancelled = True
        self.quit()
        self.wait()

    def run(self):
        try:
            if self._is_cancelled:
                return

            # 确保父目录存在
            from pathlib import Path
            save_path = Path(self.save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        # 删除部分下载的文件
                        try:
                            os.remove(self.save_path)
                        except:
                            pass
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)

            if not self._is_cancelled:
                self.finished.emit(True, "下载完成")
        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(False, f"下载失败: {str(e)}")


class DownloadManager(QObject):
    """下载管理器"""

    # 信号定义
    easytier_install_finished = Signal(bool, str)  # EasyTier安装完成信号(成功, 消息)
    me3_installer_download_finished = Signal(bool, str, str)  # ME3安装程序下载完成信号(成功, 消息, 文件路径)
    onlinefix_download_finished = Signal(bool, str)  # OnlineFix下载完成信号(成功, 消息)
    onlinefix_download_progress = Signal(int)  # OnlineFix下载进度信号(进度百分比)

    # GitHub加速镜像地址
    DEFAULT_PROXY_URLS = [
        "https://gh-proxy.com/",
        "https://ghproxy.net/",
        "https://ghfast.top/"
    ]

    def __init__(self):
        super().__init__()
        self.root_dir = Path(__file__).parent.parent.parent
        self.me3_dir = self.root_dir / "me3p"
        # self.erm_dir = self.root_dir / "ERM"  # ERModsMerger已移除
        self.esr_dir = self.root_dir / "ESR"  # EasyTier目录
        self.onlinefix_dir = self.root_dir / "OnlineFix"  # OnlineFix目录
        self.version_file = self.me3_dir / "version.json"
        # self.erm_version_file = self.erm_dir / "version.json"  # ERModsMerger已移除
        self.esr_version_file = self.esr_dir / "version.json"  # EasyTier版本文件
        self.config_file = self.me3_dir / "mirrors.json"

        # 确保目录存在
        self.me3_dir.mkdir(exist_ok=True)
        # self.erm_dir.mkdir(exist_ok=True)  # ERModsMerger已移除
        self.esr_dir.mkdir(exist_ok=True)  # 确保ESR目录存在
        self.onlinefix_dir.mkdir(exist_ok=True)  # 确保OnlineFix目录存在

        # 加载镜像配置
        self.PROXY_URLS = self.load_mirrors()

        # EasyTier版本信息缓存
        self._easytier_cache = {
            'release': {'data': None, 'timestamp': None},
            'prerelease': {'data': None, 'timestamp': None}
        }
        self._cache_duration = timedelta(minutes=5)  # 缓存5分钟

    def _is_cache_valid(self, cache_type: str) -> bool:
        """检查缓存是否有效"""
        cache = self._easytier_cache.get(cache_type)
        if not cache or not cache['timestamp'] or not cache['data']:
            return False
        return datetime.now() - cache['timestamp'] < self._cache_duration

    def _get_cached_data(self, cache_type: str):
        """获取缓存数据"""
        if self._is_cache_valid(cache_type):
            return self._easytier_cache[cache_type]['data']
        return None

    def _set_cache_data(self, cache_type: str, data):
        """设置缓存数据"""
        self._easytier_cache[cache_type] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def load_mirrors(self) -> list:
        """加载镜像配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('mirrors', self.DEFAULT_PROXY_URLS)
            return self.DEFAULT_PROXY_URLS.copy()
        except Exception as e:
            print(f"加载镜像配置失败: {e}")
            return self.DEFAULT_PROXY_URLS.copy()

    def save_mirrors(self, mirrors: list):
        """保存镜像配置"""
        try:
            data = {'mirrors': mirrors}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.PROXY_URLS = mirrors.copy()
        except Exception as e:
            print(f"保存镜像配置失败: {e}")

    def add_mirror(self, mirror_url: str):
        """添加镜像地址"""
        if mirror_url and mirror_url not in self.PROXY_URLS:
            self.PROXY_URLS.append(mirror_url)
            self.save_mirrors(self.PROXY_URLS)

    def remove_mirror(self, mirror_url: str):
        """移除镜像地址"""
        if mirror_url in self.PROXY_URLS:
            self.PROXY_URLS.remove(mirror_url)
            self.save_mirrors(self.PROXY_URLS)

    def get_mirrors(self) -> list:
        """获取当前镜像列表"""
        return self.PROXY_URLS.copy()
    
    def get_latest_release_info(self) -> Optional[Dict]:
        """获取最新版本信息"""
        api_url = "https://api.github.com/repos/garyttierney/me3/releases/latest"
        
        for proxy in [""] + self.PROXY_URLS:
            try:
                url = f"{proxy}{api_url}" if proxy else api_url
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"获取版本信息失败 ({proxy or 'direct'}): {e}")
                continue
        
        return None
    
    def get_download_url(self, release_info: Dict) -> Optional[str]:
        """获取Windows版本下载链接"""
        try:
            for asset in release_info.get('assets', []):
                if asset['name'] == 'me3-windows-amd64.zip':
                    return asset['browser_download_url']
            return None
        except Exception as e:
            print(f"解析下载链接失败: {e}")
            return None

    def get_installer_download_url(self, release_info: Dict) -> Optional[str]:
        """获取ME3安装程序下载链接"""
        try:
            for asset in release_info.get('assets', []):
                if asset['name'] == 'me3_installer.exe':
                    return asset['browser_download_url']
            return None
        except Exception as e:
            print(f"解析安装程序下载链接失败: {e}")
            return None
    
    def get_current_version(self) -> Optional[str]:
        """获取当前已安装的便携版版本"""
        try:
            import subprocess
            import re
            # 执行便携版me3.exe获取真实版本
            me3_exe_path = self.me3_dir / "bin" / "me3.exe"
            if me3_exe_path.exists():
                import sys
                creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                result = subprocess.run([str(me3_exe_path), '-V'],
                                      capture_output=True, text=True, timeout=5,
                                      creationflags=creation_flags)
                if result.returncode == 0:
                    # 解析版本输出，支持 "me3 0.8.1" 或 "0.8.1" 格式
                    output = result.stdout.strip()
                    version_match = re.search(r'v?(\d+\.\d+\.\d+)', output)
                    if version_match:
                        # 返回带v前缀的版本号，与GitHub API格式保持一致
                        return f"v{version_match.group(1)}"

            # 如果执行失败，回退到读取version.json（兼容性）
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version')
            return None
        except Exception as e:
            print(f"获取便携版版本失败: {e}")
            return None
    
    def save_version_info(self, version: str, release_info: Dict):
        """保存版本信息"""
        try:
            version_data = {
                'version': version,
                'tag_name': release_info.get('tag_name'),
                'published_at': release_info.get('published_at'),
                'download_url': self.get_download_url(release_info)
            }
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存版本信息失败: {e}")
    
    def extract_me3(self, zip_path: str) -> bool:
        """解压ME3工具"""
        try:
            # 检查zip文件是否存在
            if not os.path.exists(zip_path):
                print(f"ZIP文件不存在: {zip_path}")
                return False

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.me3_dir)

            # 删除下载的zip文件
            try:
                os.remove(zip_path)
            except Exception as e:
                print(f"删除ZIP文件失败: {e}")
                # 不影响解压成功的结果

            return True
        except Exception as e:
            print(f"解压失败: {e}")
            return False
    
    def download_me3(self, mirror_url: str = None) -> DownloadWorker:
        """下载ME3工具"""
        release_info = self.get_latest_release_info()
        if not release_info:
            return None

        download_url = self.get_download_url(release_info)
        if not download_url:
            return None

        # 智能选择镜像或使用指定镜像
        if mirror_url:
            # 使用指定的镜像
            proxy = mirror_url
        else:
            # 智能选择最佳下载源
            proxy = self.get_best_download_source(download_url)

        try:
            url = f"{proxy}{download_url}" if proxy else download_url
            zip_path = self.me3_dir / "me3-windows-amd64.zip"

            # 如果文件已存在，先删除
            if zip_path.exists():
                zip_path.unlink()

            worker = DownloadWorker(url, str(zip_path))

            def on_finished(success, message):
                if success:
                    if self.extract_me3(str(zip_path)):
                        self.save_version_info(release_info['tag_name'], release_info)
                        # 不要重复发送信号，让调用者处理
                    else:
                        # 解压失败时发送失败信号
                        pass

            worker.finished.connect(on_finished)
            return worker

        except Exception as e:
            mirror_name = self._get_mirror_display_name(proxy)
            print(f"创建ME3下载任务失败 ({mirror_name}): {e}")
            return None

    def download_me3_installer(self, mirror_url: str = None) -> DownloadWorker:
        """下载ME3安装程序"""
        release_info = self.get_latest_release_info()
        if not release_info:
            return None

        download_url = self.get_installer_download_url(release_info)
        if not download_url:
            return None

        # 智能选择镜像或使用指定镜像
        if mirror_url:
            # 使用指定的镜像
            proxy = mirror_url
        else:
            # 智能选择最佳下载源
            proxy = self.get_best_download_source(download_url)

        try:
            url = f"{proxy}{download_url}" if proxy else download_url

            # 保存到me3p目录
            installer_path = self.me3_dir / "me3_installer.exe"

            # 如果文件已存在，先删除
            if installer_path.exists():
                installer_path.unlink()

            worker = DownloadWorker(url, str(installer_path))

            def on_finished(success, message):
                if success:
                    self.me3_installer_download_finished.emit(True, "ME3安装程序下载完成", str(installer_path))
                else:
                    self.me3_installer_download_finished.emit(False, f"下载失败: {message}", "")

            worker.finished.connect(on_finished)
            return worker

        except Exception as e:
            mirror_name = self._get_mirror_display_name(proxy)
            print(f"创建ME3安装程序下载任务失败 ({mirror_name}): {e}")
            return None

    def is_me3_installed(self) -> bool:
        """检查ME3是否已安装（便携版）"""
        # ME3的可执行文件在bin子目录中
        me3_exe = self.me3_dir / "bin" / "me3.exe"
        me3_launcher = self.me3_dir / "bin" / "me3-launcher.exe"

        # 检查主要的ME3文件是否存在
        return me3_exe.exists() and me3_launcher.exists()

    def _get_system_env(self):
        """获取系统环境变量（排除虚拟环境）"""
        import os
        env = os.environ.copy()

        # 检测是否在虚拟环境中
        if 'VIRTUAL_ENV' in env:
            virtual_env = env['VIRTUAL_ENV']

            # 获取原始PATH
            original_path = env.get('PATH', '')

            # 移除虚拟环境相关的路径
            path_parts = original_path.split(os.pathsep)
            filtered_parts = []

            for part in path_parts:
                # 检查是否为虚拟环境相关路径
                # 只移除明确属于当前虚拟环境的路径
                is_venv_path = False

                # 更精确的虚拟环境路径检测
                if part and virtual_env:
                    # 标准化路径比较
                    part_normalized = os.path.normpath(part).lower()
                    venv_normalized = os.path.normpath(virtual_env).lower()

                    # 检查是否为虚拟环境的直接子路径
                    if (part_normalized.startswith(venv_normalized + os.sep.lower()) or
                        part_normalized == venv_normalized):
                        is_venv_path = True

                if not is_venv_path:
                    filtered_parts.append(part)

            # 重新构造PATH
            new_path = os.pathsep.join(filtered_parts)
            env['PATH'] = new_path

            # 移除虚拟环境变量
            del env['VIRTUAL_ENV']
            if 'PYTHONHOME' in env:
                del env['PYTHONHOME']

        return env

    def is_me3_full_installed(self) -> bool:
        """检查ME3完整安装版是否已安装"""
        try:
            import subprocess
            # 使用系统环境变量运行me3 -V命令检测
            system_env = self._get_system_env()
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(['me3', '-V'],
                                  capture_output=True, text=True, timeout=5,
                                  env=system_env, creationflags=creation_flags)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    def find_me3_install_path(self) -> Optional[str]:
        """使用where命令定位ME3安装版的me3.exe位置"""
        try:
            import subprocess
            import sys

            # 使用系统环境变量执行where命令
            system_env = self._get_system_env()
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            result = subprocess.run(['where', 'me3'],
                                  capture_output=True, text=True, timeout=10,
                                  env=system_env, creationflags=creation_flags)

            if result.returncode == 0 and result.stdout.strip():
                # where命令可能返回多个路径，取第一个
                me3_path = result.stdout.strip().split('\n')[0].strip()
                if me3_path and Path(me3_path).exists():
                    return me3_path

            return None

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            print(f"查找ME3安装路径失败: {e}")
            return None

    def find_uninstaller_path(self, me3_exe_path: str) -> Optional[str]:
        """根据me3.exe路径找到uninstall.exe（通常在../../uninstall.exe）"""
        try:
            from pathlib import Path

            me3_path = Path(me3_exe_path)
            if not me3_path.exists():
                return None

            # 尝试常见的卸载程序位置
            possible_paths = [
                me3_path.parent.parent / "uninstall.exe",  # ../../uninstall.exe
                me3_path.parent.parent / "Uninstall.exe",  # 大写版本
                me3_path.parent / "uninstall.exe",         # ../uninstall.exe
                me3_path.parent / "Uninstall.exe",         # ../Uninstall.exe
            ]

            for uninstall_path in possible_paths:
                if uninstall_path.exists():
                    return str(uninstall_path)

            return None

        except Exception as e:
            print(f"查找卸载程序路径失败: {e}")
            return None

    def uninstall_me3_full(self) -> tuple[bool, str]:
        """卸载ME3完整安装版

        Returns:
            tuple[bool, str]: (是否成功, 状态消息)
        """
        try:
            # 1. 检查是否有安装版
            if not self.is_me3_full_installed():
                return False, "未检测到ME3完整安装版"

            # 2. 定位me3.exe
            me3_path = self.find_me3_install_path()
            if not me3_path:
                return False, "无法定位ME3安装路径"

            # 3. 找到卸载程序
            uninstaller_path = self.find_uninstaller_path(me3_path)
            if not uninstaller_path:
                return False, "未找到卸载程序，请手动卸载"

            # 4. 执行静默卸载
            import subprocess
            import sys

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run([uninstaller_path, '/S'],  # /S 参数用于静默卸载
                                  capture_output=True, text=True, timeout=60,
                                  creationflags=creation_flags)

            # 5. 验证卸载结果
            # 等待一段时间让卸载程序完成
            import time
            time.sleep(2)

            # 检查是否还能检测到安装版
            if not self.is_me3_full_installed():
                return True, "ME3完整安装版卸载成功"
            else:
                return False, "卸载可能未完全成功，请检查"

        except subprocess.TimeoutExpired:
            return False, "卸载超时，请手动检查卸载状态"
        except Exception as e:
            return False, f"卸载过程中发生错误: {str(e)}"



    def get_me3_full_version(self) -> Optional[str]:
        """获取ME3完整安装版版本"""
        try:
            import subprocess
            import re
            # 使用系统环境变量运行me3 -V命令获取版本
            system_env = self._get_system_env()
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(['me3', '-V'],
                                  capture_output=True, text=True, timeout=5,
                                  env=system_env, creationflags=creation_flags)
            if result.returncode == 0:
                # 解析版本输出，支持 "me3 v0.8.1" 或 "0.8.1" 格式
                output = result.stdout.strip()
                version_match = re.search(r'v?(\d+\.\d+\.\d+)', output)
                if version_match:
                    # 返回带v前缀的版本号，与GitHub API格式保持一致
                    return f"v{version_match.group(1)}"
        except Exception as e:
            print(f"获取ME3完整版版本失败: {e}")

        return None

    def get_me3_install_type(self) -> str:
        """获取ME3安装类型"""
        if self.is_me3_full_installed():
            return "full"
        elif self.is_me3_installed():
            return "portable"
        else:
            return "none"

    def get_version_by_type(self, version_type: str = None) -> Optional[str]:
        """根据版本类型获取对应版本

        Args:
            version_type: 版本类型 ("full", "portable", None)
                         None时自动检测当前安装类型

        Returns:
            对应版本号，如果未安装或获取失败则返回None
        """
        # 如果明确指定版本类型
        if version_type == "full":
            return self.get_me3_full_version()
        elif version_type == "portable":
            return self.get_current_version()

        # 自动检测模式：优先检测安装版，再检测便携版
        if self.is_me3_full_installed():
            return self.get_me3_full_version()
        elif self.is_me3_installed():
            return self.get_current_version()

        return None
    
    def check_for_updates(self) -> bool:
        """检查是否有更新"""
        current_version = self.get_current_version()
        if not current_version:
            return True  # 未安装，需要下载

        release_info = self.get_latest_release_info()
        if not release_info:
            return False

        latest_version = release_info.get('tag_name')
        return current_version != latest_version

    # ERModsMerger相关方法已移除 - 备份在 old/utils/download_manager_erm_backup.py









    # ==================== EasyTier 相关方法 ====================

    def get_latest_easytier_version(self, include_prerelease: bool = False) -> Optional[str]:
        """获取EasyTier最新版本

        Args:
            include_prerelease: 是否包含预发行版
        """
        try:
            release_info = self.get_easytier_release_info(include_prerelease)
            if release_info:
                return release_info.get('tag_name', '').lstrip('v')
            return None
        except Exception as e:
            print(f"获取EasyTier版本失败: {e}")
            return None

    def get_easytier_release_info(self, include_prerelease: bool = False) -> Optional[Dict]:
        """获取EasyTier发行版详细信息

        Args:
            include_prerelease: 是否包含预发行版

        Returns:
            包含版本信息的字典，包括tag_name, prerelease等字段
        """
        cache_type = 'prerelease' if include_prerelease else 'release'

        # 先检查缓存
        cached_data = self._get_cached_data(cache_type)
        if cached_data:
            return cached_data

        try:
            if include_prerelease:
                # 获取所有发行版，包括预发行版
                url = "https://api.github.com/repos/EasyTier/EasyTier/releases"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                releases = response.json()
                if releases:
                    # 返回第一个发行版（最新的，可能是预发行版）
                    data = releases[0]
                    self._set_cache_data(cache_type, data)
                    return data
            else:
                # 只获取正式发行版
                url = "https://api.github.com/repos/EasyTier/EasyTier/releases/latest"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()
                self._set_cache_data(cache_type, data)
                return data
        except Exception as e:
            print(f"获取EasyTier发行版信息失败: {e}")
            return None

    def get_current_easytier_version(self) -> Optional[str]:
        """获取当前安装的EasyTier版本"""
        try:
            import subprocess
            import re
            # 执行EasyTier可执行文件获取真实版本
            easytier_exe_path = self.esr_dir / "easytier-core.exe"
            if easytier_exe_path.exists():
                import sys
                creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                result = subprocess.run([str(easytier_exe_path), '-V'],
                                      capture_output=True, text=True, timeout=5,
                                      creationflags=creation_flags)
                if result.returncode == 0:
                    # 解析版本输出，支持 "easytier-core 2.4.3-2145ef40" 格式
                    output = result.stdout.strip()
                    version_match = re.search(r'easytier-core\s+(\d+\.\d+\.\d+)', output)
                    if version_match:
                        # 返回版本号（不带v前缀，与EasyTier的格式保持一致）
                        return version_match.group(1)

            # 如果执行失败，回退到读取version.json（兼容性）
            if self.esr_version_file.exists():
                with open(self.esr_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version')
            return None
        except Exception as e:
            print(f"获取EasyTier版本失败: {e}")
            return None

    def save_easytier_version(self, version: str, is_prerelease: bool = False):
        """保存EasyTier版本信息

        Args:
            version: 版本号
            is_prerelease: 是否为预发行版
        """
        try:
            version_data = {
                'version': version,
                'is_prerelease': is_prerelease,
                'version_type': 'prerelease' if is_prerelease else 'release',
                'download_time': json.dumps(datetime.now(), default=str)
            }
            with open(self.esr_version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存EasyTier版本信息失败: {e}")

    def get_current_easytier_version_info(self) -> Optional[Dict]:
        """获取当前EasyTier版本详细信息"""
        try:
            if self.esr_version_file.exists():
                with open(self.esr_version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"读取EasyTier版本信息失败: {e}")
            return None

    def is_current_easytier_prerelease(self) -> bool:
        """检查当前安装的EasyTier是否为预发行版"""
        try:
            version_info = self.get_current_easytier_version_info()
            if version_info:
                return version_info.get('is_prerelease', False)
            return False
        except Exception as e:
            print(f"检查EasyTier版本类型失败: {e}")
            return False

    def check_easytier_update(self, include_prerelease: bool = False) -> tuple[bool, Optional[str], Optional[str]]:
        """检查EasyTier更新

        Args:
            include_prerelease: 是否包含预发行版
        """
        try:
            latest_version = self.get_latest_easytier_version(include_prerelease)
            current_version = self.get_current_easytier_version()

            if not latest_version:
                return False, None, "无法获取最新版本信息"

            if not current_version:
                version_type = "预发行版" if include_prerelease else "正式版"
                return True, latest_version, f"未安装EasyTier ({version_type})"

            # 简单的版本比较
            if latest_version != current_version:
                version_type = "预发行版" if include_prerelease else "正式版"
                return True, latest_version, f"发现新{version_type} {latest_version}"

            version_type = "预发行版" if include_prerelease else "正式版"
            return False, current_version, f"已是最新{version_type}"
        except Exception as e:
            return False, None, f"检查更新失败: {e}"

    def get_easytier_download_url(self, version: str) -> Optional[str]:
        """获取EasyTier下载链接"""
        try:
            # EasyTier Windows x86_64 下载链接格式
            filename = f"easytier-windows-x86_64-v{version}.zip"
            base_url = f"https://github.com/EasyTier/EasyTier/releases/download/v{version}/{filename}"
            return base_url
        except Exception as e:
            print(f"构建EasyTier下载链接失败: {e}")
            return None

    def download_easytier(self, version: str = None, selected_mirror: str = None, include_prerelease: bool = False) -> bool:
        """下载EasyTier

        Args:
            version: 指定版本号，如果为None则获取最新版本
            selected_mirror: 选择的镜像
            include_prerelease: 是否包含预发行版（仅在version为None时生效）
        """
        try:
            # 如果没有指定版本，获取最新版本
            if not version:
                version = self.get_latest_easytier_version(include_prerelease)
                if not version:
                    version_type = "预发行版" if include_prerelease else "正式版"
                    print(f"无法获取EasyTier最新{version_type}")
                    return False

            download_url = self.get_easytier_download_url(version)
            if not download_url:
                return False

            # 如果指定了镜像，优先使用指定的镜像
            if selected_mirror:
                self.easytier_mirrors_to_try = [selected_mirror] + [m for m in self.PROXY_URLS if m != selected_mirror] + [""]
            else:
                # 智能选择最佳下载源
                best_source = self.get_best_download_source(download_url)
                if best_source:
                    self.easytier_mirrors_to_try = [best_source] + [m for m in self.PROXY_URLS if m != best_source] + [""]
                else:
                    self.easytier_mirrors_to_try = [""] + self.PROXY_URLS

            # 保存下载参数
            self.easytier_download_params = {
                'version': version,
                'include_prerelease': include_prerelease,
                'download_url': download_url
            }

            # 开始尝试第一个镜像
            self.easytier_current_mirror_index = 0
            return self._try_next_easytier_mirror()

        except Exception as e:
            print(f"下载EasyTier失败: {e}")
            return False

    def _try_next_easytier_mirror(self) -> bool:
        """尝试下一个EasyTier镜像"""
        try:
            if self.easytier_current_mirror_index >= len(self.easytier_mirrors_to_try):
                print("所有EasyTier下载源都失败")
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(False, "所有下载源都失败")
                return False

            proxy = self.easytier_mirrors_to_try[self.easytier_current_mirror_index]
            download_url = self.easytier_download_params['download_url']
            version = self.easytier_download_params['version']

            url = f"{proxy}{download_url}" if proxy else download_url
            mirror_name = self._get_mirror_display_name(proxy)
            print(f"尝试从 {mirror_name} 下载EasyTier...")

            # 下载文件
            filename = f"easytier-windows-x86_64-v{version}.zip"
            save_path = self.esr_dir / filename

            # 创建下载工作线程
            self.easytier_download_worker = DownloadWorker(url, str(save_path))
            self.easytier_download_worker.finished.connect(
                lambda success, msg: self._on_easytier_download_finished_with_retry(success, msg, save_path)
            )
            self.easytier_download_worker.start()

            return True  # 下载已开始

        except Exception as e:
            mirror_name = self._get_mirror_display_name(self.easytier_mirrors_to_try[self.easytier_current_mirror_index])
            print(f"从 {mirror_name} 创建EasyTier下载任务失败: {e}")
            # 尝试下一个镜像
            self.easytier_current_mirror_index += 1
            return self._try_next_easytier_mirror()

    def _on_easytier_download_finished_with_retry(self, success: bool, message: str, save_path: Path):
        """EasyTier下载完成回调（带重试逻辑）"""
        if success:
            version = self.easytier_download_params['version']
            include_prerelease = self.easytier_download_params['include_prerelease']

            print("EasyTier下载完成，开始解压...")
            if self._extract_easytier(save_path, version):
                print("EasyTier安装完成")
                # 发送安装完成信号
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(True, "EasyTier安装完成")
            else:
                print("EasyTier解压失败")
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(False, "EasyTier解压失败")
        else:
            # 下载失败，尝试下一个镜像
            mirror_name = self._get_mirror_display_name(self.easytier_mirrors_to_try[self.easytier_current_mirror_index])
            print(f"从 {mirror_name} 下载EasyTier失败: {message}")

            # 尝试下一个镜像
            self.easytier_current_mirror_index += 1
            if not self._try_next_easytier_mirror():
                # 所有镜像都失败了
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(False, f"所有下载源都失败，最后错误: {message}")

    def _get_mirror_display_name(self, mirror_url: str) -> str:
        """获取镜像显示名称"""
        if not mirror_url:
            return "GitHub官方"
        elif "gh-proxy.com" in mirror_url:
            return "gh-proxy.com"
        elif "ghproxy.net" in mirror_url:
            return "ghproxy.net"
        elif "ghfast.top" in mirror_url:
            return "ghfast.top"
        else:
            return mirror_url.replace("https://", "").replace("http://", "").rstrip("/")

    def test_connectivity(self, url: str, timeout: int = 5) -> bool:
        """测试URL连通性"""
        try:
            import requests
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 400
        except Exception as e:
            print(f"连通性测试失败 {url}: {e}")
            return False

    def get_best_download_source(self, github_url: str) -> str:
        """获取最佳下载源（基于连通性测试）"""
        try:
            print("🔍 正在测试下载源连通性...")

            # 首先测试GitHub官方
            if self.test_connectivity("https://github.com", timeout=3):
                print("✅ GitHub官方连接正常")
                return ""  # 空字符串表示直接使用GitHub
            else:
                print("❌ GitHub官方连接失败，测试镜像站...")

                # 测试镜像站连通性
                for mirror in self.PROXY_URLS:
                    mirror_name = self._get_mirror_display_name(mirror)
                    test_url = f"{mirror}https://github.com"

                    if self.test_connectivity(test_url, timeout=3):
                        print(f"✅ {mirror_name} 连接正常")
                        return mirror
                    else:
                        print(f"❌ {mirror_name} 连接失败")

                print("⚠️ 所有镜像站都无法连接，将使用GitHub官方（可能较慢）")
                return ""  # 如果所有镜像都失败，还是尝试GitHub官方

        except Exception as e:
            print(f"连通性测试异常: {e}")
            return ""  # 异常时使用GitHub官方

    def _on_easytier_download_finished(self, success: bool, message: str, version: str, zip_path: Path, is_prerelease: bool = False):
        """EasyTier下载完成回调"""
        if success:
            print("EasyTier下载完成，开始解压...")
            if self._extract_easytier(zip_path, version):
                self.save_easytier_version(version, is_prerelease)
                print(f"EasyTier v{version} 安装完成")
                # 发送安装完成信号
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(True, f"EasyTier v{version} 安装完成")
            else:
                print("EasyTier解压失败")
                if hasattr(self, 'easytier_install_finished'):
                    self.easytier_install_finished.emit(False, "EasyTier解压失败")
        else:
            print(f"EasyTier下载失败: {message}")
            if hasattr(self, 'easytier_install_finished'):
                self.easytier_install_finished.emit(False, f"下载失败: {message}")

    def _extract_easytier(self, zip_path: Path, version: str) -> bool:
        """解压EasyTier"""
        try:
            import zipfile
            import shutil

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 解压到ESR目录
                zip_ref.extractall(self.esr_dir)

            # 删除zip文件
            zip_path.unlink()

            # 查找解压后的文件夹（通常是easytier-windows-x86_64）
            extracted_folders = [d for d in self.esr_dir.iterdir() if d.is_dir() and d.name.startswith('easytier-')]

            if extracted_folders:
                extracted_folder = extracted_folders[0]
                print(f"找到解压文件夹: {extracted_folder.name}")

                # 将文件从子文件夹移动到ESR根目录
                for file_path in extracted_folder.iterdir():
                    if file_path.is_file():
                        target_path = self.esr_dir / file_path.name
                        # 如果目标文件已存在，先删除
                        if target_path.exists():
                            target_path.unlink()
                        shutil.move(str(file_path), str(target_path))
                        print(f"移动文件: {file_path.name}")

                # 删除空的子文件夹
                extracted_folder.rmdir()
                print(f"删除空文件夹: {extracted_folder.name}")

            # 验证关键文件是否存在
            easytier_core = self.esr_dir / "easytier-core.exe"
            easytier_cli = self.esr_dir / "easytier-cli.exe"

            if easytier_core.exists() and easytier_cli.exists():
                print("EasyTier核心文件验证成功")
                return True
            else:
                print("EasyTier核心文件验证失败")
                print(f"查找路径: {self.esr_dir}")
                print(f"easytier-core.exe 存在: {easytier_core.exists()}")
                print(f"easytier-cli.exe 存在: {easytier_cli.exists()}")
                return False

        except Exception as e:
            print(f"解压EasyTier失败: {e}")
            return False

    # ==================== OnlineFix 相关方法 ====================

    def download_onlinefix(self, selected_mirror: str = None) -> bool:
        """下载OnlineFix工具包

        Args:
            selected_mirror: 选择的镜像
        """
        try:
            download_url = "https://github.com/QykXczj/test/releases/download/tests/OnlineFix.zip"

            # 如果指定了镜像，优先使用指定的镜像
            if selected_mirror:
                self.onlinefix_mirrors_to_try = [selected_mirror] + [m for m in self.PROXY_URLS if m != selected_mirror] + [""]
            else:
                # 智能选择最佳下载源
                best_source = self.get_best_download_source(download_url)
                if best_source:
                    self.onlinefix_mirrors_to_try = [best_source] + [m for m in self.PROXY_URLS if m != best_source] + [""]
                else:
                    self.onlinefix_mirrors_to_try = [""] + self.PROXY_URLS

            # 开始尝试第一个镜像
            self.onlinefix_current_mirror_index = 0
            return self._try_next_onlinefix_mirror(download_url)

        except Exception as e:
            print(f"下载OnlineFix失败: {e}")
            return False

    def _try_next_onlinefix_mirror(self, download_url: str) -> bool:
        """尝试下一个OnlineFix镜像"""
        try:
            if self.onlinefix_current_mirror_index >= len(self.onlinefix_mirrors_to_try):
                print("所有OnlineFix下载源都失败")
                self.onlinefix_download_finished.emit(False, "所有下载源都失败")
                return False

            proxy = self.onlinefix_mirrors_to_try[self.onlinefix_current_mirror_index]
            url = f"{proxy}{download_url}" if proxy else download_url
            mirror_name = self._get_mirror_display_name(proxy)
            print(f"尝试从 {mirror_name} 下载OnlineFix...")

            # 下载文件
            save_path = self.onlinefix_dir / "OnlineFix.zip"

            # 创建下载工作线程
            self.onlinefix_download_worker = DownloadWorker(url, str(save_path))
            self.onlinefix_download_worker.finished.connect(
                lambda success, msg: self._on_onlinefix_download_finished_with_retry(success, msg, save_path, download_url)
            )
            # 连接进度信号
            self.onlinefix_download_worker.progress.connect(self.onlinefix_download_progress.emit)
            self.onlinefix_download_worker.start()

            return True  # 下载已开始

        except Exception as e:
            mirror_name = self._get_mirror_display_name(self.onlinefix_mirrors_to_try[self.onlinefix_current_mirror_index])
            print(f"从 {mirror_name} 创建下载任务失败: {e}")
            # 尝试下一个镜像
            self.onlinefix_current_mirror_index += 1
            return self._try_next_onlinefix_mirror(download_url)

    def _on_onlinefix_download_finished_with_retry(self, success: bool, message: str, zip_path: Path, download_url: str):
        """OnlineFix下载完成回调（带重试逻辑）"""
        if success:
            print("OnlineFix下载完成，开始解压...")
            if self.extract_onlinefix(zip_path):
                print("OnlineFix工具包安装完成")
                # 发送安装完成信号
                self.onlinefix_download_finished.emit(True, "OnlineFix工具包安装完成")
            else:
                print("OnlineFix解压失败")
                self.onlinefix_download_finished.emit(False, "OnlineFix解压失败")
        else:
            # 下载失败，尝试下一个镜像
            mirror_name = self._get_mirror_display_name(self.onlinefix_mirrors_to_try[self.onlinefix_current_mirror_index])
            print(f"从 {mirror_name} 下载OnlineFix失败: {message}")

            # 尝试下一个镜像
            self.onlinefix_current_mirror_index += 1
            if not self._try_next_onlinefix_mirror(download_url):
                # 所有镜像都失败了
                self.onlinefix_download_finished.emit(False, f"所有下载源都失败，最后错误: {message}")

    def _on_onlinefix_download_finished(self, success: bool, message: str, zip_path: Path):
        """OnlineFix下载完成回调"""
        if success:
            print("OnlineFix下载完成，开始解压...")
            if self.extract_onlinefix(zip_path):
                print("OnlineFix工具包安装完成")
                # 发送安装完成信号
                self.onlinefix_download_finished.emit(True, "OnlineFix工具包安装完成")
            else:
                print("OnlineFix解压失败")
                self.onlinefix_download_finished.emit(False, "OnlineFix解压失败")
        else:
            print(f"OnlineFix下载失败: {message}")
            self.onlinefix_download_finished.emit(False, f"下载失败: {message}")

    def extract_onlinefix(self, zip_path: Path) -> bool:
        """解压OnlineFix工具包"""
        try:
            import zipfile
            import time

            if not zip_path.exists():
                print("❌ OnlineFix.zip文件不存在")
                return False

            print(f"📦 开始解压OnlineFix.zip: {zip_path}")

            # 解压文件到OnlineFix目录
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 获取压缩包内的文件列表
                file_list = zip_ref.namelist()
                print(f"📋 压缩包包含 {len(file_list)} 个文件")

                # 解压所有文件
                for file_info in zip_ref.infolist():
                    # 跳过目录
                    if file_info.is_dir():
                        continue

                    # 获取文件名（去除路径）
                    filename = Path(file_info.filename).name
                    target_path = self.onlinefix_dir / filename

                    # 如果文件已存在，先删除
                    if target_path.exists():
                        target_path.unlink()

                    # 解压文件
                    with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                        import shutil
                        shutil.copyfileobj(source, target)

                    print(f"✅ 解压完成: {filename}")

            # 创建解压完成标志
            extracted_flag = self.onlinefix_dir / ".onlinefix_extracted"
            extracted_flag.write_text(f"OnlineFix extracted at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("🎉 OnlineFix解压完成")
            print("📦 原压缩包已保留")

            return True

        except Exception as e:
            print(f"❌ OnlineFix解压失败: {e}")
            return False

    def is_onlinefix_available(self) -> bool:
        """检查OnlineFix工具包是否可用"""
        try:
            # 检查关键文件是否存在
            required_files = [
                "steam_api64.dll",
                "OnlineFix.ini",
                "OnlineFix64.dll",
                "winmm.dll",
                "dlllist.txt",
                "esl2.zip",
                "tool.zip"
            ]

            for filename in required_files:
                file_path = self.onlinefix_dir / filename
                if not file_path.exists():
                    return False

            return True

        except Exception as e:
            print(f"检查OnlineFix可用性失败: {e}")
            return False
