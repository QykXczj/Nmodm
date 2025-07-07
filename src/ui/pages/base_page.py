"""
基础页面类
所有页面的基类
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class BasePage(QWidget):
    """基础页面类"""
    
    def __init__(self, title="页面", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
    
    def setup_ui(self):
        """设置基础UI"""
        self.setStyleSheet("""
            BasePage {
                background-color: #181825;
                color: #cdd6f4;
            }
        """)
        
        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 15, 20, 20)  # 减少顶部边距
        self.main_layout.setSpacing(10)  # 减少间距

        # 页面标题
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 22px;  /* 从28px减少到22px */
                font-weight: bold;
                margin-bottom: 5px;  /* 从10px减少到5px */
                padding: 5px 0;  /* 减少内边距 */
            }
        """)
        
        self.main_layout.addWidget(self.title_label)
        self.setLayout(self.main_layout)
    
    def add_content(self, widget):
        """添加内容到页面"""
        self.main_layout.addWidget(widget, 1)  # 设置stretch factor为1，让内容区域占用所有可用空间
    
    def add_stretch(self):
        """添加弹性空间"""
        self.main_layout.addStretch()
