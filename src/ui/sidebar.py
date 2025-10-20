"""
侧边栏组件
实现现代化的导航侧边栏
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from src.i18n import t, TLabel, TranslationManager


class SidebarButton(QPushButton):
    """侧边栏按钮"""

    def __init__(self, text, icon_text="", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.icon_text = icon_text
        self.is_active = False
        self.is_hovered = False

        self.setFixedHeight(50)
        self.setCheckable(True)

        # 启用鼠标跟踪和悬停事件
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

        self.setup_style()
    
    def setup_style(self):
        """设置按钮基础样式"""
        self.update_style()

    def update_style(self):
        """更新按钮样式"""
        if self.is_active:
            if self.is_hovered:
                # 选中状态的悬停样式
                style = """
                    SidebarButton {
                        background-color: #74c7ec;
                        border: none;
                        color: #1e1e2e;
                        text-align: left;
                        padding: 12px 15px;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 8px;
                        margin: 2px 5px;
                    }
                """
            else:
                # 选中状态的正常样式
                style = """
                    SidebarButton {
                        background-color: #89b4fa;
                        border: none;
                        color: #1e1e2e;
                        text-align: left;
                        padding: 12px 15px;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 8px;
                        margin: 2px 5px;
                    }
                """
        else:
            if self.is_hovered:
                # 未选中状态的悬停样式
                style = """
                    SidebarButton {
                        background-color: #313244;
                        border: none;
                        color: #cdd6f4;
                        text-align: left;
                        padding: 12px 15px;
                        font-size: 14px;
                        font-weight: 500;
                        border-radius: 8px;
                        margin: 2px 5px;
                    }
                """
            else:
                # 未选中状态的正常样式
                style = """
                    SidebarButton {
                        background-color: transparent;
                        border: none;
                        color: #bac2de;
                        text-align: left;
                        padding: 12px 15px;
                        font-size: 14px;
                        font-weight: 500;
                        border-radius: 8px;
                        margin: 2px 5px;
                    }
                """

        self.setStyleSheet(style)
    
    def set_active(self, active):
        """设置激活状态"""
        self.is_active = active
        self.setChecked(active)
        self.update_style()

    def enterEvent(self, event):
        """鼠标进入事件"""
        super().enterEvent(event)
        self.is_hovered = True
        self.update_style()

    def leaveEvent(self, event):
        """鼠标离开事件"""
        super().leaveEvent(event)
        self.is_hovered = False
        self.update_style()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 确保悬停状态正确"""
        super().mouseMoveEvent(event)
        if not self.is_hovered:
            self.is_hovered = True
            self.update_style()


class Sidebar(QWidget):
    """侧边栏组件"""
    
    # 页面切换信号
    page_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = "welcome"
        self.buttons = {}

        # 菜单项翻译键映射
        self.menu_translations = {
            "welcome": "sidebar.menu_text.welcome",
            "home": "sidebar.menu_text.home",
            "config": "sidebar.menu_text.config",
            "me3": "sidebar.menu_text.me3",
            "mods": "sidebar.menu_text.mods",
            "lan_gaming": "sidebar.menu_text.lan_gaming",
            "virtual_lan": "sidebar.menu_text.virtual_lan",
            "misc": "sidebar.menu_text.misc"
        }

        # 菜单项图标映射
        self.menu_icons = {
            "welcome": "🏠",
            "home": "🚀",
            "config": "⚙️",
            "me3": "📥",
            "mods": "🔧",
            "lan_gaming": "🌐",
            "virtual_lan": "🌍",
            "misc": "📦"
        }

        self.setup_ui()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)
        
    def setup_ui(self):
        """设置UI"""
        self.setFixedWidth(160)
        self.setStyleSheet("""
            Sidebar {
                background-color: #1e1e2e;
                border-right: 1px solid #313244;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(0)
        
        # 应用标题
        self.create_header(layout)
        
        # 导航菜单
        self.create_navigation(layout)
        
        # 底部信息
        layout.addStretch()
        self.create_footer(layout)
        
        self.setLayout(layout)
    
    def create_header(self, layout):
        """创建头部"""
        header = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(15, 0, 15, 20)
        
        # 应用名称
        app_name = QLabel("Nmodm")
        app_name.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        
        # 副标题
        subtitle = TLabel("sidebar.app_subtitle")
        subtitle.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        
        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: #313244;
                background-color: #313244;
                border: none;
                height: 1px;
            }
        """)
        
        header_layout.addWidget(app_name)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(separator)
        
        header.setLayout(header_layout)
        layout.addWidget(header)
    
    def create_navigation(self, layout):
        """创建导航菜单"""
        nav_container = QWidget()
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 10, 0, 10)
        nav_layout.setSpacing(5)
        
        # 菜单项
        for page_id in ["welcome", "home", "config", "me3", "mods", "lan_gaming", "virtual_lan", "misc"]:
            icon = self.menu_icons[page_id]
            text = t(self.menu_translations[page_id])
            btn = SidebarButton(f"  {icon}  {text}")
            btn.clicked.connect(lambda checked=False, p=page_id: self.switch_page(p))
            self.buttons[page_id] = btn
            nav_layout.addWidget(btn)
        
        # 设置首页为默认激活
        self.buttons["welcome"].set_active(True)
        
        nav_container.setLayout(nav_layout)
        layout.addWidget(nav_container)
    
    def create_footer(self, layout):
        """创建底部信息"""
        footer = QWidget()
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(15, 10, 15, 0)
        
        # 版本信息
        version_label = QLabel("v3.1.1")
        version_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 11px;
                text-align: center;
            }
        """)
        
        footer_layout.addWidget(version_label)
        footer.setLayout(footer_layout)
        layout.addWidget(footer)
    
    def _on_language_changed(self, locale: str):
        """
        语言切换回调

        Args:
            locale: 新的语言代码
        """
        print(f"    🔄 更新侧边栏菜单项翻译 → {locale}")

        # 更新所有菜单项的文本
        for page_id, btn in self.buttons.items():
            icon = self.menu_icons[page_id]
            text = t(self.menu_translations[page_id])
            btn.setText(f"  {icon}  {text}")

    def switch_page(self, page_id):
        """切换页面"""
        if page_id == self.current_page:
            return

        # 更新按钮状态
        for btn_id, btn in self.buttons.items():
            btn.set_active(btn_id == page_id)
        
        self.current_page = page_id
        self.page_changed.emit(page_id)
    
    def set_current_page(self, page_id):
        """设置当前页面"""
        if page_id in self.buttons:
            self.switch_page(page_id)


