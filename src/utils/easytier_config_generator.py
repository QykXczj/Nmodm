"""
EasyTier配置文件生成器
负责生成TOML格式的EasyTier配置文件
"""

import uuid
import sys
from pathlib import Path
from typing import Dict, List, Optional
import toml


class EasyTierConfigGenerator:
    """EasyTier配置文件生成器"""
    
    def __init__(self):
        # 路径配置
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent
            
        self.esr_dir = self.root_dir / "ESR"
        self.config_file = self.esr_dir / "easytier.toml"
        
        # 确保目录存在
        self.esr_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_config(self, 
                       network_name: str,
                       network_secret: str,
                       hostname: str = "",
                       peers: List[str] = None,
                       dhcp: bool = True,
                       ipv4: str = "",
                       listeners: List[str] = None,
                       rpc_portal: str = "0.0.0.0:0",
                       flags: Dict = None) -> Dict:
        """
        生成EasyTier配置字典
        
        Args:
            network_name: 网络名称
            network_secret: 网络密码
            hostname: 主机名（玩家名称）
            peers: 对等节点列表
            dhcp: 是否使用DHCP
            ipv4: 手动指定的IPv4地址
            listeners: 监听地址列表
            rpc_portal: RPC门户地址
            flags: 标志配置
        
        Returns:
            配置字典
        """
        # 生成唯一的实例ID
        instance_id = str(uuid.uuid4())
        
        # 默认值处理
        if not hostname:
            hostname = f"Player_{instance_id[:8]}"
        
        if peers is None:
            peers = ["tcp://public.easytier.top:11010"]
        
        if listeners is None:
            listeners = ["udp://0.0.0.0:11010"]

        if flags is None:
            flags = {
                "enable_kcp_proxy": True,
                "enable_quic_proxy": True,
                "latency_first": True,
                "multi_thread": True,
                "enable_encryption": True,   # 默认启用加密
                "disable_ipv6": False,       # 默认不禁用IPv6
                "use_smoltcp": False,
                "enable_compression": False, # 默认不启用压缩
                "tcp_listen": False          # 默认不监听TCP
            }

        # 处理TCP监听选项
        if flags.get("tcp_listen", False):
            # 如果启用TCP监听，添加TCP监听器
            if "tcp://0.0.0.0:11010" not in listeners:
                listeners.append("tcp://0.0.0.0:11010")
        
        # 构建配置字典
        config = {
            "hostname": hostname,
            "instance_name": network_name,
            "instance_id": instance_id,
            "dhcp": dhcp,
            "listeners": listeners,
            "rpc_portal": rpc_portal,
            "network_identity": {
                "network_name": network_name,
                "network_secret": network_secret
            },
            "peer": [],
            "flags": {}
        }
        
        # 添加IPv4配置（仅在非DHCP模式下）
        if not dhcp and ipv4:
            config["ipv4"] = ipv4
        
        # 添加对等节点
        for peer_uri in peers:
            config["peer"].append({"uri": peer_uri})
        
        # 处理flags配置
        config["flags"]["enable_kcp_proxy"] = flags.get("enable_kcp_proxy", True)
        config["flags"]["enable_quic_proxy"] = flags.get("enable_quic_proxy", True)
        config["flags"]["latency_first"] = flags.get("latency_first", True)
        config["flags"]["multi_thread"] = flags.get("multi_thread", True)
        config["flags"]["use_smoltcp"] = flags.get("use_smoltcp", True)

        # 处理IPv6配置 - 在TOML中使用enable_ipv6字段
        disable_ipv6 = flags.get("disable_ipv6", False)
        if not disable_ipv6:
            config["flags"]["enable_ipv6"] = True
        else:
            config["flags"]["enable_ipv6"] = False
        
        # 处理加密配置 - 在TOML中使用enable_encryption字段
        enable_encryption = flags.get("enable_encryption", True)
        if enable_encryption:
            config["flags"]["enable_encryption"] = True
        else:
            config["flags"]["enable_encryption"] = False
        
        # 处理压缩配置
        # 如果启用压缩，则设置data_compress_algo = 2
        # 如果禁用压缩，则删除data_compress_algo字段
        if flags.get("enable_compression", True):
            config["flags"]["data_compress_algo"] = 2
        # 如果禁用压缩，不添加data_compress_algo字段
        
        return config
    
    def save_config_file(self, config: Dict) -> bool:
        """
        保存配置到TOML文件
        
        Args:
            config: 配置字典
            
        Returns:
            是否保存成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                toml.dump(config, f)
            
            print(f"✅ EasyTier配置文件已保存: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存EasyTier配置文件失败: {e}")
            return False
    
    def load_config_file(self) -> Optional[Dict]:
        """
        从TOML文件加载配置
        
        Returns:
            配置字典，如果失败返回None
        """
        try:
            if not self.config_file.exists():
                return None
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            
            print(f"✅ EasyTier配置文件已加载: {self.config_file}")
            return config
            
        except Exception as e:
            print(f"❌ 加载EasyTier配置文件失败: {e}")
            return None
    
    def generate_and_save(self, 
                         network_name: str,
                         network_secret: str,
                         hostname: str = "",
                         peers: List[str] = None,
                         dhcp: bool = True,
                         ipv4: str = "",
                         listeners: List[str] = None,
                         rpc_portal: str = "0.0.0.0:0",
                         flags: Dict = None) -> bool:
        """
        生成并保存配置文件
        
        Args:
            同generate_config方法
            
        Returns:
            是否成功
        """
        try:
            # 生成配置
            config = self.generate_config(
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
            
            # 保存配置文件
            return self.save_config_file(config)
            
        except Exception as e:
            print(f"❌ 生成并保存EasyTier配置失败: {e}")
            return False
    
    def get_config_file_path(self) -> Path:
        """获取配置文件路径"""
        return self.config_file
    
    def config_file_exists(self) -> bool:
        """检查配置文件是否存在"""
        return self.config_file.exists()
    
    def delete_config_file(self) -> bool:
        """删除配置文件"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                print(f"✅ EasyTier配置文件已删除: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 删除EasyTier配置文件失败: {e}")
            return False
    
    def validate_config(self, config: Dict) -> bool:
        """
        验证配置文件的有效性
        
        Args:
            config: 配置字典
            
        Returns:
            是否有效
        """
        try:
            # 检查必需字段
            required_fields = ["hostname", "instance_name", "network_identity"]
            for field in required_fields:
                if field not in config:
                    print(f"❌ 配置验证失败: 缺少必需字段 '{field}'")
                    return False
            
            # 检查网络身份
            network_identity = config.get("network_identity", {})
            if not network_identity.get("network_name") or not network_identity.get("network_secret"):
                print("❌ 配置验证失败: 网络身份信息不完整")
                return False
            
            # 检查对等节点
            peers = config.get("peer", [])
            if not peers:
                print("⚠️ 配置警告: 没有配置对等节点")
            
            print("✅ EasyTier配置验证通过")
            return True
            
        except Exception as e:
            print(f"❌ 配置验证异常: {e}")
            return False
    
    def print_config_summary(self, config: Dict):
        """打印配置摘要"""
        try:
            print("📋 EasyTier配置摘要:")
            print(f"  网络名称: {config.get('network_identity', {}).get('network_name', 'N/A')}")
            print(f"  主机名称: {config.get('hostname', 'N/A')}")
            print(f"  实例名称: {config.get('instance_name', 'N/A')}")
            print(f"  DHCP模式: {config.get('dhcp', False)}")
            
            if not config.get('dhcp', True) and config.get('ipv4'):
                print(f"  IPv4地址: {config.get('ipv4')}")
            
            peers = config.get('peer', [])
            print(f"  对等节点: {len(peers)} 个")
            for i, peer in enumerate(peers):
                print(f"    {i+1}. {peer.get('uri', 'N/A')}")
            
            flags = config.get('flags', {})
            print(f"  网络优化:")
            print(f"    KCP代理: {flags.get('enable_kcp_proxy', False)}")
            print(f"    QUIC代理: {flags.get('enable_quic_proxy', False)}")
            print(f"    延迟优先: {flags.get('latency_first', False)}")
            print(f"    多线程: {flags.get('multi_thread', False)}")
            print(f"    加密: {'启用' if not flags.get('disable_encryption', True) else '禁用'}")
            print(f"    IPv6: {'启用' if not flags.get('disable_ipv6', False) else '禁用'}")
            print(f"    压缩算法: {'zstd (data_compress_algo=2)' if flags.get('data_compress_algo') == 2 else '禁用'}")
            
        except Exception as e:
            print(f"❌ 打印配置摘要失败: {e}")
