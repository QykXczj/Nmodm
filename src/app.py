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
from .ui.pages.me3_page import ME3Page
from .ui.pages.mods_page import ModsPage
from .ui.pages.about_page import AboutPage
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
        self.app.setApplicationVersion("1.0.1")
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
        # 创建主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建侧边栏
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # 创建页面堆栈
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)
        
        # 创建页面
        self.pages = {}
        self.create_pages()
        
        # 设置主窗口内容
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.main_window.setCentralWidget(central_widget)
        
        # 连接信号
        self.sidebar.page_changed.connect(self.switch_page)
        
        # 设置默认页面
        self.sidebar.set_current_page("home")
    
    def create_pages(self):
        """创建所有页面"""
        # 首页
        home_page = HomePage()
        home_page.config_manager = self.config_manager
        home_page.download_manager = self.download_manager
        self.add_page("home", home_page)
        
        # 配置页面
        config_page = ConfigPage()
        config_page.config_manager = self.config_manager
        self.add_page("config", config_page)
        
        # ME3页面
        me3_page = ME3Page()
        me3_page.download_manager = self.download_manager
        self.add_page("me3", me3_page)
        
        # Mod配置页面
        mods_page = ModsPage()
        mods_page.config_manager = self.config_manager
        self.add_page("mods", mods_page)
        
        # 关于页面
        about_page = AboutPage()
        self.add_page("about", about_page)
        
        # 连接页面间的信号
        self.connect_page_signals()
    
    def add_page(self, page_id, page):
        """添加页面"""
        index = self.page_stack.addWidget(page)
        self.pages[page_id] = (index, page)
    
    def connect_page_signals(self):
        """连接页面间的信号"""
        # 获取页面实例
        _, home_page = self.pages["home"]
        _, config_page = self.pages["config"]
        _, me3_page = self.pages["me3"]
        _, mods_page = self.pages["mods"]
        
        # 连接配置变化信号
        config_page.config_changed.connect(home_page.update_status)
        me3_page.me3_status_changed.connect(home_page.update_status)
        mods_page.config_changed.connect(home_page.update_status)
        
        # 连接导航信号
        home_page.navigate_to_config.connect(lambda: self.navigate_to_page("config"))
        home_page.navigate_to_me3.connect(lambda: self.navigate_to_page("me3"))
        home_page.navigate_to_mods.connect(lambda: self.navigate_to_page("mods"))
    
    def setup_status_timer(self):
        """设置状态检查定时器"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒检查一次
    
    def update_status(self):
        """更新状态"""
        if "home" in self.pages:
            _, home_page = self.pages["home"]
            home_page.update_status()
    
    def switch_page(self, page_id):
        """切换页面"""
        if page_id in self.pages:
            index, page = self.pages[page_id]
            self.page_stack.setCurrentIndex(index)
    
    def navigate_to_page(self, page_id):
        """导航到指定页面"""
        self.sidebar.set_current_page(page_id)
    
    def run(self):
        """运行应用程序"""
        self.main_window.show()
        return self.app.exec()


def create_app():
    """创建应用程序实例"""
    return NmodmApp()
