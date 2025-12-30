"""
Mod配置页面
游戏模组管理和ME3配置
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGroupBox, QListWidget,
                               QListWidgetItem, QCheckBox, QLineEdit, QTextEdit,
                               QSplitter, QScrollArea, QComboBox, QFileDialog,
                               QMenu, QApplication, QDialog)
from PySide6.QtCore import Qt, Signal, QTimer, QProcess, QThread
from .base_page import BasePage
from ...config.mod_config_manager import ModConfigManager
from ...config.config_manager import ConfigManager
from ...i18n.manager import TranslationManager, t
import os
from pathlib import Path


class ModGameLaunchThread(QThread):
    """Mod配置页面异步游戏启动线程"""

    # 定义信号
    status_update = Signal(str, str)  # 状态消息, 状态类型(success/error/info)
    launch_completed = Signal(bool, str, str)  # 启动完成, 成功状态, 消息, 状态类型

    def __init__(self, mod_manager, config_manager):
        super().__init__()
        self.mod_manager = mod_manager
        self.config_manager = config_manager

    def run(self):
        """在后台线程中执行启动流程（智能分阶段显示）"""
        try:
            # 检查游戏路径
            game_path = self.config_manager.get_game_path()
            if not game_path or not self.config_manager.validate_game_path():
                self.launch_completed.emit(False, t("mods_page.launch_process.game_path_not_configured"), "error")
                return

            # 检查ME3可执行文件
            me3_exe = self.mod_manager.get_me3_executable_path()
            if not me3_exe:
                self.launch_completed.emit(False, t("mods_page.launch_process.me3_not_found"), "error")
                return

            # === 简洁连贯的启动流程 ===

            # 保存配置并显示状态
            self.status_update.emit(t("mods_page.launch_process.saving_config"), "info")
            if not self.mod_manager.save_config():
                self.launch_completed.emit(False, t("mods_page.launch_process.save_config_failed"), "error")
                return
            self.msleep(300)  # 让用户看到保存过程

            # 创建启动脚本
            self.status_update.emit(t("mods_page.launch_process.creating_script"), "info")
            bat_path = self._create_launch_bat_script(me3_exe, game_path, "current.bat")
            if not bat_path:
                self.launch_completed.emit(False, t("mods_page.launch_process.create_script_failed"), "error")
                return
            self.msleep(300)  # 让用户看到创建过程

            # 清理冲突进程
            self.status_update.emit(t("mods_page.launch_process.cleaning_processes"), "info")
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

            # 启动游戏
            self.status_update.emit(t("mods_page.launch_process.launching_game"), "info")
            from src.utils.dll_manager import safe_launch_game
            safe_launch_game(str(bat_path))

            # 让用户看到启动过程（400ms）
            self.msleep(400)

            self.launch_completed.emit(True, t("mods_page.launch_process.launch_success"), "success")

        except Exception as e:
            self.launch_completed.emit(False, t("mods_page.launch_process.launch_failed").format(error=str(e)), "error")

    def _create_launch_bat_script(self, me3_exe: str, game_path: str, bat_name: str) -> str:
        """创建启动bat脚本"""
        try:
            # 确保me3p/start目录存在
            start_dir = Path("me3p/start")
            start_dir.mkdir(parents=True, exist_ok=True)

            # 获取绝对路径
            config_file = str(Path(self.mod_manager.config_file).resolve())
            game_path = str(Path(game_path).resolve())

            # 读取启动参数
            launch_params = ["--skip-steam-init", "--online"]  # 默认参数
            try:
                from .quick_launch_page import LaunchParamsConfigDialog
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
                f'-p "{config_file}"'
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


class ModsPage(BasePage):
    """Mod配置页面"""

    # 定义信号：当mod配置发生变化时发出
    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(t("mods_page.page_title"), parent)
        self.mod_manager = ModConfigManager()
        self.config_manager = ConfigManager()
        self.setup_content()
        self.load_mods()

    def setup_content(self):
        """设置页面内容"""
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #313244;
                width: 2px;
            }
        """)

        # 左侧：mod管理区域
        self.setup_mod_management(main_splitter)

        # 右侧：配置预览和启动区域
        self.setup_config_preview(main_splitter)

        # 设置分割器比例 - 调整为更平衡的布局
        main_splitter.setSizes([600, 200])

        self.add_content(main_splitter)

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

    def setup_mod_management(self, parent):
        """设置mod管理区域"""
        left_widget = QFrame()
        left_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                margin: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        layout.setSpacing(8)  # 减少间距

        # 标题
        self.mod_management_title = QLabel(t("mods_page.section.mod_management"))
        self.mod_management_title.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;  /* 从18px减少到16px */
                font-weight: bold;
                margin-bottom: 3px;  /* 从10px减少到3px */
                padding: 2px 0;  /* 减少内边距 */
            }
        """)
        layout.addWidget(self.mod_management_title)

        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 扫描按钮
        self.scan_btn = QPushButton(t("mods_page.button.scan_mods"))
        self.scan_btn.setFixedHeight(35)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.scan_btn.clicked.connect(self.scan_mods)
        button_layout.addWidget(self.scan_btn)

        # 启动游戏按钮
        self.launch_btn = QPushButton(t("mods_page.button.launch_game"))
        self.launch_btn.setFixedHeight(35)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_game)
        button_layout.addWidget(self.launch_btn)

        layout.addLayout(button_layout)

        # 创建左右分割的mod列表区域
        mods_splitter = QSplitter(Qt.Horizontal)
        mods_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #313244;
                width: 2px;
            }
        """)

        # 左侧：Mod包区域
        packages_widget = QFrame()
        packages_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 6px;
                margin: 2px;
            }
        """)
        packages_layout = QVBoxLayout()
        packages_layout.setContentsMargins(10, 10, 10, 10)
        packages_layout.setSpacing(8)

        # Mod包标题
        self.packages_label = QLabel(t("mods_page.section.mod_packages"))
        self.packages_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        packages_layout.addWidget(self.packages_label)

        # Mod包列表
        self.packages_list = QListWidget()
        self.packages_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packages_list.customContextMenuRequested.connect(self.show_package_context_menu)
        self.packages_list.setStyleSheet("""
            QListWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        packages_layout.addWidget(self.packages_list, 1)  # 设置stretch factor为1，让列表占用所有可用空间

        # 添加外部Mod按钮
        self.add_external_package_btn = QPushButton(t("mods_page.button.add_external_mod"))
        self.add_external_package_btn.setFixedHeight(30)
        self.add_external_package_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.add_external_package_btn.clicked.connect(self.add_external_package)
        packages_layout.addWidget(self.add_external_package_btn)

        packages_widget.setLayout(packages_layout)
        mods_splitter.addWidget(packages_widget)

        # 右侧：Native DLL区域
        natives_widget = QFrame()
        natives_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 6px;
                margin: 2px;
            }
        """)
        natives_layout = QVBoxLayout()
        natives_layout.setContentsMargins(10, 10, 10, 10)
        natives_layout.setSpacing(8)

        # Native DLL标题
        self.natives_label = QLabel(t("mods_page.section.native_dll"))
        self.natives_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        natives_layout.addWidget(self.natives_label)

        # Native DLL列表
        self.natives_list = QListWidget()
        self.natives_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.natives_list.customContextMenuRequested.connect(self.show_native_context_menu)
        self.natives_list.setStyleSheet("""
            QListWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
            QListWidget::item:selected {
                background-color: #a6e3a1;
                color: #1e1e2e;
            }
        """)
        natives_layout.addWidget(self.natives_list, 1)  # 设置stretch factor为1，让列表占用所有可用空间

        # 添加外部DLL按钮
        self.add_external_native_btn = QPushButton(t("mods_page.button.add_external_dll"))
        self.add_external_native_btn.setFixedHeight(30)
        self.add_external_native_btn.setStyleSheet("""
            QPushButton {
                background-color: #f9e2af;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #f2d5aa;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.add_external_native_btn.clicked.connect(self.add_external_native)
        natives_layout.addWidget(self.add_external_native_btn)

        natives_widget.setLayout(natives_layout)
        mods_splitter.addWidget(natives_widget)

        # 设置左右分割比例（Mod包:Native DLL = 1:1）
        mods_splitter.setSizes([300, 300])

        layout.addWidget(mods_splitter, 1)  # 设置stretch factor为1，让mod列表区域占用所有可用空间

        left_widget.setLayout(layout)
        parent.addWidget(left_widget)

    def setup_config_preview(self, parent):
        """设置配置预览区域"""
        right_widget = QFrame()
        right_widget.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                margin: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        layout.setSpacing(8)  # 减少间距

        # 标题
        self.config_preview_title = QLabel(t("mods_page.section.config_preview"))
        self.config_preview_title.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;  /* 从18px减少到16px */
                font-weight: bold;
                margin-bottom: 3px;  /* 从10px减少到3px */
                padding: 2px 0;  /* 减少内边距 */
            }
        """)
        layout.addWidget(self.config_preview_title)

        # 配置摘要
        self.config_summary_label = QLabel(t("mods_page.label.config_summary_empty"))
        self.config_summary_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 13px;
                padding: 10px;
                background-color: #313244;
                border-radius: 6px;
                border-left: 3px solid #89b4fa;
            }
        """)
        layout.addWidget(self.config_summary_label)

        # 配置文件预览
        self.config_file_preview_label = QLabel(t("mods_page.section.config_file_preview"))
        self.config_file_preview_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.config_file_preview_label)

        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setStyleSheet("""
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.config_preview, 1)  # 设置stretch factor为1，让配置预览占用所有可用空间

        # 操作按钮
        button_layout = QHBoxLayout()

        # 保存配置按钮
        self.save_btn = QPushButton(t("mods_page.button.save_config"))
        self.save_btn.setFixedHeight(35)
        self.save_btn.setStyleSheet("""
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
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)

        # 清除配置按钮
        self.clear_btn = QPushButton(t("mods_page.button.clear_config"))
        self.clear_btn.setFixedHeight(35)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_all_mods)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 12px;
                padding: 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #a6e3a1;
                margin: 5px 0;
            }
        """)
        layout.addWidget(self.status_label)

        right_widget.setLayout(layout)
        parent.addWidget(right_widget)

    def load_mods(self):
        """加载mod配置"""
        # 加载现有配置
        self.mod_manager.load_config()

        # 扫描可用mods
        self.scan_mods()

        # 更新预览
        self.update_config_preview()

    def scan_mods(self):
        """扫描Mods目录"""
        # 首先清理外部mod列表中错误的内部mod条目
        internal_cleaned = self.mod_manager.cleanup_internal_mods_from_external_list()
        internal_cleaned_count = len(internal_cleaned['packages']) + len(internal_cleaned['natives'])

        if internal_cleaned_count > 0:
            self.show_status(t("mods_page.status.auto_cleaned_internal_mods").format(count=internal_cleaned_count), "success")

        # 检查外部mod存在性并获取缺失列表
        missing_mods = self.mod_manager.get_missing_external_mods()

        # 如果有缺失的外部mod，自动清理
        if missing_mods['packages'] or missing_mods['natives']:
            missing_count = len(missing_mods['packages']) + len(missing_mods['natives'])
            # 自动清理缺失的外部mod
            cleaned = self.mod_manager.cleanup_missing_external_mods()
            cleaned_count = len(cleaned['packages']) + len(cleaned['natives'])

            if cleaned_count > 0:
                self.show_status(t("mods_page.status.auto_cleaned_external_mods").format(count=cleaned_count), "success")
            else:
                self.show_status(t("mods_page.status.detected_missing_mods_clean_failed").format(count=missing_count), "error")

        available_mods = self.mod_manager.scan_mods_directory()

        # 更新包列表
        self.packages_list.clear()
        for package_name in available_mods["packages"]:
            item = QListWidgetItem()

            # 检查是否已在配置中
            clean_name = package_name.replace(" (外部)", "") if package_name.endswith(" (外部)") else package_name
            is_external = package_name.endswith(" (外部)")

            if is_external:
                # 对于外部mod包，需要通过完整路径匹配
                external_path = self.mod_manager.external_packages.get(clean_name)
                is_enabled = any(pkg.source == external_path and pkg.enabled
                               for pkg in self.mod_manager.packages) if external_path else False
            else:
                # 对于内部mod包，直接通过包名匹配
                is_enabled = any(pkg.id == package_name and pkg.enabled
                               for pkg in self.mod_manager.packages)

            # 创建复选框（包含备注信息）
            comment = self.mod_manager.get_mod_comment(clean_name)

            # 检查是否为缺失的外部mod
            is_missing = is_external and clean_name in missing_mods['packages']

            if is_missing:
                display_text = f"❌ {package_name} [缺失]"
            else:
                display_text = f"📁 {package_name}"

            if comment:
                display_text += f" - {comment}"

            checkbox = QCheckBox(display_text)
            checkbox.setChecked(is_enabled)

            # 为缺失的外部mod设置特殊样式
            if is_missing:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #f38ba8;
                        font-size: 13px;
                        spacing: 8px;
                        font-style: italic;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #f38ba8;
                        background-color: #313244;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #f38ba8;
                        border-color: #f38ba8;
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #eba0ac;
                    }
                """)
                # 缺失的mod不能被启用
                checkbox.setEnabled(False)
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #cdd6f4;
                        font-size: 13px;
                        spacing: 8px;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #45475a;
                        background-color: #313244;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #89b4fa;
                        border-color: #89b4fa;
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #74c7ec;
                    }
                """)
            checkbox.stateChanged.connect(
                lambda state, name=package_name: self.toggle_package(name, state == 2)
            )

            self.packages_list.addItem(item)
            self.packages_list.setItemWidget(item, checkbox)

        # 更新DLL列表
        self.natives_list.clear()
        for dll_name in available_mods["natives"]:
            item = QListWidgetItem()

            # 检查是否已在配置中
            clean_name = dll_name.replace(" (外部)", "") if dll_name.endswith(" (外部)") else dll_name
            is_external = dll_name.endswith(" (外部)")

            if is_external:
                # 对于外部DLL，需要通过完整路径匹配
                external_path = self.mod_manager.external_natives.get(clean_name)
                is_enabled = any(native.path == external_path and native.enabled
                               for native in self.mod_manager.natives) if external_path else False
            else:
                # 对于内部DLL，直接通过文件名匹配
                is_enabled = any(native.path == dll_name and native.enabled
                               for native in self.mod_manager.natives)

            # 创建复选框（包含备注信息）
            # 🔧 修复：对于内部DLL，备注key应该使用完整路径，而不是显示名称
            comment_key = clean_name  # 使用完整路径作为备注key
            comment = self.mod_manager.get_native_comment(comment_key)

            # 检查是否为缺失的外部DLL
            is_missing = is_external and clean_name in missing_mods['natives']

            # 提取DLL文件名（去除路径）
            display_dll_name = dll_name
            if "/" in dll_name and not dll_name.endswith(" (外部)"):
                # 对于内部DLL，提取文件名部分
                display_dll_name = dll_name.split("/")[-1]
            elif dll_name.endswith(" (外部)"):
                # 对于外部DLL，保持原样
                display_dll_name = dll_name

            if is_missing:
                display_text = f"❌ {display_dll_name} [缺失]"
            else:
                display_text = f"🔧 {display_dll_name}"
                
                # 检查是否启用了预加载（仅对nrsc.dll）
                if clean_name.endswith("nrsc.dll") or "nrsc.dll" in clean_name:
                    is_preload = self.mod_manager.get_native_load_early(clean_name)
                    if is_preload:
                        display_text = f"🚀 {display_dll_name} [{t('mods_page.label.preload')}]"

            if comment:
                display_text += f" - {comment}"

            checkbox = QCheckBox(display_text)
            checkbox.setChecked(is_enabled)

            # 为缺失的外部DLL设置特殊样式
            if is_missing:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #f38ba8;
                        font-size: 13px;
                        spacing: 8px;
                        font-style: italic;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #f38ba8;
                        background-color: #313244;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #f38ba8;
                        border-color: #f38ba8;
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #eba0ac;
                    }
                """)
                # 缺失的DLL不能被启用
                checkbox.setEnabled(False)
            else:
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #cdd6f4;
                        font-size: 13px;
                        spacing: 8px;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 3px;
                        border: 2px solid #45475a;
                        background-color: #313244;
                    }
                    QCheckBox::indicator:checked {
                        background-color: #a6e3a1;
                        border-color: #a6e3a1;
                    }
                    QCheckBox::indicator:checked:hover {
                        background-color: #94e2d5;
                    }
                """)
            checkbox.stateChanged.connect(
                lambda state, name=dll_name: self.toggle_native(name, state == 2)
            )

            # 🔧 修复：将完整的DLL路径存储在item的data中，用于右键菜单
            item.setData(Qt.UserRole, clean_name)  # 存储完整路径

            self.natives_list.addItem(item)
            self.natives_list.setItemWidget(item, checkbox)

        # 更新配置预览
        self.update_config_preview()

    def toggle_package(self, package_name: str, enabled: bool):
        """切换mod包状态"""
        if enabled:
            # 添加到配置
            self.mod_manager.add_package(package_name, f"{package_name}/")
            # 新启用的mod，添加到相关依赖中
            self.mod_manager.add_to_load_dependencies(package_name, is_native=False)
        else:
            # 从配置移除
            self.mod_manager.remove_package(package_name)
            # 禁用的mod，从所有依赖中移除
            self.mod_manager.update_load_dependencies()

        # 保存配置
        self.mod_manager.save_config()
        self.update_config_preview()
        # 发出配置变化信号
        self.config_changed.emit()

    def toggle_native(self, dll_name: str, enabled: bool):
        """切换native DLL状态"""
        if enabled:
            # 添加到配置
            self.mod_manager.add_native(dll_name)
            # 新启用的DLL，添加到相关依赖中
            self.mod_manager.add_to_load_dependencies(dll_name, is_native=True)
        else:
            # 从配置移除
            self.mod_manager.remove_native(dll_name)
            # 禁用的DLL，从所有依赖中移除
            self.mod_manager.update_load_dependencies()
            
            # 如果是 nrsc.dll，清除预加载状态
            clean_name = dll_name.replace(" (外部)", "")
            if clean_name.endswith("nrsc.dll") or "nrsc.dll" in clean_name:
                self.mod_manager.set_native_load_early(clean_name, False)

        # 保存配置
        self.mod_manager.save_config()
        self.update_config_preview()
        # 重新扫描以更新显示
        self.scan_mods()
        # 发出配置变化信号
        self.config_changed.emit()

    def update_config_preview(self):
        """更新配置预览"""
        # 更新摘要
        summary = self.mod_manager.get_config_summary()
        summary_text = t("mods_page.config_preview.summary").format(
            enabled=summary['enabled_packages'],
            total=summary['total_packages'],
            enabled_dll=summary['enabled_natives'],
            total_dll=summary['total_natives']
        )
        self.config_summary_label.setText(summary_text)

        # 生成配置文件内容
        config_content = self.generate_config_content()
        self.config_preview.setPlainText(config_content)

    def generate_config_content(self) -> str:
        """生成配置文件内容"""
        lines = []
        lines.append(t("mods_page.config_preview.header_title"))
        lines.append(t("mods_page.config_preview.header_generated"))
        lines.append("")
        lines.append('profileVersion = "v1"')
        lines.append("")
        lines.append("[[supports]]")
        lines.append('game = "nightreign"')
        lines.append("")

        # 添加packages
        enabled_packages = [pkg for pkg in self.mod_manager.packages if pkg.enabled]
        if enabled_packages:
            lines.append(t("mods_page.config_preview.packages_section"))
            for package in enabled_packages:
                lines.append("[[packages]]")
                lines.append(f'id = "{package.id}"')
                # 正确转义Windows路径中的反斜杠
                source_path = package.source.replace("\\", "\\\\")
                lines.append(f'source = "{source_path}"')
                if package.load_after:
                    load_after_str = self._format_dependencies(package.load_after)
                    lines.append(f"load_after = {load_after_str}")
                if package.load_before:
                    load_before_str = self._format_dependencies(package.load_before)
                    lines.append(f"load_before = {load_before_str}")
                lines.append("")

        # 添加natives
        enabled_natives = [native for native in self.mod_manager.natives if native.enabled]
        if enabled_natives:
            lines.append(t("mods_page.config_preview.natives_section"))
            for native in enabled_natives:
                lines.append("[[natives]]")
                # 正确转义Windows路径中的反斜杠
                native_path = native.path.replace("\\", "\\\\")
                lines.append(f'path = "{native_path}"')
                if native.optional:
                    lines.append(f"optional = {str(native.optional).lower()}")
                if native.initializer:
                    lines.append(f'initializer = "{native.initializer}"')
                if native.finalizer:
                    lines.append(f'finalizer = "{native.finalizer}"')
                if native.load_after:
                    load_after_str = self._format_dependencies(native.load_after)
                    lines.append(f"load_after = {load_after_str}")
                if native.load_before:
                    load_before_str = self._format_dependencies(native.load_before)
                    lines.append(f"load_before = {load_before_str}")
                if native.load_early:
                    lines.append("load_early = true")
                lines.append("")

        return "\n".join(lines)

    def save_config(self):
        """保存配置"""
        if self.mod_manager.save_config():
            self.show_status(t("mods_page.status.config_saved"), "success")
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.config_save_failed"), "error")

    def launch_game(self):
        """启动游戏"""
        # 检查游戏路径
        game_path = self.config_manager.get_game_path()
        if not game_path or not self.config_manager.validate_game_path():
            self.show_status(t("mods_page.launch_process.game_path_not_configured"), "error")
            return

        # 检查ME3可执行文件
        me3_exe = self.mod_manager.get_me3_executable_path()
        if not me3_exe:
            self.show_status(t("mods_page.launch_process.me3_not_found"), "error")
            return

        # 保存当前配置
        if not self.mod_manager.save_config():
            self.show_status(t("mods_page.launch_process.save_config_failed"), "error")
            return

        # 显示启动状态
        self.show_status(t("mods_page.launch_process.launching_game"), "info")

        # 创建异步启动线程
        self.launch_thread = ModGameLaunchThread(self.mod_manager, self.config_manager)

        # 连接信号
        self.launch_thread.status_update.connect(self._on_launch_status_update)
        self.launch_thread.launch_completed.connect(self._on_launch_completed)

        # 启动线程
        self.launch_thread.start()


    def _on_launch_status_update(self, message, status_type):
        """处理启动状态更新"""
        self.show_status(message, status_type)

    def _on_launch_completed(self, success, message, status_type):
        """处理启动完成"""
        self.show_status(message, status_type)

    def create_launch_bat_script(self, me3_exe: str, game_path: str, bat_name: str) -> str:
        """创建启动bat脚本"""
        try:
            # 确保me3p/start目录存在
            start_dir = Path("me3p/start")
            start_dir.mkdir(parents=True, exist_ok=True)

            # 获取绝对路径
            config_file = str(Path(self.mod_manager.config_file).resolve())
            game_path = str(Path(game_path).resolve())

            # 读取启动参数
            launch_params = ["--skip-steam-init", "--online"]  # 默认参数
            try:
                from .quick_launch_page import LaunchParamsConfigDialog
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
                f'-p "{config_file}"'
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

    def show_status(self, message: str, status_type: str = "info"):
        """显示状态信息"""
        if status_type == "success":
            color = "#a6e3a1"
        elif status_type == "error":
            color = "#f38ba8"
        elif status_type == "warning":
            color = "#fab387"
        else:  # info
            color = "#89b4fa"

        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                padding: 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid {color};
                margin: 5px 0;
            }}
        """)
        self.status_label.setVisible(True)

        # 根据消息类型设置不同的显示时长
        if status_type == "success":
            # 成功消息显示4秒
            QTimer.singleShot(4000, lambda: self.status_label.setVisible(False))
        elif status_type == "error":
            # 错误消息显示6秒
            QTimer.singleShot(6000, lambda: self.status_label.setVisible(False))
        else:
            # 其他消息显示4秒
            QTimer.singleShot(4000, lambda: self.status_label.setVisible(False))

    def clear_all_mods(self):
        """清除所有mod配置"""
        # 清除所有包和natives
        self.mod_manager.packages.clear()
        self.mod_manager.natives.clear()

        # 保存清空的配置到文件
        if self.mod_manager.save_config():
            # 更新UI显示
            self.refresh_mod_lists()

            # 更新配置预览
            self.update_config_preview()

            # 显示状态
            self.show_status(t("mods_page.status.all_mods_cleared"), "success")

            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.clear_failed"), "error")

    def refresh_mod_lists(self):
        """刷新mod列表显示状态"""
        # 更新packages列表的复选框状态
        for i in range(self.packages_list.count()):
            item = self.packages_list.item(i)
            checkbox = self.packages_list.itemWidget(item)
            if checkbox:
                checkbox.setChecked(False)

        # 更新natives列表的复选框状态
        for i in range(self.natives_list.count()):
            item = self.natives_list.item(i)
            checkbox = self.natives_list.itemWidget(item)
            if checkbox:
                checkbox.setChecked(False)

    def add_external_package(self):
        """添加外部mod包"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择外部Mod文件夹",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            folder_path_obj = Path(folder_path)
            success, message = self.mod_manager.add_external_package(folder_path)

            if success:
                self.show_status(t("mods_page.status.external_mod_added").format(mod_name=folder_path_obj.name), "success")
                # 重新扫描以更新列表
                self.scan_mods()
            else:
                self.show_status(t("mods_page.status.external_mod_add_failed").format(message=message), "error")

    def add_external_native(self):
        """添加外部DLL"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择外部DLL文件",
            "",
            "DLL文件 (*.dll);;所有文件 (*)"
        )

        if file_path:
            file_path_obj = Path(file_path)
            success, message = self.mod_manager.add_external_native(file_path)

            if success:
                self.show_status(t("mods_page.status.external_dll_added").format(dll_name=file_path_obj.name), "success")
                # 重新扫描以更新列表
                self.scan_mods()
            else:
                self.show_status(t("mods_page.status.external_dll_add_failed").format(message=message), "error")

    def show_package_context_menu(self, position):
        """显示mod包右键菜单"""
        item = self.packages_list.itemAt(position)
        if not item:
            return

        checkbox = self.packages_list.itemWidget(item)
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

        # 添加备注菜单项
        comment_action = menu.addAction(t("mods_page.context_menu.edit_note"))
        comment_action.triggered.connect(lambda checked=False: self.edit_mod_comment(clean_name, checkbox))

        # 添加强制最后加载选项
        menu.addSeparator()
        is_force_last = self.mod_manager.is_force_load_last(clean_name)
        if is_force_last:
            force_last_action = menu.addAction(t("mods_page.context_menu.cancel_force_last_load"))
            force_last_action.triggered.connect(lambda checked=False: self.clear_force_load_last(clean_name))
        else:
            force_last_action = menu.addAction(t("mods_page.context_menu.force_last_load"))
            force_last_action.triggered.connect(lambda checked=False: self.set_force_load_last(clean_name))

        # 如果是外部mod，添加移除选项
        if is_external:
            menu.addSeparator()
            remove_action = menu.addAction(t("mods_page.context_menu.remove_external_mod"))
            remove_action.triggered.connect(lambda checked=False: self.remove_external_mod(clean_name))

        menu.exec(self.packages_list.mapToGlobal(position))

    def show_native_context_menu(self, position):
        """显示DLL右键菜单"""
        item = self.natives_list.itemAt(position)
        if not item:
            return

        checkbox = self.natives_list.itemWidget(item)
        if not checkbox:
            return

        # 🔧 修复：从item的data中获取完整的DLL路径，而不是从显示文本解析
        clean_name = item.data(Qt.UserRole)
        if not clean_name:
            # 如果没有存储数据，回退到原来的解析方式
            full_text = checkbox.text().replace("🔧 ", "")
            if " - " in full_text:
                dll_name = full_text.split(" - ")[0]
            else:
                dll_name = full_text
            is_external = dll_name.endswith(" (外部)")
            clean_name = dll_name.replace(" (外部)", "") if is_external else dll_name

        is_external = clean_name in self.mod_manager.external_natives

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

        # 添加备注菜单项
        comment_action = menu.addAction(t("mods_page.context_menu.edit_note"))
        comment_action.triggered.connect(lambda checked=False: self.edit_native_comment(clean_name, checkbox))

        # 添加前置加载功能
        menu.addSeparator()

        # 检查当前是否已设置前置加载
        is_force_load_first = self.mod_manager.is_force_load_first_native(clean_name)

        if is_force_load_first:
            clear_load_first_action = menu.addAction(t("mods_page.context_menu.clear_force_priority_load"))
            clear_load_first_action.triggered.connect(lambda: self.clear_force_load_first_native(clean_name))
        else:
            load_first_action = menu.addAction(t("mods_page.context_menu.force_priority_load"))
            load_first_action.triggered.connect(lambda: self.set_force_load_first_native(clean_name))

        # 添加特定DLL的配置功能
        menu.addSeparator()

        # 检查DLL类型（支持路径格式）
        if clean_name.endswith("nrsc.dll") or "SeamlessCoop" in clean_name:
            print(f"✅ 添加 nrsc.dll 配置菜单")
            config_action = menu.addAction(t("mods_page.context_menu.config_seamlesscoop"))
            config_action.triggered.connect(lambda: self.configure_nrsc_settings())
            
            # 添加预加载选项
            is_preload = self.mod_manager.get_native_load_early(clean_name)
            if is_preload:
                cancel_preload_action = menu.addAction(t("mods_page.context_menu.cancel_preload"))
                cancel_preload_action.triggered.connect(lambda: self.toggle_nrsc_preload(clean_name, False))
            else:
                preload_action = menu.addAction(t("mods_page.context_menu.preload"))
                preload_action.triggered.connect(lambda: self.toggle_nrsc_preload(clean_name, True))
                
        elif clean_name.endswith("nighter.dll") or "nighter" in clean_name:
            print(f"✅ 添加 nighter.dll 配置菜单")
            difficulty_action = menu.addAction(t("mods_page.context_menu.nighter_settings"))
            difficulty_action.triggered.connect(lambda: self.configure_nighter_difficulty())
        else:
            print(f"ℹ️ DLL '{clean_name}' 无特殊配置选项")

        # 如果是外部DLL，添加移除选项
        if is_external:
            menu.addSeparator()
            remove_action = menu.addAction(t("mods_page.context_menu.remove_external_dll"))
            remove_action.triggered.connect(lambda checked=False: self.remove_external_dll(clean_name))

        menu.exec(self.natives_list.mapToGlobal(position))

    def edit_mod_comment(self, mod_name: str, checkbox: QCheckBox):
        """内联编辑mod备注"""
        current_comment = self.mod_manager.get_mod_comment(mod_name)

        # 创建内联编辑器
        edit_widget = QLineEdit()
        edit_widget.setText(current_comment)
        edit_widget.setPlaceholderText(t("mods_page.status.note_placeholder"))
        edit_widget.setStyleSheet("""
            QLineEdit {
                background-color: #45475a;
                border: 2px solid #89b4fa;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #74c7ec;
                background-color: #585b70;
            }
        """)

        def save_comment():
            comment = edit_widget.text().strip()
            self.mod_manager.set_mod_comment(mod_name, comment)
            self.update_mod_display(mod_name, checkbox, comment)
            edit_widget.deleteLater()
            self.show_status(t("mods_page.status.mod_note_saved").format(mod_name=mod_name), "success")

        def cancel_edit():
            edit_widget.deleteLater()
            self.show_status(t("mods_page.status.note_edit_cancelled"), "info")

        # 重写keyPressEvent来处理Escape键
        def keyPressEvent(event):
            if event.key() == Qt.Key_Escape:
                cancel_edit()
            else:
                QLineEdit.keyPressEvent(edit_widget, event)

        edit_widget.keyPressEvent = keyPressEvent
        edit_widget.returnPressed.connect(save_comment)

        # 在状态栏显示编辑提示
        self.show_status(t("mods_page.status.editing_mod_note").format(mod_name=mod_name), "info")

        # 将编辑器放在mod列表附近
        packages_rect = self.packages_list.geometry()
        edit_widget.setParent(self)
        # 放在mod列表的右侧
        edit_x = packages_rect.x() + packages_rect.width() + 10
        edit_y = packages_rect.y() + 50
        edit_widget.move(edit_x, edit_y)
        edit_widget.resize(400, 35)  # 更大的尺寸
        edit_widget.show()
        edit_widget.setFocus()
        edit_widget.selectAll()

    def edit_native_comment(self, dll_name: str, checkbox: QCheckBox):
        """内联编辑DLL备注"""
        current_comment = self.mod_manager.get_native_comment(dll_name)

        # 创建内联编辑器
        edit_widget = QLineEdit()
        edit_widget.setText(current_comment)
        edit_widget.setPlaceholderText(t("mods_page.status.note_placeholder"))
        edit_widget.setStyleSheet("""
            QLineEdit {
                background-color: #45475a;
                border: 2px solid #a6e3a1;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #94e2d5;
                background-color: #585b70;
            }
        """)

        def save_comment():
            comment = edit_widget.text().strip()
            self.mod_manager.set_native_comment(dll_name, comment)
            self.update_native_display(dll_name, checkbox, comment)
            edit_widget.deleteLater()
            self.show_status(t("mods_page.status.dll_note_saved").format(dll_name=dll_name), "success")

        def cancel_edit():
            edit_widget.deleteLater()
            self.show_status(t("mods_page.status.note_edit_cancelled"), "info")

        # 重写keyPressEvent来处理Escape键
        def keyPressEvent(event):
            if event.key() == Qt.Key_Escape:
                cancel_edit()
            else:
                QLineEdit.keyPressEvent(edit_widget, event)

        edit_widget.keyPressEvent = keyPressEvent
        edit_widget.returnPressed.connect(save_comment)

        # 在状态栏显示编辑提示
        self.show_status(t("mods_page.status.editing_dll_note").format(dll_name=dll_name), "info")

        # 将编辑器放在DLL列表附近
        natives_rect = self.natives_list.geometry()
        edit_widget.setParent(self)
        # 放在DLL列表的右侧
        edit_x = natives_rect.x() + natives_rect.width() + 10
        edit_y = natives_rect.y() + 50
        edit_widget.move(edit_x, edit_y)
        edit_widget.resize(400, 35)  # 更大的尺寸
        edit_widget.show()
        edit_widget.setFocus()
        edit_widget.selectAll()

    def update_mod_display(self, mod_name: str, checkbox: QCheckBox, comment: str):
        """更新mod显示（包含备注）"""
        is_external = mod_name in self.mod_manager.external_packages
        display_name = f"{mod_name} (外部)" if is_external else mod_name

        if comment:
            display_text = f"📁 {display_name} - {comment}"
        else:
            display_text = f"📁 {display_name}"

        checkbox.setText(display_text)
        self.show_status(t("mods_page.status.mod_note_updated").format(mod_name=mod_name), "success")

    def update_native_display(self, dll_name: str, checkbox: QCheckBox, comment: str):
        """更新DLL显示（包含备注）"""
        is_external = dll_name in self.mod_manager.external_natives

        # 提取DLL文件名（去除路径）
        if is_external:
            display_name = f"{dll_name} (外部)"
        else:
            # 对于内部DLL，只显示文件名
            display_name = dll_name.split("/")[-1] if "/" in dll_name else dll_name

        if comment:
            display_text = f"🔧 {display_name} - {comment}"
        else:
            display_text = f"🔧 {display_name}"

        checkbox.setText(display_text)
        self.show_status(t("mods_page.status.dll_note_updated").format(dll_name=dll_name), "success")

    def remove_external_mod(self, mod_name: str):
        """移除外部mod"""
        if self.mod_manager.remove_external_package(mod_name):
            # 同时从当前配置中移除
            self.mod_manager.remove_package(mod_name)
            # 重新扫描以更新列表
            self.scan_mods()
            self.show_status(t("mods_page.status.external_mod_removed").format(mod_name=mod_name), "success")
        else:
            self.show_status(t("mods_page.status.external_mod_remove_failed").format(mod_name=mod_name), "error")

    def remove_external_dll(self, dll_name: str):
        """移除外部DLL"""
        if self.mod_manager.remove_external_native(dll_name):
            # 同时从当前配置中移除
            self.mod_manager.remove_native(dll_name)
            # 重新扫描以更新列表
            self.scan_mods()
            self.show_status(t("mods_page.status.external_dll_removed").format(dll_name=dll_name), "success")
        else:
            self.show_status(t("mods_page.status.external_dll_remove_failed").format(dll_name=dll_name), "error")

    def set_force_load_last(self, mod_name: str):
        """设置mod强制最后加载"""
        success = self.mod_manager.set_force_load_last(mod_name)
        if success:
            self.show_status(t("mods_page.status.force_last_load_set").format(mod_name=mod_name), "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.force_last_load_set_failed").format(mod_name=mod_name), "error")

    def clear_force_load_last(self, mod_name: str):
        """清除mod的强制最后加载设置"""
        success = self.mod_manager.clear_force_load_last(mod_name)
        if success:
            self.show_status(t("mods_page.status.force_last_load_cancelled").format(mod_name=mod_name), "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.force_last_load_cancel_failed").format(mod_name=mod_name), "error")

    def set_force_load_first_native(self, dll_name: str):
        """设置DLL强制优先加载"""
        success = self.mod_manager.set_force_load_first_native(dll_name)
        if success:
            self.show_status(t("mods_page.status.force_priority_load_set").format(dll_name=dll_name), "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.force_priority_load_set_failed").format(dll_name=dll_name), "error")

    def clear_force_load_first_native(self, dll_name: str):
        """清除DLL强制优先加载"""
        success = self.mod_manager.clear_force_load_first_native(dll_name)
        if success:
            self.show_status(t("mods_page.status.force_priority_load_cleared").format(dll_name=dll_name), "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.force_priority_load_clear_failed").format(dll_name=dll_name), "error")

    def configure_nrsc_settings(self):
        """配置SeamlessCoop设置"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QFormLayout
        import configparser
        import os

        # 配置文件路径
        config_path = os.path.join("Mods", "SeamlessCoop", "nrsc_settings.ini")

        if not os.path.exists(config_path):
            self.show_status(t("mods_page.status.nrsc_config_not_found"), "error")
            return

        # 读取当前配置
        config = configparser.ConfigParser()
        try:
            config.read(config_path, encoding='utf-8')

            # 获取当前值
            health_scaling = config.getint('SCALING', 'health_scaling', fallback=100)
            damage_scaling = config.getint('SCALING', 'damage_scaling', fallback=100)
            posture_scaling = config.getint('SCALING', 'posture_scaling', fallback=100)

        except Exception as e:
            self.show_status(t("mods_page.status.nrsc_config_read_failed").format(error=e), "error")
            return

        # 创建无边框配置对话框
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setModal(True)
        dialog.resize(450, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }
            QSpinBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                color: #cdd6f4;
                padding: 8px;
                font-size: 14px;
            }
            QSpinBox:focus {
                border-color: #a6e3a1;
            }
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
            QPushButton#closeButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton#closeButton:hover {
                background-color: #eba0ac;
            }
        """)

        # 添加拖拽功能
        dialog.mousePressEvent = lambda event: setattr(dialog, '_drag_pos', event.globalPos() - dialog.pos()) if event.button() == Qt.LeftButton else None
        dialog.mouseMoveEvent = lambda event: dialog.move(event.globalPos() - dialog._drag_pos) if hasattr(dialog, '_drag_pos') and event.buttons() == Qt.LeftButton else None

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel(t("mods_page.dialog.seamlesscoop_title"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1;")

        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(dialog.reject)

        title_bar.addWidget(title_label)
        title_bar.addStretch()
        title_bar.addWidget(close_button)
        layout.addLayout(title_bar)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #45475a; margin: 10px 0;")
        layout.addWidget(separator)

        # 表单布局
        form_layout = QFormLayout()

        # 生命值缩放
        health_spinbox = QSpinBox()
        health_spinbox.setRange(1, 1000)
        health_spinbox.setValue(health_scaling)
        health_spinbox.setSuffix("%")
        form_layout.addRow(t("mods_page.dialog.seamlesscoop_health_scaling"), health_spinbox)

        # 伤害缩放
        damage_spinbox = QSpinBox()
        damage_spinbox.setRange(1, 1000)
        damage_spinbox.setValue(damage_scaling)
        damage_spinbox.setSuffix("%")
        form_layout.addRow(t("mods_page.dialog.seamlesscoop_damage_scaling"), damage_spinbox)

        # 架势缩放
        posture_spinbox = QSpinBox()
        posture_spinbox.setRange(1, 1000)
        posture_spinbox.setValue(posture_scaling)
        posture_spinbox.setSuffix("%")
        form_layout.addRow(t("mods_page.dialog.seamlesscoop_posture_scaling"), posture_spinbox)

        layout.addLayout(form_layout)

        # 说明文字
        info_label = QLabel(t("mods_page.dialog.seamlesscoop_info"))
        info_label.setStyleSheet("color: #a6adc8; font-size: 12px; margin: 10px 0;")
        layout.addWidget(info_label)

        # 按钮
        button_layout = QHBoxLayout()

        ok_button = QPushButton(t("mods_page.button.save"))
        cancel_button = QPushButton(t("mods_page.button.cancel"))
        reset_button = QPushButton(t("mods_page.button.reset_default"))

        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        # 连接信号
        def reset_to_default():
            health_spinbox.setValue(100)
            damage_spinbox.setValue(100)
            posture_spinbox.setValue(100)

        def save_settings():
            try:
                # 更新配置
                config.set('SCALING', 'health_scaling', str(health_spinbox.value()))
                config.set('SCALING', 'damage_scaling', str(damage_spinbox.value()))
                config.set('SCALING', 'posture_scaling', str(posture_spinbox.value()))

                # 保存到文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    config.write(f)

                self.show_status(t("mods_page.status.seamlesscoop_config_saved"), "success")
                dialog.accept()

            except Exception as e:
                self.show_status(t("mods_page.launch_process.save_config_failed") + f": {e}", "error")

        ok_button.clicked.connect(save_settings)
        cancel_button.clicked.connect(dialog.reject)
        reset_button.clicked.connect(reset_to_default)

        # 显示对话框
        dialog.exec()

    def configure_nighter_difficulty(self):
        """配置Nighter设置"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                       QPushButton, QRadioButton, QButtonGroup, QCheckBox)
        from PySide6.QtCore import Qt
        import json
        import os

        # 配置文件路径
        config_path = os.path.join("Mods", "nighter", "nighter.json")

        if not os.path.exists(config_path):
            self.show_status(t("mods_page.status.nighter_config_not_found"), "error")
            return

        # 读取当前配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 读取实际的配置结构
            force_unlock_deep_night = config.get('forceUnlockDeepNight', True)
            force_deep_night = config.get('forceDeepNight', {'enable': False, 'level': 3})
            bypass_online_check = config.get('bypassOnlineCheck', False)

            current_enable = force_deep_night.get('enable', False)
            current_level = force_deep_night.get('level', 3)

        except Exception as e:
            self.show_status(t("mods_page.status.nighter_config_read_failed").format(error=e), "error")
            return

        # 创建无边框配置对话框
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setModal(True)
        dialog.resize(520, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }
            QRadioButton {
                color: #cdd6f4;
                font-size: 14px;
                padding: 8px;
                spacing: 10px;
                background-color: transparent;
            }
            QRadioButton:disabled {
                color: #45475a;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
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
            QRadioButton::indicator:checked:hover {
                border-color: #f9e2af;
                background-color: #f9e2af;
            }
            QRadioButton::indicator:disabled {
                border-color: #313244;
                background-color: #1e1e2e;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 14px;
                padding: 8px;
                spacing: 10px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
            QCheckBox::indicator:checked:hover {
                border-color: #7aa2f7;
                background-color: #7aa2f7;
            }
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #89dceb;
            }
            QPushButton#closeButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton#closeButton:hover {
                background-color: #eba0ac;
            }
        """)

        # 添加拖拽功能
        dialog.mousePressEvent = lambda event: setattr(dialog, '_drag_pos', event.globalPos() - dialog.pos()) if event.button() == Qt.LeftButton else None
        dialog.mouseMoveEvent = lambda event: dialog.move(event.globalPos() - dialog._drag_pos) if hasattr(dialog, '_drag_pos') and event.buttons() == Qt.LeftButton else None

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)

        # 标题栏
        title_bar = QHBoxLayout()
        title_label = QLabel(t("mods_page.dialog.nighter_title"))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fab387;")

        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(dialog.reject)

        title_bar.addWidget(title_label)
        title_bar.addStretch()
        title_bar.addWidget(close_button)
        layout.addLayout(title_bar)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #45475a; margin: 10px 0;")
        layout.addWidget(separator)

        # 主内容区域 - 水平布局
        content_layout = QHBoxLayout()

        # 左侧设置区域
        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(2)  # 设置更紧密的垂直间距

        # 基础设置区域
        basic_settings_label = QLabel(t("mods_page.dialog.nighter_basic_settings"))
        basic_settings_label.setStyleSheet("font-size: 16px; color: #89b4fa; margin-bottom: 3px; background-color: transparent;")
        left_layout.addWidget(basic_settings_label)

        # 强制解锁深夜模式
        unlock_checkbox = QCheckBox(t("mods_page.dialog.nighter_force_unlock"))
        unlock_checkbox.setChecked(force_unlock_deep_night)
        unlock_checkbox.setStyleSheet("background-color: transparent; margin: 1px 0;")
        left_layout.addWidget(unlock_checkbox)

        # 绕过在线检查
        bypass_checkbox = QCheckBox(t("mods_page.dialog.nighter_bypass_online"))
        bypass_checkbox.setChecked(bypass_online_check)
        bypass_checkbox.setStyleSheet("background-color: transparent; margin: 1px 0;")
        left_layout.addWidget(bypass_checkbox)

        # 强制指定深夜难度
        force_night_label = QLabel(t("mods_page.dialog.nighter_force_night"))
        force_night_label.setStyleSheet("font-size: 16px; color: #89b4fa; margin: 5px 0 3px 0; background-color: transparent;")
        left_layout.addWidget(force_night_label)

        # 启用强制指定深夜难度
        enable_force_checkbox = QCheckBox(t("mods_page.dialog.nighter_enable_force"))
        enable_force_checkbox.setChecked(current_enable)
        enable_force_checkbox.setStyleSheet("background-color: transparent; margin: 1px 0;")
        left_layout.addWidget(enable_force_checkbox)

        left_layout.addStretch()

        # 右侧难度选择区域
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        # 难度选择标题
        level_label = QLabel(t("mods_page.dialog.nighter_select_level"))
        level_label.setStyleSheet("font-size: 16px; color: #89b4fa; margin-bottom: 10px; background-color: transparent;")
        right_layout.addWidget(level_label)

        # 单选框组
        radio_group = QButtonGroup()
        radio_buttons = []

        # 创建网格布局容器
        from PySide6.QtWidgets import QGridLayout
        radio_grid_widget = QWidget()
        radio_grid_widget.setStyleSheet("background-color: transparent;")
        radio_grid_layout = QGridLayout(radio_grid_widget)
        radio_grid_layout.setContentsMargins(0, 0, 0, 0)
        radio_grid_layout.setSpacing(5)

        # 创建单选框 - 网格布局，每行两个
        for level in range(1, 6):
            radio = QRadioButton(t("mods_page.dialog.nighter_level").format(level=level))
            radio.setChecked(level == current_level)
            radio.setEnabled(current_enable)  # 初始状态根据强制指定深夜难度决定
            radio.setStyleSheet("background-color: transparent;")
            radio_buttons.append(radio)
            radio_group.addButton(radio, level)

            # 计算网格位置：每行两个
            row = (level - 1) // 2
            col = (level - 1) % 2
            radio_grid_layout.addWidget(radio, row, col)

        right_layout.addWidget(radio_grid_widget)

        right_layout.addStretch()

        # 组装左右布局
        content_layout.addWidget(left_widget, 1)
        content_layout.addWidget(right_widget, 1)
        layout.addLayout(content_layout)

        # 启用/禁用难度选择的函数
        def toggle_difficulty_selection(enabled):
            for radio in radio_buttons:
                radio.setEnabled(enabled)
            # 同时更新标题颜色
            if enabled:
                level_label.setStyleSheet("font-size: 16px; color: #89b4fa; margin-bottom: 10px; background-color: transparent;")
            else:
                level_label.setStyleSheet("font-size: 16px; color: #45475a; margin-bottom: 10px; background-color: transparent;")

        # 连接强制指定深夜难度复选框信号
        enable_force_checkbox.toggled.connect(toggle_difficulty_selection)

        # 初始化标题颜色
        toggle_difficulty_selection(current_enable)

        # 注意事项区域 - 参考工具下载界面样式
        from PySide6.QtWidgets import QGroupBox
        notice_section = QGroupBox(t("mods_page.dialog.nighter_notice_title"))
        notice_section.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)

        notice_layout = QVBoxLayout()
        notice_layout.setSpacing(10)

        # 说明文字 - 参考工具下载界面样式
        help_label = QLabel(t("mods_page.dialog.nighter_help_text"))
        help_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 13px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI Light', sans-serif;
                font-weight: 300;
                line-height: 1.4;
                padding: 10px;
                background-color: #1e1e2e;
                border-radius: 6px;
                border: 1px solid #313244;
            }
        """)
        help_label.setWordWrap(True)
        notice_layout.addWidget(help_label)

        notice_section.setLayout(notice_layout)

        # 底部区域 - 说明栏和按钮水平布局
        bottom_layout = QHBoxLayout()

        # 按钮区域
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # 重置默认按钮
        reset_button = QPushButton(t("mods_page.button.reset_default"))
        reset_button.setFixedSize(80, 35)

        # 保存按钮
        ok_button = QPushButton(t("mods_page.button.save"))
        ok_button.setFixedSize(80, 35)

        button_layout.addWidget(reset_button)
        button_layout.addWidget(ok_button)

        bottom_layout.addWidget(notice_section, 1)  # 说明栏占主要空间
        bottom_layout.addWidget(button_widget, 0, Qt.AlignVCenter)  # 按钮组垂直居中

        layout.addLayout(bottom_layout)

        # 重置默认配置函数
        def reset_to_default():
            try:
                # 默认配置（基于当前nighter.json的内容）
                default_config = {
                    "forceUnlockDeepNight": True,
                    "bypassOnlineCheck": False,
                    "forceDeepNight": {
                        "enable": False,
                        "level": 3
                    },
                    "superNightLordList": [0, 1, 2, 3, 4, 5, 6]
                }

                # 更新UI控件到默认状态
                unlock_checkbox.setChecked(default_config['forceUnlockDeepNight'])
                bypass_checkbox.setChecked(default_config['bypassOnlineCheck'])
                enable_force_checkbox.setChecked(default_config['forceDeepNight']['enable'])

                # 设置默认难度等级
                default_level = default_config['forceDeepNight']['level']
                for radio in radio_buttons:
                    radio.setChecked(radio_group.id(radio) == default_level)

                # 更新难度选择的启用状态
                toggle_difficulty_selection(default_config['forceDeepNight']['enable'])

                self.show_status(t("mods_page.status.nighter_reset_success"), "success")

            except Exception as e:
                self.show_status(t("mods_page.status.nighter_reset_failed").format(error=e), "error")

        # 连接信号
        def save_settings():
            try:
                # 更新基础设置
                config['forceUnlockDeepNight'] = unlock_checkbox.isChecked()
                config['bypassOnlineCheck'] = bypass_checkbox.isChecked()

                # 更新强制深夜模式设置
                config['forceDeepNight']['enable'] = enable_force_checkbox.isChecked()

                # 获取选中的难度等级
                checked_button = radio_group.checkedButton()
                if checked_button:
                    new_level = radio_group.id(checked_button)
                    config['forceDeepNight']['level'] = new_level
                else:
                    self.show_status(t("mods_page.status.nighter_select_level_error"), "error")
                    return

                # 确保superNightLordList存在（默认全解锁）
                if 'superNightLordList' not in config:
                    config['superNightLordList'] = [0, 1, 2, 3, 4, 5, 6]

                # 保存到文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

                self.show_status(t("mods_page.status.nighter_config_saved"), "success")
                dialog.accept()

            except Exception as e:
                self.show_status(t("mods_page.status.nighter_save_failed").format(error=e), "error")

        ok_button.clicked.connect(save_settings)
        reset_button.clicked.connect(reset_to_default)

        # 显示对话框
        dialog.exec()

    def toggle_nrsc_preload(self, dll_name: str, enable: bool):
        """切换nrsc.dll预加载状态"""
        success = self.mod_manager.set_native_load_early(dll_name, enable)
        if success:
            if enable:
                self.show_status(t("mods_page.status.nrsc_preload_enabled").format(dll_name=dll_name), "success")
            else:
                self.show_status(t("mods_page.status.nrsc_preload_disabled").format(dll_name=dll_name), "success")
            
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 重新扫描以更新显示
            self.scan_mods()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(t("mods_page.status.nrsc_preload_failed").format(dll_name=dll_name), "error")

    def _format_dependencies(self, dependencies):
        """格式化依赖列表为正确的TOML格式"""
        if not dependencies:
            return "[]"

        formatted_deps = []
        for dep in dependencies:
            dep_str = "{"
            dep_parts = []

            if 'id' in dep:
                dep_parts.append(f"id = \"{dep['id']}\"")

            if 'optional' in dep:
                dep_parts.append(f"optional = {str(dep['optional']).lower()}")

            dep_str += ", ".join(dep_parts) + "}"
            formatted_deps.append(dep_str)

        return "[" + ", ".join(formatted_deps) + "]"

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        # 更新页面标题
        self.title_label.setText(t("mods_page.page_title"))

        # 更新区域标题
        self.mod_management_title.setText(t("mods_page.section.mod_management"))
        self.packages_label.setText(t("mods_page.section.mod_packages"))
        self.natives_label.setText(t("mods_page.section.native_dll"))
        self.config_preview_title.setText(t("mods_page.section.config_preview"))
        self.config_file_preview_label.setText(t("mods_page.section.config_file_preview"))

        # 更新按钮文本
        self.scan_btn.setText(t("mods_page.button.scan_mods"))
        self.launch_btn.setText(t("mods_page.button.launch_game"))
        self.add_external_package_btn.setText(t("mods_page.button.add_external_mod"))
        self.add_external_native_btn.setText(t("mods_page.button.add_external_dll"))
        self.save_btn.setText(t("mods_page.button.save_config"))
        self.clear_btn.setText(t("mods_page.button.clear_config"))

        # 更新配置摘要标签（如果是空状态）
        if self.config_summary_label.text() == "配置摘要：无mod配置" or self.config_summary_label.text() == "Config Summary: No mods":
            self.config_summary_label.setText(t("mods_page.label.config_summary_empty"))
        else:
            # 重新生成配置摘要
            summary = self.mod_manager.get_config_summary()
            summary_text = t("mods_page.config_preview.summary").format(
                enabled=summary['enabled_packages'],
                total=summary['total_packages'],
                enabled_dll=summary['enabled_natives'],
                total_dll=summary['total_natives']
            )
            self.config_summary_label.setText(summary_text)

        # 重新生成配置预览
        config_content = self.generate_config_content()
        self.config_preview.setPlainText(config_content)
        
        # 重新扫描mods以更新列表中的翻译文本（如"[预加载]"）
        self.scan_mods()
