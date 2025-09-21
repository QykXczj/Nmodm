"""
快速启动页面 - 重构版本
提供预设方案的快速启动功能
"""
import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGridLayout, QDialog,
                               QCheckBox, QSpinBox, QGroupBox, QLineEdit,
                               QTextEdit, QListWidget, QListWidgetItem,
                               QButtonGroup, QMessageBox, QTabWidget,
                               QScrollArea, QMenu)
from PySide6.QtCore import Qt, Signal, QThread

from .base_page import BasePage
from src.config.config_manager import ConfigManager
from src.config.mod_config_manager import ModConfigManager


class GameLaunchThread(QThread):
    """异步游戏启动线程"""

    # 定义信号
    status_update = Signal(str, bool)  # 状态消息, 是否为错误
    launch_completed = Signal(bool, str)  # 启动完成, 成功状态, 消息

    def __init__(self, preset_info, config_manager, mod_manager):
        super().__init__()
        self.preset_info = preset_info
        self.config_manager = config_manager
        self.mod_manager = mod_manager

    def run(self):
        """在后台线程中执行启动流程（智能分阶段显示）"""
        try:
            # 检查基本启动条件
            if not self._check_launch_conditions():
                return

            # 使用预设信息中的文件路径
            config_path = str(self.preset_info['file_path'])

            # === 阶段1：准备启动 ===
            self.status_update.emit("[1/3] 💾 正在准备启动（备份存档、创建脚本）...", False)

            # 执行自动备份
            try:
                from .misc_page import MiscPage
                MiscPage.trigger_auto_backup_if_enabled()
            except Exception as e:
                print(f"自动备份时发生错误: {e}")

            # 获取启动参数
            game_path = self.config_manager.get_game_path()
            me3_exe = self.mod_manager.get_me3_executable_path()

            # 创建bat启动脚本
            bat_path = self._create_launch_bat_script(me3_exe, str(game_path), config_path, "list.bat")
            if not bat_path:
                self.launch_completed.emit(False, "❌ 创建启动脚本失败")
                return

            # 让用户看到准备阶段（500ms）
            self.msleep(500)

            # === 阶段2：清理冲突进程 ===
            self.status_update.emit("[2/3] 🧹 正在清理冲突进程...", False)
            try:
                import threading
                from src.utils.game_process_cleaner import cleanup_game_processes

                def cleanup_processes():
                    try:
                        cleanup_game_processes()
                    except Exception as e:
                        print(f"清理进程时发生错误: {e}")

                # 在后台线程中清理进程
                cleanup_thread = threading.Thread(target=cleanup_processes, daemon=True)
                cleanup_thread.start()
                cleanup_thread.join(timeout=3)  # 最多等待3秒
            except Exception as e:
                print(f"启动进程清理时发生错误: {e}")

            # === 阶段3：启动游戏 ===
            self.status_update.emit("[3/3] 🚀 正在启动游戏...", False)
            from src.utils.dll_manager import safe_launch_game
            safe_launch_game(str(bat_path))

            # 让用户看到启动过程（300ms）
            self.msleep(300)

            me3_type = "完整安装版" if me3_exe == "me3" else "便携版"
            success_msg = f"✅ {self.preset_info['name']} 启动成功！（{me3_type}ME3 + bat脚本）"
            self.launch_completed.emit(True, success_msg)

        except Exception as e:
            error_msg = f"❌ 启动 {self.preset_info['name']} 失败: {str(e)}"
            self.launch_completed.emit(False, error_msg)

    def _check_launch_conditions(self):
        """检查启动条件"""
        try:
            # 检查游戏路径
            game_path = self.config_manager.get_game_path()
            if not game_path or not self.config_manager.validate_game_path():
                self.launch_completed.emit(False, "请先在ME3页面配置游戏路径")
                return False

            # 检查ME3可执行文件
            me3_exe = self.mod_manager.get_me3_executable_path()
            if not me3_exe:
                self.launch_completed.emit(False, "未找到ME3可执行文件，请确保ME3已正确安装")
                return False

            return True
        except Exception as e:
            self.launch_completed.emit(False, f"检查启动条件失败: {str(e)}")
            return False

    def _create_launch_bat_script(self, me3_exe: str, game_path: str, config_path: str, bat_name: str) -> str:
        """创建启动bat脚本"""
        try:
            # 确保me3p/start目录存在
            start_dir = Path("me3p/start")
            start_dir.mkdir(parents=True, exist_ok=True)

            # 获取绝对路径
            config_path = str(Path(config_path).resolve())
            game_path = str(Path(game_path).resolve())

            # 读取启动参数
            launch_params = ['--skip-steam-init', '--online']  # 默认参数
            try:
                launch_params = LaunchParamsConfigDialog.get_launch_params()
            except Exception as e:
                print(f"读取启动参数失败，使用默认参数: {e}")

            # 构建启动命令
            if me3_exe == "me3":
                # 完整安装版
                me3_cmd = "me3"
            else:
                # 便携版，使用绝对路径
                me3_cmd = f'"{str(Path(me3_exe).resolve())}"'

            # 构建完整命令
            cmd_parts = [
                me3_cmd,
                "launch",
                f'--exe "{game_path}"'
            ]
            cmd_parts.extend(launch_params)
            cmd_parts.extend([
                "--game nightreign",
                f'-p "{config_path}"'
            ])

            # 创建bat脚本内容（使用start命令）
            bat_content = f"""chcp 65001
start "Nmodm-ME3" {' '.join(cmd_parts)}
"""

            # 写入bat文件
            bat_path = start_dir / bat_name
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)

            print(f"创建启动脚本: {bat_path}")
            print(f"脚本内容: {bat_content.strip()}")

            return str(bat_path.resolve())

        except Exception as e:
            print(f"创建启动脚本失败: {e}")
            return None


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

        # 根据消息类型设置不同的显示时长
        from PySide6.QtCore import QTimer
        if status_type == "success":
            # 成功消息显示8秒
            QTimer.singleShot(8000, lambda: self.temp_status_label.setVisible(False))
        elif status_type == "error":
            # 错误消息显示10秒
            QTimer.singleShot(10000, lambda: self.temp_status_label.setVisible(False))
        else:
            # 其他消息显示5秒
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

        params_card = self.create_info_card_with_button("🎮 启动参数说明", params_content, "⚙️ 参数配置", self.show_launch_params_config)

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

    def create_info_card_with_button(self, title, content, button_text, button_callback):
        """创建带按钮的信息卡片"""
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

        # 标题和按钮的水平布局
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

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
        title_layout.addWidget(title_label)

        # 弹簧
        title_layout.addStretch()

        # 按钮
        button = QPushButton(button_text)
        button.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #7287fd;
            }
        """)
        button.clicked.connect(button_callback)
        title_layout.addWidget(button)

        layout.addLayout(title_layout)

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

        # 添加编辑预设方案按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        edit_preset_btn = QPushButton("📝 编辑预设方案")
        edit_preset_btn.setFixedHeight(30)
        edit_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7dc4a0;
            }
        """)
        edit_preset_btn.clicked.connect(self.show_preset_editor)
        button_layout.addWidget(edit_preset_btn)

        layout.addLayout(button_layout)

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
        """启动扫描到的预设（异步版本）"""
        try:
            # 显示初始状态
            self.show_status_message("🚀 正在准备启动游戏...")

            # 创建异步启动线程
            self.launch_thread = GameLaunchThread(preset_info, self.config_manager, self.mod_manager)

            # 连接信号
            self.launch_thread.status_update.connect(self._on_launch_status_update)
            self.launch_thread.launch_completed.connect(self._on_launch_completed)

            # 启动线程
            self.launch_thread.start()

        except Exception as e:
            self.show_status_message(f"❌ 启动 {preset_info['name']} 失败: {str(e)}", error=True)

    def _on_launch_status_update(self, message, is_error):
        """处理启动状态更新"""
        self.show_status_message(message, error=is_error)

    def _on_launch_completed(self, success, message):
        """处理启动完成"""
        self.show_status_message(message, error=not success)

    def create_launch_bat_script(self, me3_exe: str, game_path: str, config_path: str, bat_name: str) -> str:
        """创建启动bat脚本"""
        try:
            # 确保me3p/start目录存在
            start_dir = Path("me3p/start")
            start_dir.mkdir(parents=True, exist_ok=True)

            # 获取绝对路径
            config_path = str(Path(config_path).resolve())
            game_path = str(Path(game_path).resolve())

            # 读取启动参数
            launch_params = ['--skip-steam-init', '--online']  # 默认参数
            try:
                launch_params = LaunchParamsConfigDialog.get_launch_params()
            except Exception as e:
                print(f"读取启动参数失败，使用默认参数: {e}")

            # 构建启动命令
            if me3_exe == "me3":
                # 完整安装版
                me3_cmd = "me3"
            else:
                # 便携版，使用绝对路径
                me3_cmd = f'"{str(Path(me3_exe).resolve())}"'

            # 构建完整命令
            cmd_parts = [
                me3_cmd,
                "launch",
                f'--exe "{game_path}"'
            ]
            cmd_parts.extend(launch_params)
            cmd_parts.extend([
                "--game nightreign",
                f'-p "{config_path}"'
            ])

            # 创建bat脚本内容（使用start命令）
            bat_content = f"""chcp 65001
start "Nmodm-ME3" {' '.join(cmd_parts)}
"""

            # 写入bat文件
            bat_path = start_dir / bat_name
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)

            print(f"创建启动脚本: {bat_path}")
            print(f"脚本内容: {bat_content.strip()}")

            return str(bat_path.resolve())

        except Exception as e:
            print(f"创建启动脚本失败: {e}")
            return None



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

    def refresh_presets_section(self):
        """刷新预设方案区域"""
        try:
            # 移除所有预设相关的widget（包括网格布局和提示信息）
            widgets_to_remove = []

            for i in range(self.content_layout.count()):
                item = self.content_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()

                    # 检查是否是预设方案相关的widget
                    is_preset_widget = False

                    # 1. 检查是否是网格布局（预设卡片容器）
                    if hasattr(widget, 'layout') and widget.layout():
                        layout = widget.layout()
                        if isinstance(layout, QGridLayout):
                            is_preset_widget = True

                    # 2. 检查是否是"无预设"提示QLabel
                    elif isinstance(widget, QLabel):
                        text = widget.text()
                        if "未找到预设方案" in text or "Mods/list/" in text:
                            is_preset_widget = True

                    if is_preset_widget:
                        widgets_to_remove.append(widget)

            # 移除所有找到的预设相关widget
            for widget in widgets_to_remove:
                widget.setParent(None)

            # 重新创建预设方案区域
            self.create_presets_section(self.content_layout)

        except Exception as e:
            print(f"刷新预设方案区域失败: {e}")
            import traceback
            traceback.print_exc()

    def show_launch_params_config(self):
        """显示启动参数配置对话框"""
        dialog = LaunchParamsConfigDialog(self)
        dialog.exec()

    def show_preset_editor(self):
        """显示预设方案编辑对话框"""
        try:
            dialog = PresetEditorDialog(self)
            # 连接信号，当预设方案发生变化时刷新主页面
            dialog.presets_changed.connect(self.refresh_presets_section)
            dialog.exec()
        except Exception as e:
            print(f"显示预设编辑器失败: {e}")
            import traceback
            traceback.print_exc()


