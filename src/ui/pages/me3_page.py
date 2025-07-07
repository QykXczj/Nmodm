"""
ME3工具页面
ME3工具下载和版本管理
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QFrame, QGroupBox,
                               QTextEdit, QComboBox)
from PySide6.QtCore import Qt, Signal
from .base_page import BasePage
from ...utils.download_manager import DownloadManager


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


class ME3Page(BasePage):
    """ME3工具页面"""
    
    # 状态更新信号
    status_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__("ME3工具管理", parent)
        self.download_manager = DownloadManager()
        self.download_worker = None
        self.setup_content()
        self.check_current_status()
    
    def setup_content(self):
        """设置页面内容"""
        # 页面描述
        desc_label = QLabel("ME3工具是用于游戏模组管理的重要工具，支持从GitHub自动下载最新版本。")
        desc_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 14px;
                margin-bottom: 20px;
            }
        """)
        desc_label.setWordWrap(True)
        self.add_content(desc_label)
        
        # 版本信息区域
        self.create_version_section()
        
        # 下载区域
        self.create_download_section()
        
        # 镜像信息
        self.create_mirror_info()
        
        self.add_stretch()
    
    def create_version_section(self):
        """创建版本信息区域"""
        section = QGroupBox("版本信息")
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
        self.version_card = VersionInfoCard()
        layout.addWidget(self.version_card)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def create_download_section(self):
        """创建下载区域"""
        section = QGroupBox("下载管理")
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
        
        # 下载按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        # 下载/更新按钮
        self.download_btn = QPushButton("下载ME3工具")
        self.download_btn.setFixedHeight(40)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 8px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
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
        self.download_btn.clicked.connect(self.start_download)
        
        # 检查更新按钮
        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setFixedHeight(40)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 8px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
        """)
        self.check_update_btn.clicked.connect(self.check_for_updates)
        
        # 取消下载按钮
        self.cancel_btn = QPushButton("取消下载")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 8px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #d67a8a;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setVisible(False)

        # 镜像选择下拉框
        self.mirror_combo = QComboBox()
        self.mirror_combo.setFixedHeight(40)
        self.mirror_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
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
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cdd6f4;
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

        # 提示信息
        self.mirror_tip_label = QLabel("💡 更多镜像: https://yishijie.gitlab.io/ziyuan/")
        self.mirror_tip_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 12px;
                margin-left: 10px;
            }
        """)

        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.check_update_btn)
        button_layout.addWidget(self.mirror_combo)
        button_layout.addWidget(self.mirror_tip_label)
        button_layout.addStretch()
        
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.download_status_label = QLabel()
        self.download_status_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 12px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.download_status_label)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def create_mirror_info(self):
        """创建镜像信息区域"""
        section = QGroupBox("下载镜像")
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
        layout.setSpacing(10)
        
        # 镜像说明
        info_label = QLabel("为了解决网络访问问题，系统会自动尝试以下镜像地址：")
        info_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 13px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(info_label)
        
        # 镜像列表
        mirrors_text = QTextEdit()
        mirrors_text.setFixedHeight(100)
        mirrors_text.setReadOnly(True)
        mirrors_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #bac2de;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                padding: 8px;
            }
        """)
        
        mirror_list = "\n".join([
            "1. gh-proxy.com (GitHub代理)",
            "2. ghproxy.net (GitHub镜像)",
            "3. ghfast.top (GitHub加速)",
            "4. 直连GitHub (备用)"
        ])
        mirrors_text.setText(mirror_list)
        layout.addWidget(mirrors_text)
        
        section.setLayout(layout)
        self.add_content(section)

        # 加载镜像列表到下拉框
        self.load_mirrors()



    def check_current_status(self):
        """检查当前状态"""
        # 检查是否已安装
        is_installed = self.download_manager.is_me3_installed()
        current_version = self.download_manager.get_current_version()
        
        if is_installed:
            self.version_card.update_info(
                current_version=current_version,
                status="已安装"
            )
            self.download_btn.setText("重新下载")
        else:
            self.version_card.update_info(
                current_version=None,
                status="未安装"
            )
            self.download_btn.setText("下载ME3工具")
        
        # 异步检查最新版本
        self.check_for_updates()
    
    def check_for_updates(self):
        """检查更新"""
        self.download_status_label.setText("正在检查最新版本...")
        
        try:
            release_info = self.download_manager.get_latest_release_info()
            if release_info:
                latest_version = release_info.get('tag_name', '未知')
                self.version_card.update_info(latest_version=latest_version)
                
                # 检查是否需要更新
                current_version = self.download_manager.get_current_version()
                if current_version and current_version != latest_version:
                    self.download_btn.setText("更新ME3工具")
                    self.download_status_label.setText(f"发现新版本: {latest_version}")
                elif current_version:
                    self.download_status_label.setText("已是最新版本")
                else:
                    self.download_status_label.setText("可以下载最新版本")
            else:
                self.version_card.update_info(latest_version="获取失败")
                self.download_status_label.setText("无法获取版本信息，请检查网络连接")
        except Exception as e:
            self.download_status_label.setText(f"检查更新失败: {str(e)}")
    
    def start_download(self):
        """开始下载"""
        if self.download_worker and self.download_worker.isRunning():
            self.download_status_label.setText("下载正在进行中，请稍候")
            return

        self.download_worker = self.download_manager.download_me3()
        if not self.download_worker:
            self.download_status_label.setText("无法创建下载任务，请检查网络连接")
            return

        # 连接信号
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.finished.connect(self.download_finished)

        # 更新UI状态
        self.download_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.check_update_btn.setEnabled(False)
        self.mirror_combo.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_status_label.setText("正在下载...")

        # 开始下载
        self.download_worker.start()

    def cancel_download(self):
        """取消下载"""
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.download_status_label.setText("下载已取消")
            self.reset_download_ui()

    def reset_download_ui(self):
        """重置下载UI状态"""
        self.download_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.check_update_btn.setEnabled(True)
        self.mirror_combo.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    def update_progress(self, value):
        """更新下载进度"""
        self.progress_bar.setValue(value)
        self.download_status_label.setText(f"下载进度: {value}%")
    
    def download_finished(self, success, message):
        """下载完成"""
        self.reset_download_ui()

        if success:
            self.download_status_label.setText("ME3工具下载并安装成功")
            # 设置成功状态样式
            self.download_status_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 14px;
                    padding: 5px;
                    background-color: #1e1e2e;
                    border-radius: 4px;
                    border: 1px solid #a6e3a1;
                }
            """)
            # 延迟检查状态，避免覆盖成功消息
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self.check_current_status)
            self.status_updated.emit()  # 发送状态更新信号
        else:
            self.download_status_label.setText(f"下载失败: {message}")
            # 设置错误状态样式
            self.download_status_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 14px;
                    padding: 5px;
                    background-color: #313244;
                    border-radius: 4px;
                    border: 1px solid #f38ba8;
                }
            """)

    def load_mirrors(self):
        """加载镜像列表到下拉框"""
        if hasattr(self, 'mirror_combo'):
            self.mirror_combo.clear()
            mirrors = self.download_manager.get_mirrors()
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

                self.mirror_combo.addItem(display_name, mirror)

            # 设置当前选中的镜像（第一个）
            if mirrors:
                self.mirror_combo.setCurrentIndex(0)
    

