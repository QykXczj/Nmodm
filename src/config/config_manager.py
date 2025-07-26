"""
配置管理器
负责游戏路径配置、破解文件管理等功能
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self):
        # 处理打包后的路径问题
        if getattr(sys, 'frozen', False):
            # 打包后的环境：可执行文件所在目录
            self.root_dir = Path(sys.executable).parent
        else:
            # 开发环境：源代码目录
            self.root_dir = Path(__file__).parent.parent.parent
        self.onlinefix_dir = self.root_dir / "OnlineFix"
        self.config_file = self.onlinefix_dir / "gconfig.ini"
        
    def get_game_path(self) -> Optional[str]:
        """获取游戏路径"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    path = f.read().strip().strip('"')
                    return path if path else None
            return None
        except Exception as e:
            print(f"读取游戏路径失败: {e}")
            return None
    
    def set_game_path(self, game_path: str) -> bool:
        """设置游戏路径"""
        try:
            # 验证路径是否存在
            if not os.path.exists(game_path):
                return False
            
            # 验证是否为nightreign.exe
            if not game_path.lower().endswith('nightreign.exe'):
                return False
            
            # 保存路径到配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f'"{game_path}"\n')
            
            return True
        except Exception as e:
            print(f"保存游戏路径失败: {e}")
            return False
    
    def validate_game_path(self, game_path: str = None) -> bool:
        """验证游戏路径有效性"""
        if game_path is None:
            game_path = self.get_game_path()
        
        if not game_path:
            return False
        
        return (os.path.exists(game_path) and 
                game_path.lower().endswith('nightreign.exe'))
    
    def get_game_directory(self) -> Optional[str]:
        """获取游戏目录"""
        game_path = self.get_game_path()
        if game_path and self.validate_game_path(game_path):
            return os.path.dirname(game_path)
        return None
    
    def apply_crack(self) -> bool:
        """应用破解文件"""
        try:
            game_dir = self.get_game_directory()
            if not game_dir:
                return False

            # 定义不是破解补丁的文件（排除列表）
            excluded_files = {
                "gconfig.ini",      # 配置文件
                "esl2.zip",         # ESL工具包
                "tool.zip",         # 网络优化工具包
                "Regulations"       # 可能的文件夹
            }

            # 复制OnlineFix文件夹中的破解文件到游戏目录
            for file_path in self.onlinefix_dir.iterdir():
                if file_path.name not in excluded_files and file_path.is_file():
                    dest_path = Path(game_dir) / file_path.name
                    shutil.copy2(file_path, dest_path)
                    print(f"✅ 应用破解文件: {file_path.name}")

            return True
        except Exception as e:
            print(f"应用破解失败: {e}")
            return False
    
    def remove_crack(self) -> bool:
        """移除破解文件"""
        try:
            game_dir = self.get_game_directory()
            if not game_dir:
                return False

            # 定义不是破解补丁的文件（排除列表）
            excluded_files = {
                "gconfig.ini",      # 配置文件
                "esl2.zip",         # ESL工具包
                "tool.zip",         # 网络优化工具包
                "Regulations"       # 可能的文件夹
            }

            # 删除游戏目录中的破解文件
            for file_path in self.onlinefix_dir.iterdir():
                if file_path.name not in excluded_files and file_path.is_file():
                    crack_file = Path(game_dir) / file_path.name
                    if crack_file.exists():
                        crack_file.unlink()
                        print(f"✅ 移除破解文件: {file_path.name}")

            return True
        except Exception as e:
            print(f"移除破解失败: {e}")
            return False
    
    def is_crack_applied(self) -> bool:
        """检查是否已应用破解"""
        try:
            game_dir = self.get_game_directory()
            if not game_dir:
                return False

            # 定义不是破解补丁的文件（排除列表）
            excluded_files = {
                "gconfig.ini",      # 配置文件
                "esl2.zip",         # ESL工具包
                "tool.zip",         # 网络优化工具包
                "Regulations"       # 可能的文件夹
            }

            # 检查是否存在破解文件
            for file_path in self.onlinefix_dir.iterdir():
                if file_path.name not in excluded_files and file_path.is_file():
                    crack_file = Path(game_dir) / file_path.name
                    if crack_file.exists():
                        return True

            return False
        except Exception as e:
            print(f"检查破解状态失败: {e}")
            return False
