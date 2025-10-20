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
from ..i18n.manager import t


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
            print(t("process_cleaner.psutil_not_installed_check"))
            return []
        except Exception as e:
            print(t("process_cleaner.find_process_failed", error=e))
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
                log(t("process_cleaner.no_process_found"))
                return True

            log(t("process_cleaner.found_processes_cleaning", count=len(found_processes)), "info")

            # 第一轮：优雅终止
            log(t("process_cleaner.stage1_graceful_terminate"))
            for proc in found_processes:
                try:
                    log(t("process_cleaner.terminate_process_pid", pid=proc.pid))
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    log(t("process_cleaner.terminate_process_failed", pid=proc.pid, error=e), "warning")
            
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
                log(t("process_cleaner.stage2_force_terminate", count=len(remaining_processes)))
                for proc in remaining_processes:
                    try:
                        log(t("process_cleaner.force_terminate_process_pid", pid=proc.pid))
                        proc.kill()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        log(t("process_cleaner.force_terminate_process_failed", pid=proc.pid, error=e), "warning")
            
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
                log(t("process_cleaner.remaining_processes_warning", count=len(final_check)), "warning")

                # 尝试系统命令清理
                success = self._cleanup_with_system_command(log)
                if success:
                    return True
                else:
                    log(t("process_cleaner.partial_processes_need_admin"), "warning")
                    if not self.is_admin:
                        log(t("process_cleaner.suggest_admin_restart"), "info")
                    return False
            else:
                log(t("process_cleaner.all_processes_cleaned"), "info")
                return True

        except ImportError:
            print(t("process_cleaner.psutil_not_installed_cleanup"))
            return False
        except Exception as e:
            print(t("process_cleaner.cleanup_failed", error=e))
            return False
    
    def _cleanup_with_system_command(self, log_func) -> bool:
        """使用系统命令清理进程"""
        try:
            if sys.platform == "win32":
                if self.is_admin:
                    # 有管理员权限，直接使用taskkill
                    log_func(t("process_cleaner.stage3_admin_cleanup"))
                    result = subprocess.run(['taskkill', '/f', '/im', 'WinIPBroadcast.exe'],
                                          capture_output=True, text=True,
                                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                    if result.returncode == 0:
                        log_func(t("process_cleaner.admin_cleanup_success"), "info")
                        return True
                    else:
                        log_func(t("process_cleaner.admin_cleanup_failed", error=result.stderr), "error")
                        return False
                else:
                    # 没有管理员权限，提示用户
                    log_func(t("process_cleaner.stage3_need_admin"), "warning")
                    return self._request_admin_cleanup(log_func)
            else:
                # 非Windows系统
                result = subprocess.run(['pkill', '-f', 'WinIPBroadcast'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log_func(t("process_cleaner.pkill_success"), "info")
                    return True
                else:
                    log_func(t("process_cleaner.pkill_failed", error=result.stderr), "error")
                    return False
        except Exception as e:
            log_func(t("process_cleaner.system_command_failed", error=e), "error")
            return False
    
    def _request_admin_cleanup(self, log_func) -> bool:
        """请求管理员权限进行清理（异步非阻塞版本）"""
        try:
            log_func(t("process_cleaner.detecting_admin_process"), "info")

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
                            log_func(t("process_cleaner.admin_request_success"), "info")
                            # 等待3秒让命令执行完成
                            time.sleep(3)
                            # 验证清理效果
                            self._verify_admin_cleanup(log_func)
                        else:
                            self._handle_admin_cleanup_error(result, log_func)
                    except Exception as e:
                        log_func(t("process_cleaner.admin_execute_failed", error=e), "error")
                        log_func(t("process_cleaner.suggest_manual_cleanup"), "info")

                # 使用线程执行，避免阻塞UI
                thread = threading.Thread(target=execute_admin_command, daemon=True)
                thread.start()
                return True  # 返回True表示已启动异步清理
            else:
                # 非Windows系统，使用sudo
                log_func(t("process_cleaner.sudo_request"), "info")
                result = subprocess.run(['sudo', 'pkill', '-f', 'WinIPBroadcast'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log_func(t("process_cleaner.sudo_success"), "info")
                    return True
                else:
                    log_func(t("process_cleaner.sudo_failed", error=result.stderr), "error")
                    return False

        except Exception as e:
            log_func(t("process_cleaner.admin_cleanup_error", error=e), "error")
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
                log(t("process_cleaner.no_process_found"))
                return True

            log(t("process_cleaner.found_processes_cleaning", count=len(found_processes)), "info")

            # 第一轮：优雅终止
            log(t("process_cleaner.stage1_graceful_terminate"))
            for proc in found_processes:
                try:
                    log(t("process_cleaner.terminate_process_pid", pid=proc.pid))
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    log(t("process_cleaner.terminate_process_failed", pid=proc.pid, error=e), "warning")

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
                log(t("process_cleaner.stage2_force_terminate", count=len(remaining_processes)))
                for proc in remaining_processes:
                    try:
                        log(t("process_cleaner.force_terminate_process_pid", pid=proc.pid))
                        proc.kill()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception as e:
                        log(t("process_cleaner.force_terminate_process_failed", pid=proc.pid, error=e), "warning")

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
                log(t("process_cleaner.remaining_processes_warning", count=len(final_check)), "warning")

                # 直接尝试管理员权限清理（不再检查当前权限）
                log(t("process_cleaner.stage3_need_admin"), "info")
                success = self._request_admin_cleanup(log)
                return success
            else:
                log(t("process_cleaner.all_processes_cleaned"), "info")
                return True

        except ImportError:
            print(t("process_cleaner.psutil_not_installed_cleanup"))
            return False
        except Exception as e:
            print(t("process_cleaner.cleanup_failed", error=e))
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
                log_func(t("process_cleaner.remaining_processes_after_admin", count=len(final_check)), "warning")
                log_func(t("process_cleaner.suggest_manual_terminate"), "info")
            else:
                log_func(t("process_cleaner.all_processes_cleaned"), "info")

        except Exception as e:
            log_func(t("process_cleaner.verify_cleanup_failed", error=e), "error")

    def _handle_admin_cleanup_error(self, result, log_func):
        """处理管理员权限清理错误"""
        log_func(t("process_cleaner.admin_request_failed_code", code=result), "error")
        if result == 5:
            log_func(t("process_cleaner.user_cancelled_uac"), "warning")
        elif result == 2:
            log_func(t("process_cleaner.system_file_not_found"), "error")
        elif result == 31:
            log_func(t("process_cleaner.no_associated_app"), "error")

        # 回退到原来的提示
        log_func(t("process_cleaner.suggest_admin_restart_full"), "info")
        log_func(t("process_cleaner.suggest_run_bat_file"), "info")




# 全局实例
process_cleaner = ProcessCleaner()