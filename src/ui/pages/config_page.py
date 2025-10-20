"""
基础配置页面
游戏路径配置和破解功能管理
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QFileDialog, QFrame,
                               QGroupBox, QTextEdit, QGridLayout)
from PySide6.QtCore import Qt, Signal
from .base_page import BasePage
from ...config.config_manager import ConfigManager
from src.i18n import TLabel, t, TranslationManager


class ConfigSection(QGroupBox):
    """配置区域组件"""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)

    def set_title(self, title):
        """设置标题"""
        self.setTitle(title)


class ConfigPage(BasePage):
    """基础配置页面"""
    
    # 状态更新信号
    status_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(t("config_page.page_title"), parent)
        self.config_manager = ConfigManager()
        self.setup_content()
        self.load_current_config()
        # 初始化系统检查
        self.check_system_status()
        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)
    
    def setup_content(self):
        """设置页面内容"""
        # 创建网格布局容器
        self.create_grid_layout()

        # 通用状态显示区域（底部紧凑版）
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 3px;
                border: 1px solid #fab387;
                margin-top: 8px;
                max-height: 24px;
            }
        """)
        self.status_label.setVisible(False)
        self.add_content(self.status_label)

        self.add_stretch()

    def create_grid_layout(self):
        """创建网格布局"""
        # 创建网格容器
        grid_container = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(14)  # 调整间距为14px，更加紧凑
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：游戏路径配置（跨两列）
        game_path_section = self.create_game_path_section_widget()
        grid_layout.addWidget(game_path_section, 0, 0, 1, 2)  # 行0，列0-1，跨2列

        # 第二行：游戏信息检测 和 软件路径检测
        game_info_section = self.create_game_info_section_widget()
        software_info_section = self.create_software_info_section_widget()
        grid_layout.addWidget(game_info_section, 1, 0)    # 行1，列0
        grid_layout.addWidget(software_info_section, 1, 1) # 行1，列1

        # 第三行：破解管理 和 系统检查与修复
        crack_section = self.create_crack_section_widget()
        system_check_section = self.create_system_check_section_widget()
        grid_layout.addWidget(crack_section, 2, 0)    # 行2，列0
        grid_layout.addWidget(system_check_section, 2, 1)    # 行2，列1

        # 设置列的拉伸比例（让两列等宽）
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # 设置行的拉伸策略：底部优先，让底部区域获得更多垂直空间
        # 第一行（游戏路径配置）：不拉伸，保持紧凑
        grid_layout.setRowStretch(0, 0)
        # 第二行（信息检测区域）：较小拉伸比例，适度显示信息
        grid_layout.setRowStretch(1, 3)  # 30%的可用空间
        # 第三行（破解管理和预留区域）：较大拉伸比例，获得更多高度
        grid_layout.setRowStretch(2, 7)  # 70%的可用空间

        grid_container.setLayout(grid_layout)
        self.add_content(grid_container)
    
    def create_game_path_section_widget(self):
        """创建游戏路径配置区域widget"""
        self.game_path_section = ConfigSection(t("config_page.section.game_path"))
        # 设置智能布局策略：保持紧凑的高度，水平方向可扩展
        from PySide6.QtWidgets import QSizePolicy
        self.game_path_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        # 应用专门的紧凑样式
        self.game_path_section.setStyleSheet(self.game_path_section.styleSheet() + """
            QGroupBox {
                margin-top: 5px;
                padding-top: 8px;
                padding-bottom: 8px;
            }
        """)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(4)  # 更紧凑的垂直间距

        # 第一行：说明文本和状态显示
        top_row = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)  # 减少水平间距，更紧凑

        self.game_path_info_label = QLabel(t("config_page.form.game_path_hint"))
        self.game_path_info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        self.path_status_label = QLabel()
        self.path_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
            }
        """)

        top_layout.addWidget(self.game_path_info_label)
        top_layout.addStretch()
        top_layout.addWidget(self.path_status_label)
        top_row.setLayout(top_layout)
        main_layout.addWidget(top_row)

        # 第二行：路径输入和按钮
        input_row = QWidget()
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)  # 进一步减少按钮间距，更紧凑

        # 路径输入框
        self.game_path_input = QLineEdit()
        self.game_path_input.setPlaceholderText(t("config_page.form.game_path_placeholder"))
        # 设置智能尺寸策略：水平扩展，垂直固定
        from PySide6.QtWidgets import QSizePolicy
        self.game_path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.game_path_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 10px;
                color: #cdd6f4;
                font-size: 13px;
                max-height: 32px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)

        # 浏览按钮
        self.browse_btn = QPushButton(t("config_page.button.browse"))
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_game_path)

        # 保存按钮
        self.save_btn = QPushButton(t("config_page.button.save"))
        self.save_btn.setFixedWidth(100)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c3a3;
            }
        """)
        self.save_btn.clicked.connect(self.save_game_path)

        input_layout.addWidget(self.game_path_input)
        input_layout.addWidget(self.browse_btn)
        input_layout.addWidget(self.save_btn)
        input_row.setLayout(input_layout)
        main_layout.addWidget(input_row)

        self.game_path_section.setLayout(main_layout)
        return self.game_path_section
    
    def create_crack_section_widget(self):
        """创建破解管理区域widget"""
        self.crack_section = ConfigSection(t("config_page.section.crack"))
        # 设置尺寸策略：保持紧凑，避免空间浪费
        from PySide6.QtWidgets import QSizePolicy
        self.crack_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        layout = QVBoxLayout()
        layout.setSpacing(12)  # 优化垂直间距，充分利用空间

        # 顶部：说明文本和状态显示（水平布局）
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.crack_info_label = QLabel(t("config_page.form.crack_hint"))
        self.crack_info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        # 破解状态显示
        self.crack_status_label = QLabel()
        self.crack_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
            }
        """)

        # 破解详细信息显示（多行）
        self.crack_detail_label = QLabel()
        self.crack_detail_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                background-color: #313244;
                border: 1px solid #fab387;
                border-radius: 4px;
                padding: 6px;
                margin-top: 4px;
            }
        """)
        self.crack_detail_label.setWordWrap(True)
        self.crack_detail_label.setVisible(False)

        header_layout.addWidget(self.crack_info_label)
        header_layout.addStretch()
        header_layout.addWidget(self.crack_status_label)
        header_row.setLayout(header_layout)
        layout.addWidget(header_row)

        # 添加破解详细信息标签
        layout.addWidget(self.crack_detail_label)

        # 按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)  # 减少按钮间距

        # 应用破解按钮
        self.apply_crack_btn = QPushButton(t("config_page.button.apply_crack"))
        self.apply_crack_btn.setFixedSize(100, 30)  # 更紧凑的尺寸
        self.apply_crack_btn.setStyleSheet("""
            QPushButton {
                background-color: #f9e2af;
                border: none;
                border-radius: 5px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f7d794;
            }
            QPushButton:pressed {
                background-color: #f5cc79;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.apply_crack_btn.clicked.connect(self.apply_crack)

        # 移除破解按钮
        self.remove_crack_btn = QPushButton(t("config_page.button.remove_crack"))
        self.remove_crack_btn.setFixedSize(100, 30)  # 更紧凑的尺寸
        self.remove_crack_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 5px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f17497;
            }
            QPushButton:pressed {
                background-color: #ef5d86;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.remove_crack_btn.clicked.connect(self.remove_crack)

        button_layout.addWidget(self.apply_crack_btn)
        button_layout.addWidget(self.remove_crack_btn)
        button_layout.addStretch()

        button_container.setLayout(button_layout)
        layout.addWidget(button_container)

        # 破解文件信息（单行显示）
        self.crack_files_info_label = QLabel(t("config_page.form.crack_files"))
        self.crack_files_info_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 5px;
                padding: 8px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.crack_files_info_label)

        self.crack_section.setLayout(layout)
        return self.crack_section

    def create_system_check_section_widget(self):
        """创建系统检查与修复区域widget"""
        self.system_check_section = ConfigSection(t("config_page.section.system_check"))
        # 设置尺寸策略：允许动态扩展
        from PySide6.QtWidgets import QSizePolicy, QGridLayout
        self.system_check_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # 使用网格布局替代垂直布局
        layout = QGridLayout()
        layout.setSpacing(15)  # 增加网格间距，让布局更整齐
        layout.setContentsMargins(12, 12, 12, 12)  # 增加内边距

        # 上半部分：软件路径检测提醒
        path_check_container = QWidget()
        path_check_container.setMinimumHeight(120)  # 设置最小高度，允许动态扩展
        path_check_layout = QVBoxLayout()
        path_check_layout.setContentsMargins(8, 8, 8, 8)
        path_check_layout.setSpacing(8)

        # 软件路径检测标题
        self.path_check_title = QLabel(t("config_page.check.path_title"))
        self.path_check_title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)

        # 软件路径检测状态
        self.path_check_status = QLabel(t("config_page.check.detecting"))
        self.path_check_status.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #fab387;
            }
        """)

        # 路径检测详细信息（与OnlineFix区域对齐）
        self.path_check_info = QLabel(t("config_page.check.path_status_detecting"))
        self.path_check_info.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 10px;
                margin-top: 2px;
            }
        """)

        # 路径检测提醒文本
        self.path_check_warning = QLabel(t("config_page.message.path_warning"))
        self.path_check_warning.setStyleSheet("""
            QLabel {
                color: #f38ba8;
                font-size: 11px;
                padding: 6px;
                background-color: rgba(243, 139, 168, 0.1);
                border-radius: 4px;
                border: 1px solid #f38ba8;
            }
        """)
        self.path_check_warning.setWordWrap(True)
        self.path_check_warning.setVisible(False)  # 默认隐藏

        path_check_layout.addWidget(self.path_check_title)
        path_check_layout.addWidget(self.path_check_status)
        path_check_layout.addWidget(self.path_check_info)
        path_check_layout.addWidget(self.path_check_warning)
        path_check_container.setLayout(path_check_layout)
        layout.addWidget(path_check_container, 0, 0)  # 第一行，第一列

        # 中间部分：OnlineFix完整性检测区域
        onlinefix_check_container = QWidget()
        onlinefix_check_container.setMinimumHeight(120)  # 设置最小高度，允许动态扩展
        onlinefix_check_layout = QVBoxLayout()
        onlinefix_check_layout.setContentsMargins(8, 8, 8, 8)
        onlinefix_check_layout.setSpacing(8)

        # OnlineFix检测标题
        self.onlinefix_check_title = QLabel(t("config_page.check.onlinefix_title"))
        self.onlinefix_check_title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)

        # OnlineFix状态
        self.onlinefix_check_status = QLabel(t("config_page.check.detecting"))
        self.onlinefix_check_status.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #fab387;
            }
        """)

        # OnlineFix文件信息
        self.onlinefix_file_info = QLabel(t("config_page.check.file_status_detecting"))
        self.onlinefix_file_info.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 10px;
                margin-top: 2px;
            }
        """)

        # OnlineFix修复按钮
        self.onlinefix_restore_btn = QPushButton(t("config_page.button.restore_onlinefix"))
        self.onlinefix_restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 5px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 10px;
                margin-top: 2px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7dc4a0;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.onlinefix_restore_btn.clicked.connect(self.restore_onlinefix_files)
        self.onlinefix_restore_btn.setVisible(False)  # 默认隐藏，检测到问题时显示

        onlinefix_check_layout.addWidget(self.onlinefix_check_title)
        onlinefix_check_layout.addWidget(self.onlinefix_check_status)
        onlinefix_check_layout.addWidget(self.onlinefix_file_info)
        onlinefix_check_layout.addWidget(self.onlinefix_restore_btn)
        onlinefix_check_container.setLayout(onlinefix_check_layout)
        layout.addWidget(onlinefix_check_container, 0, 1)  # 第一行，第二列

        # 下半部分：steam_api64.dll检测区域
        dll_check_container = QWidget()
        dll_check_container.setMinimumHeight(100)  # 设置最小高度，允许动态扩展
        dll_check_layout = QHBoxLayout()  # 改为水平布局
        dll_check_layout.setContentsMargins(8, 8, 8, 8)
        dll_check_layout.setSpacing(12)

        # 左侧：状态信息区域
        dll_info_container = QWidget()
        dll_info_layout = QVBoxLayout()
        dll_info_layout.setContentsMargins(0, 0, 0, 0)
        dll_info_layout.setSpacing(6)

        # DLL检测标题
        self.dll_check_title = QLabel(t("config_page.check.dll_title"))
        self.dll_check_title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)

        # DLL文件状态
        self.dll_check_status = QLabel(t("config_page.check.detecting"))
        self.dll_check_status.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #fab387;
            }
        """)

        # DLL文件状态信息
        self.dll_size_info = QLabel(t("config_page.check.file_status_not_detected"))
        self.dll_size_info.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #1e1e2e;
                border-radius: 4px;
                border: 1px solid #313244;
            }
        """)

        dll_info_layout.addWidget(self.dll_check_title)
        dll_info_layout.addWidget(self.dll_check_status)
        dll_info_layout.addWidget(self.dll_size_info)
        dll_info_layout.addStretch()  # 添加弹性空间
        dll_info_container.setLayout(dll_info_layout)

        # 右侧：修复按钮区域
        dll_button_container = QWidget()
        dll_button_layout = QVBoxLayout()
        dll_button_layout.setContentsMargins(0, 0, 0, 0)
        dll_button_layout.setSpacing(0)

        # 一键恢复按钮
        self.dll_restore_btn = QPushButton(t("config_page.button.restore_dll"))
        self.dll_restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 5px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 11px;
                padding: 12px 16px;
                min-width: 120px;
                max-width: 140px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7dc4a0;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.dll_restore_btn.clicked.connect(self.restore_steam_api_dll)
        self.dll_restore_btn.setVisible(False)  # 默认隐藏，检测到问题时显示

        dll_button_layout.addStretch()  # 上方弹性空间
        dll_button_layout.addWidget(self.dll_restore_btn)
        dll_button_layout.addStretch()  # 下方弹性空间
        dll_button_container.setLayout(dll_button_layout)

        # 组装水平布局
        dll_check_layout.addWidget(dll_info_container, 2)  # 左侧占2/3空间
        dll_check_layout.addWidget(dll_button_container, 1)  # 右侧占1/3空间
        dll_check_container.setLayout(dll_check_layout)
        layout.addWidget(dll_check_container, 1, 0, 1, 2)  # 第二行，跨两列

        # 设置列的拉伸比例（让两列等宽）
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        # 设置行的拉伸策略 - 所有行都固定高度，不拉伸
        layout.setRowStretch(0, 0)  # 第一行：路径检查和OnlineFix检查，固定高度
        layout.setRowStretch(1, 0)  # 第二行：DLL检查，固定高度

        # 设置最小列宽，确保布局整齐
        layout.setColumnMinimumWidth(0, 200)
        layout.setColumnMinimumWidth(1, 200)

        self.system_check_section.setLayout(layout)
        return self.system_check_section

    def restore_steam_api_dll(self):
        """一键恢复steam_api64.dll文件"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.show_status(t("config_page.message.set_path_first"), "warning")
                return

            game_dir = os.path.dirname(game_path)
            steam_api_path = os.path.join(game_dir, "steam_api64.dll")

            # 检查原文件是否存在
            if not os.path.exists(steam_api_path):
                self.show_status(t("config_page.message.dll_not_found"), "warning")
                return

            # 检查OnlineFix文件夹中的dll文件
            onlinefix_dir = self.config_manager.onlinefix_dir
            onlinefix_dll = onlinefix_dir / "steam_api64.dll"

            if not onlinefix_dll.exists():
                self.show_status(t("config_page.message.onlinefix_dll_not_found"), "warning")
                return

            # 重命名原文件为.bak
            backup_path = steam_api_path + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)  # 删除已存在的备份文件

            os.rename(steam_api_path, backup_path)

            # 复制OnlineFix中的dll文件
            import shutil
            shutil.copy2(str(onlinefix_dll), steam_api_path)

            self.show_status(t("config_page.message.dll_restored"), "success")
            self.dll_restore_btn.setVisible(False)  # 隐藏恢复按钮
            self.check_system_status()  # 重新检测状态

        except Exception as e:
            self.show_status(t("config_page.message.restore_failed").format(error=str(e)), "error")

    def restore_onlinefix_files(self):
        """一键修复OnlineFix文件"""
        try:
            onlinefix_dir = self.config_manager.onlinefix_dir
            onlinefix_zip = onlinefix_dir / "OnlineFix.zip"

            if not onlinefix_zip.exists():
                self.show_status(t("config_page.message.no_zip"), "warning")
                return

            # 执行解压
            if self.extract_onlinefix_zip():
                self.show_status(t("config_page.message.onlinefix_fixed"), "success")
                self.onlinefix_restore_btn.setVisible(False)  # 隐藏修复按钮
                self.check_onlinefix_integrity()  # 重新检测状态
                self.check_steam_api_dll()  # 重新检测DLL状态
            else:
                self.show_status(t("config_page.message.fix_failed"), "error")

        except Exception as e:
            self.show_status(t("config_page.message.repair_failed").format(error=str(e)), "error")



    def extract_onlinefix_zip(self):
        """解压OnlineFix.zip文件"""
        try:
            import zipfile
            import time
            from pathlib import Path

            onlinefix_dir = self.config_manager.onlinefix_dir
            onlinefix_zip = onlinefix_dir / "OnlineFix.zip"
            extracted_flag = onlinefix_dir / ".onlinefix_extracted"

            if not onlinefix_zip.exists():
                print("❌ OnlineFix.zip文件不存在")
                return False

            print(f"📦 开始解压OnlineFix.zip: {onlinefix_zip}")

            # 解压文件到OnlineFix目录
            with zipfile.ZipFile(onlinefix_zip, 'r') as zip_ref:
                # 获取压缩包内的文件列表
                file_list = zip_ref.namelist()
                print(f"📋 压缩包包含 {len(file_list)} 个文件")

                # 解压所有文件
                for file_info in zip_ref.infolist():
                    # 跳过目录
                    if file_info.is_dir():
                        continue

                    # 获取文件名（去除路径）
                    filename = Path(file_info.filename).name
                    target_path = onlinefix_dir / filename

                    # 如果文件已存在，先删除
                    if target_path.exists():
                        target_path.unlink()

                    # 解压文件
                    with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                        import shutil
                        shutil.copyfileobj(source, target)

                    print(f"✅ 解压完成: {filename}")

            # 创建解压完成标志
            extracted_flag.write_text(f"OnlineFix extracted at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("🎉 OnlineFix解压完成")
            print("📦 原压缩包已保留")

            return True

        except Exception as e:
            print(f"❌ OnlineFix解压失败: {e}")
            return False

    def check_system_status(self):
        """检查系统状态（软件路径、OnlineFix完整性和DLL文件）"""
        self.check_software_path()
        self.check_onlinefix_integrity()
        self.check_steam_api_dll()

    def check_software_path(self):
        """检查软件路径是否合规"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.path_check_status.setText(t("config_page.check.path_not_set"))
                self.path_check_status.setStyleSheet("""
                    QLabel {
                        color: #6c7086;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #6c7086;
                    }
                """)
                self.path_check_info.setText(t("config_page.check.path_status_not_set"))
                self.path_check_warning.setVisible(False)
                return

            # 检查路径是否包含中文字符或在桌面上
            game_dir = os.path.dirname(game_path)

            # 检查是否包含中文字符
            def has_chinese(text):
                for char in text:
                    if '\u4e00' <= char <= '\u9fff':
                        return True
                return False

            # 检查是否在桌面上
            is_on_desktop = "Desktop" in game_dir or "桌面" in game_dir
            has_chinese_path = has_chinese(game_dir)

            if has_chinese_path or is_on_desktop:
                self.path_check_status.setText(t("config_page.check.path_invalid"))
                self.path_check_status.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                issues = []
                if has_chinese_path:
                    issues.append(t("config_page.check.has_chinese"))
                if is_on_desktop:
                    issues.append(t("config_page.check.on_desktop"))
                self.path_check_info.setText(t("config_page.check.issues").format(issues=', '.join(issues)))
                self.path_check_warning.setVisible(True)
            else:
                self.path_check_status.setText(t("config_page.check.path_valid"))
                self.path_check_status.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #a6e3a1;
                    }
                """)
                self.path_check_info.setText(t("config_page.check.path_status_valid"))
                self.path_check_warning.setVisible(False)

        except Exception as e:
            self.path_check_status.setText(t("config_page.check.detect_failed"))
            self.path_check_info.setText(t("config_page.check.detect_error").format(error=str(e)))
            self.path_check_warning.setVisible(False)

    def check_onlinefix_integrity(self):
        """检查OnlineFix文件夹完整性"""
        try:
            # 定义必需的OnlineFix文件
            required_files = {
                "steam_api64.dll": "Steam API库文件",
                "OnlineFix.ini": "破解配置文件",
                "OnlineFix64.dll": "主破解DLL",
                "winmm.dll": "多媒体API钩子",
                "dlllist.txt": "DLL列表文件"
            }

            onlinefix_dir = self.config_manager.onlinefix_dir
            missing_files = []

            # 检查每个必需文件
            for filename in required_files.keys():
                file_path = onlinefix_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if missing_files:
                # 有文件缺失
                self.onlinefix_check_status.setText(t("config_page.check.missing_files").format(count=len(missing_files)))
                self.onlinefix_check_status.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                self.onlinefix_file_info.setText(t("config_page.check.missing_list").format(files=', '.join(missing_files[:3]) + ('...' if len(missing_files) > 3 else '')))

                # 检查是否存在OnlineFix.zip用于修复
                onlinefix_zip = onlinefix_dir / "OnlineFix.zip"
                if onlinefix_zip.exists():
                    self.onlinefix_restore_btn.setVisible(True)
                else:
                    self.onlinefix_restore_btn.setVisible(False)
                    self.onlinefix_file_info.setText(t("config_page.check.missing_no_zip").format(files=', '.join(missing_files[:3])))
            else:
                # 所有文件完整
                self.onlinefix_check_status.setText(t("config_page.check.files_complete"))
                self.onlinefix_check_status.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #a6e3a1;
                    }
                """)
                self.onlinefix_file_info.setText(t("config_page.check.all_files_ok").format(count=len(required_files)))
                self.onlinefix_restore_btn.setVisible(False)

        except Exception as e:
            self.onlinefix_check_status.setText(t("config_page.check.detect_failed"))
            self.onlinefix_check_status.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 11px;
                    padding: 4px 8px;
                    background-color: #313244;
                    border-radius: 4px;
                    border: 1px solid #f38ba8;
                }
            """)
            self.onlinefix_file_info.setText(t("config_page.check.detect_error").format(error=str(e)))
            self.onlinefix_restore_btn.setVisible(False)

    def check_steam_api_dll(self):
        """检查steam_api64.dll文件状态"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.dll_check_status.setText(t("config_page.check.path_not_set"))
                self.dll_size_info.setText(t("config_page.check.file_status_not_detected"))
                self.dll_restore_btn.setVisible(False)
                return

            game_dir = os.path.dirname(game_path)
            steam_api_path = os.path.join(game_dir, "steam_api64.dll")

            # 使用统一的OnlineFix路径
            onlinefix_dir = self.config_manager.onlinefix_dir
            onlinefix_dll = onlinefix_dir / "steam_api64.dll"
            backup_dll = steam_api_path + ".bak"

            if not os.path.exists(steam_api_path):
                self.dll_check_status.setText(t("config_page.check.file_not_exist"))
                self.dll_check_status.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                self.dll_size_info.setText(t("config_page.check.file_status_not_exist"))
                self.dll_restore_btn.setVisible(False)
                return

            # 获取当前文件大小
            current_size = os.path.getsize(steam_api_path)
            current_size_kb = current_size / 1024

            # 检查是否存在备份文件和OnlineFix文件
            has_backup = os.path.exists(backup_dll)
            has_onlinefix = onlinefix_dll.exists()

            if has_onlinefix:
                onlinefix_size = onlinefix_dll.stat().st_size
                onlinefix_size_kb = onlinefix_size / 1024

                # 比较两个文件的大小
                if current_size != onlinefix_size:
                    # 文件大小不同，需要恢复
                    self.dll_check_status.setText(t("config_page.check.size_mismatch"))
                    self.dll_check_status.setStyleSheet("""
                        QLabel {
                            color: #fab387;
                            font-size: 11px;
                            padding: 4px 8px;
                            background-color: #313244;
                            border-radius: 4px;
                            border: 1px solid #fab387;
                        }
                    """)
                    self.dll_size_info.setText(t("config_page.check.size_compare").format(current=current_size_kb, target=onlinefix_size_kb))
                    self.dll_restore_btn.setVisible(True)
                else:
                    # 文件大小相同，正常状态
                    self.dll_check_status.setText(t("config_page.check.size_ok"))
                    self.dll_check_status.setStyleSheet("""
                        QLabel {
                            color: #a6e3a1;
                            font-size: 11px;
                            padding: 4px 8px;
                            background-color: #313244;
                            border-radius: 4px;
                            border: 1px solid #a6e3a1;
                        }
                    """)
                    self.dll_size_info.setText(t("config_page.check.file_size_normal").format(size=current_size_kb))
                    self.dll_restore_btn.setVisible(False)
            else:
                # 没有OnlineFix文件，无法进行修复
                self.dll_check_status.setText(t("config_page.check.missing_onlinefix"))
                self.dll_check_status.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 11px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                self.dll_size_info.setText(t("config_page.check.missing_onlinefix_file").format(size=current_size_kb))
                self.dll_restore_btn.setVisible(False)

        except Exception as e:
            self.dll_check_status.setText(t("config_page.check.detect_failed"))
            self.dll_size_info.setText(t("config_page.check.file_status_detect_failed"))
            self.dll_restore_btn.setVisible(False)



    def browse_game_path(self):
        """浏览游戏路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择游戏文件",
            "",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        
        if file_path:
            self.game_path_input.setText(file_path)
    
    def save_game_path(self):
        """保存游戏路径"""
        game_path = self.game_path_input.text().strip()

        if not game_path:
            self.show_status(t("config_page.message.select_path_first"), "warning")
            return

        if not game_path.lower().endswith('nightreign.exe'):
            self.show_status(t("config_page.message.select_exe"), "warning")
            return

        if not os.path.exists(game_path):
            self.show_status(t("config_page.message.file_not_exist"), "warning")
            return

        if self.config_manager.set_game_path(game_path):
            self.show_status(t("config_page.message.path_saved"), "success")
            self.update_status_display()
            self.status_updated.emit()
            # 路径更新后重新检查系统状态
            self.check_system_status()
        else:
            self.show_status(t("config_page.message.save_failed"), "error")
    
    def apply_crack(self):
        """应用破解"""
        if not self.config_manager.validate_game_path():
            self.show_status(t("config_page.message.set_valid_path"), "warning")
            return

        if self.config_manager.apply_crack():
            self.show_status(t("config_page.message.crack_applied"), "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status(t("config_page.message.apply_failed"), "error")

    def remove_crack(self):
        """移除破解"""
        if not self.config_manager.validate_game_path():
            self.show_status(t("config_page.message.set_valid_path"), "warning")
            return

        # 直接执行移除操作，不需要确认对话框
        if self.config_manager.remove_crack():
            self.show_status(t("config_page.message.crack_removed"), "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status(t("config_page.message.remove_failed"), "error")
    
    def load_current_config(self):
        """加载当前配置"""
        game_path = self.config_manager.get_game_path()
        if game_path:
            self.game_path_input.setText(game_path)

        self.update_status_display()

        # 自动检测游戏信息和软件路径信息
        self.auto_detect_info()
    
    def update_status_display(self):
        """更新状态显示"""
        # 更新游戏路径状态
        if self.config_manager.validate_game_path():
            self.path_status_label.setText(t("config_page.status.path_valid"))
            self.path_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 12px; margin-top: 5px; }")
        else:
            self.path_status_label.setText(t("config_page.status.path_invalid"))
            self.path_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 12px; margin-top: 5px; }")
        
        # 更新破解状态
        is_applied, status_info = self.config_manager.get_crack_status_info()
        game_valid = self.config_manager.validate_game_path()

        if is_applied:
            self.crack_status_label.setText(t("config_page.status.crack_applied"))
            self.crack_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")
            self.crack_detail_label.setVisible(False)
        else:
            self.crack_status_label.setText(t("config_page.status.crack_not_applied"))
            self.crack_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")

            # 显示详细的缺失信息
            if "缺失文件:" in status_info:
                # 格式化缺失文件信息为多行显示
                missing_files = status_info.replace("缺失文件: ", "").split(", ")
                detail_text = "⚠️ 检测到破解文件缺失：\n"
                for file in missing_files:
                    detail_text += f"• {file}\n"
                detail_text += "\n💡 建议点击'应用破解'按钮来修复缺失的文件"

                self.crack_detail_label.setText(detail_text)
                self.crack_detail_label.setVisible(True)
            else:
                self.crack_detail_label.setVisible(False)

        # 更新按钮状态
        self.apply_crack_btn.setEnabled(game_valid and not is_applied)
        self.remove_crack_btn.setEnabled(game_valid and is_applied)
    

    
    def show_status(self, message, status_type="info"):
        """显示状态信息"""
        if status_type == "success":
            color = "#a6e3a1"
            bg_color = "#1e1e2e"
        elif status_type == "warning":
            color = "#fab387"
            bg_color = "#313244"
        elif status_type == "error":
            color = "#f38ba8"
            bg_color = "#313244"
        else:  # info
            color = "#89b4fa"
            bg_color = "#313244"

        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                padding: 10px;
                background-color: {bg_color};
                border-radius: 6px;
                border: 1px solid {color};
                margin-bottom: 15px;
            }}
        """)
        self.status_label.setVisible(True)

        # 3秒后自动隐藏
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setVisible(False))

    def create_game_info_section_widget(self):
        """创建游戏信息检测区域widget"""
        self.game_info_section = ConfigSection(t("config_page.section.game_info"))
        # 设置尺寸策略：允许适度扩展以容纳信息显示
        from PySide6.QtWidgets import QSizePolicy
        self.game_info_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)  # 减少垂直间距

        # 标题和按钮行
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)  # 减少水平间距

        self.game_info_label = QLabel(t("config_page.form.game_info_hint"))
        self.game_info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        self.game_detect_btn = QPushButton(t("config_page.button.detect"))
        self.game_detect_btn.setFixedWidth(60)
        self.game_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        self.game_detect_btn.clicked.connect(self.detect_game_info)

        header_layout.addWidget(self.game_info_label)
        header_layout.addStretch()
        header_layout.addWidget(self.game_detect_btn)
        header_row.setLayout(header_layout)
        main_layout.addWidget(header_row)

        # 信息显示网格
        info_grid = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(6)  # 减少网格间距
        grid_layout.setVerticalSpacing(8)  # 设置垂直间距

        # 游戏版本
        self.game_version_label = QLabel(t("config_page.form.game_version"))
        self.game_version_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.game_version_value = QLabel(t("config_page.info.not_detected"))
        self.game_version_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        # DLL文件信息
        self.dll_info_label = QLabel(t("config_page.form.dll_info"))
        self.dll_info_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.dll_info_value = QLabel(t("config_page.info.not_detected"))
        self.dll_info_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        # 添加到网格
        grid_layout.addWidget(self.game_version_label, 0, 0)
        grid_layout.addWidget(self.game_version_value, 0, 1)
        grid_layout.addWidget(self.dll_info_label, 1, 0)
        grid_layout.addWidget(self.dll_info_value, 1, 1)

        # 设置列拉伸
        grid_layout.setColumnStretch(1, 1)

        info_grid.setLayout(grid_layout)
        main_layout.addWidget(info_grid)

        self.game_info_section.setLayout(main_layout)
        return self.game_info_section

    def create_software_info_section_widget(self):
        """创建软件路径检测区域widget"""
        self.software_info_section = ConfigSection(t("config_page.section.software_info"))
        # 设置尺寸策略：允许适度扩展以容纳信息显示
        from PySide6.QtWidgets import QSizePolicy
        self.software_info_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)  # 与游戏信息检测区域保持一致

        # 标题和按钮行
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)  # 与游戏信息检测区域保持一致

        self.software_info_label = QLabel(t("config_page.form.software_info_hint"))
        self.software_info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        self.software_detect_btn = QPushButton(t("config_page.button.detect"))
        self.software_detect_btn.setFixedWidth(60)
        self.software_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d4bbf9;
            }
            QPushButton:pressed {
                background-color: #b491f5;
            }
        """)
        self.software_detect_btn.clicked.connect(self.detect_software_info)

        header_layout.addWidget(self.software_info_label)
        header_layout.addStretch()
        header_layout.addWidget(self.software_detect_btn)
        header_row.setLayout(header_layout)
        main_layout.addWidget(header_row)

        # 信息显示网格（与游戏信息检测区域保持一致）
        info_grid = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(6)  # 与游戏信息检测区域保持一致
        grid_layout.setVerticalSpacing(8)  # 设置垂直间距

        # 软件路径
        self.software_path_label = QLabel(t("config_page.form.software_path"))
        self.software_path_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.software_path_value = QLabel(t("config_page.check.detecting"))
        self.software_path_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        self.software_path_value.setWordWrap(True)

        # 中文字符检测
        self.chinese_char_label = QLabel(t("config_page.form.chinese_char"))
        self.chinese_char_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.chinese_status_value = QLabel(t("config_page.check.detecting"))
        self.chinese_status_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        # 桌面位置检测
        self.desktop_loc_label = QLabel(t("config_page.form.desktop_loc"))
        self.desktop_loc_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.desktop_status_value = QLabel(t("config_page.check.detecting"))
        self.desktop_status_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        # 综合安全性
        self.safety_label = QLabel(t("config_page.form.safety"))
        self.safety_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.safety_status_value = QLabel(t("config_page.check.detecting"))
        self.safety_status_value.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        # 添加到网格（4行2列）
        grid_layout.addWidget(self.software_path_label, 0, 0)
        grid_layout.addWidget(self.software_path_value, 0, 1)
        grid_layout.addWidget(self.chinese_char_label, 1, 0)
        grid_layout.addWidget(self.chinese_status_value, 1, 1)
        grid_layout.addWidget(self.desktop_loc_label, 2, 0)
        grid_layout.addWidget(self.desktop_status_value, 2, 1)
        grid_layout.addWidget(self.safety_label, 3, 0)
        grid_layout.addWidget(self.safety_status_value, 3, 1)

        # 设置列拉伸
        grid_layout.setColumnStretch(1, 1)

        info_grid.setLayout(grid_layout)
        main_layout.addWidget(info_grid)

        self.software_info_section.setLayout(main_layout)
        return self.software_info_section

    def detect_game_info(self):
        """检测游戏信息"""
        try:
            # 获取游戏信息
            game_info = self.config_manager.get_game_info()

            # 更新版本显示
            version = game_info.get('nightreign_version')
            if version:
                self.game_version_value.setText(version)
                self.game_version_value.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)
            else:
                self.game_version_value.setText(t("config_page.info.unavailable"))
                self.game_version_value.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)

            # 更新DLL信息显示
            dll_size = game_info.get('steam_api_size')
            dll_exists = game_info.get('steam_api_exists', False)

            if dll_exists and dll_size:
                size_mb = dll_size / (1024 * 1024)
                dll_text = f"{dll_size:,} 字节 ({size_mb:.2f} MB)"
                self.dll_info_value.setText(dll_text)
                self.dll_info_value.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)
            else:
                self.dll_info_value.setText(t("config_page.info.file_not_found"))
                self.dll_info_value.setStyleSheet("""
                    QLabel {
                        color: #fab387;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)

            # 显示状态消息
            if game_info.get('error'):
                self.show_status(t("config_page.message.detect_failed").format(error=game_info['error']), "error")
            else:
                self.show_status(t("config_page.message.game_info_done"), "success")

        except Exception as e:
            self.show_status(t("config_page.message.game_info_error").format(error=str(e)), "error")
            self.game_version_value.setText(t("config_page.info.failed"))
            self.dll_info_value.setText(t("config_page.info.failed"))

    def detect_software_info(self):
        """检测软件路径信息"""
        try:
            # 获取软件信息
            nmodm_info = self.config_manager.get_nmodm_info()

            # 更新路径显示
            nmodm_path = nmodm_info.get('nmodm_path', '未知')
            self.software_path_value.setText(nmodm_path)

            # 更新中文字符检测
            has_chinese = nmodm_info.get('has_chinese', False)
            chinese_chars = nmodm_info.get('chinese_characters', [])

            if has_chinese:
                chinese_text = t("config_page.info.has_chinese").format(chars=', '.join(chinese_chars))
                self.chinese_status_value.setText(chinese_text)
                self.chinese_status_value.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)
            else:
                self.chinese_status_value.setText(t("config_page.info.no_chinese"))
                self.chinese_status_value.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)

            # 更新桌面位置检测
            is_on_desktop = nmodm_info.get('is_on_desktop', False)

            if is_on_desktop:
                self.desktop_status_value.setText(t("config_page.info.on_desktop"))
                self.desktop_status_value.setStyleSheet("""
                    QLabel {
                        color: #fab387;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)
            else:
                self.desktop_status_value.setText(t("config_page.info.not_on_desktop"))
                self.desktop_status_value.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)

            # 更新综合安全性
            overall_safe = nmodm_info.get('overall_safe', False)

            if overall_safe:
                self.safety_status_value.setText(t("config_page.info.safe"))
                self.safety_status_value.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)
            else:
                warnings = nmodm_info.get('all_warnings', [])
                warning_text = t("config_page.info.warning").format(warning=f"{len(warnings)}项" if warnings else "")

                self.safety_status_value.setText(warning_text)
                self.safety_status_value.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 13px;
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 4px;
                        padding: 5px 10px;
                    }
                """)

            # 显示状态消息
            if nmodm_info.get('error'):
                self.show_status(t("config_page.message.detect_failed").format(error=nmodm_info['error']), "error")
            else:
                self.show_status(t("config_page.message.software_info_done"), "success")

        except Exception as e:
            self.show_status(t("config_page.message.software_info_error").format(error=str(e)), "error")
            self.software_path_value.setText(t("config_page.info.failed"))
            self.chinese_status_value.setText(t("config_page.info.failed"))
            self.desktop_status_value.setText(t("config_page.info.failed"))
            self.safety_status_value.setText(t("config_page.info.failed"))

    def auto_detect_info(self):
        """自动检测信息（页面加载时调用）"""
        # 使用QTimer延迟执行，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self.detect_software_info)  # 先检测软件信息
        QTimer.singleShot(1000, self.detect_game_info)     # 再检测游戏信息

    def _on_language_changed(self, locale: str):
        """语言切换回调"""
        # 更新页面标题
        self.title_label.setText(t("config_page.page_title"))

        # 更新游戏路径配置区域
        if hasattr(self, 'game_path_section'):
            self.game_path_section.set_title(t("config_page.section.game_path"))
        if hasattr(self, 'game_path_info_label'):
            self.game_path_info_label.setText(t("config_page.form.game_path_hint"))
        if hasattr(self, 'game_path_input'):
            self.game_path_input.setPlaceholderText(t("config_page.form.game_path_placeholder"))
        if hasattr(self, 'browse_btn'):
            self.browse_btn.setText(t("config_page.button.browse"))
        if hasattr(self, 'save_btn'):
            self.save_btn.setText(t("config_page.button.save"))

        # 更新破解文件管理区域
        if hasattr(self, 'crack_section'):
            self.crack_section.set_title(t("config_page.section.crack"))
        if hasattr(self, 'crack_info_label'):
            self.crack_info_label.setText(t("config_page.form.crack_hint"))
        if hasattr(self, 'apply_crack_btn'):
            self.apply_crack_btn.setText(t("config_page.button.apply_crack"))
        if hasattr(self, 'remove_crack_btn'):
            self.remove_crack_btn.setText(t("config_page.button.remove_crack"))
        if hasattr(self, 'crack_files_info_label'):
            self.crack_files_info_label.setText(t("config_page.form.crack_files"))

        # 更新系统检查与修复区域
        if hasattr(self, 'system_check_section'):
            self.system_check_section.set_title(t("config_page.section.system_check"))
        if hasattr(self, 'path_check_title'):
            self.path_check_title.setText(t("config_page.check.path_title"))
        if hasattr(self, 'path_check_warning'):
            self.path_check_warning.setText(t("config_page.message.path_warning"))
        if hasattr(self, 'onlinefix_check_title'):
            self.onlinefix_check_title.setText(t("config_page.check.onlinefix_title"))
        if hasattr(self, 'onlinefix_restore_btn'):
            self.onlinefix_restore_btn.setText(t("config_page.button.restore_onlinefix"))
        if hasattr(self, 'dll_check_title'):
            self.dll_check_title.setText(t("config_page.check.dll_title"))
        if hasattr(self, 'dll_restore_btn'):
            self.dll_restore_btn.setText(t("config_page.button.restore_dll"))

        # 更新游戏信息检测区域
        if hasattr(self, 'game_info_section'):
            self.game_info_section.set_title(t("config_page.section.game_info"))
        if hasattr(self, 'game_info_label'):
            self.game_info_label.setText(t("config_page.form.game_info_hint"))
        if hasattr(self, 'game_detect_btn'):
            self.game_detect_btn.setText(t("config_page.button.detect"))
        if hasattr(self, 'game_version_label'):
            self.game_version_label.setText(t("config_page.form.game_version"))
        if hasattr(self, 'dll_info_label'):
            self.dll_info_label.setText(t("config_page.form.dll_info"))

        # 更新软件路径检测区域
        if hasattr(self, 'software_info_section'):
            self.software_info_section.set_title(t("config_page.section.software_info"))
        if hasattr(self, 'software_info_label'):
            self.software_info_label.setText(t("config_page.form.software_info_hint"))
        if hasattr(self, 'software_detect_btn'):
            self.software_detect_btn.setText(t("config_page.button.detect"))
        if hasattr(self, 'software_path_label'):
            self.software_path_label.setText(t("config_page.form.software_path"))
        if hasattr(self, 'chinese_char_label'):
            self.chinese_char_label.setText(t("config_page.form.chinese_char"))
        if hasattr(self, 'desktop_loc_label'):
            self.desktop_loc_label.setText(t("config_page.form.desktop_loc"))
        if hasattr(self, 'safety_label'):
            self.safety_label.setText(t("config_page.form.safety"))

        # 刷新状态显示
        self.update_status_display()
