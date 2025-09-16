#!/usr/bin/env python3
"""
构建目录清理脚本
解决打包时的目录权限问题
"""

import os
import sys
import shutil
import time
import subprocess
from pathlib import Path


def kill_processes_using_directory(directory_path: Path):
    """终止使用指定目录的进程"""
    try:
        if sys.platform == "win32":
            # Windows: 使用 handle.exe 或 lsof 等工具
            # 这里使用简单的方法，尝试终止可能的Python进程
            subprocess.run(["taskkill", "/f", "/im", "python.exe"],
                         capture_output=True, check=False,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            subprocess.run(["taskkill", "/f", "/im", "main.exe"],
                         capture_output=True, check=False,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            subprocess.run(["taskkill", "/f", "/im", "Nmodm.exe"],
                         capture_output=True, check=False,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            print("✅ 已尝试终止相关进程")
        else:
            # Linux/Mac: 使用 lsof
            result = subprocess.run(["lsof", "+D", str(directory_path)],
                                  capture_output=True, text=True, check=False,
                                  creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            if result.stdout:
                lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                pids = set()
                for line in lines:
                    parts = line.split()
                    if len(parts) > 1:
                        pids.add(parts[1])
                
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], check=False)
                print(f"✅ 已终止 {len(pids)} 个进程")
    except Exception as e:
        print(f"⚠️ 终止进程时出错: {e}")


def force_remove_directory(directory_path: Path, max_retries: int = 5):
    """强制删除目录"""
    for attempt in range(max_retries):
        try:
            if directory_path.exists():
                # 尝试修改权限
                if sys.platform == "win32":
                    subprocess.run(["attrib", "-R", str(directory_path / "*"), "/S"], 
                                 capture_output=True, check=False)
                
                # 删除目录
                shutil.rmtree(directory_path, ignore_errors=True)
                
                # 验证删除
                if not directory_path.exists():
                    print(f"✅ 成功删除目录: {directory_path}")
                    return True
                else:
                    print(f"⚠️ 第 {attempt + 1} 次删除尝试失败")
            else:
                print(f"✅ 目录不存在: {directory_path}")
                return True
                
        except Exception as e:
            print(f"❌ 第 {attempt + 1} 次删除失败: {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ 等待 2 秒后重试...")
            time.sleep(2)
    
    return False


def cleanup_build_directories():
    """清理构建目录"""
    print("🧹 开始清理构建目录...")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    
    # 需要清理的目录列表
    directories_to_clean = [
        project_root / "build",
        project_root / "dist", 
        project_root / "Builds" / "PyInstaller",
        project_root / "Builds" / "Nuitka",
        project_root / "__pycache__",
    ]
    
    # 查找所有 .spec 文件
    spec_files = list(project_root.glob("*.spec"))
    
    success_count = 0
    total_count = len(directories_to_clean)
    
    for directory in directories_to_clean:
        print(f"🗂️ 处理目录: {directory}")
        
        if directory.exists():
            # 终止使用该目录的进程
            kill_processes_using_directory(directory)
            
            # 强制删除目录
            if force_remove_directory(directory):
                success_count += 1
            else:
                print(f"❌ 无法删除目录: {directory}")
        else:
            print(f"✅ 目录不存在，跳过: {directory}")
            success_count += 1
        
        print()
    
    # 删除 .spec 文件
    print("🗂️ 清理 .spec 文件...")
    for spec_file in spec_files:
        try:
            spec_file.unlink()
            print(f"✅ 删除文件: {spec_file}")
        except Exception as e:
            print(f"❌ 删除文件失败: {spec_file} - {e}")
    
    print("=" * 50)
    print(f"📊 清理结果: {success_count}/{total_count} 个目录清理成功")
    
    if success_count == total_count:
        print("🎉 所有构建目录清理完成！")
        return True
    else:
        print("⚠️ 部分目录清理失败，请手动检查")
        return False


def cleanup_python_cache():
    """清理Python缓存"""
    print("🧹 清理Python缓存...")
    
    project_root = Path(__file__).parent
    
    # 查找所有 __pycache__ 目录
    pycache_dirs = list(project_root.rglob("__pycache__"))
    
    for pycache_dir in pycache_dirs:
        try:
            shutil.rmtree(pycache_dir, ignore_errors=True)
            print(f"✅ 删除缓存: {pycache_dir}")
        except Exception as e:
            print(f"❌ 删除缓存失败: {pycache_dir} - {e}")
    
    # 查找所有 .pyc 文件
    pyc_files = list(project_root.rglob("*.pyc"))
    
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            print(f"✅ 删除文件: {pyc_file}")
        except Exception as e:
            print(f"❌ 删除文件失败: {pyc_file} - {e}")
    
    print(f"🎉 Python缓存清理完成！")


def main():
    """主函数"""
    print("🎯 Nmodm 构建目录清理工具")
    print("=" * 50)
    
    try:
        # 清理构建目录
        build_success = cleanup_build_directories()
        
        # 清理Python缓存
        cleanup_python_cache()
        
        print("\n" + "=" * 50)
        if build_success:
            print("✅ 清理完成！现在可以重新尝试打包。")
            print("\n💡 建议使用以下命令重新打包:")
            print("   python build_manager.py")
        else:
            print("⚠️ 清理过程中遇到问题，请检查上述错误信息。")
            print("\n💡 如果问题持续存在，请尝试:")
            print("   1. 重启计算机")
            print("   2. 以管理员身份运行此脚本")
            print("   3. 手动删除 Builds 目录")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 清理过程中发生错误: {e}")


if __name__ == "__main__":
    main()
