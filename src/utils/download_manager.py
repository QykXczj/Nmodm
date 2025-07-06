"""
下载管理器
负责ME3工具的下载和版本管理
"""
import os
import json
import zipfile
import requests
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
        self.version_file = self.me3_dir / "version.json"
        self.config_file = self.me3_dir / "mirrors.json"

        # 确保me3p目录存在
        self.me3_dir.mkdir(exist_ok=True)

        # 加载镜像配置
        self.PROXY_URLS = self.load_mirrors()

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
