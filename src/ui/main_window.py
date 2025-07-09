"""
主窗口类
实现现代化无边框窗口设计
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QFrame, QPushButton, QLabel, QSizeGrip)
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap


class TitleBar(QWidget):
    """自定义标题栏"""
    
    # 窗口控制信号
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.start = QPoint(0, 0)
        self.pressing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setFixedHeight(40)
        self.setStyleSheet("""
            TitleBar {
                background-color: #1e1e2e;
                border-bottom: 1px solid #313244;
            }
        """)
        
        # 主布局
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # 应用图标和标题
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setStyleSheet("QLabel { margin-right: 8px; }")

        # 延迟加载图标
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self.load_icon)

        self.title_label = QLabel("Nmodm - 游戏管理工具")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                padding-left: 8px;
            }
        """)
        
        # 窗口控制按钮
        self.control_buttons = self.create_control_buttons()
        
        # 添加到布局
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.control_buttons)
        
        self.setLayout(layout)
    
    def create_control_buttons(self):
        """创建窗口控制按钮"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 按钮样式
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                width: 45px;
                height: 40px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """
        
        close_button_style = button_style + """
            QPushButton:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """
        
        # 最小化按钮
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setStyleSheet(button_style)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        
        # 最大化按钮
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setStyleSheet(button_style)
        self.maximize_btn.clicked.connect(self.maximize_clicked.emit)
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setStyleSheet(close_button_style)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)
        
        container.setLayout(layout)
        return container

    def load_icon(self):
        """延迟加载应用图标"""
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "zwnr.png")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"加载图标失败: {e}")

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.start = self.mapToGlobal(event.position().toPoint())
            self.pressing = True
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 实现窗口拖动"""
        if self.pressing and self.parent:
            end = self.mapToGlobal(event.position().toPoint())
            movement = end - self.start
            self.parent.move(self.parent.pos() + movement)
            self.start = end
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.pressing = False


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.is_maximized = False
        self.normal_geometry = None
        
        self.setup_window()
        self.setup_ui()
        
    def setup_window(self):
        """设置窗口属性"""
        # 无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 窗口大小和位置
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)
        
        # 居中显示
        self.center_window()
        
    def setup_ui(self):
        """设置UI"""
        # 主容器
        self.main_container = QWidget()
        self.main_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 10px;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏
        self.title_bar = TitleBar(self)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self.toggle_maximize)
        self.title_bar.close_clicked.connect(self.close)
        
        # 内容区域
        self.content_area = QWidget()
        self.content_area.setStyleSheet("""
            QWidget {
                background-color: #181825;
                border-radius: 0px 0px 10px 10px;
            }
        """)
        
        # 添加到主布局
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.content_area, 1)
        
        self.main_container.setLayout(main_layout)
        self.setCentralWidget(self.main_container)
        
        # 添加调整大小的抓手
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("""
            QSizeGrip {
                background-color: transparent;
                width: 16px;
                height: 16px;
            }
        """)
    
    def center_window(self):
        """窗口居中"""
        screen = self.screen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def toggle_maximize(self):
        """切换最大化状态"""
        if self.is_maximized:
            self.showNormal()
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.is_maximized = False
            self.title_bar.maximize_btn.setText("□")
        else:
            self.normal_geometry = self.geometry()
            screen = self.screen().availableGeometry()
            self.setGeometry(screen)
            self.is_maximized = True
            self.title_bar.maximize_btn.setText("❐")
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 调整size grip位置
        self.size_grip.move(
            self.width() - self.size_grip.width(),
            self.height() - self.size_grip.height()
        )
