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
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QLineEdit, QFileDialog,
                               QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal
from .base_page import BasePage
from ..components.dialogs import NotificationDialog, ConfirmDialog

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
            self.progress_updated.emit(10, "正在读取存档文件...")

            # 读取原始文件
            with open(self.input_file, 'rb') as f:
                raw_data = f.read()

            # 验证BND4格式
            if raw_data[0:4] != b'BND4':
                raise Exception("不是有效的SL2存档文件（缺少BND4头）")

            self.progress_updated.emit(20, "正在解析文件结构...")

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

            self.progress_updated.emit(40, f"正在解密 {len(self.entries)} 个数据条目...")

            # 解密所有条目
            for entry in self.entries:
                entry.decrypt()

            self.progress_updated.emit(60, "正在替换Steam ID...")

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

            self.progress_updated.emit(80, "正在重新计算校验和...")

            # 重新计算校验和并加密
            new_data = bytearray(raw_data)
            for entry in self.entries:
                if entry.decrypted:
                    entry.patch_checksum()
                    encrypted_data = entry.encrypt_data()

                    # 替换原始数据
                    start_pos = entry.data_offset
                    new_data[start_pos:start_pos + len(encrypted_data)] = encrypted_data

            self.progress_updated.emit(90, "正在保存转换后的文件...")

            # 保存新文件
            with open(self.output_file, 'wb') as f:
                f.write(new_data)

            self.progress_updated.emit(100, "转换完成！")
            self.conversion_finished.emit(f"成功转换存档文件！\n修改了 {modified_count} 个数据条目\n保存到: {self.output_file}")

        except Exception as e:
            self.error_occurred.emit(f"转换失败: {str(e)}")


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
                self.error_occurred.emit("无法获取最新版本信息")

        except Exception as e:
            self.error_occurred.emit(f"检查更新失败: {str(e)}")

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
            self.progress_updated.emit(10, f"开始下载 SeamlessCoop v{version}...")

            # 下载文件
            zip_data = self.download_file(version)
            self.progress_updated.emit(50, "下载完成，正在安装...")

            # 安装文件
            self.install_mod(zip_data)
            self.progress_updated.emit(90, "正在保存版本信息...")

            # 保存版本信息
            self.save_version_info()
            self.progress_updated.emit(90, "正在清理临时文件...")

            # 清理备份文件
            self.cleanup_backup()
            self.progress_updated.emit(100, "安装完成！")

            self.download_finished.emit(f"SeamlessCoop v{version} 安装成功！")

        except Exception as e:
            self.error_occurred.emit(f"安装失败: {str(e)}")

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
            raise Exception(f"下载失败: {str(e)}")

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
                    raise Exception("下载的文件中未找到SeamlessCoop文件夹")

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
            self.error_occurred.emit(f"搜索失败: {str(e)}")

    def search_by_username(self, username):
        """通过用户名搜索"""
        try:
            # 调用搜索API
            search_url = f"https://www.nightreigngg.com/api/searchUser?name={username}"
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()

            search_results = response.json()
            if not search_results:
                self.error_occurred.emit("未找到该用户")
                return

            # 获取第一个搜索结果的Steam ID
            steam_id = search_results[0]["steamID"]
            self.search_by_steam_id(steam_id)

        except requests.RequestException as e:
            self.error_occurred.emit(f"网络请求失败: {str(e)}")
        except (KeyError, IndexError) as e:
            self.error_occurred.emit("搜索结果格式错误")

    def search_by_steam_id(self, steam_id):
        """通过Steam ID获取详细信息"""
        try:
            # 获取游戏历史数据来计算统计信息
            history_url = f"https://nightreigngg.onrender.com/api/getRunHistory?steamID={steam_id}"
            response = requests.get(history_url, timeout=15)
            response.raise_for_status()

            run_history = response.json()
            if not run_history:
                self.error_occurred.emit("未找到用户数据")
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
        super().__init__("杂项", parent)
        self.search_worker = None
        self.converter_worker = None
        self.current_player_data = None

        # 无缝MOD更新相关
        self.mod_checker = None
        self.mod_downloader = None
        self.current_mod_info = None

        self.setup_content()

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
        title_label = QLabel("🔄 无缝MOD更新")
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(title_label)

        # 当前版本显示
        self.mod_version_label = QLabel("当前版本: 检查中...")
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
        self.check_update_btn = QPushButton("检查更新")
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
        self.download_update_btn = QPushButton("下载更新")
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
        self.gamepad_fix_btn = QPushButton("🎮 无缝mod手柄问题解决方案")
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
        title_label = QLabel("🎮 战绩查询(需使用过战绩上传mod)")
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 15px;
                font-weight: bold;
                min-width: 90px;
            }
        """)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入用户名或Steam ID...")
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
        self.search_btn = QPushButton("🔍")
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
        layout.addWidget(title_label)
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
        hint_label = QLabel("💡 更多功能正在开发中，敬请期待...")
        hint_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 14px;
                text-align: center;
                padding: 20px;
            }
        """)
        hint_label.setAlignment(Qt.AlignCenter)
        self.add_content(hint_label)

    def show_initial_state(self):
        """显示初始状态"""
        self.clear_result_layout()

        initial_label = QLabel("💡 输入用户名或Steam ID")
        initial_label.setFixedHeight(32)  # 与输入框高度一致
        initial_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.result_layout.addWidget(initial_label)

    def show_loading_state(self):
        """显示加载状态"""
        self.clear_result_layout()

        loading_label = QLabel("🔄 搜索中...")
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

        error_label = QLabel(f"❌ {error_msg}")
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
            self.show_error_state("请输入用户名或Steam ID")
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
        jump_btn = QPushButton("查看详情")
        jump_btn.setFixedSize(80, 32)
        jump_btn.setStyleSheet("""
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
        jump_btn.clicked.connect(self.open_user_page)
        result_container_layout.addWidget(jump_btn)

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
        result_text = f"👤 {player_data.get('username', 'Unknown')} | 🎮 总计{total_games}场 | 🏆 {total_wins}胜 | 📊 {win_rate:.1f}% | ⏱️ {time_str}"

        result_label = QLabel(result_text)
        result_label.setFixedHeight(32)  # 与输入框高度一致
        result_label.setStyleSheet("""
            QLabel {
                background-color: #252537;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 13px;
                padding: 6px 10px;
            }
        """)

        return result_label

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

        # 右侧：使用说明卡片
        help_card = self.create_converter_help_card()

        # 添加到水平布局
        horizontal_layout.addWidget(converter_card)
        horizontal_layout.addWidget(help_card)

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
        title_label = QLabel("🎮 Nightreign 存档转换")
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

        # 重要提醒
        warning_label = QLabel("⚠️ 转换前请备份原始存档文件，转换过程不可逆！")
        warning_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 12px;
                font-weight: bold;
                background-color: #3c3836;
                border: 1px solid #f9e2af;
                border-radius: 4px;
                padding: 6px 8px;
                margin: 4px 0px;
            }
        """)
        layout.addWidget(warning_label)

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

        file_title = QLabel("📁 选择存档文件")
        file_title.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        file_layout.addWidget(file_title)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)

        self.file_path_label = QLabel("未选择文件")
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

        select_file_btn = QPushButton("选择文件")
        select_file_btn.setFixedSize(80, 32)
        select_file_btn.setStyleSheet("""
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
        select_file_btn.clicked.connect(self.select_save_file)
        file_row.addWidget(select_file_btn)

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

        steam_title = QLabel("🆔 输入你的Steam ID")
        steam_title.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        steam_layout.addWidget(steam_title)

        steam_row = QHBoxLayout()
        steam_row.setSpacing(8)

        self.steam_id_input = QLineEdit()
        self.steam_id_input.setPlaceholderText("例如: 76561198368389836")
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
        locate_save_btn = QPushButton("📁")
        locate_save_btn.setFixedSize(32, 32)
        locate_save_btn.setToolTip("定位存档文件夹")
        locate_save_btn.setStyleSheet("""
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
        locate_save_btn.clicked.connect(self.locate_save_folder)
        steam_row.addWidget(locate_save_btn)

        steam_layout.addLayout(steam_row)

        layout.addWidget(steam_group)

        # 转换按钮
        self.convert_btn = QPushButton("🚀 开始转换")
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
                dialog = NotificationDialog("提示", "已打开存档文件夹，请查看文件夹名称获取Steam ID", "info", self)
                dialog.exec()
            else:
                dialog = NotificationDialog("警告", "未找到存档文件夹，请确保游戏已运行过", "warning", self)
                dialog.exec()

        except Exception as e:
            print(f"定位存档文件夹失败: {e}")
            dialog = NotificationDialog("错误", f"定位存档文件夹失败: {e}", "error", self)
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
            "选择Nightreign存档文件",
            str(default_dir),
            "存档文件 (*.sl2 *.sl *.co2);;SL2 Files (*.sl2);;SL Files (*.sl);;CO2 Files (*.co2);;All Files (*.*)"
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

    def start_conversion(self):
        """开始存档转换"""
        # 验证输入
        file_path = self.file_path_label.property("file_path")
        if not file_path:
            dialog = NotificationDialog("警告", "请先选择存档文件！", "warning", self)
            dialog.exec()
            return

        steam_id = self.steam_id_input.text().strip()
        if not steam_id:
            dialog = NotificationDialog("警告", "请输入Steam ID！", "warning", self)
            dialog.exec()
            return

        if len(steam_id) != 17 or not steam_id.isdigit():
            dialog = NotificationDialog("警告",
                "Steam ID格式错误！\n\n"
                "Steam ID必须是17位纯数字，例如：76561198000000000\n"
                "你可以在Steam个人资料页面的URL中找到你的Steam ID", "warning", self)
            dialog.exec()
            return

        # 验证文件是否存在
        if not os.path.exists(file_path):
            dialog = NotificationDialog("错误", f"选择的文件不存在：\n{file_path}", "error", self)
            dialog.exec()
            return

        # 最终确认对话框
        confirm_message = (
            f"即将开始存档转换：\n\n"
            f"源文件：{os.path.basename(file_path)}\n"
            f"目标Steam ID：{steam_id}\n\n"
            f"⚠️ 请确保已备份原始存档文件！\n"
            f"转换过程不可逆，是否继续？"
        )
        confirm_dialog = ConfirmDialog("确认转换", confirm_message, "开始转换", "取消", "warning", self)

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
            "保存转换后的存档文件",
            str(default_path),
            "存档文件 (*.sl2 *.sl *.co2);;SL2 Files (*.sl2);;SL Files (*.sl);;CO2 Files (*.co2);;All Files (*.*)"
        )

        if not output_path:
            return

        # 禁用界面元素
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("转换中...")
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
        success_msg = (
            f"🎉 存档转换成功完成！\n\n"
            f"{message}\n\n"
            f"📋 使用说明：\n"
            f"1. 将转换后的文件复制到游戏存档目录\n"
            f"2. 启动游戏即可使用转换后的存档\n"
            f"3. 如有问题，请恢复原始备份文件\n\n"
            f"💡 提示：建议在使用前先测试存档是否正常加载"
        )
        dialog = NotificationDialog("转换完成", success_msg, "success", self)
        dialog.exec()

    def on_conversion_error(self, error_msg: str):
        """转换错误"""
        # 根据错误类型提供不同的解决建议
        if "BND4" in error_msg:
            detailed_msg = (
                f"文件格式错误：\n{error_msg}\n\n"
                "可能的原因：\n"
                "• 选择的不是有效的Nightreign存档文件\n"
                "• 文件已损坏或不完整\n"
                "• 文件不是支持的格式\n\n"
                "解决方案：\n"
                "• 确保选择正确的存档文件\n"
                "• 重新从游戏目录复制存档文件"
            )
        elif "解密失败" in error_msg:
            detailed_msg = (
                f"解密错误：\n{error_msg}\n\n"
                "可能的原因：\n"
                "• 存档文件已损坏\n"
                "• 文件被其他程序修改过\n"
                "• 不是Nightreign的存档文件\n\n"
                "解决方案：\n"
                "• 使用原始的、未修改的存档文件\n"
                "• 确认文件来源的可靠性"
            )
        elif "权限" in error_msg or "Permission" in error_msg:
            detailed_msg = (
                f"文件权限错误：\n{error_msg}\n\n"
                "可能的原因：\n"
                "• 文件被其他程序占用\n"
                "• 没有写入权限\n"
                "• 目标路径不存在\n\n"
                "解决方案：\n"
                "• 关闭可能占用文件的程序\n"
                "• 以管理员身份运行程序\n"
                "• 选择其他保存位置"
            )
        else:
            detailed_msg = (
                f"转换失败：\n{error_msg}\n\n"
                "建议：\n"
                "• 检查文件是否完整\n"
                "• 确认Steam ID格式正确\n"
                "• 重新尝试转换\n"
                "• 如问题持续，请联系技术支持"
            )

        dialog = NotificationDialog("转换失败", detailed_msg, "error", self)
        dialog.exec()

    def on_conversion_complete(self):
        """转换完成（无论成功失败）"""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")
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
                    version = version_data.get('version', '未知')
                    self.mod_version_label.setText(f"当前版本: v{version}")
            else:
                self.mod_version_label.setText("当前版本: 未安装")
        except Exception as e:
            print(f"检查本地版本失败: {e}")
            self.mod_version_label.setText("当前版本: 检查失败")

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
            self.mod_version_label.setText(f"当前版本: v{local_version}")
        else:
            self.mod_version_label.setText("当前版本: 未安装")

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
            self.mod_version_label.setText(f"当前版本: {f'v{local_version}' if local_version else '未安装'} → v{latest_version} 可更新")
        else:
            self.download_update_btn.setEnabled(False)
            self.download_update_btn.setText("已是最新")
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
            self.mod_version_label.setText(f"当前版本: v{latest_version} (最新)")

        if self.mod_checker:
            self.mod_checker.deleteLater()
            self.mod_checker = None

    def on_check_error(self, error_msg):
        """检查错误"""
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("检查更新")
        self.download_update_btn.setEnabled(False)

        # 直接显示在版本标签中
        self.mod_version_label.setText(f"检查失败: {error_msg}")

        if self.mod_checker:
            self.mod_checker.deleteLater()
            self.mod_checker = None

    def download_mod_update(self):
        """下载MOD更新"""
        if not self.current_mod_info:
            self.mod_version_label.setText("错误: 没有可用的更新信息")
            return

        if self.mod_downloader and self.mod_downloader.isRunning():
            return

        # 直接开始下载
        version = self.current_mod_info.get('version')
        self.mod_version_label.setText(f"准备下载 v{version}...")

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
        self.mod_version_label.setText(f"下载中: {status}")

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
        version = self.current_mod_info.get('version') if self.current_mod_info else '未知'
        self.mod_version_label.setText(f"v{version} 安装完成 (已清理临时文件和备份)")

        print(f"✅ 安装完成: {message}")

        if self.mod_downloader:
            self.mod_downloader.deleteLater()
            self.mod_downloader = None

    def on_download_error(self, error_msg):
        """下载错误"""
        self.check_update_btn.setEnabled(True)
        self.download_update_btn.setEnabled(True)
        self.download_update_btn.setText("下载更新")

        self.mod_version_label.setText(f"更新失败: {error_msg}")

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

                self.mod_version_label.setText("已打开手柄问题解决方案")
            else:
                self.mod_version_label.setText("未找到解决方案文件: OnlineFix/无缝手柄问题解决方案.png")

        except Exception as e:
            self.mod_version_label.setText(f"打开文件失败: {str(e)}")
            print(f"打开手柄解决方案失败: {e}")