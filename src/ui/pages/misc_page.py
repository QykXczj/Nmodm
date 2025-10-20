"""
杂项页面
其他功能和工具的集合
"""
import requests
import json
import os
import struct
import hashlib
import zipfile
import shutil
import tempfile
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QLineEdit, QFileDialog,
                               QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal
from .base_page import BasePage
from ..components.dialogs import NotificationDialog, ConfirmDialog
from src.i18n.language_switcher import LanguageSwitcher
from src.i18n.manager import TranslationManager, t

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Nightreign存档转换常量
DS2_KEY = b'\x18\xF6\x32\x66\x05\xBD\x17\x8A\x55\x24\x52\x3A\xC0\xA0\xC6\x09'
IV_SIZE = 0x10
PADDING_SIZE = 0xC
START_OF_CHECKSUM_DATA = 4
END_OF_CHECKSUM_DATA = PADDING_SIZE + 16

class BND4Entry:
    """BND4文件条目处理类"""
    def __init__(self, raw_data: bytes, index: int, size: int, offset: int):
        self.index = index
        self.size = size
        self.data_offset = offset
        self._raw_data = raw_data
        self._encrypted_data = raw_data[offset:offset + size]
        self._clean_data = b''

        # 提取IV和加密载荷
        self._iv = self._encrypted_data[:IV_SIZE]
        self._encrypted_payload = self._encrypted_data[IV_SIZE:]
        self.decrypted = False

    def decrypt(self):
        """解密条目数据"""
        try:
            decryptor = Cipher(algorithms.AES(DS2_KEY), modes.CBC(self._iv)).decryptor()
            self._clean_data = decryptor.update(self._encrypted_payload) + decryptor.finalize()
            self.decrypted = True
        except Exception as e:
            raise Exception(f"解密失败: {str(e)}")

    def calculate_checksum(self) -> bytes:
        """计算MD5校验和"""
        checksum_end = len(self._clean_data) - END_OF_CHECKSUM_DATA
        data_for_hash = self._clean_data[START_OF_CHECKSUM_DATA:checksum_end]
        return hashlib.md5(data_for_hash).digest()

    def patch_checksum(self):
        """更新校验和"""
        checksum = self.calculate_checksum()
        checksum_end = len(self._clean_data) - END_OF_CHECKSUM_DATA
        self._clean_data = (
            self._clean_data[:checksum_end] +
            checksum +
            self._clean_data[checksum_end + 16:]
        )

    def encrypt_data(self) -> bytes:
        """重新加密数据"""
        encryptor = Cipher(algorithms.AES(DS2_KEY), modes.CBC(self._iv)).encryptor()
        encrypted_payload = encryptor.update(self._clean_data) + encryptor.finalize()
        return self._iv + encrypted_payload

class SaveBackupWorker(QThread):
    """存档备份工作线程"""
    progress_updated = Signal(int, str)  # 进度, 状态信息
    backup_finished = Signal(str)        # 完成信息
    error_occurred = Signal(str)         # 错误信息

    def __init__(self, source_path: str, backup_name: str = None, steam_id: str = None):
        super().__init__()
        self.source_path = source_path
        self.steam_id = steam_id
        self.backup_name = backup_name or self.generate_backup_name()
        self.backup_dir = Path("CDBAK")

    def generate_backup_name(self):
        """生成备份文件名"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%y-%m-%d_%H-%M")
        if self.steam_id:
            return f"{self.steam_id}-backup-{timestamp}.zip"
        else:
            return f"backup-{timestamp}.zip"

    def run(self):
        """执行备份"""
        try:
            import os
            from pathlib import Path

            self.progress_updated.emit(10, t("misc_page.worker.backup.preparing"))

            # 确保备份目录存在
            self.backup_dir.mkdir(exist_ok=True)

            # 检查源路径是否存在
            source = Path(self.source_path)
            if not source.exists():
                raise Exception(t("misc_page.worker.backup.source_not_exist").format(path=self.source_path))

            self.progress_updated.emit(30, t("misc_page.worker.backup.compressing"))

            # 创建备份文件路径
            backup_file = self.backup_dir / self.backup_name

            # 压缩存档文件夹
            import zipfile
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if source.is_file():
                    # 单个文件
                    zipf.write(source, source.name)
                else:
                    # 文件夹
                    total_files = sum(1 for _ in source.rglob('*') if _.is_file())
                    processed = 0

                    for file_path in source.rglob('*'):
                        if file_path.is_file():
                            # 计算相对路径
                            arcname = file_path.relative_to(source.parent)
                            zipf.write(file_path, arcname)
                            processed += 1

                            # 更新进度
                            progress = 30 + int((processed / total_files) * 60)
                            self.progress_updated.emit(progress, t("misc_page.worker.backup.compressing_progress").format(current=processed, total=total_files))

            self.progress_updated.emit(100, t("misc_page.worker.backup.complete"))

            # 获取文件大小
            file_size = backup_file.stat().st_size
            size_mb = file_size / (1024 * 1024)

            self.backup_finished.emit(t("misc_page.save_backup.dialog.backup_success").format(file=self.backup_name, size=f"{size_mb:.1f}", path=backup_file))

        except Exception as e:
            self.error_occurred.emit(t("misc_page.save_backup.error.backup_failed").format(error=str(e)))


class SaveRestoreWorker(QThread):
    """存档恢复工作线程"""
    progress_updated = Signal(int, str)  # 进度, 状态信息
    restore_finished = Signal(str)       # 完成信息
    error_occurred = Signal(str)         # 错误信息

    def __init__(self, backup_file: str, target_path: str):
        super().__init__()
        self.backup_file = backup_file
        self.target_path = target_path

    def run(self):
        """执行恢复"""
        try:
            self.progress_updated.emit(10, t("misc_page.worker.restore.preparing"))

            # 检查备份文件是否存在
            backup_path = Path(self.backup_file)
            if not backup_path.exists():
                raise Exception(t("misc_page.worker.restore.backup_not_exist").format(path=self.backup_file))

            # 检查目标路径
            target = Path(self.target_path)

            self.progress_updated.emit(30, t("misc_page.worker.restore.extracting"))

            # 解压备份文件
            import zipfile
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # 获取压缩包中的文件列表
                file_list = zipf.namelist()
                total_files = len(file_list)

                # 如果目标目录存在，先备份
                if target.exists():
                    backup_target = target.parent / f"{target.name}_backup_before_restore"
                    if backup_target.exists():
                        shutil.rmtree(backup_target)
                    shutil.move(str(target), str(backup_target))

                # 创建目标目录
                target.mkdir(parents=True, exist_ok=True)

                # 解压文件
                for i, file_name in enumerate(file_list):
                    zipf.extract(file_name, target.parent)
                    progress = 30 + int((i + 1) / total_files * 60)
                    self.progress_updated.emit(progress, t("misc_page.worker.restore.extracting_progress").format(current=i+1, total=total_files))

            self.progress_updated.emit(100, t("misc_page.worker.restore.complete"))
            self.restore_finished.emit(t("misc_page.save_backup.dialog.restore_success").format(path=self.target_path))

        except Exception as e:
            self.error_occurred.emit(t("misc_page.save_backup.error.restore_failed").format(error=str(e)))


class SaveConverterWorker(QThread):
    """存档转换工作线程"""
    progress_updated = Signal(int, str)  # 进度, 状态信息
    conversion_finished = Signal(str)    # 完成信息
    error_occurred = Signal(str)         # 错误信息

    def __init__(self, input_file: str, output_file: str, new_steam_id: str):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.new_steam_id = new_steam_id
        self.entries = []

    def run(self):
        """执行存档转换"""
        try:
            self.progress_updated.emit(10, t("misc_page.worker.converter.reading"))

            # 读取原始文件
            with open(self.input_file, 'rb') as f:
                raw_data = f.read()

            # 验证BND4格式
            if raw_data[0:4] != b'BND4':
                raise Exception(t("misc_page.worker.converter.invalid_bnd4"))

            self.progress_updated.emit(20, t("misc_page.worker.converter.parsing"))

            # 解析BND4头部
            num_entries = struct.unpack("<i", raw_data[12:16])[0]
            BND4_HEADER_LEN = 64
            BND4_ENTRY_HEADER_LEN = 32

            # 解析所有条目
            for i in range(num_entries):
                pos = BND4_HEADER_LEN + (BND4_ENTRY_HEADER_LEN * i)
                entry_header = raw_data[pos:pos + BND4_ENTRY_HEADER_LEN]

                if entry_header[0:8] != b'\x40\x00\x00\x00\xff\xff\xff\xff':
                    continue

                entry_size = struct.unpack("<i", entry_header[8:12])[0]
                entry_data_offset = struct.unpack("<i", entry_header[16:20])[0]

                entry = BND4Entry(raw_data, i, entry_size, entry_data_offset)
                self.entries.append(entry)

            self.progress_updated.emit(40, t("misc_page.worker.converter.decrypting").format(count=len(self.entries)))

            # 解密所有条目
            for entry in self.entries:
                entry.decrypt()

            self.progress_updated.emit(60, t("misc_page.worker.converter.replacing"))

            # 转换Steam ID格式
            steam_id_hex = format(int(self.new_steam_id), 'x').zfill(16)
            new_steam_id_bytes = bytes.fromhex(steam_id_hex)[::-1]  # 小端序

            # 查找并替换Steam ID
            modified_count = 0
            for entry in self.entries:
                if entry.index == 10:  # USERDATA_10包含Steam ID
                    # 在偏移0x8处查找Steam ID
                    if len(entry._clean_data) > 16:
                        entry._clean_data = bytearray(entry._clean_data)
                        entry._clean_data[8:16] = new_steam_id_bytes
                        entry._clean_data = bytes(entry._clean_data)
                        modified_count += 1

                # 在所有条目中搜索并替换Steam ID
                if entry.decrypted and len(entry._clean_data) > 8:
                    original_data = entry._clean_data
                    # 这里可以添加更全面的Steam ID搜索替换逻辑
                    if original_data != entry._clean_data:
                        modified_count += 1

            self.progress_updated.emit(80, t("misc_page.worker.converter.checksum"))

            # 重新计算校验和并加密
            new_data = bytearray(raw_data)
            for entry in self.entries:
                if entry.decrypted:
                    entry.patch_checksum()
                    encrypted_data = entry.encrypt_data()

                    # 替换原始数据
                    start_pos = entry.data_offset
                    new_data[start_pos:start_pos + len(encrypted_data)] = encrypted_data

            self.progress_updated.emit(90, t("misc_page.worker.converter.saving"))

            # 保存新文件
            with open(self.output_file, 'wb') as f:
                f.write(new_data)

            self.progress_updated.emit(100, t("misc_page.worker.converter.complete"))
            self.conversion_finished.emit(t("misc_page.worker.converter.success").format(count=modified_count, path=self.output_file))

        except Exception as e:
            self.error_occurred.emit(t("misc_page.save_converter.error.convert_failed").format(error=str(e)))


class SeamlessModChecker(QThread):
    """无缝MOD版本检查线程"""
    check_finished = Signal(dict)  # 检查完成信号
    error_occurred = Signal(str)   # 错误信号

    def __init__(self):
        super().__init__()
        self.api_url = "https://zx.xc86.pp.ua"
        self.token = "j31ElFpnnnsUBWev3U4rS8dvJY9fwjIt"

    def run(self):
        """执行版本检查"""
        try:
            # 获取本地版本
            local_version = self.get_local_version()

            # 获取最新版本
            latest_info = self.get_latest_version()

            if latest_info:
                result = {
                    'local_version': local_version,
                    'latest_version': latest_info['version'],
                    'latest_info': latest_info,
                    'needs_update': self.compare_versions(local_version, latest_info['version']) if local_version else True
                }
                self.check_finished.emit(result)
            else:
                self.error_occurred.emit(t("misc_page.worker.mod_checker.no_version_info"))

        except Exception as e:
            self.error_occurred.emit(t("misc_page.worker.mod_checker.check_failed").format(error=str(e)))

    def get_local_version(self):
        """获取本地版本信息"""
        try:
            version_file = os.path.join("Mods", "SeamlessCoop", "version.json")
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                    return version_data.get('version')
            return None
        except Exception as e:
            print(f"读取本地版本失败: {e}")
            return None

    def get_latest_version(self):
        """获取最新版本信息"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            response = requests.get(f"{self.api_url}?action=latest", headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get('success'):
                return data.get('data')
            else:
                raise Exception(f"API返回错误: {data.get('message', '未知错误')}")

        except requests.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("API返回数据格式错误")

    def compare_versions(self, local_version, latest_version):
        """比较版本号"""
        if not local_version:
            return True

        try:
            local_parts = [int(x) for x in local_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]

            # 补齐版本号位数
            while len(local_parts) < 3:
                local_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)

            for i in range(3):
                if latest_parts[i] > local_parts[i]:
                    return True
                elif latest_parts[i] < local_parts[i]:
                    return False

            return False  # 版本相同
        except Exception:
            return True  # 解析失败时建议更新


