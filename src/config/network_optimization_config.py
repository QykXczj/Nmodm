"""
网络优化配置管理
管理WinIPBroadcast、网卡跃点优化等配置
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class NetworkOptimizationConfig:
    """网络优化配置管理器"""
    
    def __init__(self):
        # 路径配置
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent
            
        self.config_dir = self.root_dir / "ESR"
        self.config_file = self.config_dir / "network_optimization.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 默认配置
        self.default_config = {
            "winip_broadcast": {
                "enabled": True,
                "description": "启用WinIPBroadcast解决局域网游戏发现问题"
            },
            "network_metric": {
                "enabled": True,
                "auto_optimize": True,
                "target_metric": 1,
                "description": "自动优化EasyTier网卡跃点为最高优先级"
            },
            # KCP代理功能已移除，因为EasyTier自带KCP支持
            "advanced": {
                "auto_start_with_easytier": True,
                "restore_on_exit": True,
                "log_optimization_status": True,
                "description": "高级优化选项"
            }
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合并默认配置（确保新增的配置项存在）
                merged_config = self._merge_config(self.default_config, config)
                return merged_config
            else:
                # 配置文件不存在，使用默认配置并保存
                self.save_config(self.default_config)
                return self.default_config.copy()
                
        except Exception as e:
            print(f"加载网络优化配置失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """保存配置文件"""
        try:
            config_to_save = config if config is not None else self.config
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            
            print(f"✅ 网络优化配置已保存: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"保存网络优化配置失败: {e}")
            return False
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """合并配置（用户配置覆盖默认配置）"""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_winip_broadcast_config(self) -> Dict[str, Any]:
        """获取WinIPBroadcast配置"""
        return self.config.get("winip_broadcast", self.default_config["winip_broadcast"])
    
    def get_network_metric_config(self) -> Dict[str, Any]:
        """获取网卡跃点优化配置"""
        return self.config.get("network_metric", self.default_config["network_metric"])
    
    # KCP代理配置获取方法已移除
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """获取高级配置"""
        return self.config.get("advanced", self.default_config["advanced"])
    
    def update_winip_broadcast_config(self, enabled: bool) -> bool:
        """更新WinIPBroadcast配置"""
        try:
            self.config["winip_broadcast"]["enabled"] = enabled
            return self.save_config()
        except Exception as e:
            print(f"更新WinIPBroadcast配置失败: {e}")
            return False
    
    def update_network_metric_config(self, enabled: bool, auto_optimize: bool = True) -> bool:
        """更新网卡跃点优化配置"""
        try:
            self.config["network_metric"]["enabled"] = enabled
            self.config["network_metric"]["auto_optimize"] = auto_optimize
            return self.save_config()
        except Exception as e:
            print(f"更新网卡跃点配置失败: {e}")
            return False
    
    # KCP代理配置方法已移除
    
    def is_winip_broadcast_enabled(self) -> bool:
        """检查WinIPBroadcast是否启用"""
        return self.get_winip_broadcast_config().get("enabled", True)
    
    def is_network_metric_enabled(self) -> bool:
        """检查网卡跃点优化是否启用"""
        return self.get_network_metric_config().get("enabled", True)
    
    # KCP代理检查方法已移除
    
    def is_auto_start_enabled(self) -> bool:
        """检查是否自动启动优化"""
        return self.get_advanced_config().get("auto_start_with_easytier", True)
    
    def get_optimization_summary(self) -> Dict[str, bool]:
        """获取优化功能启用状态摘要"""
        return {
            "WinIPBroadcast": self.is_winip_broadcast_enabled(),
            "网卡跃点优化": self.is_network_metric_enabled(),
            "自动启动": self.is_auto_start_enabled()
        }
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self.config = self.default_config.copy()
            return self.save_config()
        except Exception as e:
            print(f"重置配置失败: {e}")
            return False
