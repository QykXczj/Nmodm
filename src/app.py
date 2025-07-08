"""
主应用程序类
整合所有组件，实现完整的应用程序
"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from .ui.main_window import MainWindow
from .ui.sidebar import Sidebar
from .ui.pages.home_page import HomePage
from .ui.pages.config_page import ConfigPage
from .ui.pages.me3_page import ToolDownloadPage
from .ui.pages.mods_page import ModsPage
from .ui.pages.about_page import AboutPage
from .ui.pages.bin_merge_page import BinMergePage
from .config.config_manager import ConfigManager
from .utils.download_manager import DownloadManager


class NmodmApp:
    """主应用程序类"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_app()
        
        # 管理器
        self.config_manager = ConfigManager()
        self.download_manager = DownloadManager()
        
        # 创建主窗口
        self.main_window = MainWindow()
        self.setup_main_content()
        
        # 初始化状态检查
        self.setup_status_timer()
    
    def setup_app(self):
        """设置应用程序"""
        self.app.setApplicationName("Nmodm")
        self.app.setApplicationVersion("2.0.0")
        self.app.setOrganizationName("Nmodm Team")
        
        # 设置应用程序字体
        font = QFont("Microsoft YaHei UI", 9)
        self.app.setFont(font)
        
        # 设置应用程序样式
        self.app.setStyleSheet("""
            * {
                outline: none;
            }
            QToolTip {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px;
            }
        """)
    
    def setup_main_content(self):
        """设置主要内容"""
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        
        # 创建页面堆栈
        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #181825;
                border-radius: 0px 0px 10px 0px;
            }
        """)
        
        # 创建页面
        self.create_pages()
        
        # 添加到布局
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.page_stack, 1)
        
        content_widget.setLayout(content_layout)
        
        # 设置为主窗口的内容区域
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_widget)
        
        self.main_window.content_area.setLayout(main_layout)
    
    def create_pages(self):
        """创建所有页面"""
        # 首页
        self.home_page = HomePage()
        self.home_page.navigate_to.connect(self.navigate_to_page)
        self.page_stack.addWidget(self.home_page)
        
        # 配置页面
        self.config_page = ConfigPage()
        self.config_page.status_updated.connect(self.update_home_status)
        self.page_stack.addWidget(self.config_page)
        
        # 工具下载页面
        self.me3_page = ToolDownloadPage()
        self.me3_page.status_updated.connect(self.update_home_status)
        self.page_stack.addWidget(self.me3_page)
        
        # Mod页面
        self.mods_page = ModsPage()
        self.mods_page.config_changed.connect(self.update_home_status)
        self.page_stack.addWidget(self.mods_page)

        # BIN合并页面
        self.bin_merge_page = BinMergePage()
        self.page_stack.addWidget(self.bin_merge_page)

        # 关于页面
        self.about_page = AboutPage()
        self.page_stack.addWidget(self.about_page)
        
        # 页面映射
        self.pages = {
            "home": (0, self.home_page),
            "config": (1, self.config_page),
            "me3": (2, self.me3_page),
            "mods": (3, self.mods_page),
            "bin_merge": (4, self.bin_merge_page),
            "about": (5, self.about_page)
        }
        
        # 默认显示首页
        self.page_stack.setCurrentIndex(0)
    
    def switch_page(self, page_id):
        """切换页面"""
        if page_id in self.pages:
            index, page = self.pages[page_id]
            self.page_stack.setCurrentIndex(index)
    
    def navigate_to_page(self, page_id):
        """导航到指定页面"""
        self.sidebar.set_current_page(page_id)
        self.switch_page(page_id)
    
    def setup_status_timer(self):
        """设置状态检查定时器"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_home_status)
        self.status_timer.start(5000)  # 每5秒检查一次状态
        
        # 立即执行一次状态更新
        QTimer.singleShot(100, self.update_home_status)
    
    def update_home_status(self):
        """更新首页状态显示"""
        try:
            # 更新首页状态
            self.home_page.refresh_status()
        except Exception as e:
            print(f"更新状态失败: {e}")
    
    def run(self):
        """运行应用程序"""
        self.main_window.show()
        return self.app.exec()
    
    def quit(self):
        """退出应用程序"""
        self.app.quit()


def create_app():
    """创建应用程序实例"""
    return NmodmApp()
