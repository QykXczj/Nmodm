"""
快速启动页面 - 重构版本
提供预设方案的快速启动功能
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGridLayout)
from PySide6.QtCore import Qt, Signal

from .base_page import BasePage
from src.config.config_manager import ConfigManager
from src.config.mod_config_manager import ModConfigManager


class PresetManager:
    """预设方案管理器 - 简化版本"""

    def __init__(self, mods_dir):
        self.mods_dir = Path(mods_dir)
        self.presets_dir = self.mods_dir / "list"
        self.ensure_presets_dir()

    def ensure_presets_dir(self):
        """确保预设目录存在"""
        self.presets_dir.mkdir(exist_ok=True)

    def scan_presets(self):
        """扫描所有可用的预设方案"""
        presets = []

        if not self.presets_dir.exists():
            return presets

        for me3_file in self.presets_dir.glob("*.me3"):
            preset_info = self.parse_preset_file(me3_file)
            if preset_info:
                presets.append(preset_info)

        return presets

    def parse_preset_file(self, file_path):
        """解析预设配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取元数据
            name = self.extract_metadata(content, "方案名称")
            description = self.extract_metadata(content, "描述")
            icon = self.extract_metadata(content, "图标")

            # 如果没有找到方案名称，使用文件名
            if not name:
                name = file_path.stem

            # 解析依赖
            dependencies = self.parse_dependencies(content)

            # 检查依赖是否满足
            missing_deps = self.check_dependencies(dependencies)

            return {
                'name': name,
                'description': description or "无描述",
                'icon': icon or "🎮",
                'file_path': file_path,
                'dependencies': dependencies,
                'missing_deps': missing_deps,
                'available': len(missing_deps) == 0
            }

        except Exception as e:
            print(f"解析预设文件失败 {file_path}: {e}")
            return None

    def extract_metadata(self, content, key):
        """从配置文件注释中提取元数据"""
        import re
        pattern = rf"#\s*{key}:\s*(.+)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None

    def parse_dependencies(self, content):
        """解析配置文件中的依赖"""
        import re
        dependencies = {'packages': [], 'natives': []}

        # 解析packages
        package_pattern = r'source\s*=\s*"([^"]+)"'
        packages = re.findall(package_pattern, content)
        dependencies['packages'] = packages

        # 解析natives
        native_pattern = r'path\s*=\s*"([^"]+\.dll)"'
        natives = re.findall(native_pattern, content)
        dependencies['natives'] = natives

        return dependencies

    def check_dependencies(self, dependencies):
        """检查依赖是否存在"""
        missing = []

        # 检查packages
        for package in dependencies['packages']:
            # 处理相对路径（从list目录开始）
            if package.startswith('../'):
                package_path = self.presets_dir / package
            else:
                package_path = self.mods_dir / package

            # 解析路径
            resolved_path = package_path.resolve()
            if not resolved_path.exists():
                # 提取简洁的显示名称
                from pathlib import Path
                if package.startswith('../'):
                    # 对于相对路径，提取目录名（去掉../前缀和尾部斜杠）
                    display_name = Path(package.rstrip('/')).name
                else:
                    display_name = package
                missing.append(f"包: {display_name}")

        # 检查natives
        for native in dependencies['natives']:
            # 处理相对路径（从list目录开始）
            if native.startswith('../'):
                native_path = self.presets_dir / native
            else:
                native_path = self.mods_dir / native

            # 解析路径
            resolved_path = native_path.resolve()
            if not resolved_path.exists():
                # 提取简洁的显示名称（文件名）
                from pathlib import Path
                display_name = Path(native).name
                missing.append(f"DLL: {display_name}")

        return missing


