"""
工具下载页面
ME3工具和EasyTier下载管理
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QFrame, QGroupBox,
                               QTextEdit, QComboBox, QRadioButton)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from .base_page import BasePage
from src.i18n import TLabel, t, TranslationManager


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
        self.current_version_label = QLabel(f"{t('me3_page.label.current_version')} {t('me3_page.status.not_installed')}")
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
        self.latest_version_label = QLabel(f"{t('me3_page.label.latest_version')} {t('me3_page.status.checking')}")
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

        # 添加到主布局
        main_layout.addLayout(left_layout, 2)  # 左侧占2份
        main_layout.addLayout(right_layout, 1)  # 右侧占1份

        self.setLayout(main_layout)
    
    def update_info(self, current_version=None, latest_version=None, version_type=None, current_version_type=None):
        """更新版本信息"""
        if current_version is not None:
            current_text = f"{t('me3_page.label.current_version')} {current_version or t('me3_page.status.not_installed')}"
            if current_version and current_version_type:
                current_text += f" ({current_version_type})"
            self.current_version_label.setText(current_text)

        if latest_version is not None:
            self.latest_version = latest_version  # 保存latest_version
            latest_text = f"{t('me3_page.label.latest_version')} {latest_version or t('me3_page.error.get_failed')}"
            if version_type:
                latest_text += f" ({version_type})"
            self.latest_version_label.setText(latest_text)
        



class ToolDownloadPage(BasePage):
    """工具下载页面"""

    # 状态更新信号
    status_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(t("me3_page.page_title"), parent)
        self.download_manager = None  # 延迟初始化
        self.me3_download_worker = None
        self.me3_installer_download_worker = None  # ME3安装程序下载工作线程
        self.easytier_download_worker = None
        self.onlinefix_download_worker = None  # OnlineFix下载工作线程
        self.status_check_worker = None  # 状态检查工作线程
        self.update_check_worker = None  # 更新检查工作线程
        self.setup_content()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

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
        self.me3_section = QGroupBox(t("me3_page.section.me3_tool"))
        section = self.me3_section
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
        section = QGroupBox(t("me3_page.onlinefix_section.title"))
        # 保存组件引用用于语言切换
        self.onlinefix_section = section
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
        status_label = TLabel("me3_page.onlinefix_section.label.toolkit_status")
        # 保存组件引用用于语言切换
        self.onlinefix_status_title_label = status_label
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
        self.onlinefix_status_label = QLabel(t("me3_page.onlinefix_section.status.checking"))
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
        self.onlinefix_detail_label = QLabel(t("me3_page.onlinefix_section.detail.includes"))
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
        self.onlinefix_download_btn = QPushButton(t("me3_page.onlinefix_section.button.download"))
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
        self.onlinefix_check_btn = QPushButton(t("me3_page.onlinefix_section.button.check_status"))
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
        self.me3_download_btn = QPushButton(t("me3_page.button.download_portable"))
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
        self.me3_check_update_btn = QPushButton(t("me3_page.button.check_update"))
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
        self.me3_vcredist_btn = QPushButton(t("me3_page.button.fix_runtime"))
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

        # 卸载安装版按钮
        self.me3_uninstall_btn = QPushButton(t("me3_page.button.uninstall"))
        self.me3_uninstall_btn.setFixedHeight(35)
        self.me3_uninstall_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.me3_uninstall_btn.clicked.connect(self.uninstall_me3_full)
        self.me3_uninstall_btn.setVisible(False)  # 初始隐藏，根据安装状态动态显示

        # 取消下载按钮
        self.me3_cancel_btn = QPushButton(t("me3_page.button.cancel"))
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
        btn_row.addWidget(self.me3_uninstall_btn)
        btn_row.addStretch()

        button_layout.addLayout(btn_row)



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

        # 移除状态标签组件

    def check_current_status(self):
        """检查当前状态（异步）"""
        # 移除状态标签的文本设置
        if hasattr(self, 'onlinefix_status_label'):
            self.onlinefix_status_label.setText(t("me3_page.status.checking_status"))

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

            # 更新卸载按钮显示状态
            self.update_uninstall_button_visibility(is_me3_full_installed)

            # 更新EasyTier状态
            easytier_current_version = status_info.get('easytier_version')

            if easytier_current_version:
                self.easytier_version_card.update_info(
                    current_version=easytier_current_version
                )
                # 移除动态提示文本
            else:
                self.easytier_version_card.update_info(
                    current_version=None
                )
                # 移除动态提示文本

            # 更新OnlineFix状态
            if hasattr(self, 'onlinefix_status_label'):
                self.check_onlinefix_status()



            # 启动异步更新检查
            self.start_update_check()

        except Exception as e:
            print(f"处理状态检查结果失败: {e}")
            # 设置默认状态
            # 移除状态标签的文本设置
            if hasattr(self, 'onlinefix_status_label'):
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.status_check_failed"))

    def start_update_check(self):
        """启动异步更新检查"""
        # 移除状态标签的文本设置
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
                latest_version = result.get('latest_version', t("me3_page.error.unknown"))
                current_version = result.get('current_version')

                self.me3_version_card.update_info(latest_version=latest_version)

                # 移除状态标签的文本设置
                if current_version and current_version != latest_version:
                    # 触发版本类型切换处理，更新按钮文本
                    self.on_me3_version_type_changed()
                elif current_version:
                    # 触发版本类型切换处理，更新按钮文本
                    self.on_me3_version_type_changed()
            else:
                error = result.get('error', t("me3_page.error.unknown_error"))
                self.me3_version_card.update_info(latest_version=t("me3_page.error.get_failed"))
                # 移除状态标签的文本设置
        except Exception as e:
            # 移除状态标签的文本设置
            pass

    def on_easytier_update_checked(self, result):
        """EasyTier更新检查完成"""
        try:
            if result.get('success', False):
                has_update = result.get('has_update', False)
                latest_version = result.get('latest_version')
                current_version = result.get('current_version')
                message = result.get('message', '')
                include_prerelease = result.get('include_prerelease', False)

                version_type = t("me3_page.version_type.prerelease") if include_prerelease else t("me3_page.version_type.release")
                self.easytier_version_card.update_info(
                    current_version=current_version,
                    latest_version=latest_version,
                    version_type=version_type
                )

                # 移除动态提示文本
            else:
                error = result.get('error', '未知错误')
                # 移除状态标签的文本设置
        except Exception as e:
            # 移除状态标签的文本设置
            pass

    def check_me3_updates(self):
        """检查ME3更新"""
        # 移除状态标签的文本设置

        try:
            dm = self.get_download_manager()
            release_info = dm.get_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                self.me3_version_card.update_info(latest_version=latest_version)

                # 检查是否需要更新（根据当前选择的版本类型）
                version_type = "full" if self.me3_full_radio.isChecked() else "portable"
                current_version = dm.get_version_by_type(version_type)
                if current_version and current_version != latest_version:
                    self.me3_download_btn.setText(t("me3_page.button.update"))
                    # 移除动态提示文本
                elif current_version:
                    # 移除动态提示文本
                    pass
                else:
                    # 移除动态提示文本
                    pass
            else:
                self.me3_version_card.update_info(latest_version=t("me3_page.error.get_failed"))
                # 移除状态标签的文本设置
        except Exception as e:
            # 移除状态标签的文本设置
            pass

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
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version
            )

            # 移除动态提示文本，不再需要更新按钮文本

        except Exception as e:
            print(f"检查EasyTier更新失败: {e}")
            # 检查失败时不更新版本卡片，只更新状态标签
    
    def start_me3_download(self):
        """开始ME3下载"""
        if self.me3_download_worker and self.me3_download_worker.isRunning():
            # 移除状态标签的文本设置
            return
        if self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            # 移除状态标签的文本设置
            return

        # 根据选择的版本类型决定下载方式
        if self.me3_full_radio.isChecked():
            # 检查是否已有安装程序
            download_manager = self.get_download_manager()
            installer_path = download_manager.me3_dir / "me3_installer.exe"

            if installer_path.exists() and self.me3_download_btn.text() == t("me3_page.button.install"):
                # 直接静默安装现有的安装程序
                self.install_me3_now(str(installer_path))
                return
            else:
                # 下载安装版
                self.start_me3_installer_download()
                return

        # 下载便携版（使用智能镜像选择）
        self.me3_download_worker = self.get_download_manager().download_me3()
        if not self.me3_download_worker:
            # 移除状态标签的文本设置
            return

        # 连接信号
        self.me3_download_worker.progress.connect(self.update_me3_progress)
        self.me3_download_worker.finished.connect(self.me3_download_finished)

        # 更新UI状态
        self.me3_download_btn.setVisible(False)
        self.me3_cancel_btn.setVisible(True)
        self.me3_check_update_btn.setEnabled(False)
        self.me3_progress_bar.setVisible(True)
        self.me3_progress_bar.setValue(0)
        # 移除状态标签的文本设置

        # 开始下载
        self.me3_download_worker.start()

    def start_me3_installer_download(self):
        """开始ME3安装程序下载"""
        if self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            # 移除状态标签的文本设置
            return

        # 下载ME3安装程序（使用智能镜像选择）
        self.me3_installer_download_worker = self.get_download_manager().download_me3_installer()
        if not self.me3_installer_download_worker:
            # 移除状态标签的文本设置
            return

        # 连接信号
        self.me3_installer_download_worker.progress.connect(self.update_me3_progress)
        self.me3_installer_download_worker.finished.connect(self.me3_installer_download_finished)

        # 更新UI状态
        self.me3_download_btn.setEnabled(False)
        self.me3_cancel_btn.setVisible(True)
        self.me3_check_update_btn.setEnabled(False)
        self.me3_progress_bar.setVisible(True)
        self.me3_progress_bar.setValue(0)
        # 移除状态标签的文本设置

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
            # 移除状态标签的文本设置
            self.reset_me3_download_ui()
        elif self.me3_installer_download_worker and self.me3_installer_download_worker.isRunning():
            self.me3_installer_download_worker.cancel()
            # 移除状态标签的文本设置

            # 清理不完整的安装程序文件
            self.cleanup_incomplete_installer()

            self.reset_me3_download_ui()

    def reset_me3_download_ui(self):
        """重置ME3下载UI状态"""
        self.me3_download_btn.setVisible(True)
        self.me3_download_btn.setEnabled(True)
        self.me3_cancel_btn.setVisible(False)
        self.me3_check_update_btn.setEnabled(True)
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

            # 移除状态标签的保存和设置

            # 禁用按钮，防止重复点击
            self.me3_vcredist_btn.setEnabled(False)
            self.me3_vcredist_btn.setText(t("me3_page.status.fixing"))
            # 移除状态标签的文本设置

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
                        self.status_update.emit(t("me3_page.status.downloading_vcredist"))

                        # 使用带进度的下载
                        def download_progress(block_num, block_size, total_size):
                            if total_size > 0:
                                percent = min(100, (block_num * block_size * 100) // total_size)
                                self.status_update.emit(f"{t('me3_page.status.downloading_vcredist')} {percent}%")

                        urllib.request.urlretrieve(vcredist_url, vcredist_path, download_progress)

                        # 执行静默安装
                        self.status_update.emit(t("me3_page.status.installing"))
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
            # 移除状态标签的信号连接
            self.vcredist_worker.success.connect(self._update_vcredist_success_ui)
            self.vcredist_worker.error.connect(self._update_vcredist_error_ui)
            self.vcredist_worker.finished.connect(self._vcredist_cleanup)
            self.vcredist_thread.started.connect(self.vcredist_worker.run)

            # 启动线程
            self.vcredist_thread.start()

        except Exception as e:
            # 移除状态标签的文本设置
            pass
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
        # 移除状态标签的文本和样式设置
        self.me3_vcredist_btn.setEnabled(True)
        self.me3_vcredist_btn.setText(t("me3_page.button.fix_runtime"))

        # 移除定时器和状态清除逻辑

    def _update_vcredist_error_ui(self, error_code):
        """更新VC++运行库修复失败的UI状态"""
        # 移除状态标签的文本和样式设置
        self.me3_vcredist_btn.setEnabled(True)
        self.me3_vcredist_btn.setText(t("me3_page.button.fix_runtime"))

    def me3_download_finished(self, success, message):
        """ME3下载完成"""
        self.reset_me3_download_ui()

        if success:
            # 移除状态标签的文本和样式设置

            # 保存便携版版本信息到version.json
            self.save_portable_version_info()

            # 延迟检查状态，避免覆盖成功消息
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self.check_current_status)
            self.status_updated.emit()  # 发送状态更新信号
        else:
            # 移除状态标签的文本和样式设置
            pass



    def create_me3_version_type_selection(self):
        """创建ME3版本类型选择"""
        self.me3_version_type_container = QWidget()
        self.me3_version_type_layout = QHBoxLayout(self.me3_version_type_container)
        self.me3_version_type_layout.setContentsMargins(0, 0, 0, 0)
        self.me3_version_type_layout.setSpacing(20)

        self.me3_portable_radio = QRadioButton(t("me3_page.type.portable"))
        self.me3_full_radio = QRadioButton(t("me3_page.type.full_install"))

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
        self.me3_version_type_label = QLabel(t("me3_page.label.version_type"))
        self.me3_version_type_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        self.me3_version_type_layout.addWidget(self.me3_version_type_label)
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

        # 更新卸载按钮显示状态
        self.update_uninstall_button_visibility(is_full_installed)

        if self.me3_portable_radio.isChecked():
            # 选择便携版
            if is_portable_installed:
                # 检查是否有版本更新（使用统一版本获取接口）
                try:
                    current_version = download_manager.get_version_by_type("portable")
                    latest_version = getattr(self.me3_version_card, 'latest_version', None)

                    if current_version and latest_version and current_version != latest_version:
                        self.me3_download_btn.setText(t("me3_page.button.get_update_portable"))
                    else:
                        self.me3_download_btn.setText(t("me3_page.button.redownload_portable"))
                except Exception as e:
                    print(f"版本比较失败: {e}")
                    self.me3_download_btn.setText(t("me3_page.button.redownload_portable"))
            else:
                self.me3_download_btn.setText(t("me3_page.button.download_portable"))
        else:
            # 选择完整安装版
            if is_full_installed:
                # 检查是否有版本更新（使用统一版本获取接口）
                try:
                    current_version = download_manager.get_version_by_type("full")
                    latest_version = getattr(self.me3_version_card, 'latest_version', None)

                    if current_version and latest_version and current_version != latest_version:
                        self.me3_download_btn.setText(t("me3_page.button.get_update_full"))
                    else:
                        self.me3_download_btn.setText(t("me3_page.button.redownload_full"))
                except Exception as e:
                    print(f"版本比较失败: {e}")
                    self.me3_download_btn.setText(t("me3_page.button.redownload_full"))
            elif installer_exists:
                self.me3_download_btn.setText(t("me3_page.button.install"))
            else:
                self.me3_download_btn.setText(t("me3_page.button.download_full"))

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
                    current_version_type=t("me3_page.version_type.portable")
                )
            else:
                # 便携版未安装，显示未安装（即使安装版已安装）
                self.me3_version_card.update_info(
                    current_version=None,
                    current_version_type=None
                )
        else:
            # 显示安装版信息 - 只有安装版安装了才显示版本
            if is_me3_full_installed:
                self.me3_version_card.update_info(
                    current_version=me3_full_version,
                    current_version_type=t("me3_page.version_type.full")
                )
            else:
                # 安装版未安装，显示未安装（即使便携版已安装）
                self.me3_version_card.update_info(
                    current_version=None,
                    current_version_type=None
                )

    def update_me3_status_text(self):
        """根据当前选择的版本类型更新状态提示文本"""
        try:
            # 获取版本类型文本
            version_type_text = t("me3_page.version_type.full") if self.me3_full_radio.isChecked() else t("me3_page.version_type.portable")

            # 移除状态标签的文本获取和更新逻辑
        except Exception as e:
            print(f"更新状态文本失败: {e}")

    def create_easytier_section(self):
        """创建EasyTier工具区域"""
        section = QGroupBox(t("me3_page.easytier_section.title"))
        # 保存组件引用用于语言切换
        self.easytier_section = section
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

        version_type_label = TLabel("me3_page.easytier_section.label.version_type")
        version_type_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }
        """)
        # 保存组件引用用于语言切换
        self.easytier_version_type_label = version_type_label

        # 版本类型选择单选按钮
        self.easytier_release_radio = QRadioButton(t("me3_page.easytier_section.type.release"))
        self.easytier_prerelease_radio = QRadioButton(t("me3_page.easytier_section.type.prerelease"))

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
        self.easytier_download_btn = QPushButton(t("me3_page.easytier_section.button.download"))
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
        self.easytier_check_btn = QPushButton(t("me3_page.easytier_section.button.check_update"))
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

        # 移除状态标签组件

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
            # 版本类型切换时不更新版本卡片，只更新状态标签

        # 使用防抖定时器，避免快速切换时频繁请求
        if hasattr(self, 'easytier_version_check_timer'):
            self.easytier_version_check_timer.stop()
            self.easytier_version_check_timer.start()

    def delayed_easytier_version_check(self):
        """延迟执行的版本检查"""
        if hasattr(self, 'easytier_version_card'):
            self.check_easytier_update()

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

            # 移除状态标签的文本设置

            # 获取版本类型选择
            include_prerelease = False
            if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
                include_prerelease = True

            # 开始下载（使用智能镜像选择）
            success = download_manager.download_easytier(
                include_prerelease=include_prerelease
            )

            if success:
                # 连接进度信号
                if hasattr(download_manager, 'easytier_download_worker') and download_manager.easytier_download_worker:
                    download_manager.easytier_download_worker.progress.connect(self.easytier_progress.setValue)
            else:
                # 移除状态标签的文本设置
                self.easytier_download_btn.setEnabled(True)
                self.easytier_check_btn.setEnabled(True)
                self.easytier_progress.setVisible(False)

        except Exception as e:
            print(f"下载EasyTier失败: {e}")
            # 移除状态标签的文本设置
            self.easytier_download_btn.setEnabled(True)
            self.easytier_check_btn.setEnabled(True)
            self.easytier_progress.setVisible(False)

    def check_easytier_update(self):
        """检查EasyTier更新"""
        try:
            download_manager = self.get_download_manager()

            # 禁用按钮
            self.easytier_check_btn.setEnabled(False)
            # 检查中时不更新版本卡片，只更新状态标签

            # 获取版本类型选择
            include_prerelease = False
            if hasattr(self, 'easytier_prerelease_radio') and self.easytier_prerelease_radio.isChecked():
                include_prerelease = True

            # 检查更新
            has_update, latest_version, message = download_manager.check_easytier_update(include_prerelease)

            # 更新界面
            current_version = download_manager.get_current_easytier_version()
            version_type = t("me3_page.version_type.prerelease") if include_prerelease else t("me3_page.version_type.release")
            self.easytier_version_card.update_info(
                current_version=current_version,
                latest_version=latest_version,
                version_type=version_type
            )

            # 移除动态提示文本

        except Exception as e:
            print(f"检查EasyTier更新失败: {e}")
            # 检查失败时不更新版本卡片，只更新状态标签
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
                # 移除状态标签的文本和样式设置

                # 重新检查状态
                self.check_current_status()
            else:
                # 移除状态标签的文本和样式设置
                pass
        except Exception as e:
            print(f"处理EasyTier安装完成回调失败: {e}")

    def on_me3_installer_download_finished(self, success: bool, message: str, installer_path: str):
        """ME3安装程序下载完成回调"""
        try:
            self.reset_me3_download_ui()

            if success:
                # 移除状态标签的文本和样式设置

                # 保存版本信息到version.json
                self.save_installer_version_info(installer_path)

                # 更新按钮文本
                self.on_me3_version_type_changed()

                # 直接静默安装，不显示对话框
                self.install_me3_now(installer_path)
            else:
                # 移除状态标签的文本和样式设置
                pass
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

            # 移除状态标签的文本设置

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
            # 移除状态标签的文本设置
            pass

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
                    # 移除状态标签的文本和样式设置
                    # 重新检查状态
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(2000, self.check_current_status)
                else:
                    # 移除状态标签的文本和样式设置
                    pass
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
            self.onlinefix_download_btn.setText(t("me3_page.onlinefix_section.button.downloading"))
            self.onlinefix_progress.setVisible(True)
            self.onlinefix_progress.setValue(0)

            # 更新状态
            self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.downloading"))
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
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.start_failed"))
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
            self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.detail.error").format(message=str(e)))

    def check_onlinefix_status(self):
        """检查OnlineFix状态"""
        try:
            download_manager = self.get_download_manager()

            # 检查OnlineFix是否可用
            if download_manager.is_onlinefix_available():
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.complete"))
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
                self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.ready"))
            else:
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.missing"))
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
                self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.need_download"))

        except Exception as e:
            print(f"检查OnlineFix状态失败: {e}")
            self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.check_failed"))

    def on_onlinefix_download_finished(self, success: bool, message: str):
        """OnlineFix下载完成回调"""
        try:
            self.reset_onlinefix_download_ui()

            if success:
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.download_complete"))
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
                self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.installed"))
                # 延迟一点时间确保文件系统同步，然后重新检查状态
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, self.check_onlinefix_status)
            else:
                self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.download_failed"))
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
                self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.error").format(message=message))

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
            self.onlinefix_download_btn.setText(t("me3_page.onlinefix_section.button.download"))
            self.onlinefix_progress.setVisible(False)
            self.onlinefix_progress.setValue(0)
        except Exception as e:
            print(f"重置OnlineFix下载UI失败: {e}")

    def uninstall_me3_full(self):
        """卸载ME3完整安装版"""
        try:
            # 禁用按钮，显示卸载状态
            self.me3_uninstall_btn.setEnabled(False)
            self.me3_uninstall_btn.setText(f"🗑️ {t('me3_page.status.uninstall_progress')}")
            # 移除状态标签的文本设置

            # 执行卸载
            download_manager = self.get_download_manager()
            success, message = download_manager.uninstall_me3_full()

            if success:
                # 移除状态标签的文本和样式设置

                # 隐藏卸载按钮
                self.me3_uninstall_btn.setVisible(False)

                # 延迟刷新状态
                from PySide6.QtCore import QTimer
                QTimer.singleShot(2000, self.check_current_status)

            else:
                # 移除状态标签的文本和样式设置

                # 重新启用按钮
                self.me3_uninstall_btn.setEnabled(True)
                self.me3_uninstall_btn.setText(t("me3_page.button.uninstall"))

        except Exception as e:
            print(f"卸载ME3安装版失败: {e}")
            # 移除状态标签的文本和样式设置

            # 重新启用按钮
            self.me3_uninstall_btn.setEnabled(True)
            self.me3_uninstall_btn.setText(t("me3_page.button.uninstall"))

    def update_uninstall_button_visibility(self, is_me3_full_installed):
        """更新卸载按钮的显示状态"""
        try:
            if hasattr(self, 'me3_uninstall_btn'):
                # 只有在检测到安装版时才显示卸载按钮
                self.me3_uninstall_btn.setVisible(is_me3_full_installed)

                if is_me3_full_installed:
                    # 确保按钮可用且文本正确
                    self.me3_uninstall_btn.setEnabled(True)
                    self.me3_uninstall_btn.setText(t("me3_page.button.uninstall"))

        except Exception as e:
            print(f"更新卸载按钮显示状态失败: {e}")

    def _on_language_changed(self, locale: str):
        """语言切换回调"""
        try:
            # 更新页面标题
            if hasattr(self, 'title_label'):
                self.title_label.setText(t("me3_page.page_title"))

            # 更新ME3工具区域
            if hasattr(self, 'me3_section'):
                self.me3_section.setTitle(t("me3_page.section.me3_tool"))

            # 更新版本类型选择
            if hasattr(self, 'me3_version_type_label'):
                self.me3_version_type_label.setText(t("me3_page.label.version_type"))
            if hasattr(self, 'me3_portable_radio'):
                self.me3_portable_radio.setText(t("me3_page.type.portable"))
            if hasattr(self, 'me3_full_radio'):
                self.me3_full_radio.setText(t("me3_page.type.full_install"))

            # 更新版本信息卡片
            if hasattr(self, 'me3_version_card'):
                try:
                    # 重新获取当前状态并更新显示
                    current_version = self.me3_version_card.current_version_label.text().split(': ')[-1].split(' (')[0]
                    latest_version = self.me3_version_card.latest_version_label.text().split(': ')[-1].split(' (')[0]

                    # 更新标签文本
                    if current_version == "未安装" or current_version == "Not installed":
                        self.me3_version_card.current_version_label.setText(
                            f"{t('me3_page.label.current_version')} {t('me3_page.status.not_installed')}"
                        )
                    else:
                        self.me3_version_card.current_version_label.setText(
                            f"{t('me3_page.label.current_version')} {current_version}"
                        )

                    if latest_version == "检查中..." or latest_version == "Checking...":
                        self.me3_version_card.latest_version_label.setText(
                            f"{t('me3_page.label.latest_version')} {t('me3_page.status.checking')}"
                        )
                    elif latest_version == "获取失败" or latest_version == "Failed":
                        self.me3_version_card.latest_version_label.setText(
                            f"{t('me3_page.label.latest_version')} {t('me3_page.error.get_failed')}"
                        )
                    else:
                        self.me3_version_card.latest_version_label.setText(
                            f"{t('me3_page.label.latest_version')} {latest_version}"
                        )
                except Exception as e:
                    print(f"更新版本信息卡片失败: {e}")

            # 更新按钮文本
            if hasattr(self, 'me3_check_update_btn'):
                self.me3_check_update_btn.setText(t("me3_page.button.check_update"))
            if hasattr(self, 'me3_vcredist_btn'):
                self.me3_vcredist_btn.setText(t("me3_page.button.fix_runtime"))
            if hasattr(self, 'me3_cancel_btn'):
                self.me3_cancel_btn.setText(t("me3_page.button.cancel"))
            if hasattr(self, 'me3_uninstall_btn'):
                self.me3_uninstall_btn.setText(t("me3_page.button.uninstall"))

            # 更新下载按钮文本（根据当前状态）
            if hasattr(self, 'me3_download_btn') and hasattr(self, 'on_me3_version_type_changed'):
                try:
                    # 重新触发版本类型切换处理，更新按钮文本
                    self.on_me3_version_type_changed()
                except Exception as e:
                    print(f"更新下载按钮文本失败: {e}")

            # 更新EasyTier工具区域
            if hasattr(self, 'easytier_section'):
                self.easytier_section.setTitle(t("me3_page.easytier_section.title"))

            # 更新EasyTier版本类型选择
            if hasattr(self, 'easytier_release_radio'):
                self.easytier_release_radio.setText(t("me3_page.easytier_section.type.release"))
            if hasattr(self, 'easytier_prerelease_radio'):
                self.easytier_prerelease_radio.setText(t("me3_page.easytier_section.type.prerelease"))

            # 更新EasyTier按钮文本
            if hasattr(self, 'easytier_download_btn'):
                self.easytier_download_btn.setText(t("me3_page.easytier_section.button.download"))
            if hasattr(self, 'easytier_check_btn'):
                self.easytier_check_btn.setText(t("me3_page.easytier_section.button.check_update"))

            # 更新EasyTier版本信息卡片
            if hasattr(self, 'easytier_version_card'):
                try:
                    # 重新获取当前状态并更新显示
                    current_version = self.easytier_version_card.current_version_label.text().split(': ')[-1].split(' (')[0]
                    latest_version = self.easytier_version_card.latest_version_label.text().split(': ')[-1].split(' (')[0]

                    # 获取版本类型
                    version_type = None
                    if '(' in self.easytier_version_card.latest_version_label.text():
                        version_type_text = self.easytier_version_card.latest_version_label.text().split('(')[-1].split(')')[0]
                        # 判断是预发行版还是正式版
                        if version_type_text in ["预发行版", "Pre-release"]:
                            version_type = t("me3_page.version_type.prerelease")
                        elif version_type_text in ["正式版", "Release"]:
                            version_type = t("me3_page.version_type.release")

                    # 更新标签文本
                    if current_version == "未安装" or current_version == "Not installed":
                        self.easytier_version_card.current_version_label.setText(
                            f"{t('me3_page.label.current_version')} {t('me3_page.status.not_installed')}"
                        )
                    else:
                        self.easytier_version_card.current_version_label.setText(
                            f"{t('me3_page.label.current_version')} {current_version}"
                        )

                    if latest_version == "检查中..." or latest_version == "Checking...":
                        self.easytier_version_card.latest_version_label.setText(
                            f"{t('me3_page.label.latest_version')} {t('me3_page.status.checking')}"
                        )
                    elif latest_version == "获取失败" or latest_version == "Failed":
                        self.easytier_version_card.latest_version_label.setText(
                            f"{t('me3_page.label.latest_version')} {t('me3_page.error.get_failed')}"
                        )
                    else:
                        latest_text = f"{t('me3_page.label.latest_version')} {latest_version}"
                        if version_type:
                            latest_text += f" ({version_type})"
                        self.easytier_version_card.latest_version_label.setText(latest_text)
                except Exception as e:
                    print(f"更新Easytier版本信息卡片失败: {e}")

            # 更新OnlineFix工具包区域
            if hasattr(self, 'onlinefix_section'):
                self.onlinefix_section.setTitle(t("me3_page.onlinefix_section.title"))

            # 更新OnlineFix按钮文本
            if hasattr(self, 'onlinefix_download_btn'):
                # 根据当前状态更新按钮文本
                if self.onlinefix_download_btn.isEnabled():
                    self.onlinefix_download_btn.setText(t("me3_page.onlinefix_section.button.download"))
                else:
                    self.onlinefix_download_btn.setText(t("me3_page.onlinefix_section.button.downloading"))
            if hasattr(self, 'onlinefix_check_btn'):
                self.onlinefix_check_btn.setText(t("me3_page.onlinefix_section.button.check_status"))

            # 更新OnlineFix状态标签和详细信息标签
            if hasattr(self, 'onlinefix_status_label') and hasattr(self, 'onlinefix_detail_label'):
                try:
                    # 获取当前状态文本
                    current_status = self.onlinefix_status_label.text()
                    current_detail = self.onlinefix_detail_label.text()

                    # 根据当前状态更新文本
                    if "检查中" in current_status or "Checking" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.checking"))
                    elif "工具包完整" in current_status or "Complete" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.complete"))
                    elif "工具包缺失" in current_status or "Missing" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.missing"))
                    elif "下载完成" in current_status or "Downloaded" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.download_complete"))
                    elif "下载失败" in current_status or "Failed" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.download_failed"))
                    elif "正在下载" in current_status or "Downloading" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.downloading"))
                    elif "下载启动失败" in current_status or "Start failed" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.start_failed"))
                    elif "检查失败" in current_status or "Check failed" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.check_failed"))
                    elif "状态检查失败" in current_status or "Status check failed" in current_status:
                        self.onlinefix_status_label.setText(t("me3_page.onlinefix_section.status.status_check_failed"))

                    # 更新详细信息标签
                    if "包含" in current_detail or "Includes" in current_detail:
                        self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.includes"))
                    elif "所有必需文件已就绪" in current_detail or "All files ready" in current_detail:
                        self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.ready"))
                    elif "需要下载" in current_detail or "Need to download" in current_detail:
                        self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.need_download"))
                    elif "已安装完成" in current_detail or "installed" in current_detail:
                        self.onlinefix_detail_label.setText(t("me3_page.onlinefix_section.detail.installed"))
                    elif "错误" in current_detail or "Error" in current_detail:
                        # 保留错误消息
                        pass
                except Exception as e:
                    print(f"更新OnlineFix状态标签失败: {e}")
        except Exception as e:
            print(f"语言切换回调失败: {e}")


# 为了向后兼容，保留原来的类名作为别名
ME3Page = ToolDownloadPage