class LaunchParamsConfigDialog(QDialog):
    """启动参数配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("启动参数配置")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #89b4fa;
                border-radius: 12px;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #89b4fa;
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: transparent;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 8px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #45475a;
                background-color: #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QSpinBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QSpinBox:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #7287fd;
            }
            QLabel {
                color: #bac2de;
                font-size: 12px;
                background-color: transparent;
            }
        """)

        # 拖拽相关变量
        self.drag_position = None

        self.init_ui()
        self.load_config()

        # 如果配置文件不存在，创建默认配置文件
        config_file = self.get_config_file_path()
        if not config_file.exists():
            self.create_default_config()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏（带关闭按钮）
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("🎮 ME3启动参数配置")
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
                background-color: transparent;
            }
        """)
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #f38ba8;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        layout.addLayout(title_layout)

        # 说明
        desc_label = QLabel("配置ME3启动时使用的参数，这些设置将同时应用于快速启动和MOD配置页面。")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 性能优化参数组
        perf_group = QGroupBox("🚀 性能优化参数")
        perf_layout = QVBoxLayout()

        self.no_boot_boost_cb = QCheckBox("禁用启动加速缓存 (--no-boot-boost)")
        self.no_boot_boost_cb.setToolTip("禁用BHD文件缓存，可能会增加启动时间但减少磁盘占用")
        perf_layout.addWidget(self.no_boot_boost_cb)

        self.show_logos_cb = QCheckBox("显示游戏开场Logo (--show-logos)")
        self.show_logos_cb.setToolTip("显示游戏开场动画，取消勾选可加快进入游戏速度")
        perf_layout.addWidget(self.show_logos_cb)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # 网络参数组
        network_group = QGroupBox("🌐 网络相关参数")
        network_layout = QVBoxLayout()

        self.skip_steam_init_cb = QCheckBox("跳过Steam初始化 (--skip-steam-init)")
        self.skip_steam_init_cb.setToolTip("跳过Steam初始化，避免Steam相关问题")
        self.skip_steam_init_cb.setChecked(True)  # 默认启用
        self.skip_steam_init_cb.setEnabled(False)  # 不允许修改，因为是必需的
        network_layout.addWidget(self.skip_steam_init_cb)

        self.online_cb = QCheckBox("启用在线匹配 (--online) ⚠️ 有封号风险")
        self.online_cb.setToolTip("重新启用在线多人游戏功能，但可能导致账号被封禁")
        self.online_cb.setStyleSheet("QCheckBox { color: #f38ba8; }")
        network_layout.addWidget(self.online_cb)

        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # 调试参数组
        debug_group = QGroupBox("🛠️ 调试相关参数")
        debug_layout = QVBoxLayout()

        self.disable_arxan_cb = QCheckBox("禁用Arxan保护 (--disable-arxan)")
        self.disable_arxan_cb.setToolTip("中和Arxan/GuardIT代码保护，提高MOD兼容性")
        debug_layout.addWidget(self.disable_arxan_cb)

        self.diagnostics_cb = QCheckBox("启用诊断模式 (-d, --diagnostics)")
        self.diagnostics_cb.setToolTip("启用详细的诊断信息，用于问题排查")
        debug_layout.addWidget(self.diagnostics_cb)

        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 重置按钮
        reset_btn = QPushButton("🔄 重置默认")
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)

        # 取消按钮
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # 保存按钮
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_config_file_path(self):
        """获取配置文件路径"""
        from pathlib import Path
        config_dir = Path("me3p") / "start"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "launch_params.json"

    def create_default_config(self):
        """创建默认配置文件"""
        try:
            default_config = {
                'no_boot_boost': False,
                'show_logos': False,
                'skip_steam_init': True,  # 始终为True
                'online': True,  # 默认启用在线功能
                'disable_arxan': False,
                'diagnostics': False
            }

            config_file = self.get_config_file_path()
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            print(f"已创建默认启动参数配置: {config_file}")

        except Exception as e:
            print(f"创建默认启动参数配置失败: {e}")

    def load_config(self):
        """加载配置"""
        try:
            config_file = self.get_config_file_path()
            if config_file.exists():
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.no_boot_boost_cb.setChecked(config.get('no_boot_boost', False))
                self.show_logos_cb.setChecked(config.get('show_logos', False))
                self.online_cb.setChecked(config.get('online', True))  # 默认启用在线功能
                self.disable_arxan_cb.setChecked(config.get('disable_arxan', False))
                self.diagnostics_cb.setChecked(config.get('diagnostics', False))
            else:
                # 配置文件不存在，设置默认值
                self.no_boot_boost_cb.setChecked(False)
                self.show_logos_cb.setChecked(False)
                self.online_cb.setChecked(True)  # 默认启用在线功能
                self.disable_arxan_cb.setChecked(False)
                self.diagnostics_cb.setChecked(False)
        except Exception as e:
            print(f"加载启动参数配置失败: {e}")
            # 设置默认值
            self.no_boot_boost_cb.setChecked(False)
            self.show_logos_cb.setChecked(False)
            self.online_cb.setChecked(True)  # 默认启用在线功能
            self.disable_arxan_cb.setChecked(False)
            self.diagnostics_cb.setChecked(False)

    def save_config(self):
        """保存配置"""
        try:
            config = {
                'no_boot_boost': self.no_boot_boost_cb.isChecked(),
                'show_logos': self.show_logos_cb.isChecked(),
                'skip_steam_init': True,  # 始终为True
                'online': self.online_cb.isChecked(),
                'disable_arxan': self.disable_arxan_cb.isChecked(),
                'diagnostics': self.diagnostics_cb.isChecked()
            }

            config_file = self.get_config_file_path()
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.accept()

        except Exception as e:
            print(f"保存启动参数配置失败: {e}")

    def reset_to_default(self):
        """重置为默认设置"""
        self.no_boot_boost_cb.setChecked(False)
        self.show_logos_cb.setChecked(False)
        self.online_cb.setChecked(True)  # 默认启用在线功能
        self.disable_arxan_cb.setChecked(False)
        self.diagnostics_cb.setChecked(False)

    @staticmethod
    def get_launch_params():
        """静态方法：获取当前的启动参数列表"""
        try:
            from pathlib import Path
            config_file = Path("me3p") / "start" / "launch_params.json"

            if not config_file.exists():
                return ['--skip-steam-init', '--online']  # 返回默认参数

            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            params = []

            if config.get('no_boot_boost', False):
                params.append('--no-boot-boost')

            if config.get('show_logos', False):
                params.append('--show-logos')

            # skip_steam_init 始终添加
            params.append('--skip-steam-init')

            if config.get('online', False):
                params.append('--online')

            if config.get('disable_arxan', False):
                params.append('--disable-arxan')

            if config.get('diagnostics', False):
                params.extend(['-d'])

            return params

        except Exception as e:
            print(f"获取启动参数失败: {e}")
            return ['--skip-steam-init', '--online']  # 返回默认参数

    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖拽"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class PresetEditorDialog(QDialog):
    """预设方案编辑对话框"""

    # 添加信号，用于通知主页面刷新预设方案
    presets_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑预设方案")
        self.setFixedSize(850, 650)
        self.setModal(True)

        # 设置无边框
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # 拖拽相关
        self.drag_position = None

        # 编辑模式相关
        self.editing_file = None

        # 强制加载状态（临时存储）
        self.force_load_last_mods = set()
        self.force_load_first_dlls = set()

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 8px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #89b4fa;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #45475a;
                border-radius: 3px;
                background-color: #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QCheckBox::indicator:checked {
                image: none;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                border-radius: 4px;
                background-color: #1e1e2e;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QTabBar::tab:hover {
                background-color: #45475a;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
            QScrollArea {
                border: 1px solid #45475a;
                border-radius: 4px;
                background-color: #313244;
            }
        """)

        self.init_ui()
        self.load_available_mods()
        self.load_existing_presets()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 自定义标题栏
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)

        # 主内容区域
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 创建新预设选项卡
        create_tab = QWidget()
        self.init_create_tab(create_tab)
        self.tab_widget.addTab(create_tab, "📝 创建预设")

        # 管理预设选项卡
        manage_tab = QWidget()
        self.init_manage_tab(manage_tab)
        self.tab_widget.addTab(manage_tab, "🗂️ 管理预设")

        # 预览选项卡
        preview_tab = QWidget()
        self.init_preview_tab(preview_tab)
        self.tab_widget.addTab(preview_tab, "👁️ 预览配置")

        # 选项卡切换事件
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        content_layout.addWidget(self.tab_widget)

        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        layout.addWidget(content_widget)

        self.setLayout(layout)

    def create_title_bar(self):
        """创建自定义标题栏"""
        title_bar = QFrame()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 0, 12, 0)

        # 标题
        title_label = QLabel("📝 预设方案管理")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title_label)

        layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cdd6f4;
                border: none;
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        title_bar.setLayout(layout)
        return title_bar

    def init_preview_tab(self, tab):
        """初始化预览选项卡"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("📄 预设配置预览")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #cdd6f4;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)

        # 预设信息区域
        info_group = QGroupBox("预设信息")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        info_layout = QVBoxLayout(info_group)

        self.preview_info_label = QLabel("请从管理预设页面选择要预览的预设方案")
        self.preview_info_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 10px;")
        info_layout.addWidget(self.preview_info_label)

        layout.addWidget(info_group)

        # 配置内容预览区域
        content_group = QGroupBox("配置文件内容")
        content_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        content_layout = QVBoxLayout(content_group)

        self.preview_content = QTextEdit()
        self.preview_content.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 10px;
                line-height: 1.4;
            }
        """)
        self.preview_content.setPlainText("# 暂无预览内容\n# 请从管理预设页面点击预览按钮")
        self.preview_content.setReadOnly(True)
        content_layout.addWidget(self.preview_content)

        layout.addWidget(content_group)

    def init_create_tab(self, tab_widget):
        """初始化创建预设选项卡"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # 基本信息区域
        info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout()

        # 方案名称和文件名
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("方案名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入方案名称，如：我的自定义方案")
        name_layout.addWidget(self.name_edit)

        name_layout.addWidget(QLabel("文件名:"))
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("如：my_preset（自动添加.me3扩展名）")
        name_layout.addWidget(self.filename_edit)

        info_layout.addLayout(name_layout)

        # 方案描述
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("方案描述:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入方案描述，如：包含深夜模式和无缝联机功能")
        self.desc_edit.setMaximumHeight(50)
        desc_layout.addWidget(self.desc_edit)
        info_layout.addLayout(desc_layout)

        # 图标选择
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(QLabel("选择图标:"))
        self.icon_buttons = []
        self.icon_group = QButtonGroup()

        icons = ["🎮", "🌙", "⚔️", "🛡️", "🔥", "⭐", "💎", "🚀", "🎯", "🏆"]
        for i, icon in enumerate(icons):
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 20px;
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 0px;
                    text-align: center;
                }
                QPushButton:checked {
                    background-color: #89b4fa;
                    border-color: #89b4fa;
                }
                QPushButton:hover {
                    background-color: #45475a;
                }
            """)
            self.icon_group.addButton(btn, i)
            self.icon_buttons.append(btn)
            icon_layout.addWidget(btn)

        # 默认选择第一个图标
        self.icon_buttons[0].setChecked(True)

        icon_layout.addStretch()
        info_layout.addLayout(icon_layout)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Mod选择区域 - 使用复选框
        mod_group = QGroupBox("Mod选择")
        mod_layout = QHBoxLayout()

        # 左侧：Mod包选择
        packages_layout = QVBoxLayout()
        packages_layout.addWidget(QLabel("Mod包 (Packages):"))

        packages_scroll = QScrollArea()
        packages_widget = QWidget()
        self.packages_layout = QVBoxLayout(packages_widget)
        self.packages_checkboxes = []
        packages_scroll.setWidget(packages_widget)
        packages_scroll.setWidgetResizable(True)
        packages_scroll.setMaximumHeight(150)
        packages_layout.addWidget(packages_scroll)

        # 右侧：DLL选择
        natives_layout = QVBoxLayout()
        natives_layout.addWidget(QLabel("DLL文件 (Natives):"))

        natives_scroll = QScrollArea()
        natives_widget = QWidget()
        self.natives_layout = QVBoxLayout(natives_widget)
        self.natives_checkboxes = []
        natives_scroll.setWidget(natives_widget)
        natives_scroll.setWidgetResizable(True)
        natives_scroll.setMaximumHeight(150)
        natives_layout.addWidget(natives_scroll)

        mod_layout.addLayout(packages_layout)
        mod_layout.addLayout(natives_layout)

        mod_group.setLayout(mod_layout)
        layout.addWidget(mod_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #7c7d93;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # 根据当前选项卡显示不同的保存按钮
        self.save_btn = QPushButton("保存方案")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7dc4a0;
            }
        """)
        self.save_btn.clicked.connect(self.save_preset)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        tab_widget.setLayout(layout)

    def init_manage_tab(self, tab_widget):
        """初始化管理预设选项卡 - 采用快速启动风格"""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 顶部标题和刷新按钮
        header_layout = QHBoxLayout()

        title_label = QLabel("📋 预设方案管理")
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
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("""
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
        refresh_btn.clicked.connect(self.load_existing_presets)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # 预设卡片容器
        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setSpacing(6)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.presets_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        layout.addWidget(scroll_area)

        tab_widget.setLayout(layout)

    def load_available_mods(self):
        """加载可用的mod列表"""
        try:
            from ...config.mod_config_manager import ModConfigManager
            mod_manager = ModConfigManager()
            available_mods = mod_manager.scan_mods_directory()

            # 清空现有复选框
            for checkbox in self.packages_checkboxes:
                checkbox.setParent(None)
            self.packages_checkboxes.clear()

            for checkbox in self.natives_checkboxes:
                checkbox.setParent(None)
            self.natives_checkboxes.clear()

            # 加载mod包复选框（包含备注信息）
            for package in available_mods["packages"]:
                # 处理外部mod标识
                clean_name = package.replace(" (外部)", "")
                is_external = package.endswith(" (外部)")

                # 获取备注信息
                comment = mod_manager.get_mod_comment(clean_name)

                # 构建显示文本
                if is_external:
                    display_text = f"📁 {package}"
                else:
                    display_text = f"📁 {package}"

                if comment:
                    display_text += f" - {comment}"

                checkbox = QCheckBox(display_text)
                checkbox.setObjectName(package)
                checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
                checkbox.customContextMenuRequested.connect(
                    lambda pos, cb=checkbox: self.show_package_context_menu(pos, cb)
                )
                # 添加悬停效果
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #cdd6f4;
                        font-size: 12px;
                        padding: 4px;
                        spacing: 8px;
                    }
                    QCheckBox:hover {
                        background-color: rgba(255, 255, 255, 0.1);
                        border-radius: 4px;
                        color: #f5f5f5;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #45475a;
                        background-color: #1e1e2e;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #a6e3a1;
                        border-color: #a6e3a1;
                    }
                    QCheckBox::indicator:hover {
                        border-color: #f5f5f5;
                        background-color: rgba(255, 255, 255, 0.2);
                    }
                """)
                self.packages_checkboxes.append(checkbox)
                self.packages_layout.addWidget(checkbox)

            # 加载DLL文件复选框（包含备注信息）
            for native in available_mods["natives"]:
                # 处理外部DLL标识
                clean_name = native.replace(" (外部)", "")
                is_external = native.endswith(" (外部)")

                # 获取备注信息
                comment = mod_manager.get_native_comment(clean_name)

                # 提取DLL文件名（去除路径）
                display_dll_name = native
                if "/" in native and not native.endswith(" (外部)"):
                    # 对于内部DLL，提取文件名部分
                    display_dll_name = native.split("/")[-1]
                elif native.endswith(" (外部)"):
                    # 对于外部DLL，保持原样
                    display_dll_name = native

                # 构建显示文本
                display_text = f"🔧 {display_dll_name}"

                if comment:
                    display_text += f" - {comment}"

                checkbox = QCheckBox(display_text)
                checkbox.setObjectName(native)
                checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
                checkbox.customContextMenuRequested.connect(
                    lambda pos, cb=checkbox: self.show_native_context_menu(pos, cb)
                )
                # 添加悬停效果
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #cdd6f4;
                        font-size: 12px;
                        padding: 4px;
                        spacing: 8px;
                    }
                    QCheckBox:hover {
                        background-color: rgba(255, 255, 255, 0.1);
                        border-radius: 4px;
                        color: #f5f5f5;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #45475a;
                        background-color: #1e1e2e;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #a6e3a1;
                        border-color: #a6e3a1;
                    }
                    QCheckBox::indicator:hover {
                        border-color: #f5f5f5;
                        background-color: rgba(255, 255, 255, 0.2);
                    }
                """)
                self.natives_checkboxes.append(checkbox)
                self.natives_layout.addWidget(checkbox)

        except Exception as e:
            print(f"加载mod列表失败: {e}")

    def show_package_context_menu(self, position, checkbox):
        """显示mod包右键菜单"""
        if not checkbox:
            return

        # 获取mod名称（去除emoji前缀和备注）
        full_text = checkbox.text().replace("📁 ", "")

        # 如果包含备注（格式：ModName - Comment），提取ModName部分
        if " - " in full_text:
            mod_name = full_text.split(" - ")[0]
        else:
            mod_name = full_text

        is_external = mod_name.endswith(" (外部)")
        clean_name = mod_name.replace(" (外部)", "") if is_external else mod_name

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)

        # 添加强制最后加载选项
        # 检查临时状态
        is_force_last = hasattr(self, 'force_load_last_mods') and clean_name in self.force_load_last_mods
        if is_force_last:
            force_last_action = menu.addAction("🔓 取消强制最后加载")
            force_last_action.triggered.connect(lambda: self.clear_force_load_last(clean_name))
        else:
            force_last_action = menu.addAction("🔒 强制最后加载")
            force_last_action.triggered.connect(lambda: self.set_force_load_last(clean_name))

        menu.exec(checkbox.mapToGlobal(position))

    def show_native_context_menu(self, position, checkbox):
        """显示DLL右键菜单"""
        if not checkbox:
            return

        # 获取DLL名称（去除emoji前缀和备注）
        full_text = checkbox.text().replace("🔧 ", "")

        # 如果包含备注（格式：DLLName - Comment），提取DLLName部分
        if " - " in full_text:
            dll_name = full_text.split(" - ")[0]
        else:
            dll_name = full_text

        is_external = dll_name.endswith(" (外部)")
        clean_name = dll_name.replace(" (外部)", "") if is_external else dll_name

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #a6e3a1;
                color: #1e1e2e;
            }
        """)

        # 添加强制优先加载功能
        # 检查临时状态
        is_force_load_first = hasattr(self, 'force_load_first_dlls') and clean_name in self.force_load_first_dlls

        if is_force_load_first:
            clear_load_first_action = menu.addAction("🔓 清除强制优先加载")
            clear_load_first_action.triggered.connect(lambda: self.clear_force_load_first_native(clean_name))
        else:
            load_first_action = menu.addAction("⬆️ 强制优先加载")
            load_first_action.triggered.connect(lambda: self.set_force_load_first_native(clean_name))

        menu.exec(checkbox.mapToGlobal(position))


    def set_force_load_last(self, mod_name: str):
        """设置mod强制最后加载（临时状态）"""
        # 添加到强制最后加载集合
        self.force_load_last_mods.add(mod_name)

    def clear_force_load_last(self, mod_name: str):
        """清除mod的强制最后加载设置（临时状态）"""
        self.force_load_last_mods.discard(mod_name)

    def set_force_load_first_native(self, dll_name: str):
        """设置DLL强制优先加载（临时状态）"""
        # 添加到强制优先加载集合
        self.force_load_first_dlls.add(dll_name)

    def clear_force_load_first_native(self, dll_name: str):
        """清除DLL强制优先加载（临时状态）"""
        self.force_load_first_dlls.discard(dll_name)

    def save_preset(self):
        """保存预设方案"""
        try:
            # 获取基本信息
            name = self.name_edit.text().strip()
            description = self.desc_edit.toPlainText().strip()

            if not name:
                self.show_message("错误", "请输入方案名称")
                return

            # 获取选择的图标
            selected_icon_id = self.icon_group.checkedId()
            icons = ["🎮", "🌙", "⚔️", "🛡️", "🔥", "⭐", "💎", "🚀", "🎯", "🏆"]
            selected_icon = icons[selected_icon_id] if selected_icon_id >= 0 else "🎮"

            # 获取选择的mod包
            selected_packages = []
            for checkbox in self.packages_checkboxes:
                if checkbox.isChecked():
                    selected_packages.append(checkbox.objectName())

            # 获取选择的DLL
            selected_natives = []
            for checkbox in self.natives_checkboxes:
                if checkbox.isChecked():
                    selected_natives.append(checkbox.objectName())

            if not selected_packages and not selected_natives:
                self.show_message("错误", "请至少选择一个mod包或DLL文件")
                return

            # 生成配置文件内容
            config_content = self.generate_config_content(name, description, selected_icon, selected_packages, selected_natives)

            # 保存到文件
            import os
            from pathlib import Path

            list_dir = Path("Mods/list")
            list_dir.mkdir(exist_ok=True)

            # 确定文件路径
            if self.editing_file:
                # 编辑模式：使用原文件路径
                file_path = self.editing_file
            else:
                # 新建模式：使用用户输入的文件名或生成文件名
                filename_input = self.filename_edit.text().strip()
                if filename_input:
                    # 确保文件名以.me3结尾
                    if not filename_input.endswith('.me3'):
                        filename_input += '.me3'
                    filename = filename_input
                else:
                    # 如果没有输入文件名，根据方案名称生成
                    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_name = safe_name.replace(' ', '_')
                    filename = f"{safe_name}.me3"
                file_path = list_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            if self.editing_file:
                self.show_message("成功", f"预设方案已更新: {file_path.name}")
                # 重置编辑状态
                self.editing_file = None
                self.save_btn.setText("保存方案")
                # 刷新管理列表
                self.load_existing_presets()
                # 发出信号通知主页面刷新
                self.presets_changed.emit()
                # 切换到管理选项卡
                self.tab_widget.setCurrentIndex(1)
            else:
                self.show_message("成功", f"预设方案已保存到: {file_path}")
                # 发出信号通知主页面刷新
                self.presets_changed.emit()
                self.accept()

        except Exception as e:
            self.show_message("错误", f"保存失败: {e}")

    def generate_config_content(self, name, description, icon, packages, natives):
        """生成配置文件内容"""
        lines = []
        lines.append(f"# 方案名称: {icon} {name}")
        lines.append(f"# 描述: {description}")
        lines.append(f"# 图标: {icon}")
        lines.append('profileVersion = "v1"')
        lines.append("")

        # 添加mod包配置
        if packages:
            lines.append("# Mod包配置")

            # 处理强制最后加载的mod
            force_last_mod = None
            if hasattr(self, 'force_load_last_mods') and self.force_load_last_mods:
                # 只取第一个强制最后加载的mod（确保唯一性）
                for package in packages:
                    clean_package = package.replace(" (外部)", "")
                    if clean_package in self.force_load_last_mods:
                        force_last_mod = clean_package
                        break

            # 先添加非强制最后加载的mod
            other_packages = []
            for package in packages:
                clean_package = package.replace(" (外部)", "")
                if clean_package != force_last_mod:
                    other_packages.append(clean_package)
                    lines.append(f'[[packages]]')
                    lines.append(f'path = "../{clean_package}"')
                    lines.append("")

            # 最后添加强制最后加载的mod（带依赖）
            if force_last_mod:
                lines.append(f'[[packages]]')
                lines.append(f'path = "../{force_last_mod}"')
                if other_packages:
                    # 添加load_after依赖
                    load_after_list = []
                    for other_pkg in other_packages:
                        load_after_list.append(f'{{id = "{other_pkg}", optional = true}}')
                    lines.append(f'load_after = [{", ".join(load_after_list)}]')
                lines.append("")

        # 添加DLL配置（自动排序确保nighter.dll在nrsc.dll之前）
        if natives:
            lines.append("# Native DLL配置")

            # 对DLL进行排序，确保nighter.dll始终在nrsc.dll之前
            sorted_natives = self.sort_dlls_for_loading(natives)

            # 处理强制优先加载的DLL
            force_first_dlls = set()
            if hasattr(self, 'force_load_first_dlls'):
                force_first_dlls = self.force_load_first_dlls

            for native in sorted_natives:
                # 移除 (外部) 标记
                clean_native = native.replace(" (外部)", "")
                lines.append(f'[[natives]]')
                if "/" in clean_native:
                    # 子文件夹中的DLL
                    lines.append(f'path = "../{clean_native}"')
                else:
                    # 根目录下的DLL
                    lines.append(f'path = "../{clean_native}"')

                # 添加特定的DLL依赖关系（确保nighter.dll在nrsc.dll之前）
                if clean_native.endswith("nighter.dll") or "nighter.dll" in clean_native:
                    # 检查是否有nrsc.dll
                    has_nrsc = any("nrsc.dll" in n.replace(" (外部)", "") for n in sorted_natives)
                    if has_nrsc:
                        lines.append('load_before = [{id = "nrsc.dll", optional = false}]')

                # 如果是强制优先加载的DLL，添加load_before依赖
                elif clean_native in force_first_dlls:
                    other_dlls = []
                    for other_native in sorted_natives:
                        other_clean = other_native.replace(" (外部)", "")
                        if other_clean != clean_native:
                            other_dlls.append(other_clean)

                    if other_dlls:
                        load_before_list = []
                        for other_dll in other_dlls:
                            load_before_list.append(f'{{id = "{other_dll}", optional = true}}')
                        lines.append(f'load_before = [{", ".join(load_before_list)}]')

                lines.append("")

        return "\n".join(lines)

    def sort_dlls_for_loading(self, natives):
        """对DLL进行排序，确保特定的加载顺序"""
        if not natives:
            return natives

        # 定义特定的DLL优先级顺序
        priority_order = {
            'nighter.dll': 1,  # nighter.dll最高优先级
            'nrsc.dll': 2,     # nrsc.dll次优先级
        }

        def get_dll_priority(native):
            """获取DLL的优先级"""
            # 移除 (外部) 标记
            clean_native = native.replace(" (外部)", "")

            # 提取DLL文件名
            if "/" in clean_native:
                dll_name = clean_native.split("/")[-1]
            else:
                dll_name = clean_native

            # 检查是否匹配特定DLL
            for priority_dll, priority in priority_order.items():
                if dll_name.endswith(priority_dll) or priority_dll in dll_name:
                    return priority

            # 其他DLL使用默认优先级
            return 999

        # 按优先级排序
        sorted_natives = sorted(natives, key=get_dll_priority)

        return sorted_natives

    def load_existing_presets(self):
        """加载现有预设方案 - 卡片布局"""
        try:
            from pathlib import Path

            # 清空现有卡片
            for i in reversed(range(self.presets_layout.count())):
                child = self.presets_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)

            list_dir = Path("Mods/list")
            if not list_dir.exists():
                # 显示空状态
                empty_label = QLabel("📁 Mods/list 目录不存在")
                empty_label.setStyleSheet("""
                    QLabel {
                        color: #6c7086;
                        font-size: 14px;
                        text-align: center;
                        background-color: transparent;
                        border: none;
                        margin: 20px;
                        padding: 20px;
                    }
                """)
                empty_label.setAlignment(Qt.AlignCenter)
                self.presets_layout.addWidget(empty_label)
                return

            # 扫描.me3文件
            preset_files = list(list_dir.glob("*.me3"))

            if len(preset_files) == 0:
                # 显示空状态
                empty_label = QLabel("📋 暂无预设方案\n\n点击 '创建预设' 选项卡开始创建")
                empty_label.setStyleSheet("""
                    QLabel {
                        color: #6c7086;
                        font-size: 14px;
                        text-align: center;
                        background-color: transparent;
                        border: none;
                        margin: 20px;
                        padding: 20px;
                        line-height: 1.6;
                    }
                """)
                empty_label.setAlignment(Qt.AlignCenter)
                self.presets_layout.addWidget(empty_label)
                return

            # 添加预设卡片
            for preset_file in preset_files:
                preset_card = self.create_manage_preset_card(preset_file)
                self.presets_layout.addWidget(preset_card)

            # 🔧 修复：移除弹性空间，避免刷新时卡片向下移动

        except Exception as e:
            print(f"加载现有预设失败: {e}")
            # 显示错误状态
            error_label = QLabel(f"❌ 加载失败: {str(e)}")
            error_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 14px;
                    text-align: center;
                    background-color: transparent;
                    border: none;
                    margin: 20px;
                    padding: 20px;
                }
            """)
            error_label.setAlignment(Qt.AlignCenter)
            self.presets_layout.addWidget(error_label)

    def create_manage_preset_card(self, preset_file):
        """创建管理预设卡片 - 类似快速启动风格"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 0.5px solid #313244;
                border-radius: 6px;
                padding: 2px;
                min-height: 65px;
            }
            QFrame:hover {
                border-color: #45475a;
                background-color: #252537;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 解析预设文件获取信息
        preset_info = self.parse_preset_file(preset_file)

        # 顶部：标题、文件名和按钮
        top_layout = QHBoxLayout()

        # 标题
        title_text = f"{preset_info['icon']} {preset_info['name']}"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 15px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        top_layout.addWidget(title_label)

        # 文件名
        file_label = QLabel(preset_file.name)
        file_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 11px;
                font-family: monospace;
                background-color: transparent;
                border: none;
                margin: 0px 8px 0px 8px;
                padding: 0px;
            }
        """)
        top_layout.addWidget(file_label)

        top_layout.addStretch()

        # 操作按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(6)

        # 编辑按钮
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #7aa2f7;
            }
            QPushButton:pressed {
                background-color: #6c7ce0;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_preset(preset_file))
        buttons_layout.addWidget(edit_btn)

        # 预览按钮
        preview_btn = QPushButton("👁️ 预览")
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c991;
            }
        """)
        preview_btn.clicked.connect(lambda: self.preview_preset(preset_file))
        buttons_layout.addWidget(preview_btn)

        # 删除按钮
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #e78284;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_preset(preset_file))
        buttons_layout.addWidget(delete_btn)

        top_layout.addLayout(buttons_layout)

        layout.addLayout(top_layout)

        # 中部：描述
        description_label = QLabel(preset_info['description'])
        description_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                line-height: 1.4;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        card.setLayout(layout)
        return card

    def parse_preset_file(self, preset_file):
        """解析预设文件获取基本信息"""
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                content = f.read()

            info = {
                'name': '未知方案',
                'description': '无描述',
                'icon': '🎮'
            }

            for line in content.split('\n'):
                if line.startswith('# 方案名称:'):
                    parts = line.split(':', 1)[1].strip().split(' ', 1)
                    if len(parts) >= 2:
                        info['icon'] = parts[0]
                        info['name'] = parts[1]
                elif line.startswith('# 描述:'):
                    info['description'] = line.split(':', 1)[1].strip()

            return info

        except Exception as e:
            print(f"解析预设文件失败: {e}")
            return {'name': '解析失败', 'description': '无法读取文件', 'icon': '❌'}

    def edit_preset(self, preset_file):
        """编辑预设方案"""
        try:
            # 解析现有预设文件
            preset_data = self.parse_preset_file_detailed(preset_file)

            # 切换到创建选项卡
            self.tab_widget.setCurrentIndex(0)

            # 填充表单数据
            self.name_edit.setText(preset_data['name'])
            self.desc_edit.setPlainText(preset_data['description'])
            # 文件名去掉.me3扩展名
            filename_without_ext = preset_file.name.replace('.me3', '') if preset_file.name.endswith('.me3') else preset_file.name
            self.filename_edit.setText(filename_without_ext)

            # 设置图标
            icons = ["🎮", "🌙", "⚔️", "🛡️", "🔥", "⭐", "💎", "🚀", "🎯", "🏆"]
            if preset_data['icon'] in icons:
                icon_index = icons.index(preset_data['icon'])
                self.icon_buttons[icon_index].setChecked(True)

            # 设置mod选择
            self.set_mod_selections(preset_data['packages'], preset_data['natives'])

            # 恢复强制加载状态
            self.force_load_last_mods = preset_data.get('force_load_last_mods', set())
            self.force_load_first_dlls = preset_data.get('force_load_first_dlls', set())

            # 保存当前编辑的文件路径
            self.editing_file = preset_file

            # 更新保存按钮文本
            self.save_btn.setText("更新方案")

            self.show_message("提示", f"已加载预设方案: {preset_data['name']}\n请在'创建预设'选项卡中修改")

        except Exception as e:
            self.show_message("错误", f"加载预设失败: {e}")

    def preview_preset(self, preset_file):
        """预览预设方案"""
        try:
            # 解析预设文件
            preset_data = self.parse_preset_file_detailed(preset_file)

            # 切换到预览选项卡
            self.tab_widget.setCurrentIndex(2)  # 预览选项卡是第3个（索引2）

            # 更新预设信息
            info_text = f"""
