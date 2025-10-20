"""
通用弹窗组件
符合整体UI风格的对话框组件
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from src.i18n.manager import TranslationManager, t


class ModernDialog(QDialog):
    """现代化对话框基类"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        # 无边框窗口设置
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setMinimumSize(400, 300)

        # 拖拽支持
        self.drag_position = None

        # 主样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                background-color: transparent;
                border: none;
            }
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 16px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
            QPushButton#cancelButton {
                background-color: #6c7086;
                color: #cdd6f4;
            }
            QPushButton#cancelButton:hover {
                background-color: #7c7f93;
            }
            QPushButton#dangerButton {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
            QPushButton#dangerButton:hover {
                background-color: #f17497;
            }
            QPushButton#successButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
            }
            QPushButton#successButton:hover {
                background-color: #94d3a2;
            }
            QPushButton#warningButton {
                background-color: #fab387;
                color: #1e1e2e;
            }
            QPushButton#warningButton:hover {
                background-color: #f7d794;
            }
        """)

        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 添加标题栏
        self.setup_title_bar()

    def setup_title_bar(self):
        """设置标题栏"""
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        title_frame.setFixedHeight(30)

        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        # 标题文本
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 5px 0px;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                color: #1e1e2e;
                font-size: 18px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #f17497;
                color: #1e1e2e;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        self.main_layout.insertWidget(0, title_frame)

    def add_content(self, widget):
        """添加内容到对话框"""
        self.main_layout.addWidget(widget)

    def add_buttons(self, buttons):
        """添加按钮到对话框底部"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        for button in buttons:
            button_layout.addWidget(button)
            button_layout.addSpacing(10)

        # 移除最后一个间距
        if button_layout.count() > 1:
            button_layout.removeItem(button_layout.itemAt(button_layout.count() - 1))

        self.main_layout.addLayout(button_layout)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖拽"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于拖拽"""
        if hasattr(self, 'drag_position') and self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()


class NotificationDialog(ModernDialog):
    """通知对话框"""

    def __init__(self, title, message, dialog_type="info", parent=None):
        self.message = message
        self.dialog_type = dialog_type
        super().__init__(title, parent)
        self.setup_content()

    def setup_content(self):
        """设置内容"""
        self.setFixedSize(380, 180)

        # 紧凑的水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 图标
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }

        icon_label = QLabel(icon_map.get(self.dialog_type, "ℹ️"))
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(30, 30)
        content_layout.addWidget(icon_label)

        # 消息内容 - 尽量一行显示
        message_label = QLabel(self.message)
        message_label.setWordWrap(False)  # 禁用自动换行，尽量一行显示

        # 根据类型设置颜色
        color_map = {
            "info": "#89b4fa",
            "warning": "#fab387",
            "error": "#f38ba8",
            "success": "#a6e3a1"
        }
        text_color = color_map.get(self.dialog_type, "#cdd6f4")

        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {text_color};
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        content_layout.addWidget(message_label, 1)

        # 创建内容容器
        content_widget = QFrame()
        content_widget.setLayout(content_layout)
        content_widget.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)

        self.add_content(content_widget)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: #45475a;
                background-color: #45475a;
                border: none;
                max-height: 1px;
            }
        """)
        self.add_content(separator)

        # 按钮
        self.ok_btn = QPushButton(t("dialog.button.ok"))
        if self.dialog_type == "error":
            self.ok_btn.setObjectName("dangerButton")
        elif self.dialog_type == "success":
            self.ok_btn.setObjectName("successButton")
        elif self.dialog_type == "warning":
            self.ok_btn.setObjectName("warningButton")

        self.ok_btn.clicked.connect(self.accept)
        self.add_buttons([self.ok_btn])

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        try:
            if hasattr(self, 'ok_btn'):
                self.ok_btn.setText(t("dialog.button.ok"))
        except Exception as e:
            print(f"NotificationDialog语言切换失败: {e}")


class ConfirmDialog(ModernDialog):
    """确认对话框"""

    confirmed = Signal()

    def __init__(self, title, message, confirm_text="确定", cancel_text="取消",
                 dialog_type="warning", parent=None):
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.dialog_type = dialog_type
        super().__init__(title, parent)
        self.setup_content()

    def setup_content(self):
        """设置内容"""
        self.setFixedSize(450, 280)

        # 紧凑的水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 图标
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
            "question": "❓"
        }

        icon_label = QLabel(icon_map.get(self.dialog_type, "❓"))

        # 根据类型设置图标颜色
        icon_color_map = {
            "info": "#89b4fa",
            "warning": "#fab387",
            "error": "#f38ba8",
            "success": "#a6e3a1",
            "question": "#cba6f7"
        }
        icon_color = icon_color_map.get(self.dialog_type, "#fab387")

        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                color: {icon_color};
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(40, 40)
        content_layout.addWidget(icon_label)

        # 消息内容 - 紧凑显示
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)

        # 根据类型设置颜色
        color_map = {
            "info": "#89b4fa",
            "warning": "#fab387",
            "error": "#f38ba8",
            "success": "#a6e3a1",
            "question": "#cba6f7"
        }
        text_color = color_map.get(self.dialog_type, "#cdd6f4")

        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                line-height: 1.4;
                color: {text_color};
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        content_layout.addWidget(message_label, 1)

        # 创建内容容器
        content_widget = QFrame()
        content_widget.setLayout(content_layout)
        content_widget.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)

        self.add_content(content_widget)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: #45475a;
                background-color: #45475a;
                border: none;
                max-height: 1px;
            }
        """)
        self.add_content(separator)

        # 按钮
        self.cancel_btn = QPushButton(self.cancel_text if self.cancel_text != "取消" else t("dialog.button.cancel"))
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton(self.confirm_text if self.confirm_text != "确定" else t("dialog.button.ok"))
        if self.dialog_type == "error":
            self.confirm_btn.setObjectName("dangerButton")
        elif self.dialog_type == "success":
            self.confirm_btn.setObjectName("successButton")
        elif self.dialog_type == "warning":
            self.confirm_btn.setObjectName("warningButton")

        self.confirm_btn.clicked.connect(self.confirm_action)

        self.add_buttons([self.cancel_btn, self.confirm_btn])

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        try:
            if hasattr(self, 'cancel_btn') and self.cancel_text == "取消":
                self.cancel_btn.setText(t("dialog.button.cancel"))
            if hasattr(self, 'confirm_btn') and self.confirm_text == "确定":
                self.confirm_btn.setText(t("dialog.button.ok"))
        except Exception as e:
            print(f"ConfirmDialog语言切换失败: {e}")

    def confirm_action(self):
        """确认操作"""
        self.confirmed.emit()
        self.accept()
