"""
局域网联机页面
提供局域网联机配置和启动功能
"""
import os
import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGroupBox, QLineEdit,
                               QTextEdit, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, Signal, QProcess
from .base_page import BasePage


class LanGamingPage(BasePage):
    """局域网联机页面"""

    def __init__(self, parent=None):
        super().__init__("🌐 局域网联机", parent)
        
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境
            self.root_dir = Path(__file__).parent.parent.parent.parent
            
        self.steamclient_dir = self.root_dir / "ESL"
        self.steam_settings_dir = self.steamclient_dir / "steam_settings"
        
        self.setup_content()
        self.load_current_settings()

    def setup_content(self):
        """设置页面内容"""
        # 创建主容器
        main_container = QFrame()
        main_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                margin: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 1. 基础配置区域
        self.setup_basic_config(layout)
        
        # 2. 启动区域
        self.setup_launch_section(layout)
        
        # 3. 说明区域
        self.setup_help_section(layout)

        main_container.setLayout(layout)
        self.add_content(main_container)

    def setup_basic_config(self, parent_layout):
        """设置基础配置区域"""
        config_group = QGroupBox("🔧 局域网联机基础配置")
        config_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #1e1e2e;
            }
        """)

        config_layout = QVBoxLayout()
        config_layout.setSpacing(15)

        # Steam ID 配置
        steamid_layout = QHBoxLayout()
        steamid_label = QLabel("Steam ID:")
        steamid_label.setFixedWidth(120)
        steamid_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        self.steamid_input = QLineEdit()
        self.steamid_input.setPlaceholderText("输入Steam ID (76开头的17位数字)")
        self.steamid_input.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 8px 12px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        
        # 定位存档按钮
        locate_save_btn = QPushButton("📁 定位存档")
        locate_save_btn.setFixedWidth(100)
        locate_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
        """)
        locate_save_btn.clicked.connect(self.locate_save_folder)
        
        steamid_layout.addWidget(steamid_label)
        steamid_layout.addWidget(self.steamid_input, 1)
        steamid_layout.addWidget(locate_save_btn)
        
        # 玩家名称配置
        name_layout = QHBoxLayout()
        name_label = QLabel("玩家名称:")
        name_label.setFixedWidth(120)
        name_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
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
                padding: 8px 12px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input, 1)
        
        # 保存配置按钮
        save_config_btn = QPushButton("💾 保存配置")
        save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
        """)
        save_config_btn.clicked.connect(self.save_config)

        config_layout.addLayout(steamid_layout)
        config_layout.addLayout(name_layout)
        config_layout.addWidget(save_config_btn)
        
        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group)

    def setup_launch_section(self, parent_layout):
        """设置启动区域"""
        launch_group = QGroupBox("🚀 进入局域网联机模式")
        launch_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #1e1e2e;
            }
        """)

        launch_layout = QVBoxLayout()
        launch_layout.setSpacing(15)

        # 状态显示
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #313244;
                border-radius: 6px;
            }
        """)

        # 启动按钮
        launch_btn = QPushButton("🌐 启动局域网联机模式")
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
        """)
        launch_btn.clicked.connect(self.launch_lan_mode)

        launch_layout.addWidget(self.status_label)
        launch_layout.addWidget(launch_btn)
        
        launch_group.setLayout(launch_layout)
        parent_layout.addWidget(launch_group)

    def setup_help_section(self, parent_layout):
        """设置说明区域"""
        help_group = QGroupBox("📖 使用说明")
        help_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #1e1e2e;
            }
        """)

        help_layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(150)
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 10px;
                color: #cdd6f4;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        
        help_content = """Steam ID 获取方法：
1. 从Steam个人主页链接获取，例如：https://steamcommunity.com/profiles/76561198368389836/
   其中 76561198368389836 就是Steam ID（特征：76开头的17位数字）

2. 从本地存档文件夹获取，例如：C:\\Users\\用户名\\AppData\\Roaming\\Nightreign\\76561198368389836
   文件夹名称就是Steam ID

使用步骤：
1. 配置Steam ID和玩家名称，点击"保存配置"
2. 点击"启动局域网联机模式"，程序会重新启动进入联机模式
3. 确保所有玩家都使用相同的网络环境"""
        
        help_text.setPlainText(help_content)
        
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        parent_layout.addWidget(help_group)

    def load_current_settings(self):
        """加载当前配置"""
        try:
            # 加载Steam ID
            steamid_file = self.steam_settings_dir / "force_steamid.txt"
            if steamid_file.exists():
                with open(steamid_file, 'r', encoding='utf-8') as f:
                    steamid = f.read().strip()
                    self.steamid_input.setText(steamid)

            # 加载玩家名称
            name_file = self.steam_settings_dir / "forece_account_name.txt"
            if name_file.exists():
                with open(name_file, 'r', encoding='utf-8') as f:
                    name = f.read().strip()
                    self.name_input.setText(name)

        except Exception as e:
            print(f"加载配置失败: {e}")
            self.update_status(f"加载配置失败: {e}", "error")

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

            # 保存Steam ID
            steamid_file = self.steam_settings_dir / "force_steamid.txt"
            with open(steamid_file, 'w', encoding='utf-8') as f:
                f.write(steamid)

            # 保存玩家名称
            name_file = self.steam_settings_dir / "forece_account_name.txt"
            with open(name_file, 'w', encoding='utf-8') as f:
                f.write(name)

            self.update_status("配置保存成功", "success")

        except Exception as e:
            print(f"保存配置失败: {e}")
            self.update_status(f"保存配置失败: {e}", "error")

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