📁 文件名: {preset_file.name}
🎮 方案名称: {preset_data['icon']} {preset_data['name']}
📝 描述: {preset_data['description']}
📦 Mod包数量: {len(preset_data['packages'])}
🔧 DLL数量: {len(preset_data['natives'])}
⚡ 强制最后加载: {len(preset_data.get('force_load_last_mods', set()))} 个
🚀 强制优先加载: {len(preset_data.get('force_load_first_dlls', set()))} 个
            """.strip()
            self.preview_info_label.setText(info_text)

            # 读取并显示配置文件内容
            with open(preset_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.preview_content.setPlainText(content)

        except Exception as e:
            self.show_message("错误", f"预览预设失败: {e}")

    def parse_preset_file_detailed(self, preset_file):
        """详细解析预设文件"""
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                content = f.read()

            data = {
                'name': '未知方案',
                'description': '无描述',
                'icon': '🎮',
                'packages': [],
                'natives': [],
                'force_load_last_mods': set(),
                'force_load_first_dlls': set()
            }

            lines = content.split('\n')
            current_section = None
            current_item_path = None

            for line in lines:
                line = line.strip()

                if line.startswith('# 方案名称:'):
                    parts = line.split(':', 1)[1].strip().split(' ', 1)
                    if len(parts) >= 2:
                        data['icon'] = parts[0]
                        data['name'] = parts[1]
                elif line.startswith('# 描述:'):
                    data['description'] = line.split(':', 1)[1].strip()
                elif line.startswith('[[packages]]'):
                    current_section = 'packages'
                    current_item_path = None
                elif line.startswith('[[natives]]'):
                    current_section = 'natives'
                    current_item_path = None
                elif line.startswith('path = '):
                    if current_section:
                        # 提取路径，移除引号和../前缀
                        path = line.split('=', 1)[1].strip().strip('"').replace('../', '')
                        data[current_section].append(path)
                        current_item_path = path
                elif line.startswith('load_after = ') and current_section == 'packages' and current_item_path:
                    # 检查是否是强制最后加载（包含多个其他mod的依赖）
                    if '[' in line and '{' in line:
                        data['force_load_last_mods'].add(current_item_path)
                elif line.startswith('load_before = ') and current_section == 'natives' and current_item_path:
                    # 检查是否是强制优先加载或特定顺序
                    if '[' in line and '{' in line:
                        # 如果是nighter.dll对nrsc.dll的依赖，不算强制优先加载
                        if not (current_item_path.endswith('nighter.dll') and 'nrsc.dll' in line):
                            data['force_load_first_dlls'].add(current_item_path)

            return data

        except Exception as e:
            print(f"详细解析预设文件失败: {e}")
            return {
                'name': '解析失败',
                'description': '无法读取文件',
                'icon': '❌',
                'packages': [],
                'natives': [],
                'force_load_last_mods': set(),
                'force_load_first_dlls': set()
            }

    def set_mod_selections(self, packages, natives):
        """设置mod选择状态"""
        try:
            # 清空所有选择
            for checkbox in self.packages_checkboxes:
                checkbox.setChecked(False)
            for checkbox in self.natives_checkboxes:
                checkbox.setChecked(False)

            # 设置packages选择
            for package in packages:
                for checkbox in self.packages_checkboxes:
                    # 处理可能的 (外部) 标记
                    checkbox_name = checkbox.objectName().replace(" (外部)", "")
                    if checkbox_name == package:
                        checkbox.setChecked(True)
                        break

            # 设置natives选择
            for native in natives:
                for checkbox in self.natives_checkboxes:
                    # 处理可能的 (外部) 标记
                    checkbox_name = checkbox.objectName().replace(" (外部)", "")
                    if checkbox_name == native:
                        checkbox.setChecked(True)
                        break

        except Exception as e:
            print(f"设置mod选择失败: {e}")

    def on_tab_changed(self, index):
        """选项卡切换处理"""
        if index == 0:  # 创建预设选项卡
            if not self.editing_file:
                # 如果不是编辑模式，重置表单
                self.reset_create_form()
        elif index == 1:  # 管理预设选项卡
            # 刷新预设列表
            self.load_existing_presets()

    def reset_create_form(self):
        """重置创建表单"""
        try:
            # 清空输入框
            self.name_edit.clear()
            self.desc_edit.clear()

            # 重置图标选择
            if self.icon_buttons:
                self.icon_buttons[0].setChecked(True)

            # 清空mod选择
            for checkbox in self.packages_checkboxes:
                checkbox.setChecked(False)
            for checkbox in self.natives_checkboxes:
                checkbox.setChecked(False)

            # 重置编辑状态
            self.editing_file = None
            self.save_btn.setText("保存方案")

        except Exception as e:
            print(f"重置表单失败: {e}")

    def delete_preset(self, preset_file):
        """删除预设方案"""
        try:
            from PySide6.QtWidgets import QMessageBox

            # 创建自定义无边框确认对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认删除")
            msg_box.setText(f"确定要删除预设方案 '{preset_file.name}' 吗？\n此操作不可撤销！")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)

            # 设置无边框
            msg_box.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

            # 设置样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    border: 2px solid #f38ba8;
                    border-radius: 8px;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    min-width: 60px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #74c7ec;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #7287fd;
                }
            """)

            reply = msg_box.exec()

            if reply == QMessageBox.Yes:
                preset_file.unlink()
                self.load_existing_presets()  # 刷新列表
                self.presets_changed.emit()  # 发出信号通知主页面刷新
                self.show_message("成功", f"已删除预设方案: {preset_file.name}")

        except Exception as e:
            self.show_message("错误", f"删除失败: {e}")

    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖拽"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def show_message(self, title, message):
        """显示消息对话框"""
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        # 设置无边框
        msg_box.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #89b4fa;
                border-radius: 8px;
                padding: 10px;
            }
            QMessageBox QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #74c7ec;
            }
            QMessageBox QPushButton:pressed {
                background-color: #7287fd;
            }
        """)
        msg_box.exec()
