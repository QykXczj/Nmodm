"""
工具下载页面
ME3工具和ERModsMerger下载管理
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QFrame, QGroupBox,
                               QTextEdit, QComboBox)
from PySide6.QtCore import Qt, Signal
from .base_page import BasePage


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
            if "已安装" in status:
                color = "#a6e3a1"
                border_color = "#a6e3a1"
                bg_color = "#1e1e2e"
            elif "检查中" in status:
                color = "#fab387"
                border_color = "#fab387"
                bg_color = "#313244"
            else:
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
        self.setup_content()

        # 延迟初始化下载管理器和状态检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.delayed_init)

    def delayed_init(self):
        """延迟初始化"""
        if self.download_manager is None:
            from ...utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()
        self.check_current_status()

    def get_download_manager(self):
        """获取下载管理器（确保已初始化）"""
        if self.download_manager is None:
            from ...utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()
        return self.download_manager

    def setup_content(self):
        """设置页面内容"""
        # 页面描述
        desc_label = QLabel("工具下载页面提供ME3工具和ERModsMerger的自动下载和管理功能。")
        desc_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 14px;
                margin-bottom: 20px;
            }
        """)
        desc_label.setWordWrap(True)
        self.add_content(desc_label)

        # 使用垂直布局
        # ME3工具区域
        me3_widget = self.create_me3_section()
        self.add_content(me3_widget)

        # ERModsMerger工具区域
        erm_widget = self.create_erm_section()
        self.add_content(erm_widget)

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
        """检查当前状态"""
        # 检查ME3工具状态
        dm = self.get_download_manager()
        is_me3_installed = dm.is_me3_installed()
        me3_current_version = dm.get_current_version()

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

        # 检查ERModsMerger状态
        is_erm_installed = dm.is_erm_installed()
        erm_current_version = dm.get_erm_current_version()

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

        # 加载镜像列表
        self.load_mirrors()

        # 异步检查最新版本
        self.check_me3_updates()
        self.check_erm_updates()
    
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


# 为了向后兼容，保留原来的类名作为别名
ME3Page = ToolDownloadPage
    

