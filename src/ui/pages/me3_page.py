"""
工具下载页面
ME3工具和EasyTier下载管理
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QFrame, QGroupBox,
                               QTextEdit, QComboBox, QRadioButton)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from .base_page import BasePage


class StatusCheckWorker(QThread):
    """状态检查工作线程"""
    status_checked = Signal(dict)  # 发送状态检查结果

    def __init__(self, download_manager):
        super().__init__()
        self.download_manager = download_manager

    def run(self):
        """在后台线程中检查状态"""
        try:
            # 检查所有工具的状态（本地检查，速度快）
            status_info = {
                'me3_installed': self.download_manager.is_me3_installed(),
                'me3_full_installed': self.download_manager.is_me3_full_installed(),
                'me3_install_type': self.download_manager.get_me3_install_type(),
                'me3_version': self.download_manager.get_current_version(),
                'me3_full_version': self.download_manager.get_me3_full_version(),
                'easytier_version': self.download_manager.get_current_easytier_version(),
                'installer_exists': (self.download_manager.me3_dir / "me3_installer.exe").exists()
            }
            self.status_checked.emit(status_info)
        except Exception as e:
            print(f"状态检查失败: {e}")
            # 发送空状态，让UI显示默认状态
            self.status_checked.emit({})


class UpdateCheckWorker(QThread):
    """更新检查工作线程"""
    me3_update_checked = Signal(dict)
    easytier_update_checked = Signal(dict)

    def __init__(self, download_manager, include_prerelease=False):
        super().__init__()
        self.download_manager = download_manager
        self.include_prerelease = include_prerelease

    def run(self):
        """在后台线程中检查更新"""
        # 检查ME3更新
        try:
            release_info = self.download_manager.get_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                current_version = self.download_manager.get_current_version()
                self.me3_update_checked.emit({
                    'success': True,
                    'latest_version': latest_version,
                    'current_version': current_version
                })
            else:
                self.me3_update_checked.emit({'success': False, 'error': '无法获取版本信息'})
        except Exception as e:
            self.me3_update_checked.emit({'success': False, 'error': str(e)})

        # 检查EasyTier更新
        try:
            has_update, latest_version, message = self.download_manager.check_easytier_update(self.include_prerelease)
            current_version = self.download_manager.get_current_easytier_version()
            self.easytier_update_checked.emit({
                'success': True,
                'has_update': has_update,
                'latest_version': latest_version,
                'current_version': current_version,
                'message': message,
                'include_prerelease': self.include_prerelease
            })
        except Exception as e:
            self.easytier_update_checked.emit({'success': False, 'error': str(e)})


class VersionInfoCard(QFrame):
    """版本信息卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.latest_version = None  # 添加latest_version属性
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            VersionInfoCard {
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        # 使用水平布局，紧凑排列
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(20)

        # 左侧：当前版本和最新版本
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        # 当前版本
        self.current_version_label = QLabel("当前版本: 未安装")
        self.current_version_label.setFixedHeight(28)
        self.current_version_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0px;
            }
        """)

        # 最新版本
        self.latest_version_label = QLabel("最新版本: 检查中...")
        self.latest_version_label.setFixedHeight(28)
        self.latest_version_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0px;
            }
        """)

        left_layout.addWidget(self.current_version_label)
        left_layout.addWidget(self.latest_version_label)

        # 右侧：状态
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)

        # 状态
        self.status_label = QLabel("状态: 未安装")
        self.status_label.setFixedHeight(60)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f38ba8;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
                border: 2px solid #f38ba8;
            }
        """)

        right_layout.addWidget(self.status_label)

        # 添加到主布局
        main_layout.addLayout(left_layout, 2)  # 左侧占2份
        main_layout.addLayout(right_layout, 1)  # 右侧占1份

        self.setLayout(main_layout)
    
    def update_info(self, current_version=None, latest_version=None, status=None, version_type=None, current_version_type=None):
        """更新版本信息"""
        if current_version is not None:
            current_text = f"当前版本: {current_version or '未安装'}"
            if current_version and current_version_type:
                current_text += f" ({current_version_type})"
            self.current_version_label.setText(current_text)

        if latest_version is not None:
            self.latest_version = latest_version  # 保存latest_version
            latest_text = f"最新版本: {latest_version or '获取失败'}"
            if version_type:
                latest_text += f" ({version_type})"
            self.latest_version_label.setText(latest_text)
        
        if status is not None:
            # 根据状态设置不同的颜色和样式
            if any(keyword in status for keyword in ["已安装", "安装完成", "已是最新版本", "最新版本", "已是最新正式版", "已是最新预发行版"]):
                # 成功状态：绿色
                color = "#a6e3a1"
                border_color = "#a6e3a1"
                bg_color = "#1e1e2e"
            elif any(keyword in status for keyword in ["检查中", "下载中", "安装中", "正在"]):
                # 进行中状态：橙色
                color = "#fab387"
                border_color = "#fab387"
                bg_color = "#313244"
            elif any(keyword in status for keyword in ["未安装", "未知"]):
                # 未安装状态：蓝色
                color = "#89b4fa"
                border_color = "#89b4fa"
                bg_color = "#313244"
            else:
                # 错误状态：红色
                color = "#f38ba8"
                border_color = "#f38ba8"
                bg_color = "#313244"

            self.status_label.setText(f"状态: {status}")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 16px;
                    font-weight: bold;
                    padding: 8px 12px;
                    border-radius: 6px;
                    border: 2px solid {border_color};
                }}
            """)


