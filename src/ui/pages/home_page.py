"""
首页 - 快速启动
显示当前配置状态和快速启动功能
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QLineEdit, QDialog, QTextEdit)
from PySide6.QtCore import Signal, QProcess, Qt
from .base_page import BasePage
from src.config.config_manager import ConfigManager
from src.config.mod_config_manager import ModConfigManager


class HelpDialog(QDialog):
    """无边框帮助弹窗"""

    def __init__(self, help_text, parent=None):
        super().__init__(parent)
        self.help_text = help_text
        self.drag_position = None
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 窗口大小
        self.setFixedSize(600, 400)

        # 主容器
        main_container = QFrame()
        main_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 2px solid #89b4fa;
                border-radius: 10px;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 内容布局
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(15)

        # 标题栏
        title_bar = QFrame()
        title_bar.setStyleSheet("""
            QFrame {
                background-color: #89b4fa;
                border-radius: 8px 8px 0px 0px;
                border: none;
            }
        """)
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel("📖 ME3启动参数帮助")
        title_label.setStyleSheet("""
            QLabel {
                color: #1e1e2e;
                font-size: 16px;
                font-weight: bold;
            }
        """)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1e1e2e;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(30, 30, 46, 0.2);
            }
        """)
        close_btn.clicked.connect(self.close)

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        title_bar.setLayout(title_layout)

        # 保存标题栏引用，用于拖动检测
        self.title_bar = title_bar

        # 帮助内容
        help_content = QTextEdit()
        help_content.setPlainText(self.help_text)
        help_content.setReadOnly(True)
        help_content.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)

        # 默认参数说明
        default_params_label = QLabel("💡 默认启动参数:")
        default_params_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)

        default_params = QLabel("--exe \"%gameExe%\" --skip-steam-init --game nightreign -p \"%essentialsConfig%\"")
        default_params.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
                margin-bottom: 10px;
            }
        """)
        default_params.setWordWrap(True)

        # 添加到内容布局 - 移除底部关闭按钮，增大帮助内容显示空间
        content_layout.addWidget(title_bar)
        content_layout.addWidget(help_content, 1)  # stretch factor让帮助内容占据更多空间
        content_layout.addWidget(default_params_label)
        content_layout.addWidget(default_params)

        main_container.setLayout(content_layout)
        main_layout.addWidget(main_container)
        self.setLayout(main_layout)

        # 居中显示
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖动"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在标题栏区域
            title_bar_rect = self.title_bar.geometry()
            if title_bar_rect.contains(event.position().toPoint()):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 执行拖动"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            # 计算新位置并移动窗口
            new_position = event.globalPosition().toPoint() - self.drag_position
            self.move(new_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束拖动"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class InfoCard(QFrame):
    """信息卡片组件"""

    def __init__(self, title, content="", parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            InfoCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 15px;
            }
            InfoCard:hover {
                border-color: #45475a;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        # 内容
        self.content_label = QLabel(self.content)
        self.content_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        self.content_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(self.content_label)

        self.setLayout(layout)

    def update_content(self, content):
        """更新内容"""
        self.content = content
        self.content_label.setText(content)


class ModInfoCard(QFrame):
    """Mod信息卡片组件 - 水平布局"""

    def __init__(self, title, content="", parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.setup_ui()

    def setup_ui(self):
        """设置UI - 水平布局"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            ModInfoCard {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 15px;
            }
            ModInfoCard:hover {
                border-color: #45475a;
            }
        """)

        # 主要水平布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # 左侧：标题和统计信息
        left_section = QVBoxLayout()
        left_section.setSpacing(8)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 16px;
                font-weight: bold;
            }
        """)

        # 统计信息标签
        self.stats_label = QLabel("📦 Mod包: 0/0 个启用\n🔧 DLL: 0/0 个启用")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                line-height: 1.4;
            }
        """)

        left_section.addWidget(title_label)
        left_section.addWidget(self.stats_label)
        left_section.addStretch()

        # 右侧：详细mod列表
        right_section = QVBoxLayout()
        right_section.setSpacing(8)

        # mod列表标签
        self.mod_list_label = QLabel("💡 当前没有启用任何mod")
        self.mod_list_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        self.mod_list_label.setWordWrap(True)

        right_section.addWidget(self.mod_list_label)
        right_section.addStretch()

        # 添加到主布局
        main_layout.addLayout(left_section, 1)  # 左侧占1份
        main_layout.addLayout(right_section, 2)  # 右侧占2份

        self.setLayout(main_layout)

    def update_content(self, content):
        """更新内容 - 解析并分别显示统计和详细信息"""
        self.content = content
        lines = content.split('\n')

        # 提取统计信息（前两行）
        stats_lines = []
        mod_list_lines = []

        for line in lines:
            if line.startswith('📦 Mod包:') or line.startswith('🔧 DLL:'):
                stats_lines.append(line)
            elif line.strip() and not line.startswith('💡'):
                mod_list_lines.append(line)

        # 更新统计信息
        if stats_lines:
            self.stats_label.setText('\n'.join(stats_lines))
        else:
            self.stats_label.setText("📦 Mod包: 0/0 个启用\n🔧 DLL: 0/0 个启用")

        # 更新mod列表
        if mod_list_lines:
            self.mod_list_label.setText('\n'.join(mod_list_lines))
        else:
            self.mod_list_label.setText("💡 当前没有启用任何mod")


class LaunchParametersWidget(QFrame):
    """启动参数编辑组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            LaunchParametersWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("🚀 启动参数")
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        # 参数编辑框
        self.params_edit = QLineEdit()
        self.params_edit.setPlaceholderText("输入ME3启动参数...")
        # 设置默认启动参数
        default_params = "--exe \"%gameExe%\" --skip-steam-init --game nightreign -p \"%essentialsConfig%\""
        self.params_edit.setText(default_params)
        self.params_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                color: #cdd6f4;
                font-size: 12px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)

        # 按钮容器
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 获取帮助按钮
        self.help_btn = QPushButton("📖 获取参数帮助")
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                color: #cdd6f4;
                font-size: 12px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #6c7086;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)

        button_layout.addWidget(self.help_btn)
        button_layout.addStretch()

        layout.addWidget(title_label)
        layout.addWidget(self.params_edit)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_parameters(self):
        """获取启动参数"""
        return self.params_edit.text().strip()

    def set_parameters(self, params):
        """设置启动参数"""
        self.params_edit.setText(params)


