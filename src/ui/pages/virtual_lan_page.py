"""
虚拟局域网页面
基于EasyTier的P2P虚拟局域网功能
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTextEdit, QGroupBox,
                               QSplitter, QFrame, QGridLayout, QComboBox,
                               QCheckBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar, QTabWidget, QListWidget,
                               QListWidgetItem, QMenu, QAbstractItemView, QRadioButton)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QTextOption, QAction
import subprocess
import time
import re
import json
import base64
import os
import sys
import random
from pathlib import Path

from .base_page import BasePage
from ...utils.download_manager import DownloadManager
from ...utils.easytier_manager import EasyTierManager


class PingWorker(QThread):
    """延迟检测工作线程"""
    ping_result = Signal(int, int)  # index, ping_ms

    def __init__(self, index: int, host: str):
        super().__init__()
        self.index = index
        self.host = host

    def run(self):
        """执行ping检测"""
        try:
            # 从URL中提取主机名
            host = self.host.replace("tcp://", "").replace("udp://", "").split(":")[0]

            # 执行ping命令，隐藏终端窗口
            result = subprocess.run(
                ["ping", "-n", "3", host],  # Windows ping命令
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏终端窗口
            )

            if result.returncode == 0:
                # 解析ping结果
                output = result.stdout
                # 查找平均延迟
                match = re.search(r'平均 = (\d+)ms', output)
                if not match:
                    # 英文版本
                    match = re.search(r'Average = (\d+)ms', output)

                if match:
                    ping_ms = int(match.group(1))
                    self.ping_result.emit(self.index, ping_ms)
                else:
                    self.ping_result.emit(self.index, -1)  # 解析失败
            else:
                self.ping_result.emit(self.index, -1)  # ping失败

        except Exception as e:
            print(f"Ping检测异常: {e}")
            self.ping_result.emit(self.index, -1)


class VirtualLanPage(BasePage):
    """虚拟局域网页面"""
    
    def __init__(self, parent=None):
        super().__init__("🌐 虚拟局域网", parent)

        # 管理器
        self.download_manager = DownloadManager()
        self.easytier_manager = EasyTierManager()

        # 连接信号
        self.easytier_manager.network_status_changed.connect(self.on_network_status_changed)
        self.easytier_manager.peer_list_updated.connect(self.on_peer_list_updated)
        self.easytier_manager.connection_info_updated.connect(self.on_connection_info_updated)
        self.easytier_manager.error_occurred.connect(self.on_error_occurred)

        self.setup_content()
        self.check_installation_status()

        # 延迟检查当前房间状态，确保界面完全初始化后执行
        QTimer.singleShot(100, self.check_current_room_status)
    
    def setup_content(self):
        """设置页面内容"""
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：配置和控制区域
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)

        # 右侧：状态和日志区域
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([400, 500])

        # 添加到BasePage的布局中
        self.add_content(splitter)

    def create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # EasyTier安装状态
        self.installation_group = self.create_installation_group()
        layout.addWidget(self.installation_group)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget {
                background-color: transparent;
                border: none;
            }
            QTabWidget::pane {
                border: 2px solid #313244;
                border-radius: 8px;
                background-color: #1e1e2e;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #45475a;
            }
        """)

        # 创建"房间配置"选项卡
        room_tab = QWidget()
        room_layout = QVBoxLayout(room_tab)
        room_layout.setContentsMargins(10, 15, 10, 10)
        room_layout.setSpacing(15)

        # 房间配置
        self.room_group = self.create_room_group()
        room_layout.addWidget(self.room_group)
        room_layout.addStretch()

        # 创建"房间列表"选项卡
        room_list_tab = QWidget()
        room_list_layout = QVBoxLayout(room_list_tab)
        room_list_layout.setContentsMargins(10, 15, 10, 10)
        room_list_layout.setSpacing(15)

        # 房间列表
        self.room_list_group = self.create_room_list_group()
        room_list_layout.addWidget(self.room_list_group)
        # 减少拉伸空间，让列表占用更多空间

        # 创建"房间信息"选项卡
        create_tab = QWidget()
        create_layout = QVBoxLayout(create_tab)
        create_layout.setContentsMargins(10, 15, 10, 10)
        create_layout.setSpacing(15)

        # 网络配置
        self.network_config_group = self.create_network_config_group()
        create_layout.addWidget(self.network_config_group)

        # 创建房间按钮区域
        self.create_room_section = self.create_room_section()
        create_layout.addWidget(self.create_room_section)

        create_layout.addStretch()

        # 创建"高级设置"选项卡
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(10, 15, 10, 10)
        advanced_layout.setSpacing(15)

        # 高级设置
        self.advanced_group = self.create_advanced_group()
        advanced_layout.addWidget(self.advanced_group)
        advanced_layout.addStretch()

        # 创建"公益服务器"选项卡
        servers_tab = QWidget()
        servers_layout = QVBoxLayout(servers_tab)
        servers_layout.setContentsMargins(10, 15, 10, 10)
        servers_layout.setSpacing(15)

        # 公益服务器列表
        self.servers_group = self.create_servers_group()
        servers_layout.addWidget(self.servers_group)
        servers_layout.addStretch()

        # 添加选项卡
        self.tab_widget.addTab(room_list_tab, "房间列表")
        self.tab_widget.addTab(room_tab, "添加房间")
        self.tab_widget.addTab(create_tab, "房间信息")
        self.tab_widget.addTab(advanced_tab, "高级设置")
        self.tab_widget.addTab(servers_tab, "公益服务器")

        # 添加选项卡控件到主布局
        layout.addWidget(self.tab_widget)

        # 网络控制独立在选项卡外部
        self.control_group = self.create_control_group()
        layout.addWidget(self.control_group)

        layout.addStretch()
        return widget
    
    def create_installation_group(self) -> QGroupBox:
        """创建安装状态组"""
        group = QGroupBox("EasyTier 安装状态")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
        layout = QVBoxLayout(group)

        # 状态和版本信息水平布局
        info_layout = QHBoxLayout()

        # 状态显示
        status_container = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        status_title = QLabel("状态:")
        status_title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.status_label = QLabel("检查中...")
        self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")

        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_container.setLayout(status_layout)

        # 版本信息
        version_container = QWidget()
        version_layout = QHBoxLayout()
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(8)

        version_title = QLabel("版本:")
        version_title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.version_label = QLabel("未知")
        self.version_label.setStyleSheet("color: #bac2de;")

        version_layout.addWidget(version_title)
        version_layout.addWidget(self.version_label)
        version_layout.addStretch()
        version_container.setLayout(version_layout)

        # 添加到水平布局
        info_layout.addWidget(status_container)
        info_layout.addWidget(version_container)
        layout.addLayout(info_layout)
        

        
        return group
    
    def create_network_config_group(self) -> QGroupBox:
        """创建网络配置组"""
        group = QGroupBox("网络配置")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
            }
            QLineEdit {
                background-color: #1e1e2e;
                border: 2px solid #313244;
                border-radius: 4px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QComboBox {
                background-color: #1e1e2e;
                border: 2px solid #313244;
                border-radius: 4px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cdd6f4;
            }
        """)
        layout = QGridLayout(group)
        
        # 房间名称
        layout.addWidget(QLabel("房间名称:"), 0, 0)
        self.network_name_edit = QLineEdit()
        self.network_name_edit.setPlaceholderText("输入房间名称")
        layout.addWidget(self.network_name_edit, 0, 1)

        # 玩家名称
        layout.addWidget(QLabel("玩家名称:"), 1, 0)

        # 玩家名称容器
        player_name_container = QWidget()
        player_name_layout = QHBoxLayout()
        player_name_layout.setContentsMargins(0, 0, 0, 0)
        player_name_layout.setSpacing(8)

        self.machine_id_edit = QLineEdit()
        self.machine_id_edit.setPlaceholderText("输入玩家名称（同一房间内不可重复）")
        player_name_layout.addWidget(self.machine_id_edit)

        # 随机生成按钮
        self.random_name_btn = QPushButton("🎲")
        self.random_name_btn.setFixedSize(32, 32)
        self.random_name_btn.setToolTip("随机生成玩家名称")
        self.random_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.random_name_btn.clicked.connect(self.generate_random_name)
        player_name_layout.addWidget(self.random_name_btn)

        player_name_container.setLayout(player_name_layout)
        layout.addWidget(player_name_container, 1, 1)

        # 玩家名称提醒（跨列显示）
        player_name_hint = QLabel("💡 提醒：同一房间内玩家名称不可重复")
        player_name_hint.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(249, 226, 175, 0.1);
                border: 1px solid rgba(249, 226, 175, 0.3);
                border-radius: 4px;
                margin-top: 2px;
                margin-left: 0px;
            }
        """)
        layout.addWidget(player_name_hint, 2, 1)  # 放在第2行第1列，跨列显示

        # 房间密码
        layout.addWidget(QLabel("房间密码:"), 3, 0)

        # 房间密码容器
        password_container = QWidget()
        password_layout = QHBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(8)

        self.network_secret_edit = QLineEdit()
        self.network_secret_edit.setPlaceholderText("输入房间密码")
        self.network_secret_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.network_secret_edit)

        # 密码可见性切换按钮
        self.password_visibility_btn = QPushButton("👁")
        self.password_visibility_btn.setFixedSize(32, 32)
        self.password_visibility_btn.setToolTip("显示/隐藏密码")
        self.password_visibility_btn.setCheckable(True)
        self.password_visibility_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                border: none;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton:checked:hover {
                background-color: #74c7ec;
            }
        """)
        self.password_visibility_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.password_visibility_btn)

        password_container.setLayout(password_layout)
        layout.addWidget(password_container, 3, 1)

        # 本机IP配置
        layout.addWidget(QLabel("本机IP:"), 4, 0)

        ip_container = QWidget()
        ip_layout = QHBoxLayout()
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.setSpacing(10)

        # DHCP复选框
        self.dhcp_check = QCheckBox("自动分配(DHCP)")
        self.dhcp_check.setChecked(True)  # 默认启用DHCP
        self.dhcp_check.setStyleSheet("""
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #45475a;
                background-color: #1e1e2e;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
        """)
        self.dhcp_check.stateChanged.connect(self.on_dhcp_changed)
        ip_layout.addWidget(self.dhcp_check)

        # 手动IP输入框
        self.peer_ip_edit = QLineEdit("10.126.126.1")
        self.peer_ip_edit.setPlaceholderText("将自动分配IP地址")
        self.peer_ip_edit.setEnabled(False)  # 默认禁用，因为DHCP已启用
        self.peer_ip_edit.setMaximumWidth(150)
        ip_layout.addWidget(self.peer_ip_edit)

        ip_layout.addStretch()  # 添加弹性空间
        ip_container.setLayout(ip_layout)
        layout.addWidget(ip_container, 4, 1)

        # 公共服务器（固定值）
        layout.addWidget(QLabel("公共服务器:"), 5, 0)
        self.external_node_label = QLabel("tcp://public.easytier.top:11010")
        self.external_node_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 6px 8px;
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.external_node_label, 5, 1)
        
        return group

    def create_room_list_group(self) -> QGroupBox:
        """创建房间列表组"""
        group = QGroupBox("房间列表")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 房间列表控件
        self.room_list_widget = QListWidget()
        self.room_list_widget.setMinimumHeight(200)  # 设置最小高度
        self.room_list_widget.setMaximumHeight(300)  # 设置最大高度
        self.room_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 2px;
                margin: 6px 2px;
                background-color: transparent;
                border: none;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
        """)

        # 禁用默认选择，使用自定义单选按钮
        self.room_list_widget.setSelectionMode(QAbstractItemView.NoSelection)

        # 启用右键菜单
        self.room_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.room_list_widget.customContextMenuRequested.connect(self.show_room_context_menu)

        layout.addWidget(self.room_list_widget)

        # 刷新按钮
        refresh_layout = QHBoxLayout()
        self.refresh_room_list_btn = QPushButton("🔄 刷新列表")
        self.refresh_room_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        self.refresh_room_list_btn.clicked.connect(self.refresh_room_list_widget)
        refresh_layout.addWidget(self.refresh_room_list_btn)

        # 提示信息
        hint_label = QLabel("💡 右键房间可进行加载、分享和删除操作")
        hint_label.setStyleSheet("""
            QLabel {
                color: #74c7ec;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(116, 199, 236, 0.1);
                border: 1px solid rgba(116, 199, 236, 0.3);
                border-radius: 4px;
                margin-left: 8px;
                max-height: 24px;
            }
        """)
        refresh_layout.addWidget(hint_label)
        refresh_layout.addStretch()

        layout.addLayout(refresh_layout)

        # 初始化房间列表
        self.refresh_room_list_widget()

        return group

    def create_room_section(self) -> QGroupBox:
        """创建房间按钮区域"""
        group = QGroupBox("创建房间")
        group.setStyleSheet("""
            QGroupBox {
                color: #a6e3a1;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: rgba(166, 227, 161, 0.05);
                max-height: 80px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #a6e3a1;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 8)

        # 创建房间按钮和提示
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 创建房间按钮
        self.create_room_btn = QPushButton("🏠 创建房间")
        self.create_room_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7fb069;
            }
        """)
        self.create_room_btn.clicked.connect(self.create_room)
        button_layout.addWidget(self.create_room_btn)

        # 小白提示
        hint_label = QLabel("💡 小白用户：高级设置和公益服务器保持默认就行！")
        hint_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(249, 226, 175, 0.1);
                border: 1px solid rgba(249, 226, 175, 0.3);
                border-radius: 4px;
                margin-left: 8px;
                max-height: 24px;
            }
        """)
        button_layout.addWidget(hint_label)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        return group

    def create_room_group(self) -> QGroupBox:
        """创建添加房间组"""
        group = QGroupBox("添加房间")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(15)



        # 房间代码输入区域
        join_group = QGroupBox("通过房间代码添加")
        join_group.setStyleSheet("""
            QGroupBox {
                color: #89b4fa;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: rgba(137, 180, 250, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #89b4fa;
            }
        """)
        join_layout = QVBoxLayout(join_group)
        join_layout.setSpacing(10)

        # 房间代码输入
        room_code_label = QLabel("房间代码:")
        room_code_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 13px;")
        join_layout.addWidget(room_code_label)
        self.room_code_edit = QLineEdit()
        self.room_code_edit.setPlaceholderText("粘贴房间代码 (ESR://...)")
        self.room_code_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        join_layout.addWidget(self.room_code_edit)

        # 玩家名称输入
        player_name_label = QLabel("玩家名称:")
        player_name_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 13px;")
        join_layout.addWidget(player_name_label)

        # 玩家名称输入行（包含输入框和随机生成按钮）
        player_name_layout = QHBoxLayout()
        self.join_player_name_edit = QLineEdit()
        self.join_player_name_edit.setPlaceholderText("输入您的玩家名称")
        self.join_player_name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        player_name_layout.addWidget(self.join_player_name_edit)

        # 随机生成按钮
        random_name_btn = QPushButton("🎲")
        random_name_btn.setToolTip("随机生成玩家名称")
        random_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        random_name_btn.clicked.connect(lambda: self.join_player_name_edit.setText(self.generate_random_player_name()))
        player_name_layout.addWidget(random_name_btn)

        join_layout.addLayout(player_name_layout)

        # 加入按钮
        join_btn_layout = QHBoxLayout()
        self.join_room_btn = QPushButton("🚪 添加房间")
        self.join_room_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.join_room_btn.clicked.connect(self.join_room)
        join_btn_layout.addWidget(self.join_room_btn)

        join_hint = QLabel("解析房间代码并加入")
        join_hint.setStyleSheet("color: #bac2de; font-size: 11px;")
        join_btn_layout.addWidget(join_hint)
        join_btn_layout.addStretch()

        join_layout.addLayout(join_btn_layout)
        layout.addWidget(join_group)



        return group

    def create_servers_group(self) -> QGroupBox:
        """创建公益服务器组"""
        group = QGroupBox("公益服务器列表")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 公益服务器列表定义（默认全部未选中）
        self.server_list = [
            {"url": "tcp://gz.minebg.top:11010", "name": "广州", "enabled": False},
            {"url": "tcp://119.23.65.180:11010", "name": "深圳", "enabled": False},
            {"url": "tcp://ah.nkbpal.cn:11010", "name": "合肥", "enabled": False},
            {"url": "tcp://turn.sc.629957.xyz:11010", "name": "成都", "enabled": False},
            {"url": "tcp://8.148.29.206:11010", "name": "武汉", "enabled": False},
            {"url": "tcp://turn.js.629957.xyz:11012", "name": "宿迁", "enabled": False},
            {"url": "tcp://sh.993555.xyz:11010", "name": "上海", "enabled": False},
            {"url": "tcp://et-hk.clickor.click:11010", "name": "香港", "enabled": False},
        ]

        # 创建服务器选择控件
        self.server_checkboxes = []
        self.server_ping_labels = []

        for i, server in enumerate(self.server_list):
            # 服务器行容器
            server_row = QWidget()
            server_layout = QHBoxLayout()
            server_layout.setContentsMargins(0, 0, 0, 0)
            server_layout.setSpacing(12)

            # 复选框
            checkbox = QCheckBox(f"{server['name']} ({server['url']})")
            checkbox.setChecked(server['enabled'])
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #cdd6f4;
                    font-size: 12px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 2px solid #6c7086;
                    background-color: #313244;
                }
                QCheckBox::indicator:checked {
                    background-color: #89b4fa;
                    border-color: #89b4fa;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0iIzFlMWUyZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                }
                QCheckBox::indicator:hover {
                    border-color: #89b4fa;
                }
            """)
            checkbox.toggled.connect(lambda checked, idx=i: self.on_server_toggled(idx, checked))
            self.server_checkboxes.append(checkbox)
            server_layout.addWidget(checkbox)

            # 延迟显示标签
            ping_label = QLabel("检测中...")
            ping_label.setStyleSheet("""
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 2px 6px;
                    background-color: rgba(249, 226, 175, 0.1);
                    border: 1px solid rgba(249, 226, 175, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }
            """)
            ping_label.setAlignment(Qt.AlignCenter)
            self.server_ping_labels.append(ping_label)
            server_layout.addWidget(ping_label)

            server_layout.addStretch()
            server_row.setLayout(server_layout)
            layout.addWidget(server_row)

        # 添加说明
        hint_label = QLabel("💡 提醒：始终使用公共服务器，勾选公益服务器可提高连接成功率，建议选择延迟较低的服务器")
        hint_label.setStyleSheet("""
            QLabel {
                color: #74c7ec;
                font-size: 11px;
                font-style: italic;
                padding: 6px 8px;
                background-color: rgba(116, 199, 236, 0.1);
                border: 1px solid rgba(116, 199, 236, 0.3);
                border-radius: 4px;
                margin-top: 8px;
            }
        """)
        layout.addWidget(hint_label)

        # 启动延迟检测
        self.start_ping_detection()

        return group

    def on_server_toggled(self, index: int, checked: bool):
        """服务器选择状态变化"""
        self.server_list[index]['enabled'] = checked
        # 保存配置
        self.save_config()

    def start_ping_detection(self):
        """启动延迟检测"""
        self.ping_workers = []

        for i, server in enumerate(self.server_list):
            # 创建ping检测工作线程
            worker = PingWorker(i, server['url'])
            worker.ping_result.connect(self.on_ping_result)
            self.ping_workers.append(worker)
            worker.start()

    def on_ping_result(self, index: int, ping_ms: int):
        """处理ping检测结果"""
        if index >= len(self.server_ping_labels):
            return

        ping_label = self.server_ping_labels[index]

        if ping_ms == -1:
            # ping失败
            ping_label.setText("超时")
            ping_label.setStyleSheet("""
                QLabel {
                    color: #6c7086;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba(108, 112, 134, 0.1);
                    border: 1px solid rgba(108, 112, 134, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }
            """)
            ping_label.setToolTip("连接超时或服务器不可达")
        else:
            # 根据延迟设置颜色和状态
            if ping_ms < 50:
                color = "#a6e3a1"  # 绿色 - 优秀
                status = "优秀"
            elif ping_ms < 100:
                color = "#f9e2af"  # 黄色 - 良好
                status = "良好"
            elif ping_ms < 150:
                color = "#fab387"  # 橙色 - 一般
                status = "一般"
            else:
                color = "#f38ba8"  # 红色 - 较差
                status = "较差"

            ping_label.setText(f"{ping_ms}ms")
            ping_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
                    border: 1px solid rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }}
            """)
            ping_label.setToolTip(f"延迟: {ping_ms}ms ({status})")

    def check_current_room_status(self):
        """检查并提醒当前房间状态"""
        try:
            # 获取当前配置
            current_config = self.easytier_manager.get_config()
            current_room_name = current_config.get("network_name", "").strip()
            current_hostname = current_config.get("hostname", "").strip()

            if current_room_name:
                # 检查是否存在对应的房间配置文件
                rooms_dir = self.get_rooms_dir()
                room_file = rooms_dir / f"{current_room_name}.json"

                if room_file.exists():
                    # 房间配置文件存在
                    if current_hostname:
                        self.log_message(f"当前已加载房间 '{current_room_name}'，玩家名称: {current_hostname}", "info")
                    else:
                        self.log_message(f"当前已加载房间 '{current_room_name}'，但玩家名称为空", "warning")
                else:
                    # 房间配置文件不存在，可能是手动配置的
                    if current_hostname:
                        self.log_message(f"当前配置房间 '{current_room_name}'，玩家名称: {current_hostname} (未保存为房间)", "info")
                    else:
                        self.log_message(f"当前配置房间 '{current_room_name}'，但玩家名称为空", "warning")
            else:
                # 没有配置房间名称
                self.log_message("当前未配置房间，请先创建或加载房间", "warning")

        except Exception as e:
            print(f"检查房间状态失败: {e}")

    def generate_random_player_name(self) -> str:
        """生成随机玩家名称"""
        adjectives = [
            "勇敢的", "聪明的", "快乐的", "神秘的", "强大的", "优雅的", "敏捷的", "智慧的",
            "幸运的", "冷静的", "热情的", "友善的", "机智的", "坚强的", "温柔的", "活泼的"
        ]

        nouns = [
            "哈基追", "哈基法", "哈基蜗", "哈基弓", "无赖大人", "女爵", "神鹰哥", "尬弹哥", "铁眼大人"
        ]

        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        number = random.randint(100, 999)

        return f"{adjective}{noun}{number}"

    def log_message(self, message: str, msg_type: str = "info"):
        """在运行日志中显示消息"""
        if hasattr(self, 'log_text'):
            timestamp = time.strftime("%H:%M:%S")

            if msg_type == "error":
                color = "#f38ba8"  # 红色
                prefix = "❌"
            elif msg_type == "warning":
                color = "#f9e2af"  # 黄色
                prefix = "⚠️"
            elif msg_type == "success":
                color = "#a6e3a1"  # 绿色
                prefix = "✅"
            else:
                color = "#cdd6f4"  # 默认颜色
                prefix = "ℹ️"

            log_entry = f'<span style="color: {color};">[{timestamp}] {prefix} {message}</span>'
            self.log_text.append(log_entry)

    def refresh_room_list_widget(self):
        """刷新房间列表控件"""
        self.room_list_widget.clear()
        self.room_radio_buttons = {}  # 存储房间名到单选按钮的映射
        rooms_dir = self.get_rooms_dir()

        # 获取当前加载的房间
        current_config = self.easytier_manager.get_config()
        current_room_name = current_config.get("network_name", "")

        if rooms_dir.exists():
            for room_file in rooms_dir.glob("*.json"):
                try:
                    with open(room_file, 'r', encoding='utf-8') as f:
                        room_config = json.load(f)

                    room_name = room_config.get("network_name", room_file.stem)

                    # 获取玩家名称（优先使用hostname，然后从元数据获取）
                    player_name = room_config.get("hostname", "未知玩家")
                    if not player_name or player_name == "未知玩家":
                        # 兼容旧格式：从元数据或旧字段获取
                        room_meta = room_config.get("_room_meta", {})
                        player_name = (room_meta.get("created_by") or
                                     room_meta.get("joined_by") or
                                     room_config.get("created_by") or
                                     room_config.get("joined_by") or
                                     "未知玩家")

                    # 创建容器widget作为真正的边框容器
                    container_widget = QWidget()
                    container_widget.setMinimumHeight(32)  # 减小高度：44 → 32
                    container_widget.setStyleSheet("""
                        QWidget {
                            background-color: transparent;
                            border: 1px solid rgba(69, 71, 90, 0.5);
                            border-radius: 6px;
                        }
                        QWidget:hover {
                            background-color: rgba(137, 180, 250, 0.1);
                            border-color: rgba(137, 180, 250, 0.4);
                        }
                    """)

                    # 在容器内创建布局
                    container_layout = QHBoxLayout(container_widget)
                    container_layout.setContentsMargins(8, 4, 8, 4)  # 减小内边距：12,8,12,8 → 8,4,8,4
                    container_layout.setSpacing(10)  # 减小间距：15 → 10
                    container_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐

                    # 单选框（禁用点击功能）
                    radio_button = QRadioButton()
                    radio_button.setEnabled(False)  # 禁用交互
                    radio_button.setStyleSheet("""
                        QRadioButton {
                            background-color: transparent;
                            spacing: 0px;
                        }
                        QRadioButton::indicator {
                            width: 18px;
                            height: 18px;
                            border-radius: 9px;
                            border: 2px solid #6c7086;
                            background-color: #1e1e2e;
                            margin: 2px;
                        }
                        QRadioButton::indicator:checked {
                            background-color: #89b4fa;
                            border-color: #89b4fa;
                        }
                        QRadioButton::indicator:disabled {
                            border-color: #6c7086;
                            background-color: #1e1e2e;
                        }
                        QRadioButton::indicator:checked:disabled {
                            background-color: #89b4fa;
                            border-color: #89b4fa;
                        }
                    """)

                    # 检查是否为当前加载的房间（需要临时启用才能设置状态）
                    if room_name == current_room_name:
                        radio_button.setEnabled(True)  # 临时启用
                        radio_button.setChecked(True)
                        radio_button.setEnabled(False)  # 重新禁用

                    # 不连接点击事件，因为单选框已被禁用
                    self.room_radio_buttons[room_name] = radio_button  # 使用房间名作为键
                    container_layout.addWidget(radio_button)

                    # 房间名称
                    room_label = QLabel(room_name)
                    room_label.setStyleSheet("""
                        QLabel {
                            color: #cdd6f4;
                            font-weight: bold;
                            font-size: 13px;
                            background-color: transparent;
                            padding: 2px 4px;
                        }
                    """)
                    room_label.setMinimumWidth(120)
                    container_layout.addWidget(room_label)

                    # 玩家名称
                    player_label = QLabel(player_name)
                    player_label.setStyleSheet("""
                        QLabel {
                            color: #bac2de;
                            font-size: 12px;
                            background-color: transparent;
                            padding: 2px 4px;
                        }
                    """)
                    container_layout.addWidget(player_label)

                    container_layout.addStretch()

                    # 创建列表项
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, room_file.stem)  # 存储房间名用于操作
                    item.setSizeHint(container_widget.sizeHint())

                    self.room_list_widget.addItem(item)
                    self.room_list_widget.setItemWidget(item, container_widget)

                except Exception as e:
                    print(f"读取房间配置失败 {room_file}: {e}")



    def show_room_context_menu(self, position):
        """显示房间右键菜单"""
        item = self.room_list_widget.itemAt(position)
        if item is None:
            return

        room_name = item.data(Qt.UserRole)
        if not room_name:
            return

        # 创建右键菜单
        menu = QMenu(self.room_list_widget)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 4px;
                margin: 1px;
            }
            QMenu::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)

        # 加载房间动作
        load_action = QAction("📋 加载房间", menu)
        load_action.triggered.connect(lambda: self.load_room_from_list(room_name))
        menu.addAction(load_action)

        menu.addSeparator()  # 分隔线

        # 分享房间动作
        share_action = QAction("📤 分享房间", menu)
        share_action.triggered.connect(lambda: self.share_room_from_list(room_name))
        menu.addAction(share_action)

        # 删除房间动作
        delete_action = QAction("🗑️ 删除房间", menu)
        delete_action.triggered.connect(lambda: self.delete_room_from_list(room_name))
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec(self.room_list_widget.mapToGlobal(position))

    def load_room_from_list(self, room_name: str):
        """从列表加载房间配置"""
        try:
            # 读取房间配置
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if not room_file.exists():
                self.log_message(f"房间配置文件不存在: {room_name}", "error")
                return

            with open(room_file, 'r', encoding='utf-8') as f:
                room_config = json.load(f)

            # 获取玩家名称
            player_name = room_config.get("hostname", "未知玩家")
            if not player_name or player_name == "未知玩家":
                # 兼容旧格式
                room_meta = room_config.get("_room_meta", {})
                player_name = (room_meta.get("created_by") or
                             room_meta.get("joined_by") or
                             room_config.get("created_by") or
                             room_config.get("joined_by") or
                             "未知玩家")

            # 应用房间配置到界面
            self.apply_room_config(room_config, player_name)

            # 选中当前房间的单选按钮（需要临时启用才能设置状态）
            for name, radio_button in self.room_radio_buttons.items():
                radio_button.setEnabled(True)  # 临时启用
                if name == room_name:
                    radio_button.setChecked(True)
                else:
                    radio_button.setChecked(False)
                radio_button.setEnabled(False)  # 重新禁用

            self.log_message(f"已加载房间 '{room_name}' 的配置", "success")

        except Exception as e:
            self.log_message(f"加载房间配置失败: {str(e)}", "error")

    def share_room_from_list(self, room_name: str):
        """从列表分享房间"""
        try:
            # 读取房间配置
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if not room_file.exists():
                self.log_message(f"房间配置文件不存在: {room_name}", "error")
                return

            with open(room_file, 'r', encoding='utf-8') as f:
                room_config = json.load(f)

            # 创建分享配置（不包含hostname和房间元数据）
            share_config = {
                "network_name": room_config["network_name"],
                "network_secret": room_config["network_secret"],
                "peers": room_config.get("peers", ["tcp://public.easytier.top:11010"]),
                "dhcp": room_config.get("dhcp", True),
                "disable_encryption": room_config.get("disable_encryption", False),
                "disable_ipv6": room_config.get("disable_ipv6", False),
                "latency_first": room_config.get("latency_first", True),
                "multi_thread": room_config.get("multi_thread", True)
            }

            # 添加IP配置（如果有）
            if "ipv4" in room_config:
                share_config["ipv4"] = room_config["ipv4"]

            # 编码为base64
            config_json = json.dumps(share_config, ensure_ascii=False)
            config_b64 = base64.b64encode(config_json.encode('utf-8')).decode('ascii')
            share_code = f"ESR://{config_b64}"

            # 复制到剪切板
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(share_code)

            self.log_message(f"房间 '{room_name}' 的分享代码已复制到剪切板", "success")

        except Exception as e:
            self.log_message(f"分享房间失败: {str(e)}", "error")

    def delete_room_from_list(self, room_name: str):
        """从列表删除房间"""
        try:
            # 删除房间配置文件
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if room_file.exists():
                room_file.unlink()
                self.log_message(f"房间 '{room_name}' 已删除", "success")

                # 刷新房间列表
                self.refresh_room_list_widget()
            else:
                self.log_message(f"房间配置文件不存在: {room_name}", "error")

        except Exception as e:
            self.log_message(f"删除房间失败: {str(e)}", "error")

    def get_rooms_dir(self) -> Path:
        """获取房间配置目录"""
        if getattr(sys, 'frozen', False):
            root_dir = Path(sys.executable).parent
        else:
            root_dir = Path(__file__).parent.parent.parent.parent

        rooms_dir = root_dir / "ESR" / "rooms_config"
        rooms_dir.mkdir(parents=True, exist_ok=True)
        return rooms_dir



    def create_room(self):
        """创建房间"""
        try:
            # 获取当前配置
            network_name = self.network_name_edit.text().strip()
            hostname = self.machine_id_edit.text().strip()
            network_secret = self.network_secret_edit.text().strip()

            # 验证必填字段
            if not network_name:
                self.log_message("房间名称不能为空", "error")
                return

            if not hostname:
                self.log_message("玩家名称不能为空", "error")
                return

            if not network_secret:
                self.log_message("房间密码不能为空", "error")
                return

            # 检查房间是否已存在
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"

            if room_file.exists():
                self.log_message(f"房间 '{network_name}' 已存在", "error")
                return

            # 收集当前配置（与easytier_config.json格式统一）
            room_config = {
                "network_name": network_name,
                "hostname": hostname,  # 统一使用hostname字段
                "network_secret": network_secret,
                "dhcp": self.dhcp_check.isChecked(),
                "disable_encryption": not self.encryption_check.isChecked(),
                "disable_ipv6": not self.ipv6_check.isChecked(),
                "latency_first": self.latency_first_check.isChecked(),
                "multi_thread": self.multi_thread_check.isChecked(),
                # 房间元数据
                "_room_meta": {
                    "created_by": hostname,
                    "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            # IP配置
            if not self.dhcp_check.isChecked():
                room_config["ipv4"] = self.peer_ip_edit.text().strip()

            # 完整的peers配置（包含公共服务器和公益服务器）
            peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    if server['enabled']:
                        peers.append(server['url'])

            room_config["peers"] = peers

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(room_config, f, indent=2, ensure_ascii=False)

            # 刷新房间列表
            self.refresh_room_list_widget()  # 刷新房间列表控件

            self.log_message(f"房间 '{network_name}' 创建成功", "success")

        except Exception as e:
            self.log_message(f"创建房间失败: {str(e)}", "error")



    def join_room(self):
        """添加房间"""
        try:
            room_code = self.room_code_edit.text().strip()
            player_name = self.join_player_name_edit.text().strip()

            # 验证输入
            if not room_code:
                self.log_message("请输入房间代码", "error")
                return

            if not player_name:
                self.log_message("请输入玩家名称", "error")
                return

            # 验证房间代码格式
            if not room_code.startswith("ESR://"):
                self.log_message("房间代码格式错误，应以 ESR:// 开头", "error")
                return

            # 解码房间配置
            try:
                config_b64 = room_code[6:]  # 去掉 ESR:// 前缀
                config_json = base64.b64decode(config_b64).decode('utf-8')
                room_config = json.loads(config_json)
            except Exception as e:
                self.log_message(f"房间代码解析失败: {str(e)}", "error")
                return

            # 验证必要字段
            required_fields = ["network_name", "network_secret"]
            for field in required_fields:
                if field not in room_config:
                    self.log_message(f"房间配置缺失字段: {field}", "error")
                    return

            network_name = room_config["network_name"]

            # 检查是否已经加入过该房间
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"

            if room_file.exists():
                self.log_message(f"已经加入过房间 '{network_name}'", "error")
                return

            # 创建完整的房间配置（与easytier_config.json格式统一）
            full_config = {
                "network_name": network_name,
                "hostname": player_name,  # 统一使用hostname字段
                "network_secret": room_config["network_secret"],
                "peers": room_config.get("peers", ["tcp://public.easytier.top:11010"]),
                "dhcp": room_config.get("dhcp", True),
                "disable_encryption": room_config.get("disable_encryption", False),
                "disable_ipv6": room_config.get("disable_ipv6", False),
                "latency_first": room_config.get("latency_first", True),
                "multi_thread": room_config.get("multi_thread", True),
                # 房间元数据
                "_room_meta": {
                    "joined_by": player_name,
                    "joined_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            # 添加IP配置（如果有）
            if "ipv4" in room_config:
                full_config["ipv4"] = room_config["ipv4"]

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(full_config, f, indent=2, ensure_ascii=False)

            # 应用配置到当前界面
            self.apply_room_config(full_config, player_name)

            # 刷新房间列表
            self.refresh_room_list_widget()  # 刷新房间列表控件

            # 清空输入框
            self.room_code_edit.clear()
            self.join_player_name_edit.clear()

            self.log_message(f"成功添加房间 '{network_name}'", "success")

        except Exception as e:
            self.log_message(f"添加房间失败: {str(e)}", "error")

    def apply_room_config(self, room_config: dict, player_name: str):
        """应用房间配置到界面"""
        try:
            # 基本配置
            self.network_name_edit.setText(room_config["network_name"])
            self.machine_id_edit.setText(player_name)
            self.network_secret_edit.setText(room_config["network_secret"])

            # DHCP配置
            dhcp_enabled = room_config.get("dhcp", True)
            self.dhcp_check.setChecked(dhcp_enabled)

            if dhcp_enabled:
                self.peer_ip_edit.setText("")
                self.peer_ip_edit.setEnabled(False)
            else:
                self.peer_ip_edit.setText(room_config.get("ipv4", "10.126.126.1"))
                self.peer_ip_edit.setEnabled(True)

            # 高级设置
            self.encryption_check.setChecked(not room_config.get("disable_encryption", False))
            self.ipv6_check.setChecked(not room_config.get("disable_ipv6", False))
            self.latency_first_check.setChecked(room_config.get("latency_first", True))
            self.multi_thread_check.setChecked(room_config.get("multi_thread", True))

            # 服务器配置（从peers字段解析）
            if hasattr(self, 'server_list'):
                peers = room_config.get("peers", ["tcp://public.easytier.top:11010"])
                # 过滤掉公共服务器，只处理公益服务器
                charity_servers = [peer for peer in peers if peer != "tcp://public.easytier.top:11010"]

                # 重置所有服务器状态
                for server in self.server_list:
                    server['enabled'] = server['url'] in charity_servers

                # 更新复选框状态
                for i, checkbox in enumerate(self.server_checkboxes):
                    checkbox.setChecked(self.server_list[i]['enabled'])

            # 保存配置
            self.save_config()

        except Exception as e:
            print(f"应用房间配置失败: {e}")

    def auto_save_room_config(self, network_name: str):
        """启动网络时自动保存房间配置"""
        try:
            # 获取当前配置
            hostname = self.machine_id_edit.text().strip()
            network_secret = self.network_secret_edit.text().strip()

            # 检查房间是否已存在
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"
            is_existing_room = room_file.exists()

            # 收集当前配置（与创建房间时的格式统一）
            room_config = {
                "network_name": network_name,
                "hostname": hostname,
                "network_secret": network_secret,
                "dhcp": self.dhcp_check.isChecked(),
                "disable_encryption": not self.encryption_check.isChecked(),
                "disable_ipv6": not self.ipv6_check.isChecked(),
                "latency_first": self.latency_first_check.isChecked(),
                "multi_thread": self.multi_thread_check.isChecked(),
            }

            # IP配置
            if not self.dhcp_check.isChecked():
                room_config["ipv4"] = self.peer_ip_edit.text().strip()

            # 完整的peers配置（包含公共服务器和公益服务器）
            peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    if server['enabled']:
                        peers.append(server['url'])
            room_config["peers"] = peers

            # 添加房间元数据
            if is_existing_room:
                # 更新现有房间
                room_config["_room_meta"] = {
                    "updated_by": hostname,
                    "updated_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                # 保留原有的创建信息
                try:
                    with open(room_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                    original_meta = existing_config.get("_room_meta", {})
                    if "created_by" in original_meta:
                        room_config["_room_meta"]["created_by"] = original_meta["created_by"]
                    if "created_time" in original_meta:
                        room_config["_room_meta"]["created_time"] = original_meta["created_time"]
                except:
                    pass
            else:
                # 新建房间
                room_config["_room_meta"] = {
                    "created_by": hostname,
                    "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(room_config, f, indent=2, ensure_ascii=False)

            # 刷新房间列表
            self.refresh_room_list_widget()

            # 根据是否为新房间给出不同提示
            if is_existing_room:
                self.log_message(f"房间 '{network_name}' 配置已更新", "success")
            else:
                self.log_message(f"已自动创建新房间 '{network_name}'", "success")

        except Exception as e:
            self.log_message(f"自动保存房间配置失败: {str(e)}", "error")

    def on_dhcp_changed(self, state):
        """DHCP状态变化处理"""
        is_dhcp_enabled = state == 2  # Qt.Checked = 2

        # 启用DHCP时禁用手动IP输入，反之启用
        self.peer_ip_edit.setEnabled(not is_dhcp_enabled)

        if is_dhcp_enabled:
            # 启用DHCP时，清空IP输入框并显示提示
            self.peer_ip_edit.setText("")
            self.peer_ip_edit.setPlaceholderText("将自动分配IP地址")
        else:
            # 禁用DHCP时，恢复默认IP和提示
            self.peer_ip_edit.setText("10.126.126.1")
            self.peer_ip_edit.setPlaceholderText("10.126.126.x")

    def generate_random_name(self):
        """生成随机玩家名称"""
        import random

        # 形容词列表
        adjectives = [
            "勇敢", "智慧", "神秘", "闪耀", "迅捷", "强大", "优雅", "冷静",
            "热情", "坚定", "灵活", "敏锐", "沉稳", "活力", "幽默", "温和",
            "果断", "机智", "专注", "自由", "创新", "独特", "魅力", "传奇"
        ]

        # 名词列表
        nouns = [
            "哈基追", "哈基法", "哈基蜗", "哈基弓", "无赖大人", "女爵", "神鹰哥", "尬弹哥", "铁眼大人"
        ]

        # 随机选择形容词和名词
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)

        # 添加随机数字后缀
        number = random.randint(100, 999)

        # 生成最终名称
        random_name = f"{adjective}的{noun}{number}"

        # 设置到输入框
        self.machine_id_edit.setText(random_name)

        # 添加一个小动画效果
        self.machine_id_edit.selectAll()

    def toggle_password_visibility(self, checked):
        """切换密码可见性"""
        if checked:
            # 显示密码
            self.network_secret_edit.setEchoMode(QLineEdit.Normal)
            self.password_visibility_btn.setText("🙈")
            self.password_visibility_btn.setToolTip("隐藏密码")
        else:
            # 隐藏密码
            self.network_secret_edit.setEchoMode(QLineEdit.Password)
            self.password_visibility_btn.setText("👁")
            self.password_visibility_btn.setToolTip("显示密码")
    
    def create_advanced_group(self) -> QGroupBox:
        """创建高级设置组"""
        group = QGroupBox("高级设置")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
            QCheckBox {
                color: #cdd6f4;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #313244;
                border-radius: 4px;
                background-color: #1e1e2e;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #74c7ec;
            }
        """)
        layout = QGridLayout(group)
        layout.setSpacing(15)

        # 加密选项
        self.encryption_check = QCheckBox("启用加密")
        self.encryption_check.setChecked(True)
        layout.addWidget(self.encryption_check, 0, 0)

        # IPv6选项
        self.ipv6_check = QCheckBox("启用IPv6")
        self.ipv6_check.setChecked(True)  # 默认启用
        layout.addWidget(self.ipv6_check, 0, 1)

        # 延迟优先选项
        self.latency_first_check = QCheckBox("延迟优先")
        self.latency_first_check.setChecked(True)  # 默认启用延迟优先
        layout.addWidget(self.latency_first_check, 1, 0)

        # 多线程选项
        self.multi_thread_check = QCheckBox("使用多线程运行")
        self.multi_thread_check.setChecked(True)  # 默认启用多线程
        layout.addWidget(self.multi_thread_check, 1, 1)

        # IPv6提醒信息
        ipv6_hint = QLabel("💡 提醒：若启动失败可尝试取消勾选「启用IPv6」")
        ipv6_hint.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                font-style: italic;
                padding: 6px 8px;
                background-color: rgba(250, 179, 135, 0.1);
                border: 1px solid rgba(250, 179, 135, 0.3);
                border-radius: 4px;
                margin-top: 8px;
            }
        """)
        layout.addWidget(ipv6_hint, 2, 0, 1, 2)  # 跨两列显示

        return group
    
    def create_control_group(self) -> QGroupBox:
        """创建控制组"""
        group = QGroupBox("网络控制")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
            }
        """)
        layout = QVBoxLayout(group)
        
        # 连接状态
        status_layout = QHBoxLayout()
        status_title = QLabel("连接状态:")
        status_title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.connection_status_label = QLabel("未连接")
        self.connection_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("启动网络")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.start_btn.clicked.connect(self.start_network)
        
        self.stop_btn = QPushButton("停止网络")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_network)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        return group
    
    def create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 连接信息
        self.connection_info_group = self.create_connection_info_group()
        layout.addWidget(self.connection_info_group)
        
        # 节点列表
        self.peer_list_group = self.create_peer_list_group()
        layout.addWidget(self.peer_list_group)
        
        # 日志区域
        self.log_group = self.create_log_group()
        layout.addWidget(self.log_group)
        
        return widget
    
    def create_connection_info_group(self) -> QGroupBox:
        """创建连接信息组"""
        group = QGroupBox("连接信息")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
            }
        """)
        layout = QGridLayout(group)
        
        # 网络名称
        network_title = QLabel("当前网络:")
        network_title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(network_title, 0, 0)
        self.current_network_label = QLabel("未连接")
        self.current_network_label.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.current_network_label, 0, 1)

        # 本机IP
        ip_title = QLabel("本机IP:")
        ip_title.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(ip_title, 1, 0)
        self.current_ip_label = QLabel("未分配")
        self.current_ip_label.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.current_ip_label, 1, 1)


        
        return group

    def create_peer_list_group(self) -> QGroupBox:
        """创建节点列表组"""
        group = QGroupBox("连接节点")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
            QTableWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                gridline-color: #313244;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout = QVBoxLayout(group)

        # 节点表格
        self.peer_table = QTableWidget()
        self.peer_table.setColumnCount(4)
        self.peer_table.setHorizontalHeaderLabels(["虚拟IP地址", "玩家名称", "延迟", "连接方式"])

        # 设置表格样式
        header = self.peer_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # IP地址
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # 主机名
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 延迟
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 连接方式

        self.peer_table.setAlternatingRowColors(True)
        self.peer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.peer_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.peer_table)

        return group

    def create_log_group(self) -> QGroupBox:
        """创建日志组"""
        group = QGroupBox("运行日志")
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
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
        layout = QVBoxLayout(group)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setWordWrapMode(QTextOption.WordWrap)  # 启用自动换行
        layout.addWidget(self.log_text)

        # 清除按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)

        return group

    def check_installation_status(self):
        """检查安装状态"""
        if self.easytier_manager.is_easytier_installed():
            self.status_label.setText("已安装")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # 获取版本信息
            current_version = self.download_manager.get_current_easytier_version()
            if current_version:
                self.version_label.setText(f"v{current_version}")
            else:
                self.version_label.setText("未知版本")


        else:
            self.status_label.setText("未安装")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.version_label.setText("未安装")



        # 加载配置
        self.load_config()

    def load_config(self):
        """加载配置"""
        config = self.easytier_manager.get_config()

        self.network_name_edit.setText(config.get("network_name", ""))
        self.machine_id_edit.setText(config.get("hostname", ""))
        self.network_secret_edit.setText(config.get("network_secret", ""))

        # 加载IP配置（dhcp 和 ipv4 互斥）
        use_dhcp = config.get("dhcp", True)
        self.dhcp_check.setChecked(use_dhcp)

        if use_dhcp:
            self.peer_ip_edit.setText("")
            self.peer_ip_edit.setEnabled(False)
        else:
            # 只有在非DHCP模式下才从配置中读取ipv4
            self.peer_ip_edit.setText(config.get("ipv4", "10.126.126.1"))
            self.peer_ip_edit.setEnabled(True)

        # 外部节点已固定，无需配置

        # 设置高级选项（注意disable_*的逻辑转换，默认全部启用）
        self.encryption_check.setChecked(not config.get("disable_encryption", False))  # 默认启用加密
        self.ipv6_check.setChecked(not config.get("disable_ipv6", False))              # 默认启用IPv6
        self.latency_first_check.setChecked(config.get("latency_first", True))         # 默认启用延迟优先
        self.multi_thread_check.setChecked(config.get("multi_thread", True))           # 默认启用多线程

        # 加载服务器选择状态
        if hasattr(self, 'server_list'):
            selected_peers = config.get("peers", ["tcp://public.easytier.top:11010"])
            if isinstance(selected_peers, str):
                selected_peers = [selected_peers]

            # 过滤掉公共服务器，只处理公益服务器
            charity_peers = [peer for peer in selected_peers if peer != "tcp://public.easytier.top:11010"]

            # 重置所有公益服务器状态
            for server in self.server_list:
                server['enabled'] = server['url'] in charity_peers

            # 更新复选框状态
            for i, checkbox in enumerate(self.server_checkboxes):
                checkbox.setChecked(self.server_list[i]['enabled'])

    def save_config(self):
        """保存配置（使用EasyTier对应的参数命名）"""
        config = {
            "network_name": self.network_name_edit.text().strip(),      # --network-name
            "hostname": self.machine_id_edit.text().strip(),            # --hostname
            "network_secret": self.network_secret_edit.text().strip(),  # --network-secret
            "disable_encryption": not self.encryption_check.isChecked(), # --disable-encryption
            "disable_ipv6": not self.ipv6_check.isChecked(),           # --disable-ipv6
            "latency_first": self.latency_first_check.isChecked(),      # --latency-first
            "multi_thread": self.multi_thread_check.isChecked()         # --multi-thread
        }

        # 收集选中的公益服务器
        selected_peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
        if hasattr(self, 'server_list'):
            for server in self.server_list:
                if server['enabled']:
                    selected_peers.append(server['url'])

        config["peers"] = selected_peers  # --peers (支持多个)

        # IP配置：dhcp 和 ipv4 互斥
        if self.dhcp_check.isChecked():
            config["dhcp"] = True                                       # --dhcp
        else:
            config["ipv4"] = self.peer_ip_edit.text().strip()          # --ipv4

        self.easytier_manager.update_config(config)



    def start_network(self):
        """启动网络"""
        # 验证输入
        network_name = self.network_name_edit.text().strip()
        machine_id = self.machine_id_edit.text().strip()
        network_secret = self.network_secret_edit.text().strip()
        peer_ip = self.peer_ip_edit.text().strip()
        use_dhcp = self.dhcp_check.isChecked()

        if not network_name:
            self.log_text.append("错误: 请输入房间名称")
            return

        if not machine_id:
            self.log_text.append("错误: 请输入玩家名称")
            return

        if not network_secret:
            self.log_text.append("错误: 请输入房间密码")
            return

        # 只有在禁用DHCP时才验证手动IP
        if not use_dhcp and not peer_ip:
            self.log_text.append("错误: 请输入本机IP或启用DHCP")
            return

        # 保存配置
        self.save_config()

        # 自动保存房间配置
        self.auto_save_room_config(network_name)

        # 启动网络
        self.log_text.append(f"正在启动房间: {network_name}")
        self.log_text.append(f"玩家名称: {machine_id}")
        if use_dhcp:
            self.log_text.append("IP分配方式: 自动分配(DHCP)")
        else:
            self.log_text.append(f"IP分配方式: 手动指定({peer_ip})")

        # 获取选中的服务器列表
        selected_peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
        if hasattr(self, 'server_list'):
            for server in self.server_list:
                if server['enabled']:
                    selected_peers.append(server['url'])

        success = self.easytier_manager.start_network(
            network_name=network_name,
            network_secret=network_secret,
            ipv4=peer_ip,
            peers=selected_peers,
            hostname=machine_id,
            dhcp=use_dhcp
        )

        if success:
            self.log_text.append("房间启动成功")
        else:
            self.log_text.append("房间启动失败")

    def stop_network(self):
        """停止网络"""
        self.log_text.append("正在停止网络...")
        success = self.easytier_manager.stop_network()

        if success:
            self.log_text.append("网络已停止")
        else:
            self.log_text.append("停止网络失败")

    # 信号处理方法
    def on_network_status_changed(self, connected: bool):
        """网络状态变化"""
        if connected:
            self.connection_status_label.setText("已连接")
            self.connection_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.connection_status_label.setText("未连接")
            self.connection_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

            # 清空连接信息
            self.current_network_label.setText("未连接")
            self.current_ip_label.setText("未分配")
            self.peer_table.setRowCount(0)

    def on_peer_list_updated(self, peers: list):
        """节点列表更新"""
        self.peer_table.setRowCount(len(peers))

        for i, peer in enumerate(peers):
            # IP地址
            ip_item = QTableWidgetItem(peer.get("ip", ""))
            self.peer_table.setItem(i, 0, ip_item)

            # 主机名（玩家名称）
            hostname = peer.get("hostname", "")
            if not hostname:
                hostname = "未知"
            hostname_item = QTableWidgetItem(hostname)
            self.peer_table.setItem(i, 1, hostname_item)

            # 延迟
            latency = peer.get("latency", "")
            if latency and latency != "-":
                try:
                    # 如果是数字，添加ms单位
                    float(latency)
                    latency = f"{latency}ms"
                except:
                    pass
            latency_item = QTableWidgetItem(latency)
            self.peer_table.setItem(i, 2, latency_item)

            # 连接方式
            cost = peer.get("cost", "")
            if "relay" in cost:
                connection_type = "中继"
            elif "p2p" in cost:
                connection_type = "直连"
            else:
                connection_type = cost
            connection_item = QTableWidgetItem(connection_type)
            self.peer_table.setItem(i, 3, connection_item)

    def on_connection_info_updated(self, info: dict):
        """连接信息更新"""
        self.current_network_label.setText(info.get("network_name", "未知"))
        self.current_ip_label.setText(info.get("local_ip", "未分配"))

    def on_error_occurred(self, error_message: str):
        """错误发生"""
        self.log_text.append(f"错误: {error_message}")
