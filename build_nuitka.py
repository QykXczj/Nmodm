#!/usr/bin/env python3
"""
Nuitka 打包脚本
支持单文件模式和目录模式打包
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, List


class NuitkaBuilder:
    """Nuitka打包器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / "src"
        self.builds_dir = self.project_root / "Builds"
        self.dist_dir = self.builds_dir / "Nuitka"
        self.version = "3.0.0"  # 应用版本号
        self.build_dir = self.project_root / "build"
        
    def check_environment(self) -> bool:
        """检查打包环境"""
        print("🔍 检查打包环境...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ Python版本过低，需要3.8+")
            return False
        print(f"✅ Python版本: {sys.version}")
        
        # 检查Nuitka
        try:
            import nuitka
            print(f"✅ Nuitka已安装")
        except ImportError:
            print("❌ Nuitka未安装，正在安装...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"],
                             check=True, capture_output=True)
                print("✅ Nuitka安装成功")
            except subprocess.CalledProcessError:
                print("❌ Nuitka安装失败")
                return False

        # 检查imageio（Nuitka处理图标需要）
        try:
            import imageio
            print(f"✅ imageio已安装")
        except ImportError:
            print("❌ imageio未安装，正在安装...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "imageio"],
                             check=True, capture_output=True)
                print("✅ imageio安装成功")
            except subprocess.CalledProcessError:
                print("❌ imageio安装失败")
                return False
        
        # 检查C++编译器
        try:
            result = subprocess.run(["gcc", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ GCC编译器可用")
            else:
                print("⚠️ GCC不可用，将尝试使用MSVC")
        except FileNotFoundError:
            print("⚠️ GCC不可用，将尝试使用MSVC")
        
        # 检查PySide6
        try:
            import PySide6
            print(f"✅ PySide6已安装")
        except ImportError:
            print("❌ PySide6未安装，请先安装依赖: pip install -r requirements.txt")
            return False
        
        # 检查必要文件
        required_files = [
            self.project_root / "main.py",
            self.project_root / "zwnr.png",
            self.project_root / "OnlineFix",
            self.project_root / "ESL",
            self.src_dir,
        ]
        
        for file_path in required_files:
            if file_path.exists():
                print(f"✅ {file_path.name}")
            else:
                print(f"❌ 缺少必要文件: {file_path}")
                return False
        
        return True
    
    def clean_build_files(self):
        """清理构建文件"""
        print("🧹 清理旧的构建文件...")

        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  删除: {dir_path}")

        # 清理Nuitka缓存
        nuitka_cache = self.project_root / ".nuitka"
        if nuitka_cache.exists():
            shutil.rmtree(nuitka_cache)
            print(f"  删除: {nuitka_cache}")

        # 清理__pycache__
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)

        print("✅ 清理完成")

    def ensure_builds_dir(self):
        """确保Builds目录存在"""
        self.builds_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
    
    def get_data_files(self) -> List[str]:
        """获取数据文件列表"""
        data_files = []

        # 添加图标文件
        icon_file = self.project_root / "zwnr.png"
        if icon_file.exists():
            data_files.append(f"--include-data-file={icon_file}=zwnr.png")

        # 添加OnlineFix目录 - 逐个文件添加以确保包含所有文件
        onlinefix_dir = self.project_root / "OnlineFix"
        if onlinefix_dir.exists():
            # 递归添加OnlineFix目录中的所有文件
            for file_path in onlinefix_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.project_root)
                    data_files.append(f"--include-data-file={file_path}={rel_path}")

        # 添加ESL目录 - 逐个文件添加以确保包含所有文件
        esl_dir = self.project_root / "ESL"
        if esl_dir.exists():
            # 递归添加ESL目录中的所有文件
            for file_path in esl_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.project_root)
                    data_files.append(f"--include-data-file={file_path}={rel_path}")

        return data_files
    
    def get_include_modules(self) -> List[str]:
        """获取需要包含的模块"""
        modules = [
            # 让Nuitka自动发现依赖，只指定关键模块
            "--include-package=src",
            "--include-module=urllib.request",
            "--include-module=dataclasses",
            "--include-module=typing",
            "--include-module=enum",
            "--include-module=datetime",
            "--include-module=time",
            "--include-module=os",
            "--include-module=sys",
            "--include-module=re",
        ]
        
        return modules
    
    def build(self, onefile: bool = True, clean: bool = True) -> bool:
        """执行打包"""
        mode_name = "单文件" if onefile else "目录"
        print(f"🚀 开始Nuitka打包 ({mode_name}模式)...")

        if clean:
            self.clean_build_files()

        # 确保Builds目录存在
        self.ensure_builds_dir()
        
        # 构建命令
        cmd = [
            sys.executable, "-m", "nuitka",
            "--assume-yes-for-downloads",  # 自动下载依赖
            "--warn-implicit-exceptions",  # 警告隐式异常
            "--warn-unusual-code",         # 警告异常代码
            "--enable-plugin=pyside6",     # 启用PySide6插件
            "--disable-console",           # 禁用控制台窗口
        ]

        # 设置图标（检查图标文件是否存在）
        icon_file = self.project_root / "zwnr.png"
        if icon_file.exists():
            cmd.append(f"--windows-icon-from-ico={icon_file}")
        else:
            print("⚠️ 图标文件不存在，跳过图标设置")
        
        # 添加模式特定参数
        if onefile:
            cmd.append("--onefile")
            output_name = "Nmodm_nuitka_onefile.exe"
        else:
            cmd.append("--standalone")
            output_name = "Nmodm_nuitka_standalone"
        
        # 添加输出目录
        cmd.extend([
            f"--output-dir={self.dist_dir}",
            f"--output-filename={output_name}",
        ])
        
        # 添加数据文件
        data_files = self.get_data_files()
        cmd.extend(data_files)
        
        # 添加包含模块
        include_modules = self.get_include_modules()
        cmd.extend(include_modules)
        
        # 添加排除模块（简化列表）
        exclude_modules = [
            "--nofollow-import-to=tkinter",
            "--nofollow-import-to=matplotlib",
            "--nofollow-import-to=numpy",
            "--nofollow-import-to=pytest",
            "--nofollow-import-to=setuptools",
        ]
        cmd.extend(exclude_modules)
        
        # 添加主文件
        cmd.append("main.py")
        
        # 执行Nuitka
        start_time = time.time()
        try:
            print(f"执行命令: {' '.join(cmd[:5])}... (共{len(cmd)}个参数)")
            print("⏳ 编译中，这可能需要几分钟时间...")

            result = subprocess.run(cmd, cwd=self.project_root,
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                elapsed = time.time() - start_time
                print(f"✅ 打包成功！耗时: {elapsed:.1f}秒")
                
                # 检查输出文件
                if onefile:
                    exe_path = self.dist_dir / f"{output_name}"
                    if exe_path.exists():
                        size_mb = exe_path.stat().st_size / (1024 * 1024)
                        print(f"📁 输出文件: {exe_path}")
                        print(f"📊 文件大小: {size_mb:.1f} MB")
                    else:
                        print("❌ 未找到输出的exe文件")
                        return False
                else:
                    # Nuitka默认创建main.dist目录
                    exe_dir = self.dist_dir / "main.dist"
                    if exe_dir.exists():
                        exe_path = exe_dir / f"{output_name}.exe"
                        print(f"📁 输出目录: {exe_dir}")
                        if exe_path.exists():
                            print(f"📁 主执行文件: {exe_path}")
                        else:
                            print("⚠️ 主执行文件位置可能不同")
                            # 查找目录中的exe文件
                            exe_files = list(exe_dir.glob("*.exe"))
                            if exe_files:
                                print(f"📁 找到执行文件: {exe_files[0]}")

                        # 重命名目录为更友好的名称
                        target_dir = self.dist_dir / output_name
                        if target_dir.exists():
                            import shutil
                            shutil.rmtree(target_dir)
                        exe_dir.rename(target_dir)
                        print(f"📁 重命名为: {target_dir}")
                    else:
                        print("❌ 未找到输出目录")
                        return False
                
                return True
            else:
                print("❌ 打包失败！")
                print("错误输出:")
                print(result.stderr)
                if result.stdout:
                    print("标准输出:")
                    print(result.stdout)
                return False
                
        except Exception as e:
            print(f"❌ 打包异常: {e}")
            return False
    
    def test_executable(self, onefile: bool = True) -> bool:
        """测试可执行文件"""
        print("🧪 测试可执行文件...")
        
        if onefile:
            exe_path = self.dist_dir / "Nmodm_nuitka_onefile.exe"
        else:
            exe_dir = self.dist_dir / "Nmodm_nuitka_standalone"
            exe_path = exe_dir / "Nmodm_nuitka_standalone.exe"
            if not exe_path.exists():
                # 尝试其他可能的名称
                for possible_name in ["main.exe", "Nmodm.exe"]:
                    test_path = exe_dir / possible_name
                    if test_path.exists():
                        exe_path = test_path
                        break
        
        if not exe_path.exists():
            print(f"❌ 可执行文件不存在: {exe_path}")
            return False
        
        try:
            # 简单启动测试（3秒后自动关闭）
            print("启动应用程序进行快速测试...")
            process = subprocess.Popen([str(exe_path)], 
                                     cwd=exe_path.parent)
            
            # 等待3秒
            time.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                print("✅ 应用程序启动成功")
                process.terminate()
                process.wait(timeout=5)
                return True
            else:
                print("❌ 应用程序启动失败")
                return False
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False


def main():
    """主函数"""
    print("🎯 Nuitka 自动打包工具")
    print("=" * 50)
    print("⚠️ 注意: Nuitka首次使用可能需要下载C++编译器")
    print("⚠️ 编译时间较长，请耐心等待")
    
    builder = NuitkaBuilder()
    
    # 检查环境
    if not builder.check_environment():
        print("❌ 环境检查失败，请修复问题后重试")
        return False
    
    print("\n📋 选择打包模式:")
    print("1. 单文件模式 (onefile)")
    print("2. 独立模式 (standalone)")
    print("3. 两种模式都打包")
    
    try:
        choice = input("\n请选择 (1/2/3): ").strip()
        
        success_count = 0
        total_count = 0
        
        if choice in ['1', '3']:
            print(f"\n{'='*50}")
            print("🚀 开始单文件模式打包...")
            total_count += 1
            if builder.build(onefile=True):
                if builder.test_executable(onefile=True):
                    success_count += 1
                    print("✅ 单文件模式打包完成并测试通过")
                else:
                    print("⚠️ 单文件模式打包完成但测试失败")
            else:
                print("❌ 单文件模式打包失败")
        
        if choice in ['2', '3']:
            print(f"\n{'='*50}")
            print("🚀 开始独立模式打包...")
            total_count += 1
            if builder.build(onefile=False):
                if builder.test_executable(onefile=False):
                    success_count += 1
                    print("✅ 独立模式打包完成并测试通过")
                else:
                    print("⚠️ 独立模式打包完成但测试失败")
            else:
                print("❌ 独立模式打包失败")
        
        if choice not in ['1', '2', '3']:
            print("❌ 无效选择")
            return False
        
        # 总结
        print(f"\n{'='*50}")
        print(f"📊 打包结果: {success_count}/{total_count} 成功")
        
        if success_count > 0:
            print("\n🎉 打包完成！输出文件位置:")
            if choice in ['1', '3']:
                print(f"  📁 单文件: dist/Nmodm_nuitka_onefile.exe")
            if choice in ['2', '3']:
                print(f"  📁 独立模式: dist/Nmodm_nuitka_standalone/")
            
            print("\n💡 建议:")
            print("  - Nuitka编译的程序性能更好")
            print("  - 在不同Windows系统上测试兼容性")
            print("  - 检查所有功能是否正常工作")
            print("  - 单文件模式适合分发，独立模式启动更快")
        
        return success_count == total_count
        
    except KeyboardInterrupt:
        print("\n❌ 用户取消操作")
        return False
    except Exception as e:
        print(f"\n❌ 操作异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
