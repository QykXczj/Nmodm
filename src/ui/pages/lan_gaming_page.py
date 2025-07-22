"""
局域网配置页面
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
            
        self.steamclient_dir = self.root_dir / "ESL"
        self.steam_settings_dir = self.steamclient_dir / "steam_settings"
        
        self.setup_content()
        self.load_current_settings()

        # 检测局域网模式并更新UI
        self.check_and_update_lan_mode()

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
        config_group = QGroupBox("🔧 局域网配置")
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
        self.launch_group = QGroupBox("🚀 进入局域网联机模式")
        self.launch_group.setStyleSheet("""
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
        self.launch_btn = QPushButton("🌐 启动局域网联机模式")
        self.launch_btn.setStyleSheet("""
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
        self.launch_btn.clicked.connect(self.launch_lan_mode)

        # 退出局域网模式按钮
        self.exit_lan_btn = QPushButton("🚪 退出局域网联机模式")
        self.exit_lan_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 30px;
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
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
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
        
        self.launch_group.setLayout(launch_layout)
        parent_layout.addWidget(self.launch_group)

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
