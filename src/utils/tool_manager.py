"""
工具管理器
负责管理OnlineFix工具包的解压和工具完整性检查
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional


class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        # 路径配置
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent
            
        self.onlinefix_dir = self.root_dir / "OnlineFix"
        self.tool_zip_path = self.onlinefix_dir / "tool.zip"
        self.esr_dir = self.root_dir / "ESR"
        self.tool_dir = self.esr_dir / "tool"

        # 解压完成标志文件
        self.tool_extracted_flag = self.tool_dir / ".tool_extracted"
        
        # 必需的工具文件列表
        self.required_tools = {
            "WinIPBroadcast.exe": "IP广播工具",
            "MicrosoftEdgeWebview2Setup.exe": "WebView2安装程序"
            # KCP工具已移除，因为EasyTier自带KCP支持
        }
        
        # 确保目录存在
        self.tool_dir.mkdir(parents=True, exist_ok=True)
    
    def check_tools_integrity(self) -> Dict[str, bool]:
        """检查工具完整性"""
        integrity_status = {}
        
        for tool_file, description in self.required_tools.items():
            tool_path = self.tool_dir / tool_file
            integrity_status[tool_file] = tool_path.exists() and tool_path.is_file()
            
        return integrity_status
    
    def extract_tools(self) -> bool:
        """解压工具包到ESR/tool目录"""
        try:
            # 检查tool.zip是否存在
            if not self.tool_zip_path.exists():
                print(f"❌ 工具包不存在: {self.tool_zip_path}")
                return False
            
            print(f"📦 开始解压工具包: {self.tool_zip_path}")
            
            # 解压到临时目录，然后移动文件
            with zipfile.ZipFile(self.tool_zip_path, 'r') as zip_ref:
                # 获取压缩包内的文件列表
                file_list = zip_ref.namelist()
                print(f"📋 压缩包包含 {len(file_list)} 个文件")
                
                # 解压所有文件到tool目录
                for file_info in zip_ref.infolist():
                    # 跳过目录
                    if file_info.is_dir():
                        continue
                    
                    # 获取文件名（去除路径）
                    filename = Path(file_info.filename).name
                    
                    # 只解压我们需要的工具文件
                    if filename in self.required_tools:
                        target_path = self.tool_dir / filename
                        
                        # 如果文件已存在，先删除
                        if target_path.exists():
                            target_path.unlink()
                        
                        # 解压文件
                        with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        
                        print(f"✅ 解压完成: {filename}")
            
            print("🎉 工具包解压完成")

            # 创建解压完成标志
            self.create_extraction_flag()

            return True
            
        except Exception as e:
            print(f"❌ 解压工具包失败: {e}")
            return False
    
    def ensure_tools_available(self) -> bool:
        """确保工具可用（检查完整性，必要时解压）"""
        try:
            # 1. 检查是否已有解压完成标志
            if self.tool_extracted_flag.exists():
                # 检查工具完整性
                integrity_status = self.check_tools_integrity()
                missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

                if not missing_tools:
                    print("✅ 所有工具文件完整（已有解压标志）")
                    return True
                else:
                    print(f"⚠️ 发现缺失工具，重新解压: {', '.join(missing_tools)}")
                    # 删除标志文件，重新解压
                    self.tool_extracted_flag.unlink()

            # 2. 检查工具完整性
            integrity_status = self.check_tools_integrity()
            missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

            if not missing_tools:
                # 工具完整但没有标志，创建标志
                self.create_extraction_flag()
                print("✅ 所有工具文件完整")
                return True

            print(f"⚠️ 发现缺失工具: {', '.join(missing_tools)}")

            # 3. 检查OnlineFix文件夹中的tool.zip
            if not self.tool_zip_path.exists():
                # 检查ESR文件夹中是否有旧的tool.zip（向后兼容）
                old_tool_zip = self.esr_dir / "tool.zip"
                if old_tool_zip.exists():
                    print("📦 发现旧版tool.zip，迁移到OnlineFix文件夹")
                    self.onlinefix_dir.mkdir(exist_ok=True)
                    if self.tool_zip_path.exists():
                        self.tool_zip_path.unlink()
                    shutil.move(str(old_tool_zip), str(self.tool_zip_path))
                    print("✅ tool.zip已迁移到OnlineFix文件夹")
                else:
                    print("❌ 工具包不存在")
                    return False

            # 4. 尝试解压工具包
            if self.extract_tools():
                # 重新检查完整性
                integrity_status = self.check_tools_integrity()
                missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

                if not missing_tools:
                    print("✅ 工具解压后完整性检查通过")
                    return True
                else:
                    print(f"❌ 解压后仍有缺失工具: {', '.join(missing_tools)}")
                    return False
            else:
                print("❌ 工具包解压失败")
                return False

        except Exception as e:
            print(f"❌ 工具可用性检查失败: {e}")
            return False

    def create_extraction_flag(self):
        """创建解压完成标志文件"""
        try:
            import time
            self.tool_extracted_flag.write_text(f"Tools extracted at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("✅ 已创建工具解压完成标志")
        except Exception as e:
            print(f"创建解压标志失败: {e}")

    def ensure_tools_available_with_ui_feedback(self, log_callback=None) -> bool:
        """确保工具可用（带UI反馈）"""
        try:
            # 1. 检查是否已有解压完成标志
            if self.tool_extracted_flag.exists():
                if log_callback:
                    log_callback("🔍 检测到工具解压标志，验证完整性...", "info")

                # 检查工具完整性
                integrity_status = self.check_tools_integrity()
                missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

                if not missing_tools:
                    if log_callback:
                        log_callback("✅ 网络优化工具完整性验证通过", "success")
                    print("✅ 所有工具文件完整（已有解压标志）")
                    return True
                else:
                    if log_callback:
                        log_callback(f"⚠️ 发现缺失工具，准备重新解压: {', '.join(missing_tools)}", "warning")
                    print(f"⚠️ 发现缺失工具，重新解压: {', '.join(missing_tools)}")
                    # 删除标志文件，重新解压
                    self.tool_extracted_flag.unlink()

            # 2. 检查工具完整性
            integrity_status = self.check_tools_integrity()
            missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

            if not missing_tools:
                # 工具完整但没有标志，创建标志
                self.create_extraction_flag()
                if log_callback:
                    log_callback("✅ 网络优化工具已完整", "success")
                print("✅ 所有工具文件完整")
                return True

            if log_callback:
                log_callback(f"⚠️ 发现缺失工具: {', '.join(missing_tools)}", "warning")
            print(f"⚠️ 发现缺失工具: {', '.join(missing_tools)}")

            # 3. 检查OnlineFix文件夹中的tool.zip
            if not self.tool_zip_path.exists():
                # 检查ESR文件夹中是否有旧的tool.zip（向后兼容）
                old_tool_zip = self.esr_dir / "tool.zip"
                if old_tool_zip.exists():
                    if log_callback:
                        log_callback("📦 发现旧版tool.zip，正在迁移到OnlineFix文件夹...", "info")
                    print("📦 发现旧版tool.zip，迁移到OnlineFix文件夹")
                    self.onlinefix_dir.mkdir(exist_ok=True)
                    if self.tool_zip_path.exists():
                        self.tool_zip_path.unlink()
                    shutil.move(str(old_tool_zip), str(self.tool_zip_path))
                    if log_callback:
                        log_callback("✅ tool.zip已迁移到OnlineFix文件夹", "success")
                    print("✅ tool.zip已迁移到OnlineFix文件夹")
                else:
                    if log_callback:
                        log_callback("❌ 工具包不存在，请重新下载程序", "error")
                    print("❌ 工具包不存在")
                    return False

            # 4. 尝试解压工具包
            if log_callback:
                log_callback("📦 正在解压网络优化工具包，请稍候...", "info")

            if self.extract_tools_with_ui_feedback(log_callback):
                # 重新检查完整性
                integrity_status = self.check_tools_integrity()
                missing_tools = [tool for tool, exists in integrity_status.items() if not exists]

                if not missing_tools:
                    if log_callback:
                        log_callback("✅ 网络优化工具解压完成", "success")
                    print("✅ 工具解压后完整性检查通过")
                    return True
                else:
                    if log_callback:
                        log_callback(f"❌ 解压后仍有缺失工具: {', '.join(missing_tools)}", "error")
                    print(f"❌ 解压后仍有缺失工具: {', '.join(missing_tools)}")
                    return False
            else:
                if log_callback:
                    log_callback("❌ 网络优化工具包解压失败", "error")
                print("❌ 工具包解压失败")
                return False

        except Exception as e:
            if log_callback:
                log_callback(f"❌ 工具可用性检查失败: {e}", "error")
            print(f"❌ 工具可用性检查失败: {e}")
            return False

    def extract_tools_with_ui_feedback(self, log_callback=None) -> bool:
        """解压工具包（带UI反馈）"""
        try:
            if not self.tool_zip_path.exists():
                if log_callback:
                    log_callback("❌ 工具包文件不存在", "error")
                print("❌ 工具包文件不存在")
                return False

            # 确保目标目录存在
            self.tool_dir.mkdir(parents=True, exist_ok=True)

            if log_callback:
                log_callback(f"📦 开始解压工具包: {self.tool_zip_path.name}", "info")
            print(f"📦 开始解压工具包: {self.tool_zip_path}")

            import zipfile
            with zipfile.ZipFile(self.tool_zip_path, 'r') as zip_ref:
                # 获取压缩包中的文件列表
                file_list = zip_ref.namelist()
                if log_callback:
                    log_callback(f"📋 压缩包包含 {len(file_list)} 个文件", "info")
                print(f"📋 压缩包包含 {len(file_list)} 个文件")

                # 解压每个文件
                extracted_count = 0
                for file_info in zip_ref.infolist():
                    if file_info.is_dir():
                        continue

                    filename = Path(file_info.filename).name
                    if filename in self.required_tools:
                        target_path = self.tool_dir / filename

                        with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)

                        if log_callback:
                            log_callback(f"✅ 解压完成: {filename}", "info")
                        print(f"✅ 解压完成: {filename}")
                        extracted_count += 1

                if log_callback:
                    log_callback(f"🎉 工具包解压完成，共解压 {extracted_count} 个文件", "success")
                print("🎉 工具包解压完成")

            # 创建解压完成标志
            self.create_extraction_flag()

            return True

        except Exception as e:
            if log_callback:
                log_callback(f"❌ 工具包解压失败: {e}", "error")
            print(f"❌ 工具包解压失败: {e}")
            return False
    
    def get_tool_path(self, tool_name: str) -> Optional[Path]:
        """获取工具路径"""
        if tool_name not in self.required_tools:
            return None
        
        tool_path = self.tool_dir / tool_name
        return tool_path if tool_path.exists() else None
    
    def get_tools_status(self) -> Dict[str, Dict]:
        """获取工具状态信息"""
        status = {}
        
        for tool_file, description in self.required_tools.items():
            tool_path = self.tool_dir / tool_file
            exists = tool_path.exists()
            
            status[tool_file] = {
                "description": description,
                "exists": exists,
                "path": str(tool_path) if exists else None,
                "size": tool_path.stat().st_size if exists else 0
            }
        
        return status
    
    def cleanup_tools(self):
        """清理工具（可选，一般不需要）"""
        try:
            if self.tool_dir.exists():
                for tool_file in self.required_tools.keys():
                    tool_path = self.tool_dir / tool_file
                    if tool_path.exists():
                        tool_path.unlink()
                        print(f"🗑️ 已删除: {tool_file}")
            print("🧹 工具清理完成")
        except Exception as e:
            print(f"❌ 工具清理失败: {e}")
