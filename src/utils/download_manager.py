"""
下载管理器
负责ME3工具的下载和版本管理
"""
import os
import json
import zipfile
import requests
from datetime import datetime
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
        self.erm_dir = self.root_dir / "ERM"
        self.esr_dir = self.root_dir / "ESR"  # EasyTier目录
        self.version_file = self.me3_dir / "version.json"
        self.erm_version_file = self.erm_dir / "version.json"
        self.esr_version_file = self.esr_dir / "version.json"  # EasyTier版本文件
        self.config_file = self.me3_dir / "mirrors.json"

        # 确保目录存在
        self.me3_dir.mkdir(exist_ok=True)
        self.erm_dir.mkdir(exist_ok=True)
        self.esr_dir.mkdir(exist_ok=True)  # 确保ESR目录存在

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

    # ERModsMerger相关方法
    def get_erm_latest_release_info(self) -> Optional[Dict]:
        """获取ERModsMerger最新版本信息"""
        api_url = "https://api.github.com/repos/MadTekN1/ERModsMerger/releases/latest"

        for proxy in [""] + self.PROXY_URLS:
            try:
                url = f"{proxy}{api_url}" if proxy else api_url
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"获取ERModsMerger版本信息失败 ({proxy or 'direct'}): {e}")
                continue

        return None

    def get_erm_download_url(self, release_info: Dict) -> Optional[str]:
        """获取ERModsMerger下载链接"""
        try:
            for asset in release_info.get('assets', []):
                if 'ERModsMergerConsoleApp' in asset['name'] and asset['name'].endswith('.zip'):
                    return asset['browser_download_url']
            return None
        except Exception as e:
            print(f"解析ERModsMerger下载链接失败: {e}")
            return None

    def get_erm_current_version(self) -> Optional[str]:
        """获取ERModsMerger当前已安装版本"""
        try:
            if self.erm_version_file.exists():
                with open(self.erm_version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version')
            return None
        except Exception as e:
            print(f"读取ERModsMerger版本信息失败: {e}")
            return None

    def save_erm_version_info(self, version: str, release_info: Dict):
        """保存ERModsMerger版本信息"""
        try:
            version_data = {
                'version': version,
                'tag_name': release_info.get('tag_name'),
                'published_at': release_info.get('published_at'),
                'download_url': self.get_erm_download_url(release_info)
            }

            with open(self.erm_version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存ERModsMerger版本信息失败: {e}")

    def extract_erm(self, zip_path: str) -> bool:
        """解压ERModsMerger工具"""
        try:
            # 检查zip文件是否存在
            if not os.path.exists(zip_path):
                print(f"ZIP文件不存在: {zip_path}")
                return False

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.erm_dir)

            # 删除下载的zip文件
            try:
                os.remove(zip_path)
            except Exception as e:
                print(f"删除ZIP文件失败: {e}")
                # 不影响解压成功的结果

            return True
        except Exception as e:
            print(f"解压ERModsMerger失败: {e}")
            return False

    def download_erm(self, mirror_url: str = None) -> DownloadWorker:
        """下载ERModsMerger工具"""
        release_info = self.get_erm_latest_release_info()
        if not release_info:
            return None

        download_url = self.get_erm_download_url(release_info)
        if not download_url:
            return None

        # 使用指定的镜像或默认镜像列表
        mirrors_to_try = [mirror_url] if mirror_url else (self.PROXY_URLS + [""])

        for proxy in mirrors_to_try:
            try:
                url = f"{proxy}{download_url}" if proxy else download_url
                zip_path = self.erm_dir / "ERModsMerger.zip"

                # 如果文件已存在，先删除
                if zip_path.exists():
                    zip_path.unlink()

                worker = DownloadWorker(url, str(zip_path))

                def on_finished(success, message):
                    if success:
                        if self.extract_erm(str(zip_path)):
                            self.save_erm_version_info(release_info['tag_name'], release_info)
                            # 执行首次启动后的设置
                            self.setup_erm_after_first_run()
                        else:
                            # 解压失败时发送失败信号
                            pass

                worker.finished.connect(on_finished)
                return worker

            except Exception as e:
                print(f"创建ERModsMerger下载任务失败 ({proxy or 'direct'}): {e}")
                continue

        return None

    def is_erm_installed(self) -> bool:
        """检查ERModsMerger是否已安装"""
        # ERModsMerger的可执行文件
        erm_exe = self.erm_dir / "ERModsMerger.exe"
        return erm_exe.exists()

    def setup_erm_after_first_run(self):
        """ERModsMerger首次运行后的设置"""
        try:
            import time
            import subprocess
            import shutil

            # 首先启动ERModsMerger.exe生成配置文件夹
            erm_exe = self.erm_dir / "ERModsMerger.exe"
            if erm_exe.exists():
                print("正在首次启动ERModsMerger以生成配置文件夹...")
                # 启动程序
                process = subprocess.Popen([str(erm_exe)], cwd=str(self.erm_dir))

                # 检测必要的配置文件夹和配置文件是否生成完成
                required_folders = [
                    self.erm_dir / "ERModsMergerConfig",
                    self.erm_dir / "MergedMods",
                    self.erm_dir / "ModsToMerge"
                ]

                config_file = self.erm_dir / "ERModsMergerConfig" / "config.json"

                print("等待配置文件夹和配置文件生成...")
                max_wait_time = 60  # 最大等待60秒
                check_interval = 0.5  # 每0.5秒检查一次
                elapsed_time = 0

                while elapsed_time < max_wait_time:
                    # 检查所有必要文件夹是否都存在
                    all_folders_exist = all(folder.exists() for folder in required_folders)

                    # 检查config.json是否存在且包含完整配置
                    config_complete = self.check_config_complete(config_file)

                    if all_folders_exist and config_complete:
                        print("所有配置文件夹和配置文件已生成完成")
                        break

                    time.sleep(check_interval)
                    elapsed_time += check_interval

                    # 检查进程是否还在运行
                    if process.poll() is not None:
                        print("ERModsMerger进程已自动退出")
                        break

                # 如果进程还在运行，则关闭它
                if process.poll() is None:
                    print("关闭ERModsMerger进程...")
                    process.terminate()
                    time.sleep(1)  # 等待程序完全关闭

                print("ERModsMerger首次启动完成")

                # 检查并处理Regulations文件夹
                config_dir = self.erm_dir / "ERModsMergerConfig"
                regulations_dir = config_dir / "Regulations"
                onlinefix_regulations = self.root_dir / "OnlineFix" / "Regulations"

                if config_dir.exists():
                    print("开始配置ERModsMerger...")
                    # 删除ERModsMergerConfig内的Regulations文件夹
                    if regulations_dir.exists():
                        shutil.rmtree(regulations_dir)
                        print("已删除ERModsMergerConfig内的Regulations文件夹")

                    # 复制OnlineFix内的Regulations文件夹
                    if onlinefix_regulations.exists():
                        shutil.copytree(onlinefix_regulations, regulations_dir)
                        print("已复制OnlineFix内的Regulations文件夹到ERModsMergerConfig")
                        print("ERModsMerger配置完成！")
                    else:
                        print("警告：OnlineFix/Regulations文件夹不存在，请确保OnlineFix已正确安装")
                else:
                    print("警告：ERModsMergerConfig文件夹未生成，可能需要手动启动ERModsMerger")

        except Exception as e:
            print(f"ERModsMerger首次设置失败: {e}")

    def check_config_complete(self, config_file: Path) -> bool:
        """检查config.json配置是否完整"""
        try:
            if not config_file.exists():
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 检查必要的配置项
            required_keys = [
                "GamePath",
                "AppDataFolderPath",
                "ConfigPath",
                "ConsolePrintDelay",
                "ToolVersion",
                "CurrentProfile",
                "Profiles"
            ]

            # 检查顶级配置项
            for key in required_keys:
                if key not in config:
                    return False

            # 检查CurrentProfile配置
            current_profile = config.get("CurrentProfile", {})
            profile_required_keys = [
                "ProfileName",
                "ProfileDir",
                "ModsToMergeFolderPath",
                "MergedModsFolderPath",
                "Mods",
                "Modified"
            ]

            for key in profile_required_keys:
                if key not in current_profile:
                    return False

            # 检查Profiles数组
            profiles = config.get("Profiles", [])
            if not profiles or len(profiles) == 0:
                return False

            # 检查第一个Profile配置
            first_profile = profiles[0]
            for key in profile_required_keys:
                if key not in first_profile:
                    return False

            print("config.json配置文件完整性检查通过")
            return True

        except Exception as e:
            print(f"检查config.json配置失败: {e}")
            return False

    # ==================== EasyTier 相关方法 ====================

    def get_latest_easytier_version(self) -> Optional[str]:
        """获取EasyTier最新版本"""
        try:
            url = "https://api.github.com/repos/EasyTier/EasyTier/releases/latest"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('tag_name', '').lstrip('v')
        except Exception as e:
            print(f"获取EasyTier版本失败: {e}")
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

    def save_easytier_version(self, version: str):
        """保存EasyTier版本信息"""
        try:
            version_data = {
                'version': version,
                'download_time': json.dumps(datetime.now(), default=str)
            }
            with open(self.esr_version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存EasyTier版本信息失败: {e}")

    def check_easytier_update(self) -> tuple[bool, Optional[str], Optional[str]]:
        """检查EasyTier更新"""
        try:
            latest_version = self.get_latest_easytier_version()
            current_version = self.get_current_easytier_version()

            if not latest_version:
                return False, None, "无法获取最新版本信息"

            if not current_version:
                return True, latest_version, "未安装EasyTier"

            # 简单的版本比较
            if latest_version != current_version:
                return True, latest_version, f"发现新版本 {latest_version}"

            return False, current_version, "已是最新版本"
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

    def download_easytier(self, version: str = None, selected_mirror: str = None) -> bool:
        """下载EasyTier"""
        try:
            # 如果没有指定版本，获取最新版本
            if not version:
                version = self.get_latest_easytier_version()
                if not version:
                    print("无法获取EasyTier最新版本")
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
                        lambda success, msg: self._on_easytier_download_finished(success, msg, version, save_path)
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

    def _on_easytier_download_finished(self, success: bool, message: str, version: str, zip_path: Path):
        """EasyTier下载完成回调"""
        if success:
            print("EasyTier下载完成，开始解压...")
            if self._extract_easytier(zip_path, version):
                self.save_easytier_version(version)
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