class StatusBar(QFrame):
    """紧凑状态栏组件"""

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

        # 临时状态消息标签
        self.temp_status_label = QLabel()
        self.temp_status_label.setVisible(False)
        self.temp_status_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #89b4fa;
                margin-left: 10px;
            }
        """)
        layout.addWidget(self.temp_status_label)

        self.setLayout(layout)

    def create_status_indicator(self, icon, name):
        """创建状态指示器"""
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;
                background-color: transparent;
                min-width: 20px;
            }
        """)

        # 状态文本
        status_label = QLabel("检查中...")
        status_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
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

    def show_temp_message(self, message, status_type="info"):
        """显示临时状态消息"""
        color_map = {
            "success": "#a6e3a1",
            "error": "#f38ba8",
            "warning": "#fab387",
            "info": "#89b4fa"
        }

        color = color_map.get(status_type, "#89b4fa")

        self.temp_status_label.setText(message)
        self.temp_status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid {color};
                margin-left: 10px;
            }}
        """)
        self.temp_status_label.setVisible(True)

        # 延长显示时间到5秒
        from PySide6.QtCore import QTimer
        QTimer.singleShot(5000, lambda: self.temp_status_label.setVisible(False))

    def update_status(self, crack_status, game_status, me3_status):
        """更新所有状态"""
        self.crack_label.setText(crack_status)
        self.game_label.setText(game_status)
        self.me3_label.setText(me3_status)




class PresetCard(QFrame):
    """预设方案卡片 - 简化版本"""

    def __init__(self, preset_info, parent=None):
        super().__init__(parent)
        self.preset_info = preset_info
        self.setup_ui()

    def setup_ui(self):
        """设置预设卡片UI"""
        # 根据可用性设置不同样式
        if self.preset_info['available']:
            border_color = "#313244"
            hover_color = "#45475a"
            bg_color = "#1e1e2e"
            hover_bg = "#252537"
        else:
            border_color = "#6c7086"
            hover_color = "#6c7086"
            bg_color = "#1e1e2e"
            hover_bg = "#1e1e2e"

        self.setStyleSheet(f"""
            PresetCard {{
                background-color: {bg_color};
                border: 0.5px solid {border_color};
                border-radius: 6px;
                padding: 4px;
                min-height: 60px;
            }}
            PresetCard:hover {{
                border-color: {hover_color};
                background-color: {hover_bg};
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 标题
        title_text = f"{self.preset_info['icon']} {self.preset_info['name']}"
        title_label = QLabel(title_text)
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

        # 描述
        description_label = QLabel(self.preset_info['description'])
        description_label.setStyleSheet("""
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
        description_label.setWordWrap(True)

        # 启动按钮
        self.launch_btn = QPushButton()
        if self.preset_info['available']:
            self.launch_btn.setText("🚀 启动")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #7aa2f7;
                }
                QPushButton:pressed {
                    background-color: #6c7ce0;
                }
            """)
        else:
            self.launch_btn.setText("❌ 缺少mod")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c7086;
                    border: none;
                    border-radius: 4px;
                    color: #1e1e2e;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #6c7086;
                }
            """)
            self.launch_btn.setEnabled(False)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(self.launch_btn)
        self.setLayout(layout)


class QuickLaunchPage(BasePage):
    """快速启动页面 - 重构版本"""

    # 页面切换信号
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__("快速启动", parent)

        # 初始化管理器
        self.config_manager = ConfigManager()
        self.mod_manager = ModConfigManager()
        self.preset_manager = PresetManager(self.mod_manager.mods_dir)

        # 用户设置
        self.show_unavailable_presets = True  # 默认显示不可用的预设

        self.setup_content()
        self.refresh_status()

    def setup_content(self):
        """设置页面内容"""
        # 创建主要内容区域
        main_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)  # 紧凑间距系统

        # 状态概览区域
        self.status_bar = StatusBar()
        content_layout.addWidget(self.status_bar)

        # 启动参数说明区域
        self.create_params_info_section(content_layout)

        # 预设方案区域
        self.create_presets_section(content_layout)

        main_widget.setLayout(content_layout)
        self.add_content(main_widget)
        self.add_stretch()

        # 保存内容布局的引用，用于后续更新
        self.content_layout = content_layout
        self.content_widget = main_widget

    def create_params_info_section(self, layout):
        """创建启动参数说明区域"""
        # 创建水平布局容器
        horizontal_container = QWidget()
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(6)

        # 左侧：启动参数说明卡片
        params_content = """🚀 默认启动参数说明：
--exe "%gameExe%" --skip-steam-init --game nightreign -p "%essentialsConfig%"

📝 详细参数解释：
• --exe: 指定游戏可执行文件路径，通常指向游戏主程序
• --skip-steam-init: 跳过Steam初始化过程，避免Steam相关检查
• --game nightreign: 指定游戏类型为黑夜君临(Night Reign)
• -p: 指定ME3配置文件路径，包含mod和DLL配置信息

💡 使用说明：
下方为预设的几套启动方案，点击"🚀 启动"按钮即可快速启动游戏。
"""

        params_card = self.create_info_card("🎮 启动参数说明", params_content)

        # 右侧：Nighter配置卡片
        nighter_card = self.create_nighter_config_card()

        # 添加到水平布局
        horizontal_layout.addWidget(params_card)
        horizontal_layout.addWidget(nighter_card)

        horizontal_container.setLayout(horizontal_layout)
        layout.addWidget(horizontal_container)

    def create_info_card(self, title, content):
        """创建信息卡片"""
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

        layout.addWidget(title_label)
        layout.addWidget(content_label)
        card.setLayout(layout)

        return card

    def create_nighter_config_card(self):
        """创建Nighter配置卡片 - 嵌入式配置界面"""
        from PySide6.QtWidgets import QCheckBox, QRadioButton, QButtonGroup, QGridLayout
        import json
        import os

        # 检查Nighter模块是否存在
        nighter_dll_path = os.path.join("Mods", "nighter", "nighter.dll")
        nighter_module_exists = os.path.exists(nighter_dll_path)

        # 配置文件路径
        config_path = os.path.join("Mods", "nighter", "nighter.json")

        # 读取当前配置
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                force_unlock_deep_night = config.get('forceUnlockDeepNight', True)
                force_deep_night = config.get('forceDeepNight', {'enable': False, 'level': 3})
                bypass_online_check = config.get('bypassOnlineCheck', False)

                current_enable = force_deep_night.get('enable', False)
                current_level = force_deep_night.get('level', 3)
            else:
                # 默认配置
                force_unlock_deep_night = True
                bypass_online_check = False
                current_enable = False
                current_level = 3
                config = {
                    "forceUnlockDeepNight": True,
                    "bypassOnlineCheck": False,
                    "forceDeepNight": {"enable": False, "level": 3},
                    "superNightLordList": [0, 1, 2, 3, 4, 5, 6]
                }
        except Exception as e:
            print(f"读取nighter配置失败: {e}")
            # 使用默认配置
            force_unlock_deep_night = True
            bypass_online_check = False
            current_enable = False
            current_level = 3
            config = {
                "forceUnlockDeepNight": True,
                "bypassOnlineCheck": False,
                "forceDeepNight": {"enable": False, "level": 3},
                "superNightLordList": [0, 1, 2, 3, 4, 5, 6]
            }

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                padding: 4px;
                spacing: 8px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #45475a;
                background-color: #313244;
            }
            QCheckBox::indicator:hover {
                border-color: #89b4fa;
            }
            QCheckBox::indicator:checked {
                border-color: #89b4fa;
                background-color: #89b4fa;
            }
            QRadioButton {
                color: #cdd6f4;
                font-size: 11px;
                padding: 3px;
                spacing: 6px;
                background-color: transparent;
            }
            QRadioButton:disabled {
                color: #45475a;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 2px solid #45475a;
                background-color: #313244;
            }
            QRadioButton::indicator:hover {
                border-color: #fab387;
            }
            QRadioButton::indicator:checked {
                border-color: #fab387;
                background-color: #fab387;
            }
            QRadioButton::indicator:disabled {
                border-color: #313244;
                background-color: #1e1e2e;
            }
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # 标题和状态显示
        if nighter_module_exists:
            title_text = "🌙 Nighter 深夜模式设置"
            title_color = "#89b4fa"
        else:
            title_text = "🌙 Nighter 深夜模式设置 (模块未安装)"
            title_color = "#6c7086"

        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {title_color};
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
        """)
        layout.addWidget(title_label)

        # 如果模块不存在，显示提示信息
        if not nighter_module_exists:
            warning_label = QLabel("⚠️ 未检测到 nighter.dll 模块文件，请先安装 Nighter 模块")
            warning_label.setStyleSheet("""
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    background-color: transparent;
                    border: none;
                    margin: 2px 0px;
                    padding: 4px;
                }
            """)
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)

        # 复选框 - 水平布局
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(8)

        self.unlock_checkbox = QCheckBox("强制解锁深夜模式")
        self.unlock_checkbox.setChecked(force_unlock_deep_night)
        self.unlock_checkbox.setEnabled(nighter_module_exists)
        checkbox_layout.addWidget(self.unlock_checkbox)

        self.bypass_checkbox = QCheckBox("绕过在线检查")
        self.bypass_checkbox.setChecked(bypass_online_check)
        self.bypass_checkbox.setEnabled(nighter_module_exists)
        checkbox_layout.addWidget(self.bypass_checkbox)

        self.enable_force_checkbox = QCheckBox("启用强制指定深夜难度")
        self.enable_force_checkbox.setChecked(current_enable)
        self.enable_force_checkbox.setEnabled(nighter_module_exists)
        checkbox_layout.addWidget(self.enable_force_checkbox)

        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        # 单选框组 - 网格布局
        radio_widget = QWidget()
        radio_widget.setStyleSheet("background-color: transparent;")
        radio_grid = QGridLayout(radio_widget)
        radio_grid.setContentsMargins(0, 0, 0, 0)
        radio_grid.setSpacing(3)

        self.radio_group = QButtonGroup()
        self.radio_buttons = []

        for level in range(1, 6):
            radio = QRadioButton(f"深夜 {level}")
            radio.setChecked(level == current_level)
            # 只有模块存在且启用强制模式时才启用单选框
            radio.setEnabled(nighter_module_exists and current_enable)
            self.radio_buttons.append(radio)
            self.radio_group.addButton(radio, level)

            row = (level - 1) // 3
            col = (level - 1) % 3
            radio_grid.addWidget(radio, row, col)

        layout.addWidget(radio_widget)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)

        reset_btn = QPushButton("重置")
        reset_btn.setEnabled(nighter_module_exists)
        reset_btn.clicked.connect(self.reset_nighter_config)

        save_btn = QPushButton("保存")
        save_btn.setEnabled(nighter_module_exists)
        save_btn.clicked.connect(self.save_nighter_config)

        button_layout.addWidget(reset_btn)
        button_layout.addWidget(save_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        card.setLayout(layout)

        # 保存配置引用和模块状态
        self.nighter_config = config
        self.nighter_config_path = config_path
        self.nighter_module_exists = nighter_module_exists

        # 连接信号
        self.enable_force_checkbox.toggled.connect(self.toggle_difficulty_selection)

        # 初始化状态
        self.toggle_difficulty_selection(current_enable and nighter_module_exists)

        return card

    def toggle_difficulty_selection(self, enabled):
        """启用/禁用难度选择"""
        # 只有模块存在且启用强制模式时才启用单选框
        module_exists = hasattr(self, 'nighter_module_exists') and self.nighter_module_exists
        for radio in self.radio_buttons:
            radio.setEnabled(enabled and module_exists)

    def reset_nighter_config(self):
        """重置Nighter配置为默认值"""
        try:
            # 默认配置
            default_config = {
                "forceUnlockDeepNight": True,
                "bypassOnlineCheck": False,
                "forceDeepNight": {
                    "enable": False,
                    "level": 3
                },
                "superNightLordList": [0, 1, 2, 3, 4, 5, 6]
            }

            # 更新UI控件
            self.unlock_checkbox.setChecked(default_config['forceUnlockDeepNight'])
            self.bypass_checkbox.setChecked(default_config['bypassOnlineCheck'])
            self.enable_force_checkbox.setChecked(default_config['forceDeepNight']['enable'])

            # 设置默认难度等级
            default_level = default_config['forceDeepNight']['level']
            for radio in self.radio_buttons:
                radio.setChecked(self.radio_group.id(radio) == default_level)

            # 更新难度选择状态
            self.toggle_difficulty_selection(default_config['forceDeepNight']['enable'])

            self.show_status_message("✅ 已重置为默认配置")

        except Exception as e:
            self.show_status_message(f"❌ 重置失败: {e}", error=True)

    def save_nighter_config(self):
        """保存Nighter配置"""
        import json
        import os

        # 检查模块是否存在
        if not hasattr(self, 'nighter_module_exists') or not self.nighter_module_exists:
            self.show_status_message("❌ 未检测到 Nighter 模块，无法保存配置", error=True)
            return

        try:
            # 更新配置
            self.nighter_config['forceUnlockDeepNight'] = self.unlock_checkbox.isChecked()
            self.nighter_config['bypassOnlineCheck'] = self.bypass_checkbox.isChecked()
            self.nighter_config['forceDeepNight']['enable'] = self.enable_force_checkbox.isChecked()

            # 获取选中的难度等级
            checked_button = self.radio_group.checkedButton()
            if checked_button:
                new_level = self.radio_group.id(checked_button)
                self.nighter_config['forceDeepNight']['level'] = new_level
            else:
                self.show_status_message("❌ 请选择一个难度等级", error=True)
                return

            # 确保superNightLordList存在
            if 'superNightLordList' not in self.nighter_config:
                self.nighter_config['superNightLordList'] = [0, 1, 2, 3, 4, 5, 6]

            # 保存到文件
            os.makedirs(os.path.dirname(self.nighter_config_path), exist_ok=True)
            with open(self.nighter_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.nighter_config, f, indent=2, ensure_ascii=False)

            self.show_status_message("✅ Nighter 设置已保存")

        except Exception as e:
            self.show_status_message(f"❌ 保存失败: {e}", error=True)



    def create_presets_section(self, layout):
        """创建预设方案区域 - 动态扫描但避免弹窗"""
        # 扫描Mods/list目录中的预设方案
        all_presets = self.preset_manager.scan_presets()

        if not all_presets:
            # 如果没有预设，显示提示信息
            message = "📁 未找到预设方案\n请在 Mods/list/ 目录下添加 .me3 配置文件"
            no_presets_label = QLabel(message)
            no_presets_label.setStyleSheet("""
                QLabel {
                    color: #6c7086;
                    font-size: 14px;
                    text-align: center;
                    padding: 20px;
                    background-color: #1e1e2e;
                    border: 1px dashed #313244;
                    border-radius: 6px;
                }
            """)
            no_presets_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_presets_label)
            return

        # 移除标题，直接显示预设卡片

        # 创建预设网格（2列布局）- 紧凑间距
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(6)  # 减少网格间距

        for i, preset in enumerate(all_presets):
            preset_card = self.create_simple_preset_card_from_scan(preset)
            row = i // 2
            col = i % 2
            grid_layout.addWidget(preset_card, row, col)

        grid_widget.setLayout(grid_layout)
        layout.addWidget(grid_widget)

    def create_simple_preset_card_from_scan(self, preset_info):
        """全新设计的预设卡片 - 信息展示 + 独立按钮"""
        # 创建容器
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 0px;
            }
            QWidget:hover {
                background-color: #252537;
            }
        """)

        # 主布局：水平排列
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 左侧信息区域
        info_label = QLabel()
        icon = preset_info['icon']
        name = preset_info['name']
        desc = preset_info['description']

        if preset_info['available']:
            info_text = f"{icon} {name}\n{desc}"
            info_label.setStyleSheet("""
                QLabel {
                    color: #cdd6f4;
                    font-size: 14px;
                    background-color: transparent;
                    border: none;
                }
            """)
        else:
            missing_text = "、".join(preset_info['missing_deps'][:2])
            if len(preset_info['missing_deps']) > 2:
                missing_text += "..."
            info_text = f"{icon} {name}\n{desc}\n❌ 缺少: {missing_text}"
            info_label.setStyleSheet("""
                QLabel {
                    color: #6c7086;
                    font-size: 14px;
                    background-color: transparent;
                    border: none;
                }
            """)

        info_label.setText(info_text)
        info_label.setWordWrap(True)

        # 右侧启动按钮
        launch_btn = QPushButton()
        launch_btn.setFixedSize(70, 30)

        if preset_info['available']:
            launch_btn.setText("启动")
            launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    border: none;
                    border-radius: 6px;
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
            launch_btn.clicked.connect(lambda: self.launch_scanned_preset(preset_info))
        else:
            launch_btn.setText("不可用")
            launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c7086;
                    border: none;
                    border-radius: 6px;
                    color: #1e1e2e;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            launch_btn.setEnabled(False)

        # 组装布局
        layout.addWidget(info_label, 1)  # 信息区域占主要空间
        layout.addWidget(launch_btn, 0, Qt.AlignVCenter)  # 按钮垂直居中

        container.setLayout(layout)
        return container

    def launch_scanned_preset(self, preset_info):
        """启动扫描到的预设"""
        try:
            # 检查基本启动条件
            if not self.check_launch_conditions():
                return

            # 使用预设信息中的文件路径
            config_path = str(preset_info['file_path'])

            # 显示启动状态
            self.show_status_message("🚀 正在准备启动游戏...")
            # 强制UI刷新，确保状态显示及时更新
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            # 清理冲突进程
            try:
                from src.utils.game_process_cleaner import cleanup_game_processes
                cleanup_game_processes()
            except Exception as e:
                print(f"清理进程时发生错误: {e}")

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
            import subprocess
            import sys

            # 设置创建标志以隐藏控制台窗口
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            if me3_exe == "me3":
                # 完整安装版：不需要指定工作目录
                subprocess.Popen(cmd_args, creationflags=creation_flags)
                me3_type = "完整安装版"
            else:
                # 便携版：需要指定工作目录
                subprocess.Popen(cmd_args, cwd=os.path.dirname(me3_exe), creationflags=creation_flags)
                me3_type = "便携版"
            self.show_status_message(f"✅ {preset_info['name']} 启动成功！（使用{me3_type}ME3）")

        except Exception as e:
            self.show_status_message(f"❌ 启动 {preset_info['name']} 失败: {str(e)}", error=True)



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

    def refresh_status(self):
        """刷新状态显示"""
        # 检查破解状态
        crack_applied = self.config_manager.is_crack_applied()
        crack_status = "✅ 已应用" if crack_applied else "❌ 未应用"

        # 检查游戏配置状态
        game_configured = self.config_manager.validate_game_path()
        game_status = "✅ 已配置" if game_configured else "❌ 未配置"

        # 检查ME3工具状态
        me3_path = self.mod_manager.get_me3_executable_path()
        me3_status = "✅ 已安装" if me3_path else "❌ 未安装"

        # 更新状态栏
        self.status_bar.update_status(crack_status, game_status, me3_status)

    def show_status_message(self, message, error=False):
        """显示状态消息"""
        # 确定状态类型
        if error:
            status_type = "error"
        elif "✅" in message:
            status_type = "success"
        elif "⚠️" in message:
            status_type = "warning"
        else:
            status_type = "info"

        self.status_bar.show_temp_message(message, status_type)