class SeamlessModDownloader(QThread):
    """无缝MOD下载安装线程"""
    progress_updated = Signal(int, str)  # 进度, 状态信息
    download_finished = Signal(str)      # 完成信息
    error_occurred = Signal(str)         # 错误信息

    def __init__(self, version_info):
        super().__init__()
        self.version_info = version_info
        self.api_url = "https://zx.xc86.pp.ua"
        self.token = "j31ElFpnnnsUBWev3U4rS8dvJY9fwjIt"

    def run(self):
        """执行下载安装"""
        try:
            version = self.version_info['version']
            self.progress_updated.emit(10, t("misc_page.worker.mod_downloader.downloading").format(version=version))

            # 下载文件
            zip_data = self.download_file(version)
            self.progress_updated.emit(50, t("misc_page.worker.mod_downloader.download_complete"))

            # 安装文件
            self.install_mod(zip_data)
            self.progress_updated.emit(90, t("misc_page.worker.mod_downloader.saving_version"))

            # 保存版本信息
            self.save_version_info()
            self.progress_updated.emit(90, t("misc_page.worker.mod_downloader.cleaning"))

            # 清理备份文件
            self.cleanup_backup()
            self.progress_updated.emit(100, t("misc_page.worker.mod_downloader.complete"))

            self.download_finished.emit(t("misc_page.worker.mod_downloader.success").format(version=version))

        except Exception as e:
            self.error_occurred.emit(t("misc_page.worker.mod_downloader.install_failed").format(error=str(e)))

    def download_file(self, version):
        """下载文件"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            response = requests.get(f"{self.api_url}?version={version}", headers=headers, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise Exception(t("misc_page.worker.mod_downloader.download_failed").format(error=str(e)))

    def install_mod(self, zip_data):
        """安装MOD"""
        try:
            # 确保Mods目录存在
            mods_dir = "Mods"
            os.makedirs(mods_dir, exist_ok=True)

            seamless_dir = os.path.join(mods_dir, "SeamlessCoop")

            # 备份现有安装
            if os.path.exists(seamless_dir):
                backup_dir = f"{seamless_dir}_backup"
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.move(seamless_dir, backup_dir)

            # 创建临时目录解压
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "SeamlessCoop.zip")

                # 保存zip文件
                with open(zip_path, 'wb') as f:
                    f.write(zip_data)

                # 解压文件
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # 查找SeamlessCoop文件夹
                extracted_seamless = None
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path) and item.lower() == "seamlesscoop":
                        extracted_seamless = item_path
                        break

                if not extracted_seamless:
                    raise Exception(t("misc_page.worker.mod_downloader.folder_not_found"))

                # 移动到目标位置
                shutil.move(extracted_seamless, seamless_dir)

        except Exception as e:
            # 恢复备份
            backup_dir = os.path.join(mods_dir, "SeamlessCoop_backup")
            if os.path.exists(backup_dir):
                if os.path.exists(seamless_dir):
                    shutil.rmtree(seamless_dir)
                shutil.move(backup_dir, seamless_dir)
            raise e

    def save_version_info(self):
        """保存版本信息"""
        try:
            version_file = os.path.join("Mods", "SeamlessCoop", "version.json")
            os.makedirs(os.path.dirname(version_file), exist_ok=True)

            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(self.version_info, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"保存版本信息失败: {e}")

    def cleanup_backup(self):
        """清理备份文件"""
        try:
            backup_dir = os.path.join("Mods", "SeamlessCoop_backup")
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
                print("✅ 备份文件已清理")
        except Exception as e:
            print(f"清理备份文件失败: {e}")


class PlayerSearchWorker(QThread):
    """玩家搜索工作线程"""
    search_finished = Signal(dict)  # 搜索完成信号
    error_occurred = Signal(str)    # 错误信号

    def __init__(self, query):
        super().__init__()
        self.query = query.strip()

    def run(self):
        """执行搜索"""
        try:
            # 判断输入类型：17位纯数字为Steam ID，否则为用户名
            if self.query.isdigit() and len(self.query) == 17:
                # 直接查询Steam ID
                self.search_by_steam_id(self.query)
            else:
                # 先搜索用户名获取Steam ID
                self.search_by_username(self.query)

        except Exception as e:
            self.error_occurred.emit(t("misc_page.worker.player_search.search_failed").format(error=str(e)))

    def search_by_username(self, username):
        """通过用户名搜索"""
        try:
            # 调用搜索API
            search_url = f"https://www.nightreigngg.com/api/searchUser?name={username}"
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()

            search_results = response.json()
            if not search_results:
                self.error_occurred.emit(t("misc_page.worker.player_search.user_not_found"))
                return

            # 获取第一个搜索结果的Steam ID
            steam_id = search_results[0]["steamID"]
            self.search_by_steam_id(steam_id)

        except requests.RequestException as e:
            self.error_occurred.emit(t("misc_page.worker.player_search.network_failed").format(error=str(e)))
        except (KeyError, IndexError) as e:
            self.error_occurred.emit(t("misc_page.worker.player_search.format_error"))

    def search_by_steam_id(self, steam_id):
        """通过Steam ID获取详细信息"""
        try:
            # 获取游戏历史数据来计算统计信息
            history_url = f"https://nightreigngg.onrender.com/api/getRunHistory?steamID={steam_id}"
            response = requests.get(history_url, timeout=15)
            response.raise_for_status()

            run_history = response.json()
            if not run_history:
                self.error_occurred.emit(t("misc_page.worker.player_search.no_data"))
                return

            # 处理数据并计算统计信息
            detailed_data = self.process_run_history(run_history)

            # 构造基础玩家信息（从第一条记录中获取用户名）
            username = "Unknown"
            if run_history and len(run_history) > 0:
                players = run_history[0].get('players', [])
                for player in players:
                    if player and player.get('name'):
                        username = player.get('name')
                        break

            # 构造兼容的player_data格式
            player_data = {
                'steamID': steam_id,
                'username': username,
                'total_games': detailed_data['total']['total_games'],
                'total_wins': detailed_data['total']['total_wins'],
                'timePlayed': 0  # 暂时设为0，因为API中没有这个字段
            }

            # 发送搜索结果
            self.search_finished.emit(player_data)

        except requests.RequestException as e:
            self.error_occurred.emit(f"网络请求失败: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"数据处理失败: {str(e)}")

    def process_run_history(self, run_history):
        """处理游戏历史数据 - 简化版本，只计算总体统计"""
        total_games = len(run_history) if run_history else 0
        total_wins = 0

        for game in run_history:
            if game.get('win', False):
                total_wins += 1

        return {
            'total': {
                'total_games': total_games,
                'total_wins': total_wins
            }
        }

class MiscPage(BasePage):
    """杂项页面"""

    def __init__(self, parent=None):
        super().__init__(t("misc_page.page_title"), parent)
        self.search_worker = None
        self.converter_worker = None
        self.current_player_data = None

        # 无缝MOD更新相关
        self.mod_checker = None
        self.mod_downloader = None
        self.current_mod_info = None

        # 存档备份相关
        self.backup_worker = None
        self.restore_worker = None
        self.backup_path = None

        # 修改标题布局，添加语言切换器
        self.setup_title_with_language_switcher()

        self.setup_content()

    def setup_title_with_language_switcher(self):
        """设置标题和语言切换器"""
        # 创建水平布局容器
        title_container = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)

        # 移除原有的标题标签
        self.title_label.setParent(None)

        # 重新添加标题标签到水平布局
        title_layout.addWidget(self.title_label)

        # 添加语言切换器（紧凑模式）
        self.language_switcher = LanguageSwitcher(self, show_icon=False, compact=True)
        title_layout.addWidget(self.language_switcher)

        # 添加弹性空间，让语言切换器靠右
        title_layout.addStretch()

        title_container.setLayout(title_layout)

        # 将标题容器插入到主布局的第一个位置
        self.main_layout.insertWidget(0, title_container)

    def setup_content(self):
        """设置页面内容"""
        # 创建战绩搜索功能
        self.create_compact_search_bar()

        # 添加分隔线
        self.add_separator()

        # 创建存档转换功能
        self.create_save_converter_section()

        # 添加分隔线
        self.add_separator()

        # 创建无缝MOD更新功能
        self.create_seamless_mod_section()

        # 添加分隔线
        self.add_separator()

        # 创建其他功能提示
        self.create_other_features_hint()

        self.add_stretch()

        # 初始化备份列表
        self.refresh_backup_list()

        # 加载备份配置
        self.load_backup_config()

        # 更新自动备份按钮状态
        self.update_auto_backup_button_state()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        try:
            # 更新页面标题
            if hasattr(self, 'title_label'):
                self.title_label.setText(t("misc_page.page_title"))

            # 更新无缝MOD更新区域
            if hasattr(self, 'seamless_title_label'):
                self.seamless_title_label.setText(t("misc_page.seamless_mod.title"))
            if hasattr(self, 'check_update_btn'):
                self.check_update_btn.setText(t("misc_page.seamless_mod.button.check_update"))
            if hasattr(self, 'download_update_btn'):
                # 保持当前按钮状态的文本
                current_text = self.download_update_btn.text()
                if "%" in current_text:
                    # 下载中，保持百分比显示
                    pass
                elif t("misc_page.seamless_mod.button.downloading") in current_text:
                    self.download_update_btn.setText(t("misc_page.seamless_mod.button.downloading"))
                elif t("misc_page.seamless_mod.button.install_complete") in current_text:
                    self.download_update_btn.setText(t("misc_page.seamless_mod.button.install_complete"))
                elif t("misc_page.seamless_mod.button.is_latest") in current_text:
                    self.download_update_btn.setText(t("misc_page.seamless_mod.button.is_latest"))
                else:
                    self.download_update_btn.setText(t("misc_page.seamless_mod.button.download_update"))
            if hasattr(self, 'gamepad_fix_btn'):
                self.gamepad_fix_btn.setText(t("misc_page.seamless_mod.button.gamepad_fix"))
            if hasattr(self, 'mod_version_label'):
                # 更新版本号显示（保持当前状态）
                current_text = self.mod_version_label.text()
                # 解析当前显示的版本信息并重新生成
                if t("misc_page.seamless_mod.checking") in current_text:
                    self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: {t('misc_page.seamless_mod.checking')}")
                elif t("misc_page.seamless_mod.not_installed") in current_text:
                    self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: {t('misc_page.seamless_mod.not_installed')}")
                elif t("misc_page.seamless_mod.check_failed") in current_text:
                    self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: {t('misc_page.seamless_mod.check_failed')}")
                elif t("misc_page.seamless_mod.latest") in current_text:
                    # 提取版本号
                    import re
                    version_match = re.search(r'v([\d.]+)', current_text)
                    if version_match:
                        version = version_match.group(1)
                        self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: v{version} ({t('misc_page.seamless_mod.latest')})")
                elif t("misc_page.seamless_mod.can_update") in current_text or "→" in current_text:
                    # 提取当前版本和最新版本
                    import re
                    versions = re.findall(r'v([\d.]+)', current_text)
                    if len(versions) >= 2:
                        current_ver = versions[0]
                        latest_ver = versions[1]
                        self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: v{current_ver} → v{latest_ver} {t('misc_page.seamless_mod.can_update')}")
                elif "v" in current_text:
                    # 只有版本号
                    import re
                    version_match = re.search(r'v([\d.]+)', current_text)
                    if version_match:
                        version = version_match.group(1)
                        self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: v{version}")

            # 更新战绩查询区域
            if hasattr(self, 'player_search_title_label'):
                self.player_search_title_label.setText(t("misc_page.player_search.title"))
            if hasattr(self, 'search_input'):
                self.search_input.setPlaceholderText(t("misc_page.player_search.placeholder"))
            if hasattr(self, 'search_btn'):
                self.search_btn.setText(t("misc_page.player_search.button.search"))
            if hasattr(self, 'initial_label'):
                self.initial_label.setText(t("misc_page.player_search.status.initial"))
            if hasattr(self, 'jump_btn'):
                self.jump_btn.setText(t("misc_page.player_search.button.view_details"))
            if hasattr(self, 'result_label') and hasattr(self, 'current_player_data') and self.current_player_data:
                # 重新生成结果文本
                player_data = self.current_player_data
                total_games = player_data.get('total_games', 0)
                total_wins = player_data.get('total_wins', 0)
                time_played = player_data.get('timePlayed', 0)
                win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
                hours = time_played // 60
                minutes = time_played % 60
                time_str = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m"
                result_text = t("misc_page.player_search.result.summary").format(
                    username=player_data.get('username', 'Unknown'),
                    total_games=total_games,
                    total_wins=total_wins,
                    win_rate=win_rate,
                    time_str=time_str
                )
                self.result_label.setText(result_text)

            # 更新存档转换区域
            if hasattr(self, 'converter_title_label'):
                self.converter_title_label.setText(t("misc_page.save_converter.title"))
            if hasattr(self, 'converter_warning_title'):
                self.converter_warning_title.setText("⚠️ " + t("misc_page.save_converter.warning.title"))
            if hasattr(self, 'usage_help_btn'):
                self.usage_help_btn.setText(t("misc_page.save_converter.button.help"))
            if hasattr(self, 'file_title_label'):
                self.file_title_label.setText(t("misc_page.save_converter.file_selection.title"))
            if hasattr(self, 'file_path_label'):
                current_path = self.file_path_label.property("file_path")
                if not current_path:
                    self.file_path_label.setText(t("misc_page.save_converter.file_selection.placeholder"))
            if hasattr(self, 'select_file_btn'):
                self.select_file_btn.setText(t("misc_page.save_converter.file_selection.button"))
            if hasattr(self, 'steam_title_label'):
                self.steam_title_label.setText(t("misc_page.save_converter.steam_id.title"))
            if hasattr(self, 'steam_id_input'):
                self.steam_id_input.setPlaceholderText(t("misc_page.save_converter.steam_id.placeholder"))
            if hasattr(self, 'locate_save_btn'):
                self.locate_save_btn.setText(t("misc_page.save_converter.steam_id.button"))
                self.locate_save_btn.setToolTip(t("misc_page.save_converter.steam_id.tooltip"))
            if hasattr(self, 'convert_btn'):
                # 保持当前按钮状态的文本
                current_text = self.convert_btn.text()
                if t("misc_page.save_converter.button.converting") in current_text:
                    self.convert_btn.setText(t("misc_page.save_converter.button.converting"))
                else:
                    self.convert_btn.setText(t("misc_page.save_converter.button.convert"))

            # 更新存档备份管理区域
            if hasattr(self, 'backup_title_label'):
                self.backup_title_label.setText(t("misc_page.save_backup.title"))
            if hasattr(self, 'path_title_label'):
                self.path_title_label.setText(t("misc_page.save_backup.path_setting.title"))
            if hasattr(self, 'backup_path_label'):
                current_path = self.backup_path_label.property("folder_path")
                if not current_path:
                    self.backup_path_label.setText(t("misc_page.save_backup.path_setting.placeholder"))
            if hasattr(self, 'select_path_btn'):
                self.select_path_btn.setToolTip(t("misc_page.save_backup.path_setting.tooltip"))
            if hasattr(self, 'operation_title_label'):
                self.operation_title_label.setText(t("misc_page.save_backup.operation.title"))
            if hasattr(self, 'create_backup_btn'):
                # 保持当前按钮状态的文本
                current_text = self.create_backup_btn.text()
                if "%" in current_text or t("misc_page.save_backup.operation.creating") in current_text:
                    # 备份中，保持进度显示
                    pass
                else:
                    self.create_backup_btn.setText(t("misc_page.save_backup.operation.create"))
            if hasattr(self, 'restore_backup_btn'):
                # 保持当前按钮状态的文本
                current_text = self.restore_backup_btn.text()
                if "%" in current_text or t("misc_page.save_backup.operation.restoring") in current_text:
                    # 恢复中，保持进度显示
                    pass
                else:
                    self.restore_backup_btn.setText(t("misc_page.save_backup.operation.restore"))
            if hasattr(self, 'delete_backup_btn'):
                self.delete_backup_btn.setText(t("misc_page.save_backup.operation.delete"))
            if hasattr(self, 'list_title_label'):
                self.list_title_label.setText(t("misc_page.save_backup.list.title"))
            if hasattr(self, 'warning_label'):
                self.warning_label.setText(t("misc_page.save_backup.list.warning"))
            if hasattr(self, 'settings_title_label'):
                self.settings_title_label.setText(t("misc_page.save_backup.settings.title"))
            if hasattr(self, 'auto_backup_checkbox'):
                self.auto_backup_checkbox.setText(t("misc_page.save_backup.settings.auto_backup"))
                # 更新工具提示
                if hasattr(self, 'backup_path_label') and self.backup_path_label.property("folder_path"):
                    self.auto_backup_checkbox.setToolTip(t("misc_page.save_backup.settings.tooltip_enabled"))
                else:
                    self.auto_backup_checkbox.setToolTip(t("misc_page.save_backup.settings.tooltip_disabled"))
            if hasattr(self, 'keep_label'):
                self.keep_label.setText(t("misc_page.save_backup.settings.keep_count"))

            # 更新其他功能提示
            if hasattr(self, 'other_hint_label'):
                self.other_hint_label.setText(t("misc_page.other.hint"))

            # 刷新备份列表（更新"暂无备份文件"文本）
            self.refresh_backup_list()

        except Exception as e:
            print(f"语言切换回调执行失败: {e}")

    def create_seamless_mod_section(self):
        """创建无缝MOD更新区域"""
        # 创建容器
        container = QFrame()
        container.setFixedHeight(50)
        container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #313244, stop:1 #45475a);
                border: 1px solid #585b70;
                border-radius: 8px;
                margin: 2px;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)

        # 标题和版本信息
        self.seamless_title_label = QLabel(t("misc_page.seamless_mod.title"))
        self.seamless_title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.seamless_title_label)

        # 当前版本显示
        self.mod_version_label = QLabel(f"{t('misc_page.seamless_mod.current_version')}: {t('misc_page.seamless_mod.checking')}")
        self.mod_version_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.mod_version_label)

        layout.addStretch()

        # 检查更新按钮
        self.check_update_btn = QPushButton(t("misc_page.seamless_mod.button.check_update"))
        self.check_update_btn.setFixedSize(80, 30)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #9399b2;
            }
        """)
        self.check_update_btn.clicked.connect(self.check_mod_update)
        layout.addWidget(self.check_update_btn)

        # 下载更新按钮
        self.download_update_btn = QPushButton(t("misc_page.seamless_mod.button.download_update"))
        self.download_update_btn.setFixedSize(80, 30)
        self.download_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #9399b2;
            }
        """)
        self.download_update_btn.clicked.connect(self.download_mod_update)
        self.download_update_btn.setEnabled(False)  # 初始禁用
        layout.addWidget(self.download_update_btn)

        # 无缝手柄问题解决方案按钮
        self.gamepad_fix_btn = QPushButton(t("misc_page.seamless_mod.button.gamepad_fix"))
        self.gamepad_fix_btn.setFixedSize(185, 30)
        self.gamepad_fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4a7d1;
            }
        """)
        self.gamepad_fix_btn.clicked.connect(self.open_gamepad_fix_guide)
        layout.addWidget(self.gamepad_fix_btn)

        self.add_content(container)

        # 初始化时检查本地版本
        self.check_local_mod_version()

    def create_compact_search_bar(self):
        """创建紧凑的搜索栏"""
        # 创建容器
        container = QFrame()
        container.setFixedHeight(50)  # 调整为50px高度
        container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e1e2e, stop:1 #2a2a3e);
                border: 0.5px solid #45475a;
                border-radius: 6px;
                padding: 0px;
            }
        """)

        # 主布局
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)  # 与StatusBar一致的边距
        layout.setSpacing(15)

        # 标题标签
        self.player_search_title_label = QLabel(t("misc_page.player_search.title"))
        self.player_search_title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 15px;
                font-weight: bold;
                min-width: 90px;
            }
        """)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("misc_page.player_search.placeholder"))
        self.search_input.setFixedHeight(32)  # 增加高度适应50px容器
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 14px;
                padding: 6px 10px;
                min-width: 220px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)

        # 搜索按钮
        self.search_btn = QPushButton(t("misc_page.player_search.button.search"))
        self.search_btn.setFixedSize(40, 32)  # 增加尺寸适应50px容器
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.search_btn.clicked.connect(self.search_player)

        # 结果显示区域
        self.result_widget = QWidget()
        self.result_layout = QHBoxLayout(self.result_widget)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setAlignment(Qt.AlignVCenter)

        # 初始状态
        self.show_initial_state()

        # 添加到布局
        layout.addWidget(self.player_search_title_label)
        layout.addWidget(self.search_input)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.result_widget)
        layout.addStretch()

        self.add_content(container)

        # 绑定回车键
        self.search_input.returnPressed.connect(self.search_player)

    def add_separator(self):
        """添加分隔线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: #313244;
                margin: 10px 0;
            }
        """)
        self.add_content(separator)



    def create_other_features_hint(self):
        """创建其他功能提示"""
        self.other_hint_label = QLabel(t("misc_page.other.hint"))
        self.other_hint_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 14px;
                text-align: center;
                padding: 20px;
            }
        """)
        self.other_hint_label.setAlignment(Qt.AlignCenter)
        self.add_content(self.other_hint_label)

    def show_initial_state(self):
        """显示初始状态"""
        self.clear_result_layout()

        self.initial_label = QLabel(t("misc_page.player_search.status.initial"))
        self.initial_label.setFixedHeight(32)  # 与输入框高度一致
        self.initial_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.result_layout.addWidget(self.initial_label)

    def show_loading_state(self):
        """显示加载状态"""
        self.clear_result_layout()

        loading_label = QLabel(t("misc_page.player_search.status.searching"))
        loading_label.setFixedHeight(32)
        loading_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.result_layout.addWidget(loading_label)

    def show_error_state(self, error_msg):
        """显示错误状态"""
        self.clear_result_layout()

        error_label = QLabel(t("misc_page.player_search.status.error").format(error=error_msg))
        error_label.setFixedHeight(32)
        error_label.setStyleSheet("""
            QLabel {
                color: #f38ba8;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.result_layout.addWidget(error_label)

    def clear_result_layout(self):
        """清空结果布局"""
        while self.result_layout.count():
            child = self.result_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def search_player(self):
        """搜索玩家"""
        query = self.search_input.text().strip()
        if not query:
            self.show_error_state(t("misc_page.player_search.error.empty_input"))
            return

        # 禁用搜索按钮，显示加载状态
        self.search_btn.setEnabled(False)
        self.show_loading_state()

        # 创建并启动搜索线程
        self.search_worker = PlayerSearchWorker(query)
        self.search_worker.search_finished.connect(self.on_search_finished)
        self.search_worker.error_occurred.connect(self.on_search_error)
        self.search_worker.finished.connect(self.on_search_complete)
        self.search_worker.start()

    def on_search_finished(self, player_data):
        """搜索完成处理"""
        self.current_player_data = player_data
        self.show_player_result(player_data)

    def on_search_error(self, error_msg):
        """搜索错误处理"""
        self.show_error_state(error_msg)

    def on_search_complete(self):
        """搜索完成（无论成功失败）"""
        self.search_btn.setEnabled(True)
        if self.search_worker:
            self.search_worker.deleteLater()
            self.search_worker = None

    def show_player_result(self, player_data):
        """显示玩家结果"""
        self.clear_result_layout()

        # 创建结果容器
        result_container = QWidget()
        result_container_layout = QHBoxLayout(result_container)
        result_container_layout.setContentsMargins(0, 0, 0, 0)
        result_container_layout.setSpacing(8)

        # 创建极简结果显示
        result_line = self.create_compact_result_line(player_data)
        result_container_layout.addWidget(result_line)

        # 添加跳转按钮
        self.jump_btn = QPushButton(t("misc_page.player_search.button.view_details"))
        self.jump_btn.setFixedSize(80, 32)
        self.jump_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.jump_btn.clicked.connect(self.open_user_page)
        result_container_layout.addWidget(self.jump_btn)

        self.result_layout.addWidget(result_container)

    def create_compact_result_line(self, player_data):
        """创建极简单行结果显示"""
        # 计算数据
        total_games = player_data.get('total_games', 0)
        total_wins = player_data.get('total_wins', 0)
        time_played = player_data.get('timePlayed', 0)

        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

        # 转换游戏时长
        hours = time_played // 60
        minutes = time_played % 60
        time_str = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m"

        # 创建单行显示
        result_text = t("misc_page.player_search.result.summary").format(
            username=player_data.get('username', 'Unknown'),
            total_games=total_games,
            total_wins=total_wins,
            win_rate=win_rate,
            time_str=time_str
        )

        self.result_label = QLabel(result_text)
        self.result_label.setFixedHeight(32)  # 与输入框高度一致
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 13px;
                padding: 6px 10px;
            }
        """)

        return self.result_label

    def open_user_page(self):
        """打开用户详情页面"""
        if not self.current_player_data:
            return

        steam_id = self.current_player_data.get('steamID')
        if not steam_id:
            return

        # 构造URL并在默认浏览器中打开
        url = f"https://www.nightreigngg.com/user/{steam_id}"
        import webbrowser
        webbrowser.open(url)

    def create_save_converter_section(self):
        """创建存档转换功能区域 - 参考快速启动页的卡片设计"""
        # 创建水平布局容器
        horizontal_container = QWidget()
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(6)

        # 左侧：存档转换操作卡片
        converter_card = self.create_converter_card()

        # 右侧：存档备份卡片
        backup_card = self.create_backup_card()

        # 添加到水平布局，调整宽度比例
        # 存档转换区域：存档备份区域 = 2:3
        horizontal_layout.addWidget(converter_card, 3)
        horizontal_layout.addWidget(backup_card, 4)

        horizontal_container.setLayout(horizontal_layout)
        self.add_content(horizontal_container)

    def create_converter_card(self):
        """创建存档转换操作卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 标题
        self.converter_title_label = QLabel(t("misc_page.save_converter.title"))
        self.converter_title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        layout.addWidget(self.converter_title_label)

        # 重要提醒和使用说明
        warning_container = QFrame()
        warning_container.setStyleSheet("""
            QFrame {
                background-color: #3c3836;
                border: 1px solid #f9e2af;
                border-radius: 4px;
                margin: 4px 0px;
            }
        """)
        warning_layout = QVBoxLayout(warning_container)
        warning_layout.setContentsMargins(8, 6, 8, 6)
        warning_layout.setSpacing(4)

        # 标题行（警告图标 + 使用说明按钮）
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.converter_warning_title = QLabel("⚠️ " + t("misc_page.save_converter.warning.title"))
        self.converter_warning_title.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        title_row.addWidget(self.converter_warning_title)
        title_row.addStretch()

        # 使用说明按钮
        self.usage_help_btn = QPushButton(t("misc_page.save_converter.button.help"))
        self.usage_help_btn.setFixedSize(80, 24)
        self.usage_help_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
        """)
        self.usage_help_btn.clicked.connect(self.show_usage_help)
        title_row.addWidget(self.usage_help_btn)

        warning_layout.addLayout(title_row)

        layout.addWidget(warning_container)

        # 文件选择区域
        file_group = QFrame()
        file_group.setStyleSheet("""
            QFrame {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(6, 6, 6, 6)
        file_layout.setSpacing(6)

        self.file_title_label = QLabel(t("misc_page.save_converter.file_selection.title"))
        self.file_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        file_layout.addWidget(self.file_title_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)

        self.file_path_label = QLabel(t("misc_page.save_converter.file_selection.placeholder"))
        self.file_path_label.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 6px 10px;
                color: #a6adc8;
                font-size: 12px;
                min-height: 20px;
            }
        """)
        file_row.addWidget(self.file_path_label, 1)

        self.select_file_btn = QPushButton(t("misc_page.save_converter.file_selection.button"))
        self.select_file_btn.setFixedSize(80, 32)
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
        """)
        self.select_file_btn.clicked.connect(self.select_save_file)
        file_row.addWidget(self.select_file_btn)

        file_layout.addLayout(file_row)
        layout.addWidget(file_group)

        # Steam ID输入区域
        steam_group = QFrame()
        steam_group.setStyleSheet("""
            QFrame {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        steam_layout = QVBoxLayout(steam_group)
        steam_layout.setContentsMargins(6, 6, 6, 6)
        steam_layout.setSpacing(6)

        self.steam_title_label = QLabel(t("misc_page.save_converter.steam_id.title"))
        self.steam_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        steam_layout.addWidget(self.steam_title_label)

        steam_row = QHBoxLayout()
        steam_row.setSpacing(8)

        self.steam_id_input = QLineEdit()
        self.steam_id_input.setPlaceholderText(t("misc_page.save_converter.steam_id.placeholder"))
        self.steam_id_input.setFixedHeight(32)
        self.steam_id_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 13px;
                padding: 6px 10px;
                font-family: monospace;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        steam_row.addWidget(self.steam_id_input, 1)

        # 定位存档按钮
        self.locate_save_btn = QPushButton(t("misc_page.save_converter.steam_id.button"))
        self.locate_save_btn.setFixedSize(32, 32)
        self.locate_save_btn.setToolTip(t("misc_page.save_converter.steam_id.tooltip"))
        self.locate_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
        """)
        self.locate_save_btn.clicked.connect(self.locate_save_folder)
        steam_row.addWidget(self.locate_save_btn)

        steam_layout.addLayout(steam_row)

        layout.addWidget(steam_group)

        # 转换按钮
        self.convert_btn = QPushButton(t("misc_page.save_converter.button.convert"))
        self.convert_btn.setFixedHeight(40)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)

        # 进度显示区域 - 初始隐藏
        self.progress_container = QFrame()
        self.progress_container.setVisible(False)
        self.progress_container.setStyleSheet("""
            QFrame {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(6, 6, 6, 6)
        progress_layout.setSpacing(4)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 4px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 11px;
            }
        """)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(self.progress_container)

        card.setLayout(layout)
        return card

    def create_converter_help_card(self):
        """创建存档转换帮助卡片"""
        help_content = """🎯 转换原理：
修改存档文件中的Steam ID，使其他玩家的存档能在你的账户下使用。

📋 操作步骤：
1. 选择要转换的.sl2存档文件；      2. 输入你的17位Steam ID
3. 点击开始转换，选择保存位置； 4. 将转换后的文件复制到游戏存档目录

🔍 如何获取Steam ID：
• Steam个人主页链接：
   https://steamcommunity.com/profiles/76561198378589834/
   其中 76561198368389836 就是Steam ID

• 本地存档文件夹：
   C:\\Users\\用户名\\AppData\\Roaming\\Nightreign\\76521198568389835
   文件夹名称就是Steam ID，点击 📁 按钮可直接打开存档文件夹

⚠️ 重要提醒：
• 转换前务必备份原始存档，转换过程不可逆，请谨慎操作
• 支持格式：.sl2、.co2存档文件，转换后请先测试存档是否正常加载

💡 技术说明：
AES-CBC解密算法处理存档文件替换其中的Steam ID并重新计算校验和确保文件完整性。"""

        return self.create_info_card("📖 使用说明", help_content)

    def create_info_card(self, title, content):
        """创建信息卡片 - 参考快速启动页"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        layout.addWidget(title_label)

        # 内容
        content_label = QLabel(content)
        content_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)

        card.setLayout(layout)
        return card

    def create_backup_card(self):
        """创建存档备份管理区域 - 整体大卡片，内部无卡片设计"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 12px 12px 6px 12px;
            }
        """)

        # 使用网格布局
        from PySide6.QtWidgets import QGridLayout
        layout = QGridLayout()
        layout.setContentsMargins(8, 6, 8, 0)
        layout.setSpacing(4)

        # 标题 - 跨越整行
        self.backup_title_label = QLabel(t("misc_page.save_backup.title"))
        self.backup_title_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        layout.addWidget(self.backup_title_label, 0, 0, 1, 2)  # 第0行，跨越2列

        # 存档路径设置
        path_group = QFrame()
        path_group.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        path_layout = QVBoxLayout(path_group)
        path_layout.setContentsMargins(6, 6, 6, 6)
        path_layout.setSpacing(6)

        self.path_title_label = QLabel(t("misc_page.save_backup.path_setting.title"))
        self.path_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        path_layout.addWidget(self.path_title_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self.backup_path_label = QLabel(t("misc_page.save_backup.path_setting.placeholder"))
        self.backup_path_label.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 6px 10px;
                color: #a6adc8;
                font-size: 12px;
                min-height: 20px;
            }
        """)
        path_row.addWidget(self.backup_path_label, 1)

        self.select_path_btn = QPushButton(t("misc_page.save_backup.path_setting.button"))
        self.select_path_btn.setFixedSize(32, 32)
        self.select_path_btn.setToolTip(t("misc_page.save_backup.path_setting.tooltip"))
        self.select_path_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
        """)
        self.select_path_btn.clicked.connect(self.select_backup_path)
        path_row.addWidget(self.select_path_btn)

        path_layout.addLayout(path_row)
        layout.addWidget(path_group, 1, 0, 1, 2)  # 第1行，跨越2列

        # 备份操作按钮
        operation_group = QFrame()
        operation_group.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        operation_layout = QVBoxLayout(operation_group)
        operation_layout.setContentsMargins(6, 6, 6, 6)
        operation_layout.setSpacing(6)

        self.operation_title_label = QLabel(t("misc_page.save_backup.operation.title"))
        self.operation_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        operation_layout.addWidget(self.operation_title_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        # 创建备份按钮
        self.create_backup_btn = QPushButton(t("misc_page.save_backup.operation.create"))
        self.create_backup_btn.setFixedSize(70, 28)
        self.create_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.create_backup_btn.clicked.connect(self.create_backup)
        button_row.addWidget(self.create_backup_btn)

        # 恢复备份按钮
        self.restore_backup_btn = QPushButton(t("misc_page.save_backup.operation.restore"))
        self.restore_backup_btn.setFixedSize(70, 28)
        self.restore_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #fab387;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f7d794;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.restore_backup_btn.clicked.connect(self.restore_backup)
        button_row.addWidget(self.restore_backup_btn)

        # 删除备份按钮
        self.delete_backup_btn = QPushButton(t("misc_page.save_backup.operation.delete"))
        self.delete_backup_btn.setFixedSize(70, 28)
        self.delete_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.delete_backup_btn.clicked.connect(self.delete_backup)
        button_row.addWidget(self.delete_backup_btn)

        operation_layout.addLayout(button_row)

        layout.addWidget(operation_group, 2, 0)  # 第2行，左列

        # 备份列表
        list_group = QFrame()
        list_group.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(6, 6, 6, 0)
        list_layout.setSpacing(6)

        # 创建标题行，包含标题和警告信息
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.list_title_label = QLabel(t("misc_page.save_backup.list.title"))
        self.list_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        title_row.addWidget(self.list_title_label)

        # 添加警告信息到标题右边
        self.warning_label = QLabel(t("misc_page.save_backup.list.warning"))
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 12px;
                font-weight: bold;
                background-color: #3c3836;
                border: 1px solid #f9e2af;
                border-radius: 3px;
                padding: 2px 6px;
            }
        """)
        title_row.addWidget(self.warning_label)
        title_row.addStretch()  # 添加弹性空间

        list_layout.addLayout(title_row)

        # 备份列表显示区域
        from PySide6.QtWidgets import QListWidget
        self.backup_list = QListWidget()
        self.backup_list.setFixedHeight(120)
        self.backup_list.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 11px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #45475a;
            }
        """)
        list_layout.addWidget(self.backup_list)

        layout.addWidget(list_group, 3, 0, 1, 2)  # 第3行，跨越2列

        # 备份设置
        settings_group = QFrame()
        settings_group.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(6, 6, 6, 6)
        settings_layout.setSpacing(6)

        self.settings_title_label = QLabel(t("misc_page.save_backup.settings.title"))
        self.settings_title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        settings_layout.addWidget(self.settings_title_label)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(8)

        # 自动备份复选框
        from PySide6.QtWidgets import QCheckBox, QSpinBox
        self.auto_backup_checkbox = QCheckBox(t("misc_page.save_backup.settings.auto_backup"))
        self.auto_backup_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #a6e3a1;
                border: 1px solid #a6e3a1;
                border-radius: 3px;
            }
        """)
        # 添加变更监听
        self.auto_backup_checkbox.stateChanged.connect(self.save_backup_config)
        settings_row.addWidget(self.auto_backup_checkbox)

        settings_row.addStretch()

        # 保留数量设置
        self.keep_label = QLabel(t("misc_page.save_backup.settings.keep_count"))
        self.keep_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
            }
        """)
        settings_row.addWidget(self.keep_label)

        self.keep_count_spinbox = QSpinBox()
        self.keep_count_spinbox.setRange(1, 20)
        self.keep_count_spinbox.setValue(5)
        self.keep_count_spinbox.setFixedSize(50, 24)
        self.keep_count_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 12px;
                padding: 2px 4px;
            }
        """)
        # 添加变更监听
        self.keep_count_spinbox.valueChanged.connect(self.save_backup_config)
        settings_row.addWidget(self.keep_count_spinbox)

        settings_layout.addLayout(settings_row)

        layout.addWidget(settings_group, 2, 1)  # 第2行，右列

        # 设置列宽比例：左列(操作按钮) : 右列(备份列表) = 1:1
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        card.setLayout(layout)
        return card

    def select_backup_path(self):
        """选择备份路径"""
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择存档文件夹",
            str(Path.home() / "AppData" / "Roaming" / "Nightreign")
        )

        if folder_path:
            self.backup_path_label.setText(folder_path)
            self.backup_path_label.setProperty("folder_path", folder_path)
            self.backup_path_label.setStyleSheet("""
                QLabel {
                    background-color: #181825;
                    border: 1px solid #a6e3a1;
                    border-radius: 4px;
                    padding: 6px 10px;
                    color: #a6e3a1;
                    font-size: 12px;
                    min-height: 20px;
                }
            """)
            self.refresh_backup_list()
            # 保存配置
            self.save_backup_config()
            # 更新自动备份按钮状态
            self.update_auto_backup_button_state()

    def create_backup(self):
        """创建备份"""
        # 检查是否已选择存档路径
        backup_path = self.backup_path_label.property("folder_path")
        if not backup_path:
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.warning"), t("misc_page.save_backup.dialog.select_path_first"), "warning", self)
            dialog.exec()
            return

        # 检查路径是否存在
        if not Path(backup_path).exists():
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.error"), t("misc_page.save_backup.dialog.path_not_exist"), "error", self)
            dialog.exec()
            return

        # 禁用按钮
        self.create_backup_btn.setEnabled(False)
        self.create_backup_btn.setText(t("misc_page.save_backup.operation.creating"))

        # 启动备份线程
        steam_id = self.get_current_steam_id()
        self.backup_worker = SaveBackupWorker(backup_path, steam_id=steam_id)
        self.backup_worker.progress_updated.connect(self.on_backup_progress)
        self.backup_worker.backup_finished.connect(self.on_backup_finished)
        self.backup_worker.error_occurred.connect(self.on_backup_error)
        self.backup_worker.finished.connect(self.on_backup_complete)
        self.backup_worker.start()

    def on_backup_progress(self, progress: int, status: str):
        """更新备份进度"""
        # 这里可以添加进度显示，暂时在按钮文字中显示
        self.create_backup_btn.setText(t("misc_page.save_backup.operation.progress").format(operation=t("misc_page.save_backup.operation.creating"), progress=progress))

    def on_backup_finished(self, message: str):
        """备份完成"""
        dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.backup_success"), message, "success", self)
        dialog.exec()
        self.refresh_backup_list()

    def on_backup_error(self, error_msg: str):
        """备份错误"""
        dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.backup_failed"), error_msg, "error", self)
        dialog.exec()

    def on_backup_complete(self):
        """备份完成（无论成功失败）"""
        self.create_backup_btn.setEnabled(True)
        self.create_backup_btn.setText(t("misc_page.save_backup.operation.create"))

        if self.backup_worker:
            self.backup_worker.deleteLater()
            self.backup_worker = None

    def restore_backup(self):
        """恢复备份"""
        # 检查是否选择了备份文件
        current_item = self.backup_list.currentItem()
        if not current_item:
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.info"), t("misc_page.save_backup.dialog.select_backup_first").format(operation=t("misc_page.save_backup.operation.restore")), "info", self)
            dialog.exec()
            return

        # 检查备份列表是否为空
        if self.backup_list.count() == 0 or current_item.text() in [t("misc_page.save_backup.list.empty"), "备份列表功能正在开发中..."]:
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.info"), t("misc_page.save_backup.dialog.no_backup_available"), "info", self)
            dialog.exec()
            return

        # 检查是否设置了存档路径
        backup_path = self.backup_path_label.property("folder_path")
        if not backup_path:
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.warning"), t("misc_page.save_backup.dialog.select_path_first"), "warning", self)
            dialog.exec()
            return

        # 解析文件名
        item_text = current_item.text()
        if item_text in [t("misc_page.save_backup.list.empty"), "备份列表功能正在开发中..."]:
            return

        # 提取文件名（移除大小信息）
        file_name = item_text.split(" [")[0]
        backup_file = Path("CDBAK") / file_name

        if not backup_file.exists():
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.error"), t("misc_page.save_backup.dialog.backup_not_exist"), "error", self)
            dialog.exec()
            return

        # 安全确认
        confirm_dialog = ConfirmDialog(
            t("misc_page.save_backup.dialog.title.restore_confirm"),
            t("misc_page.save_backup.dialog.restore_confirm").format(file=file_name, path=backup_path),
            t("misc_page.save_backup.dialog.restore_button"),
            t("misc_page.save_backup.dialog.cancel_button"),
            "warning",
            self
        )

        if confirm_dialog.exec() == ConfirmDialog.Accepted:
            # 禁用按钮
            self.restore_backup_btn.setEnabled(False)
            self.restore_backup_btn.setText(t("misc_page.save_backup.operation.restoring"))

            # 启动恢复线程
            self.restore_worker = SaveRestoreWorker(str(backup_file), backup_path)
            self.restore_worker.progress_updated.connect(self.on_restore_progress)
            self.restore_worker.restore_finished.connect(self.on_restore_finished)
            self.restore_worker.error_occurred.connect(self.on_restore_error)
            self.restore_worker.finished.connect(self.on_restore_complete)
            self.restore_worker.start()

    def on_restore_progress(self, progress: int, status: str):
        """更新恢复进度"""
        self.restore_backup_btn.setText(t("misc_page.save_backup.operation.progress").format(operation=t("misc_page.save_backup.operation.restoring"), progress=progress))

    def on_restore_finished(self, message: str):
        """恢复完成"""
        dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.restore_success"), message, "success", self)
        dialog.exec()

    def on_restore_error(self, error_msg: str):
        """恢复错误"""
        dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.restore_failed"), error_msg, "error", self)
        dialog.exec()

    def on_restore_complete(self):
        """恢复完成（无论成功失败）"""
        self.restore_backup_btn.setEnabled(True)
        self.restore_backup_btn.setText(t("misc_page.save_backup.operation.restore"))

        if self.restore_worker:
            self.restore_worker.deleteLater()
            self.restore_worker = None

    def delete_backup(self):
        """删除备份"""
        # 检查是否选择了备份文件
        current_item = self.backup_list.currentItem()
        if not current_item:
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.info"), t("misc_page.save_backup.dialog.select_backup_first").format(operation=t("misc_page.save_backup.operation.delete")), "info", self)
            dialog.exec()
            return

        # 解析文件名
        item_text = current_item.text()
        if item_text in [t("misc_page.save_backup.list.empty"), "备份列表功能正在开发中..."]:
            return

        # 提取文件名（移除大小信息）
        file_name = item_text.split(" [")[0]
        backup_file = Path("CDBAK") / file_name

        if not backup_file.exists():
            dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.error"), t("misc_page.save_backup.dialog.backup_not_exist"), "error", self)
            dialog.exec()
            return

        # 确认删除
        confirm_dialog = ConfirmDialog(
            t("misc_page.save_backup.dialog.title.delete_confirm"),
            t("misc_page.save_backup.dialog.delete_confirm").format(file=file_name),
            t("misc_page.save_backup.dialog.delete_button"),
            t("misc_page.save_backup.dialog.cancel_button"),
            "warning",
            self
        )

        if confirm_dialog.exec() == ConfirmDialog.Accepted:
            try:
                backup_file.unlink()
                dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.delete_success"), t("misc_page.save_backup.dialog.delete_success"), "success", self)
                dialog.exec()
                self.refresh_backup_list()
            except Exception as e:
                dialog = NotificationDialog(t("misc_page.save_backup.dialog.title.delete_failed"), t("misc_page.save_backup.error.delete_failed").format(error=str(e)), "error", self)
                dialog.exec()

    def refresh_backup_list(self):
        """刷新备份列表"""
        self.backup_list.clear()

        backup_dir = Path("CDBAK")
        if not backup_dir.exists():
            self.backup_list.addItem(t("misc_page.save_backup.list.empty"))
            return

        # 获取所有备份文件（包括手动和自动备份）
        backup_files = list(backup_dir.glob("*-backup-*.zip")) + list(backup_dir.glob("*-auto-*.zip")) + list(backup_dir.glob("backup-*.zip")) + list(backup_dir.glob("auto-*.zip"))
        if not backup_files:
            self.backup_list.addItem(t("misc_page.save_backup.list.empty"))
            return

        # 按时间排序（最新的在前）
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for backup_file in backup_files:
            # 获取文件信息
            file_size = backup_file.stat().st_size
            size_mb = file_size / (1024 * 1024)

            # 从文件名提取时间
            file_name = backup_file.name
            if file_name.startswith("backup_") and file_name.endswith(".zip"):
                time_part = file_name[7:-4]  # 移除 "backup_" 和 ".zip"
                display_name = f"{file_name} [{size_mb:.1f}MB]"
            else:
                display_name = f"{file_name} [{size_mb:.1f}MB]"

            self.backup_list.addItem(display_name)

    def get_backup_config_path(self):
        """获取备份配置文件路径"""
        backup_dir = Path("CDBAK")
        backup_dir.mkdir(exist_ok=True)
        return backup_dir / "backup_config.json"

    def load_backup_config(self):
        """加载备份配置"""
        try:
            config_file = self.get_backup_config_path()
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 设置存档路径
                backup_path = config.get('backup_path', '')
                if backup_path and Path(backup_path).exists():
                    self.backup_path_label.setText(backup_path)
                    self.backup_path_label.setProperty("folder_path", backup_path)
                    self.backup_path_label.setStyleSheet("""
                        QLabel {
                            background-color: #181825;
                            border: 1px solid #a6e3a1;
                            border-radius: 4px;
                            padding: 6px 10px;
                            color: #a6e3a1;
                            font-size: 12px;
                            min-height: 20px;
                        }
                    """)

                # 设置自动备份选项
                auto_backup = config.get('auto_backup_enabled', False)
                self.auto_backup_checkbox.setChecked(auto_backup)

                # 设置保留数量
                keep_count = config.get('keep_count', 5)
                self.keep_count_spinbox.setValue(keep_count)

        except Exception as e:
            print(f"加载备份配置失败: {e}")

    def save_backup_config(self):
        """保存备份配置"""
        try:
            config = {
                'backup_path': self.backup_path_label.property("folder_path") or '',
                'auto_backup_enabled': self.auto_backup_checkbox.isChecked(),
                'keep_count': self.keep_count_spinbox.value()
            }

            config_file = self.get_backup_config_path()
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"保存备份配置失败: {e}")

    def update_auto_backup_button_state(self):
        """更新自动备份复选框状态"""
        try:
            # 检查是否有存档路径
            backup_path = self.backup_path_label.property("folder_path")
            has_backup_path = bool(backup_path and backup_path.strip())

            # 启用/禁用自动备份复选框
            self.auto_backup_checkbox.setEnabled(has_backup_path)

            if not has_backup_path:
                # 如果没有存档路径，禁用自动备份并更新提示
                self.auto_backup_checkbox.setChecked(False)
                self.auto_backup_checkbox.setToolTip(t("misc_page.save_backup.settings.tooltip_disabled"))
            else:
                self.auto_backup_checkbox.setToolTip(t("misc_page.save_backup.settings.tooltip_enabled"))

        except Exception as e:
            print(f"更新自动备份复选框状态失败: {e}")

    def get_current_steam_id(self):
        """优先从配置文件获取Steam ID，降级方案是从存档路径中提取"""
        try:
            # 从配置文件获取存档路径
            config_file = self.get_backup_config_path()
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                backup_path = config.get('backup_path', '')
                if backup_path:
                    from pathlib import Path
                    path = Path(backup_path)
                    # 检查路径中是否包含Steam ID
                    for part in path.parts:
                        if len(part) == 17 and part.isdigit():
                            return part

            return None
        except Exception as e:
            print(f"获取Steam ID失败: {e}")
            return None

    def check_auto_backup(self):
        """检查自动备份设置"""
        try:
            # 检查是否勾选了自动备份
            if hasattr(self, 'auto_backup_checkbox') and self.auto_backup_checkbox.isChecked():
                # 检查是否有设置存档路径
                backup_path = self.backup_path_label.property("folder_path") if hasattr(self, 'backup_path_label') else None
                if backup_path and Path(backup_path).exists():
                    # 执行自动备份
                    self.perform_auto_backup()
        except Exception as e:
            print(f"检查自动备份设置失败: {e}")

    def perform_auto_backup(self):
        """执行自动备份"""
        try:
            backup_path = self.backup_path_label.property("folder_path")
            if not backup_path or not Path(backup_path).exists():
                return

            # 检查备份数量限制
            self.cleanup_old_backups()

            # 创建自动备份（静默执行）
            from datetime import datetime
            timestamp = datetime.now().strftime("%y-%m-%d_%H-%M")

            # 获取Steam ID
            steam_id = self.get_current_steam_id()
            if steam_id:
                backup_name = f"{steam_id}-auto-{timestamp}.zip"
            else:
                backup_name = f"auto-{timestamp}.zip"

            # 启动备份线程（静默模式）
            self.auto_backup_worker = SaveBackupWorker(backup_path, backup_name)
            self.auto_backup_worker.backup_finished.connect(self.on_auto_backup_finished)
            self.auto_backup_worker.error_occurred.connect(self.on_auto_backup_error)
            self.auto_backup_worker.start()

        except Exception as e:
            print(f"自动备份失败: {e}")

    def cleanup_old_backups(self):
        """清理旧备份文件"""
        try:
            backup_dir = Path("CDBAK")
            if not backup_dir.exists():
                return

            # 获取保留数量设置
            keep_count = self.keep_count_spinbox.value() if hasattr(self, 'keep_count_spinbox') else 5

            # 获取所有备份文件
            backup_files = list(backup_dir.glob("*-backup-*.zip")) + list(backup_dir.glob("*-auto-*.zip")) + list(backup_dir.glob("backup-*.zip")) + list(backup_dir.glob("auto-*.zip"))

            # 按时间排序（最新的在前）
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # 删除超出保留数量的文件
            for old_backup in backup_files[keep_count:]:
                try:
                    old_backup.unlink()
                    print(f"已删除旧备份: {old_backup.name}")
                except Exception as e:
                    print(f"删除旧备份失败: {e}")

        except Exception as e:
            print(f"清理旧备份失败: {e}")

    def on_auto_backup_finished(self, message: str):
        """自动备份完成"""
        print(f"自动备份完成: {message}")
        self.refresh_backup_list()

    def on_auto_backup_error(self, error_msg: str):
        """自动备份错误"""
        print(f"自动备份失败: {error_msg}")

    def locate_save_folder(self):
        """定位存档文件夹"""
        try:
            import os
            from pathlib import Path

            # 获取用户目录
            user_dir = Path.home()
            nightreign_dir = user_dir / "AppData" / "Roaming" / "Nightreign"

            if nightreign_dir.exists():
                # 打开存档文件夹
                os.startfile(str(nightreign_dir))
                dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.info"), t("misc_page.save_converter.dialog.save_folder_opened"), "info", self)
                dialog.exec()
            else:
                dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.warning"), t("misc_page.save_converter.dialog.save_folder_not_found"), "warning", self)
                dialog.exec()

        except Exception as e:
            print(f"定位存档文件夹失败: {e}")
            dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.error"), t("misc_page.save_converter.dialog.locate_failed").format(error=str(e)), "error", self)
            dialog.exec()

    def select_save_file(self):
        """选择存档文件"""
        # 默认打开Nightreign存档目录
        import os
        from pathlib import Path

        user_dir = Path.home()
        default_dir = user_dir / "AppData" / "Roaming" / "Nightreign"

        # 如果默认目录不存在，使用用户目录
        if not default_dir.exists():
            default_dir = user_dir

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("misc_page.file_dialog.select_save_file"),
            str(default_dir),
            t("misc_page.file_dialog.save_file_filter")
        )

        if file_path:
            self.file_path_label.setText(os.path.basename(file_path))
            self.file_path_label.setProperty("file_path", file_path)
            self.file_path_label.setStyleSheet("""
                background-color: #181825;
                border: 1px solid #a6e3a1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #a6e3a1;
                font-size: 13px;
            """)

    def show_usage_help(self):
        """显示使用说明对话框"""
        # 创建自定义对话框，保持原有卡片的大小和格式
        from PySide6.QtWidgets import QDialog

        dialog = QDialog(self)
        dialog.setWindowTitle(t("misc_page.save_converter.help.title"))
        dialog.setMinimumSize(500, 600)  # 设置与原卡片相似的大小
        dialog.setModal(True)

        # 设置无边框窗口
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # 设置对话框样式
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                background-color: transparent;
                border: none;
            }
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
        """)

        # 创建内容区域
        content_layout = QVBoxLayout(dialog)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(12)

        # 使用原有的内容格式
        help_content = t("misc_page.save_converter.help.content")

        content_label = QLabel(help_content)
        content_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        content_label.setWordWrap(True)
        content_layout.addWidget(content_label)

        # 添加关闭按钮
        close_btn = QPushButton(t("misc_page.save_converter.help.close"))
        close_btn.setFixedSize(80, 32)
        close_btn.clicked.connect(dialog.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        content_layout.addLayout(button_layout)

        dialog.exec()

    def start_conversion(self):
        """开始存档转换"""
        # 验证输入
        file_path = self.file_path_label.property("file_path")
        if not file_path:
            dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.warning"), t("misc_page.save_converter.dialog.select_file_first"), "warning", self)
            dialog.exec()
            return

        steam_id = self.steam_id_input.text().strip()
        if not steam_id:
            dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.warning"), t("misc_page.save_converter.dialog.enter_steam_id"), "warning", self)
            dialog.exec()
            return

        if len(steam_id) != 17 or not steam_id.isdigit():
            dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.warning"), t("misc_page.save_converter.dialog.invalid_steam_id"), "warning", self)
            dialog.exec()
            return

        # 验证文件是否存在
        if not os.path.exists(file_path):
            dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.error"), t("misc_page.save_converter.dialog.file_not_exist").format(path=file_path), "error", self)
            dialog.exec()
            return

        # 最终确认对话框
        confirm_message = t("misc_page.save_converter.dialog.confirm_convert").format(file=os.path.basename(file_path), steam_id=steam_id)
        confirm_dialog = ConfirmDialog(t("misc_page.save_converter.dialog.title.convert_confirm"), confirm_message, t("misc_page.save_converter.dialog.convert_button"), t("misc_page.save_converter.dialog.cancel_button"), "warning", self)

        if confirm_dialog.exec() != ConfirmDialog.Accepted:
            return

        # 选择输出文件
        # 默认保存到Nightreign存档目录
        from pathlib import Path
        user_dir = Path.home()
        default_dir = user_dir / "AppData" / "Roaming" / "Nightreign"

        # 如果默认目录不存在，使用用户目录
        if not default_dir.exists():
            default_dir = user_dir

        # 根据原文件扩展名确定默认文件名
        original_ext = os.path.splitext(file_path)[1].lower()
        if original_ext == '.sl2':
            default_name = "NR0000.sl2"
        elif original_ext == '.sl':
            default_name = "NR0000.sl"
        elif original_ext == '.co2':
            default_name = "NR0000.co2"
        else:
            default_name = "NR0000.sl2"

        default_path = default_dir / default_name

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            t("misc_page.file_dialog.save_converted_file"),
            str(default_path),
            t("misc_page.file_dialog.save_file_filter")
        )

        if not output_path:
            return

        # 禁用界面元素
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText(t("misc_page.save_converter.button.converting"))
        self.progress_container.setVisible(True)
        self.progress_bar.setValue(0)

        # 启动转换线程
        self.converter_worker = SaveConverterWorker(file_path, output_path, steam_id)
        self.converter_worker.progress_updated.connect(self.on_conversion_progress)
        self.converter_worker.conversion_finished.connect(self.on_conversion_finished)
        self.converter_worker.error_occurred.connect(self.on_conversion_error)
        self.converter_worker.finished.connect(self.on_conversion_complete)
        self.converter_worker.start()

    def on_conversion_progress(self, progress: int, status: str):
        """更新转换进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)

    def on_conversion_finished(self, message: str):
        """转换完成"""
        success_msg = t("misc_page.save_converter.dialog.convert_success").format(message=message)
        dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.convert_success"), success_msg, "success", self)
        dialog.exec()

    def on_conversion_error(self, error_msg: str):
        """转换错误"""
        # 根据错误类型提供不同的解决建议
        if "BND4" in error_msg:
            detailed_msg = t("misc_page.save_converter.error.format_error").format(error=error_msg)
        elif "解密失败" in error_msg:
            detailed_msg = t("misc_page.save_converter.error.decrypt_error").format(error=error_msg)
        elif "权限" in error_msg or "Permission" in error_msg:
            detailed_msg = t("misc_page.save_converter.error.permission_error").format(error=error_msg)
        else:
            detailed_msg = t("misc_page.save_converter.error.convert_failed").format(error=error_msg)

        dialog = NotificationDialog(t("misc_page.save_converter.dialog.title.convert_failed"), detailed_msg, "error", self)
        dialog.exec()

    def on_conversion_complete(self):
        """转换完成（无论成功失败）"""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText(t("misc_page.save_converter.button.convert"))
        self.progress_container.setVisible(False)

        if self.converter_worker:
            self.converter_worker.deleteLater()
            self.converter_worker = None

    # 无缝MOD更新功能方法
    def check_local_mod_version(self):
        """检查本地MOD版本"""
        try:
            version_file = os.path.join("Mods", "SeamlessCoop", "version.json")
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                    version = version_data.get('version', t("misc_page.seamless_mod.not_installed"))
                    self.mod_version_label.setText(t("misc_page.seamless_mod.current_version") + f": v{version}")
            else:
                self.mod_version_label.setText(t("misc_page.seamless_mod.current_version") + ": " + t("misc_page.seamless_mod.not_installed"))
        except Exception as e:
            print(f"检查本地版本失败: {e}")
            self.mod_version_label.setText(t("misc_page.seamless_mod.current_version") + ": " + t("misc_page.seamless_mod.check_failed"))

    def check_mod_update(self):
        """检查MOD更新"""
        if self.mod_checker and self.mod_checker.isRunning():
            return

        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("检查中...")
        self.download_update_btn.setEnabled(False)

        self.mod_checker = SeamlessModChecker()
        self.mod_checker.check_finished.connect(self.on_check_finished)
        self.mod_checker.error_occurred.connect(self.on_check_error)
        self.mod_checker.start()

    def on_check_finished(self, result):
        """检查完成"""
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("检查更新")

        local_version = result.get('local_version')
        latest_version = result.get('latest_version')
        needs_update = result.get('needs_update', False)

        # 更新版本显示
        if local_version:
            self.mod_version_label.setText(t("misc_page.seamless_mod.current_version") + f": v{local_version}")
        else:
            self.mod_version_label.setText(t("misc_page.seamless_mod.current_version") + ": " + t("misc_page.seamless_mod.not_installed"))

        if needs_update:
            self.current_mod_info = result.get('latest_info')
            self.download_update_btn.setEnabled(True)
            self.download_update_btn.setText("下载更新")
            self.download_update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fab387;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f7d794;
                }
            """)

            # 直接显示在版本标签中
            current_ver = f"v{local_version}" if local_version else t("misc_page.seamless_mod.not_installed")
            self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: {current_ver} → v{latest_version} {t('misc_page.seamless_mod.can_update')}")
        else:
            self.download_update_btn.setEnabled(False)
            self.download_update_btn.setText(t("misc_page.seamless_mod.button.is_latest"))
            self.download_update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a6e3a1;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #94d3a2;
                }
            """)

            # 直接显示在版本标签中
            self.mod_version_label.setText(f"{t('misc_page.seamless_mod.current_version')}: v{latest_version} ({t('misc_page.seamless_mod.latest')})")

        if self.mod_checker:
            self.mod_checker.deleteLater()
            self.mod_checker = None

    def on_check_error(self, error_msg):
        """检查错误"""
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("检查更新")
        self.download_update_btn.setEnabled(False)

        # 直接显示在版本标签中
        self.mod_version_label.setText(t("misc_page.seamless_mod.check_failed") + f": {error_msg}")

        if self.mod_checker:
            self.mod_checker.deleteLater()
            self.mod_checker = None

    def download_mod_update(self):
        """下载MOD更新"""
        if not self.current_mod_info:
            self.mod_version_label.setText(t("misc_page.seamless_mod.error.no_update_info"))
            return

        if self.mod_downloader and self.mod_downloader.isRunning():
            return

        # 直接开始下载
        version = self.current_mod_info.get('version')
        self.mod_version_label.setText(t("misc_page.seamless_mod.status.preparing").format(version=version))

        # 开始下载
        self.check_update_btn.setEnabled(False)
        self.download_update_btn.setEnabled(False)
        self.download_update_btn.setText("下载中...")

        self.mod_downloader = SeamlessModDownloader(self.current_mod_info)
        self.mod_downloader.progress_updated.connect(self.on_download_progress)
        self.mod_downloader.download_finished.connect(self.on_download_finished)
        self.mod_downloader.error_occurred.connect(self.on_download_error)
        self.mod_downloader.start()

    def on_download_progress(self, progress, status):
        """下载进度更新"""
        self.download_update_btn.setText(f"{progress}%")
        self.mod_version_label.setText(t("misc_page.seamless_mod.status.downloading").format(status=status))

    def on_download_finished(self, message):
        """下载完成"""
        self.check_update_btn.setEnabled(True)
        self.download_update_btn.setEnabled(False)
        self.download_update_btn.setText("安装完成")
        self.download_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        # 更新本地版本显示
        self.check_local_mod_version()

        # 显示完成状态（包含清理信息）
        version = self.current_mod_info.get('version') if self.current_mod_info else t("misc_page.seamless_mod.not_installed")
        self.mod_version_label.setText(t("misc_page.seamless_mod.status.complete").format(version=version))

        print(f"✅ 安装完成: {message}")

        if self.mod_downloader:
            self.mod_downloader.deleteLater()
            self.mod_downloader = None

    def on_download_error(self, error_msg):
        """下载错误"""
        self.check_update_btn.setEnabled(True)
        self.download_update_btn.setEnabled(True)
        self.download_update_btn.setText(t("misc_page.seamless_mod.button.download_update"))

        self.mod_version_label.setText(t("misc_page.seamless_mod.error.update_failed").format(error=error_msg))

        if self.mod_downloader:
            self.mod_downloader.deleteLater()
            self.mod_downloader = None

    def open_gamepad_fix_guide(self):
        """打开无缝手柄问题解决方案"""
        try:
            guide_path = os.path.join("OnlineFix", "无缝手柄问题解决方案.png")

            if os.path.exists(guide_path):
                # 使用系统默认程序打开图片
                if os.name == 'nt':  # Windows
                    os.startfile(guide_path)
                elif os.name == 'posix':  # macOS/Linux
                    import sys
                    import subprocess
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    if sys.platform == 'darwin':  # macOS
                        subprocess.Popen(['open', guide_path], creationflags=creation_flags)
                    else:  # Linux
                        subprocess.Popen(['xdg-open', guide_path], creationflags=creation_flags)

                self.mod_version_label.setText(t("misc_page.other.gamepad_solution.opened"))
            else:
                self.mod_version_label.setText(t("misc_page.other.gamepad_solution.not_found"))

        except Exception as e:
            self.mod_version_label.setText(t("misc_page.other.gamepad_solution.error").format(error=str(e)))
            print(f"打开手柄解决方案失败: {e}")

    @staticmethod
    def trigger_auto_backup_if_enabled():
        """静态方法：在游戏启动时检查并执行自动备份"""
        import threading

        def check_and_backup():
            try:
                # 读取配置文件
                backup_dir = Path("CDBAK")
                config_file = backup_dir / "backup_config.json"

                if not config_file.exists():
                    return

                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 检查是否启用自动备份
                if not config.get('auto_backup_enabled', False):
                    return

                # 检查存档路径
                backup_path = config.get('backup_path', '')
                if not backup_path or not backup_path.strip():
                    return  # 存档路径为空，不执行自动备份

                if not Path(backup_path).exists():
                    return  # 存档路径不存在，不执行自动备份

                # 执行自动备份
                from datetime import datetime
                timestamp = datetime.now().strftime("%y-%m-%d_%H-%M")

                # 优先从配置文件获取Steam ID，降级方案是从存档路径中提取
                steam_id = None
                try:
                    path = Path(backup_path)
                    for part in path.parts:
                        if len(part) == 17 and part.isdigit():
                            steam_id = part
                            break
                except Exception:
                    pass

                if steam_id:
                    backup_name = f"{steam_id}-auto-{timestamp}.zip"
                else:
                    backup_name = f"auto-{timestamp}.zip"

                # 确保备份目录存在
                backup_dir.mkdir(exist_ok=True)

                # 创建备份文件路径
                backup_file = backup_dir / backup_name

                # 压缩存档文件夹
                import zipfile
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                    source = Path(backup_path)
                    if source.is_file():
                        # 单个文件
                        zipf.write(source, source.name)
                    else:
                        # 文件夹
                        for file_path in source.rglob('*'):
                            if file_path.is_file():
                                # 计算相对路径
                                arcname = file_path.relative_to(source.parent)
                                zipf.write(file_path, arcname)

                print(f"自动备份完成: {backup_name}")

                # 清理旧备份
                try:
                    keep_count = config.get('keep_count', 5)
                    backup_files = list(backup_dir.glob("*-backup-*.zip")) + list(backup_dir.glob("*-auto-*.zip")) + list(backup_dir.glob("backup-*.zip")) + list(backup_dir.glob("auto-*.zip"))
                    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                    for old_backup in backup_files[keep_count:]:
                        try:
                            old_backup.unlink()
                        except Exception:
                            pass
                except Exception:
                    pass

                # 备份完成后，尝试刷新UI
                try:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        # 查找杂项页面实例并刷新备份列表
                        for widget in app.topLevelWidgets():
                            if hasattr(widget, 'pages') and hasattr(widget.pages, 'get'):
                                misc_page = widget.pages.get('misc')
                                if misc_page and hasattr(misc_page, 'refresh_backup_list'):
                                    # 使用QTimer在主线程中执行刷新
                                    from PySide6.QtCore import QTimer
                                    QTimer.singleShot(100, misc_page.refresh_backup_list)
                                break
                except Exception:
                    pass

            except Exception as e:
                print(f"自动备份失败: {e}")

        # 快速检查配置文件是否存在和自动备份是否启用
        try:
            backup_dir = Path("CDBAK")
            config_file = backup_dir / "backup_config.json"

            if not config_file.exists():
                return False

            # 检查是否启用自动备份
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not config.get('auto_backup_enabled', False):
                return False

            # 检查存档路径
            backup_path = config.get('backup_path', '')
            if not backup_path or not backup_path.strip():
                return False

            if not Path(backup_path).exists():
                return False

            # 在后台线程中执行所有操作
            thread = threading.Thread(target=check_and_backup, daemon=True)
            thread.start()

            return True

        except Exception as e:
            print(f"游戏启动时自动备份失败: {e}")
            return False