class ToolDownloadPage(BasePage):
    """工具下载页面"""

    # 状态更新信号
    status_updated = Signal()

    def __init__(self, parent=None):
        super().__init__("工具下载", parent)
        self.download_manager = None  # 延迟初始化
        self.me3_download_worker = None
        self.me3_installer_download_worker = None  # ME3安装程序下载工作线程
        self.easytier_download_worker = None
        self.onlinefix_download_worker = None  # OnlineFix下载工作线程
        self.status_check_worker = None  # 状态检查工作线程
        self.update_check_worker = None  # 更新检查工作线程
        self.setup_content()

        # 延迟初始化下载管理器和状态检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.delayed_init)

    def delayed_init(self):
        """延迟初始化"""
        # 异步检查状态，避免阻塞UI
        QTimer.singleShot(100, self.check_current_status)

    def get_download_manager(self):
        """获取下载管理器（确保已初始化）"""
        if self.download_manager is None:
            from ...utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()
            # 连接EasyTier安装完成信号
            self.download_manager.easytier_install_finished.connect(self.on_easytier_install_finished)
            # 连接ME3安装程序下载完成信号
            self.download_manager.me3_installer_download_finished.connect(self.on_me3_installer_download_finished)
            # 连接OnlineFix下载完成信号
            self.download_manager.onlinefix_download_finished.connect(self.on_onlinefix_download_finished)
            # 连接OnlineFix下载进度信号
            self.download_manager.onlinefix_download_progress.connect(self.update_onlinefix_progress)
        return self.download_manager

    def setup_content(self):
        """设置页面内容"""
        # 使用水平布局来减少垂直空间占用
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

        # 创建主容器
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：ME3工具 + 说明栏（水平布局）
        me3_row_container = QWidget()
        me3_row_layout = QHBoxLayout(me3_row_container)
        me3_row_layout.setSpacing(15)
        me3_row_layout.setContentsMargins(0, 0, 0, 0)

        me3_widget = self.create_me3_section()
        onlinefix_widget = self.create_onlinefix_section()

        me3_row_layout.addWidget(me3_widget, 2)  # ME3工具占2份
        me3_row_layout.addWidget(onlinefix_widget, 1)  # OnlineFix工具包占1份

        # 第二行：EasyTier（重要工具）
        easytier_widget = self.create_easytier_section()

        main_layout.addWidget(me3_row_container)
        main_layout.addWidget(easytier_widget)

        self.add_content(main_container)
        self.add_stretch()
    
    def create_me3_section(self):
        """创建ME3工具区域"""
        section = QGroupBox("ME3工具")
        section.setStyleSheet("""
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

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 版本信息卡片
        self.me3_version_card = VersionInfoCard()
        layout.addWidget(self.me3_version_card)

        # 版本类型选择（在这里创建，因为需要在create_me3_download_controls之前）
        self.create_me3_version_type_selection()
        layout.addWidget(self.me3_version_type_container)

        # ME3下载控制区域
        self.create_me3_download_controls(layout)

        section.setLayout(layout)
        return section

    def create_onlinefix_section(self):
        """创建OnlineFix工具包区域"""
        section = QGroupBox("OnlineFix工具包")
        section.setStyleSheet("""
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

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 版本信息卡片
        self.onlinefix_version_card = self.create_onlinefix_version_card()
        layout.addWidget(self.onlinefix_version_card)

        # 下载控制区域
        self.create_onlinefix_download_controls(layout)

        section.setLayout(layout)
        return section

    def create_onlinefix_version_card(self):
        """创建OnlineFix版本信息卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 10)

        # 状态标题
        status_label = QLabel("📦 工具包状态")
        status_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(status_label)

        # 状态信息
        self.onlinefix_status_label = QLabel("检查中...")
        self.onlinefix_status_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #313244;
                border-radius: 4px;
                border: 1px solid #fab387;
            }
        """)
        layout.addWidget(self.onlinefix_status_label)

        # 详细信息
        self.onlinefix_detail_label = QLabel("包含: esl2.zip, tool.zip, 破解补丁等")
        self.onlinefix_detail_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 11px;
                margin-top: 4px;
            }
        """)
        layout.addWidget(self.onlinefix_detail_label)

        card.setLayout(layout)
        return card

    def create_onlinefix_download_controls(self, layout):
        """创建OnlineFix下载控制区域"""
        # 下载按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # 下载按钮
        self.onlinefix_download_btn = QPushButton("📥 下载工具包")
        self.onlinefix_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c3a3;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.onlinefix_download_btn.clicked.connect(self.download_onlinefix)

        # 检查按钮
        self.onlinefix_check_btn = QPushButton("🔍 检查状态")
        self.onlinefix_check_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        self.onlinefix_check_btn.clicked.connect(self.check_onlinefix_status)

        button_layout.addWidget(self.onlinefix_download_btn)
        button_layout.addWidget(self.onlinefix_check_btn)
        button_layout.addStretch()

        button_container.setLayout(button_layout)
        layout.addWidget(button_container)

        # 进度条（初始隐藏）
        self.onlinefix_progress = QProgressBar()
        self.onlinefix_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 4px;
                text-align: center;
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-size: 11px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }
        """)
        self.onlinefix_progress.setVisible(False)
        layout.addWidget(self.onlinefix_progress)

    def create_me3_download_controls(self, layout):
        """创建ME3下载控制区域"""
        # 下载按钮区域
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # 下载/更新按钮（便携版）
        self.me3_download_btn = QPushButton("下载ME3工具（便携版）")
        self.me3_download_btn.setFixedHeight(35)
        self.me3_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c3a3;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.me3_download_btn.clicked.connect(self.start_me3_download)





        # 检查更新按钮
        self.me3_check_update_btn = QPushButton("检查更新")
        self.me3_check_update_btn.setFixedHeight(35)
        self.me3_check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
        """)
        self.me3_check_update_btn.clicked.connect(self.check_me3_updates)

        # 运行库修复按钮
        self.me3_vcredist_btn = QPushButton("运行库修复")
        self.me3_vcredist_btn.setFixedHeight(35)
        self.me3_vcredist_btn.setStyleSheet("""
            QPushButton {
                background-color: #fab387;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #f9c74f;
            }
            QPushButton:pressed {
                background-color: #f8b500;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.me3_vcredist_btn.clicked.connect(self.fix_vcredist)

        # 取消下载按钮
        self.me3_cancel_btn = QPushButton("取消下载")
        self.me3_cancel_btn.setFixedHeight(35)
        self.me3_cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #d67a8a;
            }
        """)
        self.me3_cancel_btn.clicked.connect(self.cancel_me3_download)
        self.me3_cancel_btn.setVisible(False)

        btn_row.addWidget(self.me3_download_btn)
        btn_row.addWidget(self.me3_cancel_btn)
        btn_row.addWidget(self.me3_check_update_btn)
        btn_row.addWidget(self.me3_vcredist_btn)
        btn_row.addStretch()

        button_layout.addLayout(btn_row)

        # 镜像选择
        mirror_row = QHBoxLayout()
        mirror_row.setSpacing(10)

        self.me3_mirror_combo = QComboBox()
        self.me3_mirror_combo.setFixedHeight(30)
        self.me3_mirror_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 8px;
                color: #cdd6f4;
                font-size: 12px;
                min-width: 180px;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #cdd6f4;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                border: 1px solid #45475a;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
                color: #cdd6f4;
            }
        """)

        mirror_tip_label = QLabel("💡 更多镜像: https://yishijie.gitlab.io/ziyuan/")
        mirror_tip_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
            }
        """)

        mirror_row.addWidget(self.me3_mirror_combo)
        mirror_row.addWidget(mirror_tip_label)
        mirror_row.addStretch()

        button_layout.addLayout(mirror_row)

        button_container.setLayout(button_layout)
        layout.addWidget(button_container)

        # 进度条
        self.me3_progress_bar = QProgressBar()
        self.me3_progress_bar.setVisible(False)
        self.me3_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 4px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.me3_progress_bar)

        # 状态标签
        self.me3_status_label = QLabel()
        self.me3_status_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 11px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.me3_status_label)

    def check_current_status(self):
        """检查当前状态（异步）"""
        # 显示检查状态的提示
        if hasattr(self, 'me3_status_label'):
            self.me3_status_label.setText("正在检查状态...")
        if hasattr(self, 'easytier_status_label'):
            self.easytier_status_label.setText("正在检查状态...")
        if hasattr(self, 'onlinefix_status_label'):
            self.onlinefix_status_label.setText("正在检查状态...")

        # 如果已有工作线程在运行，先停止它
        if self.status_check_worker and self.status_check_worker.isRunning():
            self.status_check_worker.quit()
            self.status_check_worker.wait()

        # 创建并启动状态检查工作线程
        dm = self.get_download_manager()
        self.status_check_worker = StatusCheckWorker(dm)
        self.status_check_worker.status_checked.connect(self.on_status_checked)
        self.status_check_worker.start()

    def on_status_checked(self, status_info):
        """状态检查完成的回调"""
        try:
            # 更新ME3状态
            is_me3_installed = status_info.get('me3_installed', False)
            is_me3_full_installed = status_info.get('me3_full_installed', False)
            me3_current_version = status_info.get('me3_version')
            me3_full_version = status_info.get('me3_full_version')


            # 保存状态信息供后续使用
            self._me3_status_info = {
                'is_me3_installed': is_me3_installed,
                'is_me3_full_installed': is_me3_full_installed,
                'me3_current_version': me3_current_version,
                'me3_full_version': me3_full_version
            }

            # 根据当前选择的版本类型更新显示
            self.update_me3_version_display()



            # 根据检测结果设置单选框状态
            if is_me3_full_installed:
                self.me3_full_radio.setChecked(True)
            elif is_me3_installed:
                self.me3_portable_radio.setChecked(True)
            else:
                # 默认选择便携版
                self.me3_portable_radio.setChecked(True)

            # 更新ME3版本显示（在设置单选框状态后）
            self.update_me3_version_display()

            # 更新EasyTier状态
            easytier_current_version = status_info.get('easytier_version')

            if easytier_current_version:
                self.easytier_version_card.update_info(
                    current_version=easytier_current_version,
                    status="已安装"
                )
                self.easytier_download_btn.setText("重新下载")
            else:
                self.easytier_version_card.update_info(
                    current_version=None,
                    status="未安装"
                )
                self.easytier_download_btn.setText("下载EasyTier")

            # 更新OnlineFix状态
            if hasattr(self, 'onlinefix_status_label'):
                self.check_onlinefix_status()

            # 加载镜像列表（这个操作比较快，可以在UI线程执行）
            self.load_mirrors()

            # 启动异步更新检查
            self.start_update_check()

        except Exception as e:
            print(f"处理状态检查结果失败: {e}")
            # 设置默认状态
            if hasattr(self, 'me3_status_label'):
                self.me3_status_label.setText("状态检查失败")
            if hasattr(self, 'easytier_status_label'):
                self.easytier_status_label.setText("状态检查失败")
            if hasattr(self, 'onlinefix_status_label'):
                self.onlinefix_status_label.setText("状态检查失败")

    def start_update_check(self):
        """启动异步更新检查"""
        # 显示检查状态
        if hasattr(self, 'me3_status_label'):
            self.me3_status_label.setText("正在检查最新版本...")
        if hasattr(self, 'easytier_status_label'):
            self.easytier_status_label.setText("正在检查最新版本...")
        # OnlineFix不需要检查最新版本，保持当前状态

        # 如果已有更新检查线程在运行，先停止它
        if self.update_check_worker and self.update_check_worker.isRunning():
            self.update_check_worker.quit()
            self.update_check_worker.wait()

        # 创建并启动更新检查工作线程
        dm = self.get_download_manager()

        # 获取EasyTier版本类型选择
        include_prerelease = False
        if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
            include_prerelease = True

        self.update_check_worker = UpdateCheckWorker(dm, include_prerelease)
        self.update_check_worker.me3_update_checked.connect(self.on_me3_update_checked)
        self.update_check_worker.easytier_update_checked.connect(self.on_easytier_update_checked)
        self.update_check_worker.start()

    def on_me3_update_checked(self, result):
        """ME3更新检查完成"""
        try:
            if result.get('success', False):
                latest_version = result.get('latest_version', '未知')
                current_version = result.get('current_version')

                self.me3_version_card.update_info(latest_version=latest_version)

                # 获取版本类型文本（这里使用便携版作为默认，因为这是旧的更新检查逻辑）
                version_type_text = "便携版"
                if current_version and current_version != latest_version:
                    self.me3_status_label.setText(f"发现新版本: {latest_version} ({version_type_text})")
                    # 触发版本类型切换处理，更新按钮文本
                    self.on_me3_version_type_changed()
                elif current_version:
                    self.me3_status_label.setText(f"已是最新版本 ({version_type_text})")
                    # 触发版本类型切换处理，更新按钮文本
                    self.on_me3_version_type_changed()
                else:
                    self.me3_status_label.setText(f"可以下载最新版本 ({version_type_text})")
            else:
                error = result.get('error', '未知错误')
                self.me3_version_card.update_info(latest_version="获取失败")
                self.me3_status_label.setText(f"检查更新失败: {error}")
        except Exception as e:
            self.me3_status_label.setText(f"处理更新信息失败: {str(e)}")

    def on_easytier_update_checked(self, result):
        """EasyTier更新检查完成"""
        try:
            if result.get('success', False):
                has_update = result.get('has_update', False)
                latest_version = result.get('latest_version')
                current_version = result.get('current_version')
                message = result.get('message', '')
                include_prerelease = result.get('include_prerelease', False)

                version_type = "预发行版" if include_prerelease else "正式版"
                self.easytier_version_card.update_info(
                    current_version=current_version,
                    latest_version=latest_version,
                    status=message,
                    version_type=version_type
                )

                # 更新状态标签
                version_type = "预发行版" if include_prerelease else "正式版"
                if has_update and latest_version:
                    self.easytier_download_btn.setText(f"更新到 v{latest_version} ({version_type})")
                    self.easytier_status_label.setText(f"发现新{version_type}: v{latest_version}")
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #f9e2af;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
                elif current_version:
                    self.easytier_download_btn.setText(f"重新下载 ({version_type})")
                    self.easytier_status_label.setText(f"已是最新{version_type}")
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #a6e3a1;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
                else:
                    self.easytier_download_btn.setText(f"下载EasyTier ({version_type})")
                    self.easytier_status_label.setText(f"可以下载最新{version_type}")
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #89b4fa;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
            else:
                error = result.get('error', '未知错误')
                self.easytier_version_card.update_info(status=f"检查失败: {error}")
                self.easytier_status_label.setText(f"检查更新失败: {error}")
                self.easytier_status_label.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 12px;
                        font-style: italic;
                        margin-top: 5px;
                    }
                """)
        except Exception as e:
            self.easytier_version_card.update_info(status=f"处理更新信息失败: {str(e)}")
            self.easytier_status_label.setText(f"处理更新信息失败: {str(e)}")
            self.easytier_status_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 12px;
                    font-style: italic;
                    margin-top: 5px;
                }
            """)

    def check_me3_updates(self):
        """检查ME3更新"""
        self.me3_status_label.setText("正在检查最新版本...")

        try:
            dm = self.get_download_manager()
            release_info = dm.get_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                self.me3_version_card.update_info(latest_version=latest_version)

                # 检查是否需要更新（根据当前选择的版本类型）
                version_type = "full" if self.me3_full_radio.isChecked() else "portable"
                version_type_text = "安装版" if self.me3_full_radio.isChecked() else "便携版"
                current_version = dm.get_version_by_type(version_type)
                if current_version and current_version != latest_version:
                    self.me3_download_btn.setText("更新ME3工具")
                    self.me3_status_label.setText(f"发现新版本: {latest_version} ({version_type_text})")
                elif current_version:
                    self.me3_status_label.setText(f"已是最新版本 ({version_type_text})")
                else:
                    self.me3_status_label.setText(f"可以下载最新版本 ({version_type_text})")
            else:
                self.me3_version_card.update_info(latest_version="获取失败")
                self.me3_status_label.setText("无法获取版本信息，请检查网络连接")
        except Exception as e:
            self.me3_status_label.setText(f"检查更新失败: {str(e)}")

    def check_easytier_updates(self):
        """检查EasyTier更新"""
        try:
            dm = self.get_download_manager()

            # 获取版本类型选择
            include_prerelease = False
            if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
                include_prerelease = True

            has_update, latest_version, message = dm.check_easytier_update(include_prerelease)

            # 更新界面
            current_version = dm.get_current_easytier_version()
            version_type = "预发行版" if include_prerelease else "正式版"
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version,
                status=message,
                version_type=version_type
            )

            # 更新按钮文本
            version_type = "预发行版" if include_prerelease else "正式版"
            if has_update and latest_version:
                self.easytier_download_btn.setText(f"更新到 v{latest_version} ({version_type})")
            elif current_version:
                self.easytier_download_btn.setText(f"重新下载 ({version_type})")
            else:
                self.easytier_download_btn.setText(f"下载EasyTier ({version_type})")

        except Exception as e:
            print(f"检查EasyTier更新失败: {e}")
            self.easytier_version_card.update_info(status="检查失败")
    
    def start_me3_download(self):
        """开始ME3下载"""
        if self.me3_download_worker and self.me3_download_worker.isRunning():
            self.me3_status_label.setText("下载正在进行中，请稍候")
            return
        if self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            self.me3_status_label.setText("安装程序下载正在进行中，请稍候")
            return

        # 根据选择的版本类型决定下载方式
        if self.me3_full_radio.isChecked():
            # 检查是否已有安装程序
            download_manager = self.get_download_manager()
            installer_path = download_manager.me3_dir / "me3_installer.exe"

            if installer_path.exists() and self.me3_download_btn.text() == "安装ME3工具":
                # 直接静默安装现有的安装程序
                self.install_me3_now(str(installer_path))
                return
            else:
                # 下载安装版
                self.start_me3_installer_download()
                return

        # 获取选中的镜像
        selected_mirror = None
        if hasattr(self, 'me3_mirror_combo') and self.me3_mirror_combo.currentData():
            selected_mirror = self.me3_mirror_combo.currentData()

        # 下载便携版
        self.me3_download_worker = self.get_download_manager().download_me3(selected_mirror)
        if not self.me3_download_worker:
            self.me3_status_label.setText("无法创建下载任务，请检查网络连接")
            return

        # 连接信号
        self.me3_download_worker.progress.connect(self.update_me3_progress)
        self.me3_download_worker.finished.connect(self.me3_download_finished)

        # 更新UI状态
        self.me3_download_btn.setVisible(False)
        self.me3_cancel_btn.setVisible(True)
        self.me3_check_update_btn.setEnabled(False)
        self.me3_mirror_combo.setEnabled(False)
        self.me3_progress_bar.setVisible(True)
        self.me3_progress_bar.setValue(0)
        self.me3_status_label.setText("正在下载ME3便携版...")

        # 开始下载
        self.me3_download_worker.start()

    def start_me3_installer_download(self):
        """开始ME3安装程序下载"""
        if self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            self.me3_status_label.setText("安装程序下载正在进行中，请稍候")
            return

        # 获取选中的镜像
        selected_mirror = None
        if hasattr(self, 'me3_mirror_combo') and self.me3_mirror_combo.currentData():
            selected_mirror = self.me3_mirror_combo.currentData()

        self.me3_installer_download_worker = self.get_download_manager().download_me3_installer(selected_mirror)
        if not self.me3_installer_download_worker:
            self.me3_status_label.setText("无法创建下载任务，请检查网络连接")
            return

        # 连接信号
        self.me3_installer_download_worker.progress.connect(self.update_me3_progress)
        self.me3_installer_download_worker.finished.connect(self.me3_installer_download_finished)

        # 更新UI状态
        self.me3_download_btn.setEnabled(False)
        self.me3_cancel_btn.setVisible(True)
        self.me3_check_update_btn.setEnabled(False)
        self.me3_mirror_combo.setEnabled(False)
        self.me3_progress_bar.setVisible(True)
        self.me3_progress_bar.setValue(0)
        self.me3_status_label.setText("正在下载ME3安装程序...")

        # 开始下载
        self.me3_installer_download_worker.start()

    def me3_installer_download_finished(self, success, message):
        """ME3安装程序下载完成"""
        # 这个方法会被DownloadWorker的finished信号调用
        # 但实际的安装程序下载完成处理在on_me3_installer_download_finished中
        pass

    def cancel_me3_download(self):
        """取消ME3下载"""
        if self.me3_download_worker and self.me3_download_worker.isRunning():
            self.me3_download_worker.cancel()
            self.me3_status_label.setText("下载已取消")
            self.reset_me3_download_ui()
        elif self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            self.me3_installer_download_worker.cancel()
            self.me3_status_label.setText("安装程序下载已取消")

            # 清理不完整的安装程序文件
            self.cleanup_incomplete_installer()

            self.reset_me3_download_ui()

    def reset_me3_download_ui(self):
        """重置ME3下载UI状态"""
        self.me3_download_btn.setVisible(True)
        self.me3_download_btn.setEnabled(True)
        self.me3_cancel_btn.setVisible(False)
        self.me3_check_update_btn.setEnabled(True)
        self.me3_mirror_combo.setEnabled(True)
        self.me3_progress_bar.setVisible(False)
        self.me3_progress_bar.setValue(0)

        # 更新按钮文本状态
        self.on_me3_version_type_changed()

    def cleanup_incomplete_installer(self):
        """清理不完整的安装程序文件"""
        try:
            download_manager = self.get_download_manager()
            installer_path = download_manager.me3_dir / "me3_installer.exe"

            if installer_path.exists():
                installer_path.unlink()  # 删除不完整的文件
                print(f"已清理不完整的安装程序: {installer_path}")

                # 清理version.json中的安装程序信息
                version_file = download_manager.me3_dir / "version.json"
                if version_file.exists():
                    try:
                        import json
                        with open(version_file, 'r', encoding='utf-8') as f:
                            version_info = json.load(f)

                        # 移除安装程序相关信息
                        version_info.pop('installer_version', None)
                        version_info.pop('installer_path', None)
                        version_info.pop('installer_downloaded_at', None)
                        version_info['installer_exists'] = False

                        with open(version_file, 'w', encoding='utf-8') as f:
                            json.dump(version_info, f, indent=2, ensure_ascii=False)

                    except Exception as e:
                        print(f"清理version.json失败: {e}")

        except Exception as e:
            print(f"清理不完整安装程序失败: {e}")

    def update_me3_progress(self, value):
        """更新ME3下载进度"""
        self.me3_progress_bar.setValue(value)

    def fix_vcredist(self):
        """修复VC++运行库"""
        try:
            import threading
            import urllib.request
            import subprocess
            from pathlib import Path
            from PySide6.QtCore import QObject, Signal, QThread

            # 保存当前ME3状态信息（在开始修复前保存）
            self._me3_original_status = self.me3_status_label.text()
            self._me3_original_style = self.me3_status_label.styleSheet()

            # 禁用按钮，防止重复点击
            self.me3_vcredist_btn.setEnabled(False)
            self.me3_vcredist_btn.setText("正在修复...")
            self.me3_status_label.setText("正在下载VC++运行库...")

            # 创建信号发射器
            class VCRedistWorker(QObject):
                status_update = Signal(str)
                success = Signal()
                error = Signal(int)
                finished = Signal()

                def __init__(self, parent_widget):
                    super().__init__()
                    self.parent_widget = parent_widget

                def run(self):
                    try:
                        # 创建tools目录
                        download_manager = self.parent_widget.get_download_manager()
                        tools_dir = download_manager.me3_dir / "tools"
                        tools_dir.mkdir(exist_ok=True)

                        # VC++运行库下载URL
                        vcredist_url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
                        vcredist_path = tools_dir / "vc_redist.x64.exe"
                        log_path = tools_dir / "vcredist_install.log"

                        # 下载VC++运行库
                        self.status_update.emit("正在下载VC++运行库...")

                        # 使用带进度的下载
                        def download_progress(block_num, block_size, total_size):
                            if total_size > 0:
                                percent = min(100, (block_num * block_size * 100) // total_size)
                                self.status_update.emit(f"正在下载VC++运行库... {percent}%")

                        urllib.request.urlretrieve(vcredist_url, vcredist_path, download_progress)

                        # 执行静默安装
                        self.status_update.emit("正在安装VC++运行库...")
                        install_cmd = [
                            str(vcredist_path),
                            "/install",
                            "/quiet",
                            "/norestart",
                            "/passive",
                            "/log",
                            str(log_path)
                        ]

                        import sys
                        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        result = subprocess.run(install_cmd, capture_output=True, text=True, creationflags=creation_flags)

                        # 发射结果信号
                        if result.returncode == 0:
                            self.success.emit()
                        else:
                            self.error.emit(result.returncode)

                    except Exception as e:
                        self.status_update.emit(f"运行库修复失败: {str(e)}")
                        print(f"VC++运行库修复失败: {e}")
                    finally:
                        self.finished.emit()

            # 创建工作线程
            self.vcredist_worker = VCRedistWorker(self)
            self.vcredist_thread = QThread()
            self.vcredist_worker.moveToThread(self.vcredist_thread)

            # 连接信号
            self.vcredist_worker.status_update.connect(self.me3_status_label.setText)
            self.vcredist_worker.success.connect(self._update_vcredist_success_ui)
            self.vcredist_worker.error.connect(self._update_vcredist_error_ui)
            self.vcredist_worker.finished.connect(self._vcredist_cleanup)
            self.vcredist_thread.started.connect(self.vcredist_worker.run)

            # 启动线程
            self.vcredist_thread.start()

        except Exception as e:
            self.me3_status_label.setText(f"运行库修复失败: {str(e)}")
            self.me3_vcredist_btn.setEnabled(True)
            self.me3_vcredist_btn.setText("运行库修复")
            print(f"VC++运行库修复失败: {e}")

    def _vcredist_cleanup(self):
        """清理VC++修复线程"""
        if hasattr(self, 'vcredist_thread'):
            self.vcredist_thread.quit()
            self.vcredist_thread.wait()
            self.vcredist_thread.deleteLater()
            delattr(self, 'vcredist_thread')
        if hasattr(self, 'vcredist_worker'):
            self.vcredist_worker.deleteLater()
            delattr(self, 'vcredist_worker')

    def _update_vcredist_success_ui(self):
        """更新VC++运行库修复成功的UI状态"""
        self.me3_status_label.setText("VC++运行库修复完成")
        self.me3_status_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 11px;
                padding: 3px;
                border-radius: 3px;
                border: 1px solid #a6e3a1;
            }
        """)
        self.me3_vcredist_btn.setEnabled(True)
        self.me3_vcredist_btn.setText("运行库修复")

        # 3秒后清除状态和样式
        from PySide6.QtCore import QTimer
        timer = QTimer(self)
        timer.setSingleShot(True)
        def clear_status():
            # 检查是否需要恢复ME3状态信息
            if hasattr(self, '_me3_original_status') and self._me3_original_status:
                self.me3_status_label.setText(self._me3_original_status)
                self.me3_status_label.setStyleSheet(self._me3_original_style)
                delattr(self, '_me3_original_status')
                delattr(self, '_me3_original_style')
            else:
                self.me3_status_label.setText("")
                self.me3_status_label.setStyleSheet("")  # 清除样式
        timer.timeout.connect(clear_status)
        timer.start(3000)

    def _update_vcredist_error_ui(self, error_code):
        """更新VC++运行库修复失败的UI状态"""
        self.me3_status_label.setText(f"VC++运行库安装失败 (错误码: {error_code})")
        self.me3_status_label.setStyleSheet("""
            QLabel {
                color: #f38ba8;
                font-size: 11px;
                padding: 3px;
                border-radius: 3px;
                border: 1px solid #f38ba8;
            }
        """)
        self.me3_vcredist_btn.setEnabled(True)
        self.me3_vcredist_btn.setText("运行库修复")

    def me3_download_finished(self, success, message):
        """ME3下载完成"""
        self.reset_me3_download_ui()

        if success:
            self.me3_status_label.setText("ME3工具下载并安装成功")
            # 设置成功状态样式
            self.me3_status_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 11px;
                    padding: 3px;
                    border-radius: 3px;
                    border: 1px solid #a6e3a1;
                }
            """)

            # 保存便携版版本信息到version.json
            self.save_portable_version_info()

            # 延迟检查状态，避免覆盖成功消息
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self.check_current_status)
            self.status_updated.emit()  # 发送状态更新信号
        else:
            self.me3_status_label.setText(f"下载失败: {message}")
            # 设置错误状态样式
            self.me3_status_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 11px;
                    padding: 3px;
                    border-radius: 3px;
                    border: 1px solid #f38ba8;
                }
            """)

    def load_mirrors(self):
        """加载镜像列表到下拉框"""
        mirrors = self.get_download_manager().get_mirrors()

        # 加载ME3镜像
        if hasattr(self, 'me3_mirror_combo'):
            self.me3_mirror_combo.clear()
            for mirror in mirrors:
                # 显示简化的镜像名称
                if "gh-proxy.com" in mirror:
                    display_name = "gh-proxy.com (GitHub代理)"
                elif "ghproxy.net" in mirror:
                    display_name = "ghproxy.net (GitHub镜像)"
                elif "ghfast.top" in mirror:
                    display_name = "ghfast.top (GitHub加速)"
                elif "github.com" in mirror:
                    display_name = "直连GitHub (备用)"
                else:
                    display_name = mirror.replace("https://", "").replace("http://", "").rstrip("/")

                self.me3_mirror_combo.addItem(display_name, mirror)

            # 设置当前选中的镜像（第一个）
            if mirrors:
                self.me3_mirror_combo.setCurrentIndex(0)

        # 加载EasyTier镜像
        if hasattr(self, 'easytier_mirror_combo'):
            self.easytier_mirror_combo.clear()
            for mirror in mirrors:
                # 显示简化的镜像名称
                if "gh-proxy.com" in mirror:
                    display_name = "gh-proxy.com (GitHub代理)"
                elif "ghproxy.net" in mirror:
                    display_name = "ghproxy.net (GitHub镜像)"
                elif "ghfast.top" in mirror:
                    display_name = "ghfast.top (GitHub加速)"
                elif "github.com" in mirror:
                    display_name = "直连GitHub (备用)"
                else:
                    display_name = mirror.replace("https://", "").replace("http://", "").rstrip("/")

                self.easytier_mirror_combo.addItem(display_name, mirror)

            # 设置当前选中的镜像（第一个）
            if mirrors:
                self.easytier_mirror_combo.setCurrentIndex(0)

    def create_me3_version_type_selection(self):
        """创建ME3版本类型选择"""
        self.me3_version_type_container = QWidget()
        self.me3_version_type_layout = QHBoxLayout(self.me3_version_type_container)
        self.me3_version_type_layout.setContentsMargins(0, 0, 0, 0)
        self.me3_version_type_layout.setSpacing(20)

        self.me3_portable_radio = QRadioButton("便携版")
        self.me3_full_radio = QRadioButton("完整安装版")

        # 设置单选框样式
        radio_style = """
            QRadioButton {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #6c7086;
                border-radius: 7px;
                background-color: transparent;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #89b4fa;
                border-radius: 7px;
                background-color: #89b4fa;
            }
        """

        self.me3_portable_radio.setStyleSheet(radio_style)
        self.me3_full_radio.setStyleSheet(radio_style)

        # 默认选择便携版
        self.me3_portable_radio.setChecked(True)

        # 连接信号
        self.me3_portable_radio.toggled.connect(self.on_me3_version_type_changed)
        self.me3_full_radio.toggled.connect(self.on_me3_version_type_changed)

        # 创建标签
        type_label = QLabel("版本类型:")
        type_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.me3_version_type_layout.addWidget(type_label)
        self.me3_version_type_layout.addWidget(self.me3_portable_radio)
        self.me3_version_type_layout.addWidget(self.me3_full_radio)
        self.me3_version_type_layout.addStretch()

    def on_me3_version_type_changed(self):
        """ME3版本类型切换处理"""
        # 更新版本显示
        self.update_me3_version_display()

        # 更新状态提示文本
        self.update_me3_status_text()

        # 获取当前状态
        download_manager = self.get_download_manager()
        is_portable_installed = download_manager.is_me3_installed()
        is_full_installed = download_manager.is_me3_full_installed()

        # 检查是否存在安装程序
        installer_path = download_manager.me3_dir / "me3_installer.exe"
        installer_exists = installer_path.exists()

        if self.me3_portable_radio.isChecked():
            # 选择便携版
            if is_portable_installed:
                # 检查是否有版本更新（使用统一版本获取接口）
                try:
                    current_version = download_manager.get_version_by_type("portable")
                    latest_version = getattr(self.me3_version_card, 'latest_version', None)

                    if current_version and latest_version and current_version != latest_version:
                        self.me3_download_btn.setText("获取更新（便携版）")
                    else:
                        self.me3_download_btn.setText("重新下载（便携版）")
                except Exception as e:
                    print(f"版本比较失败: {e}")
                    self.me3_download_btn.setText("重新下载（便携版）")
            else:
                self.me3_download_btn.setText("下载ME3工具（便携版）")
        else:
            # 选择完整安装版
            if is_full_installed:
                # 检查是否有版本更新（使用统一版本获取接口）
                try:
                    current_version = download_manager.get_version_by_type("full")
                    latest_version = getattr(self.me3_version_card, 'latest_version', None)

                    if current_version and latest_version and current_version != latest_version:
                        self.me3_download_btn.setText("获取更新（安装版）")
                    else:
                        self.me3_download_btn.setText("重新下载（安装版）")
                except Exception as e:
                    print(f"版本比较失败: {e}")
                    self.me3_download_btn.setText("重新下载（安装版）")
            elif installer_exists:
                self.me3_download_btn.setText("安装ME3工具")
            else:
                self.me3_download_btn.setText("下载ME3安装版")

    def update_me3_version_display(self):
        """根据当前选择的版本类型更新ME3版本显示"""
        if not hasattr(self, '_me3_status_info'):
            return

        status_info = self._me3_status_info
        is_me3_installed = status_info.get('is_me3_installed', False)
        is_me3_full_installed = status_info.get('is_me3_full_installed', False)
        me3_current_version = status_info.get('me3_current_version')
        me3_full_version = status_info.get('me3_full_version')

        if self.me3_portable_radio.isChecked():
            # 显示便携版信息 - 只有便携版安装了才显示版本
            if is_me3_installed:
                self.me3_version_card.update_info(
                    current_version=me3_current_version,
                    current_version_type="便携版",
                    status="已安装（便携版）"
                )
            else:
                # 便携版未安装，显示未安装（即使安装版已安装）
                self.me3_version_card.update_info(
                    current_version=None,
                    current_version_type=None,
                    status="未安装"
                )
        else:
            # 显示安装版信息 - 只有安装版安装了才显示版本
            if is_me3_full_installed:
                self.me3_version_card.update_info(
                    current_version=me3_full_version,
                    current_version_type="安装版",
                    status="已安装（安装版）"
                )
            else:
                # 安装版未安装，显示未安装（即使便携版已安装）
                self.me3_version_card.update_info(
                    current_version=None,
                    current_version_type=None,
                    status="未安装"
                )

    def update_me3_status_text(self):
        """根据当前选择的版本类型更新状态提示文本"""
        try:
            # 获取版本类型文本
            version_type_text = "安装版" if self.me3_full_radio.isChecked() else "便携版"

            # 获取当前状态文本
            current_text = self.me3_status_label.text()

            # 更新状态文本，添加版本类型标识
            if "发现新版本:" in current_text:
                # 提取版本号
                import re
                version_match = re.search(r'发现新版本: (v?\d+\.\d+\.\d+)', current_text)
                if version_match:
                    version = version_match.group(1)
                    self.me3_status_label.setText(f"发现新版本: {version} ({version_type_text})")
            elif "已是最新版本" in current_text:
                self.me3_status_label.setText(f"已是最新版本 ({version_type_text})")
            elif "可以下载最新版本" in current_text:
                self.me3_status_label.setText(f"可以下载最新版本 ({version_type_text})")
            # 其他状态文本保持不变（如错误信息等）
        except Exception as e:
            print(f"更新状态文本失败: {e}")

    def create_easytier_section(self):
        """创建EasyTier工具区域"""
        section = QGroupBox("EasyTier虚拟局域网工具")
        section.setStyleSheet("""
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

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 版本信息卡片
        self.easytier_version_card = VersionInfoCard()
        layout.addWidget(self.easytier_version_card)

        # EasyTier下载控制区域
        self.create_easytier_download_controls(layout)

        # EasyTier镜像选择区域
        self.create_easytier_mirror_controls(layout)

        section.setLayout(layout)
        return section

    def create_easytier_download_controls(self, layout):
        """创建EasyTier下载控制区域"""
        # 下载按钮区域
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        # 版本类型选择区域
        version_type_container = QWidget()
        version_type_layout = QHBoxLayout()
        version_type_layout.setContentsMargins(0, 0, 0, 0)
        version_type_layout.setSpacing(10)

        version_type_label = QLabel("版本类型:")
        version_type_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)

        # 版本类型选择单选按钮
        self.easytier_release_radio = QRadioButton("正式版")
        self.easytier_prerelease_radio = QRadioButton("预发行版")

        # 根据当前安装的版本类型自动选择
        self.auto_select_version_type()

        # 设置单选按钮样式
        radio_style = """
            QRadioButton {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #6c7086;
                border-radius: 7px;
                background-color: #1e1e2e;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #89b4fa;
                border-radius: 7px;
                background-color: #89b4fa;
            }
        """
        self.easytier_release_radio.setStyleSheet(radio_style)
        self.easytier_prerelease_radio.setStyleSheet(radio_style)

        # 连接信号，当版本类型改变时自动检查更新
        self.easytier_release_radio.toggled.connect(self.on_easytier_version_type_changed)
        self.easytier_prerelease_radio.toggled.connect(self.on_easytier_version_type_changed)

        # 创建防抖定时器
        self.easytier_version_check_timer = QTimer()
        self.easytier_version_check_timer.setSingleShot(True)
        self.easytier_version_check_timer.timeout.connect(self.delayed_easytier_version_check)
        self.easytier_version_check_timer.setInterval(300)  # 300ms防抖延迟

        version_type_layout.addWidget(version_type_label)
        version_type_layout.addWidget(self.easytier_release_radio)
        version_type_layout.addWidget(self.easytier_prerelease_radio)
        version_type_layout.addStretch()

        version_type_container.setLayout(version_type_layout)
        button_layout.addWidget(version_type_container)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # 下载/更新按钮
        self.easytier_download_btn = QPushButton("下载EasyTier")
        self.easytier_download_btn.setFixedHeight(35)
        self.easytier_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7dc383;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.easytier_download_btn.clicked.connect(self.download_easytier)

        # 检查更新按钮
        self.easytier_check_btn = QPushButton("检查更新")
        self.easytier_check_btn.setFixedHeight(35)
        self.easytier_check_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
            QPushButton:disabled {
                background-color: #6c7086;
                color: #45475a;
            }
        """)
        self.easytier_check_btn.clicked.connect(self.check_easytier_update)

        btn_row.addWidget(self.easytier_download_btn)
        btn_row.addWidget(self.easytier_check_btn)
        btn_row.addStretch()

        button_layout.addLayout(btn_row)

        # 进度条
        self.easytier_progress = QProgressBar()
        self.easytier_progress.setVisible(False)
        self.easytier_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #313244;
                border-radius: 6px;
                text-align: center;
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 4px;
            }
        """)
        button_layout.addWidget(self.easytier_progress)

        button_container.setLayout(button_layout)
        layout.addWidget(button_container)

    def auto_select_version_type(self):
        """根据当前安装的版本类型自动选择单选框"""
        try:
            download_manager = self.get_download_manager()
            is_prerelease = download_manager.is_current_easytier_prerelease()

            if is_prerelease:
                self.easytier_prerelease_radio.setChecked(True)
                print("🔄 自动选择预发行版（基于当前安装版本）")
            else:
                self.easytier_release_radio.setChecked(True)
                print("🔄 自动选择正式版（基于当前安装版本或默认）")
        except Exception as e:
            # 如果出错，默认选择正式版
            self.easytier_release_radio.setChecked(True)
            print(f"⚠️ 自动选择版本类型失败，使用默认正式版: {e}")

    def on_easytier_version_type_changed(self):
        """版本类型改变时的回调"""
        # 显示切换状态
        if hasattr(self, 'easytier_version_card'):
            version_type = "预发行版" if (hasattr(self, 'easytier_prerelease_radio') and
                                      self.easytier_prerelease_radio.isChecked()) else "正式版"
            self.easytier_version_card.update_info(status=f"正在切换到{version_type}...")

        # 使用防抖定时器，避免快速切换时频繁请求
        if hasattr(self, 'easytier_version_check_timer'):
            self.easytier_version_check_timer.stop()
            self.easytier_version_check_timer.start()

    def delayed_easytier_version_check(self):
        """延迟执行的版本检查"""
        if hasattr(self, 'easytier_version_card'):
            self.check_easytier_update()

    def create_easytier_mirror_controls(self, layout):
        """创建EasyTier镜像选择控件"""
        # 镜像选择区域
        mirror_container = QWidget()
        mirror_layout = QVBoxLayout()
        mirror_layout.setContentsMargins(0, 5, 0, 0)
        mirror_layout.setSpacing(8)

        # 镜像选择标签和下拉框
        mirror_row = QHBoxLayout()
        mirror_row.setSpacing(10)

        mirror_label = QLabel("下载镜像:")
        mirror_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)

        self.easytier_mirror_combo = QComboBox()
        self.easytier_mirror_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e1e2e;
                border: 2px solid #313244;
                border-radius: 4px;
                padding: 6px 8px;
                color: #cdd6f4;
                font-size: 12px;
                min-width: 200px;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #cdd6f4;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
                color: #cdd6f4;
            }
        """)

        mirror_row.addWidget(mirror_label)
        mirror_row.addWidget(self.easytier_mirror_combo)
        mirror_row.addStretch()

        mirror_layout.addLayout(mirror_row)

        # 状态标签
        self.easytier_status_label = QLabel("准备就绪")
        self.easytier_status_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 12px;
                font-style: italic;
                margin-top: 5px;
            }
        """)
        mirror_layout.addWidget(self.easytier_status_label)

        mirror_container.setLayout(mirror_layout)
        layout.addWidget(mirror_container)

    def download_easytier(self):
        """下载EasyTier"""
        try:
            download_manager = self.get_download_manager()

            # 禁用按钮
            self.easytier_download_btn.setEnabled(False)
            self.easytier_check_btn.setEnabled(False)

            # 显示进度条
            self.easytier_progress.setVisible(True)
            self.easytier_progress.setRange(0, 100)  # 设置进度范围
            self.easytier_progress.setValue(0)  # 初始化为0

            # 更新状态
            self.easytier_version_card.update_info(status="下载中...")
            self.easytier_status_label.setText("正在下载...")

            # 获取选中的镜像
            selected_mirror = None
            if hasattr(self, 'easytier_mirror_combo') and self.easytier_mirror_combo.currentData():
                selected_mirror = self.easytier_mirror_combo.currentData()

            # 获取版本类型选择
            include_prerelease = False
            if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
                include_prerelease = True

            # 开始下载
            success = download_manager.download_easytier(
                selected_mirror=selected_mirror,
                include_prerelease=include_prerelease
            )

            if success:
                # 连接进度信号
                if hasattr(download_manager, 'easytier_download_worker') and download_manager.easytier_download_worker:
                    download_manager.easytier_download_worker.progress.connect(self.easytier_progress.setValue)
            else:
                self.easytier_version_card.update_info(status="下载失败")
                self.easytier_status_label.setText("下载失败")
                self.easytier_download_btn.setEnabled(True)
                self.easytier_check_btn.setEnabled(True)
                self.easytier_progress.setVisible(False)

        except Exception as e:
            print(f"下载EasyTier失败: {e}")
            self.easytier_version_card.update_info(status="下载失败")
            self.easytier_status_label.setText(f"下载失败: {e}")
            self.easytier_download_btn.setEnabled(True)
            self.easytier_check_btn.setEnabled(True)
            self.easytier_progress.setVisible(False)

    def check_easytier_update(self):
        """检查EasyTier更新"""
        try:
            download_manager = self.get_download_manager()

            # 禁用按钮
            self.easytier_check_btn.setEnabled(False)
            self.easytier_version_card.update_info(status="检查中...")

            # 获取版本类型选择
            include_prerelease = False
            if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
                include_prerelease = True

            # 检查更新
            has_update, latest_version, message = download_manager.check_easytier_update(include_prerelease)

            # 更新界面
            current_version = download_manager.get_current_easytier_version()
            version_type = "预发行版" if include_prerelease else "正式版"
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version,
                status=message,
                version_type=version_type
            )

            # 更新按钮文本
            version_type = "预发行版" if include_prerelease else "正式版"
            if has_update and latest_version:
                self.easytier_download_btn.setText(f"更新到 v{latest_version} ({version_type})")
            else:
                self.easytier_download_btn.setText(f"下载EasyTier ({version_type})")

        except Exception as e:
            print(f"检查EasyTier更新失败: {e}")
            self.easytier_version_card.update_info(status="检查失败")
        finally:
            self.easytier_check_btn.setEnabled(True)

    def on_easytier_install_finished(self, success: bool, message: str):
        """EasyTier安装完成回调"""
        try:
            # 隐藏进度条
            if hasattr(self, 'easytier_progress'):
                self.easytier_progress.setVisible(False)

            # 重新启用按钮
            if hasattr(self, 'easytier_download_btn'):
                self.easytier_download_btn.setEnabled(True)
            if hasattr(self, 'easytier_check_btn'):
                self.easytier_check_btn.setEnabled(True)

            if success:
                # 安装成功
                if hasattr(self, 'easytier_version_card'):
                    self.easytier_version_card.update_info(status="安装完成")
                if hasattr(self, 'easytier_status_label'):
                    self.easytier_status_label.setText(message)
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #a6e3a1;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)

                # 更新按钮文本
                if hasattr(self, 'easytier_download_btn'):
                    self.easytier_download_btn.setText("重新下载")

                # 重新检查状态
                self.check_current_status()
            else:
                # 安装失败
                if hasattr(self, 'easytier_version_card'):
                    self.easytier_version_card.update_info(status="安装失败")
                if hasattr(self, 'easytier_status_label'):
                    self.easytier_status_label.setText(message)
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #f38ba8;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
        except Exception as e:
            print(f"处理EasyTier安装完成回调失败: {e}")

    def on_me3_installer_download_finished(self, success: bool, message: str, installer_path: str):
        """ME3安装程序下载完成回调"""
        try:
            self.reset_me3_download_ui()

            if success:
                # 下载成功，询问用户是否立即安装
                self.me3_status_label.setText("ME3安装程序下载完成")
                self.me3_status_label.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 11px;
                        padding: 3px;
                        border-radius: 3px;
                        border: 1px solid #a6e3a1;
                    }
                """)

                # 保存版本信息到version.json
                self.save_installer_version_info(installer_path)

                # 更新按钮文本
                self.on_me3_version_type_changed()

                # 直接静默安装，不显示对话框
                self.install_me3_now(installer_path)
            else:
                # 下载失败
                self.me3_status_label.setText(f"安装程序下载失败: {message}")
                self.me3_status_label.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 11px;
                        padding: 3px;
                        border-radius: 3px;
                        border: 1px solid #f38ba8;
                    }
                """)
        except Exception as e:
            print(f"处理ME3安装程序下载完成回调失败: {e}")

    def save_installer_version_info(self, installer_path: str):
        """保存安装程序版本信息到version.json"""
        try:
            import json
            from pathlib import Path
            from datetime import datetime

            # 获取下载管理器
            download_manager = self.get_download_manager()
            version_file = download_manager.me3_dir / "version.json"

            # 读取现有版本信息
            version_info = {}
            if version_file.exists():
                try:
                    with open(version_file, 'r', encoding='utf-8') as f:
                        version_info = json.load(f)
                except:
                    version_info = {}

            # 获取当前最新版本信息
            latest_version = getattr(self, '_latest_me3_version', None)
            if not latest_version:
                # 如果没有缓存的版本信息，尝试从版本卡片获取
                if hasattr(self, 'me3_version_card'):
                    latest_version = self.me3_version_card.latest_version

            # 获取下载链接而不是本地路径
            download_url = None
            try:
                release_info = download_manager.get_latest_release_info()
                if release_info:
                    download_url = download_manager.get_installer_download_url(release_info)
            except Exception as e:
                print(f"获取下载链接失败: {e}")

            # 更新安装程序信息
            version_info.update({
                'installer_version': latest_version or 'unknown',
                'installer_path': download_url or str(installer_path),  # 优先使用下载链接
                'installer_downloaded_at': str(datetime.now()),
                'installer_exists': True
            })

            # 保存到文件
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)

            print(f"安装程序版本信息已保存: {latest_version}, 下载链接: {download_url}")

        except Exception as e:
            print(f"保存安装程序版本信息失败: {e}")

    def save_portable_version_info(self):
        """保存便携版版本信息到version.json"""
        try:
            import json
            from pathlib import Path
            from datetime import datetime

            # 获取下载管理器
            download_manager = self.get_download_manager()
            version_file = download_manager.me3_dir / "version.json"

            # 读取现有版本信息
            version_info = {}
            if version_file.exists():
                try:
                    with open(version_file, 'r', encoding='utf-8') as f:
                        version_info = json.load(f)
                except:
                    version_info = {}

            # 获取当前最新版本信息
            latest_version = getattr(self, '_latest_me3_version', None)
            if not latest_version:
                # 如果没有缓存的版本信息，尝试从版本卡片获取
                if hasattr(self, 'me3_version_card'):
                    latest_version = self.me3_version_card.latest_version

            # 更新便携版信息
            version_info.update({
                'portable_version': latest_version or 'unknown',
                'portable_downloaded_at': str(datetime.now()),
                'portable_installed': True
            })

            # 保存到文件
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)

            print(f"便携版版本信息已保存: {latest_version}")

        except Exception as e:
            print(f"保存便携版版本信息失败: {e}")

    def install_me3_now(self, installer_path: str):
        """立即安装ME3"""
        try:
            import subprocess
            import os

            # 使用统一的安装路径
            install_dir = f"{os.environ.get('LOCALAPPDATA', '')}\\Programs\\garyttierney\\me3"
            cmd = [installer_path, "/S", f"/D={install_dir}"]

            self.me3_status_label.setText("正在安装ME3...")

            # 在后台运行安装程序
            import sys
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            process = subprocess.Popen(cmd, creationflags=creation_flags)

            # 使用定时器检查安装进度
            from PySide6.QtCore import QTimer
            self.install_check_timer = QTimer()
            self.install_check_timer.timeout.connect(lambda: self.check_install_progress(process, install_dir))
            self.install_check_timer.start(1000)  # 每秒检查一次

        except Exception as e:
            self.me3_status_label.setText(f"启动安装程序失败: {str(e)}")

    def check_install_progress(self, process, install_dir):
        """检查安装进度"""
        try:
            # 检查进程是否结束
            if process.poll() is not None:
                # 安装程序已结束
                self.install_check_timer.stop()

                # 检查安装是否成功
                from pathlib import Path
                me3_exe = Path(install_dir) / "bin" / "me3.exe"
                if me3_exe.exists():
                    self.me3_status_label.setText("ME3安装完成！")
                    self.me3_status_label.setStyleSheet("""
                        QLabel {
                            color: #a6e3a1;
                            font-size: 11px;
                            padding: 3px;
                            border-radius: 3px;
                            border: 1px solid #a6e3a1;
                        }
                    """)
                    # 重新检查状态
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(2000, self.check_current_status)
                else:
                    self.me3_status_label.setText("ME3安装可能失败，请检查")
                    self.me3_status_label.setStyleSheet("""
                        QLabel {
                            color: #f38ba8;
                            font-size: 11px;
                            padding: 3px;
                            border-radius: 3px;
                            border: 1px solid #f38ba8;
                        }
                    """)
        except Exception as e:
            print(f"检查安装进度失败: {e}")
            self.install_check_timer.stop()

    # ==================== OnlineFix 相关方法 ====================

    def download_onlinefix(self):
        """下载OnlineFix工具包"""
        try:
            download_manager = self.get_download_manager()

            # 禁用下载按钮，显示进度条
            self.onlinefix_download_btn.setEnabled(False)
            self.onlinefix_download_btn.setText("📥 下载中...")
            self.onlinefix_progress.setVisible(True)
            self.onlinefix_progress.setValue(0)

            # 更新状态
            self.onlinefix_status_label.setText("正在下载...")
            self.onlinefix_status_label.setStyleSheet("""
                QLabel {
                    color: #fab387;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #313244;
                    border-radius: 4px;
                    border: 1px solid #fab387;
                }
            """)

            # 开始下载
            success = download_manager.download_onlinefix()
            if not success:
                self.reset_onlinefix_download_ui()
                self.onlinefix_status_label.setText("下载启动失败")
                self.onlinefix_status_label.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 12px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)

        except Exception as e:
            print(f"下载OnlineFix失败: {e}")
            self.reset_onlinefix_download_ui()
            self.onlinefix_status_label.setText(f"下载失败: {str(e)}")

    def check_onlinefix_status(self):
        """检查OnlineFix状态"""
        try:
            download_manager = self.get_download_manager()

            # 检查OnlineFix是否可用
            if download_manager.is_onlinefix_available():
                self.onlinefix_status_label.setText("✅ 工具包完整")
                self.onlinefix_status_label.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 12px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #a6e3a1;
                    }
                """)
                self.onlinefix_detail_label.setText("所有必需文件已就绪")
            else:
                self.onlinefix_status_label.setText("❌ 工具包缺失")
                self.onlinefix_status_label.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 12px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                self.onlinefix_detail_label.setText("需要下载OnlineFix工具包")

        except Exception as e:
            print(f"检查OnlineFix状态失败: {e}")
            self.onlinefix_status_label.setText("检查失败")

    def on_onlinefix_download_finished(self, success: bool, message: str):
        """OnlineFix下载完成回调"""
        try:
            self.reset_onlinefix_download_ui()

            if success:
                self.onlinefix_status_label.setText("✅ 下载完成")
                self.onlinefix_status_label.setStyleSheet("""
                    QLabel {
                        color: #a6e3a1;
                        font-size: 12px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #a6e3a1;
                    }
                """)
                self.onlinefix_detail_label.setText("OnlineFix工具包已安装完成")
                # 延迟一点时间确保文件系统同步，然后重新检查状态
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, self.check_onlinefix_status)
            else:
                self.onlinefix_status_label.setText(f"❌ 下载失败")
                self.onlinefix_status_label.setStyleSheet("""
                    QLabel {
                        color: #f38ba8;
                        font-size: 12px;
                        padding: 4px 8px;
                        background-color: #313244;
                        border-radius: 4px;
                        border: 1px solid #f38ba8;
                    }
                """)
                self.onlinefix_detail_label.setText(f"错误: {message}")

        except Exception as e:
            print(f"处理OnlineFix下载完成回调失败: {e}")

    def update_onlinefix_progress(self, progress: int):
        """更新OnlineFix下载进度"""
        try:
            self.onlinefix_progress.setValue(progress)
        except Exception as e:
            print(f"更新OnlineFix下载进度失败: {e}")

    def reset_onlinefix_download_ui(self):
        """重置OnlineFix下载UI状态"""
        try:
            self.onlinefix_download_btn.setEnabled(True)
            self.onlinefix_download_btn.setText("📥 下载工具包")
            self.onlinefix_progress.setVisible(False)
            self.onlinefix_progress.setValue(0)
        except Exception as e:
            print(f"重置OnlineFix下载UI失败: {e}")


# 为了向后兼容，保留原来的类名作为别名
ME3Page = ToolDownloadPage
