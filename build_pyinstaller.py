#!/usr/bin/env python3
"""
PyInstaller 打包脚本
支持单文件模式和目录模式打包
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, List


class PyInstallerBuilder:
    """PyInstaller打包器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / "src"
        self.builds_dir = self.project_root / "Builds"
        self.dist_dir = self.builds_dir / "PyInstaller"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "nmodm.spec"
        self.version = "3.0.3"  # 应用版本号
        
    def check_environment(self) -> bool:
        """检查打包环境"""
        print("🔍 检查打包环境...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ Python版本过低，需要3.8+")
            return False
        print(f"✅ Python版本: {sys.version}")
        
        # 检查PyInstaller
        try:
            import PyInstaller
            print(f"✅ PyInstaller版本: {PyInstaller.__version__}")
        except ImportError:
            print("❌ PyInstaller未安装，正在安装...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                             check=True, capture_output=True)
                print("✅ PyInstaller安装成功")
            except subprocess.CalledProcessError:
                print("❌ PyInstaller安装失败")
                return False
        
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

        # 清理__pycache__
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)

        print("✅ 清理完成")

    def ensure_builds_dir(self):
        """确保Builds目录存在"""
        self.builds_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
    
    def create_spec_file(self, onefile: bool = True) -> Path:
        """创建spec文件"""
        print(f"📝 创建spec文件 ({'单文件' if onefile else '目录'}模式)...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 项目根目录
project_root = Path.cwd()

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 静态资源文件
        ('zwnr.png', '.'),

        # OnlineFix目录 - 包含破解文件、ESL工具包、网络优化工具包等
        ('OnlineFix', 'OnlineFix'),

        # ESL目录不再需要打包 - 现在从OnlineFix/esl2.zip解压
        # 注释：ESL工具现在统一从OnlineFix文件夹的esl2.zip解压，无需预置ESL目录

        # 源代码目录
        ('src', 'src'),
    ],
    hiddenimports=[
        # PySide6相关模块
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        
        # 项目核心模块
        'src.app',
        'src.config.config_manager',
        'src.config.mod_config_manager',
        'src.ui.main_window',
        'src.ui.sidebar',
        'src.utils.download_manager',
        
        # UI页面模块
        'src.ui.pages.base_page',
        'src.ui.pages.home_page',
        'src.ui.pages.config_page',
        'src.ui.pages.me3_page',
        'src.ui.pages.mods_page',
        'src.ui.pages.bin_merge_page',
        'src.ui.pages.lan_gaming_page',
        'src.ui.pages.about_page',
        
        # 标准库模块
        'json', 'toml', 'pathlib', 'subprocess', 'threading',
        'requests', 'tempfile', 'zipfile', 'shutil', 'configparser',
        'urllib.parse', 'urllib.request', 'dataclasses', 'typing',
        'enum', 'datetime', 'time', 'os', 'sys', 're',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型模块
        'tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'cv2', 'jupyter', 'IPython', 'notebook',
        'sphinx', 'pytest', 'setuptools', 'wheel', 'pip',
        'conda', 'anaconda', 'spyder', 'pyqt5', 'wx',
        'gtk', 'kivy', 'django', 'flask', 'tornado',
        'sqlalchemy', 'pymongo', 'redis', 'celery',
        'scrapy', 'beautifulsoup4', 'lxml', 'selenium',
        'tensorflow', 'torch', 'keras', 'sklearn',
        'plotly', 'bokeh', 'seaborn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,'''
        
        if onefile:
            spec_content += '''
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Nmodm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='zwnr.png',  # 应用程序图标
)'''
        else:
            spec_content += '''
    [],
    exclude_binaries=True,
    name='Nmodm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='zwnr.png',  # 应用程序图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Nmodm'
)'''
        
        # 写入spec文件
        spec_filename = f"nmodm_{'onefile' if onefile else 'onedir'}.spec"
        spec_path = self.project_root / spec_filename
        
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ Spec文件创建: {spec_path}")
        return spec_path
    
    def build(self, onefile: bool = True, clean: bool = True) -> bool:
        """执行打包"""
        mode_name = "单文件" if onefile else "目录"
        print(f"🚀 开始PyInstaller打包 ({mode_name}模式)...")

        if clean:
            self.clean_build_files()

        # 确保Builds目录存在
        self.ensure_builds_dir()

        # 创建spec文件
        spec_path = self.create_spec_file(onefile)
        
        # 执行PyInstaller
        start_time = time.time()
        try:
            cmd = [sys.executable, "-m", "PyInstaller",
                   "--distpath", str(self.dist_dir),
                   str(spec_path)]
            print(f"执行命令: {' '.join(cmd)}")

            result = subprocess.run(cmd, cwd=self.project_root,
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                elapsed = time.time() - start_time
                print(f"✅ 打包成功！耗时: {elapsed:.1f}秒")
                
                # 检查输出文件
                if onefile:
                    exe_path = self.dist_dir / "Nmodm.exe"
                    if exe_path.exists():
                        size_mb = exe_path.stat().st_size / (1024 * 1024)
                        print(f"📁 输出文件: {exe_path}")
                        print(f"📊 文件大小: {size_mb:.1f} MB")
                    else:
                        print("❌ 未找到输出的exe文件")
                        return False
                else:
                    exe_dir = self.dist_dir / "Nmodm"
                    exe_path = exe_dir / "Nmodm.exe"
                    if exe_path.exists():
                        print(f"📁 输出目录: {exe_dir}")
                        print(f"📁 主执行文件: {exe_path}")
                    else:
                        print("❌ 未找到输出目录")
                        return False
                
                return True
            else:
                print("❌ 打包失败！")
                print("错误输出:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 打包异常: {e}")
            return False
    
    def test_executable(self, onefile: bool = True) -> bool:
        """测试可执行文件"""
        print("🧪 测试可执行文件...")
        
        if onefile:
            exe_path = self.dist_dir / "Nmodm.exe"
        else:
            exe_path = self.dist_dir / "Nmodm" / "Nmodm.exe"
        
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
    print("🎯 PyInstaller 自动打包工具")
    print("=" * 50)
    
    builder = PyInstallerBuilder()
    
    # 检查环境
    if not builder.check_environment():
        print("❌ 环境检查失败，请修复问题后重试")
        return False
    
    print("\n📋 选择打包模式:")
    print("1. 单文件模式 (onefile)")
    print("2. 目录模式 (onedir)")
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
            print("🚀 开始目录模式打包...")
            total_count += 1
            if builder.build(onefile=False):
                if builder.test_executable(onefile=False):
                    success_count += 1
                    print("✅ 目录模式打包完成并测试通过")
                else:
                    print("⚠️ 目录模式打包完成但测试失败")
            else:
                print("❌ 目录模式打包失败")
        
        if choice not in ['1', '2', '3']:
            print("❌ 无效选择")
            return False
        
        # 总结
        print(f"\n{'='*50}")
        print(f"📊 打包结果: {success_count}/{total_count} 成功")
        
        if success_count > 0:
            print("\n🎉 打包完成！输出文件位置:")
            if choice in ['1', '3']:
                print(f"  📁 单文件: dist/Nmodm.exe")
            if choice in ['2', '3']:
                print(f"  📁 目录模式: dist/Nmodm/")
            
            print("\n💡 建议:")
            print("  - 在不同Windows系统上测试兼容性")
            print("  - 检查所有功能是否正常工作")
            print("  - 单文件模式适合分发，目录模式启动更快")
        
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
