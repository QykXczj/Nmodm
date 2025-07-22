"""
DLL管理工具
用于管理steamclient.dll的加载和卸载
"""
import ctypes
import ctypes.wintypes
import psutil
import os
import sys
from pathlib import Path
from typing import List, Optional


class DLLManager:
    """DLL管理器"""
    
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.psapi = ctypes.windll.psapi
        
    def is_dll_loaded(self, dll_name: str) -> bool:
        """检查DLL是否已加载到当前进程"""
        try:
            handle = self.kernel32.GetModuleHandleW(dll_name)
            return handle != 0
        except Exception as e:
            print(f"检查DLL加载状态失败: {e}")
            return False
    
    def get_loaded_dlls(self) -> List[str]:
        """获取当前进程加载的所有DLL"""
        try:
            # 获取当前进程句柄
            process_handle = self.kernel32.GetCurrentProcess()
            
            # 枚举模块
            modules = (ctypes.wintypes.HMODULE * 1024)()
            needed = ctypes.wintypes.DWORD()
            
            if self.psapi.EnumProcessModules(
                process_handle,
                ctypes.byref(modules),
                ctypes.sizeof(modules),
                ctypes.byref(needed)
            ):
                module_count = needed.value // ctypes.sizeof(ctypes.wintypes.HMODULE)
                dll_list = []
                
                for i in range(module_count):
                    module_name = ctypes.create_unicode_buffer(260)
                    if self.psapi.GetModuleFileNameExW(
                        process_handle,
                        modules[i],
                        module_name,
                        260
                    ):
                        dll_path = module_name.value
                        dll_name = Path(dll_path).name.lower()
                        if 'steamclient' in dll_name:
                            dll_list.append(dll_path)
                
                return dll_list
        except Exception as e:
            print(f"获取DLL列表失败: {e}")
        
        return []
    
    def unload_dll(self, dll_name: str) -> bool:
        """尝试卸载指定的DLL"""
        try:
            # 获取DLL句柄
            handle = self.kernel32.GetModuleHandleW(dll_name)
            if handle == 0:
                print(f"DLL {dll_name} 未加载")
                return True
            
            # 尝试释放DLL
            result = self.kernel32.FreeLibrary(handle)
            if result:
                print(f"✅ 成功卸载DLL: {dll_name}")
                return True
            else:
                print(f"❌ 卸载DLL失败: {dll_name}")
                return False
                
        except Exception as e:
            print(f"卸载DLL异常: {e}")
            return False
    
    def force_unload_steamclient(self) -> bool:
        """强制卸载steamclient相关DLL"""
        success = True
        steamclient_dlls = [
            "steamclient.dll",
            "steamclient64.dll"
        ]
        
        print("🔄 开始卸载steamclient DLL...")
        
        for dll_name in steamclient_dlls:
            if self.is_dll_loaded(dll_name):
                print(f"发现已加载的DLL: {dll_name}")
                
                # 多次尝试卸载（有些DLL可能被多次引用）
                for attempt in range(5):
                    if self.unload_dll(dll_name):
                        if not self.is_dll_loaded(dll_name):
                            print(f"✅ {dll_name} 已完全卸载")
                            break
                        else:
                            print(f"🔄 {dll_name} 仍在加载中，继续尝试...")
                    else:
                        print(f"❌ 第{attempt + 1}次卸载{dll_name}失败")
                        success = False
                        break
            else:
                print(f"✅ {dll_name} 未加载")
        
        return success
    
    def restart_steam_processes(self) -> bool:
        """重启Steam相关进程"""
        try:
            steam_exe_path = None
            killed_processes = []

            # 首先找到steam.exe的路径
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if proc_name == 'steam.exe':
                        steam_exe_path = proc.info.get('exe')
                        print(f"发现Steam主程序: {steam_exe_path}")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 终止Steam相关进程
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if 'steamclient' in proc_name or 'steam' in proc_name:
                        # 排除当前进程
                        if proc.pid != os.getpid():
                            print(f"终止Steam相关进程: {proc_name} (PID: {proc.pid})")
                            proc.terminate()
                            killed_processes.append(proc_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed_processes:
                print(f"✅ 已终止进程: {', '.join(set(killed_processes))}")

                # 等待进程完全终止
                import time
                time.sleep(2)

                # 重启Steam
                if steam_exe_path and os.path.exists(steam_exe_path):
                    print(f"🔄 正在重启Steam: {steam_exe_path}")
                    import subprocess
                    subprocess.Popen([steam_exe_path], cwd=os.path.dirname(steam_exe_path))
                    print("✅ Steam重启命令已发送")
                else:
                    print("⚠️ 未找到Steam安装路径，请手动重启Steam")

                return True
            else:
                print("✅ 未发现需要重启的Steam进程")
                return True

        except Exception as e:
            print(f"重启Steam进程失败: {e}")
            return False

    def kill_steamclient_processes(self) -> bool:
        """终止steamclient相关进程（保留原方法以兼容）"""
        return self.restart_steam_processes()
    
    def restart_nmodm_application(self) -> bool:
        """重启Nmodm应用程序"""
        try:
            import subprocess

            # 获取当前Nmodm程序路径（类似获取Steam路径的方式）
            current_nmodm_path = self._get_current_nmodm_path()

            if not current_nmodm_path:
                print("❌ 无法获取Nmodm程序路径")
                return False

            print(f"🔄 准备重启Nmodm应用程序...")
            print(f"Nmodm程序路径: {current_nmodm_path}")

            # 立即启动新的Nmodm实例（使用start命令）
            # 智能判断启动方式
            is_frozen = getattr(sys, 'frozen', False)
            is_nmodm_exe = current_nmodm_path and 'nmodm' in current_nmodm_path.lower() and current_nmodm_path.lower().endswith('.exe')
            is_python_exe = current_nmodm_path and 'python.exe' in current_nmodm_path.lower()

            print(f"环境检测: frozen={is_frozen}, nmodm_exe={is_nmodm_exe}, python_exe={is_python_exe}")

            if is_frozen or is_nmodm_exe:
                # 打包后的环境或找到了Nmodm的exe文件
                if is_python_exe:
                    # 如果获取到的是python.exe，说明是开发环境，需要构建正确的命令
                    script_path = sys.argv[0] if sys.argv else 'main.py'
                    start_cmd = f'start "" "{current_nmodm_path}" "{script_path}"'
                    print("使用Python解释器启动脚本")
                else:
                    # 直接启动exe文件
                    start_cmd = f'start "" "{current_nmodm_path}"'
                    print("使用打包模式启动exe")
            else:
                # 开发环境，使用python启动脚本
                script_path = sys.argv[0] if sys.argv else 'main.py'
                python_exe = sys.executable
                start_cmd = f'start "" "{python_exe}" "{script_path}"'
                print("使用开发模式启动")

            print(f"🚀 启动新的Nmodm实例: {start_cmd}")

            # 使用start命令启动新实例
            result = subprocess.run(start_cmd, shell=True, cwd=os.getcwd())

            if result.returncode == 0:
                print("✅ 新的Nmodm实例已启动")
                return True
            else:
                print(f"❌ 启动新Nmodm实例失败，返回码: {result.returncode}")
                return False

        except Exception as e:
            print(f"重启Nmodm应用程序失败: {e}")
            return False

    def _get_current_nmodm_path(self) -> str:
        """获取当前Nmodm程序路径（类似获取Steam路径的方式）"""
        try:
            current_pid = os.getpid()
            print(f"当前进程PID: {current_pid}")

            # 通过当前进程获取程序路径
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['pid'] == current_pid:
                        exe_path = proc.info.get('exe')
                        if exe_path:
                            print(f"发现当前Nmodm进程: {exe_path}")

                            # 验证路径是否存在
                            if os.path.exists(exe_path):
                                print(f"路径验证成功: {exe_path}")
                                return exe_path
                            else:
                                print(f"路径不存在: {exe_path}")

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 如果通过进程获取失败，使用sys.executable作为备用
            backup_path = sys.executable
            print(f"使用备用路径: {backup_path}")

            # 验证备用路径
            if os.path.exists(backup_path):
                print(f"备用路径验证成功: {backup_path}")
                return backup_path
            else:
                print(f"备用路径不存在: {backup_path}")

                # 最后尝试：在当前目录查找exe文件
                current_dir = os.getcwd()
                for file in os.listdir(current_dir):
                    if file.lower().endswith('.exe') and 'nmodm' in file.lower():
                        exe_path = os.path.join(current_dir, file)
                        print(f"在当前目录找到exe: {exe_path}")
                        return exe_path

                print("❌ 无法找到有效的Nmodm程序路径")
                return ""

        except Exception as e:
            print(f"获取Nmodm程序路径失败: {e}")
            return ""

    def cleanup_steam_environment(self) -> bool:
        """清理Steam环境"""
        print("🧹 开始清理Steam环境...")

        success = True

        # 1. 卸载DLL
        if not self.force_unload_steamclient():
            print("⚠️ DLL卸载不完全，但继续清理...")
            success = False

        # 2. 重启相关进程
        if not self.restart_steam_processes():
            print("⚠️ Steam进程重启不完全，但继续清理...")
            success = False

        # 3. 清理环境变量（如果有的话）
        steam_env_vars = ['STEAM_COMPAT_DATA_PATH', 'STEAM_COMPAT_CLIENT_INSTALL_PATH']
        for var in steam_env_vars:
            if var in os.environ:
                del os.environ[var]
                print(f"✅ 清理环境变量: {var}")

        if success:
            print("✅ Steam环境清理完成")
        else:
            print("⚠️ Steam环境清理部分完成，建议手动重启Steam")

        return success
    
    def get_cleanup_status(self) -> dict:
        """获取清理状态"""
        return {
            'steamclient_dll_loaded': self.is_dll_loaded('steamclient.dll'),
            'steamclient64_dll_loaded': self.is_dll_loaded('steamclient64.dll'),
            'loaded_steamclient_dlls': self.get_loaded_dlls(),
            'steam_processes': self._get_steam_processes()
        }
    
    def _get_steam_processes(self) -> List[dict]:
        """获取Steam相关进程"""
        steam_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if 'steam' in proc_name and proc.pid != os.getpid():
                        steam_processes.append({
                            'pid': proc.pid,
                            'name': proc.info['name'],
                            'exe': proc.info.get('exe', 'N/A')
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"获取Steam进程列表失败: {e}")
        
        return steam_processes


# 全局DLL管理器实例
_dll_manager_instance: Optional[DLLManager] = None


def get_dll_manager() -> DLLManager:
    """获取DLL管理器单例"""
    global _dll_manager_instance
    if _dll_manager_instance is None:
        _dll_manager_instance = DLLManager()
    return _dll_manager_instance


def cleanup_steam_dlls() -> bool:
    """清理Steam DLL的便捷函数"""
    manager = get_dll_manager()
    return manager.cleanup_steam_environment()


def get_steam_cleanup_status() -> dict:
    """获取Steam清理状态的便捷函数"""
    manager = get_dll_manager()
    return manager.get_cleanup_status()
