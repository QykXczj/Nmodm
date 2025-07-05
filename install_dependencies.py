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
    build_packages = [
        "pyinstaller",
        "nuitka",
    ]
    
    # 检查基础依赖
    print("\n🔍 检查基础依赖...")
    missing_base = []
    for package in base_packages:
        if check_package(package):
            print(f"✅ {package}: 已安装")
        else:
            print(f"❌ {package}: 未安装")
            missing_base.append(package)
    
    # 检查打包工具
    print("\n🔍 检查打包工具...")
    missing_build = []
    for package in build_packages:
        if check_package(package):
            print(f"✅ {package}: 已安装")
        else:
            print(f"❌ {package}: 未安装")
            missing_build.append(package)
    
    # 安装缺失的依赖
    all_missing = missing_base + missing_build
    
    if not all_missing:
        print("\n🎉 所有依赖都已安装！")
        return
    
    print(f"\n📋 需要安装 {len(all_missing)} 个包:")
    for package in all_missing:
        print(f"  - {package}")
    
    # 询问用户是否安装
    response = input("\n是否现在安装这些依赖? (y/n): ").lower().strip()
    if response not in ['y', 'yes', '是']:
        print("👋 安装已取消")
        return
    
    # 升级pip
    print("\n🔧 升级 pip...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        print("✅ pip 升级成功")
    except subprocess.CalledProcessError:
        print("⚠️ pip 升级失败，继续安装依赖...")
    
    # 安装依赖
    print("\n📦 开始安装依赖...")
    success_count = 0
    
    for package in all_missing:
        if install_package(package):
            success_count += 1
    
    # 总结
    print(f"\n📊 安装完成:")
    print(f"✅ 成功: {success_count}/{len(all_missing)}")
    print(f"❌ 失败: {len(all_missing) - success_count}/{len(all_missing)}")
    
    if success_count == len(all_missing):
        print("\n🎉 所有依赖安装成功！")
        print("现在可以运行以下命令:")
        print("  python main.py              # 运行应用")
        print("  python build_manager.py     # 打包应用")
    else:
        print("\n⚠️ 部分依赖安装失败，请检查错误信息")


if __name__ == "__main__":
    main()