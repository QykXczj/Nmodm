"""
虚拟局域网页面
基于EasyTier的P2P虚拟局域网功能
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTextEdit, QGroupBox,
                               QSplitter, QFrame, QGridLayout, QComboBox,
                               QCheckBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar, QTabWidget, QListWidget,
                               QListWidgetItem, QMenu, QAbstractItemView, QRadioButton)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QTextOption, QAction
import subprocess
import time
import re
import json
import base64
import os
import sys
import random
from pathlib import Path

from .base_page import BasePage
from ...utils.download_manager import DownloadManager
from ...utils.easytier_manager import EasyTierManager
from ...config.network_optimization_config import NetworkOptimizationConfig
from ...i18n.manager import TranslationManager, t

class PingWorker(QThread):
    """延迟检测工作线程"""
    ping_result = Signal(int, int)  # index, ping_ms

    def __init__(self, index: int, host: str):
        super().__init__()
        self.index = index
        self.host = host

    def run(self):
        """执行ping检测"""
        try:
            # 从URL中提取主机名
            host = self.host.replace("tcp://", "").replace("udp://", "").split(":")[0]

            # 执行ping命令，隐藏终端窗口
            result = subprocess.run(
                ["ping", "-n", "3", host],  # Windows ping命令
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏终端窗口
            )

            if result.returncode == 0:
                # 解析ping结果
                output = result.stdout
                # 查找平均延迟
                match = re.search(r'平均 = (\d+)ms', output)
                if not match:
                    # 英文版本
                    match = re.search(r'Average = (\d+)ms', output)

                if match:
                    ping_ms = int(match.group(1))
                    self.ping_result.emit(self.index, ping_ms)
                else:
                    self.ping_result.emit(self.index, -1)  # 解析失败
            else:
                self.ping_result.emit(self.index, -1)  # ping失败

        except Exception as e:
            print(f"Ping检测异常: {e}")
            self.ping_result.emit(self.index, -1)


class VirtualLanInitWorker(QThread):
    """虚拟局域网页面初始化工作线程"""

    progress_updated = Signal(str, str)  # message, msg_type
    initialization_complete = Signal(dict, dict, dict, dict)  # installation, tools, config, room
    initialization_error = Signal(str)  # error_message

    def __init__(self, page):
        super().__init__()
        self.page = page

    def run(self):
        """在后台线程中执行初始化"""
        try:
            # 1. 检查安装状态
            self.progress_updated.emit(t("virtual_lan_page.log.checking_installation"), "info")
            installation_result = self.page.check_installation_status_sync()

            # 2. 检查工具状态
            self.progress_updated.emit(t("virtual_lan_page.log.checking_tools"), "info")
            tools_result = self.page.check_tools_status_sync()

            # 3. 加载配置
            self.progress_updated.emit(t("virtual_lan_page.log.loading_config"), "info")
            config_result = self.page.load_config_sync()

            # 4. 检查房间状态
            self.progress_updated.emit(t("virtual_lan_page.log.checking_room_status"), "info")
            room_result = self.page.check_current_room_status_sync()

            # 发送完成信号
            self.initialization_complete.emit(
                installation_result, tools_result, config_result, room_result
            )

        except Exception as e:
            print(f"初始化工作线程异常: {e}")
            self.initialization_error.emit(str(e))

class VirtualLanPage(BasePage):
    """虚拟局域网页面"""

    # 🔧 添加线程安全的日志信号
    log_signal = Signal(str, str)  # message, msg_type

    def __init__(self, parent=None):
        super().__init__(t("virtual_lan_page.page_title"), parent)

        # 管理器
        self.download_manager = DownloadManager()
        self.easytier_manager = EasyTierManager()
        self.network_config = NetworkOptimizationConfig()

        # 工具管理器（使用单例）
        from src.utils.tool_manager import get_tool_manager
        self.tool_manager = get_tool_manager()

        # 创建虚拟的连接信息标签（用于存储状态，不显示）
        self.current_network_label = QLabel(t("virtual_lan_page.status.not_connected"))
        self.current_ip_label = QLabel(t("virtual_lan_page.status.not_assigned"))
        self.optimization_status_label = QLabel(t("virtual_lan_page.status.not_enabled"))

        # 连接信号
        self.easytier_manager.network_status_changed.connect(self.on_network_status_changed)
        self.easytier_manager.peer_list_updated.connect(self.on_peer_list_updated)
        self.easytier_manager.connection_info_updated.connect(self.on_connection_info_updated)
        self.easytier_manager.error_occurred.connect(self.on_error_occurred)

        # 🔧 连接线程安全的日志信号到UI更新槽
        self.log_signal.connect(self._update_log_ui)

        self.setup_content()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)

        # 标记页面未被用户访问
        self._user_visited = False
        self._initialization_completed = False

        # 显示初始化状态（但不执行耗时操作）
        self.show_initialization_status()

    def show_initialization_status(self):
        """显示初始化状态提示"""
        try:
            # 设置初始状态显示
            if hasattr(self, 'status_label'):
                self.status_label.setText(t("virtual_lan_page.status.click_to_init"))
                self.status_label.setStyleSheet("color: #89b4fa; font-weight: bold;")

            if hasattr(self, 'version_label'):
                self.version_label.setText(t("virtual_lan_page.status.waiting_init"))

            # 初始化提示已简化，不再显示技术细节

        except Exception as e:
            print(f"显示初始化状态失败: {e}")

    def ensure_initialization(self):
        """确保页面已初始化（仅在用户访问时执行）"""
        if not self._initialization_completed and not hasattr(self, '_initializing'):
            self._initializing = True
            print("🔍 用户访问虚拟局域网页面，开始初始化...")

            # 更新状态显示
            if hasattr(self, 'status_label'):
                self.status_label.setText(t("virtual_lan_page.status.initializing"))
                self.status_label.setStyleSheet("color: #f9e2af; font-weight: bold;")

            # 异步执行所有耗时的初始化操作（使用线程安全方式）
            self._schedule_async_initialization()
            self._user_visited = True

    def showEvent(self, event):
        """页面显示事件 - 用户切换到此页面时触发"""
        super().showEvent(event)
        # 确保页面已初始化
        self.ensure_initialization()

    def mousePressEvent(self, event):
        """鼠标点击事件 - 用户点击页面时触发"""
        super().mousePressEvent(event)
        # 确保页面已初始化
        self.ensure_initialization()

    def async_initialize_page(self):
        """异步初始化页面 - 使用QThread执行耗时操作"""
        try:
            # 创建初始化工作线程
            self.init_worker = VirtualLanInitWorker(self)
            self.init_worker.progress_updated.connect(self.on_init_progress)
            self.init_worker.initialization_complete.connect(self.on_initialization_complete)
            self.init_worker.initialization_error.connect(self.on_initialization_error)

            # 启动工作线程
            self.init_worker.start()

            # 延迟清理残余进程，防止干扰本次运行（不阻塞UI）
            self._schedule_cleanup_processes()

        except Exception as e:
            print(f"启动异步初始化失败: {e}")
            # 初始化错误简化，只在控制台输出技术细节

    def on_init_progress(self, message, msg_type):
        """初始化进度更新"""
        self.log_message(message, msg_type)

    def cleanup_residual_processes_async(self):
        """异步清理残余进程，防止阻塞UI"""
        try:
            print("🧹 开始异步清理残余进程...")
            # 后台清理过程简化，不显示技术细节

            # 使用线程池执行清理任务，避免阻塞UI
            from concurrent.futures import ThreadPoolExecutor

            def cleanup_task():
                """在后台线程中执行清理任务"""
                try:
                    # 清理各种残余进程
                    self._cleanup_easytier_processes()

                    # 使用新的管理员权限清理方法
                    print("🧹 使用管理员权限清理WinIPBroadcast进程...")
                    # 进程清理过程简化，不显示技术细节

                    from src.utils.process_cleaner import process_cleaner

                    def ui_callback(message, level):
                        """UI回调函数，将清理日志显示到界面（线程安全版本）"""
                        # 🔧 使用线程安全的log_message方法
                        try:
                            # 现在log_message内部会自动处理线程安全问题
                            self.log_message(message, level)
                        except Exception as e:
                            print(f"UI回调错误: {e}")

                    # 使用新的管理员权限清理方法
                    cleanup_success = process_cleaner.cleanup_winip_processes_with_admin_request(ui_callback)

                    if cleanup_success:
                        # 清理成功，静默处理
                        pass
                    else:
                        self.log_message(t("virtual_lan_page.log.backend_cleanup_partial"), "warning")

                    return cleanup_success
                except Exception as e:
                    print(f"❌ 后台清理失败: {e}")
                    self.log_message(t("virtual_lan_page.log.backend_cleanup_failed", error=str(e)), "error")
                    return False

            # 在线程池中执行清理
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(cleanup_task)

            # 使用线程安全的方式检查任务完成状态
            self._start_cleanup_monitoring(future, executor)

        except Exception as e:
            print(f"❌ 启动异步清理失败: {e}")
            self.log_message(t("virtual_lan_page.log.cleanup_startup_warning", error=str(e)), "warning")



    # 注释：原来的同步清理方法已移除，现在使用异步清理避免UI卡顿

    def _cleanup_easytier_processes(self):
        """清理EasyTier残余进程"""
        try:
            import psutil
            found_processes = []

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'easytier-core.exe':
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if found_processes:
                print(f"🔍 发现 {len(found_processes)} 个残余EasyTier进程")
                # EasyTier进程清理简化，不显示技术细节

                for proc in found_processes:
                    try:
                        print(f"  终止EasyTier进程 PID: {proc.pid}")
                        proc.terminate()
                        # 等待进程结束
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        # 强制终止
                        try:
                            proc.kill()
                            print(f"  强制终止EasyTier进程 PID: {proc.pid}")
                        except:
                            pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        print(f"  终止进程 {proc.pid} 失败: {e}")

                print("✅ EasyTier残余进程已清理")
            else:
                print("🔍 未发现EasyTier残余进程")

        except Exception as e:
            print(f"❌ 清理EasyTier进程失败: {e}")

    def _cleanup_winip_processes(self):
        """清理WinIPBroadcast残余进程"""
        try:
            import psutil
            import time
            
            # 第一次扫描
            found_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'winipbroadcast.exe':
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if found_processes:
                print(f"🔍 发现 {len(found_processes)} 个残余WinIPBroadcast进程，正在清理...")
                # WinIPBroadcast进程清理简化，不显示技术细节

                # 第一轮：尝试优雅终止
                for proc in found_processes:
                    try:
                        print(f"  优雅终止WinIPBroadcast进程 PID: {proc.pid}")
                        proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        print(f"  终止进程 {proc.pid} 失败: {e}")

                # 等待进程结束
                time.sleep(2)

                # 第二轮：强制终止仍在运行的进程
                remaining_processes = []
                for proc in found_processes:
                    try:
                        if proc.is_running():
                            remaining_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if remaining_processes:
                    print(f"  仍有 {len(remaining_processes)} 个进程运行，强制终止...")
                    for proc in remaining_processes:
                        try:
                            print(f"  强制终止WinIPBroadcast进程 PID: {proc.pid}")
                            proc.kill()
                            proc.wait(timeout=3)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        except Exception as e:
                            print(f"  强制终止进程 {proc.pid} 失败: {e}")

                # 第三次验证：检查是否还有残余进程
                time.sleep(1)
                final_check = []
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() == 'winipbroadcast.exe':
                            final_check.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if final_check:
                    print(f"⚠️ 仍有 {len(final_check)} 个WinIPBroadcast进程未能清理")
                    self.log_message(t("virtual_lan_page.log.winip_processes_detected", count=len(final_check)), "warning")
                    
                    # 尝试使用系统命令强制终止（静默方式）
                    try:
                        import subprocess
                        import sys
                        
                        if sys.platform == "win32":
                            # 检查是否有管理员权限
                            import ctypes
                            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                            
                            if is_admin:
                                # 有管理员权限，直接使用taskkill
                                result = subprocess.run(['taskkill', '/f', '/im', 'WinIPBroadcast.exe'], 
                                                      capture_output=True, text=True)
                                if result.returncode == 0:
                                    print("✅ 使用管理员权限成功清理WinIPBroadcast进程")
                                    # 清理成功，静默处理
                                else:
                                    print(f"⚠️ 管理员权限清理失败: {result.stderr}")
                                    self.log_message(t("virtual_lan_page.log.backend_cleanup_partial_admin"), "warning")
                            else:
                                # 没有管理员权限，静默处理，不弹窗
                                print("⚠️ WinIPBroadcast进程以管理员权限运行，当前权限无法清理")
                                self.log_message(t("virtual_lan_page.log.winip_admin_required"), "warning")
                                self.log_message(t("virtual_lan_page.log.admin_restart_tip"), "info")
                        else:
                            # 非Windows系统
                            result = subprocess.run(['pkill', '-f', 'WinIPBroadcast'], 
                                                  capture_output=True, text=True)
                            if result.returncode == 0:
                                print("✅ 使用pkill成功清理WinIPBroadcast进程")
                                # 清理成功，静默处理
                            else:
                                print(f"⚠️ pkill执行失败: {result.stderr}")
                                self.log_message(t("virtual_lan_page.log.backend_cleanup_partial_admin"), "warning")
                                
                    except Exception as e:
                        print(f"⚠️ 系统命令清理失败: {e}")
                        self.log_message(t("virtual_lan_page.log.backend_cleanup_partial_admin"), "warning")
                else:
                    print("✅ 所有WinIPBroadcast进程已成功清理")
                    # 清理成功，静默处理
            else:
                print("🔍 未发现WinIPBroadcast残余进程")

        except Exception as e:
            print(f"❌ 清理WinIPBroadcast进程失败: {e}")
            self.log_message(t("virtual_lan_page.log.process_cleanup_failed", error=str(e)), "error")

    # KCP进程清理功能已移除，因为EasyTier自带KCP支持
    
    def setup_content(self):
        """设置页面内容"""
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：配置和控制区域
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)

        # 右侧：状态和日志区域
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([500, 400])

        # 禁止用户拖动调整
        splitter.setChildrenCollapsible(False)  # 禁止折叠
        splitter.handle(1).setEnabled(False)    # 禁用拖动手柄

        # 添加到BasePage的布局中
        self.add_content(splitter)

    def create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # EasyTier安装状态
        self.installation_group = self.create_installation_group()
        layout.addWidget(self.installation_group)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget {
                background-color: transparent;
                border: none;
            }
            QTabWidget::pane {
                border: 2px solid #313244;
                border-radius: 8px;
                background-color: #1e1e2e;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #45475a;
            }
        """)

        # 创建"房间配置"选项卡
        room_tab = QWidget()
        room_layout = QVBoxLayout(room_tab)
        room_layout.setContentsMargins(10, 15, 10, 10)
        room_layout.setSpacing(15)

        # 房间配置
        self.room_group = self.create_room_group()
        room_layout.addWidget(self.room_group)
        room_layout.addStretch()

        # 创建"房间列表"选项卡
        room_list_tab = QWidget()
        room_list_layout = QVBoxLayout(room_list_tab)
        room_list_layout.setContentsMargins(10, 15, 10, 10)
        room_list_layout.setSpacing(15)

        # 房间列表
        self.room_list_group = self.create_room_list_group()
        room_list_layout.addWidget(self.room_list_group)
        # 减少拉伸空间，让列表占用更多空间

        # 创建"房间信息"选项卡
        create_tab = QWidget()
        create_layout = QVBoxLayout(create_tab)
        create_layout.setContentsMargins(10, 15, 10, 10)
        create_layout.setSpacing(15)

        # 网络配置
        self.network_config_group = self.create_network_config_group()
        create_layout.addWidget(self.network_config_group)

        # 创建房间按钮区域
        self.create_room_section = self.create_room_section()
        create_layout.addWidget(self.create_room_section)

        create_layout.addStretch()

        # 创建"高级设置"选项卡
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(10, 15, 10, 10)
        advanced_layout.setSpacing(15)

        # 高级设置
        self.advanced_group = self.create_advanced_group()
        advanced_layout.addWidget(self.advanced_group)
        advanced_layout.addStretch()

        # 创建"公益服务器"选项卡
        servers_tab = QWidget()
        servers_layout = QVBoxLayout(servers_tab)
        servers_layout.setContentsMargins(10, 15, 10, 10)
        servers_layout.setSpacing(15)

        # 公益服务器列表
        self.servers_group = self.create_servers_group()
        servers_layout.addWidget(self.servers_group)
        servers_layout.addStretch()

        # 添加选项卡
        self.tab_widget.addTab(room_list_tab, t("virtual_lan_page.tab.room_list"))
        self.tab_widget.addTab(room_tab, t("virtual_lan_page.tab.add_room"))
        self.tab_widget.addTab(create_tab, t("virtual_lan_page.tab.room_info"))
        self.tab_widget.addTab(advanced_tab, t("virtual_lan_page.tab.advanced"))
        self.tab_widget.addTab(servers_tab, t("virtual_lan_page.tab.servers"))

        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 添加选项卡控件到主布局
        layout.addWidget(self.tab_widget)

        # 网络控制独立在选项卡外部
        self.control_group = self.create_control_group()
        layout.addWidget(self.control_group)

        layout.addStretch()
        return widget

    def on_tab_changed(self, index: int):
        """标签页切换事件处理"""
        try:
            # 获取当前标签页的文本
            current_tab_text = self.tab_widget.tabText(index)

            # 如果切换到"公益服务器"标签页(索引为4)
            if index == 4:  # 使用索引而不是文本,避免翻译问题
                # 如果还未开始延迟检测，则启动
                if not getattr(self, 'ping_detection_started', False):
                    print(f"🔍 用户切换到{current_tab_text}标签页，开始延迟检测...")
                    self.start_ping_detection()
                    self.ping_detection_started = True
                else:
                    print(f"🔍 用户切换到{current_tab_text}标签页，延迟检测已在进行中")
            else:
                # 切换到其他标签页时，立即停止延迟检测
                if getattr(self, 'ping_detection_started', False):
                    print(f"🔍 用户切换到{current_tab_text}标签页，立即停止延迟检测")
                    self.stop_ping_detection()
                    self.ping_detection_started = False

        except Exception as e:
            print(f"❌ 标签页切换处理失败: {e}")

    def register_page_leave_handler(self, retry_count=0):
        """注册页面离开事件处理"""
        try:
            # 获取主窗口的App实例
            main_window = self.window()
            if main_window and hasattr(main_window, 'app_instance'):
                app_instance = main_window.app_instance
                if app_instance and hasattr(app_instance, 'sidebar'):
                    # 连接侧边栏的页面切换信号
                    app_instance.sidebar.page_changed.connect(self.on_page_changed)
                    print("✅ 已注册页面离开事件处理")
                    return True
                else:
                    if retry_count < 3:  # 最多重试3次
                        print(f"⚠️ App实例或侧边栏未就绪，{2}秒后重试 ({retry_count + 1}/3)")
                        self._schedule_retry_register(retry_count + 1)
                    else:
                        print("⚠️ 无法获取App实例或侧边栏（已达最大重试次数）")
            else:
                if retry_count < 3:  # 最多重试3次
                    print(f"⚠️ 主窗口或App实例未就绪，{2}秒后重试 ({retry_count + 1}/3)")
                    self._schedule_retry_register(retry_count + 1)
                else:
                    print("⚠️ 无法获取主窗口或App实例（已达最大重试次数）")
        except Exception as e:
            print(f"❌ 注册页面离开事件处理失败: {e}")
            return False

    def _schedule_retry_register(self, retry_count):
        """线程安全的重试调度"""
        import threading
        import time

        def retry_task():
            try:
                time.sleep(2)  # 等待2秒
                self.register_page_leave_handler(retry_count)
            except Exception as e:
                print(f"重试注册失败: {e}")

        retry_thread = threading.Thread(target=retry_task, daemon=True)
        retry_thread.start()

    def on_page_changed(self, page_id: str):
        """处理页面切换事件"""
        try:
            # 如果用户离开虚拟局域网页面，停止延迟检测
            if page_id != "virtual_lan" and getattr(self, 'ping_detection_started', False):
                print(f"🔍 用户离开虚拟局域网页面，切换到{page_id}页面，立即停止延迟检测")
                self.stop_ping_detection()
                self.ping_detection_started = False
        except Exception as e:
            print(f"❌ 页面切换事件处理失败: {e}")

    def create_installation_group(self) -> QGroupBox:
        """创建安装状态组"""
        group = QGroupBox(t("virtual_lan_page.section.installation"))
        self.installation_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)
        layout = QVBoxLayout(group)

        # 状态和版本信息水平布局
        info_layout = QHBoxLayout()

        # 状态显示
        status_container = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        self.status_title_label = QLabel(t("virtual_lan_page.label.status"))
        self.status_title_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.status_label = QLabel(t("virtual_lan_page.status.checking"))
        self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")

        status_layout.addWidget(self.status_title_label)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_container.setLayout(status_layout)

        # 版本信息
        version_container = QWidget()
        version_layout = QHBoxLayout()
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(8)

        self.version_title_label = QLabel(t("virtual_lan_page.label.version"))
        self.version_title_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.version_label = QLabel(t("virtual_lan_page.status.unknown"))
        self.version_label.setStyleSheet("color: #bac2de;")

        version_layout.addWidget(self.version_title_label)
        version_layout.addWidget(self.version_label)
        version_layout.addStretch()
        version_container.setLayout(version_layout)

        # 添加到水平布局
        info_layout.addWidget(status_container)
        info_layout.addWidget(version_container)
        layout.addLayout(info_layout)
        

        
        return group
    
    def create_network_config_group(self) -> QGroupBox:
        """创建网络配置组"""
        group = QGroupBox(t("virtual_lan_page.section.network_config"))
        self.network_config_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
            }
            QLineEdit {
                background-color: #1e1e2e;
                border: 2px solid #313244;
                border-radius: 4px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QComboBox {
                background-color: #1e1e2e;
                border: 2px solid #313244;
                border-radius: 4px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cdd6f4;
            }
        """)
        layout = QGridLayout(group)
        
        # 房间名称
        self.room_name_label = QLabel(t("virtual_lan_page.label.room_name"))
        layout.addWidget(self.room_name_label, 0, 0)
        self.network_name_edit = QLineEdit()
        self.network_name_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_name"))
        layout.addWidget(self.network_name_edit, 0, 1)

        # 玩家名称
        self.player_name_label = QLabel(t("virtual_lan_page.label.player_name"))
        layout.addWidget(self.player_name_label, 1, 0)

        # 玩家名称容器
        player_name_container = QWidget()
        player_name_layout = QHBoxLayout()
        player_name_layout.setContentsMargins(0, 0, 0, 0)
        player_name_layout.setSpacing(8)

        self.machine_id_edit = QLineEdit()
        self.machine_id_edit.setPlaceholderText(t("virtual_lan_page.placeholder.player_name_unique"))
        player_name_layout.addWidget(self.machine_id_edit)

        # 随机生成按钮
        self.random_name_btn = QPushButton("🎲")
        self.random_name_btn.setFixedSize(32, 32)
        self.random_name_btn.setToolTip(t("virtual_lan_page.tooltip.random_name"))
        self.random_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 4px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.random_name_btn.clicked.connect(self.generate_random_name)
        player_name_layout.addWidget(self.random_name_btn)

        player_name_container.setLayout(player_name_layout)
        layout.addWidget(player_name_container, 1, 1)

        # 玩家名称提醒（跨列显示）
        self.player_name_hint_label = QLabel(t("virtual_lan_page.hint.player_name_unique"))
        self.player_name_hint_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(249, 226, 175, 0.1);
                border: 1px solid rgba(249, 226, 175, 0.3);
                border-radius: 4px;
                margin-top: 2px;
                margin-left: 0px;
            }
        """)
        layout.addWidget(self.player_name_hint_label, 2, 1)  # 放在第2行第1列，跨列显示

        # 房间密码
        self.room_password_label = QLabel(t("virtual_lan_page.label.room_password"))
        layout.addWidget(self.room_password_label, 3, 0)

        # 房间密码容器
        password_container = QWidget()
        password_layout = QHBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(8)

        self.network_secret_edit = QLineEdit()
        self.network_secret_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_password"))
        self.network_secret_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.network_secret_edit)

        # 密码可见性切换按钮
        self.password_visibility_btn = QPushButton("👁")
        self.password_visibility_btn.setFixedSize(32, 32)
        self.password_visibility_btn.setToolTip(t("virtual_lan_page.tooltip.toggle_password"))
        self.password_visibility_btn.setCheckable(True)
        self.password_visibility_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                border: none;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton:checked:hover {
                background-color: #74c7ec;
            }
        """)
        self.password_visibility_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.password_visibility_btn)

        password_container.setLayout(password_layout)
        layout.addWidget(password_container, 3, 1)

        # 本机IP配置
        self.local_ip_label = QLabel(t("virtual_lan_page.label.local_ip"))
        layout.addWidget(self.local_ip_label, 4, 0)

        ip_container = QWidget()
        ip_layout = QHBoxLayout()
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.setSpacing(10)

        # DHCP复选框
        self.dhcp_check = QCheckBox(t("virtual_lan_page.checkbox.dhcp"))
        self.dhcp_check.setChecked(True)  # 默认启用DHCP
        self.dhcp_check.setStyleSheet("""
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #45475a;
                background-color: #1e1e2e;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
        """)
        self.dhcp_check.stateChanged.connect(self.on_dhcp_changed)
        ip_layout.addWidget(self.dhcp_check)

        # 手动IP输入框
        self.peer_ip_edit = QLineEdit("10.126.126.1")
        self.peer_ip_edit.setPlaceholderText(t("virtual_lan_page.placeholder.auto_ip"))
        self.peer_ip_edit.setEnabled(False)  # 默认禁用，因为DHCP已启用
        self.peer_ip_edit.setMaximumWidth(150)
        ip_layout.addWidget(self.peer_ip_edit)

        ip_layout.addStretch()  # 添加弹性空间
        ip_container.setLayout(ip_layout)
        layout.addWidget(ip_container, 4, 1)

        # 公共服务器（固定值）
        self.public_server_label = QLabel(t("virtual_lan_page.label.public_server"))
        layout.addWidget(self.public_server_label, 5, 0)
        self.external_node_label = QLabel("tcp://public.easytier.top:11010")
        self.external_node_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 6px 8px;
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.external_node_label, 5, 1)
        
        return group

    def create_room_list_group(self) -> QGroupBox:
        """创建房间列表组"""
        group = QGroupBox(t("virtual_lan_page.section.room_list"))
        self.room_list_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 房间列表控件
        self.room_list_widget = QListWidget()
        self.room_list_widget.setMinimumHeight(200)  # 设置最小高度
        self.room_list_widget.setMaximumHeight(300)  # 设置最大高度
        self.room_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 2px;
                margin: 6px 2px;
                background-color: transparent;
                border: none;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
        """)

        # 禁用默认选择，使用自定义单选按钮
        self.room_list_widget.setSelectionMode(QAbstractItemView.NoSelection)

        # 启用右键菜单
        self.room_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.room_list_widget.customContextMenuRequested.connect(self.show_room_context_menu)

        layout.addWidget(self.room_list_widget)

        # 刷新按钮
        refresh_layout = QHBoxLayout()
        self.refresh_room_list_btn = QPushButton(t("virtual_lan_page.button.refresh_list"))
        self.refresh_room_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        self.refresh_room_list_btn.clicked.connect(self.refresh_room_list_widget)
        refresh_layout.addWidget(self.refresh_room_list_btn)

        # 提示信息
        self.room_right_click_hint_label = QLabel(t("virtual_lan_page.hint.room_right_click"))
        self.room_right_click_hint_label.setStyleSheet("""
            QLabel {
                color: #74c7ec;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(116, 199, 236, 0.1);
                border: 1px solid rgba(116, 199, 236, 0.3);
                border-radius: 4px;
                margin-left: 8px;
                max-height: 24px;
            }
        """)
        refresh_layout.addWidget(self.room_right_click_hint_label)
        refresh_layout.addStretch()

        layout.addLayout(refresh_layout)

        # 初始化房间列表
        self.refresh_room_list_widget()

        return group

    def create_room_section(self) -> QGroupBox:
        """创建房间按钮区域"""
        group = QGroupBox(t("virtual_lan_page.section.create_room"))
        self.create_room_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #a6e3a1;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: rgba(166, 227, 161, 0.05);
                max-height: 80px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #a6e3a1;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 8)

        # 创建房间按钮和提示
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 创建房间按钮
        self.create_room_btn = QPushButton(t("virtual_lan_page.button.create_room"))
        self.create_room_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #7fb069;
            }
        """)
        self.create_room_btn.clicked.connect(self.create_room)
        button_layout.addWidget(self.create_room_btn)

        # 小白提示
        self.beginner_tip_hint_label = QLabel(t("virtual_lan_page.hint.beginner_tip"))
        self.beginner_tip_hint_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(249, 226, 175, 0.1);
                border: 1px solid rgba(249, 226, 175, 0.3);
                border-radius: 4px;
                margin-left: 8px;
                max-height: 24px;
            }
        """)
        button_layout.addWidget(self.beginner_tip_hint_label)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        return group

    def create_room_group(self) -> QGroupBox:
        """创建添加房间组"""
        group = QGroupBox(t("virtual_lan_page.section.add_room"))
        self.add_room_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(15)

        # 房间代码输入区域
        join_group = QGroupBox(t("virtual_lan_page.section.join_by_code"))
        self.join_group = join_group
        join_group.setStyleSheet("""
            QGroupBox {
                color: #89b4fa;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: rgba(137, 180, 250, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #89b4fa;
            }
        """)
        join_layout = QVBoxLayout(join_group)
        join_layout.setSpacing(10)

        # 房间代码输入
        self.room_code_label = QLabel(t("virtual_lan_page.label.room_code"))
        self.room_code_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 13px; background-color: transparent;")
        join_layout.addWidget(self.room_code_label)
        self.room_code_edit = QLineEdit()
        self.room_code_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_code"))
        self.room_code_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        join_layout.addWidget(self.room_code_edit)

        # 玩家名称输入
        self.join_player_name_label = QLabel(t("virtual_lan_page.label.player_name"))
        self.join_player_name_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 13px; background-color: transparent;")
        join_layout.addWidget(self.join_player_name_label)

        # 玩家名称输入行（包含输入框和随机生成按钮）
        player_name_layout = QHBoxLayout()
        self.join_player_name_edit = QLineEdit()
        self.join_player_name_edit.setPlaceholderText(t("virtual_lan_page.placeholder.join_player_name"))
        self.join_player_name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        player_name_layout.addWidget(self.join_player_name_edit)

        # 随机生成按钮
        random_name_btn = QPushButton("🎲")
        random_name_btn.setToolTip(t("virtual_lan_page.tooltip.random_name"))
        random_name_btn.setStyleSheet("""
            QPushButton {
                background-color: #74c7ec;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
            }
            QPushButton:hover {
                background-color: #89dceb;
            }
            QPushButton:pressed {
                background-color: #5fb3d4;
            }
        """)
        random_name_btn.clicked.connect(lambda checked=False: self.join_player_name_edit.setText(self.generate_random_player_name()))
        player_name_layout.addWidget(random_name_btn)

        join_layout.addLayout(player_name_layout)

        # 加入按钮
        join_btn_layout = QHBoxLayout()
        self.join_room_btn = QPushButton(t("virtual_lan_page.button.add_room"))
        self.join_room_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #6c7086;
            }
        """)
        self.join_room_btn.clicked.connect(self.join_room)
        join_btn_layout.addWidget(self.join_room_btn)

        self.join_hint_label = QLabel(t("virtual_lan_page.hint.parse_room_code"))
        self.join_hint_label.setStyleSheet("color: #bac2de; font-size: 11px; background-color: transparent;")
        join_btn_layout.addWidget(self.join_hint_label)
        join_btn_layout.addStretch()

        join_layout.addLayout(join_btn_layout)
        layout.addWidget(join_group)

        return group

    def create_servers_group(self) -> QGroupBox:
        """创建公益服务器组"""
        group = QGroupBox(t("virtual_lan_page.section.servers"))
        self.servers_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #1e1e2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 公益服务器列表定义（默认全部未选中）
        self.server_list = [
            {"url": "tcp://gz.minebg.top:11010", "name": "广州", "enabled": False},
            {"url": "tcp://119.23.65.180:11010", "name": "深圳", "enabled": False},
            {"url": "tcp://ah.nkbpal.cn:11010", "name": "合肥", "enabled": False},
            {"url": "tcp://39.108.52.138:11010", "name": "深圳", "enabled": False},
            {"url": "tcp://8.148.29.206:11010", "name": "武汉", "enabled": False},
            {"url": "tcp://turn.js.629957.xyz:11012", "name": "宿迁", "enabled": False},
            {"url": "tcp://sh.993555.xyz:11010", "name": "上海", "enabled": False},
            {"url": "tcp://et-hk.clickor.click:11010", "name": "香港", "enabled": False},
        ]

        # 创建服务器选择控件
        self.server_checkboxes = []
        self.server_ping_labels = []

        for i, server in enumerate(self.server_list):
            # 服务器行容器
            server_row = QWidget()
            server_layout = QHBoxLayout()
            server_layout.setContentsMargins(0, 0, 0, 0)
            server_layout.setSpacing(12)

            # 复选框
            checkbox = QCheckBox(f"{server['name']} ({server['url']})")
            checkbox.setChecked(server['enabled'])
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #cdd6f4;
                    font-size: 12px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 2px solid #6c7086;
                    background-color: #313244;
                }
                QCheckBox::indicator:checked {
                    background-color: #89b4fa;
                    border-color: #89b4fa;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0iIzFlMWUyZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
                }
                QCheckBox::indicator:hover {
                    border-color: #89b4fa;
                }
            """)
            checkbox.toggled.connect(lambda checked, idx=i: self.on_server_toggled(idx, checked))
            self.server_checkboxes.append(checkbox)
            server_layout.addWidget(checkbox)

            # 延迟显示标签
            ping_label = QLabel(t("virtual_lan_page.status.detecting"))
            ping_label.setStyleSheet("""
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    padding: 2px 6px;
                    background-color: rgba(249, 226, 175, 0.1);
                    border: 1px solid rgba(249, 226, 175, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }
            """)
            ping_label.setAlignment(Qt.AlignCenter)
            self.server_ping_labels.append(ping_label)
            server_layout.addWidget(ping_label)

            server_layout.addStretch()
            server_row.setLayout(server_layout)
            layout.addWidget(server_row)

        # 添加说明
        self.server_selection_hint_label = QLabel(t("virtual_lan_page.hint.server_selection"))
        self.server_selection_hint_label.setStyleSheet("""
            QLabel {
                color: #74c7ec;
                font-size: 11px;
                font-style: italic;
                padding: 6px 8px;
                background-color: rgba(116, 199, 236, 0.1);
                border: 1px solid rgba(116, 199, 236, 0.3);
                border-radius: 4px;
                margin-top: 8px;
            }
        """)
        layout.addWidget(self.server_selection_hint_label)

        # 不在这里启动延迟检测，改为在用户点击"公益服务器"标签时启动
        # self.start_ping_detection()  # 移除自动启动

        # 添加延迟检测状态标记
        self.ping_detection_started = False

        return group

    def on_server_toggled(self, index: int, checked: bool):
        """服务器选择状态变化"""
        self.server_list[index]['enabled'] = checked
        # 保存配置
        self.save_config()

    def start_ping_detection(self):
        """启动延迟检测"""
        # 防止重复启动
        if hasattr(self, 'ping_workers') and self.ping_workers:
            print("🔍 延迟检测已在进行中，跳过重复启动")
            return

        print("🚀 开始公益服务器延迟检测...")
        self.ping_workers = []

        for i, server in enumerate(self.server_list):
            # 创建ping检测工作线程
            worker = PingWorker(i, server['url'])
            worker.ping_result.connect(self.on_ping_result)
            self.ping_workers.append(worker)
            worker.start()

    def stop_ping_detection(self):
        """停止延迟检测"""
        if hasattr(self, 'ping_workers') and self.ping_workers:
            print("🛑 停止公益服务器延迟检测...")
            for worker in self.ping_workers:
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(1000)  # 等待最多1秒
            self.ping_workers = []

    def on_ping_result(self, index: int, ping_ms: int):
        """处理ping检测结果"""
        if index >= len(self.server_ping_labels):
            return

        # 保存延迟值供语言切换时使用
        if not hasattr(self, 'server_ping_values'):
            self.server_ping_values = {}
        self.server_ping_values[index] = ping_ms

        ping_label = self.server_ping_labels[index]

        if ping_ms == -1:
            # ping失败
            ping_label.setText(t("virtual_lan_page.status.timeout"))
            ping_label.setStyleSheet("""
                QLabel {
                    color: #6c7086;
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba(108, 112, 134, 0.1);
                    border: 1px solid rgba(108, 112, 134, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }
            """)
            ping_label.setToolTip(t("virtual_lan_page.tooltip.connection_timeout"))
        else:
            # 根据延迟设置颜色和状态
            if ping_ms < 50:
                color = "#a6e3a1"  # 绿色 - 优秀
                status = t("virtual_lan_page.ping_status.excellent")
            elif ping_ms < 100:
                color = "#f9e2af"  # 黄色 - 良好
                status = t("virtual_lan_page.ping_status.good")
            elif ping_ms < 150:
                color = "#fab387"  # 橙色 - 一般
                status = t("virtual_lan_page.ping_status.fair")
            else:
                color = "#f38ba8"  # 红色 - 较差
                status = t("virtual_lan_page.ping_status.poor")

            ping_label.setText(f"{ping_ms}ms")
            ping_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 11px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-weight: bold;
                    padding: 2px 6px;
                    background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
                    border: 1px solid rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3);
                    border-radius: 3px;
                    min-width: 60px;
                }}
            """)
            ping_label.setToolTip(t("virtual_lan_page.tooltip.server_latency").format(ping_ms=ping_ms, status=status))

    def check_current_room_status(self):
        """检查并提醒当前房间状态"""
        try:
            # 获取当前配置
            current_config = self.easytier_manager.get_config()
            current_room_name = current_config.get("network_name", "").strip()
            current_hostname = current_config.get("hostname", "").strip()

            if current_room_name:
                # 检查是否存在对应的房间配置文件
                rooms_dir = self.get_rooms_dir()
                room_file = rooms_dir / f"{current_room_name}.json"

                if room_file.exists():
                    # 房间配置文件存在
                    if not current_hostname:
                        self.log_message(t("virtual_lan_page.log.player_name_empty", room_name=current_room_name), "warning")
                else:
                    # 房间配置文件不存在，可能是手动配置的
                    if not current_hostname:
                        self.log_message(t("virtual_lan_page.log.player_name_empty", room_name=current_room_name), "warning")
            else:
                # 没有配置房间名称
                self.log_message(t("virtual_lan_page.log.create_room_first"), "warning")

        except Exception as e:
            print(f"检查房间状态失败: {e}")

    def generate_random_player_name(self) -> str:
        """生成随机玩家名称"""
        adjectives = [
            "勇敢的", "聪明的", "快乐的", "神秘的", "强大的", "优雅的", "敏捷的", "智慧的",
            "幸运的", "冷静的", "热情的", "友善的", "机智的", "坚强的", "温柔的", "活泼的"
        ]

        nouns = [
            "哈基追", "哈基法", "哈基蜗", "哈基弓", "无赖大人", "女爵", "神鹰哥", "尬弹哥", "铁眼大人"
        ]

        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        number = random.randint(100, 999)

        return f"{adjective}{noun}{number}"

    def log_message(self, message: str, msg_type: str = "info"):
        """线程安全的日志显示方法"""
        # 🔧 线程安全检测和自动路由
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        current_thread = QThread.currentThread()
        main_thread = QApplication.instance().thread() if QApplication.instance() else None
        is_main_thread = current_thread == main_thread

        # 🔧 线程安全路由：根据线程类型选择处理方式
        if is_main_thread:
            # 在主线程，直接更新UI
            self._update_log_ui(message, msg_type)
        else:
            # 在后台线程，发射信号
            self.log_signal.emit(message, msg_type)

    def _update_log_ui(self, message: str, msg_type: str = "info"):
        """实际的UI更新方法（仅在主线程调用）"""
        if hasattr(self, 'log_text'):
            timestamp = time.strftime("%H:%M:%S")

            if msg_type == "error":
                color = "#f38ba8"  # 红色
                prefix = "❌"
            elif msg_type == "warning":
                color = "#f9e2af"  # 黄色
                prefix = "⚠️"
            elif msg_type == "success":
                color = "#a6e3a1"  # 绿色
                prefix = "✅"
            else:
                color = "#cdd6f4"  # 默认颜色
                prefix = "ℹ️"

            log_entry = f'<span style="color: {color};">[{timestamp}] {prefix} {message}</span>'
            self.log_text.append(log_entry)

    def refresh_room_list_widget(self):
        """刷新房间列表控件"""
        self.room_list_widget.clear()
        self.room_radio_buttons = {}  # 存储房间名到单选按钮的映射
        rooms_dir = self.get_rooms_dir()

        # 获取当前加载的房间
        current_config = self.easytier_manager.get_config()
        current_room_name = current_config.get("network_name", "")

        if rooms_dir.exists():
            for room_file in rooms_dir.glob("*.json"):
                try:
                    with open(room_file, 'r', encoding='utf-8') as f:
                        room_config = json.load(f)

                    room_name = room_config.get("network_name", room_file.stem)

                    # 获取玩家名称（优先使用hostname，然后从元数据获取）
                    player_name = room_config.get("hostname", "未知玩家")
                    if not player_name or player_name == "未知玩家":
                        # 兼容旧格式：从元数据或旧字段获取
                        room_meta = room_config.get("_room_meta", {})
                        player_name = (room_meta.get("created_by") or
                                     room_meta.get("joined_by") or
                                     room_config.get("created_by") or
                                     room_config.get("joined_by") or
                                     "未知玩家")

                    # 创建容器widget作为真正的边框容器
                    container_widget = QWidget()
                    container_widget.setMinimumHeight(32)  # 减小高度：44 → 32
                    container_widget.setStyleSheet("""
                        QWidget {
                            background-color: transparent;
                            border: 1px solid rgba(69, 71, 90, 0.5);
                            border-radius: 6px;
                        }
                        QWidget:hover {
                            background-color: rgba(137, 180, 250, 0.1);
                            border-color: rgba(137, 180, 250, 0.4);
                        }
                    """)

                    # 在容器内创建布局
                    container_layout = QHBoxLayout(container_widget)
                    container_layout.setContentsMargins(8, 4, 8, 4)  # 减小内边距：12,8,12,8 → 8,4,8,4
                    container_layout.setSpacing(10)  # 减小间距：15 → 10
                    container_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐

                    # 单选框（禁用点击功能）
                    radio_button = QRadioButton()
                    radio_button.setEnabled(False)  # 禁用交互
                    radio_button.setStyleSheet("""
                        QRadioButton {
                            background-color: transparent;
                            spacing: 0px;
                        }
                        QRadioButton::indicator {
                            width: 18px;
                            height: 18px;
                            border-radius: 9px;
                            border: 2px solid #6c7086;
                            background-color: #1e1e2e;
                            margin: 2px;
                        }
                        QRadioButton::indicator:checked {
                            background-color: #89b4fa;
                            border-color: #89b4fa;
                        }
                        QRadioButton::indicator:disabled {
                            border-color: #6c7086;
                            background-color: #1e1e2e;
                        }
                        QRadioButton::indicator:checked:disabled {
                            background-color: #89b4fa;
                            border-color: #89b4fa;
                        }
                    """)

                    # 检查是否为当前加载的房间（需要临时启用才能设置状态）
                    if room_name == current_room_name:
                        radio_button.setEnabled(True)  # 临时启用
                        radio_button.setChecked(True)
                        radio_button.setEnabled(False)  # 重新禁用

                    # 不连接点击事件，因为单选框已被禁用
                    self.room_radio_buttons[room_name] = radio_button  # 使用房间名作为键
                    container_layout.addWidget(radio_button)

                    # 房间名称
                    room_label = QLabel(room_name)
                    room_label.setStyleSheet("""
                        QLabel {
                            color: #cdd6f4;
                            font-weight: bold;
                            font-size: 13px;
                            background-color: transparent;
                            padding: 2px 4px;
                        }
                    """)
                    room_label.setMinimumWidth(120)
                    container_layout.addWidget(room_label)

                    # 玩家名称
                    player_label = QLabel(player_name)
                    player_label.setStyleSheet("""
                        QLabel {
                            color: #bac2de;
                            font-size: 12px;
                            background-color: transparent;
                            padding: 2px 4px;
                        }
                    """)
                    container_layout.addWidget(player_label)

                    container_layout.addStretch()

                    # 创建列表项
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, room_file.stem)  # 存储房间名用于操作
                    item.setSizeHint(container_widget.sizeHint())

                    self.room_list_widget.addItem(item)
                    self.room_list_widget.setItemWidget(item, container_widget)

                except Exception as e:
                    print(f"读取房间配置失败 {room_file}: {e}")

    def show_room_context_menu(self, position):
        """显示房间右键菜单"""
        item = self.room_list_widget.itemAt(position)
        if item is None:
            return

        room_name = item.data(Qt.UserRole)
        if not room_name:
            return

        # 创建右键菜单
        menu = QMenu(self.room_list_widget)
        menu.setStyleSheet("""
            QMenu {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 4px;
                margin: 1px;
            }
            QMenu::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)

        # 加载房间动作
        load_action = QAction(t("virtual_lan_page.menu.load_room"), menu)
        load_action.triggered.connect(lambda checked=False: self.load_room_from_list(room_name))
        menu.addAction(load_action)

        menu.addSeparator()  # 分隔线

        # 分享房间动作
        share_action = QAction(t("virtual_lan_page.menu.share_room"), menu)
        share_action.triggered.connect(lambda checked=False: self.share_room_from_list(room_name))
        menu.addAction(share_action)

        # 删除房间动作
        delete_action = QAction(t("virtual_lan_page.menu.delete_room"), menu)
        delete_action.triggered.connect(lambda checked=False: self.delete_room_from_list(room_name))
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec(self.room_list_widget.mapToGlobal(position))

    def load_room_from_list(self, room_name: str):
        """从列表加载房间配置"""
        try:
            # 检查网络运行状态
            if self.easytier_manager.is_running:
                current_network_name = self.network_name_edit.text().strip()
                if current_network_name != room_name:
                    self.log_message(t("virtual_lan_page.log.room_load_network_running", room_name=room_name), "error")
                    return
                else:
                    # 如果是当前房间，允许重新加载（刷新配置）
                    self.log_message(t("virtual_lan_page.log.room_reload_config", room_name=room_name), "info")

            # 读取房间配置
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if not room_file.exists():
                self.log_message(t("virtual_lan_page.log.room_config_not_exist", room_name=room_name), "error")
                return

            with open(room_file, 'r', encoding='utf-8') as f:
                room_config = json.load(f)

            # 获取玩家名称
            player_name = room_config.get("hostname", "未知玩家")
            if not player_name or player_name == "未知玩家":
                # 兼容旧格式
                room_meta = room_config.get("_room_meta", {})
                player_name = (room_meta.get("created_by") or
                             room_meta.get("joined_by") or
                             room_config.get("created_by") or
                             room_config.get("joined_by") or
                             "未知玩家")

            # 检查并更新房间配置文件（添加缺失的字段）
            updated_config = self.update_room_config_compatibility(room_config)
            if updated_config != room_config:
                # 配置已更新，保存回文件
                with open(room_file, 'w', encoding='utf-8') as f:
                    json.dump(updated_config, f, indent=2, ensure_ascii=False)
                self.log_message(t("virtual_lan_page.log.room_config_format_updated", room_name=room_name), "info")
                room_config = updated_config

            # 应用房间配置到界面
            self.apply_room_config(room_config, player_name)

            # 选中当前房间的单选按钮（需要临时启用才能设置状态）
            for name, radio_button in self.room_radio_buttons.items():
                radio_button.setEnabled(True)  # 临时启用
                if name == room_name:
                    radio_button.setChecked(True)
                else:
                    radio_button.setChecked(False)
                radio_button.setEnabled(False)  # 重新禁用

            self.log_message(t("virtual_lan_page.log.room_config_loaded", room_name=room_name), "success")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.room_load_failed", error=str(e)), "error")

    def share_room_from_list(self, room_name: str):
        """从列表分享房间"""
        try:
            # 读取房间配置
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if not room_file.exists():
                self.log_message(t("virtual_lan_page.log.room_config_not_exist", room_name=room_name), "error")
                return

            with open(room_file, 'r', encoding='utf-8') as f:
                room_config = json.load(f)

            # 创建分享配置（包含核心字段和高级设置）
            share_config = {
                "n": room_config["network_name"],      # 房间名称
                "s": room_config["network_secret"],    # 房间密码
            }

            # 本机IP配置（只在非DHCP时添加）
            if not room_config.get("dhcp", True):
                # 检查是否是有效的IPv4地址
                ipv4 = room_config.get("ipv4", "")
                if self._is_valid_ipv4(ipv4):
                    share_config["i"] = ipv4  # 包含具体IP
                else:
                    share_config["d"] = False  # 标记为非DHCP但无有效IP
            # DHCP模式不添加任何IP相关字段（默认就是DHCP）

            # 高级设置（只在非默认值时添加，减少分享代码长度）
            # 加密设置（默认禁用，只在启用时添加）
            if not room_config.get("disable_encryption", True):
                share_config["e"] = True  # 启用加密

            # IPv6设置（默认启用，只在禁用时添加）
            if room_config.get("disable_ipv6", False):
                share_config["6"] = False  # 禁用IPv6

            # 延迟优先（默认启用，只在禁用时添加）
            if not room_config.get("latency_first", True):
                share_config["l"] = False  # 禁用延迟优先

            # 多线程（默认启用，只在禁用时添加）
            if not room_config.get("multi_thread", True):
                share_config["m"] = False  # 禁用多线程

            # EasyTier网络加速选项
            # KCP代理（默认启用，只在禁用时添加）
            if not room_config.get("enable_kcp_proxy", True):
                share_config["k"] = False  # 禁用KCP代理

            # QUIC代理（默认启用，只在禁用时添加）
            if not room_config.get("enable_quic_proxy", True):
                share_config["q"] = False  # 禁用QUIC代理

            # 用户态网络栈（默认禁用，只在启用时添加）
            if room_config.get("use_smoltcp", False):
                share_config["u"] = True  # 启用用户态网络栈

            # 压缩算法（默认启用，只在禁用时添加）
            if not room_config.get("enable_compression", True):
                share_config["z"] = False  # 禁用压缩

            # 网络优化设置（只在非默认值时添加）
            network_opt = room_config.get("network_optimization", {})
            if not network_opt.get("winip_broadcast", True):
                share_config["w"] = False  # 禁用WinIP广播
            if not network_opt.get("auto_metric", True):
                share_config["a"] = False  # 禁用自动跃点

            # 公益服务器配置（只在选择了公益服务器时添加城市名）
            peers = room_config.get("peers", ["tcp://public.easytier.top:11010"])
            charity_servers = [peer for peer in peers if peer != "tcp://public.easytier.top:11010"]

            if charity_servers:
                # 获取选中的公益服务器城市名
                city_names = []
                for server_url in charity_servers:
                    for server in self.server_list:
                        if server['url'] == server_url:
                            city_names.append(server['name'])
                            break

                if city_names:
                    share_config["c"] = city_names  # 城市名列表

            # 使用紧凑的JSON格式（无空格）并编码为base64
            config_json = json.dumps(share_config, ensure_ascii=False, separators=(',', ':'))
            config_b64 = base64.b64encode(config_json.encode('utf-8')).decode('ascii')
            share_code = f"ESR://{config_b64}"

            # 复制到剪切板
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(share_code)

            self.log_message(t("virtual_lan_page.log.share_code_copied", room_name=room_name), "success")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.share_room_failed", error=str(e)), "error")

    def _is_valid_ipv4(self, ip: str) -> bool:
        """验证是否是有效的IPv4地址"""
        try:
            import ipaddress
            ipaddress.IPv4Address(ip)
            return True
        except:
            return False

    def _convert_share_config(self, raw_config: dict) -> dict:
        """转换极简分享配置到完整格式，兼容新旧格式"""
        # 如果是新的极简格式（只有n、s等核心字段）
        if "n" in raw_config and "s" in raw_config:
            # 分享格式转换为完整格式，使用默认值并应用分享的设置
            converted = {
                "network_name": raw_config["n"],
                "network_secret": raw_config["s"],
                "peers": ["tcp://public.easytier.top:11010"],  # 默认使用公共服务器
                "dhcp": True,  # 默认使用DHCP
                # 高级选项：使用默认值，然后应用分享的设置
                "disable_encryption": not raw_config.get("e", False),  # 默认禁用加密，除非分享中启用
                "disable_ipv6": not raw_config.get("6", True),         # 默认启用IPv6，除非分享中禁用
                "latency_first": raw_config.get("l", True),            # 默认启用延迟优先，除非分享中禁用
                "multi_thread": raw_config.get("m", True),             # 默认启用多线程，除非分享中禁用
                # EasyTier网络加速选项
                "enable_kcp_proxy": raw_config.get("k", True),         # 默认启用KCP代理，除非分享中禁用
                "enable_quic_proxy": raw_config.get("q", True),        # 默认启用QUIC代理，除非分享中禁用
                "use_smoltcp": raw_config.get("u", False),             # 默认禁用用户态网络栈，除非分享中启用
                "enable_compression": raw_config.get("z", True),       # 默认启用压缩，除非分享中禁用
                # 网络优化配置
                "network_optimization": {
                    "winip_broadcast": raw_config.get("w", True),      # 默认启用WinIP广播，除非分享中禁用
                    "auto_metric": raw_config.get("a", True)           # 默认启用自动跃点，除非分享中禁用
                }
            }

            # 处理IP配置
            if "i" in raw_config:
                # 有具体IP地址
                converted["ipv4"] = raw_config["i"]
                converted["dhcp"] = False
            elif "d" in raw_config and not raw_config["d"]:
                # 标记为非DHCP但无具体IP
                converted["dhcp"] = False
            # 否则使用默认DHCP

            # 处理公益服务器配置
            if "c" in raw_config:
                # 根据城市名找到对应的服务器URL
                city_names = raw_config["c"]
                if isinstance(city_names, str):
                    city_names = [city_names]

                # 查找对应的服务器URL
                for city_name in city_names:
                    for server in self.server_list:
                        if server['name'] == city_name:
                            converted["peers"].append(server['url'])
                            break

            return converted
        else:
            # 旧的完整格式，直接返回（向后兼容）
            return raw_config

    def delete_room_from_list(self, room_name: str):
        """从列表删除房间"""
        try:
            # 检查是否是当前加载的房间
            current_network_name = self.network_name_edit.text().strip()
            is_current_room = (current_network_name == room_name)

            # 如果是当前加载的房间且网络正在运行，则拒绝删除
            if is_current_room and self.easytier_manager.is_running:
                self.log_message(t("virtual_lan_page.log.room_delete_network_running", room_name=room_name), "error")
                return

            # 删除房间配置文件
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{room_name}.json"

            if room_file.exists():
                room_file.unlink()
                self.log_message(t("virtual_lan_page.log.room_deleted", room_name=room_name), "success")

                # 刷新房间列表
                self.refresh_room_list_widget()

                # 如果删除的是当前加载的房间且网络未运行，处理后续逻辑
                if is_current_room and not self.easytier_manager.is_running:
                    # 检查是否还有其他房间
                    rooms_dir = self.get_rooms_dir()
                    remaining_rooms = [f.stem for f in rooms_dir.glob("*.json") if f.is_file()]

                    if remaining_rooms:
                        # 还有其他房间，自动加载第一个
                        self.auto_load_first_room()
                    else:
                        # 没有房间了，清空界面和配置文件
                        self.clear_all_config()
                        self.log_message(t("virtual_lan_page.log.all_config_cleared_no_rooms"), "info")

            else:
                self.log_message(t("virtual_lan_page.log.room_config_not_exist", room_name=room_name), "error")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.room_delete_exception", error=str(e)), "error")

    def auto_load_first_room(self):
        """自动加载列表中的第一个房间"""
        try:
            # 安全检查：确保网络未运行
            if self.easytier_manager.is_running:
                self.log_message(t("virtual_lan_page.log.network_running_skip"), "warning")
                return

            # 获取房间列表
            rooms_dir = self.get_rooms_dir()
            room_files = list(rooms_dir.glob("*.json"))

            if room_files:
                # 按文件名排序，加载第一个
                room_files.sort(key=lambda x: x.stem)
                first_room_name = room_files[0].stem

                # 加载第一个房间
                self.load_room_from_list(first_room_name)
                self.log_message(t("virtual_lan_page.log.room_auto_loaded", room_name=first_room_name), "info")
            else:
                # 没有房间了，清空配置
                self.clear_room_config()
                self.log_message(t("virtual_lan_page.log.room_list_empty"), "info")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.auto_load_failed", error=str(e)), "warning")

    def clear_room_config(self):
        """清空房间配置"""
        try:
            # 清空UI输入框
            self.network_name_edit.clear()
            self.machine_id_edit.clear()
            self.network_secret_edit.clear()
            self.peer_ip_edit.clear()

            # 重置复选框为默认状态
            self.dhcp_check.setChecked(True)
            self.encryption_check.setChecked(True)   # 默认启用加密
            self.ipv6_check.setChecked(True)
            self.latency_first_check.setChecked(True)
            self.multi_thread_check.setChecked(True)

            # 重置EasyTier网络加速选项为默认状态
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setChecked(True)
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setChecked(True)
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setChecked(False)  # 默认禁用用户态网络栈
            if hasattr(self, 'compression_check'):
                self.compression_check.setChecked(True)

            # 重置网络优化选项为默认状态
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.setChecked(True)
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.setChecked(True)
            # KCP配置已移除

        except Exception as e:
            print(f"清空房间配置失败: {e}")

    def get_rooms_dir(self) -> Path:
        """获取房间配置目录"""
        if getattr(sys, 'frozen', False):
            root_dir = Path(sys.executable).parent
        else:
            root_dir = Path(__file__).parent.parent.parent.parent

        rooms_dir = root_dir / "ESR" / "rooms_config"
        rooms_dir.mkdir(parents=True, exist_ok=True)
        return rooms_dir

    def create_room(self):
        """创建房间"""
        try:
            # 获取当前配置
            network_name = self.network_name_edit.text().strip()
            hostname = self.machine_id_edit.text().strip()
            network_secret = self.network_secret_edit.text().strip()

            # 验证必填字段
            if not network_name:
                self.log_message(t("virtual_lan_page.error.room_name_required"), "error")
                return

            if not hostname:
                self.log_message(t("virtual_lan_page.error.player_name_required"), "error")
                return

            if not network_secret:
                self.log_message(t("virtual_lan_page.error.room_password_required"), "error")
                return

            # 检查房间是否已存在
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"

            if room_file.exists():
                self.log_message(t("virtual_lan_page.log.room_already_exists", room_name=network_name), "error")
                return

            # 收集当前配置（与easytier_config.json格式统一）
            room_config = {
                "network_name": network_name,
                "hostname": hostname,  # 统一使用hostname字段
                "network_secret": network_secret,
                "dhcp": self.dhcp_check.isChecked(),
                "enable_encryption": self.encryption_check.isChecked(),
                "disable_ipv6": not self.ipv6_check.isChecked(),
                "latency_first": self.latency_first_check.isChecked(),
                "multi_thread": self.multi_thread_check.isChecked(),
                # EasyTier网络加速选项
                "enable_kcp_proxy": self.kcp_proxy_check.isChecked(),
                "enable_quic_proxy": self.quic_proxy_check.isChecked(),
                "use_smoltcp": self.smoltcp_check.isChecked(),
                "enable_compression": self.compression_check.isChecked(),
                "tcp_listen": self.tcp_listen_check.isChecked(),
                # 网络优化配置
                "network_optimization": {
                    "winip_broadcast": self.winip_broadcast_check.isChecked(),
                    "auto_metric": self.auto_metric_check.isChecked(),
                },
                # 房间元数据
                "_room_meta": {
                    "created_by": hostname,
                    "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            # IP配置
            if not self.dhcp_check.isChecked():
                room_config["ipv4"] = self.peer_ip_edit.text().strip()

            # 完整的peers配置（包含公共服务器和公益服务器）
            peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    if server['enabled']:
                        peers.append(server['url'])

            room_config["peers"] = peers

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(room_config, f, indent=2, ensure_ascii=False)

            # 刷新房间列表
            self.refresh_room_list_widget()  # 刷新房间列表控件

            self.log_message(t("virtual_lan_page.log.room_created", room_name=network_name), "success")

            # 自动加载刚创建的房间
            self.load_room_from_list(network_name)
            self.log_message(t("virtual_lan_page.log.room_auto_loaded", room_name=network_name), "info")
            
            # 实时更新TOML配置文件
            self.update_toml_config_file()

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.create_room_failed", error=str(e)), "error")

    def join_room(self):
        """添加房间"""
        try:
            room_code = self.room_code_edit.text().strip()
            player_name = self.join_player_name_edit.text().strip()

            # 验证输入
            if not room_code:
                self.log_message(t("virtual_lan_page.error.room_code_required"), "error")
                return

            if not player_name:
                self.log_message(t("virtual_lan_page.error.player_name_input_required"), "error")
                return

            # 验证房间代码格式
            if not room_code.startswith("ESR://"):
                self.log_message(t("virtual_lan_page.error.room_code_format"), "error")
                return

            # 解码房间配置
            try:
                config_b64 = room_code[6:]  # 去掉 ESR:// 前缀
                config_json = base64.b64decode(config_b64).decode('utf-8')
                raw_config = json.loads(config_json)

                # 转换精简格式到完整格式
                room_config = self._convert_share_config(raw_config)

            except Exception as e:
                self.log_message(t("virtual_lan_page.log.parse_room_code_failed", error=str(e)), "error")
                return

            # 验证必要字段
            required_fields = ["network_name", "network_secret"]
            for field in required_fields:
                if field not in room_config:
                    self.log_message(t("virtual_lan_page.log.room_config_missing_field", field=field), "error")
                    return

            network_name = room_config["network_name"]

            # 检查是否已经加入过该房间
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"

            if room_file.exists():
                self.log_message(t("virtual_lan_page.log.room_already_joined", room_name=network_name), "error")
                return

            # 创建完整的房间配置（与easytier_config.json格式统一）
            full_config = {
                "network_name": network_name,
                "hostname": player_name,  # 统一使用hostname字段
                "network_secret": room_config["network_secret"],
                "peers": room_config.get("peers", ["tcp://public.easytier.top:11010"]),
                "dhcp": room_config.get("dhcp", True),
                "disable_encryption": room_config.get("disable_encryption", False),
                "disable_ipv6": room_config.get("disable_ipv6", False),
                "latency_first": room_config.get("latency_first", True),
                "multi_thread": room_config.get("multi_thread", True),
                # 网络优化配置（从分享的房间配置中获取，如果没有则使用当前设置）
                "network_optimization": room_config.get("network_optimization", {
                    "winip_broadcast": self.winip_broadcast_check.isChecked(),
                    "auto_metric": self.auto_metric_check.isChecked(),
                }),
                # 房间元数据
                "_room_meta": {
                    "joined_by": player_name,
                    "joined_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

            # 添加IP配置（如果有）
            if "ipv4" in room_config:
                full_config["ipv4"] = room_config["ipv4"]

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(full_config, f, indent=2, ensure_ascii=False)

            # 应用配置到当前界面
            self.apply_room_config(full_config, player_name)

            # 刷新房间列表
            self.refresh_room_list_widget()  # 刷新房间列表控件

            # 清空输入框
            self.room_code_edit.clear()
            self.join_player_name_edit.clear()

            self.log_message(t("virtual_lan_page.log.room_added", room_name=network_name), "success")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.add_room_failed", error=str(e)), "error")

    def apply_room_config(self, room_config: dict, player_name: str):
        """应用房间配置到界面"""
        try:
            # 基本配置
            self.network_name_edit.setText(room_config["network_name"])
            self.machine_id_edit.setText(player_name)
            self.network_secret_edit.setText(room_config["network_secret"])

            # DHCP配置
            dhcp_enabled = room_config.get("dhcp", True)
            self.dhcp_check.setChecked(dhcp_enabled)

            if dhcp_enabled:
                self.peer_ip_edit.setText("")
                self.peer_ip_edit.setEnabled(False)
            else:
                self.peer_ip_edit.setText(room_config.get("ipv4", "10.126.126.1"))
                self.peer_ip_edit.setEnabled(True)

            # 高级设置（使用新的默认值）
            self.encryption_check.setChecked(room_config.get("enable_encryption", True))       # 默认启用加密
            self.ipv6_check.setChecked(not room_config.get("disable_ipv6", False))
            self.latency_first_check.setChecked(room_config.get("latency_first", True))
            self.multi_thread_check.setChecked(room_config.get("multi_thread", True))

            # EasyTier网络加速设置（向后兼容，使用新的默认值）
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setChecked(room_config.get("enable_kcp_proxy", True))
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setChecked(room_config.get("enable_quic_proxy", True))
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setChecked(room_config.get("use_smoltcp", False))  # 默认禁用用户态网络栈
            if hasattr(self, 'compression_check'):
                self.compression_check.setChecked(room_config.get("enable_compression", True))

            # 网络优化设置
            network_optimization = room_config.get("network_optimization", {})
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.setChecked(network_optimization.get("winip_broadcast", True))
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.setChecked(network_optimization.get("auto_metric", True))
            # KCP配置已移除

            # 服务器配置（从peers字段解析）
            if hasattr(self, 'server_list'):
                peers = room_config.get("peers", ["tcp://public.easytier.top:11010"])
                # 过滤掉公共服务器，只处理公益服务器
                charity_servers = [peer for peer in peers if peer != "tcp://public.easytier.top:11010"]

                # 重置所有服务器状态
                for server in self.server_list:
                    server['enabled'] = server['url'] in charity_servers

                # 更新复选框状态
                for i, checkbox in enumerate(self.server_checkboxes):
                    checkbox.setChecked(self.server_list[i]['enabled'])

            # 保存配置
            self.save_config()

        except Exception as e:
            print(f"应用房间配置失败: {e}")

    def auto_save_room_config(self, network_name: str):
        """启动网络时自动保存房间配置"""
        try:
            # 获取当前配置
            hostname = self.machine_id_edit.text().strip()
            network_secret = self.network_secret_edit.text().strip()

            # 检查房间是否已存在
            rooms_dir = self.get_rooms_dir()
            room_file = rooms_dir / f"{network_name}.json"
            is_existing_room = room_file.exists()

            # 收集当前配置（与创建房间时的格式统一）
            room_config = {
                "network_name": network_name,
                "hostname": hostname,
                "network_secret": network_secret,
                "dhcp": self.dhcp_check.isChecked(),
                "enable_encryption": self.encryption_check.isChecked(),
                "disable_ipv6": not self.ipv6_check.isChecked(),
                "latency_first": self.latency_first_check.isChecked(),
                "multi_thread": self.multi_thread_check.isChecked(),
                # EasyTier网络加速选项
                "enable_kcp_proxy": self.kcp_proxy_check.isChecked(),
                "enable_quic_proxy": self.quic_proxy_check.isChecked(),
                "use_smoltcp": self.smoltcp_check.isChecked(),
                "enable_compression": self.compression_check.isChecked(),
                "tcp_listen": self.tcp_listen_check.isChecked(),
                # 网络优化配置
                "network_optimization": {
                    "winip_broadcast": self.winip_broadcast_check.isChecked(),
                    "auto_metric": self.auto_metric_check.isChecked(),
                },
            }

            # IP配置
            if not self.dhcp_check.isChecked():
                room_config["ipv4"] = self.peer_ip_edit.text().strip()

            # 完整的peers配置（包含公共服务器和公益服务器）
            peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    if server['enabled']:
                        peers.append(server['url'])
            room_config["peers"] = peers

            # 添加房间元数据
            if is_existing_room:
                # 更新现有房间
                room_config["_room_meta"] = {
                    "updated_by": hostname,
                    "updated_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                # 保留原有的创建信息
                try:
                    with open(room_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                    original_meta = existing_config.get("_room_meta", {})
                    if "created_by" in original_meta:
                        room_config["_room_meta"]["created_by"] = original_meta["created_by"]
                    if "created_time" in original_meta:
                        room_config["_room_meta"]["created_time"] = original_meta["created_time"]
                except:
                    pass
            else:
                # 新建房间
                room_config["_room_meta"] = {
                    "created_by": hostname,
                    "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

            # 保存房间配置
            with open(room_file, 'w', encoding='utf-8') as f:
                json.dump(room_config, f, indent=2, ensure_ascii=False)

            # 刷新房间列表
            self.refresh_room_list_widget()

            # 根据是否为新房间给出不同提示
            if is_existing_room:
                self.log_message(t("virtual_lan_page.log.room_config_updated", room_name=network_name), "success")
            else:
                self.log_message(t("virtual_lan_page.log.room_auto_created", room_name=network_name), "success")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.auto_save_config_failed", error=str(e)), "error")

    def on_dhcp_changed(self, state):
        """DHCP状态变化处理"""
        is_dhcp_enabled = state == 2  # Qt.Checked = 2

        # 启用DHCP时禁用手动IP输入，反之启用
        self.peer_ip_edit.setEnabled(not is_dhcp_enabled)

        if is_dhcp_enabled:
            # 启用DHCP时，清空IP输入框并显示提示
            self.peer_ip_edit.setText("")
            self.peer_ip_edit.setPlaceholderText(t("virtual_lan_page.placeholder.auto_ip"))
        else:
            # 禁用DHCP时，恢复默认IP和提示
            self.peer_ip_edit.setText("10.126.126.1")
            self.peer_ip_edit.setPlaceholderText("10.126.126.x")

    def generate_random_name(self):
        """生成随机玩家名称"""
        import random

        # 形容词列表
        adjectives = [
            "勇敢", "智慧", "神秘", "闪耀", "迅捷", "强大", "优雅", "冷静",
            "热情", "坚定", "灵活", "敏锐", "沉稳", "活力", "幽默", "温和",
            "果断", "机智", "专注", "自由", "创新", "独特", "魅力", "传奇"
        ]

        # 名词列表
        nouns = [
            "哈基追", "哈基法", "哈基蜗", "哈基弓", "无赖大人", "女爵", "神鹰哥", "尬弹哥", "铁眼大人"
        ]

        # 随机选择形容词和名词
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)

        # 添加随机数字后缀
        number = random.randint(100, 999)

        # 生成最终名称
        random_name = f"{adjective}的{noun}{number}"

        # 设置到输入框
        self.machine_id_edit.setText(random_name)

        # 添加一个小动画效果
        self.machine_id_edit.selectAll()

    def toggle_password_visibility(self, checked):
        """切换密码可见性"""
        if checked:
            # 显示密码
            self.network_secret_edit.setEchoMode(QLineEdit.Normal)
            self.password_visibility_btn.setText("🙈")
            self.password_visibility_btn.setToolTip(t("virtual_lan_page.tooltip.hide_password"))
        else:
            # 隐藏密码
            self.network_secret_edit.setEchoMode(QLineEdit.Password)
            self.password_visibility_btn.setText("👁")
            self.password_visibility_btn.setToolTip(t("virtual_lan_page.tooltip.show_password"))
    
    def create_advanced_group(self) -> QGroupBox:
        """创建高级设置组"""
        group = QGroupBox(t("virtual_lan_page.section.advanced"))
        self.advanced_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #313244;
                border-radius: 4px;
                background-color: #1e1e2e;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #74c7ec;
            }
        """)
        layout = QGridLayout(group)
        layout.setSpacing(6)  # 减少组件间距
        layout.setContentsMargins(12, 8, 12, 8)  # 减少内边距

        # 设置紧凑的复选框样式
        compact_checkbox_style = """
            QCheckBox {
                margin: 1px 0px;
                padding: 1px 0px;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
        """

        # 加密选项
        self.encryption_check = QCheckBox(t("virtual_lan_page.checkbox.encryption"))
        self.encryption_check.setChecked(True)   # 默认启用加密
        self.encryption_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.encryption_check, 0, 0)

        # IPv6选项
        self.ipv6_check = QCheckBox(t("virtual_lan_page.checkbox.ipv6"))
        self.ipv6_check.setChecked(True)  # 默认启用
        self.ipv6_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.ipv6_check, 0, 1)

        # 延迟优先选项
        self.latency_first_check = QCheckBox(t("virtual_lan_page.checkbox.latency_first"))
        self.latency_first_check.setChecked(True)  # 默认启用延迟优先
        self.latency_first_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.latency_first_check, 1, 0)

        # 多线程选项
        self.multi_thread_check = QCheckBox(t("virtual_lan_page.checkbox.multi_thread_full"))
        self.multi_thread_check.setChecked(True)  # 默认启用多线程
        self.multi_thread_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.multi_thread_check, 1, 1)

        # IPv6提醒信息
        self.ipv6_hint_label = QLabel(t("virtual_lan_page.hint.ipv6_warning"))
        self.ipv6_hint_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background-color: rgba(250, 179, 135, 0.1);
                border: 1px solid rgba(250, 179, 135, 0.3);
                border-radius: 3px;
                margin: 3px 0px;
                min-height: 16px;
            }
        """)
        layout.addWidget(self.ipv6_hint_label, 2, 0, 1, 2)  # 跨两列显示

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #45475a; }")
        layout.addWidget(separator, 3, 0, 1, 2)

        # 网络优化标题
        self.game_optimization_label = QLabel(t("virtual_lan_page.label.game_optimization"))
        self.game_optimization_label.setStyleSheet("""
            QLabel {
                color: #a6e3a1;
                font-size: 12px;
                font-weight: bold;
                margin: 4px 0px 2px 0px;
                padding: 0px;
            }
        """)
        layout.addWidget(self.game_optimization_label, 4, 0, 1, 2)

        # WinIPBroadcast选项
        self.winip_broadcast_check = QCheckBox(t("virtual_lan_page.checkbox.winip_broadcast"))
        self.winip_broadcast_check.setChecked(self.network_config.is_winip_broadcast_enabled())
        self.winip_broadcast_check.setToolTip(t("virtual_lan_page.tooltip.winip_broadcast"))
        self.winip_broadcast_check.stateChanged.connect(self.on_optimization_setting_changed)
        self.winip_broadcast_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.winip_broadcast_check, 5, 0)

        # 网卡跃点优化选项
        self.auto_metric_check = QCheckBox(t("virtual_lan_page.checkbox.auto_metric"))
        self.auto_metric_check.setChecked(self.network_config.is_network_metric_enabled())
        self.auto_metric_check.setToolTip(t("virtual_lan_page.tooltip.auto_metric"))
        self.auto_metric_check.stateChanged.connect(self.on_optimization_setting_changed)
        self.auto_metric_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.auto_metric_check, 5, 1)

        # 添加分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setStyleSheet("QFrame { color: #45475a; }")
        layout.addWidget(separator2, 6, 0, 1, 2)

        # EasyTier网络优化标题
        self.easytier_acceleration_label = QLabel(t("virtual_lan_page.label.easytier_acceleration"))
        self.easytier_acceleration_label.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 12px;
                font-weight: bold;
                margin: 4px 0px 2px 0px;
                padding: 0px;
            }
        """)
        layout.addWidget(self.easytier_acceleration_label, 7, 0, 1, 2)

        # KCP代理选项
        self.kcp_proxy_check = QCheckBox(t("virtual_lan_page.checkbox.kcp_proxy_full"))
        self.kcp_proxy_check.setChecked(True)  # 默认启用
        self.kcp_proxy_check.setToolTip(t("virtual_lan_page.tooltip.kcp_proxy"))
        self.kcp_proxy_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.kcp_proxy_check, 8, 0)

        # QUIC代理选项
        self.quic_proxy_check = QCheckBox(t("virtual_lan_page.checkbox.quic_proxy_full"))
        self.quic_proxy_check.setChecked(True)  # 默认启用
        self.quic_proxy_check.setToolTip(t("virtual_lan_page.tooltip.quic_proxy"))
        self.quic_proxy_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.quic_proxy_check, 8, 1)

        # 用户态网络栈选项
        self.smoltcp_check = QCheckBox(t("virtual_lan_page.checkbox.smoltcp_full"))
        self.smoltcp_check.setChecked(False)  # 默认禁用（提升兼容性）
        self.smoltcp_check.setToolTip(t("virtual_lan_page.tooltip.smoltcp"))
        self.smoltcp_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.smoltcp_check, 9, 0)

        # 压缩算法选项
        self.compression_check = QCheckBox(t("virtual_lan_page.checkbox.compression"))
        self.compression_check.setChecked(False)  # 默认不启用
        self.compression_check.setToolTip(t("virtual_lan_page.tooltip.compression"))
        self.compression_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.compression_check, 9, 1)

        # 监听TCP选项
        self.tcp_listen_check = QCheckBox(t("virtual_lan_page.checkbox.tcp_listen"))
        self.tcp_listen_check.setChecked(False)  # 默认不勾选
        self.tcp_listen_check.setToolTip(t("virtual_lan_page.tooltip.tcp_listen"))
        self.tcp_listen_check.setStyleSheet(compact_checkbox_style)
        layout.addWidget(self.tcp_listen_check, 10, 0)

        # 参数详解按钮
        self.params_help_btn = QPushButton(t("virtual_lan_page.button.params_help"))
        self.params_help_btn.setToolTip(t("virtual_lan_page.tooltip.params_help"))
        self.params_help_btn.clicked.connect(self.show_params_help)
        self.params_help_btn.setStyleSheet("""
            QPushButton {
                background-color: #fab387;
                color: #1e1e2e;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                margin: 1px 0px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #f9e2af;
            }
        """)
        layout.addWidget(self.params_help_btn, 10, 1)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 优化状态显示按钮
        self.optimization_status_btn = QPushButton(t("virtual_lan_page.button.view_status"))
        self.optimization_status_btn.setToolTip(t("virtual_lan_page.tooltip.optimization_status"))
        self.optimization_status_btn.clicked.connect(self.show_optimization_status)
        self.optimization_status_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                margin: 1px 0px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #7c7f93;
            }
        """)
        button_layout.addWidget(self.optimization_status_btn)

        # 配置文件查看按钮
        self.config_file_btn = QPushButton(t("virtual_lan_page.button.config_file"))
        self.config_file_btn.setToolTip(t("virtual_lan_page.tooltip.config_file"))
        self.config_file_btn.clicked.connect(self.show_config_file)
        self.config_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                margin: 1px 0px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
        """)
        button_layout.addWidget(self.config_file_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout, 11, 0, 1, 2)

        return group
    
    def create_control_group(self) -> QGroupBox:
        """创建控制组"""
        group = QGroupBox(t("virtual_lan_page.section.control"))
        self.control_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
            }
        """)
        layout = QVBoxLayout(group)
        
        # 连接状态
        status_layout = QHBoxLayout()
        self.connection_status_title_label = QLabel(t("virtual_lan_page.label.connection_status"))
        self.connection_status_title_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.connection_status_label = QLabel(t("virtual_lan_page.status.disconnected"))
        self.connection_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        status_layout.addWidget(self.connection_status_title_label)
        status_layout.addWidget(self.connection_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton(t("virtual_lan_page.button.start_network"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.start_btn.clicked.connect(self.start_network)
        
        self.stop_btn = QPushButton(t("virtual_lan_page.button.stop_network"))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_network)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        return group
    
    def create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 网络优化工具状态
        self.optimization_tools_group = self.create_optimization_tools_group()
        layout.addWidget(self.optimization_tools_group)

        # 组队房间信息
        self.peer_list_group = self.create_peer_list_group()
        layout.addWidget(self.peer_list_group)
        
        # 日志区域
        self.log_group = self.create_log_group()
        layout.addWidget(self.log_group)
        
        return widget
    

    def create_optimization_tools_group(self) -> QGroupBox:
        """创建网络优化工具状态组"""
        group = QGroupBox(t("virtual_lan_page.section.optimization_tools"))
        self.optimization_tools_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #a6e3a1;
            }
            QLabel {
                color: #cdd6f4;
                font-weight: normal;
                font-size: 12px;
            }
        """)
        layout = QGridLayout(group)

        # WinIPBroadcast状态
        self.winip_title_label = QLabel(t("virtual_lan_page.label.ip_broadcast"))
        self.winip_title_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(self.winip_title_label, 0, 0)
        self.winip_status_label = QLabel(t("virtual_lan_page.status.not_running"))
        self.winip_status_label.setStyleSheet("color: #f38ba8;")
        layout.addWidget(self.winip_status_label, 0, 1)

        # 网卡跃点状态
        self.metric_title_label = QLabel(t("virtual_lan_page.label.metric_optimization"))
        self.metric_title_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(self.metric_title_label, 1, 0)
        self.metric_status_label = QLabel(t("virtual_lan_page.status.not_optimized"))
        self.metric_status_label.setStyleSheet("color: #f38ba8;")
        layout.addWidget(self.metric_status_label, 1, 1)

        # KCP代理状态已移除

        # 工具状态按钮组
        button_layout = QHBoxLayout()

        # 刷新状态按钮
        self.refresh_optimization_btn = QPushButton(t("virtual_lan_page.button.refresh"))
        self.refresh_optimization_btn.setToolTip(t("virtual_lan_page.tooltip.refresh_optimization"))
        self.refresh_optimization_btn.clicked.connect(self.refresh_optimization_tools_status)
        self.refresh_optimization_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
        """)
        button_layout.addWidget(self.refresh_optimization_btn)

        # 详细状态按钮
        self.detail_optimization_btn = QPushButton(t("virtual_lan_page.button.detail"))
        self.detail_optimization_btn.setToolTip(t("virtual_lan_page.tooltip.optimization_detail"))
        self.detail_optimization_btn.clicked.connect(self.show_optimization_details)
        self.detail_optimization_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
        """)
        button_layout.addWidget(self.detail_optimization_btn)

        layout.addLayout(button_layout, 3, 0, 1, 2)

        return group

    def create_peer_list_group(self) -> QGroupBox:
        """创建组队房间信息组"""
        group = QGroupBox(t("virtual_lan_page.section.team_room_info"))
        self.team_room_info_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
            QTableWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                gridline-color: #313244;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout = QVBoxLayout(group)

        # 节点表格
        self.peer_table = QTableWidget()
        self.peer_table.setColumnCount(4)
        self.peer_table.setHorizontalHeaderLabels([t("virtual_lan_page.table.virtual_ip"), t("virtual_lan_page.table.player_name"), t("virtual_lan_page.table.latency"), t("virtual_lan_page.table.connection_type")])

        # 设置表格样式
        header = self.peer_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # IP地址
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # 玩家名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 延迟
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 连接方式

        # 隐藏行号列
        self.peer_table.verticalHeader().setVisible(False)

        self.peer_table.setAlternatingRowColors(False)
        self.peer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.peer_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.peer_table)

        return group

    def update_peer_table_with_local_info(self):
        """智能更新节点表格，包含本机信息"""
        try:
            # 获取本机信息
            local_ip = getattr(self, 'current_ip_label', None)
            local_network = getattr(self, 'current_network_label', None)

            local_ip_text = local_ip.text() if local_ip else "未分配"
            local_network_text = local_network.text() if local_network else "未连接"

            # 只有在有有效连接信息时才更新
            if local_ip_text == "未分配" or local_network_text == "未连接":
                return

            # 检查是否需要添加本机信息行
            local_row_exists = False
            local_row_index = -1

            # 查找本机信息行
            for row in range(self.peer_table.rowCount()):
                name_item = self.peer_table.item(row, 1)
                if name_item and "(本人)" in name_item.text():
                    local_row_exists = True
                    local_row_index = row
                    break

            # 获取主机名
            hostname = "本机"
            if hasattr(self, 'machine_id_edit') and self.machine_id_edit.text().strip():
                hostname = self.machine_id_edit.text().strip()
            elif hasattr(self, 'hostname_input') and self.hostname_input.text().strip():
                hostname = self.hostname_input.text().strip()
            elif hasattr(self, 'hostname_edit') and self.hostname_edit.text().strip():
                hostname = self.hostname_edit.text().strip()

            if not local_row_exists:
                # 添加本机信息行到第一行
                self.peer_table.insertRow(0)
                local_row_index = 0

                # 创建本机信息项
                self._create_local_info_row(0, local_ip_text, hostname)
            else:
                # 更新现有本机信息
                self._update_local_info_row(local_row_index, local_ip_text, hostname)

            # 获取其他节点信息（如果有的话）
            if hasattr(self.easytier_manager, 'get_peer_info'):
                peers = self.easytier_manager.get_peer_info()
                self._update_peer_rows(peers, local_row_index)

        except Exception as e:
            print(f"❌ 更新节点表格失败: {e}")

    def _create_local_info_row(self, row_index: int, ip_text: str, hostname: str):
        """创建本机信息行"""
        # IP地址
        ip_item = QTableWidgetItem(ip_text)
        ip_item.setTextAlignment(Qt.AlignCenter)
        self.peer_table.setItem(row_index, 0, ip_item)

        # 玩家名称（标注本人）
        display_name = f"{hostname} (本人)"
        name_item = QTableWidgetItem(display_name)
        name_item.setTextAlignment(Qt.AlignCenter)
        name_item.setForeground(QColor("#a6e3a1"))  # 绿色高亮本人
        self.peer_table.setItem(row_index, 1, name_item)

        # 延迟
        latency_item = QTableWidgetItem("0ms")
        latency_item.setTextAlignment(Qt.AlignCenter)
        latency_item.setForeground(QColor("#a6e3a1"))
        self.peer_table.setItem(row_index, 2, latency_item)

        # 连接方式
        connection_item = QTableWidgetItem(t("virtual_lan_page.table.local_machine"))
        connection_item.setTextAlignment(Qt.AlignCenter)
        connection_item.setForeground(QColor("#89b4fa"))
        self.peer_table.setItem(row_index, 3, connection_item)

    def _update_local_info_row(self, row_index: int, ip_text: str, hostname: str):
        """更新本机信息行"""
        # 只更新可能变化的信息
        ip_item = self.peer_table.item(row_index, 0)
        if ip_item and ip_item.text() != ip_text:
            ip_item.setText(ip_text)

        name_item = self.peer_table.item(row_index, 1)
        new_name = f"{hostname} (本人)"
        if name_item and name_item.text() != new_name:
            name_item.setText(new_name)

    def _update_peer_rows(self, peers: list, local_row_index: int):
        """更新其他节点行"""
        # 这里可以添加其他节点的智能更新逻辑
        # 目前先保持简单，只处理本机信息
        # 避免未使用参数警告
        _ = peers, local_row_index

    def ensure_local_info_exists(self):
        """确保本机信息始终存在于表格首行"""
        try:
            # 获取连接信息
            local_ip_text = self.current_ip_label.text() if hasattr(self, 'current_ip_label') else "未分配"
            local_network_text = self.current_network_label.text() if hasattr(self, 'current_network_label') else "未连接"

            # 只有在有有效连接时才添加本机信息
            if local_ip_text == "未分配" or local_network_text == "未连接":
                return

            # 检查首行是否是本机信息
            if self.peer_table.rowCount() == 0:
                # 表格为空，添加本机信息
                hostname = "本机"
                if hasattr(self, 'machine_id_edit') and self.machine_id_edit.text().strip():
                    hostname = self.machine_id_edit.text().strip()
                elif hasattr(self, 'hostname_input') and self.hostname_input.text().strip():
                    hostname = self.hostname_input.text().strip()
                elif hasattr(self, 'hostname_edit') and self.hostname_edit.text().strip():
                    hostname = self.hostname_edit.text().strip()

                self.peer_table.insertRow(0)
                self._create_local_info_row(0, local_ip_text, hostname)

            else:
                # 检查首行是否是本机信息
                name_item = self.peer_table.item(0, 1)
                if not name_item or "(本人)" not in name_item.text():
                    # 首行不是本机信息，插入本机信息到首行
                    hostname = "本机"
                    if hasattr(self, 'machine_id_edit') and self.machine_id_edit.text().strip():
                        hostname = self.machine_id_edit.text().strip()
                    elif hasattr(self, 'hostname_input') and self.hostname_input.text().strip():
                        hostname = self.hostname_input.text().strip()
                    elif hasattr(self, 'hostname_edit') and self.hostname_edit.text().strip():
                        hostname = self.hostname_edit.text().strip()

                    self.peer_table.insertRow(0)
                    self._create_local_info_row(0, local_ip_text, hostname)

        except Exception as e:
            print(f"❌ 确保本机信息存在失败: {e}")

    def create_log_group(self) -> QGroupBox:
        """创建日志组"""
        group = QGroupBox(t("virtual_lan_page.section.log"))
        self.log_group = group
        group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)
        layout = QVBoxLayout(group)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        self.log_text.setWordWrapMode(QTextOption.WordWrap)  # 启用自动换行
        layout.addWidget(self.log_text)

        # 清除按钮
        self.clear_log_btn = QPushButton(t("virtual_lan_page.button.clear_log"))
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(self.clear_log_btn)

        return group

    def check_installation_status_sync(self):
        """同步检查安装状态 - 在后台线程中执行"""
        try:
            # 检查EasyTier安装状态
            is_installed = self.easytier_manager.is_easytier_installed()
            current_version = None

            if is_installed:
                # 获取版本信息
                current_version = self.download_manager.get_current_easytier_version()

            return {
                'installed': is_installed,
                'version': current_version
            }
        except Exception as e:
            print(f"检查安装状态失败: {e}")
            return {'installed': False, 'version': None, 'error': str(e)}

    def check_installation_status(self):
        """检查安装状态 - 保持向后兼容"""
        result = self.check_installation_status_sync()
        self.update_installation_status_ui(result)

    def update_installation_status_ui(self, result):
        """更新安装状态UI"""
        try:
            if result.get('installed', False):
                self.status_label.setText(t("virtual_lan_page.status.installed"))
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

                # 获取版本信息
                current_version = result.get('version')
                if current_version:
                    self.version_label.setText(f"v{current_version}")
                else:
                    self.version_label.setText(t("virtual_lan_page.status.unknown_version"))
            else:
                self.status_label.setText(t("virtual_lan_page.status.not_installed"))
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.version_label.setText(t("virtual_lan_page.status.not_installed"))
                # EasyTier安装状态已在左上角状态栏显示，不需要在日志中重复

            if result.get('error'):
                self.log_message(t("virtual_lan_page.log.installation_check_issue", error=result['error']), "warning")

        except Exception as e:
            print(f"更新安装状态UI失败: {e}")

    def check_tools_status_sync(self):
        """同步检查网络优化工具状态 - 在后台线程中执行"""
        try:
            print("🔍 检查网络优化工具状态...")

            # 检查工具是否可用（不使用UI反馈，避免跨线程问题）
            tools_available = self.tool_manager.ensure_tools_available()

            return {
                'available': tools_available,
                'status': 'success' if tools_available else 'error'
            }
        except Exception as e:
            print(f"❌ 工具状态检查失败: {e}")
            return {'available': False, 'status': 'error', 'error': str(e)}

    def check_tools_status(self):
        """检查网络优化工具状态 - 保持向后兼容"""
        result = self.check_tools_status_sync()
        self.update_tools_status_ui(result)

    def update_tools_status_ui(self, result):
        """更新工具状态UI"""
        try:
            if result.get('available', False):
                print("✅ 网络优化工具检查完成")
                self.log_message(t("virtual_lan_page.log.optimization_tools_ready"), "success")
            else:
                print("❌ 网络优化工具检查失败")
                error_msg = result.get('error', t("virtual_lan_page.error.tools_missing_or_damaged"))
                self.log_message(t("virtual_lan_page.log.optimization_tools_error", error=error_msg), "error")
        except Exception as e:
            print(f"更新工具状态UI失败: {e}")

    def load_config_sync(self):
        """同步加载配置 - 在后台线程中执行"""
        try:
            config = self.easytier_manager.get_config()
            return {'config': config, 'status': 'success'}
        except Exception as e:
            print(f"加载配置失败: {e}")
            return {'config': {}, 'status': 'error', 'error': str(e)}

    def check_current_room_status_sync(self):
        """同步检查当前房间状态 - 在后台线程中执行"""
        try:
            # 获取当前配置
            current_config = self.easytier_manager.get_config()
            current_room_name = current_config.get("network_name", "").strip()
            current_hostname = current_config.get("hostname", "").strip()

            room_status = {
                'room_name': current_room_name,
                'hostname': current_hostname,
                'status': 'success'
            }

            if current_room_name:
                # 检查是否存在对应的房间配置文件
                rooms_dir = self.get_rooms_dir()
                room_file = rooms_dir / f"{current_room_name}.json"
                room_status['has_config_file'] = room_file.exists()
            else:
                room_status['has_config_file'] = False

            return room_status
        except Exception as e:
            print(f"检查房间状态失败: {e}")
            return {'status': 'error', 'error': str(e)}

    def load_config(self):
        """加载配置"""
        config = self.easytier_manager.get_config()

        self.network_name_edit.setText(config.get("network_name", ""))
        self.machine_id_edit.setText(config.get("hostname", ""))
        self.network_secret_edit.setText(config.get("network_secret", ""))

        # 加载IP配置（dhcp 和 ipv4 互斥）
        use_dhcp = config.get("dhcp", True)
        self.dhcp_check.setChecked(use_dhcp)

        if use_dhcp:
            self.peer_ip_edit.setText("")
            self.peer_ip_edit.setEnabled(False)
        else:
            # 只有在非DHCP模式下才从配置中读取ipv4
            self.peer_ip_edit.setText(config.get("ipv4", "10.126.126.1"))
            self.peer_ip_edit.setEnabled(True)

        # 外部节点已固定，无需配置

        # 设置高级选项（注意disable_*的逻辑转换，使用新的默认值）
        self.encryption_check.setChecked(config.get("enable_encryption", True))        # 默认启用加密
        self.ipv6_check.setChecked(not config.get("disable_ipv6", False))              # 默认启用IPv6
        self.latency_first_check.setChecked(config.get("latency_first", True))         # 默认启用延迟优先
        self.multi_thread_check.setChecked(config.get("multi_thread", True))           # 默认启用多线程

        # 加载网络优化设置（从 easytier_config.json）
        self.load_network_optimization_from_easytier_config()

        # 加载服务器选择状态
        if hasattr(self, 'server_list'):
            selected_peers = config.get("peers", ["tcp://public.easytier.top:11010"])
            if isinstance(selected_peers, str):
                selected_peers = [selected_peers]

            # 过滤掉公共服务器，只处理公益服务器
            charity_peers = [peer for peer in selected_peers if peer != "tcp://public.easytier.top:11010"]

            # 重置所有公益服务器状态
            for server in self.server_list:
                server['enabled'] = server['url'] in charity_peers

            # 更新复选框状态
            for i, checkbox in enumerate(self.server_checkboxes):
                checkbox.setChecked(self.server_list[i]['enabled'])

    def on_initialization_complete(self, installation_result, tools_result, config_result, room_result):
        """初始化完成处理"""
        try:
            # 更新安装状态UI
            self.update_installation_status_ui(installation_result)

            # 更新工具状态UI
            self.update_tools_status_ui(tools_result)

            # 更新配置UI
            self.update_config_ui(config_result)

            # 更新房间状态UI
            self.update_room_status_ui(room_result)

            # 标记初始化完成
            self._initialization_completed = True
            if hasattr(self, '_initializing'):
                delattr(self, '_initializing')

            # 初始化完成，静默处理

        except Exception as e:
            print(f"初始化完成处理失败: {e}")
            self.log_message(t("virtual_lan_page.log.init_complete_issue", error=str(e)), "warning")

    def on_initialization_error(self, error_msg):
        """初始化错误处理"""
        try:
            self.log_message(t("virtual_lan_page.log.page_init_failed", error=error_msg), "error")

            # 设置错误状态
            if hasattr(self, 'status_label'):
                self.status_label.setText(t("virtual_lan_page.status.init_failed"))
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

            # 清除初始化标记
            if hasattr(self, '_initializing'):
                delattr(self, '_initializing')

        except Exception as e:
            print(f"初始化错误处理失败: {e}")

    def update_config_ui(self, result):
        """更新配置UI"""
        try:
            config = result.get('config', {})

            self.network_name_edit.setText(config.get("network_name", ""))
            self.machine_id_edit.setText(config.get("hostname", ""))
            self.network_secret_edit.setText(config.get("network_secret", ""))

            # 加载IP配置（dhcp 和 ipv4 互斥）
            use_dhcp = config.get("dhcp", True)
            self.dhcp_check.setChecked(use_dhcp)

            if use_dhcp:
                self.peer_ip_edit.setText("")
                self.peer_ip_edit.setEnabled(False)
            else:
                # 只有在非DHCP模式下才从配置中读取ipv4
                self.peer_ip_edit.setText(config.get("ipv4", "10.126.126.1"))
                self.peer_ip_edit.setEnabled(True)

            # 设置高级选项
            self.encryption_check.setChecked(config.get("enable_encryption", True))
            self.ipv6_check.setChecked(not config.get("disable_ipv6", False))
            self.latency_first_check.setChecked(config.get("latency_first", True))
            self.multi_thread_check.setChecked(config.get("multi_thread", True))

            # 加载网络优化设置
            self.load_network_optimization_from_easytier_config()

            # 加载服务器选择状态
            if hasattr(self, 'server_list'):
                selected_peers = config.get("peers", ["tcp://public.easytier.top:11010"])
                if isinstance(selected_peers, str):
                    selected_peers = [selected_peers]

                # 过滤掉公共服务器，只处理公益服务器
                charity_peers = [peer for peer in selected_peers if peer != "tcp://public.easytier.top:11010"]

                # 重置所有公益服务器状态
                for server in self.server_list:
                    server['enabled'] = server['url'] in charity_peers

                # 更新复选框状态
                for i, checkbox in enumerate(self.server_checkboxes):
                    checkbox.setChecked(self.server_list[i]['enabled'])

            if result.get('error'):
                self.log_message(t("virtual_lan_page.log.config_load_issue", error=result['error']), "warning")
            else:
                self.log_message(t("virtual_lan_page.log.config_load_complete"), "success")

        except Exception as e:
            print(f"更新配置UI失败: {e}")

    def update_room_status_ui(self, result):
        """更新房间状态UI"""
        try:
            if result.get('status') == 'success':
                room_name = result.get('room_name', '')
                hostname = result.get('hostname', '')
                has_config_file = result.get('has_config_file', False)

                if room_name:
                    if not hostname:
                        self.log_message(t("virtual_lan_page.log.player_name_empty", room_name=room_name), "warning")
                    else:
                        self.log_message(t("virtual_lan_page.log.current_room_info", room_name=room_name), "success")
                else:
                    self.log_message(t("virtual_lan_page.log.create_or_load_room_first"), "warning")
            else:
                error_msg = result.get('error', t("virtual_lan_page.error.unknown_error"))
                self.log_message(t("virtual_lan_page.log.room_status_check_issue", error=error_msg), "warning")

        except Exception as e:
            print(f"更新房间状态UI失败: {e}")

    def save_config(self):
        """保存配置（使用EasyTier对应的参数命名）"""
        config = {
            "network_name": self.network_name_edit.text().strip(),      # --network-name
            "hostname": self.machine_id_edit.text().strip(),            # --hostname
            "network_secret": self.network_secret_edit.text().strip(),  # --network-secret
            "enable_encryption": self.encryption_check.isChecked(),      # --enable-encryption
            "disable_ipv6": not self.ipv6_check.isChecked(),           # --disable-ipv6
            "latency_first": self.latency_first_check.isChecked(),      # --latency-first
            "multi_thread": self.multi_thread_check.isChecked(),        # --multi-thread
            # EasyTier网络加速选项
            "enable_kcp_proxy": self.kcp_proxy_check.isChecked(),       # --enable-kcp-proxy
            "enable_quic_proxy": self.quic_proxy_check.isChecked(),     # --enable-quic-proxy
            "use_smoltcp": self.smoltcp_check.isChecked(),              # --use-smoltcp
            "enable_compression": self.compression_check.isChecked(),   # 压缩算法设置
            "tcp_listen": self.tcp_listen_check.isChecked(),            # TCP监听设置
            # 网络优化配置
            "network_optimization": {
                "winip_broadcast": self.winip_broadcast_check.isChecked(),
                "auto_metric": self.auto_metric_check.isChecked()
            }
        }

        # 收集选中的公益服务器
        selected_peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
        if hasattr(self, 'server_list'):
            for server in self.server_list:
                if server['enabled']:
                    selected_peers.append(server['url'])

        config["peers"] = selected_peers  # --peers (支持多个)

        # IP配置：dhcp 和 ipv4 互斥
        if self.dhcp_check.isChecked():
            config["dhcp"] = True                                       # --dhcp
        else:
            config["ipv4"] = self.peer_ip_edit.text().strip()          # --ipv4

        self.easytier_manager.update_config(config)

    def update_toml_config_file(self):
        """实时更新TOML配置文件，确保用户能立即看到配置变化"""
        try:
            # 获取当前界面配置
            network_name = self.network_name_edit.text().strip()
            hostname = self.machine_id_edit.text().strip()
            network_secret = self.network_secret_edit.text().strip()
            
            # 如果基本信息不完整，使用默认值
            if not network_name:
                network_name = "未设置房间"
            if not hostname:
                hostname = "未设置玩家名"
            if not network_secret:
                network_secret = "未设置密码"
            
            # 构建flags配置
            flags = {
                "enable_kcp_proxy": self.kcp_proxy_check.isChecked(),
                "enable_quic_proxy": self.quic_proxy_check.isChecked(),
                "latency_first": self.latency_first_check.isChecked(),
                "multi_thread": self.multi_thread_check.isChecked(),
                "enable_encryption": self.encryption_check.isChecked(),
                "disable_ipv6": not self.ipv6_check.isChecked(),
                "use_smoltcp": self.smoltcp_check.isChecked(),
                "enable_compression": self.compression_check.isChecked(),
                "tcp_listen": self.tcp_listen_check.isChecked()
            }
            
            # 收集选中的公益服务器
            selected_peers = ["tcp://public.easytier.top:11010"]
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    if server['enabled']:
                        selected_peers.append(server['url'])
            
            # 生成并保存TOML配置文件
            success = self.easytier_manager.config_generator.generate_and_save(
                network_name=network_name,
                network_secret=network_secret,
                hostname=hostname,
                peers=selected_peers,
                dhcp=self.dhcp_check.isChecked(),
                ipv4=self.peer_ip_edit.text().strip() if not self.dhcp_check.isChecked() else "",
                flags=flags
            )
            
            if success:
                print(f"✅ TOML配置文件已实时更新")
            else:
                print(f"❌ TOML配置文件更新失败")
                
        except Exception as e:
            print(f"❌ 更新TOML配置文件时出错: {e}")

    def start_network(self):
        """启动网络"""
        # 验证输入
        network_name = self.network_name_edit.text().strip()
        machine_id = self.machine_id_edit.text().strip()
        network_secret = self.network_secret_edit.text().strip()
        peer_ip = self.peer_ip_edit.text().strip()
        use_dhcp = self.dhcp_check.isChecked()

        if not network_name:
            self.log_text.append(t("virtual_lan_page.error.room_name_required"))
            return

        if not machine_id:
            self.log_text.append(t("virtual_lan_page.error.player_name_required"))
            return

        if not network_secret:
            self.log_text.append(t("virtual_lan_page.error.room_password_required"))
            return

        # 只有在禁用DHCP时才验证手动IP
        if not use_dhcp and not peer_ip:
            self.log_text.append(t("virtual_lan_page.error.ip_or_dhcp_required"))
            return

        # 保存配置
        self.save_config()

        # 自动保存房间配置
        self.auto_save_room_config(network_name)

        # 启动网络
        self.log_text.append(t("virtual_lan_page.log.starting_room", room_name=network_name))
        self.log_text.append(t("virtual_lan_page.log.player_name_info", player_name=machine_id))
        if use_dhcp:
            self.log_text.append(t("virtual_lan_page.log.ip_allocation_dhcp"))
        else:
            self.log_text.append(t("virtual_lan_page.log.ip_allocation_manual", ip=peer_ip))

        # 获取选中的服务器列表
        selected_peers = ["tcp://public.easytier.top:11010"]  # 始终包含公共服务器
        if hasattr(self, 'server_list'):
            for server in self.server_list:
                if server['enabled']:
                    selected_peers.append(server['url'])

        # 构建flags配置
        flags = {
            "enable_kcp_proxy": self.kcp_proxy_check.isChecked(),
            "enable_quic_proxy": self.quic_proxy_check.isChecked(),
            "latency_first": self.latency_first_check.isChecked(),
            "multi_thread": self.multi_thread_check.isChecked(),
            "enable_encryption": self.encryption_check.isChecked(),  # 注意：这里是enable_encryption
            "disable_ipv6": not self.ipv6_check.isChecked(),
            "use_smoltcp": self.smoltcp_check.isChecked(),
            "enable_compression": self.compression_check.isChecked(),
            "tcp_listen": self.tcp_listen_check.isChecked()
        }

        # 检查是否启用网络优化
        winip_enabled = hasattr(self, 'winip_broadcast_check') and self.winip_broadcast_check.isChecked()
        metric_enabled = hasattr(self, 'auto_metric_check') and self.auto_metric_check.isChecked()

        enable_optimization = winip_enabled or metric_enabled

        if enable_optimization:
            # 显示启用的优化项目
            enabled_optimizations = []
            if winip_enabled:
                enabled_optimizations.append(t("virtual_lan_page.log.ip_broadcast"))
            if metric_enabled:
                enabled_optimizations.append(t("virtual_lan_page.log.metric_optimization"))

            optimization_text = " + ".join(enabled_optimizations)
            self.log_text.append(t("virtual_lan_page.log.starting_network_with_optimization", optimizations=optimization_text))

            # 收集当前网络优化配置
            network_optimization = {
                "winip_broadcast": self.winip_broadcast_check.isChecked(),
                "auto_metric": self.auto_metric_check.isChecked(),
            }

            # 使用优化版本启动
            success = self.easytier_manager.start_network_with_optimization(
                network_name=network_name,
                network_secret=network_secret,
                ipv4=peer_ip,
                peers=selected_peers,
                hostname=machine_id,
                dhcp=use_dhcp,
                network_optimization=network_optimization,
                flags=flags  # 传递高级设置flags
            )
        else:
            # 使用配置文件模式启动（未启用优化）
            self.log_text.append(t("virtual_lan_page.log.starting_network_no_optimization"))
            success = self.easytier_manager.start_network_with_config_file(
                network_name=network_name,
                network_secret=network_secret,
                ipv4=peer_ip,
                peers=selected_peers,
                hostname=machine_id,
                dhcp=use_dhcp,
                flags=flags  # 传递高级设置flags
            )

        if success:
            self.log_text.append(t("virtual_lan_page.log.network_started_success"))
            # 更新按钮状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            # 启动状态监控
            self.start_status_monitoring()
        else:
            self.log_text.append(t("virtual_lan_page.log.network_started_failed"))

    def stop_network(self):
        """停止网络"""
        # 检查是否启用了网络优化
        winip_enabled = hasattr(self, 'winip_broadcast_check') and self.winip_broadcast_check.isChecked()
        metric_enabled = hasattr(self, 'auto_metric_check') and self.auto_metric_check.isChecked()

        enable_optimization = winip_enabled or metric_enabled

        # 禁用停止按钮，防止重复点击
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText(t("virtual_lan_page.status.stopping"))

        if enable_optimization:
            self.log_text.append(t("virtual_lan_page.log.stopping_network_and_optimization"))
            # 使用后台线程停止，避免UI卡顿
            self._stop_network_async(with_optimization=True)
        else:
            self.log_text.append(t("virtual_lan_page.log.stopping_network"))
            # 使用后台线程停止，避免UI卡顿
            self._stop_network_async(with_optimization=False)

    def _stop_network_async(self, with_optimization=False):
        """异步停止网络，避免UI卡顿"""
        from PySide6.QtCore import QThread, QObject, Signal
        
        class StopNetworkWorker(QObject):
            finished = Signal(bool)  # 停止结果
            
            def __init__(self, easytier_manager, with_optimization):
                super().__init__()
                self.easytier_manager = easytier_manager
                self.with_optimization = with_optimization
            
            def run(self):
                try:
                    if self.with_optimization:
                        success = self.easytier_manager.stop_network_with_optimization()
                    else:
                        success = self.easytier_manager.stop_network()
                    self.finished.emit(success)
                except Exception as e:
                    print(f"停止网络异常: {e}")
                    self.finished.emit(False)
        
        # 创建工作线程
        self.stop_thread = QThread()
        self.stop_worker = StopNetworkWorker(self.easytier_manager, with_optimization)
        self.stop_worker.moveToThread(self.stop_thread)
        
        # 连接信号
        self.stop_thread.started.connect(self.stop_worker.run)
        self.stop_worker.finished.connect(self._on_stop_network_finished)
        self.stop_worker.finished.connect(self.stop_thread.quit)
        self.stop_worker.finished.connect(self.stop_worker.deleteLater)
        self.stop_thread.finished.connect(self.stop_thread.deleteLater)
        
        # 启动线程
        self.stop_thread.start()

    def _on_stop_network_finished(self, success):
        """停止网络完成回调"""
        # 恢复停止按钮状态
        self.stop_btn.setText(t("virtual_lan_page.button.stop_network"))
        
        if success:
            self.log_text.append(t("virtual_lan_page.log.network_stopped_success"))
            # 更新按钮状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            # 重置优化状态显示
            if hasattr(self, 'optimization_status_label'):
                self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))
                self.optimization_status_label.setStyleSheet("color: #6c7086;")
            # 停止状态监控
            self.stop_status_monitoring()
        else:
            self.log_text.append(t("virtual_lan_page.log.network_stopped_failed"))
            # 恢复停止按钮
            self.stop_btn.setEnabled(True)

    # 信号处理方法

    def on_peer_list_updated(self, peers: list):
        """节点列表更新，保留本机信息"""
        try:
            # 检查是否有本机信息行
            local_row_exists = False
            local_row_data = None

            if self.peer_table.rowCount() > 0:
                name_item = self.peer_table.item(0, 1)
                if name_item and "(本人)" in name_item.text():
                    local_row_exists = True
                    # 保存本机信息
                    local_row_data = []
                    for col in range(4):
                        item = self.peer_table.item(0, col)
                        local_row_data.append(item.text() if item else "")

            # 设置表格行数（本机信息 + 其他节点）
            total_rows = len(peers) + (1 if local_row_exists else 0)
            self.peer_table.setRowCount(total_rows)

            # 恢复本机信息到第一行
            if local_row_exists and local_row_data:
                for col, text in enumerate(local_row_data):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)

                    # 设置本机信息的颜色
                    if col == 1:  # 玩家名称
                        item.setForeground(QColor("#a6e3a1"))
                    elif col == 2:  # 延迟
                        item.setForeground(QColor("#a6e3a1"))
                    elif col == 3:  # 连接方式
                        item.setForeground(QColor("#89b4fa"))

                    self.peer_table.setItem(0, col, item)

            # 添加其他节点信息（从第二行开始，如果有本机信息的话）
            start_row = 1 if local_row_exists else 0

            for i, peer in enumerate(peers):
                row_index = start_row + i

                # IP地址
                ip_item = QTableWidgetItem(peer.get("ip", ""))
                ip_item.setTextAlignment(Qt.AlignCenter)
                self.peer_table.setItem(row_index, 0, ip_item)

                # 主机名（玩家名称）
                hostname = peer.get("hostname", "")
                if not hostname:
                    hostname = "未知"
                hostname_item = QTableWidgetItem(hostname)
                hostname_item.setTextAlignment(Qt.AlignCenter)
                self.peer_table.setItem(row_index, 1, hostname_item)

                # 延迟
                latency = peer.get("latency", "")
                if latency and latency != "-":
                    try:
                        # 如果是数字，添加ms单位
                        float(latency)
                        latency = f"{latency}ms"
                    except:
                        pass
                latency_item = QTableWidgetItem(latency)
                latency_item.setTextAlignment(Qt.AlignCenter)
                self.peer_table.setItem(row_index, 2, latency_item)

                # 连接方式
                cost = peer.get("cost", "")
                if "relay" in cost:
                    connection_type = "中继"
                elif "p2p" in cost:
                    connection_type = "直连"
                else:
                    connection_type = cost
                connection_item = QTableWidgetItem(connection_type)
                connection_item.setTextAlignment(Qt.AlignCenter)
                self.peer_table.setItem(row_index, 3, connection_item)

        except Exception as e:
            print(f"❌ 更新节点列表失败: {e}")

    def on_connection_info_updated(self, info: dict):
        """连接信息更新"""
        old_network = self.current_network_label.text()
        old_ip = self.current_ip_label.text()

        new_network = info.get("network_name", "未知")
        new_ip = info.get("local_ip", "未分配")

        self.current_network_label.setText(new_network)
        self.current_ip_label.setText(new_ip)

        # 只有在信息真正变化时才更新表格
        if old_network != new_network or old_ip != new_ip:
            self._schedule_peer_table_updates()

    def on_error_occurred(self, error_message: str):
        """错误发生"""
        self.log_text.append(t("virtual_lan_page.error.general", error=error_message))

    def update_optimization_status(self):
        """更新网络优化状态显示"""
        try:
            if hasattr(self.easytier_manager, 'get_optimization_status'):
                status = self.easytier_manager.get_optimization_status()

                active_optimizations = []
                if status.get("WinIPBroadcast", False):
                    active_optimizations.append("IP广播")
                if status.get("网卡跃点优化", False):
                    active_optimizations.append("跃点优化")

                if active_optimizations:
                    status_text = " + ".join(active_optimizations)
                    self.optimization_status_label.setText(status_text)
                    self.optimization_status_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
                else:
                    self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))
                    self.optimization_status_label.setStyleSheet("color: #6c7086;")
            else:
                self.optimization_status_label.setText(t("virtual_lan_page.status.not_supported"))
                self.optimization_status_label.setStyleSheet("color: #6c7086;")

        except Exception as e:
            print(f"更新优化状态失败: {e}")

    def on_network_status_changed(self, is_connected: bool):
        """网络状态变化处理"""
        if is_connected:
            # 更新连接状态显示
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText(t("virtual_lan_page.status.connected"))
                self.connection_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # 更新按钮状态
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            # 网络连接后更新优化状态（使用线程安全方式）
            self._schedule_delayed_updates()
        else:
            # 更新连接状态显示
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText(t("virtual_lan_page.status.disconnected"))
                self.connection_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

            # 更新按钮状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

            # 清空表格
            self.peer_table.setRowCount(0)

            # 网络断开时重置优化状态
            if hasattr(self, 'optimization_status_label'):
                self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))
                self.optimization_status_label.setStyleSheet("color: #6c7086;")

            # 重置工具状态
            if hasattr(self, 'winip_status_label'):
                self.winip_status_label.setText(t("virtual_lan_page.status.not_running"))
                self.winip_status_label.setStyleSheet("color: #f38ba8;")
            if hasattr(self, 'metric_status_label'):
                self.metric_status_label.setText(t("virtual_lan_page.status.not_optimized"))
                self.metric_status_label.setStyleSheet("color: #f38ba8;")

    def on_optimization_setting_changed(self):
        """网络优化设置变化处理"""
        try:
            # 批量更新配置，避免重复保存
            winip_enabled = self.winip_broadcast_check.isChecked()
            metric_enabled = self.auto_metric_check.isChecked()

            # 直接更新配置对象，不立即保存
            self.network_config.config["winip_broadcast"]["enabled"] = winip_enabled
            self.network_config.config["network_metric"]["enabled"] = metric_enabled
            self.network_config.config["network_metric"]["auto_optimize"] = metric_enabled

            # 一次性保存所有配置
            if self.network_config.save_config():
                print("✅ 网络优化设置已保存到全局配置")

            # 同步网络优化配置到 easytier_config.json
            optimization_config = {
                "winip_broadcast": winip_enabled,
                "auto_metric": metric_enabled,
            }

            self.easytier_manager.update_network_optimization_config(optimization_config)

        except Exception as e:
            print(f"❌ 保存网络优化设置失败: {e}")

    def load_network_optimization_from_easytier_config(self):
        """从 easytier_config.json 加载网络优化配置"""
        try:
            # 获取 EasyTier 完整配置
            easytier_config = self.easytier_manager.config

            # 获取网络优化设置
            optimization_config = easytier_config.get("network_optimization", {})

            # 应用网络优化到UI控件（临时断开信号避免重复保存）
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.stateChanged.disconnect()
                self.winip_broadcast_check.setChecked(optimization_config.get("winip_broadcast", True))
                self.winip_broadcast_check.stateChanged.connect(self.on_optimization_setting_changed)
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.stateChanged.disconnect()
                self.auto_metric_check.setChecked(optimization_config.get("auto_metric", True))
                self.auto_metric_check.stateChanged.connect(self.on_optimization_setting_changed)

            # 应用EasyTier网络加速设置到UI控件
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setChecked(easytier_config.get("enable_kcp_proxy", True))
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setChecked(easytier_config.get("enable_quic_proxy", True))
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setChecked(easytier_config.get("use_smoltcp", False))
            if hasattr(self, 'compression_check'):
                self.compression_check.setChecked(easytier_config.get("enable_compression", True))

            print("✅ 已从 easytier_config.json 加载网络优化配置")

        except Exception as e:
            print(f"⚠️ 从 easytier_config.json 加载网络优化配置失败: {e}")
            # 使用默认值（临时断开信号避免重复保存）
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.stateChanged.disconnect()
                self.winip_broadcast_check.setChecked(True)
                self.winip_broadcast_check.stateChanged.connect(self.on_optimization_setting_changed)
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.stateChanged.disconnect()
                self.auto_metric_check.setChecked(True)
                self.auto_metric_check.stateChanged.connect(self.on_optimization_setting_changed)
            # EasyTier网络加速默认值
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setChecked(True)
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setChecked(True)
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setChecked(False)  # 新默认值
            if hasattr(self, 'compression_check'):
                self.compression_check.setChecked(True)

    def show_optimization_status(self):
        """显示网络优化状态详情"""
        try:

            # 获取当前优化状态
            if hasattr(self.easytier_manager, 'get_optimization_status'):
                status = self.easytier_manager.get_optimization_status()

            # 获取配置状态
            config_summary = self.network_config.get_optimization_summary()

            # 状态名称翻译映射
            status_name_map = {
                "WinIPBroadcast": "virtual_lan_page.status.winip_broadcast",
                "网卡跃点优化": "virtual_lan_page.status.metric_optimization",
                "自动启动": "virtual_lan_page.status.auto_start"
            }

            # 构建状态信息
            status_text = t("virtual_lan_page.dialog.optimization_status_title") + "\n\n"

            status_text += t("virtual_lan_page.dialog.optimization_status_running") + "\n"
            for name, enabled in status.items():
                translated_name = t(status_name_map.get(name, name)) if name in status_name_map else name
                icon = "✅" if enabled else "❌"
                status_text += f"   {icon} {translated_name}\n"

            status_text += "\n" + t("virtual_lan_page.dialog.optimization_status_config") + "\n"
            for name, enabled in config_summary.items():
                translated_name = t(status_name_map.get(name, name)) if name in status_name_map else name
                icon = "✅" if enabled else "❌"
                status_text += f"   {icon} {translated_name}\n"

            status_text += "\n" + t("virtual_lan_page.dialog.optimization_status_note") + "\n"
            status_text += t("virtual_lan_page.dialog.optimization_status_winip_desc") + "\n"
            status_text += t("virtual_lan_page.dialog.optimization_status_metric_desc") + "\n"
            status_text += t("virtual_lan_page.dialog.optimization_status_auto_desc")

            # 创建自定义状态对话框
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
            from PySide6.QtCore import Qt

            dialog = QDialog(self)
            dialog.setWindowTitle(t("virtual_lan_page.dialog.optimization_status"))
            dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            dialog.setFixedSize(450, 350)

            # 设置对话框样式
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e2e;
                    border: 2px solid #89b4fa;
                    border-radius: 12px;
                }
                QLabel {
                    color: #cdd6f4;
                    font-family: 'Microsoft YaHei', sans-serif;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 8px 16px;
                    margin: 8px;
                }
                QPushButton:hover {
                    background-color: #74c7ec;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)

            # 标题
            title_label = QLabel(t("virtual_lan_page.dialog.optimization_status_title"))
            title_label.setStyleSheet("""
                QLabel {
                    color: #89b4fa;
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
            """)
            layout.addWidget(title_label)

            # 状态内容
            content_label = QLabel(status_text)
            content_label.setStyleSheet("""
                QLabel {
                    color: #cdd6f4;
                    font-size: 12px;
                    line-height: 1.4;
                    padding: 10px;
                    background-color: rgba(69, 71, 90, 0.3);
                    border-radius: 8px;
                }
            """)
            content_label.setWordWrap(True)
            layout.addWidget(content_label)

            # 关闭按钮
            close_btn = QPushButton(t("virtual_lan_page.button.close"))
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            # 显示对话框
            dialog.exec()

        except Exception as e:
            print(f"❌ 显示优化状态失败: {e}")

    def show_config_file(self):
        """显示EasyTier配置文件内容"""
        try:
            # 先更新内存配置
            self.save_config()

            # 强制生成最新的TOML配置文件
            # 配置文件生成过程简化，不显示技术细节

            # 从当前配置生成TOML配置文件
            config = self.easytier_manager.config

            # 构建flags配置
            flags = {
                "enable_kcp_proxy": config.get("enable_kcp_proxy", True),
                "enable_quic_proxy": config.get("enable_quic_proxy", True),
                "latency_first": config.get("latency_first", True),
                "multi_thread": config.get("multi_thread", True),
                "enable_encryption": config.get("enable_encryption", True),
                "disable_ipv6": config.get("disable_ipv6", False),
                "use_smoltcp": config.get("use_smoltcp", False),
                "enable_compression": config.get("enable_compression", False),
                "tcp_listen": config.get("tcp_listen", False)
            }

            # 生成并保存配置文件
            success = self.easytier_manager.config_generator.generate_and_save(
                network_name=config.get("network_name", ""),
                network_secret=config.get("network_secret", ""),
                hostname=config.get("hostname", ""),
                peers=config.get("peers", ["tcp://public.easytier.top:11010"]),
                dhcp=config.get("dhcp", True),
                ipv4=config.get("ipv4", ""),
                listeners=["udp://0.0.0.0:11010"],
                rpc_portal="0.0.0.0:0",
                flags=flags
            )

            if not success:
                self.log_message(t("virtual_lan_page.log.config_gen_failed"), "error")
                return

            # 获取配置文件路径
            config_file_path = self.easytier_manager.config_generator.get_config_file_path()

            if not config_file_path.exists():
                self.log_message(t("virtual_lan_page.log.config_not_exist_after_gen"), "error")
                return

            # 读取配置文件内容
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            # 创建配置文件查看对话框
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
            from PySide6.QtCore import Qt

            dialog = QDialog(self)
            dialog.setWindowTitle(t("virtual_lan_page.dialog.config_file_title"))
            dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            dialog.setFixedSize(600, 500)

            # 设置对话框样式
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e2e;
                    border: 2px solid #89b4fa;
                    border-radius: 12px;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)

            # 标题
            title_label = QLabel(t("virtual_lan_page.dialog.config_file_label"))
            title_label.setStyleSheet("""
                QLabel {
                    color: #89b4fa;
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
            """)
            layout.addWidget(title_label)

            # 文件路径
            path_label = QLabel(f"{t('virtual_lan_page.dialog.config_file_path')} {config_file_path}")
            path_label.setStyleSheet("""
                QLabel {
                    color: #bac2de;
                    font-size: 11px;
                    margin-bottom: 10px;
                    font-family: 'Consolas', 'Monaco', monospace;
                }
            """)
            layout.addWidget(path_label)

            # 配置内容
            content_text = QTextEdit()
            content_text.setPlainText(config_content)
            content_text.setReadOnly(True)
            content_text.setStyleSheet("""
                QTextEdit {
                    color: #cdd6f4;
                    font-size: 12px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            layout.addWidget(content_text)

            # 提示信息
            hint_label = QLabel(t("virtual_lan_page.dialog.config_file_hint"))
            hint_label.setStyleSheet("""
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    font-style: italic;
                    margin-top: 5px;
                }
            """)
            layout.addWidget(hint_label)

            # 关闭按钮
            close_btn = QPushButton(t("virtual_lan_page.button.close"))
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #74c7ec;
                }
            """)
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            # 显示对话框
            dialog.exec()

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.read_config_failed", error=e), "error")

    def generate_config_file(self) -> bool:
        """生成配置文件"""
        try:
            # 更新当前配置
            self.save_config()

            # 生成TOML配置文件
            success = self.easytier_manager.config_generator.generate_config(self.easytier_manager.config)
            if success:
                self.log_message(t("virtual_lan_page.log.config_gen_success"), "success")
                return True
            else:
                self.log_message(t("virtual_lan_page.log.config_file_gen_failed_simple"), "error")
                return False
        except Exception as e:
            self.log_message(t("virtual_lan_page.log.config_gen_exception", error=e), "error")
            return False

    def update_room_config_compatibility(self, room_config: dict) -> dict:
        """更新房间配置的兼容性，添加缺失的字段"""
        updated_config = room_config.copy()
        config_updated = False

        # 检查并添加EasyTier高级设置字段
        easytier_fields = {
            "enable_kcp_proxy": True,      # 默认启用KCP代理
            "enable_quic_proxy": True,     # 默认启用QUIC代理
            "use_smoltcp": False,          # 默认禁用用户态网络栈
            "enable_compression": True,    # 默认启用压缩
        }

        for field, default_value in easytier_fields.items():
            if field not in updated_config:
                updated_config[field] = default_value
                config_updated = True

        # 检查并更新加密设置的默认值
        if "disable_encryption" not in updated_config:
            updated_config["disable_encryption"] = True  # 新默认值：禁用加密
            config_updated = True

        # 确保peers字段存在
        if "peers" not in updated_config:
            updated_config["peers"] = ["tcp://public.easytier.top:11010"]
            config_updated = True

        # 确保network_optimization字段存在
        if "network_optimization" not in updated_config:
            updated_config["network_optimization"] = {
                "winip_broadcast": True,
                "auto_metric": True
            }
            config_updated = True

        if config_updated:
            print(f"🔄 房间配置已更新兼容性: {updated_config.get('network_name', '未知房间')}")

        return updated_config

    def clear_all_config(self):
        """清空所有配置（当没有房间时调用）"""
        try:
            # 清空界面
            self.network_name_edit.clear()
            self.machine_id_edit.clear()
            self.network_secret_edit.clear()
            self.peer_ip_edit.clear()

            # 重置复选框为默认状态
            self.dhcp_check.setChecked(True)
            self.encryption_check.setChecked(True)   # 默认启用加密
            self.ipv6_check.setChecked(True)
            self.latency_first_check.setChecked(True)
            self.multi_thread_check.setChecked(True)

            # 重置EasyTier网络加速选项为默认状态
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setChecked(True)
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setChecked(True)
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setChecked(False)  # 默认禁用用户态网络栈
            if hasattr(self, 'compression_check'):
                self.compression_check.setChecked(True)

            # 重置网络优化选项
            self.winip_broadcast_check.setChecked(True)
            self.auto_metric_check.setChecked(True)

            # 重置公益服务器选择
            if hasattr(self, 'server_list'):
                for server in self.server_list:
                    server['enabled'] = False
                # 更新复选框状态
                for checkbox in self.server_checkboxes:
                    checkbox.setChecked(False)

            # 清空easytier_config.json
            config_file = self.easytier_manager.esr_dir / "easytier_config.json"
            if config_file.exists():
                config_file.unlink()
                # 配置文件清空，静默处理

            # 清空EasyTier管理器的配置
            self.easytier_manager.config.clear()

            self.log_message(t("virtual_lan_page.log.all_config_cleared_success"), "success")

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.clear_config_failed", error=e), "error")

    def refresh_optimization_tools_status(self):
        """刷新网络优化工具状态"""
        try:
            # 获取优化器状态
            if hasattr(self.easytier_manager, 'network_optimizer'):
                optimizer = self.easytier_manager.network_optimizer
                status = optimizer.get_optimization_status()

                # 更新WinIPBroadcast状态
                if status.get("WinIPBroadcast", False):
                    self.winip_status_label.setText(t("virtual_lan_page.status.running"))
                    self.winip_status_label.setStyleSheet("color: #a6e3a1;")
                else:
                    self.winip_status_label.setText(t("virtual_lan_page.status.not_running"))
                    self.winip_status_label.setStyleSheet("color: #f38ba8;")

                # 更新网卡跃点状态（增强版本）
                if status.get("网卡跃点优化", False):
                    # 获取详细的跃点状态
                    try:
                        detailed_status = self.easytier_manager.network_optimizer.get_detailed_metric_status()
                        health_check = detailed_status.get("health_check", "unknown")
                        interfaces_count = detailed_status.get("interfaces_count", 0)

                        if health_check == "healthy":
                            self.metric_status_label.setText(t("virtual_lan_page.status.optimized_interfaces", count=interfaces_count))
                            self.metric_status_label.setStyleSheet("color: #a6e3a1;")
                        elif health_check == "degraded":
                            self.metric_status_label.setText(t("virtual_lan_page.status.partially_degraded_interfaces", count=interfaces_count))
                            self.metric_status_label.setStyleSheet("color: #fab387;")
                        else:
                            self.metric_status_label.setText(t("virtual_lan_page.status.status_abnormal"))
                            self.metric_status_label.setStyleSheet("color: #f9e2af;")
                    except:
                        # 回退到基本状态显示
                        self.metric_status_label.setText(t("virtual_lan_page.status.optimized"))
                        self.metric_status_label.setStyleSheet("color: #a6e3a1;")
                else:
                    self.metric_status_label.setText(t("virtual_lan_page.status.not_optimized"))
                    self.metric_status_label.setStyleSheet("color: #f38ba8;")

                # KCP状态已移除

                # 更新总体优化状态
                enabled_count = sum(1 for enabled in status.values() if enabled)
                if enabled_count > 0:
                    enabled_items = [name for name, enabled in status.items() if enabled]
                    optimization_text = " + ".join([
                        "IP广播" if "WinIPBroadcast" in item else
                        "跃点优化" if "网卡跃点优化" in item else
                        item  # 默认显示原名称
                        for item in enabled_items
                    ])
                    self.optimization_status_label.setText(optimization_text)
                    self.optimization_status_label.setStyleSheet("color: #a6e3a1;")
                else:
                    self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))
                    self.optimization_status_label.setStyleSheet("color: #6c7086;")

                print("✅ 网络优化工具状态已刷新")
            else:
                # 重置所有状态为未启用
                self.winip_status_label.setText(t("virtual_lan_page.status.not_running"))
                self.winip_status_label.setStyleSheet("color: #f38ba8;")
                self.metric_status_label.setText(t("virtual_lan_page.status.not_optimized"))
                self.metric_status_label.setStyleSheet("color: #f38ba8;")
                self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))
                self.optimization_status_label.setStyleSheet("color: #6c7086;")

        except Exception as e:
            print(f"❌ 刷新优化工具状态失败: {e}")

    def show_optimization_details(self):
        """显示网络优化详细状态"""
        try:
            from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                                         QHBoxLayout, QTableWidget, QTableWidgetItem,
                                         QHeaderView, QTabWidget, QWidget, QGroupBox)
            from PySide6.QtCore import Qt, QTimer

            # 创建无边框详情对话框
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setFixedSize(600, 380)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    border: 2px solid #45475a;
                    border-radius: 12px;
                }
                QLabel {
                    color: #cdd6f4;
                    font-size: 12px;
                    padding: 5px;
                }
                QTableWidget {
                    background-color: #181825;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    color: #cdd6f4;
                    gridline-color: #313244;
                    selection-background-color: #89b4fa;
                    selection-color: #1e1e2e;
                }
                QTableWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #313244;
                }
                QHeaderView::section {
                    background-color: #313244;
                    color: #cdd6f4;
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #74c7ec;
                }
                QTabWidget::pane {
                    border: 1px solid #313244;
                    border-radius: 6px;
                    background-color: #181825;
                }
                QTabBar::tab {
                    background-color: #313244;
                    color: #cdd6f4;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QTabBar::tab:selected {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                }
                QGroupBox {
                    color: #cdd6f4;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #313244;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #89b4fa;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # 自定义标题栏
            title_bar = QWidget()
            title_bar.setFixedHeight(40)
            title_bar.setStyleSheet("""
                QWidget {
                    background-color: #313244;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    border-bottom: 1px solid #45475a;
                }
            """)
            title_bar_layout = QHBoxLayout(title_bar)
            title_bar_layout.setContentsMargins(15, 0, 15, 0)

            # 标题文字
            title_label = QLabel(t("virtual_lan_page.dialog.network_interface_details"))
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4;")
            title_bar_layout.addWidget(title_label)

            title_bar_layout.addStretch()

            # 关闭按钮
            close_title_btn = QPushButton("✕")
            close_title_btn.setFixedSize(30, 30)
            close_title_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f38ba8;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f9e2af;
                }
            """)
            close_title_btn.clicked.connect(dialog.close)
            title_bar_layout.addWidget(close_title_btn)

            layout.addWidget(title_bar)

            # 内容区域
            content_widget = QWidget()
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: #1e1e2e;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                }
            """)
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(15, 10, 15, 10)
            content_layout.setSpacing(8)

            # 添加拖拽功能
            def mousePressEvent(event):
                if event.button() == Qt.LeftButton:
                    dialog.drag_start_position = event.globalPosition().toPoint()

            def mouseMoveEvent(event):
                if hasattr(dialog, 'drag_start_position') and event.buttons() == Qt.LeftButton:
                    dialog.move(dialog.pos() + event.globalPosition().toPoint() - dialog.drag_start_position)
                    dialog.drag_start_position = event.globalPosition().toPoint()

            title_bar.mousePressEvent = mousePressEvent
            title_bar.mouseMoveEvent = mouseMoveEvent

            # 创建选项卡
            tab_widget = QTabWidget()

            # 选项卡1：所有网络接口
            all_interfaces_tab = QWidget()
            all_layout = QVBoxLayout(all_interfaces_tab)

            # 刷新按钮（放在表格上方）
            refresh_layout = QHBoxLayout()
            refresh_layout.setContentsMargins(0, 0, 0, 3)
            refresh_interfaces_btn = QPushButton(t("virtual_lan_page.button.refresh"))
            refresh_interfaces_btn.setFixedHeight(28)
            refresh_interfaces_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a6e3a1;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #94e2d5;
                }
            """)
            refresh_layout.addWidget(refresh_interfaces_btn)
            refresh_layout.addStretch()
            all_layout.addLayout(refresh_layout)

            # 所有接口表格
            all_table = QTableWidget()
            all_table.setColumnCount(5)
            all_table.setHorizontalHeaderLabels([
                t("virtual_lan_page.dialog.interface_name"),
                t("virtual_lan_page.dialog.metric"),
                t("virtual_lan_page.dialog.mtu"),
                t("virtual_lan_page.dialog.state"),
                t("virtual_lan_page.dialog.type")
            ])

            # 初始化空表格，稍后异步加载数据
            all_interfaces = []

            # 先显示加载提示
            all_table.setRowCount(1)
            loading_item = QTableWidgetItem(t("virtual_lan_page.status.loading_network_interfaces"))
            all_table.setItem(0, 0, loading_item)
            all_table.setSpan(0, 0, 1, 5)

            # 异步加载数据的函数
            def load_interfaces_async():
                """异步加载网络接口数据"""
                try:
                    if hasattr(self, 'easytier_manager') and self.easytier_manager.network_optimizer:
                        interfaces = self.easytier_manager.network_optimizer.get_network_interfaces()
                        interfaces.sort(key=lambda x: x.get("metric", 999))
                        return interfaces
                    return []
                except Exception as e:
                    print(f"加载网络接口失败: {e}")
                    return []

            # 使用QTimer延迟加载，避免阻塞UI
            def delayed_load():
                interfaces = load_interfaces_async()
                populate_interfaces_table(interfaces)

            def populate_interfaces_table(interfaces):
                """填充接口表格"""
                all_table.setRowCount(0)

                if interfaces:
                    all_table.setRowCount(len(interfaces))
                    for row, interface in enumerate(interfaces):
                        # 接口名称
                        name_item = QTableWidgetItem(interface.get("name", t("virtual_lan_page.status.unknown")))
                        all_table.setItem(row, 0, name_item)

                        # 当前跃点（添加优先级颜色标识）
                        metric_value = interface.get("metric", 999)
                        metric_item = QTableWidgetItem(str(metric_value))

                        # 根据跃点值设置颜色（跃点越小优先级越高）
                        if metric_value == 1:
                            metric_item.setBackground(Qt.darkGreen)  # 最高优先级
                            metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_highest"))
                        elif metric_value <= 10:
                            metric_item.setBackground(Qt.darkYellow)  # 高优先级
                            metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_high"))
                        elif metric_value <= 25:
                            metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_medium"))
                        else:
                            metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_low"))

                        all_table.setItem(row, 1, metric_item)

                        # MTU
                        mtu_item = QTableWidgetItem(str(interface.get("mtu", "N/A")))
                        all_table.setItem(row, 2, mtu_item)

                        # 状态
                        state_item = QTableWidgetItem(interface.get("state", t("virtual_lan_page.status.unknown")))
                        all_table.setItem(row, 3, state_item)

                        # 类型判断
                        interface_name = interface.get("name", "").lower()
                        if "easytier" in interface_name or "tap" in interface_name or "tun" in interface_name:
                            type_text = t("virtual_lan_page.status.interface_easytier")
                            name_item.setBackground(Qt.darkGreen)
                        elif "ethernet" in interface_name or "以太网" in interface_name:
                            type_text = t("virtual_lan_page.status.interface_ethernet")
                        elif "wi-fi" in interface_name or "wlan" in interface_name or "无线" in interface_name:
                            type_text = t("virtual_lan_page.status.interface_wifi")
                        elif "loopback" in interface_name or "回环" in interface_name:
                            type_text = t("virtual_lan_page.status.interface_loopback")
                        else:
                            type_text = t("virtual_lan_page.status.interface_other")

                        type_item = QTableWidgetItem(type_text)
                        all_table.setItem(row, 4, type_item)
                else:
                    all_table.setRowCount(1)
                    no_data_item = QTableWidgetItem(t("virtual_lan_page.error.cannot_get_network_interfaces"))
                    all_table.setItem(0, 0, no_data_item)
                    all_table.setSpan(0, 0, 1, 5)

            # 设置表格样式
            header = all_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)  # 接口名称
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 跃点
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # MTU
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 状态
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 类型
            all_table.verticalHeader().setVisible(False)
            all_table.setAlternatingRowColors(False)  # 保持统一背景

            all_layout.addWidget(all_table)
            tab_widget.addTab(all_interfaces_tab, t("virtual_lan_page.dialog.all_interfaces_tab"))

            # 选项卡2：优化状态
            optimization_tab = QWidget()
            opt_layout = QVBoxLayout(optimization_tab)

            # 优化状态组
            opt_group = QGroupBox(t("virtual_lan_page.section.optimization_status"))
            opt_group_layout = QVBoxLayout(opt_group)

            # 刷新按钮（优化状态）
            refresh_opt_layout = QHBoxLayout()
            refresh_opt_layout.setContentsMargins(0, 0, 0, 3)
            refresh_optimization_btn = QPushButton(t("virtual_lan_page.button.refresh"))
            refresh_optimization_btn.setFixedHeight(28)
            refresh_optimization_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #74c7ec;
                }
            """)
            refresh_opt_layout.addWidget(refresh_optimization_btn)
            refresh_opt_layout.addStretch()
            opt_group_layout.addLayout(refresh_opt_layout)

            # 优化状态表格
            opt_table = QTableWidget()
            opt_table.setColumnCount(4)
            opt_table.setHorizontalHeaderLabels([
                t("virtual_lan_page.dialog.interface_name"),
                t("virtual_lan_page.dialog.original_metric"),
                t("virtual_lan_page.dialog.current_metric"),
                t("virtual_lan_page.dialog.optimization_status_column")
            ])

            # 先显示加载提示
            opt_table.setRowCount(1)
            loading_opt_item = QTableWidgetItem(t("virtual_lan_page.status.loading_optimization_status"))
            opt_table.setItem(0, 0, loading_opt_item)
            opt_table.setSpan(0, 0, 1, 4)

            # 异步加载优化状态的函数
            def load_optimization_async():
                """异步加载优化状态数据"""
                try:
                    optimization_enabled = False
                    detailed_status = {"interfaces": {}, "health_check": "disabled"}

                    if hasattr(self, 'easytier_manager') and self.easytier_manager.network_optimizer:
                        optimizer = self.easytier_manager.network_optimizer
                        basic_status = optimizer.get_optimization_status()
                        optimization_enabled = basic_status.get("网卡跃点优化", False)

                        if optimization_enabled:
                            detailed_status = optimizer.get_detailed_metric_status()

                    return optimization_enabled, detailed_status
                except Exception as e:
                    print(f"加载优化状态失败: {e}")
                    return False, {"interfaces": {}, "health_check": "disabled"}

            def delayed_load_optimization():
                """延迟加载优化状态"""
                optimization_enabled, detailed_status = load_optimization_async()
                populate_optimization_table(optimization_enabled, detailed_status)
                update_health_status(optimization_enabled, detailed_status)

            def populate_optimization_table(optimization_enabled, detailed_status):
                """填充优化状态表格"""
                opt_table.setRowCount(0)

                if optimization_enabled and detailed_status.get("interfaces"):
                    interfaces = detailed_status.get("interfaces", {})
                    opt_table.setRowCount(len(interfaces))

                    for row, (interface_name, interface_info) in enumerate(interfaces.items()):
                        # 接口名称
                        name_item = QTableWidgetItem(interface_name)
                        opt_table.setItem(row, 0, name_item)

                        # 原始跃点
                        original_metric = interface_info.get('original_metric', 'N/A')
                        original_item = QTableWidgetItem(str(original_metric))
                        opt_table.setItem(row, 1, original_item)

                        # 当前跃点
                        current_metric = interface_info.get('current_metric', 'N/A')
                        current_item = QTableWidgetItem(str(current_metric))
                        opt_table.setItem(row, 2, current_item)

                        # 优化状态
                        interface_status = interface_info.get('status', 'unknown')
                        status_map = {
                            'optimized': t("virtual_lan_page.status.optimization_optimized"),
                            'degraded': t("virtual_lan_page.status.optimization_degraded"),
                            'missing': t("virtual_lan_page.status.optimization_missing"),
                            'unknown': t("virtual_lan_page.status.optimization_unknown")
                        }
                        status_text = status_map.get(interface_status, t("virtual_lan_page.status.optimization_unknown"))
                        status_item = QTableWidgetItem(status_text)

                        # 设置状态颜色
                        if interface_status == 'optimized':
                            status_item.setBackground(Qt.darkGreen)
                        elif interface_status == 'degraded':
                            status_item.setBackground(Qt.darkYellow)
                        elif interface_status == 'missing':
                            status_item.setBackground(Qt.darkRed)

                        opt_table.setItem(row, 3, status_item)
                else:
                    opt_table.setRowCount(1)
                    no_opt_item = QTableWidgetItem(t("virtual_lan_page.status.metric_optimization_not_enabled"))
                    opt_table.setItem(0, 0, no_opt_item)
                    opt_table.setSpan(0, 0, 1, 4)

            # 设置优化表格样式
            opt_header = opt_table.horizontalHeader()
            opt_header.setSectionResizeMode(0, QHeaderView.Stretch)  # 接口名称
            opt_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 原始跃点
            opt_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 当前跃点
            opt_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 状态
            opt_table.verticalHeader().setVisible(False)
            opt_table.setAlternatingRowColors(False)

            opt_group_layout.addWidget(opt_table)
            opt_layout.addWidget(opt_group)

            # 健康状态标签（稍后异步更新）
            health_label = QLabel(t("virtual_lan_page.status.health_checking"))
            health_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 5px; color: #89b4fa;")
            opt_layout.addWidget(health_label)

            # 更新健康状态的函数
            def update_health_status(optimization_enabled, detailed_status):
                """更新健康状态显示"""
                if optimization_enabled:
                    health_check = detailed_status.get('health_check', 'unknown')
                    health_map = {
                        'healthy': t("virtual_lan_page.status.health_healthy"),
                        'degraded': t("virtual_lan_page.status.health_degraded"),
                        'error': t("virtual_lan_page.status.health_error"),
                        'unknown': t("virtual_lan_page.status.health_unknown")
                    }
                    health_text = health_map.get(health_check, t("virtual_lan_page.status.health_unknown"))
                    health_label.setText(t("virtual_lan_page.dialog.overall_health").format(status=health_text))
                else:
                    health_label.setText(t("virtual_lan_page.status.health_not_enabled"))

            tab_widget.addTab(optimization_tab, t("virtual_lan_page.dialog.optimization_tab"))

            content_layout.addWidget(tab_widget)

            # 创建刷新函数
            def refresh_all_interfaces_table():
                """刷新所有接口表格"""
                try:
                    # 获取最新的网络接口信息
                    updated_interfaces = []
                    if hasattr(self, 'easytier_manager') and self.easytier_manager.network_optimizer:
                        updated_interfaces = self.easytier_manager.network_optimizer.get_network_interfaces()
                        updated_interfaces.sort(key=lambda x: x.get("metric", 999))

                    # 清空表格
                    all_table.setRowCount(0)

                    if updated_interfaces:
                        all_table.setRowCount(len(updated_interfaces))
                        for row, interface in enumerate(updated_interfaces):
                            # 接口名称
                            name_item = QTableWidgetItem(interface.get("name", t("virtual_lan_page.status.unknown")))
                            all_table.setItem(row, 0, name_item)

                            # 当前跃点（添加优先级颜色标识）
                            metric_value = interface.get("metric", 999)
                            metric_item = QTableWidgetItem(str(metric_value))

                            # 根据跃点值设置颜色
                            if metric_value == 1:
                                metric_item.setBackground(Qt.darkGreen)
                                metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_highest"))
                            elif metric_value <= 10:
                                metric_item.setBackground(Qt.darkYellow)
                                metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_high"))
                            elif metric_value <= 25:
                                metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_medium"))
                            else:
                                metric_item.setToolTip(t("virtual_lan_page.tooltip.metric_low"))

                            all_table.setItem(row, 1, metric_item)

                            # MTU
                            mtu_item = QTableWidgetItem(str(interface.get("mtu", "N/A")))
                            all_table.setItem(row, 2, mtu_item)

                            # 状态
                            state_item = QTableWidgetItem(interface.get("state", t("virtual_lan_page.status.unknown")))
                            all_table.setItem(row, 3, state_item)

                            # 类型判断
                            interface_name = interface.get("name", "").lower()
                            if "easytier" in interface_name or "tap" in interface_name or "tun" in interface_name:
                                type_text = t("virtual_lan_page.status.interface_easytier")
                                name_item.setBackground(Qt.darkGreen)
                            elif "ethernet" in interface_name or "以太网" in interface_name:
                                type_text = t("virtual_lan_page.status.interface_ethernet")
                            elif "wi-fi" in interface_name or "wlan" in interface_name or "无线" in interface_name:
                                type_text = t("virtual_lan_page.status.interface_wifi")
                            elif "loopback" in interface_name or "回环" in interface_name:
                                type_text = t("virtual_lan_page.status.interface_loopback")
                            else:
                                type_text = t("virtual_lan_page.status.interface_other")

                            type_item = QTableWidgetItem(type_text)
                            all_table.setItem(row, 4, type_item)
                    else:
                        all_table.setRowCount(1)
                        no_data_item = QTableWidgetItem(t("virtual_lan_page.error.cannot_get_network_interfaces"))
                        all_table.setItem(0, 0, no_data_item)
                        all_table.setSpan(0, 0, 1, 5)

                    print("✅ 网络接口表格已刷新")
                except Exception as e:
                    print(f"刷新接口表格失败: {e}")

            def refresh_optimization_table():
                """刷新优化状态表格"""
                try:
                    # 获取最新的优化状态
                    optimization_enabled = False
                    detailed_status = {"interfaces": {}, "health_check": "disabled"}

                    if hasattr(self, 'easytier_manager') and self.easytier_manager.network_optimizer:
                        optimizer = self.easytier_manager.network_optimizer
                        basic_status = optimizer.get_optimization_status()
                        optimization_enabled = basic_status.get("网卡跃点优化", False)

                        if optimization_enabled:
                            detailed_status = optimizer.get_detailed_metric_status()

                    # 清空表格
                    opt_table.setRowCount(0)

                    if optimization_enabled and detailed_status.get("interfaces"):
                        interfaces = detailed_status.get("interfaces", {})
                        opt_table.setRowCount(len(interfaces))

                        for row, (interface_name, interface_info) in enumerate(interfaces.items()):
                            # 接口名称
                            name_item = QTableWidgetItem(interface_name)
                            opt_table.setItem(row, 0, name_item)

                            # 原始跃点
                            original_metric = interface_info.get('original_metric', 'N/A')
                            original_item = QTableWidgetItem(str(original_metric))
                            opt_table.setItem(row, 1, original_item)

                            # 当前跃点
                            current_metric = interface_info.get('current_metric', 'N/A')
                            current_item = QTableWidgetItem(str(current_metric))
                            opt_table.setItem(row, 2, current_item)

                            # 优化状态
                            interface_status = interface_info.get('status', 'unknown')
                            status_map = {
                                'optimized': t("virtual_lan_page.status.optimization_optimized"),
                                'degraded': t("virtual_lan_page.status.optimization_degraded"),
                                'missing': t("virtual_lan_page.status.optimization_missing"),
                                'unknown': t("virtual_lan_page.status.optimization_unknown")
                            }
                            status_text = status_map.get(interface_status, t("virtual_lan_page.status.optimization_unknown"))
                            status_item = QTableWidgetItem(status_text)

                            # 设置状态颜色
                            if interface_status == 'optimized':
                                status_item.setBackground(Qt.darkGreen)
                            elif interface_status == 'degraded':
                                status_item.setBackground(Qt.darkYellow)
                            elif interface_status == 'missing':
                                status_item.setBackground(Qt.darkRed)

                            opt_table.setItem(row, 3, status_item)
                    else:
                        opt_table.setRowCount(1)
                        no_opt_item = QTableWidgetItem(t("virtual_lan_page.status.metric_optimization_not_enabled"))
                        opt_table.setItem(0, 0, no_opt_item)
                        opt_table.setSpan(0, 0, 1, 4)

                    # 更新健康状态
                    update_health_status(optimization_enabled, detailed_status)

                    print("✅ 优化状态表格已刷新")
                except Exception as e:
                    print(f"刷新优化状态表格失败: {e}")

            # 连接刷新按钮
            refresh_interfaces_btn.clicked.connect(refresh_all_interfaces_table)
            refresh_optimization_btn.clicked.connect(refresh_optimization_table)

            # 将内容区域添加到主布局
            layout.addWidget(content_widget)

            # 启动异步数据加载（使用线程安全方式）
            import threading
            def async_load_task():
                import time
                try:
                    time.sleep(0.1)  # 100ms
                    delayed_load()
                    time.sleep(0.1)  # 再等100ms，总共200ms
                    delayed_load_optimization()
                except Exception as e:
                    print(f"异步加载任务失败: {e}")

            load_thread = threading.Thread(target=async_load_task, daemon=True)
            load_thread.start()

            # 显示对话框
            dialog.exec()

        except Exception as e:
            print(f"显示优化详情失败: {e}")
            import traceback
            traceback.print_exc()
            # 简单的错误提示
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"无法显示详细状态: {str(e)}")



    def start_status_monitoring(self):
        """启动状态监控（线程安全版本）"""
        try:
            # 🔧 线程安全检测
            from PySide6.QtCore import QThread, QTimer
            from PySide6.QtWidgets import QApplication

            current_thread = QThread.currentThread()
            main_thread = QApplication.instance().thread() if QApplication.instance() else None
            is_main_thread = current_thread == main_thread

            if is_main_thread:
                # 在主线程，直接启动定时器
                if not hasattr(self, 'status_timer'):
                    self.status_timer = QTimer()
                    self.status_timer.timeout.connect(self.refresh_optimization_tools_status)

                self.status_timer.start(5000)  # 5秒间隔
                print("✅ 状态监控已启动")
            else:
                # 在后台线程，使用信号槽机制
                print("🔧 后台线程请求启动状态监控，使用信号槽机制")
                # 使用QTimer.singleShot在主线程中执行
                QTimer.singleShot(0, self._start_timer_in_main_thread)

        except Exception as e:
            print(f"❌ 启动状态监控失败: {e}")

    def _start_timer_in_main_thread(self):
        """在主线程中启动定时器"""
        try:
            if not hasattr(self, 'status_timer'):
                self.status_timer = QTimer()
                self.status_timer.timeout.connect(self.refresh_optimization_tools_status)

            self.status_timer.start(5000)  # 5秒间隔
            print("✅ 状态监控已启动（通过信号槽）")
        except Exception as e:
            print(f"❌ 主线程启动定时器失败: {e}")

    def stop_status_monitoring(self):
        """停止状态监控（线程安全版本）"""
        try:
            # 🔧 线程安全检测
            from PySide6.QtCore import QThread, QTimer
            from PySide6.QtWidgets import QApplication

            current_thread = QThread.currentThread()
            main_thread = QApplication.instance().thread() if QApplication.instance() else None
            is_main_thread = current_thread == main_thread

            if is_main_thread:
                # 在主线程，直接停止定时器
                if hasattr(self, 'status_timer') and self.status_timer.isActive():
                    self.status_timer.stop()
                    print("✅ 状态监控已停止")
            else:
                # 在后台线程，使用信号槽机制
                print("🔧 后台线程请求停止状态监控，使用信号槽机制")
                # 使用QTimer.singleShot在主线程中执行
                QTimer.singleShot(0, self._stop_timer_in_main_thread)

        except Exception as e:
            print(f"❌ 停止状态监控失败: {e}")

    def _stop_timer_in_main_thread(self):
        """在主线程中停止定时器"""
        try:
            if hasattr(self, 'status_timer') and self.status_timer.isActive():
                self.status_timer.stop()
                print("✅ 状态监控已停止（通过信号槽）")
        except Exception as e:
            print(f"❌ 主线程停止定时器失败: {e}")

    def _schedule_delayed_updates(self):
        """线程安全的延迟更新调度"""
        import threading

        def delayed_update_task():
            import time
            try:
                # 延迟2秒更新优化状态
                time.sleep(2)
                self.update_optimization_status()

                # 延迟3秒刷新工具状态
                time.sleep(1)  # 总共3秒
                self.refresh_optimization_tools_status()

                # 延迟4秒确保本机信息存在
                time.sleep(1)  # 总共4秒
                self.ensure_local_info_exists()

            except Exception as e:
                print(f"延迟更新任务失败: {e}")

        # 在后台线程中执行延迟更新
        update_thread = threading.Thread(target=delayed_update_task, daemon=True)
        update_thread.start()

    def _schedule_async_initialization(self):
        """线程安全的异步初始化调度"""
        import threading
        import time

        def init_task():
            try:
                time.sleep(0.05)  # 50ms
                self.async_initialize_page()

                # 等待初始化完成后再注册页面离开处理器
                max_wait = 10  # 最多等待10秒
                wait_count = 0
                while not self._initialization_completed and wait_count < max_wait * 10:
                    time.sleep(0.1)
                    wait_count += 1

                if self._initialization_completed:
                    self.register_page_leave_handler()
                else:
                    print("⚠️ 初始化超时，跳过页面离开处理器注册")

            except Exception as e:
                print(f"异步初始化任务失败: {e}")

        init_thread = threading.Thread(target=init_task, daemon=True)
        init_thread.start()

    def _schedule_cleanup_processes(self):
        """线程安全的清理进程调度"""
        import threading
        import time

        def cleanup_task():
            try:
                time.sleep(0.5)  # 500ms
                self.cleanup_residual_processes_async()
            except Exception as e:
                print(f"清理进程任务失败: {e}")

        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()

    def _schedule_peer_table_updates(self):
        """线程安全的对等节点表格更新调度"""
        import threading
        import time

        def update_task():
            try:
                time.sleep(0.5)  # 500ms
                self.update_peer_table_with_local_info()

                time.sleep(0.1)  # 再等100ms，总共600ms
                self.ensure_local_info_exists()

            except Exception as e:
                print(f"对等节点表格更新任务失败: {e}")

        update_thread = threading.Thread(target=update_task, daemon=True)
        update_thread.start()

    def _start_cleanup_monitoring(self, future, executor):
        """线程安全的清理监控"""
        import threading
        import time

        def monitor_task():
            try:
                # 每100ms检查一次任务状态
                while not future.done():
                    time.sleep(0.1)

                # 任务完成，获取结果
                success = future.result()

                if success:
                    print("✅ 异步清理完成")
                else:
                    print("❌ 异步清理失败")
                    # 🔧 使用线程安全的log_message方法
                    self.log_message(t("virtual_lan_page.log.backend_cleanup_issue"), "warning")

                # 关闭线程池
                executor.shutdown(wait=False)

            except Exception as e:
                print(f"❌ 监控清理状态失败: {e}")
                executor.shutdown(wait=False)

        monitor_thread = threading.Thread(target=monitor_task, daemon=True)
        monitor_thread.start()

    def show_params_help(self):
        """显示参数详解对话框"""
        try:
            from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                                         QScrollArea, QWidget, QHBoxLayout)
            from PySide6.QtCore import Qt

            # 创建参数详解对话框（参考配置文件对话框风格）
            dialog = QDialog(self)
            dialog.setWindowTitle(t("virtual_lan_page.dialog.params_help"))
            dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            dialog.setFixedSize(600, 500)

            # 设置对话框样式
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e2e;
                    border: 2px solid #89b4fa;
                    border-radius: 12px;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)

            # 标题
            title_label = QLabel(t("virtual_lan_page.params_help.title"))
            title_label.setStyleSheet("""
                QLabel {
                    color: #89b4fa;
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
            """)
            layout.addWidget(title_label)

            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setStyleSheet("""
                QScrollArea {
                    color: #cdd6f4;
                    font-size: 12px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)

            # 参数说明内容
            params_info = [
                (t("virtual_lan_page.params_help.kcp_proxy"), t("virtual_lan_page.params_help.kcp_proxy_desc")),
                (t("virtual_lan_page.params_help.quic_proxy"), t("virtual_lan_page.params_help.quic_proxy_desc")),
                (t("virtual_lan_page.params_help.smoltcp"), t("virtual_lan_page.params_help.smoltcp_desc")),
                (t("virtual_lan_page.params_help.ipv6"), t("virtual_lan_page.params_help.ipv6_desc")),
                (t("virtual_lan_page.params_help.latency_first"), t("virtual_lan_page.params_help.latency_first_desc")),
                (t("virtual_lan_page.params_help.multi_thread"), t("virtual_lan_page.params_help.multi_thread_desc")),
                (t("virtual_lan_page.params_help.compression"), t("virtual_lan_page.params_help.compression_desc")),
                (t("virtual_lan_page.params_help.tcp_listen"), t("virtual_lan_page.params_help.tcp_listen_desc")),
                (t("virtual_lan_page.params_help.optimization"), t("virtual_lan_page.params_help.optimization_desc"))
            ]

            for title, description in params_info:
                param_widget = QWidget()
                param_layout = QVBoxLayout(param_widget)
                param_layout.setContentsMargins(8, 4, 8, 4)

                # 参数标题
                param_title = QLabel(title)
                param_title.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        color: #f9e2af;
                        font-size: 13px;
                        margin-bottom: 4px;
                    }
                """)
                param_layout.addWidget(param_title)

                # 参数描述
                param_desc = QLabel(description)
                param_desc.setStyleSheet("""
                    QLabel {
                        color: #bac2de;
                        font-size: 11px;
                        margin-left: 16px;
                        margin-bottom: 8px;
                    }
                """)
                param_desc.setWordWrap(True)
                param_layout.addWidget(param_desc)

                scroll_layout.addWidget(param_widget)

            # 添加分隔线和提示
            separator = QLabel("─" * 60)
            separator.setStyleSheet("""
                QLabel {
                    color: #45475a;
                    font-size: 10px;
                    margin: 10px 0px;
                }
            """)
            separator.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(separator)

            tip_label = QLabel(t("virtual_lan_page.params_help.tip"))
            tip_label.setStyleSheet("""
                QLabel {
                    color: #f9e2af;
                    font-size: 11px;
                    font-style: italic;
                    margin-top: 5px;
                }
            """)
            tip_label.setWordWrap(True)
            scroll_layout.addWidget(tip_label)

            scroll_area.setWidget(scroll_widget)
            scroll_area.setWidgetResizable(True)
            layout.addWidget(scroll_area)

            # 关闭按钮
            close_btn = QPushButton(t("virtual_lan_page.button.close"))
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #74c7ec;
                }
            """)
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()

        except Exception as e:
            self.log_message(t("virtual_lan_page.log.show_params_help_failed", error=e), "error")

    def _on_language_changed(self, language_code):
        """语言切换回调"""
        try:
            # 更新页面标题
            if hasattr(self, 'title_label'):
                self.title_label.setText(t("virtual_lan_page.page_title"))

            # 更新标签页标题
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setTabText(0, t("virtual_lan_page.tab.room_list"))
                self.tab_widget.setTabText(1, t("virtual_lan_page.tab.add_room"))
                self.tab_widget.setTabText(2, t("virtual_lan_page.tab.room_info"))
                self.tab_widget.setTabText(3, t("virtual_lan_page.tab.advanced"))
                self.tab_widget.setTabText(4, t("virtual_lan_page.tab.servers"))

            # 更新区域标题
            if hasattr(self, 'installation_group'):
                self.installation_group.setTitle(t("virtual_lan_page.section.installation"))
            if hasattr(self, 'network_config_group'):
                self.network_config_group.setTitle(t("virtual_lan_page.section.network_config"))
            if hasattr(self, 'room_list_group'):
                self.room_list_group.setTitle(t("virtual_lan_page.section.room_list"))
            if hasattr(self, 'create_room_group'):
                self.create_room_group.setTitle(t("virtual_lan_page.section.create_room"))
            if hasattr(self, 'add_room_group'):
                self.add_room_group.setTitle(t("virtual_lan_page.section.add_room"))
            if hasattr(self, 'join_group'):
                self.join_group.setTitle(t("virtual_lan_page.section.join_by_code"))
            if hasattr(self, 'servers_group'):
                self.servers_group.setTitle(t("virtual_lan_page.section.servers"))
            if hasattr(self, 'advanced_group'):
                self.advanced_group.setTitle(t("virtual_lan_page.section.advanced"))
            if hasattr(self, 'control_group'):
                self.control_group.setTitle(t("virtual_lan_page.section.control"))
            if hasattr(self, 'optimization_tools_group'):
                self.optimization_tools_group.setTitle(t("virtual_lan_page.section.optimization_tools"))
            if hasattr(self, 'team_room_info_group'):
                self.team_room_info_group.setTitle(t("virtual_lan_page.section.team_room_info"))
            if hasattr(self, 'log_group'):
                self.log_group.setTitle(t("virtual_lan_page.section.log"))

            # 更新按钮
            if hasattr(self, 'install_btn'):
                if self.install_btn.text() in ["安装 EasyTier", "Install EasyTier"]:
                    self.install_btn.setText(t("virtual_lan_page.button.install"))
                elif self.install_btn.text() in ["卸载 EasyTier", "Uninstall EasyTier"]:
                    self.install_btn.setText(t("virtual_lan_page.button.uninstall"))
            if hasattr(self, 'create_room_btn'):
                self.create_room_btn.setText(t("virtual_lan_page.button.create_room"))
            if hasattr(self, 'refresh_room_list_btn'):
                self.refresh_room_list_btn.setText(t("virtual_lan_page.button.refresh_list"))
            if hasattr(self, 'join_room_btn'):
                self.join_room_btn.setText(t("virtual_lan_page.button.add_room"))
            if hasattr(self, 'start_btn'):
                current_text = self.start_btn.text()
                if "启动" in current_text or "Start" in current_text:
                    self.start_btn.setText(t("virtual_lan_page.button.start_network"))
                elif "停止" in current_text or "Stop" in current_text:
                    self.start_btn.setText(t("virtual_lan_page.button.stop_network"))
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setText(t("virtual_lan_page.button.stop_network"))
            if hasattr(self, 'params_help_btn'):
                self.params_help_btn.setText(t("virtual_lan_page.button.params_help"))
            if hasattr(self, 'optimization_status_btn'):
                self.optimization_status_btn.setText(t("virtual_lan_page.button.view_status"))
            if hasattr(self, 'config_file_btn'):
                self.config_file_btn.setText(t("virtual_lan_page.button.config_file"))

            # 更新标签
            if hasattr(self, 'status_title_label'):
                self.status_title_label.setText(t("virtual_lan_page.label.status"))
            if hasattr(self, 'version_title_label'):
                self.version_title_label.setText(t("virtual_lan_page.label.version"))
            if hasattr(self, 'room_name_label'):
                self.room_name_label.setText(t("virtual_lan_page.label.room_name"))
            if hasattr(self, 'player_name_label'):
                self.player_name_label.setText(t("virtual_lan_page.label.player_name"))
            if hasattr(self, 'player_name_hint_label'):
                self.player_name_hint_label.setText(t("virtual_lan_page.hint.player_name_unique"))
            if hasattr(self, 'room_password_label'):
                self.room_password_label.setText(t("virtual_lan_page.label.room_password"))
            if hasattr(self, 'local_ip_label'):
                self.local_ip_label.setText(t("virtual_lan_page.label.local_ip"))
            if hasattr(self, 'public_server_label'):
                self.public_server_label.setText(t("virtual_lan_page.label.public_server"))
            if hasattr(self, 'room_right_click_hint_label'):
                self.room_right_click_hint_label.setText(t("virtual_lan_page.hint.room_right_click"))
            if hasattr(self, 'beginner_tip_hint_label'):
                self.beginner_tip_hint_label.setText(t("virtual_lan_page.hint.beginner_tip"))
            if hasattr(self, 'room_code_label'):
                self.room_code_label.setText(t("virtual_lan_page.label.room_code"))
            if hasattr(self, 'join_player_name_label'):
                self.join_player_name_label.setText(t("virtual_lan_page.label.player_name"))
            if hasattr(self, 'join_hint_label'):
                self.join_hint_label.setText(t("virtual_lan_page.hint.parse_room_code"))
            if hasattr(self, 'server_selection_hint_label'):
                self.server_selection_hint_label.setText(t("virtual_lan_page.hint.server_selection"))
            if hasattr(self, 'ipv6_hint_label'):
                self.ipv6_hint_label.setText(t("virtual_lan_page.hint.ipv6_warning"))
            if hasattr(self, 'game_optimization_label'):
                self.game_optimization_label.setText(t("virtual_lan_page.label.game_optimization"))
            if hasattr(self, 'easytier_acceleration_label'):
                self.easytier_acceleration_label.setText(t("virtual_lan_page.label.easytier_acceleration"))
            if hasattr(self, 'connection_status_title_label'):
                self.connection_status_title_label.setText(t("virtual_lan_page.label.connection_status"))
            if hasattr(self, 'winip_title_label'):
                self.winip_title_label.setText(t("virtual_lan_page.label.ip_broadcast"))
            if hasattr(self, 'metric_title_label'):
                self.metric_title_label.setText(t("virtual_lan_page.label.metric_optimization"))
            if hasattr(self, 'clear_log_btn'):
                self.clear_log_btn.setText(t("virtual_lan_page.button.clear_log"))
            if hasattr(self, 'refresh_optimization_btn'):
                self.refresh_optimization_btn.setText(t("virtual_lan_page.button.refresh"))
            if hasattr(self, 'detail_optimization_btn'):
                self.detail_optimization_btn.setText(t("virtual_lan_page.button.detail"))

            # 更新表格标题
            if hasattr(self, 'peer_table'):
                self.peer_table.setHorizontalHeaderLabels([
                    t("virtual_lan_page.table.virtual_ip"),
                    t("virtual_lan_page.table.player_name"),
                    t("virtual_lan_page.table.latency"),
                    t("virtual_lan_page.table.connection_type")
                ])

            # 更新动态状态文本
            if hasattr(self, 'status_label'):
                current_text = self.status_label.text()
                if "已安装" in current_text or "Installed" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.installed"))
                elif "未安装" in current_text or "Not Installed" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.not_installed"))
                elif "检测中" in current_text or "Checking" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.checking"))
                elif "初始化失败" in current_text or "Init Failed" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.init_failed"))
                elif "点击页面" in current_text or "Click" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.click_to_init"))
                elif "等待初始化" in current_text or "Waiting" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.waiting_init"))
                elif "初始化中" in current_text or "Initializing" in current_text:
                    self.status_label.setText(t("virtual_lan_page.status.initializing"))

            if hasattr(self, 'version_label'):
                current_text = self.version_label.text()
                if "未知" in current_text or "Unknown" in current_text:
                    self.version_label.setText(t("virtual_lan_page.status.unknown"))
                elif "未安装" in current_text or "Not Installed" in current_text:
                    self.version_label.setText(t("virtual_lan_page.status.not_installed"))
                elif "版本未知" in current_text or "Unknown Version" in current_text:
                    self.version_label.setText(t("virtual_lan_page.status.unknown_version"))

            # 更新连接状态动态文本
            if hasattr(self, 'connection_status_label'):
                current_text = self.connection_status_label.text()
                if "未连接" in current_text or current_text == "Disconnected":
                    self.connection_status_label.setText(t("virtual_lan_page.status.disconnected"))
                elif "连接中" in current_text or current_text == "Connecting":
                    self.connection_status_label.setText(t("virtual_lan_page.status.connecting"))
                elif "已连接" in current_text or current_text == "Connected":
                    self.connection_status_label.setText(t("virtual_lan_page.status.connected"))

            # 更新网络优化工具状态动态文本
            if hasattr(self, 'winip_status_label'):
                current_text = self.winip_status_label.text()
                if "未运行" in current_text or "Not Running" in current_text:
                    self.winip_status_label.setText(t("virtual_lan_page.status.not_running"))
                elif "运行中" in current_text or "Running" in current_text:
                    self.winip_status_label.setText(t("virtual_lan_page.status.running"))

            if hasattr(self, 'metric_status_label'):
                current_text = self.metric_status_label.text()
                if "未优化" in current_text or "Not Optimized" in current_text:
                    self.metric_status_label.setText(t("virtual_lan_page.status.not_optimized"))
                elif "已优化" in current_text or "Optimized" in current_text:
                    self.metric_status_label.setText(t("virtual_lan_page.status.optimized"))

            # 更新复选框
            if hasattr(self, 'dhcp_check'):
                self.dhcp_check.setText(t("virtual_lan_page.checkbox.dhcp"))
            if hasattr(self, 'encryption_check'):
                self.encryption_check.setText(t("virtual_lan_page.checkbox.encryption"))
            if hasattr(self, 'ipv6_check'):
                self.ipv6_check.setText(t("virtual_lan_page.checkbox.ipv6"))
            if hasattr(self, 'latency_first_check'):
                self.latency_first_check.setText(t("virtual_lan_page.checkbox.latency_first"))
            if hasattr(self, 'multi_thread_check'):
                self.multi_thread_check.setText(t("virtual_lan_page.checkbox.multi_thread_full"))
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.setText(t("virtual_lan_page.checkbox.winip_broadcast"))
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.setText(t("virtual_lan_page.checkbox.auto_metric"))
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setText(t("virtual_lan_page.checkbox.kcp_proxy_full"))
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setText(t("virtual_lan_page.checkbox.quic_proxy_full"))
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setText(t("virtual_lan_page.checkbox.smoltcp_full"))
            if hasattr(self, 'compression_check'):
                self.compression_check.setText(t("virtual_lan_page.checkbox.compression"))
            if hasattr(self, 'tcp_listen_check'):
                self.tcp_listen_check.setText(t("virtual_lan_page.checkbox.tcp_listen"))

            # 更新占位符
            if hasattr(self, 'network_name_edit'):
                self.network_name_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_name"))
            if hasattr(self, 'machine_id_edit'):
                self.machine_id_edit.setPlaceholderText(t("virtual_lan_page.placeholder.player_name_unique"))
            if hasattr(self, 'network_secret_edit'):
                self.network_secret_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_password"))
            if hasattr(self, 'peer_ip_edit'):
                self.peer_ip_edit.setPlaceholderText(t("virtual_lan_page.placeholder.auto_ip"))
            if hasattr(self, 'room_code_edit'):
                self.room_code_edit.setPlaceholderText(t("virtual_lan_page.placeholder.room_code"))
            if hasattr(self, 'join_player_name_edit'):
                self.join_player_name_edit.setPlaceholderText(t("virtual_lan_page.placeholder.join_player_name"))

            # 更新工具提示
            if hasattr(self, 'random_name_btn'):
                self.random_name_btn.setToolTip(t("virtual_lan_page.tooltip.random_name"))
            if hasattr(self, 'password_visibility_btn'):
                # 根据当前状态设置工具提示
                if self.password_visibility_btn.isChecked():
                    self.password_visibility_btn.setToolTip(t("virtual_lan_page.tooltip.hide_password"))
                else:
                    self.password_visibility_btn.setToolTip(t("virtual_lan_page.tooltip.show_password"))
            if hasattr(self, 'winip_broadcast_check'):
                self.winip_broadcast_check.setToolTip(t("virtual_lan_page.tooltip.winip_broadcast"))
            if hasattr(self, 'auto_metric_check'):
                self.auto_metric_check.setToolTip(t("virtual_lan_page.tooltip.auto_metric"))
            if hasattr(self, 'kcp_proxy_check'):
                self.kcp_proxy_check.setToolTip(t("virtual_lan_page.tooltip.kcp_proxy"))
            if hasattr(self, 'quic_proxy_check'):
                self.quic_proxy_check.setToolTip(t("virtual_lan_page.tooltip.quic_proxy"))
            if hasattr(self, 'smoltcp_check'):
                self.smoltcp_check.setToolTip(t("virtual_lan_page.tooltip.smoltcp"))
            if hasattr(self, 'compression_check'):
                self.compression_check.setToolTip(t("virtual_lan_page.tooltip.compression"))
            if hasattr(self, 'tcp_listen_check'):
                self.tcp_listen_check.setToolTip(t("virtual_lan_page.tooltip.tcp_listen"))
            if hasattr(self, 'params_help_btn'):
                self.params_help_btn.setToolTip(t("virtual_lan_page.tooltip.params_help"))
            if hasattr(self, 'optimization_status_btn'):
                self.optimization_status_btn.setToolTip(t("virtual_lan_page.tooltip.optimization_status"))
            if hasattr(self, 'config_file_btn'):
                self.config_file_btn.setToolTip(t("virtual_lan_page.tooltip.config_file"))

            # 更新动态文本
            if hasattr(self, 'current_network_label'):
                current_text = self.current_network_label.text()
                if "未连接" in current_text or "Not Connected" in current_text:
                    self.current_network_label.setText(t("virtual_lan_page.status.not_connected"))
                elif "已连接" in current_text or "Connected" in current_text:
                    self.current_network_label.setText(t("virtual_lan_page.status.connected"))

            if hasattr(self, 'current_ip_label'):
                current_text = self.current_ip_label.text()
                if "未分配" in current_text or "Not Assigned" in current_text:
                    self.current_ip_label.setText(t("virtual_lan_page.status.not_assigned"))

            if hasattr(self, 'optimization_status_label'):
                current_text = self.optimization_status_label.text()
                if "未启用" in current_text or "Not Enabled" in current_text:
                    self.optimization_status_label.setText(t("virtual_lan_page.status.not_enabled"))

            # 更新公益服务器延迟标签
            if hasattr(self, 'server_ping_labels') and hasattr(self, 'server_ping_values'):
                for i, ping_label in enumerate(self.server_ping_labels):
                    current_text = ping_label.text()
                    if "检测中" in current_text or "Detecting" in current_text:
                        ping_label.setText(t("virtual_lan_page.status.detecting"))
                    elif "超时" in current_text or "Timeout" in current_text:
                        ping_label.setText(t("virtual_lan_page.status.timeout"))
                        ping_label.setToolTip(t("virtual_lan_page.tooltip.server_timeout"))
                    elif "ms" in current_text:
                        # 延迟值已显示,只更新tooltip
                        ping_ms = self.server_ping_values.get(i, -1)
                        if ping_ms > 0:
                            if ping_ms < 50:
                                status = t("virtual_lan_page.ping_status.excellent")
                            elif ping_ms < 100:
                                status = t("virtual_lan_page.ping_status.good")
                            elif ping_ms < 150:
                                status = t("virtual_lan_page.ping_status.fair")
                            else:
                                status = t("virtual_lan_page.ping_status.poor")
                            ping_label.setToolTip(t("virtual_lan_page.tooltip.server_latency").format(ping_ms=ping_ms, status=status))

            # 更新网络优化状态标签
            if hasattr(self, 'winip_status_label'):
                current_text = self.winip_status_label.text()
                if "未运行" in current_text or "Not Running" in current_text:
                    self.winip_status_label.setText(t("virtual_lan_page.status.not_running"))
                elif "运行中" in current_text or "Running" in current_text:
                    self.winip_status_label.setText(t("virtual_lan_page.status.running"))

            if hasattr(self, 'metric_status_label'):
                current_text = self.metric_status_label.text()
                if "未优化" in current_text or "Not Optimized" in current_text:
                    self.metric_status_label.setText(t("virtual_lan_page.status.not_optimized"))
                elif "已优化" in current_text or "Optimized" in current_text:
                    # 检查是否包含接口数量
                    import re
                    match = re.search(r'\((\d+)', current_text)
                    if match:
                        count = int(match.group(1))
                        self.metric_status_label.setText(t("virtual_lan_page.status.optimized_interfaces", count=count))
                    else:
                        self.metric_status_label.setText(t("virtual_lan_page.status.optimized"))
                elif "部分降级" in current_text or "Partially Degraded" in current_text:
                    import re
                    match = re.search(r'\((\d+)', current_text)
                    if match:
                        count = int(match.group(1))
                        self.metric_status_label.setText(t("virtual_lan_page.status.partially_degraded_interfaces", count=count))
                elif "状态异常" in current_text or "Status Abnormal" in current_text:
                    self.metric_status_label.setText(t("virtual_lan_page.status.status_abnormal"))

        except Exception as e:
            print(f"语言切换更新失败: {e}")
