"""
游戏进程清理工具
用于启动前自动清理冲突的游戏相关进程
"""

import psutil
import time
from typing import List


def cleanup_game_processes() -> bool:
    """
    启动前清理游戏相关进程
    
    Returns:
        bool: 清理是否成功完成
    """
    # 需要清理的目标进程
    target_processes = ["nightreign.exe", "me3.exe", "me3-launcher.exe"]
    
    try:
        found_processes = []
        
        # 第一阶段：查找目标进程
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if proc_name in [p.lower() for p in target_processes]:
                    found_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not found_processes:
            return True  # 没有需要清理的进程
        
        # 第二阶段：优雅终止进程
        for proc in found_processes:
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 等待进程退出
        time.sleep(2)
        
        # 第三阶段：强制终止仍在运行的进程
        remaining_processes = []
        for proc in found_processes:
            try:
                if proc.is_running():
                    remaining_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if remaining_processes:
            for proc in remaining_processes:
                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception:
                    pass
        
        return True
        
    except Exception as e:
        print(f"清理游戏进程时发生错误: {e}")
        return False


def get_running_game_processes() -> List[str]:
    """
    获取当前运行的游戏相关进程列表
    
    Returns:
        List[str]: 运行中的游戏进程名称列表
    """
    target_processes = ["nightreign.exe", "me3.exe", "me3-launcher.exe"]
    running_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if proc_name in [p.lower() for p in target_processes]:
                    running_processes.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    
    return running_processes