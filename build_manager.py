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
    
    def install_tool(self, tool_name: str) -> bool:
        """安装打包工具"""
        print(f"📦 正在安装 {tool_name}...")

        # 特殊处理Nuitka，需要同时安装imageio
        packages = [tool_name]
        if tool_name == "nuitka":
            packages.append("imageio")
            print("  同时安装imageio（Nuitka图标处理需要）")

        try:
            for package in packages:
                subprocess.run([sys.executable, "-m", "pip", "install", package],
                             check=True, capture_output=True)
                print(f"  ✅ {package} 安装成功")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ {tool_name} 安装失败")
            return False
    
    def run_build_script(self, script_name: str) -> bool:
        """运行打包脚本"""
        script_path = self.project_root / script_name
        
        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            return False
        
        try:
            print(f"🚀 执行打包脚本: {script_name}")
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run([sys.executable, str(script_path)],
                                  cwd=self.project_root, creationflags=creation_flags)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 执行脚本失败: {e}")
            return False
    
    def show_results(self):
        """显示打包结果"""
        print("\n📊 打包结果汇总:")
        print("-" * 40)

        if not self.builds_dir.exists():
            print("❌ 没有找到Builds目录")
            return

        # 检查PyInstaller输出
        pyinstaller_dir = self.builds_dir / "PyInstaller"
        if pyinstaller_dir.exists():
            print("🔧 PyInstaller 输出:")
            exe_files = list(pyinstaller_dir.glob("*.exe"))
            dirs = [d for d in pyinstaller_dir.iterdir() if d.is_dir()]

            if exe_files:
                for exe_file in exe_files:
                    size_mb = exe_file.stat().st_size / (1024 * 1024)
                    print(f"  • {exe_file.name} ({size_mb:.1f} MB)")

            if dirs:
                for dir_path in dirs:
                    exe_in_dir = list(dir_path.glob("*.exe"))
                    if exe_in_dir:
                        print(f"  • {dir_path.name}/ (包含 {len(exe_in_dir)} 个exe文件)")

        # 检查Nuitka输出
        nuitka_dir = self.builds_dir / "Nuitka"
        if nuitka_dir.exists():
            print("⚡ Nuitka 输出:")
            exe_files = list(nuitka_dir.glob("*.exe"))
            dirs = [d for d in nuitka_dir.iterdir() if d.is_dir()]

            if exe_files:
                for exe_file in exe_files:
                    size_mb = exe_file.stat().st_size / (1024 * 1024)
                    print(f"  • {exe_file.name} ({size_mb:.1f} MB)")

            if dirs:
                for dir_path in dirs:
                    exe_in_dir = list(dir_path.glob("*.exe"))
                    if exe_in_dir:
                        print(f"  • {dir_path.name}/ (包含 {len(exe_in_dir)} 个exe文件)")

        if not pyinstaller_dir.exists() and not nuitka_dir.exists():
            print("❌ 没有找到打包输出文件")
    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print("\n" + "=" * 60)
            print("📋 选择打包方案:")
            print("1. PyInstaller - 单文件模式")
            print("2. PyInstaller - 目录模式") 
            print("3. PyInstaller - 两种模式")
            print("4. Nuitka - 单文件模式")
            print("5. Nuitka - 独立模式")
            print("6. Nuitka - 两种模式")
            print("7. 全部打包 (PyInstaller + Nuitka)")
            print("8. 查看打包结果")
            print("9. 清理输出文件")
            print("0. 退出")
            
            try:
                choice = input("\n请选择 (0-9): ").strip()
                
                if choice == '0':
                    print("👋 退出打包工具")
                    break
                elif choice == '1':
                    self._build_pyinstaller_onefile()
                elif choice == '2':
                    self._build_pyinstaller_onedir()
                elif choice == '3':
                    self._build_pyinstaller_both()
                elif choice == '4':
                    self._build_nuitka_onefile()
                elif choice == '5':
                    self._build_nuitka_standalone()
                elif choice == '6':
                    self._build_nuitka_both()
                elif choice == '7':
                    self._build_all()
                elif choice == '8':
                    self.show_results()
                elif choice == '9':
                    self._clean_output()
                else:
                    print("❌ 无效选择，请重试")
                    
            except KeyboardInterrupt:
                print("\n👋 用户取消操作")
                break
            except Exception as e:
                print(f"❌ 操作异常: {e}")
    
    def _build_pyinstaller_onefile(self):
        """PyInstaller单文件模式"""
        print("\n🚀 PyInstaller - 单文件模式")
        # 模拟选择1的输入
        self._run_pyinstaller_with_input("1")
    
    def _build_pyinstaller_onedir(self):
        """PyInstaller目录模式"""
        print("\n🚀 PyInstaller - 目录模式")
        # 模拟选择2的输入
        self._run_pyinstaller_with_input("2")
    
    def _build_pyinstaller_both(self):
        """PyInstaller两种模式"""
        print("\n🚀 PyInstaller - 两种模式")
        # 模拟选择3的输入
        self._run_pyinstaller_with_input("3")
    
    def _build_nuitka_onefile(self):
        """Nuitka单文件模式"""
        print("\n🚀 Nuitka - 单文件模式")
        # 模拟选择1的输入
        self._run_nuitka_with_input("1")
    
    def _build_nuitka_standalone(self):
        """Nuitka独立模式"""
        print("\n🚀 Nuitka - 独立模式")
        # 模拟选择2的输入
        self._run_nuitka_with_input("2")
    
    def _build_nuitka_both(self):
        """Nuitka两种模式"""
        print("\n🚀 Nuitka - 两种模式")
        # 模拟选择3的输入
        self._run_nuitka_with_input("3")
    
    def _build_all(self):
        """全部打包"""
        print("\n🚀 全部打包 (PyInstaller + Nuitka)")
        
        # 检查工具
        tools = self.check_tools()
        
        success_count = 0
        total_count = 0
        
        if tools.get('pyinstaller', False):
            print("\n" + "="*50)
            print("🔧 PyInstaller 打包...")
            if self._run_pyinstaller_with_input("3"):
                success_count += 1
            total_count += 1
        else:
            print("⚠️ PyInstaller 不可用，跳过")
        
        if tools.get('nuitka', False):
            print("\n" + "="*50)
            print("🔧 Nuitka 打包...")
            if self._run_nuitka_with_input("3"):
                success_count += 1
            total_count += 1
        else:
            print("⚠️ Nuitka 不可用，跳过")
        
        print(f"\n📊 全部打包结果: {success_count}/{total_count} 成功")
    
    def _run_pyinstaller_with_input(self, choice: str) -> bool:
        """运行PyInstaller脚本并提供输入"""
        script_path = self.project_root / "build_pyinstaller.py"
        
        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            return False
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.project_root
            )
            
            # 发送选择
            stdout, _ = process.communicate(input=choice)
            
            # 显示输出
            print(stdout)
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"❌ 执行PyInstaller脚本失败: {e}")
            return False
    
    def _run_nuitka_with_input(self, choice: str) -> bool:
        """运行Nuitka脚本并提供输入"""
        script_path = self.project_root / "build_nuitka.py"
        
        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            return False
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.project_root
            )
            
            # 发送选择
            stdout, _ = process.communicate(input=choice)
            
            # 显示输出
            print(stdout)
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"❌ 执行Nuitka脚本失败: {e}")
            return False
    
    def _clean_output(self):
        """清理输出文件"""
        print("\n🧹 清理输出文件...")

        dirs_to_clean = [
            self.builds_dir,
            self.project_root / "build",
            self.project_root / ".nuitka",
        ]

        cleaned_count = 0
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"  删除: {dir_path}")
                cleaned_count += 1

        # 清理spec文件
        for spec_file in self.project_root.glob("*.spec"):
            spec_file.unlink()
            print(f"  删除: {spec_file}")
            cleaned_count += 1

        # 清理__pycache__
        for pycache in self.project_root.rglob("__pycache__"):
            import shutil
            shutil.rmtree(pycache)
            cleaned_count += 1

        if cleaned_count > 0:
            print(f"✅ 清理完成，删除了 {cleaned_count} 个项目")
        else:
            print("✅ 没有需要清理的文件")


def main():
    """主函数"""
    manager = BuildManager()
    manager.show_banner()
    
    # 检查工具可用性
    tools = manager.check_tools()
    
    # 提示安装缺失的工具
    missing_tools = [tool for tool, available in tools.items() if not available]
    if missing_tools:
        print(f"\n⚠️ 缺少打包工具: {', '.join(missing_tools)}")
        print("💡 建议安装:")
        for tool in missing_tools:
            print(f"   pip install {tool}")
        
        install_choice = input("\n是否现在安装缺失的工具? (y/N): ").strip().lower()
        if install_choice == 'y':
            for tool in missing_tools:
                if manager.install_tool(tool):
                    tools[tool] = True
    
    # 检查是否有可用的工具
    available_tools = [tool for tool, available in tools.items() if available]
    if not available_tools:
        print("❌ 没有可用的打包工具，请先安装 PyInstaller 或 Nuitka")
        return False
    
    print(f"\n✅ 可用的打包工具: {', '.join(available_tools)}")
    
    # 启动交互式菜单
    manager.interactive_menu()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        sys.exit(0)
