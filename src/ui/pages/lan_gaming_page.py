"""
局域网配置页面
提供局域网联机配置和启动功能
"""
import os
import sys
import subprocess
import zipfile
import configparser
import time
import shutil
from pathlib import Path
from typing import Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGroupBox, QLineEdit,
                               QTextEdit, QFileDialog, QMessageBox, QProgressBar,
                               QGridLayout, QScrollArea, QSplitter)
from PySide6.QtCore import Qt, Signal, QProcess, QThread, QTimer
from .base_page import BasePage
from ...i18n.manager import TranslationManager, t


class ESLExtractWorker(QThread):
    """ESL解压工作线程"""
    progress_updated = Signal(int)  # 进度更新
    status_updated = Signal(str, str)  # 状态更新 (message, type)
    extraction_finished = Signal(bool)  # 解压完成 (success)

    def __init__(self, zip_path, extract_path):
        super().__init__()
        self.zip_path = zip_path
        self.extract_path = extract_path

    def run(self):
        """执行解压操作"""
        try:
            self.status_updated.emit(t("lan_gaming_page.status.esl_extracting"), "info")

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)

                for i, file_name in enumerate(file_list):
                    zip_ref.extract(file_name, self.extract_path)
                    progress = int((i + 1) / total_files * 100)
                    self.progress_updated.emit(progress)

                    # 添加小延迟让用户看到进度
                    self.msleep(10)

            self.status_updated.emit(t("lan_gaming_page.status.esl_extracted"), "success")
            self.extraction_finished.emit(True)

        except Exception as e:
            self.status_updated.emit(t("lan_gaming_page.error.extract_failed").format(error=e), "error")
            self.extraction_finished.emit(False)


