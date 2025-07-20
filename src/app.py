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
from .config.config_manager import ConfigManager


class NmodmApp:
    """主应用程序类"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_app()

        # 管理器（延迟初始化）
        self.config_manager = None
        self.download_manager = None

        # 页面缓存（延迟加载）
        self._pages_cache = {}

        # 创建主窗口
        self.main_window = MainWindow()

        # 设置局域网模式状态
        self.main_window.set_lan_mode(self.lan_detector.is_lan_mode)

        self.setup_main_content()

        # 延迟初始化其他组件
        QTimer.singleShot(100, self.delayed_initialization)

        # 如果是局域网模式，延迟显示提示
        if self.lan_detector.is_lan_mode:
            QTimer.singleShot(1000, self.show_lan_mode_notification)

    def delayed_initialization(self):
        """延迟初始化非关键组件"""
        # 初始化管理器
        if self.config_manager is None:
            self.config_manager = ConfigManager()

        # 延迟初始化下载管理器
        QTimer.singleShot(200, self.init_download_manager)

        # 延迟状态检查
        QTimer.singleShot(500, self.setup_status_timer)

    def init_download_manager(self):
        """初始化下载管理器"""
        if self.download_manager is None:
            from .utils.download_manager import DownloadManager
            self.download_manager = DownloadManager()

    def setup_app(self):
        """设置应用程序"""
        self.app.setApplicationName("Nmodm")
        self.app.setApplicationVersion("2.0.4")
        self.app.setOrganizationName("Nmodm Team")

        # 初始化局域网模式检测器
        from src.utils.lan_mode_detector import get_lan_mode_detector
        self.lan_detector = get_lan_mode_detector()

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
        
        # 只创建首页，其他页面延迟加载
        self.create_initial_page()
        
        # 添加到布局
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.page_stack, 1)
        
        content_widget.setLayout(content_layout)
        
        # 设置为主窗口的内容区域
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_widget)
        
        self.main_window.content_area.setLayout(main_layout)
    
    def create_initial_page(self):
        """只创建首页，其他页面延迟加载"""
        from .ui.pages.home_page import HomePage

        # 首页
        self.home_page = HomePage()
        self.home_page.navigate_to.connect(self.navigate_to_page)
        self.page_stack.addWidget(self.home_page)

        # 页面映射（延迟加载）
        self.pages = {
            "home": (0, self.home_page),
            "config": (1, None),
            "me3": (2, None),
            "mods": (3, None),
            "bin_merge": (4, None),
            "lan_gaming": (5, None),
            "about": (6, None)
        }

    def get_or_create_page(self, page_name):
        """获取或创建页面（延迟加载）"""
        if page_name not in self.pages:
            return None

        index, page = self.pages[page_name]

        # 如果页面还未创建，则创建它
        if page is None:
            page = self._create_page(page_name)
            if page:
                # 添加到页面堆栈
                if self.page_stack.count() <= index:
                    # 确保有足够的位置
                    while self.page_stack.count() <= index:
                        placeholder = QWidget()
                        self.page_stack.addWidget(placeholder)

                # 替换占位符
                old_widget = self.page_stack.widget(index)
                self.page_stack.removeWidget(old_widget)
                self.page_stack.insertWidget(index, page)

                # 更新映射
                self.pages[page_name] = (index, page)

        return page

    def _create_page(self, page_name):
        """创建具体的页面"""
        try:
            if page_name == "config":
                from .ui.pages.config_page import ConfigPage
                page = ConfigPage()
                page.status_updated.connect(self.update_home_status)
                return page

            elif page_name == "me3":
                from .ui.pages.me3_page import ToolDownloadPage
                page = ToolDownloadPage()
                page.status_updated.connect(self.update_home_status)
                return page

            elif page_name == "mods":
                from .ui.pages.mods_page import ModsPage
                page = ModsPage()
                page.config_changed.connect(self.update_home_status)
                return page

            elif page_name == "bin_merge":
                from .ui.pages.bin_merge_page import BinMergePage
                page = BinMergePage()
                return page

            elif page_name == "lan_gaming":
                from .ui.pages.lan_gaming_page import LanGamingPage
                page = LanGamingPage()
                return page

            elif page_name == "about":
                from .ui.pages.about_page import AboutPage
                page = AboutPage()
                return page

        except Exception as e:
            print(f"创建页面 {page_name} 失败: {e}")

        return None
        
        # 默认显示首页
        self.page_stack.setCurrentIndex(0)
    
    def switch_page(self, page_id):
        """切换页面（延迟加载）"""
        if page_id in self.pages:
            # 获取或创建页面
            page = self.get_or_create_page(page_id)
            if page:
                index, _ = self.pages[page_id]
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
            # 确保管理器已初始化
            if self.config_manager is None:
                self.config_manager = ConfigManager()

            # 更新首页状态
            if hasattr(self, 'home_page') and self.home_page:
                self.home_page.refresh_status()
        except Exception as e:
            print(f"更新状态失败: {e}")
    
    def run(self):
        """运行应用程序"""
        self.main_window.show()
        return self.app.exec()
    
    def show_lan_mode_notification(self):
        """显示局域网模式通知"""
        try:
            # 获取检测器状态信息
            status_info = self.lan_detector.get_status_info()
            detection_method = status_info.get('detection_method', 'unknown')

            # 根据检测方法显示不同的消息
            if detection_method == 'dll_injection':
                print("🌐 【局域网联机模式】已激活 - 检测到steamclient DLL注入")
            elif detection_method == 'parent_process':
                print("🌐 【局域网联机模式】已激活 - 通过steamclient_loader启动")
            else:
                print("🌐 【局域网联机模式】已激活 - 现在可以与局域网内的其他玩家一起游戏")

            # 显示醒目的启动通知
            self._show_lan_mode_popup()

        except Exception as e:
            print(f"显示局域网模式通知失败: {e}")

    def _show_lan_mode_popup(self):
        """显示局域网模式弹窗通知"""
        try:
            from PySide6.QtWidgets import QMessageBox
            from PySide6.QtCore import Qt

            # 创建消息框
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("🌐 局域网联机模式")
            msg_box.setText("🎉 局域网联机模式已激活！")
            msg_box.setInformativeText(
                "现在您可以与局域网内的其他玩家一起游戏。\n\n"
                "✅ steamclient已成功注入\n"
                "✅ 局域网联机功能已启用\n"
                "✅ 可以开始联机游戏了"
            )
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)

            # 设置样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                }
                QMessageBox QLabel {
                    color: #cdd6f4;
                    font-size: 14px;
                }
                QMessageBox QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QMessageBox QPushButton:hover {
                    background-color: #74c7ec;
                }
            """)

            # 显示消息框
            msg_box.exec()

        except Exception as e:
            print(f"显示局域网模式弹窗失败: {e}")

    def quit(self):
        """退出应用程序"""
        # 清理局域网模式状态
        try:
            print("🧹 程序退出，清理局域网模式状态...")
            from src.utils.lan_mode_detector import cleanup_lan_mode_on_exit
            cleanup_lan_mode_on_exit()
        except Exception as e:
            print(f"清理局域网模式状态失败: {e}")

        self.app.quit()


def create_app():
    """创建应用程序实例"""
    return NmodmApp()
