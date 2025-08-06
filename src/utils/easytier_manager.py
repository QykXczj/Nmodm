"""
EasyTier管理器
负责EasyTier进程管理、网络操作和状态监控
"""

import json
import subprocess
import time
import ctypes
from pathlib import Path
from typing import Optional, Dict, List
from PySide6.QtCore import QObject, QThread, Signal, QTimer
import sys
import uuid

from .tool_manager import ToolManager
from .network_optimizer import NetworkOptimizer
from .easytier_config_generator import EasyTierConfigGenerator


class EasyTierStartWorker(QThread):
    """EasyTier启动工作线程"""

    # 信号定义
    start_finished = Signal(bool, str, object)  # 启动完成(成功, 消息, 进程对象)

    def __init__(self, easytier_manager, cmd):
        super().__init__()
        self.easytier_manager = easytier_manager
        self.cmd = cmd

    def run(self):
        """在后台线程中启动EasyTier"""
        try:
            process = self.easytier_manager._start_as_admin(self.cmd)
            if process and process.poll() is None:
                self.start_finished.emit(True, "启动成功", process)
            else:
                self.start_finished.emit(False, "启动失败", None)
        except Exception as e:
            self.start_finished.emit(False, f"启动异常: {e}", None)


class NetworkOptimizationWorker(QThread):
    """网络优化工作线程"""
    optimization_finished = Signal(bool, str)  # 成功/失败, 消息

    def __init__(self, network_optimizer):
        super().__init__()
        self.network_optimizer = network_optimizer

    def run(self):
        """在后台线程中启动网络优化"""
        try:
            # 等待EasyTier完全启动
            print("⏳ 等待EasyTier完全启动...")
            time.sleep(3)

            # 启动网络优化
            print("🚀 启动网络优化...")
            optimization_success = self.network_optimizer.start_all_optimizations()

            if optimization_success:
                self.optimization_finished.emit(True, "网络优化启动成功")
            else:
                self.optimization_finished.emit(False, "部分网络优化启动失败，但EasyTier正常运行")

        except Exception as e:
            self.optimization_finished.emit(False, f"网络优化启动失败: {e}")