class LanGamingPage(BasePage):
    """局域网配置页面"""

    def __init__(self, parent=None):
        super().__init__(t("lan_gaming_page.page_title"), parent)

        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境
            self.root_dir = Path(__file__).parent.parent.parent.parent

        # ESL相关路径
        self.steamclient_dir = self.root_dir / "ESL"
        self.steam_settings_dir = self.steamclient_dir / "steam_settings"
        self.config_file_path = self.steam_settings_dir / "configs.user.ini"

        # OnlineFix文件夹路径
        self.onlinefix_dir = self.root_dir / "OnlineFix"
        self.esl_zip_path = self.onlinefix_dir / "esl2.zip"

        # 解压完成标志文件
        self.esl_extracted_flag = self.steamclient_dir / ".esl_extracted"

        # ESL解压工作线程
        self.extract_worker = None

        self.setup_content()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

        # 显示初始化状态
        self.show_initialization_status()

        # 异步执行所有耗时的初始化操作
        QTimer.singleShot(50, self.async_initialize_page)

    def show_initialization_status(self):
        """显示初始化状态提示"""
        try:
            # 更新ESL状态显示
            self.update_esl_status(t("lan_gaming_page.status.esl_initializing"), "info")

        except Exception as e:
            print(f"显示初始化状态失败: {e}")

    def async_initialize_page(self):
        """异步初始化页面 - 使用QThread执行耗时操作"""
        try:
            # 创建初始化工作线程
            self.init_worker = LanGamingInitWorker(self)
            self.init_worker.progress_updated.connect(self.on_init_progress)
            self.init_worker.initialization_complete.connect(self.on_initialization_complete)
            self.init_worker.initialization_error.connect(self.on_initialization_error)

            # 启动工作线程
            self.init_worker.start()

        except Exception as e:
            print(f"启动异步初始化失败: {e}")
            self.update_esl_status(t("lan_gaming_page.error.init_failed").format(error=e), "error")

    def on_init_progress(self, message, msg_type):
        """初始化进度更新"""
        self.update_esl_status(message, msg_type)

    def setup_content(self):
        """设置页面内容 - 使用优化的网格布局"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #313244;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #585b70;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c7086;
            }
        """)

        # 创建主容器
        main_container = QFrame()
        main_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                margin: 5px;
            }
        """)

        # 使用网格布局替代垂直布局
        layout = QGridLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 第一行：ESL状态区域（跨两列）
        self.setup_esl_status_section_compact(layout, 0, 0, 1, 2)

        # 第二行：左列配置，右列启动
        self.setup_basic_config_compact(layout, 1, 0)
        self.setup_launch_section_compact(layout, 1, 1)

        # 第三行：说明区域（跨两列，但高度受限）
        self.setup_help_section_compact(layout, 2, 0, 1, 2)

        # 设置列的拉伸比例
        layout.setColumnStretch(0, 1)  # 左列
        layout.setColumnStretch(1, 1)  # 右列

        # 设置行的拉伸比例
        layout.setRowStretch(0, 0)  # ESL状态行 - 固定高度
        layout.setRowStretch(1, 1)  # 主要内容行 - 可拉伸
        layout.setRowStretch(2, 0)  # 说明行 - 固定高度

        main_container.setLayout(layout)
        scroll_area.setWidget(main_container)
        self.add_content(scroll_area)

    def setup_esl_status_section_compact(self, parent_layout, row, col, row_span, col_span):
        """设置ESL状态区域 - 紧凑版"""
        self.esl_status_group = QGroupBox(t("lan_gaming_page.section.esl_status"))
        self.esl_status_group.setMaximumHeight(120)  # 限制高度
        self.esl_status_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                background-color: #1e1e2e;
            }
        """)

        status_layout = QHBoxLayout()  # 改为水平布局
        status_layout.setSpacing(10)

        # ESL状态标签
        self.esl_status_label = QLabel(t("lan_gaming_page.label.esl_status_checking"))
        self.esl_status_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 13px;
                font-weight: bold;
                padding: 6px 10px;
                background-color: #313244;
                border-radius: 6px;
            }
        """)

        # 进度条（初始隐藏）
        self.esl_progress_bar = QProgressBar()
        self.esl_progress_bar.setVisible(False)
        self.esl_progress_bar.setMaximumHeight(25)
        self.esl_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #313244;
                border-radius: 6px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
        """)

        status_layout.addWidget(self.esl_status_label, 1)
        status_layout.addWidget(self.esl_progress_bar, 1)

        self.esl_status_group.setLayout(status_layout)
        parent_layout.addWidget(self.esl_status_group, row, col, row_span, col_span)

    def setup_basic_config_compact(self, parent_layout, row, col):
        """设置基础配置区域 - 紧凑版"""
        config_group = QGroupBox(t("lan_gaming_page.section.lan_config"))
        config_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                background-color: #1e1e2e;
            }
        """)

        config_layout = QVBoxLayout()
        config_layout.setSpacing(12)

        # Steam ID 配置 - 垂直布局节省空间
        steamid_container = QFrame()
        steamid_container.setStyleSheet("QFrame { border: none; }")
        steamid_vlayout = QVBoxLayout()
        steamid_vlayout.setSpacing(6)
        steamid_vlayout.setContentsMargins(0, 0, 0, 0)

        self.steamid_label = QLabel(t("lan_gaming_page.label.steamid"))
        self.steamid_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        steamid_hlayout = QHBoxLayout()
        steamid_hlayout.setSpacing(8)

        self.steamid_input = QLineEdit()
        self.steamid_input.setPlaceholderText(t("lan_gaming_page.placeholder.steamid"))
        self.steamid_input.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)

        # 定位存档按钮
        self.locate_save_btn = QPushButton("📁")
        self.locate_save_btn.setFixedSize(30, 30)
        self.locate_save_btn.setToolTip(t("lan_gaming_page.tooltip.locate_save"))
        self.locate_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
        """)
        self.locate_save_btn.clicked.connect(self.locate_save_folder)

        steamid_hlayout.addWidget(self.steamid_input, 1)
        steamid_hlayout.addWidget(self.locate_save_btn)

        steamid_vlayout.addWidget(self.steamid_label)
        steamid_vlayout.addLayout(steamid_hlayout)
        steamid_container.setLayout(steamid_vlayout)

        # 玩家名称配置 - 垂直布局
        name_container = QFrame()
        name_container.setStyleSheet("QFrame { border: none; }")
        name_vlayout = QVBoxLayout()
        name_vlayout.setSpacing(6)
        name_vlayout.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(t("lan_gaming_page.label.player_name"))
        self.name_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("lan_gaming_page.placeholder.player_name"))
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)

        name_vlayout.addWidget(self.name_label)
        name_vlayout.addWidget(self.name_input)
        name_container.setLayout(name_vlayout)

        # 保存配置按钮
        self.save_config_btn = QPushButton(t("lan_gaming_page.button.save_config"))
        self.save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
        """)
        self.save_config_btn.clicked.connect(self.save_config)

        config_layout.addWidget(steamid_container)
        config_layout.addWidget(name_container)
        config_layout.addWidget(self.save_config_btn)
        config_layout.addStretch()  # 添加弹性空间

        self.config_group = config_group
        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group, row, col)

    def setup_launch_section_compact(self, parent_layout, row, col):
        """设置启动区域 - 紧凑版"""
        self.launch_group = QGroupBox(t("lan_gaming_page.section.launch"))
        self.launch_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                background-color: #1e1e2e;
            }
        """)

        launch_layout = QVBoxLayout()
        launch_layout.setSpacing(12)

        # 状态显示
        self.status_label = QLabel(t("lan_gaming_page.label.status_ready"))
        self.status_label.setWordWrap(True)  # 允许文字换行
        self.status_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 8px;
                background-color: #313244;
                border-radius: 6px;
            }
        """)

        # 启动按钮
        self.launch_btn = QPushButton(t("lan_gaming_page.button.launch_lan"))
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_lan_mode)

        # 退出局域网模式按钮
        self.exit_lan_btn = QPushButton(t("lan_gaming_page.button.exit_lan"))
        self.exit_lan_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
        """)
        self.exit_lan_btn.clicked.connect(self.exit_lan_mode)
        self.exit_lan_btn.setVisible(False)  # 默认隐藏

        # DLL状态检查按钮
        self.check_dll_btn = QPushButton(t("lan_gaming_page.button.check_dll"))
        self.check_dll_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.check_dll_btn.clicked.connect(self.check_dll_status)
        self.check_dll_btn.setVisible(False)  # 默认隐藏，只在局域网模式下显示

        launch_layout.addWidget(self.status_label)
        launch_layout.addWidget(self.launch_btn)
        launch_layout.addWidget(self.exit_lan_btn)
        launch_layout.addWidget(self.check_dll_btn)
        launch_layout.addStretch()  # 添加弹性空间

        self.launch_group.setLayout(launch_layout)
        parent_layout.addWidget(self.launch_group, row, col)

    def setup_help_section_compact(self, parent_layout, row, col, row_span, col_span):
        """设置说明区域 - 紧凑版"""
        self.help_group = QGroupBox(t("lan_gaming_page.section.help"))
        self.help_group.setMaximumHeight(200)  # 限制高度
        self.help_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 15px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                background-color: #1e1e2e;
            }
        """)

        help_layout = QHBoxLayout()  # 改为水平布局
        help_layout.setSpacing(15)

        # 左侧：Steam ID获取方法
        left_text = QTextEdit()
        left_text.setReadOnly(True)
        left_text.setMaximumHeight(160)
        left_text.setStyleSheet("""
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 11px;
                line-height: 1.3;
            }
            QScrollBar:vertical {
                background-color: #45475a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #6c7086;
                border-radius: 4px;
            }
        """)

        left_content = f"""{t("lan_gaming_page.help.steamid_title")}

{t("lan_gaming_page.help.steamid_method_1")}
{t("lan_gaming_page.help.steamid_method_1_example")}
{t("lan_gaming_page.help.steamid_method_1_note")}

{t("lan_gaming_page.help.steamid_method_2")}
{t("lan_gaming_page.help.steamid_method_2_example")}
{t("lan_gaming_page.help.steamid_method_2_note")}

{t("lan_gaming_page.help.steamid_method_3")}"""

        left_text.setPlainText(left_content)

        # 保存组件引用用于语言切换
        self.help_left_text = left_text

        # 右侧：使用步骤
        right_text = QTextEdit()
        right_text.setReadOnly(True)
        right_text.setMaximumHeight(160)
        right_text.setStyleSheet("""
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 11px;
                line-height: 1.3;
            }
            QScrollBar:vertical {
                background-color: #45475a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #6c7086;
                border-radius: 4px;
            }
        """)

        right_content = f"""{t("lan_gaming_page.help.usage_title")}

{t("lan_gaming_page.help.usage_step_1")}
{t("lan_gaming_page.help.usage_step_2")}
{t("lan_gaming_page.help.usage_step_3")}
{t("lan_gaming_page.help.usage_step_4")}
{t("lan_gaming_page.help.usage_step_5")}

