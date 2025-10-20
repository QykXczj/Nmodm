"""
主窗口类
实现现代化无边框窗口设计
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QFrame, QPushButton, QLabel, QSizeGrip)
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap

from src.i18n import t, TLabel


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

        self.title_label = TLabel("main_window.title")
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

    def set_lan_mode(self, is_lan_mode: bool):
        """设置局域网模式状态"""
        # 标题栏不再显示指示器，只更新窗口标题
        pass




class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self, app_instance=None):
        super().__init__()
        self.is_maximized = False
        self.normal_geometry = None

        # 保存App实例的引用，用于访问页面
        self.app_instance = app_instance

        # 局域网模式状态
        self.is_lan_mode = False
        self.base_title = "Nmodm v3.1.1"

        self.setup_window()
        self.setup_ui()
        self.setup_status_bar()
        
    def setup_window(self):
        """设置窗口属性"""
        # 无边框窗口，但保留任务栏交互
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 窗口大小和位置
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        # 居中显示
        self.center_window()

        # 确保窗口在任务栏中正确显示
        self.setWindowTitle("Nmodm v3.1.1")
        
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

    def changeEvent(self, event):
        """窗口状态改变事件 - 处理任务栏点击恢复"""
        if event.type() == event.Type.WindowStateChange:
            # 处理窗口状态变化
            if self.windowState() & Qt.WindowMinimized:
                # 窗口被最小化
                pass
            elif event.oldState() & Qt.WindowMinimized:
                # 从最小化状态恢复
                self.showNormal()
                self.raise_()
                self.activateWindow()

        super().changeEvent(event)

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        # 确保窗口能够获得焦点
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        """窗口隐藏事件"""
        super().hideEvent(event)

    def nativeEvent(self, eventType, message):
        """处理原生Windows事件 - 用于任务栏交互"""
        try:
            # 在Windows上处理任务栏点击事件
            if eventType == "windows_generic_MSG":
                import ctypes
                from ctypes import wintypes

                # 获取消息结构
                msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents

                # WM_SYSCOMMAND = 0x0112
                # SC_RESTORE = 0xF120
                if msg.message == 0x0112 and (msg.wParam & 0xFFF0) == 0xF120:
                    # 任务栏点击恢复
                    if self.isMinimized():
                        self.showNormal()
                        self.raise_()
                        self.activateWindow()
                        return True, 0

        except Exception as e:
            # 静默处理异常，避免影响正常功能
            pass

        return super().nativeEvent(eventType, message)

    def set_lan_mode(self, is_lan_mode: bool):
        """设置局域网模式状态"""
        self.is_lan_mode = is_lan_mode
        self.update_window_title()
        self.update_lan_status_bar()

        # 如果有标题栏，更新标题栏状态
        if hasattr(self, 'title_bar'):
            self.title_bar.set_lan_mode(is_lan_mode)

    def update_window_title(self):
        """更新窗口标题"""
        if self.is_lan_mode:
            title = f"{t('main_window.lan_mode_prefix')} {self.base_title}"
        else:
            title = self.base_title

        self.setWindowTitle(title)

        # 如果有标题栏，也更新标题栏显示
        if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'title_label'):
            self.title_bar.title_label.setText(title)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 检查是否可以关闭软件
        if not self._can_close_application():
            event.ignore()  # 阻止关闭
            return

        # 允许关闭，接受事件
        print("🚪 软件正常关闭")
        super().closeEvent(event)

    def _can_close_application(self) -> bool:
        """检查是否可以关闭应用程序"""
        try:
            # 检查是否有局域网模式重启标志
            if hasattr(self, '_lan_mode_restart') and self._lan_mode_restart:
                print("🔄 检测到局域网模式重启标志，允许关闭窗口")
                return True

            # 1. 检查是否为局域网联机模式
            if self._is_in_lan_gaming_mode():
                self._show_lan_gaming_mode_warning()
                return False

            # 2. 检查是否启动了网络
            if self._is_network_running():
                self._show_network_running_warning()
                return False

            # 3. 所有检查通过，可以关闭
            return True

        except Exception as e:
            print(f"❌ 关闭检查失败: {e}")
            # 发生异常时允许关闭，避免软件无法退出
            return True

    def _is_in_lan_gaming_mode(self) -> bool:
        """检查是否处于局域网联机模式"""
        try:
            from src.utils.lan_mode_detector import is_lan_mode
            is_lan = is_lan_mode()

            if is_lan:
                print("🎮 检测到局域网联机模式激活")

            return is_lan

        except Exception as e:
            print(f"❌ 局域网模式检测失败: {e}")
            return False

    def _show_lan_gaming_mode_warning(self):
        """显示局域网联机模式警告"""
        from PySide6.QtWidgets import QMessageBox

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(t('main_window.close_warning.title'))
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(t('main_window.close_warning.lan_mode.title'))
        msg_box.setInformativeText(t('main_window.close_warning.lan_mode.detailed_message'))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def _is_network_running(self) -> bool:
        """检查是否有网络正在运行"""
        try:
            # 检查虚拟局域网页面的网络状态
            virtual_lan_page = self._get_virtual_lan_page()
            if virtual_lan_page and hasattr(virtual_lan_page, 'easytier_manager'):
                # 注意：is_running 是属性，不是方法
                easytier_running = virtual_lan_page.easytier_manager.is_running
                if easytier_running:
                    print("🌐 检测到EasyTier网络正在运行")
                    return True

            # 检查其他可能的网络状态
            # 可以在这里添加更多网络状态检查

            return False

        except Exception as e:
            print(f"❌ 网络状态检测失败: {e}")
            return False

    def _get_virtual_lan_page(self):
        """获取虚拟局域网页面实例"""
        try:
            if not self.app_instance:
                print("❌ 无法访问App实例")
                return None

            # 通过App实例获取虚拟局域网页面
            virtual_lan_page = self.app_instance.get_or_create_page("virtual_lan")

            # 检查页面是否有easytier_manager属性
            if virtual_lan_page and hasattr(virtual_lan_page, 'easytier_manager'):
                return virtual_lan_page
            else:
                print("❌ 虚拟局域网页面未找到或未初始化")
                return None

        except Exception as e:
            print(f"❌ 获取虚拟局域网页面失败: {e}")
            return None

    def _show_network_running_warning(self):
        """显示网络运行警告"""
        from PySide6.QtWidgets import QMessageBox

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(t('main_window.close_warning.title'))
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(t('main_window.close_warning.network_running.title'))
        msg_box.setInformativeText(t('main_window.close_warning.network_running.detailed_message'))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    # 注释：进程清理方法已移除
    # 现在软件关闭时不再自动清理进程，而是检查状态并提示用户手动停止

    # 注释：并行查找进程方法已移除

    # 注释：所有进程处理相关方法已移除
    # 包括：_find_process_by_tasklist, _find_processes_psutil_optimized,
    # _find_processes_fallback, _parallel_terminate_processes,
    # _parallel_force_kill_processes, _terminate_single_process, _force_kill_single_process

    # 注释：所有进程处理方法已移除，现在使用状态检查代替进程清理

    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border-top: 1px solid #313244;
                font-size: 12px;
            }
        """)

        # 局域网模式指示器（初始隐藏）
        self.lan_status_widget = None

    def update_lan_status_bar(self):
        """更新状态栏的局域网模式指示"""
        if self.is_lan_mode:
            if not self.lan_status_widget:
                from PySide6.QtWidgets import QLabel
                self.lan_status_widget = TLabel("main_window.lan_status.active")
                self.lan_status_widget.setStyleSheet("""
                    QLabel {
                        background-color: #a6e3a1;
                        color: #1e1e2e;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 13px;
                        margin: 2px;
                    }
                """)
                self.status_bar.addPermanentWidget(self.lan_status_widget)
        else:
            if self.lan_status_widget:
                self.status_bar.removeWidget(self.lan_status_widget)
                self.lan_status_widget.deleteLater()
                self.lan_status_widget = None
