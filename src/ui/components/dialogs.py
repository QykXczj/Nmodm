"""
通用弹窗组件
符合整体UI风格的对话框组件
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class BaseDialog(QDialog):
    """基础弹窗类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_position = None
        self.setup_base_ui()
    
    def setup_base_ui(self):
        """设置基础UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 基础样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
            }
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
            QPushButton#dangerButton {
                background-color: #f38ba8;
            }
            QPushButton#dangerButton:hover {
                background-color: #f17497;
            }
            QPushButton#successButton {
                background-color: #a6e3a1;
            }
            QPushButton#successButton:hover {
                background-color: #94d3a2;
            }
            QPushButton#warningButton {
                background-color: #fab387;
            }
            QPushButton#warningButton:hover {
                background-color: #f7d794;
            }
        """)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖拽"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.pos()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于拖拽"""
        if hasattr(self, 'drag_position') and self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)


class NotificationDialog(BaseDialog):
    """通知弹窗"""
    
    def __init__(self, title, message, dialog_type="info", parent=None):
        self.title = title
        self.message = message
        self.dialog_type = dialog_type
        super().__init__(parent)
        self.setup_content()
    
    def setup_content(self):
        """设置内容"""
        self.setFixedSize(450, 280)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 图标和标题
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        icon = icon_map.get(self.dialog_type, "ℹ️")
        title_label = QLabel(f"{icon} {self.title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #89b4fa;
                margin-bottom: 10px;
            }
        """)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6c7086;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """)
        close_btn.clicked.connect(self.reject)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("QFrame { color: #45475a; }")
        layout.addWidget(line)
        
        # 消息内容
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.5;
                color: #bac2de;
                padding: 10px;
                background-color: #181825;
                border-radius: 8px;
                border: 1px solid #313244;
            }
        """)
        layout.addWidget(message_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(100)
        if self.dialog_type == "error":
            ok_btn.setObjectName("dangerButton")
        elif self.dialog_type == "success":
            ok_btn.setObjectName("successButton")
        elif self.dialog_type == "warning":
            ok_btn.setObjectName("warningButton")
        
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)


class ConfirmDialog(BaseDialog):
    """确认弹窗"""
    
    confirmed = Signal()
    
    def __init__(self, title, message, confirm_text="确定", cancel_text="取消", 
                 dialog_type="warning", parent=None):
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.dialog_type = dialog_type
        super().__init__(parent)
        self.setup_content()
    
    def setup_content(self):
        """设置内容"""
        self.setFixedSize(480, 320)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 图标和标题
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "question": "❓"
        }
        
        icon = icon_map.get(self.dialog_type, "❓")
        title_label = QLabel(f"{icon} {self.title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #89b4fa;
                margin-bottom: 10px;
            }
        """)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6c7086;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """)
        close_btn.clicked.connect(self.reject)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("QFrame { color: #45475a; }")
        layout.addWidget(line)
        
        # 消息内容
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.5;
                color: #bac2de;
                padding: 15px;
                background-color: #181825;
                border-radius: 8px;
                border: 1px solid #313244;
            }
        """)
        layout.addWidget(message_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton(self.cancel_text)
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                border: none;
                border-radius: 6px;
                color: #cdd6f4;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7c7f93;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        # 确认按钮
        confirm_btn = QPushButton(self.confirm_text)
        confirm_btn.setFixedWidth(100)
        if self.dialog_type == "error":
            confirm_btn.setObjectName("dangerButton")
        elif self.dialog_type == "success":
            confirm_btn.setObjectName("successButton")
        elif self.dialog_type == "warning":
            confirm_btn.setObjectName("warningButton")
        
        confirm_btn.clicked.connect(self.confirm_action)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def confirm_action(self):
        """确认操作"""
        self.confirmed.emit()
        self.accept()