{t("lan_gaming_page.help.notes_title")}
{t("lan_gaming_page.help.notes_1")}
{t("lan_gaming_page.help.notes_2")}
{t("lan_gaming_page.help.notes_3")}"""

        right_text.setPlainText(right_content)

        # 保存组件引用用于语言切换
        self.help_right_text = right_text

        help_layout.addWidget(left_text, 1)
        help_layout.addWidget(right_text, 1)

        self.help_group.setLayout(help_layout)
        parent_layout.addWidget(self.help_group, row, col, row_span, col_span)

    def initialize_esl_sync(self):
        """同步初始化ESL工具 - 在后台线程中执行"""
        try:
            # 1. 检查是否已有解压完成标志
            if self.esl_extracted_flag.exists() and self.validate_esl_structure():
                return {
                    'status': 'success',
                    'message': t("lan_gaming_page.status.esl_ready"),
                    'ready': True,
                    'need_extract': False
                }

            # 2. 检查OnlineFix文件夹中的esl2.zip
            if self.esl_zip_path.exists():
                return {
                    'status': 'need_extract',
                    'message': t("lan_gaming_page.status.esl_found_zip"),
                    'ready': False,
                    'need_extract': True,
                    'zip_path': str(self.esl_zip_path)
                }

            # 3. 检查ESL文件夹中是否有旧的esl2.zip（向后兼容）
            old_esl_zip = self.steamclient_dir / "esl2.zip"
            if old_esl_zip.exists():
                # 迁移到OnlineFix文件夹
                self.onlinefix_dir.mkdir(exist_ok=True)
                if self.esl_zip_path.exists():
                    self.esl_zip_path.unlink()
                shutil.move(str(old_esl_zip), str(self.esl_zip_path))
                print(f"✅ ESL压缩包已迁移到OnlineFix文件夹")

                return {
                    'status': 'need_extract',
                    'message': t("lan_gaming_page.status.esl_migrated"),
                    'ready': False,
                    'need_extract': True,
                    'zip_path': str(self.esl_zip_path)
                }

            # 4. 都不存在，错误状态
            return {
                'status': 'error',
                'message': t("lan_gaming_page.error.esl_missing"),
                'ready': False,
                'need_extract': False
            }

        except Exception as e:
            print(f"ESL初始化失败: {e}")
            return {
                'status': 'error',
                'message': t("lan_gaming_page.error.init_failed").format(error=e),
                'ready': False,
                'need_extract': False,
                'error': str(e)
            }

    def initialize_esl(self):
        """初始化ESL工具 - 保持向后兼容"""
        result = self.initialize_esl_sync()
        self.update_esl_initialization_ui(result)
        return result.get('ready', False)



    def validate_esl_structure(self):
        """验证ESL文件结构完整性（增强版本）"""
        try:
            # 定义必需的文件和目录（基于实际ESL结构）
            required_items = {
                "steamclient_loader.exe": {
                    "path": self.steamclient_dir / "steamclient_loader.exe",
                    "type": "file",
                    "check_pe": True
                },
                "steam_settings目录": {
                    "path": self.steam_settings_dir,
                    "type": "directory",
                    "check_pe": False
                },
                "steamclient64.dll": {
                    "path": self.steamclient_dir / "steamclient64.dll",
                    "type": "file",
                    "check_pe": True
                },
                "unsteam64.dll": {
                    "path": self.steamclient_dir / "unsteam64.dll",
                    "type": "file",
                    "check_pe": True
                },
                "steam_api64.dll": {
                    "path": self.steamclient_dir / "steam_api64.dll",
                    "type": "file",
                    "check_pe": True
                }
            }

            all_valid = True

            for item_name, item_info in required_items.items():
                path = item_info["path"]
                item_type = item_info["type"]
                check_pe = item_info["check_pe"]

                if not path.exists():
                    print(f"⚠️ ESL缺失项目: {item_name}")
                    all_valid = False
                    continue

                if item_type == "file":
                    # 检查文件大小
                    try:
                        file_size = path.stat().st_size
                        if file_size == 0:
                            print(f"⚠️ ESL文件大小为0: {item_name}")
                            all_valid = False
                            continue

                        # 检查PE头（对于exe和dll文件）
                        if check_pe:
                            with open(path, 'rb') as f:
                                header = f.read(1024)
                                if not header.startswith(b'MZ'):
                                    print(f"⚠️ ESL文件PE头损坏: {item_name}")
                                    all_valid = False
                                    continue

                    except Exception as e:
                        print(f"⚠️ 检查ESL文件时出错 {item_name}: {e}")
                        all_valid = False
                        continue

                elif item_type == "directory":
                    if not path.is_dir():
                        print(f"⚠️ ESL目录无效: {item_name}")
                        all_valid = False
                        continue

            return all_valid

        except Exception as e:
            print(f"验证ESL结构失败: {e}")
            return False

    def get_esl_integrity_report(self) -> Dict[str, Dict]:
        """获取ESL详细完整性报告"""
        required_items = {
            "steamclient_loader.exe": {
                "path": self.steamclient_dir / "steamclient_loader.exe",
                "type": "file",
                "check_pe": True,
                "description": "ESL主程序"
            },
            "steam_settings目录": {
                "path": self.steam_settings_dir,
                "type": "directory",
                "check_pe": False,
                "description": "Steam设置目录"
            },
            "steamclient64.dll": {
                "path": self.steamclient_dir / "steamclient64.dll",
                "type": "file",
                "check_pe": True,
                "description": "Steam客户端库"
            },
            "unsteam64.dll": {
                "path": self.steamclient_dir / "unsteam64.dll",
                "type": "file",
                "check_pe": True,
                "description": "Unsteam核心库"
            },
            "steam_api64.dll": {
                "path": self.steamclient_dir / "steam_api64.dll",
                "type": "file",
                "check_pe": True,
                "description": "Steam API库"
            }
        }

        detailed_report = {}

        for item_name, item_info in required_items.items():
            path = item_info["path"]
            item_type = item_info["type"]
            check_pe = item_info["check_pe"]
            description = item_info["description"]

            report = {
                "description": description,
                "type": item_type,
                "exists": False,
                "size": 0,
                "readable": False,
                "valid_format": False,
                "status": "missing"
            }

            try:
                if path.exists():
                    report["exists"] = True

                    if item_type == "file":
                        # 检查文件
                        if path.is_file():
                            file_size = path.stat().st_size
                            report["size"] = file_size

                            if file_size > 0:
                                try:
                                    with open(path, 'rb') as f:
                                        header = f.read(1024)
                                        if len(header) > 0:
                                            report["readable"] = True

                                            if check_pe:
                                                if header.startswith(b'MZ'):
                                                    report["valid_format"] = True
                                                    report["status"] = "healthy"
                                                else:
                                                    report["status"] = "corrupted"
                                            else:
                                                report["valid_format"] = True
                                                report["status"] = "healthy"
                                        else:
                                            report["status"] = "empty_content"
                                except Exception as e:
                                    report["status"] = f"read_error: {str(e)}"
                            else:
                                report["status"] = "zero_size"
                        else:
                            report["status"] = "not_file"

                    elif item_type == "directory":
                        if path.is_dir():
                            report["status"] = "healthy"
                            report["valid_format"] = True
                        else:
                            report["status"] = "not_directory"
                else:
                    report["status"] = "missing"

            except Exception as e:
                report["status"] = f"check_error: {str(e)}"

            detailed_report[item_name] = report

        return detailed_report

    def print_esl_integrity_report(self):
        """打印ESL详细完整性报告"""
        print("📋 ESL完整性详细报告:")
        print("=" * 60)

        detailed_report = self.get_esl_integrity_report()

        for item_name, report in detailed_report.items():
            status_icon = {
                "healthy": "✅",
                "missing": "❌",
                "corrupted": "⚠️",
                "zero_size": "⚠️",
                "empty_content": "⚠️",
                "not_file": "⚠️",
                "not_directory": "⚠️"
            }.get(report["status"], "❓")

            print(f"{status_icon} {item_name}")
            print(f"   描述: {report['description']}")
            print(f"   类型: {report['type']}")
            print(f"   状态: {report['status']}")
            if report['type'] == 'file':
                print(f"   大小: {report['size']} 字节")
                print(f"   可读: {report['readable']}")
                print(f"   格式: {report['valid_format']}")
            print(f"   存在: {report['exists']}")
            print()

    def extract_esl_package(self):
        """解压ESL压缩包"""
        try:
            if self.extract_worker and self.extract_worker.isRunning():
                return

            # 显示进度条
            self.esl_progress_bar.setVisible(True)
            self.esl_progress_bar.setValue(0)

            # 创建解压工作线程
            self.extract_worker = ESLExtractWorker(
                str(self.esl_zip_path),
                str(self.steamclient_dir.parent)
            )

            # 连接信号
            self.extract_worker.progress_updated.connect(self.on_extract_progress)
            self.extract_worker.status_updated.connect(self.update_esl_status)
            self.extract_worker.extraction_finished.connect(self.on_extract_finished)

            # 启动解压
            self.extract_worker.start()

        except Exception as e:
            print(f"启动ESL解压失败: {e}")
            self.update_esl_status(f"❌ 解压启动失败: {e}", "error")

    def on_extract_progress(self, progress):
        """解压进度更新"""
        self.esl_progress_bar.setValue(progress)

    def on_extract_finished(self, success):
        """解压完成处理"""
        try:
            self.esl_progress_bar.setVisible(False)

            if success:
                # 验证解压结果
                if self.validate_esl_structure():
                    # 创建解压完成标志文件
                    try:
                        import time
                        self.esl_extracted_flag.write_text(f"ESL extracted at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        print("✅ 已创建ESL解压完成标志")
                    except Exception as e:
                        print(f"创建解压标志失败: {e}")

                    self.update_esl_status(t("lan_gaming_page.status.esl_complete"), "success")

                    # 压缩包已经在OnlineFix文件夹中，无需移动
                    print("📦 ESL压缩包保留在OnlineFix文件夹")

                    # 加载配置
                    self.load_current_settings()
                else:
                    self.update_esl_status(t("lan_gaming_page.status.esl_incomplete"), "error")
            else:
                self.update_esl_status(t("lan_gaming_page.error.extract_failed").format(error=""), "error")

        except Exception as e:
            print(f"解压完成处理失败: {e}")
            self.update_esl_status(t("lan_gaming_page.error.init_failed").format(error=e), "error")

    def update_esl_status(self, message, status_type="info"):
        """更新ESL状态显示"""
        color_map = {
            "success": "#a6e3a1",
            "error": "#f38ba8",
            "warning": "#f9e2af",
            "info": "#89b4fa"
        }

        color = color_map.get(status_type, "#cdd6f4")

        self.esl_status_label.setText(message)
        self.esl_status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #313244;
                border-radius: 6px;
            }}
        """)

    def load_current_settings(self):
        """加载当前配置"""
        try:
            if not self.config_file_path.exists():
                print("配置文件不存在，使用默认值")
                return

            # 读取INI配置文件
            config_data = self.parse_ini_config()

            if config_data:
                # 加载Steam ID
                steamid = config_data.get('account_steamid', '')
                if steamid:
                    self.steamid_input.setText(steamid)

                # 加载玩家名称
                account_name = config_data.get('account_name', '')
                if account_name:
                    self.name_input.setText(account_name)

                print(f"✅ 配置加载成功: Steam ID={steamid}, 玩家名称={account_name}")
            else:
                print("⚠️ 配置文件解析失败，使用默认值")

        except Exception as e:
            print(f"加载配置失败: {e}")
            self.update_status(f"加载配置失败: {e}", "error")

    def parse_ini_config(self):
        """解析INI配置文件"""
        try:
            config_data = {}

            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 手动解析INI文件（保持注释）
            in_user_section = False
            for line in lines:
                line = line.strip()

                # 检查是否进入[user::general]段
                if line == '[user::general]':
                    in_user_section = True
                    continue
                elif line.startswith('[') and line.endswith(']'):
                    in_user_section = False
                    continue

                # 解析配置项
                if in_user_section and '=' in line and not line.startswith('//'):
                    key, value = line.split('=', 1)
                    config_data[key.strip()] = value.strip()

            return config_data

        except Exception as e:
            print(f"解析INI配置失败: {e}")
            return None

    def save_config(self):
        """保存配置"""
        try:
            steamid = self.steamid_input.text().strip()
            name = self.name_input.text().strip()

            # 验证Steam ID
            if not steamid:
                self.update_status(t("lan_gaming_page.error.steamid_required"), "error")
                return

            if not steamid.startswith('76') or len(steamid) != 17 or not steamid.isdigit():
                self.update_status(t("lan_gaming_page.error.steamid_invalid"), "error")
                return

            # 验证玩家名称
            if not name:
                self.update_status(t("lan_gaming_page.error.name_required"), "error")
                return

            # 确保目录存在
            self.steam_settings_dir.mkdir(parents=True, exist_ok=True)

            # 更新INI配置文件
            success = self.update_ini_config(steamid, name)

            if success:
                self.update_status(t("lan_gaming_page.status.config_saved"), "success")
                print(f"✅ 配置已保存: Steam ID={steamid}, 玩家名称={name}")
            else:
                self.update_status(t("lan_gaming_page.status.config_save_failed"), "error")

        except Exception as e:
            print(f"保存配置失败: {e}")
            self.update_status(t("lan_gaming_page.status.config_load_failed").format(error=e), "error")

    def update_ini_config(self, steamid, account_name):
        """更新INI配置文件"""
        try:
            # 如果配置文件不存在，创建默认配置
            if not self.config_file_path.exists():
                self.create_default_config(steamid, account_name)
                return True

            # 读取现有配置文件
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 更新配置项
            updated_lines = []
            in_user_section = False
            steamid_updated = False
            name_updated = False

            for line in lines:
                original_line = line
                stripped_line = line.strip()

                # 检查是否进入[user::general]段
                if stripped_line == '[user::general]':
                    in_user_section = True
                    updated_lines.append(original_line)
                    continue
                elif stripped_line.startswith('[') and stripped_line.endswith(']'):
                    in_user_section = False
                    updated_lines.append(original_line)
                    continue

                # 更新配置项
                if in_user_section and '=' in stripped_line and not stripped_line.startswith('//'):
                    key, value = stripped_line.split('=', 1)
                    key = key.strip()

                    if key == 'account_steamid':
                        updated_lines.append(f"account_steamid={steamid}\n")
                        steamid_updated = True
                    elif key == 'account_name':
                        updated_lines.append(f"account_name={account_name}\n")
                        name_updated = True
                    else:
                        updated_lines.append(original_line)
                else:
                    updated_lines.append(original_line)

            # 如果某些配置项没有找到，添加到[user::general]段末尾
            if in_user_section and (not steamid_updated or not name_updated):
                if not steamid_updated:
                    updated_lines.append(f"account_steamid={steamid}\n")
                if not name_updated:
                    updated_lines.append(f"account_name={account_name}\n")

            # 写回文件
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)

            return True

        except Exception as e:
            print(f"更新INI配置失败: {e}")
            return False

    def create_default_config(self, steamid, account_name):
        """创建默认配置文件"""
        try:
            default_config = f"""[user::general]
//下面的用户名随意更改 因为游戏显示的是你创建的角色名称
account_name={account_name}
//将下方的ID改成你steam的76开头的ID(或者自行修改数字保证唯一性)
account_steamid={steamid}
language=schinese
ip_country=CN
"""

            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                f.write(default_config)

            print("✅ 已创建默认配置文件")
            return True

        except Exception as e:
            print(f"创建默认配置失败: {e}")
            return False

    def locate_save_folder(self):
        """定位存档文件夹"""
        try:
            # 获取用户目录
            user_dir = Path.home()
            nightreign_dir = user_dir / "AppData" / "Roaming" / "Nightreign"

            if nightreign_dir.exists():
                # 打开存档文件夹
                os.startfile(str(nightreign_dir))
                self.update_status(t("lan_gaming_page.status.save_folder_opened"), "info")
            else:
                self.update_status(t("lan_gaming_page.status.save_folder_not_found"), "warning")

        except Exception as e:
            print(f"定位存档文件夹失败: {e}")
            self.update_status(t("lan_gaming_page.status.save_folder_locate_failed").format(error=e), "error")

    def check_coldclient_config(self):
        """检查ColdClientLoader.ini配置"""
        try:
            config_file = self.steamclient_dir / "ColdClientLoader.ini"
            if not config_file.exists():
                return False, "ColdClientLoader.ini文件不存在"

            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查Exe配置是否正确
            if "Exe=..\\Nmodm.exe" not in content and "Exe=../Nmodm.exe" not in content:
                return False, "ColdClientLoader.ini中Exe配置不正确"

            return True, "配置检查通过"

        except Exception as e:
            return False, f"检查配置失败: {e}"

    def launch_lan_mode(self):
        """启动局域网联机模式"""
        try:
            # 检查ESL工具是否就绪
            if not self.validate_esl_structure():
                self.update_status(t("lan_gaming_page.error.esl_not_ready"), "error")
                return

            # 检查配置文件
            is_valid, message = self.check_coldclient_config()
            if not is_valid:
                self.update_status(message, "error")
                return

            # 检查steamclient_loader.exe是否存在
            loader_exe = self.steamclient_dir / "steamclient_loader.exe"
            if not loader_exe.exists():
                self.update_status(t("lan_gaming_page.error.steamclient_loader_not_exist"), "error")
                return

            # 检查配置是否已保存
            steamid = self.steamid_input.text().strip()
            name = self.name_input.text().strip()

            if not steamid or not name:
                self.update_status(t("lan_gaming_page.error.save_config_first"), "warning")
                return

            # 验证配置文件是否存在且正确
            if not self.config_file_path.exists():
                self.update_status(t("lan_gaming_page.error.config_not_exist"), "warning")
                return

            self.update_status(t("lan_gaming_page.status.launching"), "info")

            # 设置局域网模式状态（在启动前）
            self._set_lan_mode_status(True)

            # 启动steamclient_loader.exe
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen([str(loader_exe)], cwd=str(self.steamclient_dir), creationflags=creation_flags)

            # 提示用户并延迟关闭窗口
            self.update_status(t("lan_gaming_page.status.launch_success"), "success")

            # 延迟关闭当前窗口，给用户时间看到提示
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._close_current_window)

        except Exception as e:
            print(f"启动局域网联机模式失败: {e}")
            self.update_status(t("lan_gaming_page.status.launch_failed").format(error=e), "error")
            # 启动失败时重置状态
            self._set_lan_mode_status(False)

    def _set_lan_mode_status(self, active: bool):
        """设置局域网模式状态"""
        try:
            from src.utils.lan_mode_detector import get_lan_mode_detector
            detector = get_lan_mode_detector()
            detector.set_lan_mode(active)
        except Exception as e:
            print(f"设置局域网模式状态失败: {e}")

    def _close_current_window(self):
        """关闭当前窗口"""
        try:
            # 获取主窗口并关闭
            main_window = self.window()
            if main_window:
                print("🚪 局域网联机模式启动，关闭当前窗口...")

                # 设置特殊标志，允许在局域网模式下关闭窗口
                main_window._lan_mode_restart = True

                main_window.close()
        except Exception as e:
            print(f"关闭窗口失败: {e}")

    def check_and_update_lan_mode_sync(self):
        """同步检测局域网模式 - 在后台线程中执行"""
        try:
            from src.utils.lan_mode_detector import get_lan_mode_detector
            detector = get_lan_mode_detector()

            return {
                'status': 'success',
                'is_lan_mode': detector.is_lan_mode
            }

        except Exception as e:
            print(f"检测局域网模式失败: {e}")
            return {
                'status': 'error',
                'is_lan_mode': False,
                'error': str(e)
            }

    def check_and_update_lan_mode(self):
        """检测局域网模式并更新UI - 保持向后兼容"""
        result = self.check_and_update_lan_mode_sync()
        self.update_lan_mode_ui(result)

    def on_initialization_complete(self, esl_result, lan_mode_result):
        """初始化完成处理"""
        try:
            # 更新ESL状态UI
            self.update_esl_initialization_ui(esl_result)

            # 更新局域网模式UI
            self.update_lan_mode_ui(lan_mode_result)

            # 如果ESL已就绪，加载当前设置
            if esl_result.get('ready', False):
                self.load_current_settings()

            # 如果需要解压，启动解压过程
            if esl_result.get('need_extract', False):
                self.extract_esl_package()

            print("✅ 局域网配置页面初始化完成")

        except Exception as e:
            print(f"初始化完成处理失败: {e}")

    def on_initialization_error(self, error_msg):
        """初始化错误处理"""
        try:
            self.update_esl_status(f"❌ 页面初始化失败: {error_msg}", "error")
        except Exception as e:
            print(f"初始化错误处理失败: {e}")

    def update_esl_initialization_ui(self, result):
        """更新ESL初始化UI"""
        try:
            status = result.get('status', 'error')
            message = result.get('message', '未知状态')

            if status == 'success':
                self.update_esl_status(message, "success")
            elif status == 'need_extract':
                self.update_esl_status(message, "info")
            else:
                self.update_esl_status(message, "error")

        except Exception as e:
            print(f"更新ESL初始化UI失败: {e}")

    def update_lan_mode_ui(self, result):
        """更新局域网模式UI"""
        try:
            if result.get('status') == 'success':
                is_lan_mode = result.get('is_lan_mode', False)

                if is_lan_mode:
                    # 当前处于局域网模式
                    self.update_ui_for_lan_mode(True)
                    self.update_status(t("lan_gaming_page.status.in_lan_mode"), "success")
                else:
                    # 当前处于正常模式
                    self.update_ui_for_lan_mode(False)
            else:
                error_msg = result.get('error', '未知错误')
                print(f"局域网模式检测失败: {error_msg}")

        except Exception as e:
            print(f"更新局域网模式UI失败: {e}")

    def update_ui_for_lan_mode(self, is_lan_mode: bool):
        """根据局域网模式更新UI"""
        if is_lan_mode:
            # 局域网模式：隐藏启动按钮，显示退出按钮和DLL检查按钮
            self.launch_btn.setVisible(False)
            self.exit_lan_btn.setVisible(True)
            self.check_dll_btn.setVisible(True)

            # 更新组标题
            if hasattr(self, 'launch_group'):
                self.launch_group.setTitle(t("lan_gaming_page.section.launch_in_lan"))
        else:
            # 正常模式：显示启动按钮，隐藏退出按钮和DLL检查按钮
            self.launch_btn.setVisible(True)
            self.exit_lan_btn.setVisible(False)
            self.check_dll_btn.setVisible(False)

            # 更新组标题
            if hasattr(self, 'launch_group'):
                self.launch_group.setTitle(t("lan_gaming_page.section.launch"))

    def exit_lan_mode(self):
        """退出局域网联机模式"""
        try:
            print("🚪 用户请求退出局域网联机模式")
            print("⚠️ 安全提示: 由于DLL注入，Steam和Nmodm需要重启以确保系统安全")
            self.update_status(t("lan_gaming_page.status.exiting_lan"), "info")

            # 执行安全退出流程
            self._perform_safe_exit()

        except Exception as e:
            print(f"退出局域网联机模式失败: {e}")
            self.update_status(t("lan_gaming_page.status.exit_failed").format(error=e), "error")

    def _perform_safe_exit(self):
        """执行安全退出流程"""
        try:
            from PySide6.QtCore import QTimer
            from src.utils.dll_manager import get_dll_manager

            # 获取DLL管理器
            dll_manager = get_dll_manager()

            # 显示安全提示
            print("🛡️ 安全退出流程说明:")
            print("1. 卸载steamclient DLL")
            print("2. 重启Steam程序")
            print("3. 清理状态文件")
            print("4. 重启Nmodm程序")
            print("此流程确保DLL注入完全清除，保证系统安全")

            # 步骤1: 显示安全提示
            self.update_status(t("lan_gaming_page.status.exit_step_1"), "info")

            # 延迟执行安全退出步骤
            QTimer.singleShot(1000, lambda: self._safe_exit_step_1(dll_manager))

        except Exception as e:
            print(f"安全退出流程失败: {e}")
            self.update_status(t("lan_gaming_page.status.exit_failed").format(error=e), "error")

    def _safe_exit_step_1(self, dll_manager):
        """安全退出步骤1: 卸载DLL"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status(t("lan_gaming_page.status.exit_step_2"), "info")
            print("🔄 正在卸载steamclient DLL以确保安全...")

            # 卸载DLL
            dll_success = dll_manager.force_unload_steamclient()

            if dll_success:
                print("✅ DLL卸载成功，系统安全性已恢复")
            else:
                print("⚠️ DLL卸载部分成功，重启将完全清除")

            # 继续下一步
            QTimer.singleShot(1500, lambda: self._safe_exit_step_2(dll_manager))

        except Exception as e:
            print(f"DLL卸载失败: {e}")
            self.update_status(t("lan_gaming_page.status.dll_unload_failed").format(error=e), "error")

    def _safe_exit_step_2(self, dll_manager):
        """安全退出步骤2: 重启Steam"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status(t("lan_gaming_page.status.exit_step_3"), "info")
            print("🔄 正在重启Steam以清除DLL注入...")

            # 重启Steam进程
            process_success = dll_manager.restart_steam_processes()

            if process_success:
                print("✅ Steam重启成功，DLL注入已清除")
            else:
                print("⚠️ Steam重启部分成功，建议手动重启Steam")

            # 继续下一步
            QTimer.singleShot(2000, lambda: self._safe_exit_step_3())

        except Exception as e:
            print(f"Steam重启失败: {e}")
            self.update_status(t("lan_gaming_page.status.steam_restart_failed").format(error=e), "error")

    def _safe_exit_step_3(self):
        """安全退出步骤3: 清理状态文件"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status(t("lan_gaming_page.status.exit_step_4"), "info")
            print("🧹 正在清理局域网模式状态文件...")

            # 清理局域网模式状态
            self._set_lan_mode_status(False)

            print("✅ 状态文件清理成功，下次启动将恢复正常模式")

            # 最后一步：重启Nmodm
            QTimer.singleShot(1000, self._safe_exit_final)

        except Exception as e:
            print(f"状态文件清理失败: {e}")
            self.update_status(t("lan_gaming_page.status.state_clean_failed").format(error=e), "error")

    def _safe_exit_final(self):
        """安全退出最后步骤：重启Nmodm"""
        try:
            from src.utils.dll_manager import get_dll_manager

            self.update_status(t("lan_gaming_page.status.exit_complete"), "success")
            print("🔄 正在重启Nmodm以确保完全清除DLL注入...")

            # 获取DLL管理器并重启应用程序
            dll_manager = get_dll_manager()
            restart_success = dll_manager.restart_nmodm_application()

            if restart_success:
                print("✅ 新的Nmodm实例已启动")
                print("🛡️ 安全退出完成，系统已恢复到安全状态")
                print("📋 新实例将自动恢复正常模式")

                # 立即关闭当前程序，因为新实例已经启动
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self._close_application)
            else:
                print("⚠️ Nmodm重启失败，请手动重启程序")
                # 重启失败时延迟关闭，给用户时间看到错误信息
                from PySide6.QtCore import QTimer
                QTimer.singleShot(3000, self._close_application)

        except Exception as e:
            print(f"安全退出失败: {e}")
            self.update_status(f"安全退出失败: {e}", "error")
            # 如果重启失败，仍然关闭当前程序
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._close_application)

    def check_dll_status(self):
        """检查DLL状态"""
        try:
            from src.utils.dll_manager import get_dll_manager

            self.update_status(t("lan_gaming_page.status.checking_dll"), "info")

            dll_manager = get_dll_manager()
            status = dll_manager.get_cleanup_status()

            # 输出状态报告到控制台
            print("🔍 DLL状态检查报告")
            print("=" * 50)

            # DLL加载状态
            print("📋 DLL加载状态:")
            if status['steamclient_dll_loaded']:
                print("  ✅ steamclient.dll: 已加载")
            else:
                print("  ❌ steamclient.dll: 未加载")

            if status['steamclient64_dll_loaded']:
                print("  ✅ steamclient64.dll: 已加载")
            else:
                print("  ❌ steamclient64.dll: 未加载")

            # 加载的DLL列表
            if status['loaded_steamclient_dlls']:
                print(f"\n📁 已加载的steamclient DLL ({len(status['loaded_steamclient_dlls'])}个):")
                for dll_path in status['loaded_steamclient_dlls']:
                    print(f"  • {dll_path}")
            else:
                print("\n✅ 未发现已加载的steamclient DLL")

            # Steam进程
            if status['steam_processes']:
                print(f"\n🔄 Steam相关进程 ({len(status['steam_processes'])}个):")
                for proc in status['steam_processes']:
                    print(f"  • {proc['name']} (PID: {proc['pid']})")
            else:
                print("\n✅ 未发现Steam相关进程")

            print("=" * 50)

            # 更新状态
            if status['steamclient_dll_loaded'] or status['steamclient64_dll_loaded']:
                self.update_status(t("lan_gaming_page.status.dll_loaded"), "success")
            else:
                self.update_status(t("lan_gaming_page.status.dll_not_loaded"), "info")

        except Exception as e:
            print(f"检查DLL状态失败: {e}")
            self.update_status(t("lan_gaming_page.status.dll_check_failed").format(error=e), "error")

    def _close_application(self):
        """关闭整个应用程序"""
        try:
            # 获取主窗口并关闭
            main_window = self.window()
            if main_window:
                print("🚪 退出局域网联机模式，关闭应用程序...")
                main_window.close()
        except Exception as e:
            print(f"关闭应用程序失败: {e}")

    def update_status(self, message, status_type="info"):
        """更新状态显示"""
        color_map = {
            "success": "#a6e3a1",
            "error": "#f38ba8",
            "warning": "#f9e2af",
            "info": "#89b4fa"
        }

        color = color_map.get(status_type, "#cdd6f4")

        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #313244;
                border-radius: 6px;
            }}
        """)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        try:
            # 更新页面标题
            if hasattr(self, 'title_label'):
                self.title_label.setText(t("lan_gaming_page.page_title"))

            # 更新区域标题
            if hasattr(self, 'esl_status_group'):
                self.esl_status_group.setTitle(t("lan_gaming_page.section.esl_status"))
            if hasattr(self, 'config_group'):
                self.config_group.setTitle(t("lan_gaming_page.section.lan_config"))
            if hasattr(self, 'help_group'):
                self.help_group.setTitle(t("lan_gaming_page.section.help"))

            # 更新启动区域标题（根据当前模式）
            if hasattr(self, 'launch_group'):
                from src.utils.lan_mode_detector import get_lan_mode_detector
                detector = get_lan_mode_detector()
                is_lan_mode = detector.is_lan_mode

                if is_lan_mode:
                    self.launch_group.setTitle(t("lan_gaming_page.section.launch_in_lan"))
                else:
                    self.launch_group.setTitle(t("lan_gaming_page.section.launch"))

            # 更新按钮文本
            if hasattr(self, 'save_config_btn'):
                self.save_config_btn.setText(t("lan_gaming_page.button.save_config"))
            if hasattr(self, 'launch_btn'):
                self.launch_btn.setText(t("lan_gaming_page.button.launch_lan"))
            if hasattr(self, 'exit_lan_btn'):
                self.exit_lan_btn.setText(t("lan_gaming_page.button.exit_lan"))
            if hasattr(self, 'check_dll_btn'):
                self.check_dll_btn.setText(t("lan_gaming_page.button.check_dll"))

            # 更新标签文本
            if hasattr(self, 'steamid_label'):
                self.steamid_label.setText(t("lan_gaming_page.label.steamid"))
            if hasattr(self, 'name_label'):
                self.name_label.setText(t("lan_gaming_page.label.player_name"))

            # 更新占位符文本
            if hasattr(self, 'steamid_input'):
                self.steamid_input.setPlaceholderText(t("lan_gaming_page.placeholder.steamid"))
            if hasattr(self, 'name_input'):
                self.name_input.setPlaceholderText(t("lan_gaming_page.placeholder.player_name"))

            # 更新工具提示
            if hasattr(self, 'locate_save_btn'):
                self.locate_save_btn.setToolTip(t("lan_gaming_page.tooltip.locate_save"))

            # 更新ESL状态标签（动态文本）
            if hasattr(self, 'esl_status_label'):
                current_text = self.esl_status_label.text()

                # 判断当前状态并重新生成文本
                if "正在检查" in current_text or "Checking" in current_text:
                    self.esl_status_label.setText(t("lan_gaming_page.label.esl_status_checking"))
                elif "已就绪" in current_text or "ready" in current_text.lower():
                    self.esl_status_label.setText(t("lan_gaming_page.status.esl_ready"))
                elif "缺失" in current_text or "missing" in current_text.lower():
                    self.esl_status_label.setText(t("lan_gaming_page.error.esl_missing"))
                elif "初始化完成" in current_text or "initialized" in current_text.lower():
                    self.esl_status_label.setText(t("lan_gaming_page.status.esl_complete"))
                elif "解压不完整" in current_text or "incomplete" in current_text.lower():
                    self.esl_status_label.setText(t("lan_gaming_page.status.esl_incomplete"))
                elif "正在初始化" in current_text or "Initializing" in current_text:
                    self.esl_status_label.setText(t("lan_gaming_page.status.esl_initializing"))

            # 更新启动状态标签（动态文本）
            if hasattr(self, 'status_label'):
                current_text = self.status_label.text()

                # 判断当前状态并重新生成文本
                if "准备就绪" in current_text or "Ready" in current_text:
                    self.status_label.setText(t("lan_gaming_page.label.status_ready"))
                elif "当前处于局域网联机模式" in current_text or "Currently in LAN mode" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.in_lan_mode"))
                elif "配置保存成功" in current_text or "Config saved" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.config_saved"))
                elif "配置保存失败" in current_text or "Failed to save config" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.config_save_failed"))
                elif "已打开存档文件夹" in current_text or "Save folder opened" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.save_folder_opened"))
                elif "未找到存档文件夹" in current_text or "Save folder not found" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.save_folder_not_found"))
                elif "正在启动局域网联机模式" in current_text or "Launching LAN mode" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.launching"))
                elif "局域网联机模式启动中" in current_text or "LAN mode launching" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.launch_success"))
                elif "正在安全退出" in current_text or "Safely exiting" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exiting_lan"))
                elif "步骤1/4" in current_text or "Step 1/4" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exit_step_1"))
                elif "步骤2/4" in current_text or "Step 2/4" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exit_step_2"))
                elif "步骤3/4" in current_text or "Step 3/4" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exit_step_3"))
                elif "步骤4/4" in current_text or "Step 4/4" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exit_step_4"))
                elif "安全退出完成" in current_text or "Safe exit complete" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.exit_complete"))
                elif "正在检查DLL状态" in current_text or "Checking DLL" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.checking_dll"))
                elif "检测到steamclient DLL已加载" in current_text or "Detected steamclient DLL loaded" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.dll_loaded"))
                elif "未检测到steamclient DLL" in current_text or "No steamclient DLL detected" in current_text:
                    self.status_label.setText(t("lan_gaming_page.status.dll_not_loaded"))
                # 错误消息
                elif "请输入Steam ID" in current_text or "Please enter Steam ID" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.steamid_required"))
                elif "Steam ID格式错误" in current_text or "Invalid Steam ID format" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.steamid_invalid"))
                elif "请输入玩家名称" in current_text or "Please enter player name" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.name_required"))
                elif "配置文件不存在" in current_text or "Config file not exist" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.config_not_exist"))
                elif "请先保存配置" in current_text or "Please save config first" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.save_config_first"))
                elif "ESL工具未就绪" in current_text or "ESL tool not ready" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.esl_not_ready"))
                elif "steamclient_loader.exe不存在" in current_text or "steamclient_loader.exe not exist" in current_text:
                    self.status_label.setText(t("lan_gaming_page.error.steamclient_loader_not_exist"))

            # 更新使用说明文本
            if hasattr(self, 'help_left_text'):
                left_content = f"""{t("lan_gaming_page.help.steamid_title")}

{t("lan_gaming_page.help.steamid_method_1")}
{t("lan_gaming_page.help.steamid_method_1_example")}
{t("lan_gaming_page.help.steamid_method_1_note")}

{t("lan_gaming_page.help.steamid_method_2")}
{t("lan_gaming_page.help.steamid_method_2_example")}
{t("lan_gaming_page.help.steamid_method_2_note")}

{t("lan_gaming_page.help.steamid_method_3")}"""
                self.help_left_text.setPlainText(left_content)

            if hasattr(self, 'help_right_text'):
                right_content = f"""{t("lan_gaming_page.help.usage_title")}

{t("lan_gaming_page.help.usage_step_1")}
{t("lan_gaming_page.help.usage_step_2")}
{t("lan_gaming_page.help.usage_step_3")}
{t("lan_gaming_page.help.usage_step_4")}
{t("lan_gaming_page.help.usage_step_5")}

{t("lan_gaming_page.help.notes_title")}
{t("lan_gaming_page.help.notes_1")}
{t("lan_gaming_page.help.notes_2")}
{t("lan_gaming_page.help.notes_3")}"""
                self.help_right_text.setPlainText(right_content)

        except Exception as e:
            print(f"语言切换回调失败: {e}")


class LanGamingInitWorker(QThread):
    """局域网配置页面初始化工作线程"""

    progress_updated = Signal(str, str)  # message, msg_type
    initialization_complete = Signal(dict, dict)  # esl_result, lan_mode_result
    initialization_error = Signal(str)  # error_message

    def __init__(self, page):
        super().__init__()
        self.page = page

    def run(self):
        """在后台线程中执行初始化"""
        try:
            # 1. 初始化ESL工具
            self.progress_updated.emit("🔧 正在初始化ESL工具...", "info")
            esl_result = self.page.initialize_esl_sync()

            # 2. 检测局域网模式
            self.progress_updated.emit("🌐 正在检测局域网模式...", "info")
            lan_mode_result = self.page.check_and_update_lan_mode_sync()

            # 发送完成信号
            self.initialization_complete.emit(esl_result, lan_mode_result)

        except Exception as e:
            print(f"初始化工作线程异常: {e}")
            self.initialization_error.emit(str(e))
