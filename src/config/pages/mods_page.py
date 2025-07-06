"""
Mod配置页面
游戏模组管理和ME3配置
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGroupBox, QListWidget,
                               QListWidgetItem, QCheckBox, QLineEdit, QTextEdit,
                               QSplitter, QScrollArea, QComboBox, QFileDialog,
                               QMenu, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer, QProcess
from .base_page import BasePage
from ...config.mod_config_manager import ModConfigManager
from ...config.config_manager import ConfigManager
import subprocess
import os
from pathlib import Path


class ModsPage(BasePage):
    """Mod配置页面"""

    # 定义信号：当mod配置发生变化时发出
    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__("Mod配置", parent)
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
        title_label = QLabel("🎮 Mod管理")
        title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;  /* 从18px减少到16px */
                font-weight: bold;
                margin-bottom: 3px;  /* 从10px减少到3px */
                padding: 2px 0;  /* 减少内边距 */
            }
        """)
        layout.addWidget(title_label)

        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 扫描按钮
        scan_btn = QPushButton("🔄 扫描Mods")
        scan_btn.setFixedHeight(35)
        scan_btn.setStyleSheet("""
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
        scan_btn.clicked.connect(self.scan_mods)
        button_layout.addWidget(scan_btn)

        # 启动游戏按钮
        launch_btn = QPushButton("🚀 启动游戏")
        launch_btn.setFixedHeight(35)
        launch_btn.setStyleSheet("""
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
        launch_btn.clicked.connect(self.launch_game)
        button_layout.addWidget(launch_btn)

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
        packages_label = QLabel("📦 Mod包")
        packages_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        packages_layout.addWidget(packages_label)

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
        add_external_package_btn = QPushButton("📁 添加外部Mod")
        add_external_package_btn.setFixedHeight(30)
        add_external_package_btn.setStyleSheet("""
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
        add_external_package_btn.clicked.connect(self.add_external_package)
        packages_layout.addWidget(add_external_package_btn)

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
        natives_label = QLabel("🔧 Native DLL")
        natives_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        natives_layout.addWidget(natives_label)

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
        add_external_native_btn = QPushButton("🔧 添加外部DLL")
        add_external_native_btn.setFixedHeight(30)
        add_external_native_btn.setStyleSheet("""
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
        add_external_native_btn.clicked.connect(self.add_external_native)
        natives_layout.addWidget(add_external_native_btn)

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
        title_label = QLabel("⚙️ 配置预览")
        title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;  /* 从18px减少到16px */
                font-weight: bold;
                margin-bottom: 3px;  /* 从10px减少到3px */
                padding: 2px 0;  /* 减少内边距 */
            }
        """)
        layout.addWidget(title_label)

        # 配置摘要
        self.config_summary_label = QLabel("配置摘要：无mod配置")
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
        preview_label = QLabel("📄 配置文件预览")
        preview_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        layout.addWidget(preview_label)

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
        save_btn = QPushButton("💾 保存配置")
        save_btn.setFixedHeight(35)
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        # 清除配置按钮
        clear_btn = QPushButton("🗑️ 清除配置")
        clear_btn.setFixedHeight(35)
        clear_btn.setStyleSheet("""
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
        clear_btn.clicked.connect(self.clear_all_mods)
        button_layout.addWidget(clear_btn)

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
            self.show_status(f"自动清理了 {internal_cleaned_count} 个错误的内部mod条目", "success")

        # 检查外部mod存在性并获取缺失列表
        missing_mods = self.mod_manager.get_missing_external_mods()

        # 如果有缺失的外部mod，自动清理
        if missing_mods['packages'] or missing_mods['natives']:
            missing_count = len(missing_mods['packages']) + len(missing_mods['natives'])
            # 自动清理缺失的外部mod
            cleaned = self.mod_manager.cleanup_missing_external_mods()
            cleaned_count = len(cleaned['packages']) + len(cleaned['natives'])

            if cleaned_count > 0:
                self.show_status(f"自动清理了 {cleaned_count} 个缺失的外部mod", "success")
            else:
                self.show_status(f"检测到 {missing_count} 个缺失的外部mod，但清理失败", "error")

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
            comment = self.mod_manager.get_native_comment(clean_name)

            # 检查是否为缺失的外部DLL
            is_missing = is_external and clean_name in missing_mods['natives']

            if is_missing:
                display_text = f"❌ {dll_name} [缺失]"
            else:
                display_text = f"🔧 {dll_name}"

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

            self.natives_list.addItem(item)
            self.natives_list.setItemWidget(item, checkbox)

        # 更新配置预览
        self.update_config_preview()

    def toggle_package(self, package_name: str, enabled: bool):
        """切换mod包状态"""
        if enabled:
            # 添加到配置
            self.mod_manager.add_package(package_name, f"{package_name}/")
        else:
            # 从配置移除
            self.mod_manager.remove_package(package_name)

        self.update_config_preview()
        # 发出配置变化信号
        self.config_changed.emit()

    def toggle_native(self, dll_name: str, enabled: bool):
        """切换native DLL状态"""
        if enabled:
            # 添加到配置
            self.mod_manager.add_native(dll_name)
        else:
            # 从配置移除
            self.mod_manager.remove_native(dll_name)

        self.update_config_preview()
        # 发出配置变化信号
        self.config_changed.emit()

    def update_config_preview(self):
        """更新配置预览"""
        # 更新摘要
        summary = self.mod_manager.get_config_summary()
        summary_text = (f"📦 Mod包: {summary['enabled_packages']}/{summary['total_packages']} "
                       f"🔧 DLL: {summary['enabled_natives']}/{summary['total_natives']}")
        self.config_summary_label.setText(summary_text)

        # 生成配置文件内容
        config_content = self.generate_config_content()
        self.config_preview.setPlainText(config_content)

    def generate_config_content(self) -> str:
        """生成配置文件内容"""
        lines = []
        lines.append("# ME3 Mod配置文件")
        lines.append("# 由Nmodm自动生成")
        lines.append("")
        lines.append('profileVersion = "v1"')
        lines.append("")

        # 添加packages
        enabled_packages = [pkg for pkg in self.mod_manager.packages if pkg.enabled]
        if enabled_packages:
            lines.append("# Mod包配置")
            for package in enabled_packages:
                lines.append("[[packages]]")
                lines.append(f'id = "{package.id}"')
                lines.append(f'source = "{package.source}"')
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
            lines.append("# Native DLL配置")
            for native in enabled_natives:
                lines.append("[[natives]]")
                lines.append(f'path = "{native.path}"')
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
                lines.append("")

        return "\n".join(lines)

    def save_config(self):
        """保存配置"""
        if self.mod_manager.save_config():
            self.show_status("配置保存成功", "success")
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status("配置保存失败", "error")

    def launch_game(self):
        """启动游戏"""
        # 检查游戏路径
        game_path = self.config_manager.get_game_path()
        if not game_path or not self.config_manager.validate_game_path():
            self.show_status("请先在ME3页面配置游戏路径", "error")
            return

        # 检查ME3可执行文件
        me3_exe = self.mod_manager.get_me3_executable_path()
        if not me3_exe:
            self.show_status("未找到ME3可执行文件，请确保ME3已正确安装", "error")
            return

        # 保存当前配置
        if not self.mod_manager.save_config():
            self.show_status("保存配置失败", "error")
            return

        # 构建启动命令
        config_file = str(self.mod_manager.config_file)
        cmd = [
            me3_exe,
            "launch",
            "--exe", game_path,
            "--skip-steam-init",
            "--game", "nightreign",
            "-p", config_file
        ]

        try:
            # 启动游戏
            self.show_status("正在启动游戏...", "info")
            subprocess.Popen(cmd, cwd=os.path.dirname(me3_exe))
            self.show_status("游戏启动成功", "success")
        except Exception as e:
            self.show_status(f"启动失败: {str(e)}", "error")

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

        # 3秒后自动隐藏
        QTimer.singleShot(3000, lambda: self.status_label.setVisible(False))

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
            self.show_status("已清除所有mod配置", "success")

            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status("清除配置失败", "error")

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
                self.show_status(f"已添加外部mod: {folder_path_obj.name}", "success")
                # 重新扫描以更新列表
                self.scan_mods()
            else:
                self.show_status(f"添加外部mod失败: {message}", "error")

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
                self.show_status(f"已添加外部DLL: {file_path_obj.name}", "success")
                # 重新扫描以更新列表
                self.scan_mods()
            else:
                self.show_status(f"添加外部DLL失败: {message}", "error")

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
        comment_action = menu.addAction("📝 编辑备注")
        comment_action.triggered.connect(lambda: self.edit_mod_comment(clean_name, checkbox))

        # 添加强制最后加载选项
        menu.addSeparator()
        is_force_last = self.mod_manager.is_force_load_last(clean_name)
        if is_force_last:
            force_last_action = menu.addAction("🔓 取消强制最后加载")
            force_last_action.triggered.connect(lambda: self.clear_force_load_last(clean_name))
        else:
            force_last_action = menu.addAction("🔒 强制最后加载")
            force_last_action.triggered.connect(lambda: self.set_force_load_last(clean_name))

        # 如果是外部mod，添加移除选项
        if is_external:
            menu.addSeparator()
            remove_action = menu.addAction("🗑️ 移除外部Mod")
            remove_action.triggered.connect(lambda: self.remove_external_mod(clean_name))

        menu.exec(self.packages_list.mapToGlobal(position))

    def show_native_context_menu(self, position):
        """显示DLL右键菜单"""
        item = self.natives_list.itemAt(position)
        if not item:
            return

        checkbox = self.natives_list.itemWidget(item)
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

        # 添加备注菜单项
        comment_action = menu.addAction("📝 编辑备注")
        comment_action.triggered.connect(lambda: self.edit_native_comment(clean_name, checkbox))

        # 如果是外部DLL，添加移除选项
        if is_external:
            menu.addSeparator()
            remove_action = menu.addAction("🗑️ 移除外部DLL")
            remove_action.triggered.connect(lambda: self.remove_external_dll(clean_name))

        menu.exec(self.natives_list.mapToGlobal(position))

    def edit_mod_comment(self, mod_name: str, checkbox: QCheckBox):
        """内联编辑mod备注"""
        current_comment = self.mod_manager.get_mod_comment(mod_name)

        # 创建内联编辑器
        edit_widget = QLineEdit()
        edit_widget.setText(current_comment)
        edit_widget.setPlaceholderText("输入备注信息... (回车保存，Esc取消)")
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
            self.show_status(f"已保存 {mod_name} 的备注", "success")

        def cancel_edit():
            edit_widget.deleteLater()
            self.show_status("已取消编辑", "info")

        # 重写keyPressEvent来处理Escape键
        def keyPressEvent(event):
            if event.key() == Qt.Key_Escape:
                cancel_edit()
            else:
                QLineEdit.keyPressEvent(edit_widget, event)

        edit_widget.keyPressEvent = keyPressEvent
        edit_widget.returnPressed.connect(save_comment)

        # 在状态栏显示编辑提示
        self.show_status(f"正在编辑 {mod_name} 的备注，回车保存，Esc取消", "info")

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
        edit_widget.setPlaceholderText("输入备注信息... (回车保存，Esc取消)")
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
            self.show_status(f"已保存 {dll_name} 的备注", "success")

        def cancel_edit():
            edit_widget.deleteLater()
            self.show_status("已取消编辑", "info")

        # 重写keyPressEvent来处理Escape键
        def keyPressEvent(event):
            if event.key() == Qt.Key_Escape:
                cancel_edit()
            else:
                QLineEdit.keyPressEvent(edit_widget, event)

        edit_widget.keyPressEvent = keyPressEvent
        edit_widget.returnPressed.connect(save_comment)

        # 在状态栏显示编辑提示
        self.show_status(f"正在编辑 {dll_name} 的备注，回车保存，Esc取消", "info")

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
        self.show_status(f"已更新 {mod_name} 的备注", "success")

    def update_native_display(self, dll_name: str, checkbox: QCheckBox, comment: str):
        """更新DLL显示（包含备注）"""
        is_external = dll_name in self.mod_manager.external_natives
        display_name = f"{dll_name} (外部)" if is_external else dll_name

        if comment:
            display_text = f"🔧 {display_name} - {comment}"
        else:
            display_text = f"🔧 {display_name}"

        checkbox.setText(display_text)
        self.show_status(f"已更新 {dll_name} 的备注", "success")

    def remove_external_mod(self, mod_name: str):
        """移除外部mod"""
        if self.mod_manager.remove_external_package(mod_name):
            # 同时从当前配置中移除
            self.mod_manager.remove_package(mod_name)
            # 重新扫描以更新列表
            self.scan_mods()
            self.show_status(f"已移除外部Mod: {mod_name}", "success")
        else:
            self.show_status(f"移除外部Mod失败: {mod_name}", "error")

    def remove_external_dll(self, dll_name: str):
        """移除外部DLL"""
        if self.mod_manager.remove_external_native(dll_name):
            # 同时从当前配置中移除
            self.mod_manager.remove_native(dll_name)
            # 重新扫描以更新列表
            self.scan_mods()
            self.show_status(f"已移除外部DLL: {dll_name}", "success")
        else:
            self.show_status(f"移除外部DLL失败: {dll_name}", "error")

    def set_force_load_last(self, mod_name: str):
        """设置mod强制最后加载"""
        success = self.mod_manager.set_force_load_last(mod_name)
        if success:
            self.show_status(f"已设置 {mod_name} 强制最后加载", "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(f"设置强制最后加载失败: {mod_name}", "error")

    def clear_force_load_last(self, mod_name: str):
        """清除mod的强制最后加载设置"""
        success = self.mod_manager.clear_force_load_last(mod_name)
        if success:
            self.show_status(f"已取消 {mod_name} 的强制最后加载", "success")
            # 保存配置并更新预览
            self.mod_manager.save_config()
            self.update_config_preview()
            # 发出配置变化信号
            self.config_changed.emit()
        else:
            self.show_status(f"取消强制最后加载失败: {mod_name}", "error")

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
