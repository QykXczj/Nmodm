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


class StatusBar(QFrame):
    """紧凑状态栏组件 - 专业UI设计"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置紧凑状态栏UI"""
        self.setFixedHeight(45)  # 固定高度，紧凑设计
        self.setStyleSheet("""
            StatusBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e1e2e, stop:1 #2a2a3e);
                border: 0.5px solid #45475a;
                border-radius: 6px;
                padding: 0px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(20)

        # 状态指示器
        self.crack_indicator = self.create_status_indicator("🔓", "破解状态")
        self.game_indicator = self.create_status_indicator("🎮", "游戏配置")
        self.me3_indicator = self.create_status_indicator("🔧", "ME3工具")

        layout.addWidget(self.crack_indicator)
        layout.addWidget(self.game_indicator)
        layout.addWidget(self.me3_indicator)
        layout.addStretch()

        self.setLayout(layout)

    def create_status_indicator(self, icon, name):
        """创建状态指示器"""
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")  # 设置透明背景
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        status_label = QLabel("检查中...")
        status_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: 500;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        layout.addWidget(icon_label)
        layout.addWidget(status_label)
        container.setLayout(layout)

        # 存储引用以便更新 - 直接映射到英文属性名
        name_mapping = {
            "破解状态": "crack",
            "游戏配置": "game",
            "ME3工具": "me3"
        }
        attr_name = name_mapping.get(name, name.lower().replace(' ', '_'))
        setattr(self, f"{attr_name}_label", status_label)

        return container

    def update_status(self, crack_status, game_status, me3_status):
        """更新所有状态"""
        self.crack_label.setText(crack_status)
        self.game_label.setText(game_status)
        self.me3_label.setText(me3_status)


class NighterCard(QFrame):
    """深夜模式专用卡片 - 包含等级控制和启动按钮"""

    def __init__(self, title, mod_manager, parent=None):
        super().__init__(parent)
        self.title = title
        self.mod_manager = mod_manager
        self.setup_ui()

    def setup_ui(self):
        """设置深夜模式卡片UI"""
        self.setStyleSheet("""
            NighterCard {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
                min-height: 60px;
            }
            NighterCard:hover {
                border-color: #45475a;
                background-color: #252537;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        # 内容描述
        content_text = """包含：
• Deepfix mod包 - 深度修复
• nighter.dll - 深夜解锁
• nrsc.dll - 无缝联机"""

        content_label = QLabel(content_text)
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

        # 深夜等级控制
        level_container = QWidget()
        level_container.setStyleSheet("QWidget { background-color: transparent; }")  # 设置透明背景
        level_layout = QHBoxLayout()
        level_layout.setContentsMargins(0, 4, 0, 4)
        level_layout.setSpacing(6)

        level_label = QLabel("深夜等级:")
        level_label.setStyleSheet("color: #cdd6f4; font-size: 12px; background-color: transparent;")

        self.level_display = QLabel("4")
        self.level_display.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                min-width: 20px;
            }
        """)

        # 等级调整按钮
        self.level_down_btn = QPushButton("-")
        self.level_down_btn.setFixedSize(20, 20)
        self.level_down_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 10px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #f2708a; }
        """)
        self.level_down_btn.clicked.connect(lambda: self.adjust_night_level(-1))

        self.level_up_btn = QPushButton("+")
        self.level_up_btn.setFixedSize(20, 20)
        self.level_up_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 10px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #94d3a2; }
        """)
        self.level_up_btn.clicked.connect(lambda: self.adjust_night_level(1))

        level_layout.addWidget(level_label)
        level_layout.addWidget(self.level_down_btn)
        level_layout.addWidget(self.level_display)
        level_layout.addWidget(self.level_up_btn)
        level_layout.addStretch()
        level_container.setLayout(level_layout)

        # 启动按钮
        self.launch_btn = QPushButton("🌙 深夜模式启动")
        self.launch_btn.setFixedHeight(28)  # 只固定高度，宽度自适应
        self.launch_btn.setMinimumWidth(160)  # 设置最小宽度
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7aa2f7;
            }
            QPushButton:pressed {
                background-color: #6c7ce0;
            }
        """)

        layout.addWidget(title_label)
        layout.addWidget(content_label)
        layout.addWidget(level_container)
        layout.addWidget(self.launch_btn)
        self.setLayout(layout)

        # 初始化等级显示和按钮状态
        self.update_level_display()
        self.update_launch_button_state()

    def get_night_level(self):
        """获取当前深夜等级"""
        import os
        import json

        try:
            nighter_json_path = os.path.join(self.mod_manager.mods_dir, "nighter", "nighter.json")
            if os.path.exists(nighter_json_path):
                with open(nighter_json_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("deepNightLevel", 4)
            return None  # 返回None表示没有nighter.json文件
        except Exception:
            return None

    def set_night_level(self, level):
        """设置深夜等级 - 只修改现有的nighter.json，不创建新文件"""
        import os
        import json

        try:
            nighter_json_path = os.path.join(self.mod_manager.mods_dir, "nighter", "nighter.json")

            # 只有文件存在时才允许修改
            if not os.path.exists(nighter_json_path):
                return False

            # 读取现有配置
            with open(nighter_json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 更新深夜等级
            config["deepNightLevel"] = level

            # 保存配置
            with open(nighter_json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True
        except Exception:
            return False

    def adjust_night_level(self, delta):
        """调整深夜等级"""
        current_level = self.get_night_level()
        new_level = max(1, min(5, current_level + delta))

        if new_level != current_level:
            if self.set_night_level(new_level):
                self.update_level_display()

    def update_level_display(self):
        """更新深夜等级显示"""
        current_level = self.get_night_level()

        if current_level is None:
            # 没有nighter.json文件，显示不可用状态
            self.level_display.setText("N/A")
            self.level_down_btn.setEnabled(False)
            self.level_up_btn.setEnabled(False)
        else:
            # 有nighter.json文件，正常显示和控制
            self.level_display.setText(str(current_level))
            self.level_down_btn.setEnabled(current_level > 1)
            self.level_up_btn.setEnabled(current_level < 5)

    def update_launch_button_state(self):
        """更新启动按钮状态 - 检测对应mod是否存在"""
        # 检测深夜模式相关mod
        nighter_available = self.check_nighter_mod_available()
        self.launch_btn.setEnabled(nighter_available)

        if not nighter_available:
            # 按钮不可用时的样式
            self.launch_btn.setText("🌙 深夜模式启动 (缺少mod)")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c7086;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6c7086;
                }
            """)
            self.launch_btn.setToolTip("缺少必要的mod文件：nighter目录、nighter.json或nighter.dll")
        else:
            # 按钮可用时的样式
            self.launch_btn.setText("🌙 深夜模式启动")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7aa2f7;
                }
                QPushButton:pressed {
                    background-color: #6c7ce0;
                }
            """)
            self.launch_btn.setToolTip("启动深夜模式配置")

    def check_nighter_mod_available(self):
        """检查深夜模式mod是否可用"""
        import os

        try:
            # 检查nighter目录是否存在
            nighter_dir = os.path.join(self.mod_manager.mods_dir, "nighter")
            if not os.path.exists(nighter_dir):
                return False

            # 检查nighter.json是否存在
            nighter_json_path = os.path.join(nighter_dir, "nighter.json")
            if not os.path.exists(nighter_json_path):
                return False

            # 检查nighter.dll是否存在
            nighter_dll_path = os.path.join(nighter_dir, "nighter.dll")
            if not os.path.exists(nighter_dll_path):
                return False

            return True
        except Exception:
            return False


class VinsCard(QFrame):
    """VINS大修mod专用卡片 - 包含启动按钮"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()

    def setup_ui(self):
        """设置VINS卡片UI"""
        self.setStyleSheet("""
            VinsCard {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
                min-height: 60px;
            }
            VinsCard:hover {
                border-color: #45475a;
                background-color: #252537;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        # 内容描述
        content_text = """包含：
• VINS mod包 (多版本)
• VINSnightfix 夜晚修复
• FPS/FOV优化DLL
• 无缝联机支持"""

        content_label = QLabel(content_text)
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

        # 启动按钮
        self.launch_btn = QPushButton("🎯 VINS大修mod启动")
        self.launch_btn.setFixedHeight(28)  # 只固定高度，宽度自适应
        self.launch_btn.setMinimumWidth(160)  # 设置最小宽度
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c991;
            }
        """)

        layout.addWidget(title_label)
        layout.addWidget(content_label)
        layout.addWidget(self.launch_btn)
        self.setLayout(layout)

        # 初始化按钮状态
        self.update_launch_button_state()

    def update_launch_button_state(self):
        """更新启动按钮状态 - 检测VINS mod是否存在"""
        vins_available = self.check_vins_mod_available()
        self.launch_btn.setEnabled(vins_available)

        if not vins_available:
            # 按钮不可用时的样式
            self.launch_btn.setText("🎯 VINS大修mod启动 (缺少mod)")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c7086;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6c7086;
                }
            """)
            self.launch_btn.setToolTip("缺少VINS相关mod文件，请检查Mods目录中是否有VINS开头的mod包")
        else:
            # 按钮可用时的样式
            self.launch_btn.setText("🎯 VINS大修mod启动")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a6e3a1;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #94d3a2;
                }
                QPushButton:pressed {
                    background-color: #82c991;
                }
            """)
            self.launch_btn.setToolTip("启动VINS大修mod配置")

    def check_vins_mod_available(self):
        """检查VINS mod是否可用"""
        import os

        try:
            # 获取mod管理器实例
            from src.config.mod_config_manager import ModConfigManager
            mod_manager = ModConfigManager()

            # 检查是否有VINS相关的mod包
            mods_dir = mod_manager.mods_dir
            if not os.path.exists(mods_dir):
                return False

            # 扫描VINS相关包
            has_vins = False
            for item in os.listdir(mods_dir):
                item_path = os.path.join(mods_dir, item)
                if os.path.isdir(item_path) and item.startswith("VINS"):
                    has_vins = True
                    break

            return has_vins
        except Exception:
            return False


class InfoCard(QFrame):
    """优化的信息卡片组件"""

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
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
                min-height: 60px;
            }
            InfoCard:hover {
                border-color: #45475a;
                background-color: #252537;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)  # 专业设计间距
        layout.setSpacing(4)  # 4px基准间距系统

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)

        # 内容
        self.content_label = QLabel(self.content)
        self.content_label.setStyleSheet("""
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
        self.content_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(self.content_label)

        self.setLayout(layout)

    def update_content(self, content):
        """更新内容"""
        self.content = content
        self.content_label.setText(content)






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
        main_layout.setSpacing(4)  # 专业4px间距系统

        # 状态概览区域
        self.create_status_section(main_layout)

        # 添加启动参数说明区域
        self.create_blank_section_1(main_layout)

        # 添加水平布局的区域2和区域3
        self.create_horizontal_sections(main_layout)

        main_widget.setLayout(main_layout)
        self.add_content(main_widget)
        self.add_stretch()
    
    def create_status_section(self, layout):
        """创建状态概览区域 - 使用专业设计的紧凑状态栏"""
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)

    def create_blank_section_1(self, layout):
        """创建启动参数说明区域"""
        params_content = """🚀 默认启动参数说明：
--exe "%gameExe%" --skip-steam-init --game nightreign -p "%essentialsConfig%"

📝 详细参数解释：
• --exe: 指定游戏可执行文件路径，通常指向游戏主程序
• --skip-steam-init: 跳过Steam初始化过程，避免Steam相关检查
• --game nightreign: 指定游戏类型为夜之王朝(Night Reign)
• -p: 指定ME3配置文件路径，包含mod和DLL配置信息

💡 使用说明：
如需启动游戏，请前往"Mod配置"页面使用启动功能。
参数中的占位符会自动替换为实际路径。"""
        params_card = InfoCard("🎮 启动参数说明", params_content)
        layout.addWidget(params_card)



    def create_horizontal_sections(self, layout):
        """创建水平布局的区域2和区域3"""
        # 创建水平容器
        horizontal_container = QWidget()
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(6)  # 专业设计：6px水平间距

        # 区域2 - 深夜模式配置
        section2_card = NighterCard("🌙 深夜模式", self.mod_manager)
        section2_card.launch_btn.clicked.connect(self.launch_nighter_config)

        # 区域3 - VINS大修mod配置
        section3_card = VinsCard("🎯 VINS大修mod")
        section3_card.launch_btn.clicked.connect(self.launch_vins_config)

        # 保存引用以便后续更新状态
        self.vins_card = section3_card

        horizontal_layout.addWidget(section2_card, 1)  # stretch factor = 1，等宽分配
        horizontal_layout.addWidget(section3_card, 1)  # stretch factor = 1，等宽分配

        horizontal_container.setLayout(horizontal_layout)
        layout.addWidget(horizontal_container)

    def launch_nighter_config(self):
        """启动Nighter预设配置"""
        try:
            # 检查基本启动条件
            if not self.check_launch_conditions():
                return

            # 创建nighter.me3配置内容
            nighter_config = '''profileVersion = "v1"

# Mod包配置
[[packages]]
id = "Deepfix"
source = "Deepfix/"

# Native DLL配置
[[natives]]
path = "nighter/nighter.dll"
load_before = [{id = "nrsc.dll", optional = false}]

[[natives]]
path = "SeamlessCoop/nrsc.dll"
'''

            # 保存配置并启动
            self.launch_with_config(nighter_config, "nighter.me3", "🌙 深夜模式")

        except Exception as e:
            self.show_status_message(f"❌ 启动深夜模式失败: {str(e)}", error=True)

    def launch_vins_config(self):
        """启动VINS预设配置"""
        try:
            # 检查基本启动条件
            if not self.check_launch_conditions():
                return

            # 动态检测VINS版本
            vins_packages = self.detect_vins_packages()
            if not vins_packages:
                self.show_status_message("❌ 未找到VINS mod包，请检查Mods目录", error=True)
                return

            # 创建vins.me3配置内容
            vins_config = self.generate_vins_config(vins_packages)

            # 保存配置并启动
            self.launch_with_config(vins_config, "vins.me3", "🎯 VINS大修mod")

        except Exception as e:
            self.show_status_message(f"❌ 启动VINS大修mod失败: {str(e)}", error=True)

    def check_launch_conditions(self):
        """检查启动条件"""
        # 检查游戏路径
        if not self.config_manager.validate_game_path():
            self.show_status_message("❌ 请先配置有效的游戏路径", error=True)
            return False

        # 检查ME3工具
        me3_exe = self.mod_manager.get_me3_executable_path()
        if not me3_exe:
            self.show_status_message("❌ 未找到ME3可执行文件", error=True)
            return False

        return True

    def detect_vins_packages(self):
        """动态检测VINS包版本"""
        import os
        mods_dir = self.mod_manager.mods_dir
        vins_packages = []

        if not os.path.exists(mods_dir):
            return vins_packages

        # 扫描Mods目录
        for item in os.listdir(mods_dir):
            item_path = os.path.join(mods_dir, item)
            if os.path.isdir(item_path):
                # 检测VINS包
                if item.startswith("VINS") and not item.startswith("VINSnightfix"):
                    vins_packages.append({"id": item, "type": "vins"})
                # 检测VINSnightfix包
                elif item.startswith("VINSnightfix"):
                    vins_packages.append({"id": item, "type": "nightfix"})

        return vins_packages

    def generate_vins_config(self, vins_packages):
        """生成VINS配置内容"""
        config_lines = ['profileVersion = "v1"', '', '# Mod包配置']

        # 添加VINS包
        vins_mods = [pkg for pkg in vins_packages if pkg["type"] == "vins"]
        nightfix_mods = [pkg for pkg in vins_packages if pkg["type"] == "nightfix"]

        for pkg in vins_mods:
            config_lines.extend([
                '[[packages]]',
                f'id = "{pkg["id"]}"',
                f'source = "{pkg["id"]}/"',
                ''
            ])

        for pkg in nightfix_mods:
            # 构建load_after依赖
            load_after = []
            for vins_pkg in vins_mods:
                load_after.append(f'{{id = "{vins_pkg["id"]}", optional = true}}')

            config_lines.extend([
                '[[packages]]',
                f'id = "{pkg["id"]}"',
                f'source = "{pkg["id"]}/"',
                f'load_after = [{", ".join(load_after)}]' if load_after else '',
                ''
            ])

        # 添加Native DLL配置
        config_lines.extend([
            '# Native DLL配置',
            '[[natives]]',
            'path = "SeamlessCoop/nrsc.dll"',
            '',
            '[[natives]]',
            'path = "nighter/nighter.dll"',
            'load_before = [{id = "nrsc.dll", optional = false}]',
            ''
        ])

        # 添加VINS DLL
        for pkg in vins_mods:
            config_lines.extend([
                '[[natives]]',
                f'path = "{pkg["id"]}/dll/NightreignFPSFOV.dll"',
                ''
            ])

        return '\n'.join(config_lines)

    def launch_with_config(self, config_content, config_filename, config_name):
        """使用指定配置启动游戏"""
        import os
        import subprocess

        try:
            # 获取配置目录
            config_dir = os.path.dirname(self.mod_manager.config_file)
            config_path = os.path.join(config_dir, config_filename)

            # 保存配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            # 获取启动参数
            game_path = self.config_manager.get_game_path()
            me3_exe = self.mod_manager.get_me3_executable_path()

            # 构建启动命令
            cmd_args = [
                me3_exe,
                "launch",
                "--exe", str(game_path),
                "--skip-steam-init",
                "--game", "nightreign",
                "-p", config_path
            ]

            # 启动游戏
            self.show_status_message(f"🚀 正在使用{config_name}启动游戏...")
            subprocess.Popen(cmd_args, cwd=os.path.dirname(me3_exe))
            self.show_status_message(f"✅ {config_name}启动成功！")

        except Exception as e:
            self.show_status_message(f"❌ {config_name}启动失败: {str(e)}", error=True)











    
    def refresh_status(self):
        """刷新状态显示 - 适配新的专业StatusBar组件"""
        # 检查破解状态
        crack_applied = self.config_manager.is_crack_applied()
        crack_status = "✅ 已应用" if crack_applied else "❌ 未应用"

        # 检查游戏配置状态
        game_configured = self.config_manager.validate_game_path()
        game_status = "✅ 已配置" if game_configured else "❌ 未配置"

        # 检查ME3工具状态
        me3_path = self.mod_manager.get_me3_executable_path()
        me3_status = "✅ 已安装" if me3_path else "❌ 未安装"

        # 更新专业状态栏
        self.status_bar.update_status(crack_status, game_status, me3_status)

        # 更新mod相关按钮状态
        self.update_mod_buttons_state()

    def update_mod_buttons_state(self):
        """更新mod相关按钮状态"""
        try:
            # 更新深夜模式相关按钮和等级显示
            if hasattr(self, 'level_display'):
                self.update_level_display()

            # 更新深夜模式启动按钮（在NighterCard中）
            nighter_card = None
            for child in self.findChildren(NighterCard):
                nighter_card = child
                break

            if nighter_card and hasattr(nighter_card, 'update_launch_button_state'):
                nighter_card.update_launch_button_state()

            # 更新VINS启动按钮
            if hasattr(self, 'vins_card') and hasattr(self.vins_card, 'update_launch_button_state'):
                self.vins_card.update_launch_button_state()

        except Exception as e:
            print(f"更新mod按钮状态失败: {e}")













    def show_status_message(self, message, error=False):
        """显示状态消息"""
        # 这里可以添加状态消息显示逻辑
        status_prefix = "❌ 错误" if error else "ℹ️ 信息"
        print(f"{status_prefix}: {message}")  # 临时使用print，后续可以改为状态栏显示
