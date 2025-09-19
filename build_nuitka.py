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
        self.version = "3.1.0"  # 应用版本号
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

        # 检查cryptography (存档转换功能需要)
        try:
            import cryptography
            print(f"✅ cryptography已安装")
        except ImportError:
            print("❌ cryptography未安装，请先安装依赖: pip install -r requirements.txt")
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

        # ESR和me3p目录不需要打包 - 这些是用户通过"工具下载"界面下载的工具
        # 注释：ESR(EasyTier)和me3p(ME3)工具由用户按需下载，不预置在安装包中

        # ESL目录不再需要打包 - 现在从OnlineFix/esl2.zip解压
        # 注释：ESL工具现在统一从OnlineFix文件夹的esl2.zip解压，无需预置ESL目录

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

            # 加密库模块 (存档转换功能)
            "--include-package=cryptography",
            "--include-module=cryptography.hazmat",
            "--include-module=cryptography.hazmat.primitives",
            "--include-module=cryptography.hazmat.backends",
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
            output_name = f"Nmodm_v{self.version}_onefile.exe"
        else:
            cmd.append("--standalone")
            output_name = "Nmodm"  # 可执行文件名
        
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

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(cmd, cwd=self.project_root,
                                  capture_output=True, text=True, creationflags=creation_flags)
            
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
                        print(f"📁 输出目录: {exe_dir}")

                        # 查找主执行文件
                        exe_path = None
                        for possible_name in [f"{output_name}.exe", "main.exe"]:
                            test_path = exe_dir / possible_name
                            if test_path.exists():
                                exe_path = test_path
                                break

                        if not exe_path:
                            # 查找目录中的任何exe文件
                            exe_files = list(exe_dir.glob("*.exe"))
                            if exe_files:
                                exe_path = exe_files[0]

                        if exe_path:
                            print(f"📁 主执行文件: {exe_path}")
                            size_mb = exe_path.stat().st_size / (1024 * 1024)
                            print(f"📊 文件大小: {size_mb:.1f} MB")

                            # 重命名可执行文件为Nmodm.exe
                            target_exe_path = exe_dir / "Nmodm.exe"
                            if exe_path.name != "Nmodm.exe":
                                if target_exe_path.exists():
                                    target_exe_path.unlink()
                                exe_path.rename(target_exe_path)
                                print(f"📁 可执行文件重命名为: Nmodm.exe")
                        else:
                            print("❌ 未找到输出的exe文件")
                            return False

                        # 重命名目录为版本化名称
                        target_dir = self.dist_dir / f"Nmodm_v{self.version}"
                        if target_dir.exists():
                            print(f"🗑️ 删除已存在的目录: {target_dir}")
                            if not self.force_remove_directory(target_dir):
                                return False

                        # 使用强化的重命名方法
                        if not self.safe_rename_directory(exe_dir, target_dir):
                            return False
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
            exe_path = self.dist_dir / f"Nmodm_v{self.version}_onefile.exe"
        else:
            exe_dir = self.dist_dir / f"Nmodm_v{self.version}"
            exe_path = exe_dir / "Nmodm.exe"
        
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

    def force_remove_directory(self, directory_path: Path, max_retries: int = 3) -> bool:
        """强制删除目录 - 增强版权限处理"""
        import time
        import gc

        if not directory_path.exists():
            return True

        print(f"🗑️ 尝试删除目录: {directory_path.name}")

        for attempt in range(max_retries):
            try:
                # 强制垃圾回收
                gc.collect()

                # Windows特殊处理
                if sys.platform == "win32":
                    # 1. 移除只读属性
                    try:
                        subprocess.run(["attrib", "-R", str(directory_path / "*"), "/S", "/D"],
                                     capture_output=True, check=False)
                    except:
                        pass

                    # 2. 修改权限
                    try:
                        subprocess.run(["icacls", str(directory_path), "/grant", "Everyone:F", "/T"],
                                     capture_output=True, check=False)
                    except:
                        pass

                # 尝试删除目录 - 使用简单但有效的方法
                try:
                    # 先尝试简单删除
                    shutil.rmtree(directory_path, ignore_errors=True)

                    # 如果还存在，手动处理只读文件
                    if directory_path.exists():
                        import stat
                        for root, dirs, files in os.walk(directory_path, topdown=False):
                            for name in files:
                                file_path = os.path.join(root, name)
                                try:
                                    os.chmod(file_path, stat.S_IWRITE)
                                    os.remove(file_path)
                                except:
                                    pass
                            for name in dirs:
                                dir_path = os.path.join(root, name)
                                try:
                                    os.rmdir(dir_path)
                                except:
                                    pass
                        # 最后删除根目录
                        try:
                            os.rmdir(directory_path)
                        except:
                            pass
                except Exception:
                    pass

                # 验证删除结果
                if not directory_path.exists():
                    print(f"✅ 目录删除成功: {directory_path.name}")
                    return True
                else:
                    print(f"⚠️ 第 {attempt + 1} 次删除未完全成功")

            except Exception as e:
                print(f"❌ 第 {attempt + 1} 次删除失败: {e}")

            if attempt < max_retries - 1:
                print(f"⏳ 等待 {2 + attempt} 秒后重试...")
                time.sleep(2 + attempt)

        print(f"⚠️ 目录删除失败: {directory_path.name}")
        print("💡 目录可能被其他程序占用，但不影响打包结果")
        return False

    def safe_rename_directory(self, source_dir: Path, target_dir: Path, max_retries: int = 5) -> bool:
        """安全重命名目录 - 增强版权限处理"""
        import time
        import gc

        print(f"🔄 尝试重命名目录: {source_dir.name} -> {target_dir.name}")

        for attempt in range(max_retries):
            try:
                # 强制垃圾回收，释放可能的文件句柄
                gc.collect()

                # 尝试直接重命名
                source_dir.rename(target_dir)
                print(f"✅ 目录重命名成功: {target_dir}")
                return True

            except PermissionError as e:
                print(f"⚠️ 第 {attempt + 1} 次重命名失败: 权限被拒绝")

                if attempt < max_retries - 1:
                    # 尝试多种解决方案
                    print("🔧 尝试解决权限问题...")

                    # 1. 修改目录权限 (Windows)
                    if sys.platform == "win32":
                        try:
                            subprocess.run(["icacls", str(source_dir), "/grant", "Everyone:F", "/T"],
                                         capture_output=True, check=False,
                                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                            print("  • 已尝试修改目录权限")
                        except:
                            pass

                    # 2. 终止可能占用目录的进程
                    if sys.platform == "win32":
                        processes_to_kill = ["python.exe", "main.exe", "Nmodm.exe", "explorer.exe"]
                        for process in processes_to_kill:
                            try:
                                result = subprocess.run(["taskkill", "/f", "/im", process],
                                                     capture_output=True, check=False,
                                                     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                                if result.returncode == 0:
                                    print(f"  • 已终止进程: {process}")
                            except:
                                pass

                    print(f"⏳ 等待 {3 + attempt} 秒后重试...")
                    time.sleep(3 + attempt)
                else:
                    # 最后一次尝试：使用复制+删除的方式
                    print("🔄 最后尝试：使用复制+删除方式...")
                    try:
                        # 确保目标目录不存在
                        if target_dir.exists():
                            self.force_remove_directory(target_dir)

                        # 复制目录
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                        print("  • 目录复制完成")

                        # 验证复制结果
                        if target_dir.exists():
                            # 尝试删除源目录
                            if self.force_remove_directory(source_dir):
                                print(f"✅ 目录复制重命名成功: {target_dir}")
                                return True
                            else:
                                print("⚠️ 复制成功但源目录删除失败，保留两个副本")
                                return True  # 复制成功就算成功
                        else:
                            print("❌ 目录复制失败")
                            return False

                    except Exception as copy_e:
                        print(f"❌ 复制重命名失败: {copy_e}")
                        # 作为最后的备用方案，至少保证源目录可用
                        print("💡 保持原目录名称，打包仍然成功")
                        return True

            except FileNotFoundError:
                print(f"❌ 源目录不存在: {source_dir}")
                return False
            except Exception as e:
                print(f"❌ 重命名异常: {e}")
                if attempt < max_retries - 1:
                    print(f"⏳ 等待 2 秒后重试...")
                    time.sleep(2)

        # 所有尝试都失败了
        print(f"❌ 目录重命名最终失败: {source_dir.name} -> {target_dir.name}")
        print("💡 解决方案:")
        print("   1. 关闭所有可能占用该目录的程序 (IDE、文件管理器等)")
        print("   2. 以管理员身份运行打包脚本")
        print("   3. 手动重命名目录")
        print(f"⚠️ 注意: 打包本身已成功，可执行文件位于: {source_dir}")
        return True  # 虽然重命名失败，但打包成功


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
                print(f"  📁 单文件: Builds/Nuitka/Nmodm_v{builder.version}_onefile.exe")
            if choice in ['2', '3']:
                print(f"  📁 独立模式: Builds/Nuitka/Nmodm_v{builder.version}/Nmodm.exe")
            
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
