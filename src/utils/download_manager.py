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
        self.version_file = self.me3_dir / "version.json"
        # self.erm_version_file = self.erm_dir / "version.json"  # ERModsMerger已移除
        self.esr_version_file = self.esr_dir / "version.json"  # EasyTier版本文件
        self.config_file = self.me3_dir / "mirrors.json"

        # 确保目录存在
        self.me3_dir.mkdir(exist_ok=True)
        # self.erm_dir.mkdir(exist_ok=True)  # ERModsMerger已移除
        self.esr_dir.mkdir(exist_ok=True)  # 确保ESR目录存在

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
    
    def get_current_version(self) -> Optional[str]:
        """获取当前已安装版本"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version')
            return None
        except Exception as e:
            print(f"读取版本信息失败: {e}")
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

        # 使用指定的镜像或默认镜像列表
        mirrors_to_try = [mirror_url] if mirror_url else (self.PROXY_URLS + [""])

        for proxy in mirrors_to_try:
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
                print(f"创建下载任务失败 ({proxy or 'direct'}): {e}")
                continue

        return None
    
    def is_me3_installed(self) -> bool:
        """检查ME3是否已安装"""
        # ME3的可执行文件在bin子目录中
        me3_exe = self.me3_dir / "bin" / "me3.exe"
        me3_launcher = self.me3_dir / "bin" / "me3-launcher.exe"

        # 检查主要的ME3文件是否存在
        return me3_exe.exists() and me3_launcher.exists()
    
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
            if self.esr_version_file.exists():
                with open(self.esr_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version')
            return None
        except Exception as e:
            print(f"读取EasyTier版本失败: {e}")
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
                mirrors_to_try = [selected_mirror] + [m for m in self.PROXY_URLS if m != selected_mirror] + [""]
            else:
                mirrors_to_try = [""] + self.PROXY_URLS

            # 尝试使用镜像下载
            for proxy in mirrors_to_try:
                try:
                    url = f"{proxy}{download_url}" if proxy else download_url
                    mirror_name = self._get_mirror_display_name(proxy)
                    print(f"尝试从 {mirror_name} 下载EasyTier...")

                    # 下载文件
                    filename = f"easytier-windows-x86_64-v{version}.zip"
                    save_path = self.esr_dir / filename

                    # 创建下载工作线程
                    self.easytier_download_worker = DownloadWorker(url, str(save_path))
                    self.easytier_download_worker.finished.connect(
                        lambda success, msg: self._on_easytier_download_finished(success, msg, version, save_path, include_prerelease)
                    )
                    self.easytier_download_worker.start()

                    return True  # 下载已开始

                except Exception as e:
                    mirror_name = self._get_mirror_display_name(proxy)
                    print(f"从 {mirror_name} 下载失败: {e}")
                    continue

            print("所有下载源都失败")
            return False

        except Exception as e:
            print(f"下载EasyTier失败: {e}")
            return False

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
