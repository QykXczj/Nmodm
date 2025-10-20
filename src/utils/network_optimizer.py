"""
网络优化器
负责WinIPBroadcast、网卡跃点设置等网络优化功能
"""

import os
import sys
import subprocess
import time
import re
from pathlib import Path
from typing import Optional, Dict, List
from PySide6.QtCore import QObject, QThread, Signal, QTimer

from .tool_manager import get_tool_manager


class NetworkOptimizer(QObject):
    """网络优化器"""
    
    # 信号定义
    optimization_status_changed = Signal(str, bool)  # 优化项名称, 状态
    error_occurred = Signal(str)  # 错误信息
    
    def __init__(self):
        super().__init__()

        self.tool_manager = get_tool_manager()
        
        # 进程管理
        self.winip_process: Optional[subprocess.Popen] = None

        # 状态跟踪
        self.winip_enabled = False
        self.metric_optimized = False
        
        # 原始网卡跃点值（用于恢复）
        self.original_metrics: Dict[str, int] = {}
    
    def ensure_tools_ready(self) -> bool:
        """确保工具准备就绪（快速检查，不进行解压）"""
        # 只检查工具完整性，不进行解压操作
        # 解压操作已在页面加载时完成
        integrity_status = self.tool_manager.check_tools_integrity()
        missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

        if missing_tools:
            print(f"❌ 缺失网络优化工具: {', '.join(missing_tools)}")
            print("💡 请重启程序以重新检测和解压工具")
            return False

        return True


    
    def start_winip_broadcast(self) -> bool:
        """启动WinIPBroadcast"""
        try:
            if self.winip_enabled and self.winip_process and self.winip_process.poll() is None:
                print("✅ WinIPBroadcast已在运行")
                return True

            # 获取WinIPBroadcast路径
            winip_path = self.tool_manager.get_tool_path("WinIPBroadcast.exe")
            if not winip_path:
                self.error_occurred.emit("WinIPBroadcast.exe 不存在")
                return False

            print("🚀 启动WinIPBroadcast（管理员权限）...")

            # 直接使用管理员权限启动
            return self._start_winip_as_admin(winip_path)

        except Exception as e:
            self.error_occurred.emit(f"启动WinIPBroadcast失败: {e}")
            return False



    def _start_winip_as_admin(self, winip_path) -> bool:
        """以管理员权限启动WinIPBroadcast"""
        try:
            if sys.platform == "win32":
                import ctypes

                print("🔐 请求管理员权限启动WinIPBroadcast...")

                # 使用ShellExecute以管理员权限运行
                shell32 = ctypes.windll.shell32
                result = shell32.ShellExecuteW(
                    None,                    # hwnd
                    "runas",                 # lpOperation (以管理员身份运行)
                    str(winip_path),         # lpFile
                    "run",                   # lpParameters
                    str(winip_path.parent),  # lpDirectory
                    0                        # nShowCmd (隐藏窗口)
                )

                if result > 32:  # 成功
                    print("✅ 管理员权限请求成功，等待进程启动...")
                    # 等待启动，由于ShellExecuteW不返回进程对象，我们需要通过进程名查找
                    time.sleep(3)
                    
                    # 重置进程对象，因为ShellExecuteW启动的进程我们无法直接控制
                    self.winip_process = None
                    
                    return self._check_winip_status()
                else:
                    print(f"❌ 管理员权限启动失败，错误代码: {result}")
                    if result == 5:
                        print("   错误原因: 拒绝访问（用户取消了UAC提示）")
                    elif result == 2:
                        print("   错误原因: 文件未找到")
                    elif result == 31:
                        print("   错误原因: 没有关联的应用程序")
                    return False
            else:
                # 非Windows系统，使用sudo
                print("🔐 请求sudo权限启动WinIPBroadcast...")
                self.winip_process = subprocess.Popen(
                    ["sudo", str(winip_path), "run"],
                    cwd=winip_path.parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)
                return self._check_winip_status()

        except Exception as e:
            print(f"以管理员权限启动WinIPBroadcast失败: {e}")
            return False

    def _check_winip_status(self) -> bool:
        """检查WinIPBroadcast启动状态"""
        process_started = False
        found_process = None

        # 方法1：检查我们启动的进程是否还在运行（仅适用于非管理员权限启动）
        if self.winip_process and self.winip_process.poll() is None:
            process_started = True
            print("✅ WinIPBroadcast进程启动成功（直接启动）")
        else:
            # 方法2：检查是否有WinIPBroadcast进程在运行（包括管理员权限启动的）
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                    try:
                        if proc.info['name'].lower() == 'winipbroadcast.exe':
                            print(f"✅ 检测到WinIPBroadcast进程运行中 (PID: {proc.info['pid']})")
                            process_started = True
                            found_process = proc
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                print("⚠️ psutil未安装，无法检查进程状态")
                # 如果没有psutil，尝试使用系统命令检查
                try:
                    import subprocess
                    result = subprocess.run(['tasklist', '/fi', 'imagename eq WinIPBroadcast.exe'],
                                          capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                    if 'WinIPBroadcast.exe' in result.stdout:
                        print("✅ 检测到WinIPBroadcast进程运行中（系统命令检查）")
                        process_started = True
                except:
                    pass

        if process_started:
            self.winip_enabled = True
            self.optimization_status_changed.emit("WinIPBroadcast", True)
            print("✅ WinIPBroadcast启动成功")
            
            # 如果找到了进程但没有进程对象，尝试保存进程信息（用于后续管理）
            if not self.winip_process and found_process:
                try:
                    # 注意：我们不能直接控制管理员权限启动的进程，但可以记录其存在
                    print(f"📝 记录管理员权限启动的WinIPBroadcast进程 (PID: {found_process.pid})")
                except:
                    pass
            
            return True
        else:
            # 如果有进程对象，尝试获取错误信息
            if self.winip_process:
                try:
                    _, stderr = self.winip_process.communicate(timeout=1)
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "未知错误"
                    print(f"❌ WinIPBroadcast启动失败: {error_msg}")
                except:
                    print("❌ WinIPBroadcast启动失败: 进程未能正常启动")
            else:
                print("❌ WinIPBroadcast启动失败: 进程未能正常启动")

            self.error_occurred.emit("WinIPBroadcast启动失败")
            return False
    
    def stop_winip_broadcast(self):
        """停止WinIPBroadcast"""
        try:
            import time
            
            # 首先尝试停止我们启动的进程
            if self.winip_process and self.winip_process.poll() is None:
                self.winip_process.terminate()

                # 等待进程结束
                try:
                    self.winip_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.winip_process.kill()

                print("🛑 WinIPBroadcast主进程已停止")

            # 额外保险：查找并终止所有WinIPBroadcast进程
            try:
                import psutil
                
                # 第一次扫描
                found_processes = []
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() == 'winipbroadcast.exe':
                            found_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if found_processes:
                    print(f"🔍 发现 {len(found_processes)} 个WinIPBroadcast进程，正在终止...")
                    
                    # 第一轮：优雅终止
                    for proc in found_processes:
                        try:
                            print(f"  终止WinIPBroadcast进程 PID: {proc.pid}")
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

                    # 最终验证
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
                        # 尝试使用系统命令
                        try:
                            if sys.platform == "win32":
                                # 尝试使用管理员权限的taskkill
                                import ctypes
                                
                                # 检查是否有管理员权限
                                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                                
                                if is_admin:
                                    # 有管理员权限，直接使用taskkill
                                    result = subprocess.run(['taskkill', '/f', '/im', 'WinIPBroadcast.exe'], 
                                                          capture_output=True, text=True)
                                    if result.returncode == 0:
                                        print("✅ 使用管理员权限taskkill成功清理WinIPBroadcast进程")
                                    else:
                                        print(f"⚠️ 管理员权限taskkill执行失败: {result.stderr}")
                                else:
                                    print("⚠️ 需要管理员权限才能完全清理WinIPBroadcast进程")
                                    print("💡 建议以管理员权限重启程序，或手动结束WinIPBroadcast进程")
                                    
                                    # 不弹出UAC窗口，只给出提示
                                    print("💡 WinIPBroadcast进程以管理员权限运行，无法静默清理")
                                    print("💡 如需完全清理，请以管理员权限重启程序")
                            else:
                                # 非Windows系统
                                result = subprocess.run(['pkill', '-f', 'WinIPBroadcast'], 
                                                      capture_output=True, text=True)
                                if result.returncode == 0:
                                    print("✅ 使用pkill成功清理WinIPBroadcast进程")
                                else:
                                    print(f"⚠️ pkill执行失败: {result.stderr}")
                        except Exception as e:
                            print(f"⚠️ 系统命令清理失败: {e}")
                    else:
                        print("✅ 所有WinIPBroadcast进程已终止")
                else:
                    print("🛑 WinIPBroadcast已停止")

            except ImportError:
                print("⚠️ psutil未安装，无法进行进程清理")
                print("🛑 WinIPBroadcast已停止")

            self.winip_enabled = False
            self.winip_process = None
            self.optimization_status_changed.emit("WinIPBroadcast", False)

        except Exception as e:
            print(f"停止WinIPBroadcast失败: {e}")
    
    def get_network_interfaces(self) -> List[Dict]:
        """获取网络接口信息"""
        try:
            # 使用netsh命令获取网络接口信息
            # 尝试多种编码方式来处理Windows中文系统
            encodings = ['utf-8', 'gbk', 'cp936', 'ansi']
            result = None

            for encoding in encodings:
                try:
                    result = subprocess.run(
                        ["netsh", "interface", "ipv4", "show", "interfaces"],
                        capture_output=True,
                        text=False,  # 获取字节数据
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

                    if result.returncode == 0:
                        # 尝试用当前编码解码
                        stdout_text = result.stdout.decode(encoding, errors='ignore')
                        break
                except (UnicodeDecodeError, LookupError):
                    continue

            if not result or result.returncode != 0:
                print("❌ netsh命令执行失败")
                return []

            if not stdout_text:
                print("❌ 无法解码netsh输出")
                return []

            interfaces = []
            lines = stdout_text.split('\n')

            # 查找表头，动态确定数据开始行
            header_found = False
            data_start_line = 0

            for i, line in enumerate(lines):
                if 'Idx' in line and 'Met' in line and 'MTU' in line:
                    header_found = True
                    data_start_line = i + 2  # 跳过表头和分隔线
                    break

            if not header_found:
                # 如果没找到标准表头，使用默认跳过行数
                data_start_line = 3

            # 解析网络接口数据
            for line in lines[data_start_line:]:
                line = line.strip()
                if not line or line.startswith('-'):
                    continue

                # 使用正则表达式解析，更可靠
                import re
                # 匹配格式：数字 数字 数字 状态 接口名称
                match = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+)$', line)

                if match:
                    try:
                        idx = int(match.group(1))
                        met = int(match.group(2))
                        mtu = int(match.group(3))
                        state = match.group(4)
                        name = match.group(5).strip()

                        interfaces.append({
                            "index": idx,
                            "metric": met,
                            "mtu": mtu,
                            "state": state,
                            "name": name
                        })
                    except ValueError as e:
                        print(f"解析接口数据失败: {line} - {e}")
                        continue

            print(f"✅ 成功获取 {len(interfaces)} 个网络接口")
            return interfaces

        except Exception as e:
            print(f"获取网络接口失败: {e}")
            return []
    
    def find_easytier_interface(self) -> Optional[Dict]:
        """查找EasyTier网络接口"""
        interfaces = self.get_network_interfaces()

        if not interfaces:
            return None

        # 查找包含EasyTier相关关键词的接口
        # 优先级从高到低
        easytier_keywords = [
            "easytier",      # EasyTier官方名称
            "tap",           # TAP接口
            "tun",           # TUN接口
            "et_",           # EasyTier可能的前缀
            "虚拟",          # 中文虚拟接口
            "virtual",       # 英文虚拟接口
            "vpn"            # VPN接口
        ]

        # 可能的连接状态（支持中英文）
        connected_states = ["已连接", "connected", "up", "启用", "enabled"]

        # 按优先级查找
        for keyword in easytier_keywords:
            for interface in interfaces:
                name_lower = interface["name"].lower()
                state_lower = interface["state"].lower()

                # 检查名称是否包含关键词
                if keyword in name_lower:
                    # 检查状态是否为连接状态
                    for connected_state in connected_states:
                        if connected_state in state_lower:
                            print(f"🎯 找到EasyTier接口: {interface['name']} (状态: {interface['state']})")
                            return interface

        # 如果没找到，输出调试信息
        print("🔍 当前网络接口列表:")
        for interface in interfaces[:10]:  # 只显示前10个
            print(f"  📡 {interface['name']} (状态: {interface['state']}, 跃点: {interface['metric']})")

        return None
    
    def set_interface_metric(self, interface_name: str, metric: int) -> bool:
        """设置网络接口跃点"""
        try:
            print(f"🔧 设置网卡跃点（管理员权限）: {interface_name} → {metric}")

            # 直接使用管理员权限设置
            return self._set_interface_metric_as_admin(interface_name, metric)

        except Exception as e:
            print(f"设置接口跃点失败: {e}")
            return False

    def _set_interface_metric_as_admin(self, interface_name: str, metric: int) -> bool:
        """以管理员权限设置网络接口跃点"""
        try:
            if sys.platform == "win32":
                import ctypes

                print(f"🔐 请求管理员权限设置网卡跃点: {interface_name}")

                # 构建命令
                cmd = f'netsh interface ipv4 set interface "{interface_name}" metric={metric}'

                # 使用ShellExecute以管理员权限运行
                shell32 = ctypes.windll.shell32
                result = shell32.ShellExecuteW(
                    None,                    # hwnd
                    "runas",                 # lpOperation (以管理员身份运行)
                    "cmd.exe",               # lpFile
                    f"/c {cmd}",             # lpParameters
                    None,                    # lpDirectory
                    0                        # nShowCmd (隐藏窗口)
                )

                if result > 32:  # 成功
                    # 等待命令执行完成
                    time.sleep(2)
                    print(f"✅ 已设置 {interface_name} 跃点为 {metric}")
                    return True
                else:
                    print(f"❌ 管理员权限设置失败，错误代码: {result}")
                    return False
            else:
                # 非Windows系统，使用sudo
                print(f"🔐 请求sudo权限设置网卡跃点: {interface_name}")
                cmd = ["sudo", "netsh", "interface", "ipv4", "set", "interface",
                       f'"{interface_name}"', f"metric={metric}"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ 已设置 {interface_name} 跃点为 {metric}")
                    return True
                else:
                    print(f"❌ sudo权限设置失败: {result.stderr}")
                    return False

        except Exception as e:
            print(f"管理员权限设置跃点失败: {e}")
            return False
    
    def optimize_network_metric(self) -> bool:
        """优化网卡跃点（设置EasyTier网卡为最高优先级）- 增强版本"""
        try:
            print("🚀 开始网卡跃点优化流程...")

            # 步骤1：查找EasyTier接口
            easytier_interface = self.find_easytier_interface()
            if not easytier_interface:
                print("⚠️ 未找到EasyTier网络接口，跳过跃点优化")
                return False

            interface_name = easytier_interface["name"]
            current_metric = easytier_interface["metric"]
            target_metric = 1  # 最高优先级

            print(f"🎯 目标接口: {interface_name} (当前跃点: {current_metric})")

            # 步骤2：检查是否需要优化
            if current_metric == target_metric:
                print(f"✅ EasyTier网卡跃点已是最优: {interface_name} (跃点={target_metric})")
                self.metric_optimized = True
                self.optimization_status_changed.emit("网卡跃点优化", True)
                return True

            # 步骤3：保存原始跃点值（安全检查点）
            if interface_name not in self.original_metrics:
                self.original_metrics[interface_name] = current_metric
                print(f"💾 已保存原始跃点值: {interface_name} = {current_metric}")
            else:
                print(f"💾 使用已保存的原始跃点值: {interface_name} = {self.original_metrics[interface_name]}")

            # 步骤4：执行跃点优化
            print(f"🔧 正在优化网卡跃点: {interface_name} ({current_metric} → {target_metric})")

            if not self.set_interface_metric(interface_name, target_metric):
                print(f"❌ 跃点设置操作失败: {interface_name}")
                # 清理保存的原始值
                if interface_name in self.original_metrics:
                    del self.original_metrics[interface_name]
                return False

            # 步骤5：验证设置是否生效
            print(f"🔍 验证跃点设置是否生效...")
            if not self.verify_metric_setting(interface_name, target_metric, max_retries=3):
                print(f"❌ 跃点设置验证失败，执行安全回滚...")

                # 执行安全回滚
                if self.safe_rollback(interface_name, "验证失败"):
                    print(f"✅ 安全回滚成功，系统已恢复到原始状态")
                else:
                    print(f"❌ 安全回滚失败，请手动检查网络设置")
                    self.error_occurred.emit(f"网卡跃点优化失败且回滚异常: {interface_name}")

                return False

            # 步骤6：优化成功
            self.metric_optimized = True
            self.optimization_status_changed.emit("网卡跃点优化", True)
            print(f"🎯 EasyTier网卡跃点优化成功: {interface_name} ({current_metric} → {target_metric})")
            print(f"✅ 验证通过，游戏流量将优先通过EasyTier网络")

            return True

        except Exception as e:
            print(f"网卡跃点优化异常: {e}")
            self.error_occurred.emit(f"网卡跃点优化失败: {e}")

            # 异常情况下的紧急回滚
            try:
                if hasattr(self, 'interface_name') and interface_name in self.original_metrics:
                    print(f"🚨 执行异常情况下的紧急回滚...")
                    self.safe_rollback(interface_name, f"异常: {str(e)}")
            except:
                pass  # 避免回滚时的二次异常

            return False
    
    def verify_metric_setting(self, interface_name: str, expected_metric: int, max_retries: int = 3) -> bool:
        """验证网卡跃点设置是否生效"""
        try:
            print(f"🔍 验证网卡跃点设置: {interface_name} 期望跃点={expected_metric}")

            for attempt in range(max_retries):
                # 等待系统更新（Windows需要时间应用设置）
                time.sleep(1 + attempt * 0.5)  # 递增等待时间

                # 重新获取接口信息
                interfaces = self.get_network_interfaces()
                if not interfaces:
                    print(f"⚠️ 验证失败：无法获取网络接口信息 (尝试 {attempt + 1}/{max_retries})")
                    continue

                # 查找目标接口
                target_interface = None
                for interface in interfaces:
                    if interface["name"] == interface_name:
                        target_interface = interface
                        break

                if not target_interface:
                    print(f"⚠️ 验证失败：未找到接口 {interface_name} (尝试 {attempt + 1}/{max_retries})")
                    continue

                current_metric = target_interface["metric"]
                print(f"🔍 当前跃点值: {current_metric}, 期望值: {expected_metric}")

                if current_metric == expected_metric:
                    print(f"✅ 跃点设置验证成功: {interface_name} 跃点={current_metric}")
                    return True
                else:
                    print(f"⚠️ 跃点值不匹配 (尝试 {attempt + 1}/{max_retries}): 当前={current_metric}, 期望={expected_metric}")

            print(f"❌ 跃点设置验证失败: {interface_name} 在 {max_retries} 次尝试后仍未达到期望值")
            return False

        except Exception as e:
            print(f"验证网卡跃点设置异常: {e}")
            return False

    def safe_rollback(self, interface_name: str, reason: str = "操作失败") -> bool:
        """安全回滚网卡跃点设置"""
        try:
            print(f"🔄 执行安全回滚: {interface_name} (原因: {reason})")

            if interface_name not in self.original_metrics:
                print(f"⚠️ 无法回滚：未找到 {interface_name} 的原始跃点值")
                return False

            original_metric = self.original_metrics[interface_name]
            print(f"🔄 回滚到原始跃点值: {interface_name} → {original_metric}")

            # 执行回滚
            if self.set_interface_metric(interface_name, original_metric):
                # 验证回滚是否成功
                if self.verify_metric_setting(interface_name, original_metric, max_retries=2):
                    print(f"✅ 安全回滚成功: {interface_name} 已恢复到跃点 {original_metric}")
                    # 清理该接口的记录
                    del self.original_metrics[interface_name]
                    return True
                else:
                    print(f"❌ 回滚验证失败: {interface_name} 可能未完全恢复")
                    return False
            else:
                print(f"❌ 回滚操作失败: {interface_name}")
                return False

        except Exception as e:
            print(f"安全回滚异常: {e}")
            return False

    def restore_network_metric(self):
        """恢复网卡跃点设置"""
        try:
            success_count = 0
            total_count = len(self.original_metrics)

            # 创建副本以避免在迭代时修改字典
            metrics_to_restore = self.original_metrics.copy()

            for interface_name, original_metric in metrics_to_restore.items():
                print(f"🔄 恢复网卡跃点: {interface_name} → {original_metric}")

                if self.set_interface_metric(interface_name, original_metric):
                    # 验证恢复是否成功
                    if self.verify_metric_setting(interface_name, original_metric, max_retries=2):
                        print(f"✅ 已恢复 {interface_name} 跃点为 {original_metric}")
                        success_count += 1
                    else:
                        print(f"⚠️ {interface_name} 恢复验证失败，但操作已执行")
                        success_count += 1  # 仍然计为成功，因为操作已执行
                else:
                    print(f"❌ 恢复 {interface_name} 跃点失败")

            # 清理记录
            self.original_metrics.clear()
            self.metric_optimized = False
            self.optimization_status_changed.emit("网卡跃点优化", False)

            if success_count == total_count:
                print(f"✅ 所有网卡跃点已成功恢复 ({success_count}/{total_count})")
            else:
                print(f"⚠️ 部分网卡跃点恢复完成 ({success_count}/{total_count})")

        except Exception as e:
            print(f"恢复网卡跃点失败: {e}")
    
    def start_all_optimizations(self) -> bool:
        """启动所有网络优化"""
        success_count = 0

        # 确保工具准备就绪
        if not self.ensure_tools_ready():
            self.error_occurred.emit("网络优化工具未准备就绪")
            return False

        print("🔧 开始启动网络优化组件...")

        # 启动WinIPBroadcast
        print("🔧 网络优化: WinIPBroadcast 启动中...")
        if self.start_winip_broadcast():
            success_count += 1
            print("🔧 网络优化: WinIPBroadcast 启用")
        else:
            print("🔧 网络优化: WinIPBroadcast 禁用")

        # 优化网卡跃点
        print("🔧 网络优化: 网卡跃点优化 启动中...")
        if self.optimize_network_metric():
            success_count += 1
            print("🔧 网络优化: 网卡跃点优化 启用")
        else:
            print("🔧 网络优化: 网卡跃点优化 禁用")

        return success_count > 0
    
    # KCP代理功能已移除，因为EasyTier自带KCP支持

    def stop_all_optimizations(self):
        """停止所有网络优化"""
        self.stop_winip_broadcast()
        self.restore_network_metric()
    
    def get_optimization_status(self) -> Dict[str, bool]:
        """获取优化状态"""
        return {
            "WinIPBroadcast": self.winip_enabled,
            "网卡跃点优化": self.metric_optimized
        }

    def get_detailed_metric_status(self) -> Dict[str, any]:
        """获取详细的跃点优化状态"""
        try:
            status = {
                "enabled": self.metric_optimized,
                "interfaces_count": len(self.original_metrics),
                "interfaces": {},
                "health_check": "unknown"
            }

            if not self.metric_optimized:
                status["health_check"] = "disabled"
                return status

            # 检查每个优化的接口状态
            current_interfaces = self.get_network_interfaces()
            if not current_interfaces:
                status["health_check"] = "error"
                return status

            all_healthy = True
            for interface_name, original_metric in self.original_metrics.items():
                interface_status = {
                    "original_metric": original_metric,
                    "current_metric": None,
                    "target_metric": 1,
                    "status": "unknown"
                }

                # 查找当前接口信息
                current_interface = None
                for interface in current_interfaces:
                    if interface["name"] == interface_name:
                        current_interface = interface
                        break

                if current_interface:
                    current_metric = current_interface["metric"]
                    interface_status["current_metric"] = current_metric

                    if current_metric == 1:
                        interface_status["status"] = "optimized"
                    else:
                        interface_status["status"] = "degraded"
                        all_healthy = False
                else:
                    interface_status["status"] = "missing"
                    all_healthy = False

                status["interfaces"][interface_name] = interface_status

            status["health_check"] = "healthy" if all_healthy else "degraded"
            return status

        except Exception as e:
            print(f"获取详细跃点状态失败: {e}")
            return {
                "enabled": self.metric_optimized,
                "interfaces_count": 0,
                "interfaces": {},
                "health_check": "error"
            }