class EasyTierManager(QObject):
    """EasyTier管理器"""
    
    # 信号定义
    network_status_changed = Signal(bool)  # 网络状态变化
    peer_list_updated = Signal(list)       # 节点列表更新
    connection_info_updated = Signal(dict) # 连接信息更新
    error_occurred = Signal(str)           # 错误发生
    
    def __init__(self):
        super().__init__()

        # 路径配置
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent

        self.esr_dir = self.root_dir / "ESR"
        self.easytier_core = self.esr_dir / "easytier-core.exe"
        self.easytier_cli = self.esr_dir / "easytier-cli.exe"
        self.config_file = self.esr_dir / "easytier_config.json"  # 保留JSON配置用于兼容

        # 配置文件生成器
        self.config_generator = EasyTierConfigGenerator()

        # 进程管理
        self.easytier_process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.start_worker = None

        # 状态监控定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_status)

        # 网络优化器
        self.network_optimizer = NetworkOptimizer()
        self.network_optimizer.optimization_status_changed.connect(self._on_optimization_status_changed)
        self.network_optimizer.error_occurred.connect(self._on_optimization_error)

        # 网络优化工作线程
        self.optimization_worker = None

        # 确保目录存在
        self.esr_dir.mkdir(exist_ok=True)

        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 默认配置
                # 使用EasyTier对应的参数命名，默认启用所有高级选项
                default_config = {
                    "network_name": "",           # --network-name
                    "hostname": "",               # --hostname
                    "network_secret": "",         # --network-secret
                    "peers": ["tcp://public.easytier.top:11010"],  # --peers (默认只使用公共服务器)
                    "dhcp": True,                 # --dhcp (默认启用，与ipv4互斥)
                    # "ipv4": "10.126.126.1",    # --ipv4 (与dhcp互斥，不同时存在)
                    "disable_encryption": True,  # --disable-encryption (默认禁用加密，提升性能)
                    "disable_ipv6": False,       # --disable-ipv6 (默认不禁用，即启用IPv6)
                    "latency_first": True,       # --latency-first (默认启用)
                    "multi_thread": True,        # --multi-thread (默认启用)
                    # EasyTier网络加速选项
                    "enable_kcp_proxy": True,    # --enable-kcp-proxy (默认启用KCP代理)
                    "enable_quic_proxy": True,   # --enable-quic-proxy (默认启用QUIC代理)
                    "use_smoltcp": False,        # --use-smoltcp (默认禁用用户态网络栈，提升兼容性)
                    "enable_compression": True,  # --compression zstd (默认启用压缩)
                    # 网络优化配置
                    "network_optimization": {
                        "winip_broadcast": True,
                        "auto_metric": True
                    }
                }
                self.save_config(default_config)
                return default_config
        except Exception as e:
            print(f"加载EasyTier配置失败: {e}")
            return {}
    
    def save_config(self, config: Dict = None):
        """保存配置文件"""
        try:
            if config is None:
                config = self.config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.config = config
        except Exception as e:
            print(f"保存EasyTier配置失败: {e}")
    
    def is_easytier_installed(self) -> bool:
        """检查EasyTier是否已安装"""
        return self.easytier_core.exists() and self.easytier_cli.exists()

    def is_admin(self) -> bool:
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def check_wintun_driver(self) -> bool:
        """检查WinTUN驱动是否存在"""
        wintun_dll = self.esr_dir / "wintun.dll"
        return wintun_dll.exists()

    def start_network_with_config_file(self, network_name: str, network_secret: str = "",
                                      ipv4: str = "", peers: List[str] = None,
                                      hostname: str = "", dhcp: bool = True,
                                      listeners: List[str] = None,
                                      rpc_portal: str = "0.0.0.0:0",
                                      flags: Dict = None) -> bool:
        """
        使用配置文件启动EasyTier网络（推荐方式）

        Args:
            network_name: 网络名称
            network_secret: 网络密码
            ipv4: IPv4地址（非DHCP模式）
            peers: 对等节点列表
            hostname: 主机名（玩家名称）
            dhcp: 是否使用DHCP
            listeners: 监听地址列表
            rpc_portal: RPC门户地址

        Returns:
            是否启动成功
        """
        try:
            if self.is_running:
                self.error_occurred.emit("EasyTier网络已在运行中")
                return False

            # 检查EasyTier是否已安装
            if not self.is_easytier_installed():
                self.error_occurred.emit("EasyTier未安装\n请先下载并安装EasyTier")
                return False

            # 检查WinTUN驱动
            if not self.check_wintun_driver():
                self.error_occurred.emit("缺少WinTUN驱动文件(wintun.dll)\n请重新下载EasyTier")
                return False

            # 处理peers参数
            if peers is None:
                peers = ["tcp://public.easytier.top:11010"]  # 默认公共服务器
            elif isinstance(peers, str):
                peers = [peers]  # 转换为列表

            # 处理listeners参数
            if listeners is None:
                listeners = ["udp://0.0.0.0:11010"]

            # 构建flags配置（优先使用传入的flags，否则使用配置中的默认值）
            print(f"🔍 调试：传入的flags = {flags}")
            if flags is None:
                print("🔍 调试：flags为None，使用默认配置")
                flags = {
                    "enable_kcp_proxy": self.config.get("enable_kcp_proxy", True),
                    "enable_quic_proxy": self.config.get("enable_quic_proxy", True),
                    "latency_first": self.config.get("latency_first", True),
                    "multi_thread": self.config.get("multi_thread", True),
                    "enable_encryption": not self.config.get("disable_encryption", True),  # 转换为enable_encryption
                    "disable_ipv6": self.config.get("disable_ipv6", False),
                    "use_smoltcp": self.config.get("use_smoltcp", False),
                    "enable_compression": self.config.get("enable_compression", True)
                }
            else:
                print(f"🔍 调试：使用传入的flags，enable_encryption = {flags.get('enable_encryption')}")

            # 生成并保存配置文件
            success = self.config_generator.generate_and_save(
                network_name=network_name,
                network_secret=network_secret,
                hostname=hostname,
                peers=peers,
                dhcp=dhcp,
                ipv4=ipv4,
                listeners=listeners,
                rpc_portal=rpc_portal,
                flags=flags
            )

            if not success:
                self.error_occurred.emit("生成EasyTier配置文件失败")
                return False

            # 构建启动命令（使用配置文件）
            config_file_path = self.config_generator.get_config_file_path()
            cmd = [
                str(self.easytier_core),
                "--config-file", str(config_file_path)
            ]

            # 添加日志配置（覆盖配置文件中的设置）
            logs_dir = self.esr_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            cmd.extend(["--file-log-dir", str(logs_dir)])
            cmd.extend(["--file-log-level", "info"])
            cmd.extend(["--console-log-level", "warn"])

            print(f"🚀 启动EasyTier命令（配置文件模式）: {' '.join(cmd)}")

            # 保存配置到JSON文件（保持兼容性）
            update_config = {
                "network_name": network_name,
                "network_secret": network_secret,
                "peers": peers,
                "hostname": hostname
            }

            # IP配置：dhcp 和 ipv4 互斥
            if dhcp:
                update_config["dhcp"] = True
                self.config.pop("ipv4", None)
            else:
                update_config["ipv4"] = ipv4
                self.config.pop("dhcp", None)

            self.config.update(update_config)
            self.save_config()

            # 在后台线程中启动EasyTier
            self.start_worker = EasyTierStartWorker(self, cmd)
            self.start_worker.start_finished.connect(self._on_start_finished)
            self.start_worker.start()

            return True  # 返回True表示启动请求已发送

        except Exception as e:
            self.error_occurred.emit(f"启动EasyTier网络失败: {e}")
            return False

    def start_network(self, network_name: str, network_secret: str,
                     ipv4: str = "10.126.126.1",
                     peers: list = None,
                     hostname: str = "",
                     dhcp: bool = True) -> bool:
        """启动EasyTier网络"""
        try:
            if not self.is_easytier_installed():
                self.error_occurred.emit("EasyTier未安装，请先下载安装")
                return False

            if self.is_running:
                self.error_occurred.emit("EasyTier已在运行中")
                return False

            # 不再检查整个应用的管理员权限，而是以管理员权限启动EasyTier

            # 检查WinTUN驱动
            if not self.check_wintun_driver():
                self.error_occurred.emit("缺少WinTUN驱动文件(wintun.dll)\n请重新下载EasyTier")
                return False
            
            # 处理peers参数
            if peers is None:
                peers = ["tcp://public.easytier.top:11010"]  # 默认公共服务器
            elif isinstance(peers, str):
                peers = [peers]  # 转换为列表

            # 构建启动命令
            cmd = [
                str(self.easytier_core),
                "--network-name", network_name,
                "--network-secret", network_secret
            ]

            # 添加多个peers参数
            for peer in peers:
                cmd.extend(["--peers", peer])

            # 添加可选参数（统一使用true/false值，直接使用配置中的值）
            # 加密设置
            if self.config.get("disable_encryption", False):
                cmd.extend(["--disable-encryption", "true"])
            else:
                cmd.extend(["--disable-encryption", "false"])

            # IPv6设置
            if self.config.get("disable_ipv6", False):
                cmd.extend(["--disable-ipv6", "true"])
            else:
                cmd.extend(["--disable-ipv6", "false"])

            # 延迟优先设置
            if self.config.get("latency_first", True):
                cmd.extend(["--latency-first", "true"])
            else:
                cmd.extend(["--latency-first", "false"])

            # 多线程设置
            if self.config.get("multi_thread", True):
                cmd.extend(["--multi-thread", "true"])
            else:
                cmd.extend(["--multi-thread", "false"])

            # 添加IP配置（dhcp 和 ipv4 互斥）
            if dhcp:
                cmd.extend(["--dhcp"])
            elif ipv4:  # 只有在非DHCP且有IP地址时才添加ipv4参数
                cmd.extend(["--ipv4", ipv4])

            # 添加玩家名称（hostname）
            if hostname.strip():
                cmd.extend(["--hostname", hostname.strip()])

            # 添加EasyTier网络加速参数
            # KCP代理
            if self.config.get("enable_kcp_proxy", True):
                cmd.extend(["--enable-kcp-proxy", "true"])

            # QUIC代理
            if self.config.get("enable_quic_proxy", True):
                cmd.extend(["--enable-quic-proxy", "true"])

            # 用户态网络栈
            if self.config.get("use_smoltcp", True):
                cmd.extend(["--use-smoltcp", "true"])

            # 压缩算法
            if self.config.get("enable_compression", True):
                cmd.extend(["--compression", "zstd"])
            else:
                cmd.extend(["--compression", "none"])

            # 日志配置
            logs_dir = self.esr_dir / "logs"
            logs_dir.mkdir(exist_ok=True)  # 确保logs目录存在
            cmd.extend(["--file-log-dir", str(logs_dir)])
            cmd.extend(["--file-log-level", "info"])  # 设置文件日志级别
            cmd.extend(["--console-log-level", "warn"])  # 控制台只显示警告和错误

            # 移除空参数
            cmd = [arg for arg in cmd if arg]
            
            print(f"启动EasyTier命令: {' '.join(cmd)}")

            # 保存配置（提前保存，避免启动失败时丢失）
            # 更新配置（dhcp 和 ipv4 互斥）
            update_config = {
                "network_name": network_name,
                "network_secret": network_secret,
                "peers": peers,
                "hostname": hostname
            }

            # IP配置：dhcp 和 ipv4 互斥
            if dhcp:
                update_config["dhcp"] = True
                # 移除ipv4配置（如果存在）
                self.config.pop("ipv4", None)
            else:
                update_config["ipv4"] = ipv4
                # 移除dhcp配置（如果存在）
                self.config.pop("dhcp", None)

            self.config.update(update_config)
            self.save_config()

            # 在后台线程中启动EasyTier
            self.start_worker = EasyTierStartWorker(self, cmd)
            self.start_worker.start_finished.connect(self._on_start_finished)
            self.start_worker.start()

            return True  # 返回True表示启动请求已发送
                
        except Exception as e:
            self.error_occurred.emit(f"启动EasyTier网络失败: {e}")
            return False

    def _on_start_finished(self, success: bool, message: str, process):
        """启动完成回调"""
        if success and process:
            self.easytier_process = process
            self.is_running = True

            # 开始状态监控
            self.status_timer.start(5000)  # 每5秒检查一次

            self.network_status_changed.emit(True)
            print("EasyTier网络启动成功")
        else:
            self.is_running = False
            self.easytier_process = None

            # 分析具体错误原因
            error_message = self._analyze_error(message)
            self.error_occurred.emit(error_message)
            print(f"EasyTier启动失败: {message}")

        # 清理工作线程
        if self.start_worker:
            self.start_worker.deleteLater()
            self.start_worker = None
    
    def stop_network(self) -> bool:
        """停止EasyTier网络（优化版本，减少卡顿）"""
        try:
            # 停止状态监控
            self.status_timer.stop()

            # 终止进程（快速版本）
            if self.easytier_process:
                try:
                    self.easytier_process.terminate()

                    # 减少等待时间，避免卡顿
                    try:
                        self.easytier_process.wait(timeout=1)  # 从3秒减少到1秒
                    except:
                        # 如果1秒内没有结束，直接强制杀死
                        self.easytier_process.kill()
                        # 不再等待kill的结果，避免额外延迟

                except Exception as e:
                    print(f"终止EasyTier进程失败: {e}")

            # 快速重置状态，不等待进程清理完成
            self.is_running = False
            self.easytier_process = None
            self.network_status_changed.emit(False)

            # 异步清理残留进程，避免阻塞UI
            QTimer.singleShot(100, self._cleanup_remaining_processes)

            print("EasyTier网络已停止")
            return True

        except Exception as e:
            print(f"停止EasyTier网络失败: {e}")
            # 即使出错也要重置状态
            self.is_running = False
            self.easytier_process = None
            self.network_status_changed.emit(False)
            return False

    def _cleanup_remaining_processes(self):
        """异步清理残留进程，避免阻塞UI"""
        try:
            import psutil
            found_processes = []

            # 只查找easytier-core.exe进程，提高效率
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'easytier-core.exe':
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if found_processes:
                print(f"🧹 后台清理 {len(found_processes)} 个残留EasyTier进程...")
                for proc in found_processes:
                    try:
                        proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        print(f"清理进程 {proc.pid} 失败: {e}")

        except Exception as e:
            print(f"后台清理残留进程时出错: {e}")
    
    def get_network_status(self) -> Dict:
        """获取网络状态"""
        try:
            if not self.is_running or not self.easytier_process:
                return {"connected": False, "peers": [], "local_ip": "", "node_info": {}}

            # 获取节点信息和对等节点信息
            node_info = self._get_node_info()
            peers = self._get_peer_list()

            # 从节点信息中提取本机IP
            local_ip = node_info.get("ipv4_addr", self.config.get("peer_ip", ""))
            if "/" in local_ip:
                local_ip = local_ip.split("/")[0]  # 移除CIDR后缀

            return {
                "connected": True,
                "peers": peers,
                "local_ip": local_ip,
                "network_name": self.config.get("network_name", ""),
                "node_info": node_info
            }

        except Exception as e:
            print(f"获取网络状态失败: {e}")
            # 如果进程还在运行，则认为已连接
            if self.is_running and self.easytier_process and self.easytier_process.poll() is None:
                return {
                    "connected": True,
                    "peers": [],
                    "local_ip": self.config.get("peer_ip", ""),
                    "network_name": self.config.get("network_name", ""),
                    "node_info": {}
                }
            return {"connected": False, "peers": [], "local_ip": "", "node_info": {}}
    
    def _get_node_info(self) -> Dict:
        """获取节点信息"""
        try:
            cmd = [str(self.easytier_cli), "-o", "json", "node", "info"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            if result.returncode == 0 and result.stdout:
                import json
                return json.loads(result.stdout)
            else:
                print(f"获取节点信息失败: {result.stderr}")
                return {}
        except Exception as e:
            print(f"获取节点信息异常: {e}")
            return {}

    def _get_peer_list(self) -> List[Dict]:
        """获取对等节点列表"""
        try:
            cmd = [str(self.easytier_cli), "-o", "json", "peer", "list"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            if result.returncode == 0 and result.stdout:
                import json
                peer_data = json.loads(result.stdout)

                # 过滤掉本机节点和公共服务器节点
                peers = []
                for peer in peer_data:
                    # 跳过本机节点（cost为Local）和公共服务器节点（hostname包含PublicServer）
                    if (peer.get("cost") != "Local" and
                        not peer.get("hostname", "").startswith("PublicServer") and
                        peer.get("ipv4")):  # 确保有IP地址

                        peers.append({
                            "ip": peer.get("ipv4", ""),
                            "hostname": peer.get("hostname", ""),
                            "latency": peer.get("lat_ms", "unknown"),
                            "cost": peer.get("cost", ""),
                            "loss_rate": peer.get("loss_rate", ""),
                            "rx_bytes": peer.get("rx_bytes", ""),
                            "tx_bytes": peer.get("tx_bytes", ""),
                            "tunnel_proto": peer.get("tunnel_proto", ""),
                            "nat_type": peer.get("nat_type", ""),
                            "version": peer.get("version", ""),
                            "id": peer.get("id", "")
                        })

                return peers
            else:
                print(f"获取对等节点列表失败: {result.stderr}")
                return []
        except Exception as e:
            print(f"获取对等节点列表异常: {e}")
            return []
    
    def _check_status(self):
        """定期检查状态"""
        if self.easytier_process and self.easytier_process.poll() is not None:
            # 进程已结束
            self.is_running = False
            self.status_timer.stop()
            self.network_status_changed.emit(False)
            self.error_occurred.emit("EasyTier进程意外退出")
        else:
            # 获取并更新状态信息
            status = self.get_network_status()
            if status["connected"]:
                self.peer_list_updated.emit(status["peers"])
                self.connection_info_updated.emit(status)
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict):
        """更新配置"""
        self.config.update(new_config)
        self.save_config()

    def update_network_optimization_config(self, optimization_config: Dict):
        """更新网络优化配置"""
        try:
            if "network_optimization" not in self.config:
                self.config["network_optimization"] = {}

            self.config["network_optimization"].update(optimization_config)
            self.save_config()
            print(f"✅ 网络优化配置已同步到 easytier_config.json")

        except Exception as e:
            print(f"❌ 同步网络优化配置失败: {e}")

    def get_network_optimization_config(self) -> Dict:
        """获取网络优化配置"""
        return self.config.get("network_optimization", {
            "winip_broadcast": True,
            "auto_metric": True
        })

    def _start_as_admin(self, cmd: list) -> subprocess.Popen:
        """以管理员权限启动进程"""
        try:
            if sys.platform == "win32":
                # Windows下使用ShellExecute以管理员权限启动
                import ctypes
                from ctypes import wintypes

                # 使用ShellExecuteW以管理员权限启动
                shell32 = ctypes.windll.shell32

                # 构建参数字符串
                args = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd[1:])

                # 以管理员权限启动
                result = shell32.ShellExecuteW(
                    None,                    # hwnd
                    "runas",                 # lpOperation (以管理员身份运行)
                    cmd[0],                  # lpFile (可执行文件路径)
                    args,                    # lpParameters (参数)
                    str(self.esr_dir),       # lpDirectory (工作目录)
                    0                        # nShowCmd (隐藏窗口)
                )

                if result > 32:  # 成功
                    # 等待进程启动
                    time.sleep(3)

                    # 查找EasyTier进程
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if proc.info['name'] == 'easytier-core.exe':
                                # 创建一个伪Popen对象来管理进程
                                class AdminProcess:
                                    def __init__(self, pid):
                                        self.pid = pid
                                        self.returncode = None
                                        self.stdout = None  # 管理员进程无法获取stdout
                                        self.stderr = None  # 管理员进程无法获取stderr

                                    def poll(self):
                                        try:
                                            proc = psutil.Process(self.pid)
                                            return None if proc.is_running() else 1
                                        except:
                                            return 1

                                    def terminate(self):
                                        try:
                                            proc = psutil.Process(self.pid)
                                            proc.terminate()
                                        except:
                                            pass

                                    def kill(self):
                                        try:
                                            proc = psutil.Process(self.pid)
                                            proc.kill()
                                        except:
                                            pass

                                    def wait(self, timeout=None):
                                        try:
                                            proc = psutil.Process(self.pid)
                                            proc.wait(timeout)
                                        except:
                                            pass

                                print(f"找到EasyTier进程，PID: {proc.info['pid']}")
                                return AdminProcess(proc.info['pid'])
                        except:
                            continue

                    # 如果没找到进程，可能启动失败了
                    raise Exception("未找到启动的EasyTier进程")
                else:
                    raise Exception(f"ShellExecute失败，错误代码: {result}")
            else:
                # 非Windows系统，使用sudo
                sudo_cmd = ["sudo"] + cmd
                return subprocess.Popen(
                    sudo_cmd,
                    cwd=str(self.esr_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
        except Exception as e:
            print(f"以管理员权限启动失败: {e}")
            print("回退到普通权限启动...")
            # 回退到普通权限启动
            return subprocess.Popen(
                cmd,
                cwd=str(self.esr_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

    def _analyze_error(self, error_output: str) -> str:
        """分析错误输出，提供用户友好的错误信息"""
        if "Failed to create adapter" in error_output:
            return ("虚拟网络适配器创建失败\n\n可能的解决方案：\n"
                   "1. 检查防火墙/杀毒软件是否阻止\n"
                   "2. 重启计算机后重试\n"
                   "3. 检查Windows版本兼容性\n"
                   "4. 尝试手动以管理员身份运行")
        elif "Permission denied" in error_output or "Access denied" in error_output:
            return ("权限不足\n\n程序已尝试以管理员权限启动EasyTier")
        elif "Address already in use" in error_output:
            return ("网络地址已被占用\n\n请尝试使用不同的IP地址")
        elif "Network unreachable" in error_output:
            return ("网络不可达\n\n请检查网络连接和服务器地址")
        elif "Connection refused" in error_output:
            return ("连接被拒绝\n\n请检查服务器地址和端口")
        else:
            # 返回原始错误信息，但格式化一下
            return f"EasyTier启动失败\n\n详细错误信息：\n{error_output}"

    def _on_optimization_status_changed(self, optimization_name: str, enabled: bool):
        """网络优化状态变化回调"""
        status = "启用" if enabled else "禁用"
        print(f"🔧 网络优化: {optimization_name} {status}")

    def _on_optimization_error(self, error_message: str):
        """网络优化错误回调"""
        print(f"❌ 网络优化错误: {error_message}")
        self.error_occurred.emit(f"网络优化错误: {error_message}")

    def start_with_optimization(self, config: Optional[Dict] = None) -> bool:
        """启动EasyTier并应用网络优化（已弃用）"""
        print("⚠️ start_with_optimization方法已弃用，请使用start_network_with_optimization")
        return False

    def stop_with_optimization(self):
        """停止EasyTier并清理网络优化"""
        try:
            # 停止网络优化
            print("🛑 停止网络优化...")
            self.network_optimizer.stop_all_optimizations()

            # 停止EasyTier
            self.stop_network()

            print("✅ EasyTier和网络优化已停止")

        except Exception as e:
            print(f"❌ 停止EasyTier和网络优化失败: {e}")

    def get_optimization_status(self) -> Dict[str, bool]:
        """获取网络优化状态"""
        return self.network_optimizer.get_optimization_status()

    def toggle_winip_broadcast(self, enabled: bool) -> bool:
        """切换WinIPBroadcast状态"""
        if enabled:
            return self.network_optimizer.start_winip_broadcast()
        else:
            self.network_optimizer.stop_winip_broadcast()
            return True

    def refresh_network_metric(self) -> bool:
        """刷新网卡跃点优化"""
        return self.network_optimizer.optimize_network_metric()

    def start_network_with_optimization(self, network_name: str, network_secret: str = "",
                                      ipv4: str = "", peers: List[str] = None,
                                      hostname: str = "", dhcp: bool = True,
                                      network_optimization: Dict = None,
                                      flags: Dict = None) -> bool:
        """启动网络并应用优化（使用配置文件模式）"""
        try:
            # 如果提供了网络优化配置，同步到 easytier_config.json
            if network_optimization:
                self.update_network_optimization_config(network_optimization)

            # 使用配置文件模式启动EasyTier网络
            if not self.start_network_with_config_file(
                network_name=network_name,
                network_secret=network_secret,
                ipv4=ipv4,
                peers=peers,
                hostname=hostname,
                dhcp=dhcp,
                flags=flags  # 传递flags参数
            ):
                return False

            # 异步启动网络优化，避免阻塞UI
            self._start_optimization_async()

            return True

        except Exception as e:
            print(f"❌ 启动网络和优化失败: {e}")
            self.error_occurred.emit(f"启动失败: {e}")
            return False

    def _start_optimization_async(self):
        """异步启动网络优化"""
        try:
            # 创建网络优化工作线程
            self.optimization_worker = NetworkOptimizationWorker(self.network_optimizer)

            # 连接信号并启动线程
            self.optimization_worker.optimization_finished.connect(self._on_optimization_finished)
            self.optimization_worker.start()

        except Exception as e:
            print(f"❌ 启动网络优化线程失败: {e}")

    def _on_optimization_finished(self, success: bool, message: str):
        """网络优化完成回调"""
        if success:
            print(f"✅ {message}")
        else:
            print(f"⚠️ {message}")

        # 清理工作线程
        if self.optimization_worker:
            self.optimization_worker.deleteLater()
            self.optimization_worker = None

    def stop_network_with_optimization(self) -> bool:
        """停止网络并清理优化"""
        try:
            # 停止网络优化工作线程
            if self.optimization_worker and self.optimization_worker.isRunning():
                self.optimization_worker.terminate()
                self.optimization_worker.wait(3000)  # 等待3秒
                self.optimization_worker = None

            self.stop_with_optimization()
            return True
        except Exception as e:
            print(f"❌ 停止网络和优化失败: {e}")
            return False