class HomePage(BasePage):
    """快速启动页面"""

    # 页面切换信号
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__("快速启动", parent)

        # 初始化管理器
        self.config_manager = ConfigManager()
        self.mod_manager = ModConfigManager()

        self.setup_content()
        self.refresh_status()
    
    def setup_content(self):
        """设置页面内容"""
        # 创建主要内容区域
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # 状态概览区域
        self.create_status_section(main_layout)

        # mod配置信息区域
        self.create_mod_info_section(main_layout)

        # 启动参数区域
        self.create_launch_params_section(main_layout)

        # 启动按钮区域
        self.create_launch_button_section(main_layout)

        main_widget.setLayout(main_layout)
        self.add_content(main_widget)
        self.add_stretch()
    
    def create_status_section(self, layout):
        """创建状态概览区域"""
        # 状态卡片容器
        status_container = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(15)

        # 破解状态卡片
        self.crack_status_card = InfoCard("🔓 破解状态", "检查中...")

        # 游戏配置状态卡片
        self.game_status_card = InfoCard("🎮 游戏配置", "检查中...")

        # ME3工具状态卡片
        self.me3_status_card = InfoCard("🔧 ME3工具", "检查中...")

        status_layout.addWidget(self.crack_status_card)
        status_layout.addWidget(self.game_status_card)
        status_layout.addWidget(self.me3_status_card)

        status_container.setLayout(status_layout)
        layout.addWidget(status_container)
    
    def create_mod_info_section(self, layout):
        """创建mod配置信息区域"""
        # mod信息卡片 - 使用水平布局的ModInfoCard
        self.mod_info_card = ModInfoCard("📦 当前Mod配置", "正在加载...")
        layout.addWidget(self.mod_info_card)

    def create_launch_params_section(self, layout):
        """创建启动参数区域"""
        self.launch_params_widget = LaunchParametersWidget()
        self.launch_params_widget.help_btn.clicked.connect(self.get_launch_help)
        layout.addWidget(self.launch_params_widget)

    def create_launch_button_section(self, layout):
        """创建启动按钮区域"""
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)

        # 启动游戏按钮
        self.launch_btn = QPushButton("🚀 启动游戏")
        self.launch_btn.setFixedHeight(50)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 12px;
                color: #1e1e2e;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c991;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_game)

        button_layout.addWidget(self.launch_btn)
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
    
    def refresh_status(self):
        """刷新状态显示"""
        # 检查破解状态
        crack_applied = self.config_manager.is_crack_applied()
        if crack_applied:
            self.crack_status_card.update_content("✅ 已应用\n破解文件已复制到游戏目录")
        else:
            self.crack_status_card.update_content("❌ 未应用\n需要先应用破解文件")

        # 检查游戏配置状态
        game_configured = self.config_manager.validate_game_path()
        if game_configured:
            game_path = self.config_manager.get_game_path()
            self.game_status_card.update_content(f"✅ 已配置\n{game_path}")
        else:
            self.game_status_card.update_content("❌ 未配置\n请先配置游戏路径")

        # 检查ME3工具状态
        me3_path = self.mod_manager.get_me3_executable_path()
        if me3_path:
            self.me3_status_card.update_content("✅ 已安装\nME3工具可用")
        else:
            self.me3_status_card.update_content("❌ 未安装\n请下载ME3工具")

        # 更新mod配置信息
        self.update_mod_info()

        # 更新启动按钮状态
        self.update_launch_button_state()

    def update_mod_info(self):
        """更新mod配置信息"""
        try:
            # 先加载配置文件
            self.mod_manager.load_config()

            # 获取配置摘要
            summary = self.mod_manager.get_config_summary()

            # 构建信息文本
            info_lines = []
            info_lines.append(f"📦 Mod包: {summary['enabled_packages']}/{summary['total_packages']} 个启用")
            info_lines.append(f"🔧 DLL: {summary['enabled_natives']}/{summary['total_natives']} 个启用")

            # 显示启用的mod名称
            if summary['packages']:
                info_lines.append("\n📋 启用的Mod包:")
                for pkg in summary['packages']:
                    # 获取备注
                    comment = self.mod_manager.mod_comments.get(pkg.id, "")
                    display_name = f"{pkg.id}-{comment}" if comment else pkg.id
                    status = "(外部)" if pkg.is_external else "(内部)"
                    info_lines.append(f"  • {display_name} {status}")

            if summary['natives']:
                info_lines.append("\n🔧 启用的DLL:")
                for native in summary['natives']:
                    # 获取备注
                    comment = self.mod_manager.native_comments.get(native.path, "")
                    display_name = f"{native.path}-{comment}" if comment else native.path
                    status = "(外部)" if native.is_external else "(内部)"
                    info_lines.append(f"  • {display_name} {status}")

            if not summary['packages'] and not summary['natives']:
                info_lines.append("\n💡 当前没有启用任何mod")

            self.mod_info_card.update_content("\n".join(info_lines))

        except Exception as e:
            self.mod_info_card.update_content(f"❌ 获取mod信息失败: {e}")

    def update_launch_button_state(self):
        """更新启动按钮状态"""
        # 检查启动条件 - 与Mod配置页面保持一致
        game_configured = self.config_manager.validate_game_path()
        me3_installed = self.mod_manager.get_me3_executable_path() is not None

        # 基本条件：游戏路径和ME3工具
        can_launch = game_configured and me3_installed

        self.launch_btn.setEnabled(can_launch)

        if not can_launch:
            missing = []
            if not game_configured:
                missing.append("游戏配置")
            if not me3_installed:
                missing.append("ME3工具")

            self.launch_btn.setText(f"🚫 缺少: {', '.join(missing)}")
        else:
            self.launch_btn.setText("🚀 启动游戏")

    def get_launch_help(self):
        """获取启动参数帮助"""
        try:
            me3_path = self.mod_manager.get_me3_executable_path()
            if not me3_path:
                self.show_status_message("❌ ME3工具未安装，无法获取帮助信息", error=True)
                return

            # 执行me3.exe launch -h命令
            process = QProcess()
            process.setProgram(me3_path)
            process.setArguments(["launch", "-h"])

            # 启动进程并等待完成
            process.start()
            if process.waitForFinished(5000):  # 等待5秒
                output = process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
                error_output = process.readAllStandardError().data().decode('utf-8', errors='ignore')

                if output or error_output:
                    help_text = output + error_output
                    # 使用无边框弹窗显示帮助信息
                    help_dialog = HelpDialog(help_text, self)
                    help_dialog.exec()
                else:
                    self.show_status_message("❌ 未获取到帮助信息", error=True)
            else:
                self.show_status_message("❌ 获取帮助信息超时", error=True)

        except Exception as e:
            self.show_status_message(f"❌ 获取帮助失败: {e}", error=True)



    def launch_game(self):
        """启动游戏 - 与Mod配置页面保持一致的逻辑"""
        try:
            # 检查启动条件
            if not self.launch_btn.isEnabled():
                return

            # 检查游戏路径
            game_path = self.config_manager.get_game_path()
            if not game_path or not self.config_manager.validate_game_path():
                self.show_status_message("❌ 请先配置有效的游戏路径", error=True)
                return

            # 检查ME3可执行文件
            me3_exe = self.mod_manager.get_me3_executable_path()
            if not me3_exe:
                self.show_status_message("❌ 未找到ME3可执行文件，请确保ME3已正确安装", error=True)
                return

            # 保存当前配置
            if not self.mod_manager.save_config():
                self.show_status_message("❌ 保存配置失败", error=True)
                return

            # 获取启动参数
            custom_params = self.launch_params_widget.get_parameters()

            if custom_params:
                # 使用自定义参数，替换占位符
                config_file = str(self.mod_manager.config_file)
                processed_params = custom_params.replace("%gameExe%", str(game_path))
                processed_params = processed_params.replace("%essentialsConfig%", config_file)

                # 构建命令
                cmd_args = [me3_exe, "launch"]

                # 分割参数并添加到命令中
                param_list = []
                parts = processed_params.split()
                i = 0
                while i < len(parts):
                    part = parts[i]
                    # 处理带引号的参数
                    if part.startswith('"') and not part.endswith('"'):
                        # 查找结束引号
                        quoted_part = part
                        i += 1
                        while i < len(parts) and not parts[i].endswith('"'):
                            quoted_part += " " + parts[i]
                            i += 1
                        if i < len(parts):
                            quoted_part += " " + parts[i]
                        # 移除引号
                        param_list.append(quoted_part.strip('"'))
                    else:
                        # 移除引号（如果有）
                        param_list.append(part.strip('"'))
                    i += 1

                cmd_args.extend(param_list)
            else:
                # 使用默认参数 - 与Mod配置页面相同
                config_file = str(self.mod_manager.config_file)
                cmd_args = [
                    me3_exe,
                    "launch",
                    "--exe", game_path,
                    "--skip-steam-init",
                    "--game", "nightreign",
                    "-p", config_file
                ]

            # 启动游戏 - 使用与Mod配置页面相同的方式
            self.show_status_message("🚀 正在启动游戏...")

            import subprocess
            import os
            subprocess.Popen(cmd_args, cwd=os.path.dirname(me3_exe))

            self.show_status_message("✅ 游戏启动成功！")

        except Exception as e:
            self.show_status_message(f"❌ 启动失败: {str(e)}", error=True)

    def show_status_message(self, message, error=False):
        """显示状态消息"""
        # 这里可以添加状态消息显示逻辑
        status_prefix = "❌ 错误" if error else "ℹ️ 信息"
        print(f"{status_prefix}: {message}")  # 临时使用print，后续可以改为状态栏显示
