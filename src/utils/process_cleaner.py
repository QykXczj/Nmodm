#!/usr/bin/env python3
"""
进程清理工具
专门用于清理WinIPBroadcast等后台进程
"""
import sys
import time
import subprocess
import os
from typing import List, Tuple


class ProcessCleaner:
    """进程清理器"""
    
    def __init__(self):
        self.is_admin = self._check_admin_privileges()
    
    def _check_admin_privileges(self) -> bool:
        """检查是否有管理员权限"""
        if sys.platform == "win32":
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            except:
                return False
        else:
            return os.geteuid() == 0
    
    def find_winip_processes(self) -> List[Tuple[int, str]]:
        """查找WinIPBroadcast进程"""
        try:
            import psutil
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if proc.info['name'].lower() == 'winipbroadcast.exe':
                        processes.append((proc.info['pid'], proc.info['status']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return processes
        except ImportError:
            print("⚠️ psutil未安装，无法检查进程")
            return []
        except Exception as e:
            print(f"❌ 查找进程失败: {e}")
            return []
    
    def cleanup_winip_processes(self, callback=None) -> bool:
        """
        清理WinIPBroadcast进程
        
        Args:
            callback: 回调函数，用于更新UI状态
        
        Returns:
            bool: 清理是否成功
        """
        try:
            import psutil
            
            def log(message, level="info"):
                print(message)
                if callback:
                    callback(message, level)
            
            # 第一次扫描
            found_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'winipbroadcast.exe':
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found_processes:
                log("🔍 未发现WinIPBroadcast进程")
                return True
            
            log(f"🔍 发现 {len(found_processes)} 个WinIPBroadcast进程，正在清理...", "info")
            
            # 第一轮：优雅终止
            log("第一阶段：尝试优雅终止进程...")
            for proc in found_processes:
                try:
                    log(f"  终止进程 PID: {proc.pid}")
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    log(f"  终止进程 {proc.pid} 失败: {e}", "warning")
            
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
                log(f"第二阶段：强制终止 {len(remaining_processes)} 个进程...")
                for proc in remaining_processes:
                    try:
                        log(f"  强制终止进程 PID: {proc.pid}")
                        proc.kill()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        log(f"  强制终止进程 {proc.pid} 失败: {e}", "warning")
            
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
                log(f"⚠️ 仍有 {len(final_check)} 个WinIPBroadcast进程未能清理", "warning")
                
                # 尝试系统命令清理
                success = self._cleanup_with_system_command(log)
                if success:
                    return True
                else:
                    log("⚠️ 部分进程可能需要管理员权限才能清理", "warning")
                    if not self.is_admin:
                        log("💡 建议以管理员权限重启程序，或手动结束进程", "info")
                    return False
            else:
                log("✅ 所有WinIPBroadcast进程已成功清理", "info")
                return True
                
        except ImportError:
            print("❌ psutil未安装，无法进行进程清理")
            return False
        except Exception as e:
            print(f"❌ 进程清理失败: {e}")
            return False
    
    def _cleanup_with_system_command(self, log_func) -> bool:
        """使用系统命令清理进程"""
        try:
            if sys.platform == "win32":
                if self.is_admin:
                    # 有管理员权限，直接使用taskkill
                    log_func("第三阶段：使用管理员权限清理...")
                    result = subprocess.run(['taskkill', '/f', '/im', 'WinIPBroadcast.exe'],
                                          capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                    if result.returncode == 0:
                        log_func("✅ 使用管理员权限成功清理WinIPBroadcast进程", "info")
                        return True
                    else:
                        log_func(f"❌ 管理员权限清理失败: {result.stderr}", "error")
                        return False
                else:
                    # 没有管理员权限，提示用户
                    log_func("第三阶段：需要管理员权限清理残余进程...", "warning")
                    return self._request_admin_cleanup(log_func)
            else:
                # 非Windows系统
                result = subprocess.run(['pkill', '-f', 'WinIPBroadcast'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log_func("✅ 使用pkill成功清理WinIPBroadcast进程", "info")
                    return True
                else:
                    log_func(f"❌ pkill清理失败: {result.stderr}", "error")
                    return False
        except Exception as e:
            log_func(f"❌ 系统命令清理失败: {e}", "error")
            return False
    
    def _request_admin_cleanup(self, log_func) -> bool:
        """请求管理员权限进行清理（异步非阻塞版本）"""
        try:
            log_func("🔐 检测到管理员权限进程，正在请求管理员权限清理...", "info")

            if sys.platform == "win32":
                import ctypes
                import threading
                import time

                # 使用ShellExecute以管理员权限运行taskkill命令
                shell32 = ctypes.windll.shell32

                # 构建清理命令
                cmd = "taskkill /f /im WinIPBroadcast.exe"

                # 使用线程执行，避免阻塞UI线程和QTimer跨线程问题
                def execute_admin_command():
                    try:
                        result = shell32.ShellExecuteW(
                            None,                    # hwnd
                            "runas",                 # lpOperation (以管理员身份运行)
                            "cmd.exe",               # lpFile
                            f"/c {cmd}",             # lpParameters
                            None,                    # lpDirectory
                            0                        # nShowCmd (隐藏窗口)
                        )

                        if result > 32:  # 成功
                            log_func("✅ 管理员权限请求成功，正在清理进程...", "info")
                            # 等待3秒让命令执行完成
                            time.sleep(3)
                            # 验证清理效果
                            self._verify_admin_cleanup(log_func)
                        else:
                            self._handle_admin_cleanup_error(result, log_func)
                    except Exception as e:
                        log_func(f"❌ 管理员权限执行失败: {e}", "error")
                        log_func("💡 建议手动清理或以管理员权限重启程序", "info")

                # 使用线程执行，避免阻塞UI
                thread = threading.Thread(target=execute_admin_command, daemon=True)
                thread.start()
                return True  # 返回True表示已启动异步清理
            else:
                # 非Windows系统，使用sudo
                log_func("🔐 请求sudo权限清理WinIPBroadcast进程...", "info")
                result = subprocess.run(['sudo', 'pkill', '-f', 'WinIPBroadcast'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log_func("✅ 使用sudo成功清理WinIPBroadcast进程", "info")
                    return True
                else:
                    log_func(f"❌ sudo清理失败: {result.stderr}", "error")
                    return False

        except Exception as e:
            log_func(f"❌ 管理员权限清理失败: {e}", "error")
            return False

    def cleanup_winip_processes_with_admin_request(self, callback=None) -> bool:
        """
        启动时清理WinIPBroadcast进程（主动请求管理员权限）

        Args:
            callback: 回调函数，用于更新UI状态

        Returns:
            bool: 清理是否成功
        """
        try:
            import psutil

            def log(message, level="info"):
                print(message)
                if callback:
                    callback(message, level)

            # 第一次扫描
            found_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'winipbroadcast.exe':
                        found_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not found_processes:
                log("🔍 未发现WinIPBroadcast进程")
                return True

            log(f"🔍 发现 {len(found_processes)} 个WinIPBroadcast进程，正在清理...", "info")

            # 第一轮：优雅终止
            log("第一阶段：尝试优雅终止进程...")
            for proc in found_processes:
                try:
                    log(f"  终止进程 PID: {proc.pid}")
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    log(f"  终止进程 {proc.pid} 失败: {e}", "warning")

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
                log(f"第二阶段：强制终止 {len(remaining_processes)} 个进程...")
                for proc in remaining_processes:
                    try:
                        log(f"  强制终止进程 PID: {proc.pid}")
                        proc.kill()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        log(f"  强制终止进程 {proc.pid} 失败: {e}", "warning")

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
                log(f"⚠️ 仍有 {len(final_check)} 个WinIPBroadcast进程未能清理", "warning")

                # 直接尝试管理员权限清理（不再检查当前权限）
                log("第三阶段：请求管理员权限清理残余进程...", "info")
                success = self._request_admin_cleanup(log)
                return success
            else:
                log("✅ 所有WinIPBroadcast进程已成功清理", "info")
                return True

        except ImportError:
            print("❌ psutil未安装，无法进行进程清理")
            return False
        except Exception as e:
            print(f"❌ 进程清理失败: {e}")
            return False

    def _verify_admin_cleanup(self, log_func):
        """异步验证管理员权限清理效果"""
        try:
            import psutil

            # 验证清理效果
            final_check = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'winipbroadcast.exe':
                        final_check.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if final_check:
                log_func(f"⚠️ 仍有 {len(final_check)} 个进程未能清理", "warning")
                log_func("💡 可能需要手动结束进程", "info")
            else:
                log_func("✅ 所有WinIPBroadcast进程已成功清理", "info")

        except Exception as e:
            log_func(f"❌ 验证清理效果失败: {e}", "error")

    def _handle_admin_cleanup_error(self, result, log_func):
        """处理管理员权限清理错误"""
        log_func(f"❌ 管理员权限请求失败，错误代码: {result}", "error")
        if result == 5:
            log_func("   用户取消了UAC提示", "warning")
        elif result == 2:
            log_func("   系统文件未找到", "error")
        elif result == 31:
            log_func("   没有关联的应用程序", "error")

        # 回退到原来的提示
        log_func("💡 如需完全清理，请以管理员权限重启程序", "info")
        log_func("💡 或运行项目根目录下的'清理WinIPBroadcast进程.bat'文件", "info")




# 全局实例
process_cleaner = ProcessCleaner()