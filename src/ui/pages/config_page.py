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


class ConfigPage(BasePage):
    """基础配置页面"""
    
    # 状态更新信号
    status_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__("基础配置", parent)
        self.config_manager = ConfigManager()
        self.setup_content()
        self.load_current_config()
        # 初始化系统检查
        self.check_system_status()
    
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
        section = ConfigSection("游戏路径配置")
        # 设置智能布局策略：保持紧凑的高度，水平方向可扩展
        from PySide6.QtWidgets import QSizePolicy
        section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        # 应用专门的紧凑样式
        section.setStyleSheet(section.styleSheet() + """
            QGroupBox[title="游戏路径配置"] {
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

        info_label = QLabel("请选择 nightreign.exe 游戏文件的路径")
        info_label.setStyleSheet("""
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

        top_layout.addWidget(info_label)
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
        self.game_path_input.setPlaceholderText("请选择游戏文件路径...")
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
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet("""
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
        browse_btn.clicked.connect(self.browse_game_path)

        # 保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_game_path)

        input_layout.addWidget(self.game_path_input)
        input_layout.addWidget(browse_btn)
        input_layout.addWidget(save_btn)
        input_row.setLayout(input_layout)
        main_layout.addWidget(input_row)

        section.setLayout(main_layout)
        return section
    
    def create_crack_section_widget(self):
        """创建破解管理区域widget"""
        section = ConfigSection("破解文件管理")
        # 设置尺寸策略：保持紧凑，避免空间浪费
        from PySide6.QtWidgets import QSizePolicy
        section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        layout = QVBoxLayout()
        layout.setSpacing(12)  # 优化垂直间距，充分利用空间

        # 顶部：说明文本和状态显示（水平布局）
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        info_label = QLabel("管理OnlineFix破解文件的应用和移除")
        info_label.setStyleSheet("""
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

        header_layout.addWidget(info_label)
        header_layout.addStretch()
        header_layout.addWidget(self.crack_status_label)
        header_row.setLayout(header_layout)
        layout.addWidget(header_row)

        # 按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)  # 减少按钮间距

        # 应用破解按钮
        self.apply_crack_btn = QPushButton("应用破解")
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
        self.remove_crack_btn = QPushButton("移除破解")
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
        files_info_label = QLabel("破解文件: dlllist.txt, OnlineFix.ini, OnlineFix64.dll, winmm.dll")
        files_info_label.setStyleSheet("""
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
        layout.addWidget(files_info_label)

        section.setLayout(layout)
        return section

    def create_system_check_section_widget(self):
        """创建系统检查与修复区域widget"""
        section = ConfigSection("系统检查与修复")
        # 设置尺寸策略：最小化空间占用
        from PySide6.QtWidgets import QSizePolicy
        section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        layout = QVBoxLayout()
        layout.setSpacing(15)  # 增加间距，与其他区域保持一致
        layout.setContentsMargins(8, 8, 8, 8)  # 添加内边距

        # 上半部分：软件路径检测提醒
        path_check_container = QWidget()
        path_check_layout = QVBoxLayout()
        path_check_layout.setContentsMargins(0, 0, 0, 0)
        path_check_layout.setSpacing(6)

        # 软件路径检测标题
        path_check_title = QLabel("📍 软件路径检测")
        path_check_title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)

        # 软件路径检测状态
        self.path_check_status = QLabel("检测中...")
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

        # 路径检测提醒文本
        self.path_check_warning = QLabel("⚠️ 游戏路径包含中文字符或位于桌面，可能导致运行异常")
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

        path_check_layout.addWidget(path_check_title)
        path_check_layout.addWidget(self.path_check_status)
        path_check_layout.addWidget(self.path_check_warning)
        path_check_container.setLayout(path_check_layout)
        layout.addWidget(path_check_container)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: #45475a;
                background-color: #45475a;
                border: none;
                max-height: 1px;
                margin: 8px 0px;
            }
        """)
        layout.addWidget(separator)

        # 下半部分：steam_api64.dll检测区域
        dll_check_container = QWidget()
        dll_check_layout = QVBoxLayout()
        dll_check_layout.setContentsMargins(0, 0, 0, 0)
        dll_check_layout.setSpacing(6)

        # DLL检测标题
        dll_check_title = QLabel("🔧 steam_api64.dll检测")
        dll_check_title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)

        # DLL文件状态
        self.dll_check_status = QLabel("检测中...")
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
        self.dll_size_info = QLabel("文件状态: 未检测")
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

        # 一键恢复按钮
        self.dll_restore_btn = QPushButton("🔧 一键修复 steam_api64.dll")
        self.dll_restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 5px;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 11px;
                padding: 8px 12px;
                margin-top: 4px;
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

        dll_check_layout.addWidget(dll_check_title)
        dll_check_layout.addWidget(self.dll_check_status)
        dll_check_layout.addWidget(self.dll_size_info)
        dll_check_layout.addWidget(self.dll_restore_btn)
        dll_check_container.setLayout(dll_check_layout)
        layout.addWidget(dll_check_container)

        section.setLayout(layout)
        return section

    def restore_steam_api_dll(self):
        """一键恢复steam_api64.dll文件"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.show_status("请先配置游戏路径", "warning")
                return

            game_dir = os.path.dirname(game_path)
            steam_api_path = os.path.join(game_dir, "steam_api64.dll")

            # 检查原文件是否存在
            if not os.path.exists(steam_api_path):
                self.show_status("未找到steam_api64.dll文件", "warning")
                return

            # 检查OnlineFix文件夹中的dll文件（在项目根目录下）
            onlinefix_dir = os.path.join(os.getcwd(), "OnlineFix")
            onlinefix_dll = os.path.join(onlinefix_dir, "steam_api64.dll")

            if not os.path.exists(onlinefix_dll):
                self.show_status("未找到OnlineFix文件夹中的steam_api64.dll", "warning")
                return

            # 重命名原文件为.bak
            backup_path = steam_api_path + ".bak"
            if os.path.exists(backup_path):
                os.remove(backup_path)  # 删除已存在的备份文件

            os.rename(steam_api_path, backup_path)

            # 复制OnlineFix中的dll文件
            import shutil
            shutil.copy2(onlinefix_dll, steam_api_path)

            self.show_status("steam_api64.dll恢复成功", "success")
            self.dll_restore_btn.setVisible(False)  # 隐藏恢复按钮
            self.check_system_status()  # 重新检测状态

        except Exception as e:
            self.show_status(f"恢复失败: {str(e)}", "error")

    def check_system_status(self):
        """检查系统状态（软件路径和DLL文件）"""
        self.check_software_path()
        self.check_steam_api_dll()

    def check_software_path(self):
        """检查软件路径是否合规"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.path_check_status.setText("未配置游戏路径")
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
                self.path_check_status.setText("❌ 路径不合规")
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
                self.path_check_warning.setVisible(True)
            else:
                self.path_check_status.setText("✅ 路径合规")
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
                self.path_check_warning.setVisible(False)

        except Exception as e:
            self.path_check_status.setText("检测失败")
            self.path_check_warning.setVisible(False)

    def check_steam_api_dll(self):
        """检查steam_api64.dll文件状态"""
        try:
            game_path = self.config_manager.get_game_path()
            if not game_path:
                self.dll_check_status.setText("未配置游戏路径")
                self.dll_size_info.setText("文件状态: 未检测")
                self.dll_restore_btn.setVisible(False)
                return

            game_dir = os.path.dirname(game_path)
            steam_api_path = os.path.join(game_dir, "steam_api64.dll")

            # OnlineFix文件夹在项目根目录下
            onlinefix_dir = os.path.join(os.getcwd(), "OnlineFix")
            onlinefix_dll = os.path.join(onlinefix_dir, "steam_api64.dll")
            backup_dll = steam_api_path + ".bak"

            if not os.path.exists(steam_api_path):
                self.dll_check_status.setText("❌ 文件不存在")
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
                self.dll_size_info.setText("文件状态: 文件不存在")
                self.dll_restore_btn.setVisible(False)
                return

            # 获取当前文件大小
            current_size = os.path.getsize(steam_api_path)
            current_size_kb = current_size / 1024

            # 检查是否存在备份文件和OnlineFix文件
            has_backup = os.path.exists(backup_dll)
            has_onlinefix = os.path.exists(onlinefix_dll)

            if has_onlinefix:
                onlinefix_size = os.path.getsize(onlinefix_dll)
                onlinefix_size_kb = onlinefix_size / 1024

                # 比较两个文件的大小
                if current_size != onlinefix_size:
                    # 文件大小不同，需要恢复
                    self.dll_check_status.setText("⚠️ 文件大小不匹配")
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
                    self.dll_size_info.setText(f"当前: {current_size_kb:.1f} KB | 目标: {onlinefix_size_kb:.1f} KB")
                    self.dll_restore_btn.setVisible(True)
                else:
                    # 文件大小相同，正常状态
                    self.dll_check_status.setText("✅ 文件大小正常")
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
                    self.dll_size_info.setText(f"文件大小: {current_size_kb:.1f} KB (正常)")
                    self.dll_restore_btn.setVisible(False)
            else:
                # 没有OnlineFix文件，无法进行修复
                self.dll_check_status.setText("❌ 缺少OnlineFix")
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
                self.dll_size_info.setText(f"文件状态: 缺少OnlineFix文件 ({current_size_kb:.1f} KB)")
                self.dll_restore_btn.setVisible(False)

        except Exception as e:
            self.dll_check_status.setText("检测失败")
            self.dll_size_info.setText("文件状态: 检测失败")
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
            self.show_status("请先选择游戏文件路径", "warning")
            return

        if not game_path.lower().endswith('nightreign.exe'):
            self.show_status("请选择 nightreign.exe 文件", "warning")
            return

        if not os.path.exists(game_path):
            self.show_status("选择的文件不存在", "warning")
            return

        if self.config_manager.set_game_path(game_path):
            self.show_status("游戏路径保存成功", "success")
            self.update_status_display()
            self.status_updated.emit()
            # 路径更新后重新检查系统状态
            self.check_system_status()
        else:
            self.show_status("保存游戏路径失败", "error")
    
    def apply_crack(self):
        """应用破解"""
        if not self.config_manager.validate_game_path():
            self.show_status("请先配置有效的游戏路径", "warning")
            return

        if self.config_manager.apply_crack():
            self.show_status("破解文件应用成功", "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status("应用破解失败", "error")
    
    def remove_crack(self):
        """移除破解"""
        if not self.config_manager.validate_game_path():
            self.show_status("请先配置有效的游戏路径", "warning")
            return

        # 直接执行移除操作，不需要确认对话框
        if self.config_manager.remove_crack():
            self.show_status("破解文件移除成功", "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status("移除破解失败", "error")
    
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
            self.path_status_label.setText("✅ 游戏路径配置正确")
            self.path_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 12px; margin-top: 5px; }")
        else:
            self.path_status_label.setText("❌ 游戏路径无效或未配置")
            self.path_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 12px; margin-top: 5px; }")
        
        # 更新破解状态
        is_applied = self.config_manager.is_crack_applied()
        game_valid = self.config_manager.validate_game_path()
        
        if is_applied:
            self.crack_status_label.setText("✅ 破解已应用")
            self.crack_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")
        else:
            self.crack_status_label.setText("❌ 破解未应用")
            self.crack_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")
        
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
        section = ConfigSection("游戏信息检测")
        # 设置尺寸策略：允许适度扩展以容纳信息显示
        from PySide6.QtWidgets import QSizePolicy
        section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)  # 减少垂直间距

        # 标题和按钮行
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)  # 减少水平间距

        info_label = QLabel("检测游戏版本和相关文件信息")
        info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        detect_btn = QPushButton("检测")
        detect_btn.setFixedWidth(60)
        detect_btn.setStyleSheet("""
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
        detect_btn.clicked.connect(self.detect_game_info)

        header_layout.addWidget(info_label)
        header_layout.addStretch()
        header_layout.addWidget(detect_btn)
        header_row.setLayout(header_layout)
        main_layout.addWidget(header_row)

        # 信息显示网格
        info_grid = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(6)  # 减少网格间距
        grid_layout.setVerticalSpacing(8)  # 设置垂直间距

        # 游戏版本
        version_label = QLabel("游戏版本:")
        version_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.game_version_value = QLabel("未检测")
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
        dll_label = QLabel("steam_api64.dll:")
        dll_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.dll_info_value = QLabel("未检测")
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
        grid_layout.addWidget(version_label, 0, 0)
        grid_layout.addWidget(self.game_version_value, 0, 1)
        grid_layout.addWidget(dll_label, 1, 0)
        grid_layout.addWidget(self.dll_info_value, 1, 1)

        # 设置列拉伸
        grid_layout.setColumnStretch(1, 1)

        info_grid.setLayout(grid_layout)
        main_layout.addWidget(info_grid)

        section.setLayout(main_layout)
        return section

    def create_software_info_section_widget(self):
        """创建软件路径检测区域widget"""
        section = ConfigSection("软件路径检测")
        # 设置尺寸策略：允许适度扩展以容纳信息显示
        from PySide6.QtWidgets import QSizePolicy
        section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)  # 与游戏信息检测区域保持一致

        # 标题和按钮行
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)  # 与游戏信息检测区域保持一致

        info_label = QLabel("检测Nmodm软件路径的安全性")
        info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
            }
        """)

        detect_software_btn = QPushButton("检测")
        detect_software_btn.setFixedWidth(60)
        detect_software_btn.setStyleSheet("""
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
        detect_software_btn.clicked.connect(self.detect_software_info)

        header_layout.addWidget(info_label)
        header_layout.addStretch()
        header_layout.addWidget(detect_software_btn)
        header_row.setLayout(header_layout)
        main_layout.addWidget(header_row)

        # 信息显示网格（与游戏信息检测区域保持一致）
        info_grid = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(6)  # 与游戏信息检测区域保持一致
        grid_layout.setVerticalSpacing(8)  # 设置垂直间距

        # 软件路径
        path_label = QLabel("软件路径:")
        path_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.software_path_value = QLabel("检测中...")
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
        chinese_label = QLabel("中文字符:")
        chinese_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.chinese_status_value = QLabel("检测中...")
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
        desktop_label = QLabel("桌面位置:")
        desktop_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.desktop_status_value = QLabel("检测中...")
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
        safety_label = QLabel("综合安全:")
        safety_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.safety_status_value = QLabel("检测中...")
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
        grid_layout.addWidget(path_label, 0, 0)
        grid_layout.addWidget(self.software_path_value, 0, 1)
        grid_layout.addWidget(chinese_label, 1, 0)
        grid_layout.addWidget(self.chinese_status_value, 1, 1)
        grid_layout.addWidget(desktop_label, 2, 0)
        grid_layout.addWidget(self.desktop_status_value, 2, 1)
        grid_layout.addWidget(safety_label, 3, 0)
        grid_layout.addWidget(self.safety_status_value, 3, 1)

        # 设置列拉伸
        grid_layout.setColumnStretch(1, 1)

        info_grid.setLayout(grid_layout)
        main_layout.addWidget(info_grid)

        section.setLayout(main_layout)
        return section

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
                self.game_version_value.setText("无法获取")
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
                self.dll_info_value.setText("文件不存在")
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
                self.show_status(f"检测失败: {game_info['error']}", "error")
            else:
                self.show_status("游戏信息检测完成", "success")

        except Exception as e:
            self.show_status(f"检测游戏信息时出错: {e}", "error")
            self.game_version_value.setText("检测失败")
            self.dll_info_value.setText("检测失败")

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
                chinese_text = f"包含中文: {', '.join(chinese_chars)}"
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
                self.chinese_status_value.setText("无中文字符")
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
                self.desktop_status_value.setText("在桌面上")
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
                self.desktop_status_value.setText("不在桌面")
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
                self.safety_status_value.setText("安全")
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
                warning_text = "有风险"
                if warnings:
                    warning_text = f"有风险 ({len(warnings)}项)"

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
                self.show_status(f"检测失败: {nmodm_info['error']}", "error")
            else:
                self.show_status("软件路径检测完成", "success")

        except Exception as e:
            self.show_status(f"检测软件路径时出错: {e}", "error")
            self.software_path_value.setText("检测失败")
            self.chinese_status_value.setText("检测失败")
            self.desktop_status_value.setText("检测失败")
            self.safety_status_value.setText("检测失败")

    def auto_detect_info(self):
        """自动检测信息（页面加载时调用）"""
        # 使用QTimer延迟执行，避免阻塞UI
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self.detect_software_info)  # 先检测软件信息
        QTimer.singleShot(1000, self.detect_game_info)     # 再检测游戏信息
