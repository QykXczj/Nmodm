#!/usr/bin/env python3
"""
统一打包管理脚本
支持PyInstaller和Nuitka两种打包工具
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class BuildManager:
    """统一打包管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.builds_dir = self.project_root / "Builds"
        
    def show_banner(self):
        """显示横幅"""
        print("🎯 Nmodm 统一打包管理工具")
        print("=" * 60)
        print("支持 PyInstaller 和 Nuitka 两种打包方案")
        print("支持 单文件模式 和 目录模式")
        print("=" * 60)
    
    def check_tools(self) -> Dict[str, bool]:
        """检查打包工具可用性"""
        print("🔍 检查打包工具...")
        
        tools = {}
        
        # 检查PyInstaller
        try:
            import PyInstaller
            tools['pyinstaller'] = True
            print(f"✅ PyInstaller: {PyInstaller.__version__}")
        except ImportError:
            tools['pyinstaller'] = False
            print("❌ PyInstaller: 未安装")
        
        # 检查Nuitka
        try:
            import nuitka
            tools['nuitka'] = True
            print("✅ Nuitka: 已安装")
        except ImportError:
            tools['nuitka'] = False
            print("❌ Nuitka: 未安装")
        
        return tools
    
    def show_menu(self, tools: Dict[str, bool]) -> Tuple[str, str]:
        """显示菜单并获取用户选择"""
        print("\n📋 选择打包工具:")
        
        options = []
        if tools['pyinstaller']:
            options.extend([
                ("1", "PyInstaller - 单文件模式"),
                ("2", "PyInstaller - 目录模式")
            ])
        
        if tools['nuitka']:
            options.extend([
                ("3", "Nuitka - 单文件模式"),
                ("4", "Nuitka - 目录模式")
            ])
        
        options.append(("5", "安装缺失的打包工具"))
        options.append(("0", "退出"))
        
        for key, desc in options:
            print(f"  {key}. {desc}")
        
        while True:
            choice = input("\n请选择 (0-5): ").strip()
            
            if choice == "0":
                return "exit", ""
            elif choice == "1" and tools['pyinstaller']:
                return "pyinstaller", "onefile"
            elif choice == "2" and tools['pyinstaller']:
                return "pyinstaller", "onedir"
            elif choice == "3" and tools['nuitka']:
                return "nuitka", "onefile"
            elif choice == "4" and tools['nuitka']:
                return "nuitka", "onedir"
            elif choice == "5":
                return "install", ""
            else:
                print("❌ 无效选择，请重试")
    
    def install_tools(self):
        """安装打包工具"""
        print("\n🔧 安装打包工具...")
        
        try:
            # 运行依赖安装脚本
            install_script = self.project_root / "install_dependencies.py"
            if install_script.exists():
                print("📦 运行依赖安装脚本...")
                subprocess.run([sys.executable, str(install_script)], check=True)
            else:
                print("📦 手动安装打包工具...")
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "nuitka"], check=True)
            
            print("✅ 打包工具安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {e}")
            return False
    
    def run_build(self, tool: str, mode: str):
        """执行打包"""
        print(f"\n🚀 开始 {tool.upper()} {mode} 打包...")
        
        # 确保Builds目录存在
        self.builds_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        
        try:
            if tool == "pyinstaller":
                script_path = self.project_root / "build_pyinstaller.py"
            else:  # nuitka
                script_path = self.project_root / "build_nuitka.py"
            
            if not script_path.exists():
                print(f"❌ 打包脚本不存在: {script_path}")
                return False
            
            # 设置环境变量来指定模式
            env = os.environ.copy()
            env['BUILD_MODE'] = mode
            
            # 执行打包脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                env=env,
                cwd=self.project_root,
                capture_output=False,
                text=True
            )
            
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"\n🎉 打包成功完成！")
                print(f"⏱️  用时: {elapsed_time:.1f} 秒")
                print(f"📁 输出目录: {self.builds_dir}")
                return True
            else:
                print(f"\n❌ 打包失败，退出代码: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ 打包过程中出错: {e}")
            return False
    
    def show_results(self):
        """显示打包结果"""
        if not self.builds_dir.exists():
            print("📁 没有找到打包输出目录")
            return
        
        print(f"\n📊 打包结果统计:")
        print(f"📁 输出目录: {self.builds_dir}")
        
        # 统计各种打包结果
        pyinstaller_dir = self.builds_dir / "PyInstaller"
        nuitka_dir = self.builds_dir / "Nuitka"
        
        if pyinstaller_dir.exists():
            print(f"  📦 PyInstaller: {len(list(pyinstaller_dir.iterdir()))} 个输出")
        
        if nuitka_dir.exists():
            print(f"  📦 Nuitka: {len(list(nuitka_dir.iterdir()))} 个输出")
    
    def run(self):
        """主运行函数"""
        self.show_banner()
        
        while True:
            tools = self.check_tools()
            
            if not any(tools.values()):
                print("\n⚠️  没有可用的打包工具")
                if input("是否安装打包工具? (y/n): ").lower() == 'y':
                    if self.install_tools():
                        continue
                    else:
                        break
                else:
                    break
            
            tool, mode = self.show_menu(tools)
            
            if tool == "exit":
                break
            elif tool == "install":
                self.install_tools()
                continue
            else:
                success = self.run_build(tool, mode)
                if success:
                    self.show_results()
                
                if input("\n是否继续打包? (y/n): ").lower() != 'y':
                    break
        
        print("\n👋 感谢使用 Nmodm 打包工具！")


def main():
    """主函数"""
    try:
        manager = BuildManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")


if __name__ == "__main__":
    main()