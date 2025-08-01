"""
工具下载页面
ME3工具和ERModsMerger下载管理
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QFrame, QGroupBox,
                               QTextEdit, QComboBox)
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
                'me3_version': self.download_manager.get_current_version(),
                'erm_installed': self.download_manager.is_erm_installed(),
                'erm_version': self.download_manager.get_erm_current_version(),
                'easytier_version': self.download_manager.get_current_easytier_version()
            }
            self.status_checked.emit(status_info)
        except Exception as e:
            print(f"状态检查失败: {e}")
            # 发送空状态，让UI显示默认状态
            self.status_checked.emit({})


class UpdateCheckWorker(QThread):
    """更新检查工作线程"""
    me3_update_checked = Signal(dict)
    erm_update_checked = Signal(dict)
    easytier_update_checked = Signal(dict)

    def __init__(self, download_manager):
        super().__init__()
        self.download_manager = download_manager

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

        # 检查ERM更新
        try:
            release_info = self.download_manager.get_erm_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                current_version = self.download_manager.get_erm_current_version()
                self.erm_update_checked.emit({
                    'success': True,
                    'latest_version': latest_version,
                    'current_version': current_version
                })
            else:
                self.erm_update_checked.emit({'success': False, 'error': '无法获取版本信息'})
        except Exception as e:
            self.erm_update_checked.emit({'success': False, 'error': str(e)})

        # 检查EasyTier更新
        try:
            has_update, latest_version, message = self.download_manager.check_easytier_update()
            current_version = self.download_manager.get_current_easytier_version()
            self.easytier_update_checked.emit({
                'success': True,
                'has_update': has_update,
                'latest_version': latest_version,
                'current_version': current_version,
                'message': message
            })
        except Exception as e:
            self.easytier_update_checked.emit({'success': False, 'error': str(e)})


class VersionInfoCard(QFrame):
    """版本信息卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            VersionInfoCard {
                background-color: #1e1e2e;
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
                background-color: #313244;
                border-radius: 6px;
                border: 2px solid #f38ba8;
            }
        """)

        right_layout.addWidget(self.status_label)

        # 添加到主布局
        main_layout.addLayout(left_layout, 2)  # 左侧占2份
        main_layout.addLayout(right_layout, 1)  # 右侧占1份

        self.setLayout(main_layout)
    
    def update_info(self, current_version=None, latest_version=None, status=None):
        """更新版本信息"""
        if current_version is not None:
            self.current_version_label.setText(f"当前版本: {current_version or '未安装'}")
        
        if latest_version is not None:
            self.latest_version_label.setText(f"最新版本: {latest_version or '获取失败'}")
        
        if status is not None:
            # 根据状态设置不同的颜色和样式
            if any(keyword in status for keyword in ["已安装", "安装完成", "已是最新版本", "最新版本"]):
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
                    background-color: {bg_color};
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
        self.erm_download_worker = None
        self.easytier_download_worker = None
        self.status_check_worker = None  # 状态检查工作线程
        self.update_check_worker = None  # 更新检查工作线程
        self.setup_content()

        # 延迟初始化下载管理器和状态检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.delayed_init)

    def delayed_init(self):
        """延迟初始化"""
        if self.download_manager is None:
            from ...utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()
            # 连接EasyTier安装完成信号
            self.download_manager.easytier_install_finished.connect(self.on_easytier_install_finished)
        # 异步检查状态，避免阻塞UI
        QTimer.singleShot(100, self.check_current_status)

    def get_download_manager(self):
        """获取下载管理器（确保已初始化）"""
        if self.download_manager is None:
            from ...utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()
            # 连接EasyTier安装完成信号
            self.download_manager.easytier_install_finished.connect(self.on_easytier_install_finished)
        return self.download_manager

    def setup_content(self):
        """设置页面内容"""
        # 页面描述
        desc_label = QLabel("工具下载页面提供ME3工具、ERModsMerger和EasyTier的自动下载和管理功能。")
        desc_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 14px;
                margin-bottom: 15px;
            }
        """)
        desc_label.setWordWrap(True)
        self.add_content(desc_label)

        # 使用水平布局来减少垂直空间占用
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

        # 创建主容器
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：ME3和ERModsMerger并排
        first_row = QWidget()
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setSpacing(15)
        first_row_layout.setContentsMargins(0, 0, 0, 0)

        me3_widget = self.create_me3_section()
        erm_widget = self.create_erm_section()

        first_row_layout.addWidget(me3_widget)
        first_row_layout.addWidget(erm_widget)

        # 第二行：EasyTier独占一行（因为比较重要）
        easytier_widget = self.create_easytier_section()

        main_layout.addWidget(first_row)
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

        # ME3下载控制区域
        self.create_me3_download_controls(layout)

        section.setLayout(layout)
        return section
    
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

        # 下载/更新按钮
        self.me3_download_btn = QPushButton("下载ME3工具")
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
    
    def create_erm_section(self):
        """创建ERModsMerger工具区域"""
        section = QGroupBox("ERModsMerger")
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
        self.erm_version_card = VersionInfoCard()
        layout.addWidget(self.erm_version_card)

        # ERModsMerger下载控制区域
        self.create_erm_download_controls(layout)

        section.setLayout(layout)
        return section

    def create_erm_download_controls(self, layout):
        """创建ERModsMerger下载控制区域"""
        # 下载按钮区域
        button_container = QWidget()
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # 下载/更新按钮
        self.erm_download_btn = QPushButton("下载ERModsMerger")
        self.erm_download_btn.setFixedHeight(35)
        self.erm_download_btn.setStyleSheet("""
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
        self.erm_download_btn.clicked.connect(self.start_erm_download)

        # 检查更新按钮
        self.erm_check_update_btn = QPushButton("检查更新")
        self.erm_check_update_btn.setFixedHeight(35)
        self.erm_check_update_btn.setStyleSheet("""
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
        self.erm_check_update_btn.clicked.connect(self.check_erm_updates)

        # 取消下载按钮
        self.erm_cancel_btn = QPushButton("取消下载")
        self.erm_cancel_btn.setFixedHeight(35)
        self.erm_cancel_btn.setStyleSheet("""
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
        self.erm_cancel_btn.clicked.connect(self.cancel_erm_download)
        self.erm_cancel_btn.setVisible(False)

        btn_row.addWidget(self.erm_download_btn)
        btn_row.addWidget(self.erm_cancel_btn)
        btn_row.addWidget(self.erm_check_update_btn)
        btn_row.addStretch()

        button_layout.addLayout(btn_row)

        # 镜像选择
        mirror_row = QHBoxLayout()
        mirror_row.setSpacing(10)

        self.erm_mirror_combo = QComboBox()
        self.erm_mirror_combo.setFixedHeight(30)
        self.erm_mirror_combo.setStyleSheet("""
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

        mirror_row.addWidget(self.erm_mirror_combo)
        mirror_row.addWidget(mirror_tip_label)
        mirror_row.addStretch()

        button_layout.addLayout(mirror_row)

        button_container.setLayout(button_layout)
        layout.addWidget(button_container)

        # 进度条
        self.erm_progress_bar = QProgressBar()
        self.erm_progress_bar.setVisible(False)
        self.erm_progress_bar.setStyleSheet("""
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
        layout.addWidget(self.erm_progress_bar)

        # 状态标签
        self.erm_status_label = QLabel()
        self.erm_status_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 11px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.erm_status_label)

    def check_current_status(self):
        """检查当前状态（异步）"""
        # 显示检查状态的提示
        if hasattr(self, 'me3_status_label'):
            self.me3_status_label.setText("正在检查状态...")
        if hasattr(self, 'erm_status_label'):
            self.erm_status_label.setText("正在检查状态...")
        if hasattr(self, 'easytier_status_label'):
            self.easytier_status_label.setText("正在检查状态...")

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
            me3_current_version = status_info.get('me3_version')

            if is_me3_installed:
                self.me3_version_card.update_info(
                    current_version=me3_current_version,
                    status="已安装"
                )
                self.me3_download_btn.setText("重新下载")
            else:
                self.me3_version_card.update_info(
                    current_version=None,
                    status="未安装"
                )
                self.me3_download_btn.setText("下载ME3工具")

            # 更新ERModsMerger状态
            is_erm_installed = status_info.get('erm_installed', False)
            erm_current_version = status_info.get('erm_version')

            if is_erm_installed:
                self.erm_version_card.update_info(
                    current_version=erm_current_version,
                    status="已安装"
                )
                self.erm_download_btn.setText("重新下载")
            else:
                self.erm_version_card.update_info(
                    current_version=None,
                    status="未安装"
                )
                self.erm_download_btn.setText("下载ERModsMerger")

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

            # 加载镜像列表（这个操作比较快，可以在UI线程执行）
            self.load_mirrors()

            # 启动异步更新检查
            self.start_update_check()

        except Exception as e:
            print(f"处理状态检查结果失败: {e}")
            # 设置默认状态
            if hasattr(self, 'me3_status_label'):
                self.me3_status_label.setText("状态检查失败")
            if hasattr(self, 'erm_status_label'):
                self.erm_status_label.setText("状态检查失败")
            if hasattr(self, 'easytier_status_label'):
                self.easytier_status_label.setText("状态检查失败")

    def start_update_check(self):
        """启动异步更新检查"""
        # 显示检查状态
        if hasattr(self, 'me3_status_label'):
            self.me3_status_label.setText("正在检查最新版本...")
        if hasattr(self, 'erm_status_label'):
            self.erm_status_label.setText("正在检查最新版本...")
        if hasattr(self, 'easytier_status_label'):
            self.easytier_status_label.setText("正在检查最新版本...")

        # 如果已有更新检查线程在运行，先停止它
        if self.update_check_worker and self.update_check_worker.isRunning():
            self.update_check_worker.quit()
            self.update_check_worker.wait()

        # 创建并启动更新检查工作线程
        dm = self.get_download_manager()
        self.update_check_worker = UpdateCheckWorker(dm)
        self.update_check_worker.me3_update_checked.connect(self.on_me3_update_checked)
        self.update_check_worker.erm_update_checked.connect(self.on_erm_update_checked)
        self.update_check_worker.easytier_update_checked.connect(self.on_easytier_update_checked)
        self.update_check_worker.start()

    def on_me3_update_checked(self, result):
        """ME3更新检查完成"""
        try:
            if result.get('success', False):
                latest_version = result.get('latest_version', '未知')
                current_version = result.get('current_version')

                self.me3_version_card.update_info(latest_version=latest_version)

                if current_version and current_version != latest_version:
                    self.me3_download_btn.setText("更新ME3工具")
                    self.me3_status_label.setText(f"发现新版本: {latest_version}")
                elif current_version:
                    self.me3_status_label.setText("已是最新版本")
                else:
                    self.me3_status_label.setText("可以下载最新版本")
            else:
                error = result.get('error', '未知错误')
                self.me3_version_card.update_info(latest_version="获取失败")
                self.me3_status_label.setText(f"检查更新失败: {error}")
        except Exception as e:
            self.me3_status_label.setText(f"处理更新信息失败: {str(e)}")

    def on_erm_update_checked(self, result):
        """ERM更新检查完成"""
        try:
            if result.get('success', False):
                latest_version = result.get('latest_version', '未知')
                current_version = result.get('current_version')

                self.erm_version_card.update_info(latest_version=latest_version)

                if current_version and current_version != latest_version:
                    self.erm_download_btn.setText("更新ERModsMerger")
                    self.erm_status_label.setText(f"发现新版本: {latest_version}")
                elif current_version:
                    self.erm_status_label.setText("已是最新版本")
                else:
                    self.erm_status_label.setText("可以下载最新版本")
            else:
                error = result.get('error', '未知错误')
                self.erm_version_card.update_info(latest_version="获取失败")
                self.erm_status_label.setText(f"检查更新失败: {error}")
        except Exception as e:
            self.erm_status_label.setText(f"处理更新信息失败: {str(e)}")

    def on_easytier_update_checked(self, result):
        """EasyTier更新检查完成"""
        try:
            if result.get('success', False):
                has_update = result.get('has_update', False)
                latest_version = result.get('latest_version')
                current_version = result.get('current_version')
                message = result.get('message', '')

                self.easytier_version_card.update_info(
                    current_version=current_version,
                    latest_version=latest_version,
                    status=message
                )

                # 更新状态标签
                if has_update and latest_version:
                    self.easytier_download_btn.setText(f"更新到 v{latest_version}")
                    self.easytier_status_label.setText(f"发现新版本: v{latest_version}")
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #f9e2af;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
                elif current_version:
                    self.easytier_download_btn.setText("重新下载")
                    self.easytier_status_label.setText("已是最新版本")
                    self.easytier_status_label.setStyleSheet("""
                        QLabel {
                            color: #a6e3a1;
                            font-size: 12px;
                            font-style: italic;
                            margin-top: 5px;
                        }
                    """)
                else:
                    self.easytier_download_btn.setText("下载EasyTier")
                    self.easytier_status_label.setText("可以下载最新版本")
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

                # 检查是否需要更新
                current_version = dm.get_current_version()
                if current_version and current_version != latest_version:
                    self.me3_download_btn.setText("更新ME3工具")
                    self.me3_status_label.setText(f"发现新版本: {latest_version}")
                elif current_version:
                    self.me3_status_label.setText("已是最新版本")
                else:
                    self.me3_status_label.setText("可以下载最新版本")
            else:
                self.me3_version_card.update_info(latest_version="获取失败")
                self.me3_status_label.setText("无法获取版本信息，请检查网络连接")
        except Exception as e:
            self.me3_status_label.setText(f"检查更新失败: {str(e)}")

    def check_erm_updates(self):
        """检查ERModsMerger更新"""
        self.erm_status_label.setText("正在检查最新版本...")

        try:
            dm = self.get_download_manager()
            release_info = dm.get_erm_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                self.erm_version_card.update_info(latest_version=latest_version)

                # 检查是否需要更新
                current_version = dm.get_erm_current_version()
                if current_version and current_version != latest_version:
                    self.erm_download_btn.setText("更新ERModsMerger")
                    self.erm_status_label.setText(f"发现新版本: {latest_version}")
                elif current_version:
                    self.erm_status_label.setText("已是最新版本")
                else:
                    self.erm_status_label.setText("可以下载最新版本")
            else:
                self.erm_version_card.update_info(latest_version="获取失败")
                self.erm_status_label.setText("无法获取版本信息，请检查网络连接")
        except Exception as e:
            self.erm_status_label.setText(f"检查更新失败: {str(e)}")

    def check_easytier_updates(self):
        """检查EasyTier更新"""
        try:
            dm = self.get_download_manager()
            has_update, latest_version, message = dm.check_easytier_update()

            # 更新界面
            current_version = dm.get_current_easytier_version()
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version,
                status=message
            )

            # 更新按钮文本
            if has_update and latest_version:
                self.easytier_download_btn.setText(f"更新到 v{latest_version}")
            elif current_version:
                self.easytier_download_btn.setText("重新下载")
            else:
                self.easytier_download_btn.setText("下载EasyTier")

        except Exception as e:
            print(f"检查EasyTier更新失败: {e}")
            self.easytier_version_card.update_info(status="检查失败")
    
    def start_me3_download(self):
        """开始ME3下载"""
        if self.me3_download_worker and self.me3_download_worker.isRunning():
            self.me3_status_label.setText("下载正在进行中，请稍候")
            return

        self.me3_download_worker = self.get_download_manager().download_me3()
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
        self.me3_status_label.setText("正在下载...")

        # 开始下载
        self.me3_download_worker.start()

    def start_erm_download(self):
        """开始ERModsMerger下载"""
        if self.erm_download_worker and self.erm_download_worker.isRunning():
            self.erm_status_label.setText("下载正在进行中，请稍候")
            return

        self.erm_download_worker = self.get_download_manager().download_erm()
        if not self.erm_download_worker:
            self.erm_status_label.setText("无法创建下载任务，请检查网络连接")
            return

        # 连接信号
        self.erm_download_worker.progress.connect(self.update_erm_progress)
        self.erm_download_worker.finished.connect(self.erm_download_finished)

        # 更新UI状态
        self.erm_download_btn.setVisible(False)
        self.erm_cancel_btn.setVisible(True)
        self.erm_check_update_btn.setEnabled(False)
        self.erm_mirror_combo.setEnabled(False)
        self.erm_progress_bar.setVisible(True)
        self.erm_progress_bar.setValue(0)
        self.erm_status_label.setText("正在下载...")

        # 开始下载
        self.erm_download_worker.start()

    def cancel_me3_download(self):
        """取消ME3下载"""
        if self.me3_download_worker and self.me3_download_worker.isRunning():
            self.me3_download_worker.cancel()
            self.me3_status_label.setText("下载已取消")
            self.reset_me3_download_ui()

    def cancel_erm_download(self):
        """取消ERModsMerger下载"""
        if self.erm_download_worker and self.erm_download_worker.isRunning():
            self.erm_download_worker.cancel()
            self.erm_status_label.setText("下载已取消")
            self.reset_erm_download_ui()

    def reset_me3_download_ui(self):
        """重置ME3下载UI状态"""
        self.me3_download_btn.setVisible(True)
        self.me3_cancel_btn.setVisible(False)
        self.me3_check_update_btn.setEnabled(True)
        self.me3_mirror_combo.setEnabled(True)
        self.me3_progress_bar.setVisible(False)
        self.me3_progress_bar.setValue(0)

    def reset_erm_download_ui(self):
        """重置ERModsMerger下载UI状态"""
        self.erm_download_btn.setVisible(True)
        self.erm_cancel_btn.setVisible(False)
        self.erm_check_update_btn.setEnabled(True)
        self.erm_mirror_combo.setEnabled(True)
        self.erm_progress_bar.setVisible(False)
        self.erm_progress_bar.setValue(0)
    
    def update_me3_progress(self, value):
        """更新ME3下载进度"""
        self.me3_progress_bar.setValue(value)
        self.me3_status_label.setText(f"下载进度: {value}%")

    def update_erm_progress(self, value):
        """更新ERModsMerger下载进度"""
        self.erm_progress_bar.setValue(value)
        self.erm_status_label.setText(f"下载进度: {value}%")

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
                    background-color: #1e1e2e;
                    border-radius: 3px;
                    border: 1px solid #a6e3a1;
                }
            """)
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
                    background-color: #313244;
                    border-radius: 3px;
                    border: 1px solid #f38ba8;
                }
            """)

    def erm_download_finished(self, success, message):
        """ERModsMerger下载完成"""
        self.reset_erm_download_ui()

        if success:
            self.erm_status_label.setText("ERModsMerger下载并安装成功")
            # 设置成功状态样式
            self.erm_status_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 11px;
                    padding: 3px;
                    background-color: #1e1e2e;
                    border-radius: 3px;
                    border: 1px solid #a6e3a1;
                }
            """)
            # 延迟检查状态，避免覆盖成功消息
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self.check_current_status)
            self.status_updated.emit()  # 发送状态更新信号
        else:
            self.erm_status_label.setText(f"下载失败: {message}")
            # 设置错误状态样式
            self.erm_status_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 11px;
                    padding: 3px;
                    background-color: #313244;
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

        # 加载ERModsMerger镜像
        if hasattr(self, 'erm_mirror_combo'):
            self.erm_mirror_combo.clear()
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

                self.erm_mirror_combo.addItem(display_name, mirror)

            # 设置当前选中的镜像（第一个）
            if mirrors:
                self.erm_mirror_combo.setCurrentIndex(0)

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

            # 开始下载
            success = download_manager.download_easytier(selected_mirror=selected_mirror)

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

            # 检查更新
            has_update, latest_version, message = download_manager.check_easytier_update()

            # 更新界面
            current_version = download_manager.get_current_easytier_version()
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version,
                status=message
            )

            # 更新按钮文本
            if has_update and latest_version:
                self.easytier_download_btn.setText(f"更新到 v{latest_version}")
            else:
                self.easytier_download_btn.setText("下载EasyTier")

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


# 为了向后兼容，保留原来的类名作为别名
ME3Page = ToolDownloadPage
    

