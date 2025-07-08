#!/usr/bin/env python3
"""
依赖安装脚本
自动安装打包所需的所有依赖
"""

import sys
import subprocess
from pathlib import Path


def install_package(package_name: str) -> bool:
    """安装单个包"""
    try:
        print(f"📦 安装 {package_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return False


def check_package(package_name: str) -> bool:
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def main():
    """主函数"""
    print("🎯 Nmodm 打包依赖安装工具")
    print("=" * 50)
    
    # 基础依赖
    base_packages = [
        "PySide6",
        "requests", 
        "toml",
        "psutil",  # 用于测试脚本
    ]
    
    # 打包工具
    packaging_tools = [
        "pyinstaller",
        "nuitka",
        "imageio",  # Nuitka图标处理需要
    ]
    
    all_packages = base_packages + packaging_tools
    
    print("📋 需要安装的包:")
    for pkg in all_packages:
        print(f"  • {pkg}")
    
    print("\n🔍 检查已安装的包...")
    installed = []
    missing = []
    
    for pkg in all_packages:
        # 特殊处理包名映射
        check_name = pkg
        if pkg == "pyinstaller":
            check_name = "PyInstaller"
        elif pkg == "PySide6":
            check_name = "PySide6"
        
        if check_package(check_name):
            print(f"✅ {pkg} - 已安装")
            installed.append(pkg)
        else:
            print(f"❌ {pkg} - 未安装")
            missing.append(pkg)
    
    if not missing:
        print("\n🎉 所有依赖都已安装！")
        return True
    
    print(f"\n📦 需要安装 {len(missing)} 个包:")
    for pkg in missing:
        print(f"  • {pkg}")
    
    # 询问是否安装
    try:
        choice = input("\n是否现在安装缺失的包? (Y/n): ").strip().lower()
        if choice in ['', 'y', 'yes']:
            print("\n🚀 开始安装...")
            
            success_count = 0
            for pkg in missing:
                if install_package(pkg):
                    success_count += 1
                print()  # 空行分隔
            
            print(f"📊 安装结果: {success_count}/{len(missing)} 成功")
            
            if success_count == len(missing):
                print("🎉 所有依赖安装完成！")
                print("\n💡 现在可以运行打包脚本:")
                print("  python build_manager.py")
                return True
            else:
                print("⚠️ 部分依赖安装失败，请手动安装")
                failed = [pkg for i, pkg in enumerate(missing) if i >= success_count]
                print("失败的包:")
                for pkg in failed:
                    print(f"  pip install {pkg}")
                return False
        else:
            print("👋 取消安装")
            return False
            
    except KeyboardInterrupt:
        print("\n👋 用户取消安装")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
