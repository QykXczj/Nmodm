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
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGroupBox, QLineEdit,
                               QTextEdit, QFileDialog, QMessageBox, QProgressBar,
                               QGridLayout, QScrollArea, QSplitter)
from PySide6.QtCore import Qt, Signal, QProcess, QThread
from .base_page import BasePage


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
            self.status_updated.emit("正在解压ESL工具...", "info")

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)

                for i, file_name in enumerate(file_list):
                    zip_ref.extract(file_name, self.extract_path)
                    progress = int((i + 1) / total_files * 100)
                    self.progress_updated.emit(progress)

                    # 添加小延迟让用户看到进度
                    self.msleep(10)

            self.status_updated.emit("ESL工具解压完成", "success")
            self.extraction_finished.emit(True)

        except Exception as e:
            self.status_updated.emit(f"解压失败: {e}", "error")
            self.extraction_finished.emit(False)


class LanGamingPage(BasePage):
    """局域网配置页面"""

    def __init__(self, parent=None):
        super().__init__("🌐 局域网配置", parent)

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

        # 初始化ESL工具
        self.initialize_esl()

        # 检测局域网模式并更新UI
        self.check_and_update_lan_mode()

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
        self.esl_status_group = QGroupBox("🔧 ESL工具状态")
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
        self.esl_status_label = QLabel("正在检查ESL工具状态...")
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
        config_group = QGroupBox("🔧 局域网配置")
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

        steamid_label = QLabel("Steam ID (76开头的17位数字):")
        steamid_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        steamid_hlayout = QHBoxLayout()
        steamid_hlayout.setSpacing(8)

        self.steamid_input = QLineEdit()
        self.steamid_input.setPlaceholderText("例如: 76561198368389836")
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
        locate_save_btn = QPushButton("📁")
        locate_save_btn.setFixedSize(30, 30)
        locate_save_btn.setToolTip("定位存档文件夹")
        locate_save_btn.setStyleSheet("""
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
        locate_save_btn.clicked.connect(self.locate_save_folder)

        steamid_hlayout.addWidget(self.steamid_input, 1)
        steamid_hlayout.addWidget(locate_save_btn)

        steamid_vlayout.addWidget(steamid_label)
        steamid_vlayout.addLayout(steamid_hlayout)
        steamid_container.setLayout(steamid_vlayout)

        # 玩家名称配置 - 垂直布局
        name_container = QFrame()
        name_container.setStyleSheet("QFrame { border: none; }")
        name_vlayout = QVBoxLayout()
        name_vlayout.setSpacing(6)
        name_vlayout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel("玩家名称:")
        name_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入虚拟Steam玩家名称")
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

        name_vlayout.addWidget(name_label)
        name_vlayout.addWidget(self.name_input)
        name_container.setLayout(name_vlayout)

        # 保存配置按钮
        save_config_btn = QPushButton("💾 保存配置")
        save_config_btn.setStyleSheet("""
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
        save_config_btn.clicked.connect(self.save_config)

        config_layout.addWidget(steamid_container)
        config_layout.addWidget(name_container)
        config_layout.addWidget(save_config_btn)
        config_layout.addStretch()  # 添加弹性空间

        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group, row, col)

    def setup_launch_section_compact(self, parent_layout, row, col):
        """设置启动区域 - 紧凑版"""
        self.launch_group = QGroupBox("🚀 进入局域网联机模式")
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
        self.status_label = QLabel("准备就绪")
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
        self.launch_btn = QPushButton("🌐 进入局域网联机模式")
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
        self.exit_lan_btn = QPushButton("🚪 退出局域网联机")
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
        self.check_dll_btn = QPushButton("🔍 检查DLL状态")
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
        help_group = QGroupBox("📖 使用说明")
        help_group.setMaximumHeight(200)  # 限制高度
        help_group.setStyleSheet("""
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

        left_content = """Steam ID 获取方法：

1. Steam个人主页链接：
   https://steamcommunity.com/profiles/76561198368389836/
   其中 76561198368389836 就是Steam ID

2. 本地存档文件夹：
   C:\\Users\\用户名\\AppData\\Roaming\\Nightreign\\76561198368389836
   文件夹名称就是Steam ID

3. 点击 📁 按钮可直接打开存档文件夹"""

        left_text.setPlainText(left_content)

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

        right_content = """使用步骤：

1. 首次启动会自动解压ESL工具
2. 配置Steam ID和玩家名称
3. 点击"保存配置"
4. 点击"启动局域网联机"
5. 程序会重新启动进入联机模式

注意事项：
• 玩家名称可随意更改
• Steam ID需保证唯一性
• 确保所有玩家在同一网络环境"""

        right_text.setPlainText(right_content)

        help_layout.addWidget(left_text, 1)
        help_layout.addWidget(right_text, 1)

        help_group.setLayout(help_layout)
        parent_layout.addWidget(help_group, row, col, row_span, col_span)

    def initialize_esl(self):
        """初始化ESL工具"""
        try:
            # 1. 检查是否已有解压完成标志
            if self.esl_extracted_flag.exists() and self.validate_esl_structure():
                self.update_esl_status("✅ ESL工具已就绪", "success")
                self.load_current_settings()
                return True

            # 2. 检查OnlineFix文件夹中的esl2.zip
            if self.esl_zip_path.exists():
                self.update_esl_status("📦 发现ESL压缩包，准备解压...", "info")
                self.extract_esl_package()
                return True

            # 3. 检查ESL文件夹中是否有旧的esl2.zip（向后兼容）
            old_esl_zip = self.steamclient_dir / "esl2.zip"
            if old_esl_zip.exists():
                self.update_esl_status("📦 发现旧版ESL压缩包，准备迁移并解压...", "info")
                # 迁移到OnlineFix文件夹
                self.onlinefix_dir.mkdir(exist_ok=True)
                if self.esl_zip_path.exists():
                    self.esl_zip_path.unlink()
                shutil.move(str(old_esl_zip), str(self.esl_zip_path))
                print(f"✅ ESL压缩包已迁移到OnlineFix文件夹")
                self.extract_esl_package()
                return True

            # 4. 都不存在，错误状态
            self.update_esl_status("❌ ESL工具缺失，请重新下载程序", "error")
            return False

        except Exception as e:
            print(f"ESL初始化失败: {e}")
            self.update_esl_status(f"❌ ESL初始化失败: {e}", "error")
            return False

    def validate_esl_structure(self):
        """验证ESL文件结构完整性"""
        try:
            required_files = [
                self.steamclient_dir / "steamclient_loader.exe",
                self.steam_settings_dir,
            ]

            return all(path.exists() for path in required_files)

        except Exception as e:
            print(f"验证ESL结构失败: {e}")
            return False

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

                    self.update_esl_status("✅ ESL工具初始化完成", "success")

                    # 压缩包已经在OnlineFix文件夹中，无需移动
                    print("📦 ESL压缩包保留在OnlineFix文件夹")

                    # 加载配置
                    self.load_current_settings()
                else:
                    self.update_esl_status("❌ ESL工具解压不完整", "error")
            else:
                self.update_esl_status("❌ ESL工具解压失败", "error")

        except Exception as e:
            print(f"解压完成处理失败: {e}")
            self.update_esl_status(f"❌ 解压后处理失败: {e}", "error")

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
                self.update_status("请输入Steam ID", "error")
                return

            if not steamid.startswith('76') or len(steamid) != 17 or not steamid.isdigit():
                self.update_status("Steam ID格式错误，应为76开头的17位数字", "error")
                return

            # 验证玩家名称
            if not name:
                self.update_status("请输入玩家名称", "error")
                return

            # 确保目录存在
            self.steam_settings_dir.mkdir(parents=True, exist_ok=True)

            # 更新INI配置文件
            success = self.update_ini_config(steamid, name)

            if success:
                self.update_status("配置保存成功", "success")
                print(f"✅ 配置已保存: Steam ID={steamid}, 玩家名称={name}")
            else:
                self.update_status("配置保存失败", "error")

        except Exception as e:
            print(f"保存配置失败: {e}")
            self.update_status(f"保存配置失败: {e}", "error")

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
                self.update_status("已打开存档文件夹，请查看文件夹名称获取Steam ID", "info")
            else:
                self.update_status("未找到存档文件夹，请确保游戏已运行过", "warning")

        except Exception as e:
            print(f"定位存档文件夹失败: {e}")
            self.update_status(f"定位存档文件夹失败: {e}", "error")

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
                self.update_status("ESL工具未就绪，请等待初始化完成", "error")
                return

            # 检查配置文件
            is_valid, message = self.check_coldclient_config()
            if not is_valid:
                self.update_status(message, "error")
                return

            # 检查steamclient_loader.exe是否存在
            loader_exe = self.steamclient_dir / "steamclient_loader.exe"
            if not loader_exe.exists():
                self.update_status("steamclient_loader.exe不存在", "error")
                return

            # 检查配置是否已保存
            steamid = self.steamid_input.text().strip()
            name = self.name_input.text().strip()

            if not steamid or not name:
                self.update_status("请先保存配置", "warning")
                return

            # 验证配置文件是否存在且正确
            if not self.config_file_path.exists():
                self.update_status("配置文件不存在，请先保存配置", "warning")
                return

            self.update_status("正在启动局域网联机模式...", "info")

            # 设置局域网模式状态（在启动前）
            self._set_lan_mode_status(True)

            # 启动steamclient_loader.exe
            subprocess.Popen([str(loader_exe)], cwd=str(self.steamclient_dir))

            # 提示用户并延迟关闭窗口
            self.update_status("局域网联机模式启动中，程序将重新启动", "success")

            # 延迟关闭当前窗口，给用户时间看到提示
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._close_current_window)

        except Exception as e:
            print(f"启动局域网联机模式失败: {e}")
            self.update_status(f"启动失败: {e}", "error")
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
                main_window.close()
        except Exception as e:
            print(f"关闭窗口失败: {e}")

    def check_and_update_lan_mode(self):
        """检测局域网模式并更新UI"""
        try:
            from src.utils.lan_mode_detector import get_lan_mode_detector
            detector = get_lan_mode_detector()

            if detector.is_lan_mode:
                # 当前处于局域网模式
                self.update_ui_for_lan_mode(True)
                self.update_status("🌐 当前处于局域网联机模式", "success")
            else:
                # 当前处于正常模式
                self.update_ui_for_lan_mode(False)

        except Exception as e:
            print(f"检测局域网模式失败: {e}")

    def update_ui_for_lan_mode(self, is_lan_mode: bool):
        """根据局域网模式更新UI"""
        if is_lan_mode:
            # 局域网模式：隐藏启动按钮，显示退出按钮和DLL检查按钮
            self.launch_btn.setVisible(False)
            self.exit_lan_btn.setVisible(True)
            self.check_dll_btn.setVisible(True)

            # 更新组标题
            if hasattr(self, 'launch_group'):
                self.launch_group.setTitle("🌐 局域网联机模式管理")
        else:
            # 正常模式：显示启动按钮，隐藏退出按钮和DLL检查按钮
            self.launch_btn.setVisible(True)
            self.exit_lan_btn.setVisible(False)
            self.check_dll_btn.setVisible(False)

            # 更新组标题
            if hasattr(self, 'launch_group'):
                self.launch_group.setTitle("🚀 进入局域网联机模式")

    def exit_lan_mode(self):
        """退出局域网联机模式"""
        try:
            print("🚪 用户请求退出局域网联机模式")
            print("⚠️ 安全提示: 由于DLL注入，Steam和Nmodm需要重启以确保系统安全")
            self.update_status("正在安全退出局域网联机模式...", "info")

            # 执行安全退出流程
            self._perform_safe_exit()

        except Exception as e:
            print(f"退出局域网联机模式失败: {e}")
            self.update_status(f"退出失败: {e}", "error")

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
            self.update_status("步骤1/4: 准备安全退出...", "info")

            # 延迟执行安全退出步骤
            QTimer.singleShot(1000, lambda: self._safe_exit_step_1(dll_manager))

        except Exception as e:
            print(f"安全退出流程失败: {e}")
            self.update_status(f"安全退出失败: {e}", "error")

    def _safe_exit_step_1(self, dll_manager):
        """安全退出步骤1: 卸载DLL"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status("步骤2/4: 卸载steamclient DLL...", "info")
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
            self.update_status(f"DLL卸载失败: {e}", "error")

    def _safe_exit_step_2(self, dll_manager):
        """安全退出步骤2: 重启Steam"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status("步骤3/4: 重启Steam程序...", "info")
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
            self.update_status(f"Steam重启失败: {e}", "error")

    def _safe_exit_step_3(self):
        """安全退出步骤3: 清理状态文件"""
        try:
            from PySide6.QtCore import QTimer

            self.update_status("步骤4/4: 清理状态文件...", "info")
            print("🧹 正在清理局域网模式状态文件...")

            # 清理局域网模式状态
            self._set_lan_mode_status(False)

            print("✅ 状态文件清理成功，下次启动将恢复正常模式")

            # 最后一步：重启Nmodm
            QTimer.singleShot(1000, self._safe_exit_final)

        except Exception as e:
            print(f"状态文件清理失败: {e}")
            self.update_status(f"状态文件清理失败: {e}", "error")

    def _safe_exit_final(self):
        """安全退出最后步骤：重启Nmodm"""
        try:
            from src.utils.dll_manager import get_dll_manager

            self.update_status("✅ 安全退出完成，正在重启Nmodm...", "success")
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

            self.update_status("正在检查DLL状态...", "info")

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
                self.update_status("🌐 检测到steamclient DLL已加载", "success")
            else:
                self.update_status("✅ 未检测到steamclient DLL", "info")

        except Exception as e:
            print(f"检查DLL状态失败: {e}")
            self.update_status(f"检查DLL状态失败: {e}", "error")

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
