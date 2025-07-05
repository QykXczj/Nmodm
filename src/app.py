"""
主应用程序类
整合所有组件，实现完整的应用程序
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .ui.main_window import MainWindow
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
        self.main_window.show()
    
    def setup_app(self):
        """设置应用程序"""
        self.app.setApplicationName("Nmodm")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Nmodm Team")
        
        # 设置应用程序字体
        font = QFont("Microsoft YaHei UI", 9)
        self.app.setFont(font)
    
    def run(self):
        """运行应用程序"""
        return self.app.exec()


def create_app():
    """创建应用程序实例"""
    return NmodmApp()