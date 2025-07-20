"""
局域网联机模式检测器
使用DLL注入检测和状态文件双重验证
"""
import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Optional
from datetime import datetime


class LanModeDetector:
    """局域网联机模式检测器"""
    
    def __init__(self):
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境
            self.root_dir = Path(__file__).parent.parent.parent
        
        self.esl_dir = self.root_dir / "ESL"
        self.status_file = self.esl_dir / "lan_status.json"
        
        # 检测当前模式
        self._current_mode = self._detect_lan_mode()
        
        # 更新状态文件
        self._update_status_file()
    
    @property
    def is_lan_mode(self) -> bool:
        """是否处于局域网联机模式"""
        return self._current_mode
    
    def _detect_lan_mode(self) -> bool:
        """检测局域网联机模式"""

        # 优先级1: DLL注入检测（最准确）
        dll_detected = self._check_dll_injection()
        if dll_detected:
            print("🌐 检测到steamclient DLL注入，确认为局域网联机模式")
            return True

        # 优先级2: 检查父进程（启动检测）
        parent_detected = self._check_parent_process()
        if parent_detected:
            print("🌐 检测到steamclient_loader父进程，判断为局域网联机模式")
            return True

        # 优先级3: 检查状态文件（持久化状态）- 但需要验证有效性
        status_file_detected = self._check_status_file()
        if status_file_detected:
            # 如果只有状态文件而没有其他证据，可能是残留状态
            print("⚠️ 检测到状态文件但无DLL注入或父进程，可能是残留状态，清理中...")
            self._reset_status_file()
            return False

        print("🔍 未检测到局域网联机模式特征，判断为正常模式")
        return False
    
    def _check_dll_injection(self) -> bool:
        """检查DLL注入（主要判断依据）"""
        try:
            kernel32 = ctypes.windll.kernel32
            
            # 检查steamclient.dll
            handle = kernel32.GetModuleHandleW("steamclient.dll")
            if handle:
                return True
            
            # 检查steamclient64.dll
            handle = kernel32.GetModuleHandleW("steamclient64.dll")
            if handle:
                return True
                
        except Exception as e:
            print(f"DLL检测异常: {e}")
        
        return False
    
    def _check_status_file(self) -> bool:
        """检查状态配置文件"""
        try:
            if not self.status_file.exists():
                return False
            
            with open(self.status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # 检查状态
            if status_data.get('lan_mode_active', False):
                # 检查状态是否过期（防止异常退出导致的状态残留）
                last_update = status_data.get('last_update')
                if last_update:
                    from datetime import datetime, timedelta
                    try:
                        last_time = datetime.fromisoformat(last_update)
                        # 如果状态超过1小时未更新，认为已过期
                        if datetime.now() - last_time > timedelta(hours=1):
                            print("⚠️ 状态文件已过期，重置为正常模式")
                            self._reset_status_file()
                            return False
                    except ValueError:
                        print("⚠️ 状态文件时间格式错误，重置为正常模式")
                        self._reset_status_file()
                        return False

                return True
        
        except Exception as e:
            print(f"状态文件检查异常: {e}")
        
        return False
    
    def _check_parent_process(self) -> bool:
        """检查父进程"""
        try:
            import psutil
            current_process = psutil.Process()
            parent = current_process.parent()
            
            if parent:
                parent_name = parent.name().lower()
                if 'steamclient_loader' in parent_name:
                    return True
                    
        except Exception as e:
            print(f"父进程检查异常: {e}")
        
        return False
    
    def _update_status_file(self):
        """更新状态文件"""
        try:
            # 确保ESL目录存在
            self.esl_dir.mkdir(parents=True, exist_ok=True)
            
            status_data = {
                'lan_mode_active': self._current_mode,
                'last_update': datetime.now().isoformat(),
                'detection_method': self._get_detection_method(),
                'process_id': os.getpid(),
                'executable_path': sys.executable if getattr(sys, 'frozen', False) else __file__
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"更新状态文件失败: {e}")
    
    def _get_detection_method(self) -> str:
        """获取检测方法"""
        if self._check_dll_injection():
            return "dll_injection"
        elif self._check_parent_process():
            return "parent_process"
        elif self._check_status_file():
            return "status_file"
        else:
            return "normal_mode"
    
    def _reset_status_file(self):
        """重置状态文件"""
        try:
            if self.status_file.exists():
                self.status_file.unlink()
        except Exception as e:
            print(f"重置状态文件失败: {e}")
    
    def set_lan_mode(self, active: bool):
        """手动设置局域网模式状态（供ESL启动器调用）"""
        self._current_mode = active
        self._update_status_file()
        print(f"🌐 手动设置局域网模式: {'激活' if active else '关闭'}")
    
    def get_status_info(self) -> dict:
        """获取详细状态信息"""
        return {
            'is_lan_mode': self.is_lan_mode,
            'detection_method': self._get_detection_method(),
            'dll_injection': self._check_dll_injection(),
            'parent_process': self._check_parent_process(),
            'status_file': self._check_status_file(),
            'status_file_path': str(self.status_file),
            'esl_dir': str(self.esl_dir)
        }
    
    def cleanup_on_exit(self):
        """程序退出时清理状态"""
        # 总是清理状态文件，因为程序退出了
        self._reset_status_file()
        print("🧹 程序退出，清理局域网模式状态文件")


# 全局检测器实例
_detector_instance: Optional[LanModeDetector] = None


def get_lan_mode_detector() -> LanModeDetector:
    """获取局域网模式检测器单例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LanModeDetector()
    return _detector_instance


def is_lan_mode() -> bool:
    """快速检查是否为局域网模式"""
    return get_lan_mode_detector().is_lan_mode


def cleanup_lan_mode_on_exit():
    """程序退出时清理局域网模式状态"""
    global _detector_instance
    if _detector_instance:
        _detector_instance.cleanup_on_exit()
