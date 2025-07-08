"""
BIN合并页面
regulation.bin文件合并功能
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QListWidget, QListWidgetItem,
                               QFileDialog, QProgressBar, QTextEdit, QGroupBox)
from PySide6.QtCore import Signal, QThread
from .base_page import BasePage


class BinMergeWorker(QThread):
    """BIN合并工作线程"""
    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str)  # 完成信号(成功, 消息)

    def __init__(self, bin_files: List[str], erm_dir: Path, mods_dir: Path):
        super().__init__()
        self.bin_files = bin_files
        self.erm_dir = erm_dir
        self.mods_dir = mods_dir
        self._is_cancelled = False

    def cancel(self):
        """取消合并"""
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return

            # 1. 准备文件夹
            mods_to_merge_dir = self.erm_dir / "ModsToMerge"
            merged_mods_dir = self.erm_dir / "MergedMods"

            if not mods_to_merge_dir.exists():
                self.finished.emit(False, "ModsToMerge文件夹不存在，请先下载并设置ERModsMerger")
                return

            self.progress.emit("正在清理ModsToMerge和MergedMods文件夹...")

            # 清空ModsToMerge文件夹
            for item in mods_to_merge_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            # 清空MergedMods文件夹
            if merged_mods_dir.exists():
                for item in merged_mods_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            if self._is_cancelled:
                return

            # 2. 创建rbin文件夹并复制bin文件
            self.progress.emit("正在准备bin文件...")
            for i, bin_file in enumerate(self.bin_files):
                if self._is_cancelled:
                    return

                rbin_folder = mods_to_merge_dir / f"rbin{i}"
                rbin_folder.mkdir(exist_ok=True)
                
                # 复制bin文件到rbin文件夹
                dest_file = rbin_folder / "regulation.bin"
                shutil.copy2(bin_file, dest_file)
                self.progress.emit(f"已复制 {Path(bin_file).name} 到 rbin{i}")

            if self._is_cancelled:
                return

            # 3. 执行ERModsMerger合并命令
            self.progress.emit("正在执行bin文件合并...")
            erm_exe = self.erm_dir / "ERModsMerger.exe"
            if not erm_exe.exists():
                self.finished.emit(False, "ERModsMerger.exe不存在，请先下载ERModsMerger")
                return

            # 使用start命令执行合并
            try:
                # 使用start命令启动ERModsMerger
                process = subprocess.Popen(
                    ["start", "/wait", str(erm_exe), "/merge"],
                    cwd=str(self.erm_dir),
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # 等待进程完成
                stdout, stderr = process.communicate(timeout=300)  # 5分钟超时

                if self._is_cancelled:
                    return

                if process.returncode != 0:
                    error_msg = stderr or "合并过程中发生未知错误"
                    self.finished.emit(False, f"合并失败: {error_msg}")
                    return

            except subprocess.TimeoutExpired:
                self.finished.emit(False, "合并超时，请检查bin文件是否有效")
                return

            # 4. 检查合并是否成功
            self.progress.emit("正在检查合并结果...")
            merged_mods_dir = self.erm_dir / "MergedMods"
            merged_regulation_bin = merged_mods_dir / "regulation.bin"

            if not merged_mods_dir.exists():
                self.finished.emit(False, "MergedMods文件夹不存在，合并失败")
                return

            if not merged_regulation_bin.exists():
                self.finished.emit(False, "MergedMods中未生成regulation.bin文件，合并失败")
                return

            self.progress.emit("✅ 检测到合并成功生成的regulation.bin文件")

            # 5. 复制MergedMods到Mods文件夹并重命名
            self.progress.emit("正在复制合并结果...")

            # 目标文件夹
            merged_bin_dir = self.mods_dir / "MergedBin"

            # 如果目标文件夹存在，先删除
            if merged_bin_dir.exists():
                shutil.rmtree(merged_bin_dir)

            # 复制MergedMods到Mods/MergedBin
            shutil.copytree(merged_mods_dir, merged_bin_dir)
            self.progress.emit("合并完成！已复制到Mods/MergedBin")

            if not self._is_cancelled:
                self.finished.emit(True, "BIN文件合并成功完成")

        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(False, f"合并过程中发生错误: {str(e)}")


class BinMergePage(BasePage):
    """BIN合并页面"""
    
    def __init__(self, parent=None):
        super().__init__("BIN合并", parent)
        self.bin_files = []
        self.merge_worker = None
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.erm_dir = self.root_dir / "ERM"
        self.mods_dir = self.root_dir / "Mods"
        self.setup_content()
    
    def setup_content(self):
        """设置页面内容"""
        # 使用水平布局
        main_container = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：文件选择和合并控制
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 文件选择区域
        file_section = self.create_file_selection_section()
        left_layout.addWidget(file_section)

        # 合并控制区域
        control_section = self.create_merge_control_section()
        left_layout.addWidget(control_section)

        left_layout.addStretch()
        left_widget.setLayout(left_layout)

        # 右侧：日志区域
        log_section = self.create_log_section()

        # 添加到主布局
        main_layout.addWidget(left_widget, 2)  # 左侧占2份
        main_layout.addWidget(log_section, 1)  # 右侧占1份

        main_container.setLayout(main_layout)
        self.add_content(main_container)

        self.add_stretch()
    
    def create_file_selection_section(self):
        """创建文件选择区域"""
        section = QGroupBox("选择regulation.bin文件")
        section.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 添加文件按钮
        self.add_files_btn = QPushButton("添加bin文件")
        self.add_files_btn.setFixedHeight(35)
        self.add_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
        """)
        self.add_files_btn.clicked.connect(self.add_bin_files)
        
        # 删除选中按钮
        self.remove_selected_btn = QPushButton("删除选中")
        self.remove_selected_btn.setFixedHeight(35)
        self.remove_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #fab387;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #f9c74f;
            }
            QPushButton:pressed {
                background-color: #f8961e;
            }
        """)
        self.remove_selected_btn.clicked.connect(self.remove_selected_files)

        # 清空列表按钮
        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.setFixedHeight(35)
        self.clear_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #d67a8a;
            }
        """)
        self.clear_files_btn.clicked.connect(self.clear_file_list)

        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.remove_selected_btn)
        button_layout.addWidget(self.clear_files_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #cdd6f4;
                font-size: 11px;
                padding: 8px;
                min-height: 350px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #313244;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
        """)
        layout.addWidget(self.file_list)
        
        section.setLayout(layout)
        return section

    def create_merge_control_section(self):
        """创建合并控制区域"""
        section = QGroupBox("合并控制")
        section.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 按钮区域
        button_layout = QHBoxLayout()

        # 开始合并按钮
        self.start_merge_btn = QPushButton("开始合并")
        self.start_merge_btn.setFixedHeight(40)
        self.start_merge_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 8px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c3a3;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.start_merge_btn.clicked.connect(self.start_merge)

        # 取消合并按钮
        self.cancel_merge_btn = QPushButton("取消合并")
        self.cancel_merge_btn.setFixedHeight(40)
        self.cancel_merge_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 8px;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
            QPushButton:pressed {
                background-color: #d67a8a;
            }
        """)
        self.cancel_merge_btn.clicked.connect(self.cancel_merge)
        self.cancel_merge_btn.setVisible(False)

        button_layout.addWidget(self.start_merge_btn)
        button_layout.addWidget(self.cancel_merge_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 12px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.status_label)

        section.setLayout(layout)
        return section

    def create_log_section(self):
        """创建日志区域"""
        section = QGroupBox("合并日志")
        section.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #89b4fa;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(300)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #cdd6f4;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setFixedHeight(30)
        clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c7086;
                border: none;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #7c7f93;
            }
        """)
        clear_log_btn.clicked.connect(self.clear_log)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(clear_log_btn)
        layout.addLayout(button_layout)

        section.setLayout(layout)
        return section

    def add_bin_files(self):
        """添加bin文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Regulation files (*.bin);;All files (*.*)")
        file_dialog.setWindowTitle("选择regulation.bin文件")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            added_count = 0
            duplicate_count = 0

            for file_path in selected_files:
                if file_path not in self.bin_files:
                    self.bin_files.append(file_path)
                    added_count += 1

                    # 添加到列表显示完整路径
                    display_text = f"{len(self.bin_files)}. {file_path}"
                    item = QListWidgetItem(display_text)
                    item.setToolTip(f"完整路径: {file_path}")
                    self.file_list.addItem(item)
                else:
                    duplicate_count += 1

            # 记录添加结果
            if added_count > 0:
                self.log(f"已添加 {added_count} 个bin文件")
            if duplicate_count > 0:
                self.log(f"跳过 {duplicate_count} 个重复文件")

            self.update_merge_button_state()

    def remove_selected_files(self):
        """删除选中的文件"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            self.log("请先选择要删除的文件")
            return

        removed_count = 0
        for item in selected_items:
            row = self.file_list.row(item)
            if 0 <= row < len(self.bin_files):
                removed_file = self.bin_files.pop(row)
                self.file_list.takeItem(row)
                removed_count += 1
                self.log(f"已删除: {Path(removed_file).name}")

        # 重新编号列表项
        self.refresh_file_list()

        if removed_count > 0:
            self.log(f"共删除 {removed_count} 个文件")

        self.update_merge_button_state()

    def clear_file_list(self):
        """清空文件列表"""
        if self.bin_files:
            self.bin_files.clear()
            self.file_list.clear()
            self.log("已清空文件列表")
            self.update_merge_button_state()

    def refresh_file_list(self):
        """刷新文件列表显示"""
        self.file_list.clear()
        for i, file_path in enumerate(self.bin_files):
            display_text = f"{i + 1}. {file_path}"
            item = QListWidgetItem(display_text)
            item.setToolTip(f"完整路径: {file_path}")
            self.file_list.addItem(item)

    def update_merge_button_state(self):
        """更新合并按钮状态"""
        has_files = len(self.bin_files) > 0
        erm_exists = (self.erm_dir / "ERModsMerger.exe").exists()

        self.start_merge_btn.setEnabled(has_files and erm_exists)

        if not erm_exists:
            self.status_label.setText("请先下载并设置ERModsMerger")
        elif not has_files:
            self.status_label.setText("请选择要合并的bin文件")
        else:
            self.status_label.setText(f"已选择 {len(self.bin_files)} 个bin文件，可以开始合并")

    def start_merge(self):
        """开始合并"""
        if not self.bin_files:
            self.log("❌ 错误：请先选择要合并的bin文件")
            return

        if not (self.erm_dir / "ERModsMerger.exe").exists():
            self.log("❌ 错误：ERModsMerger.exe不存在，请先下载ERModsMerger")
            return

        # 直接开始合并，不弹窗确认
        self.log(f"准备合并 {len(self.bin_files)} 个bin文件")
        self.log("合并结果将保存到Mods/MergedBin文件夹")

        # 检查并修正config.json配置
        if not self.check_and_fix_config():
            self.log("❌ 配置文件检查失败，无法继续合并")
            return

        # 开始合并
        self.log("开始BIN文件合并...")
        self.merge_worker = BinMergeWorker(self.bin_files, self.erm_dir, self.mods_dir)
        self.merge_worker.progress.connect(self.log)
        self.merge_worker.finished.connect(self.merge_finished)

        # 更新UI状态
        self.start_merge_btn.setVisible(False)
        self.cancel_merge_btn.setVisible(True)
        self.add_files_btn.setEnabled(False)
        self.clear_files_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在合并...")

        self.merge_worker.start()

    def cancel_merge(self):
        """取消合并"""
        if self.merge_worker and self.merge_worker.isRunning():
            self.merge_worker.cancel()
            self.log("用户取消了合并操作")
            self.reset_merge_ui()

    def reset_merge_ui(self):
        """重置合并UI状态"""
        self.start_merge_btn.setVisible(True)
        self.cancel_merge_btn.setVisible(False)
        self.add_files_btn.setEnabled(True)
        self.clear_files_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.update_merge_button_state()

    def merge_finished(self, success, message):
        """合并完成"""
        self.reset_merge_ui()

        if success:
            self.log(f"✅ {message}")
            self.status_label.setText("合并完成！")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #a6e3a1;
                    font-size: 12px;
                    margin-top: 5px;
                    font-weight: bold;
                }
            """)
            # 不显示弹窗，信息已在日志中显示
        else:
            self.log(f"❌ {message}")
            self.status_label.setText("合并失败")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #f38ba8;
                    font-size: 12px;
                    margin-top: 5px;
                    font-weight: bold;
                }
            """)
            # 不显示弹窗，错误信息已在日志中显示

    def log(self, message):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()



    def check_and_fix_config(self):
        """检查并修正config.json配置"""
        config_file = self.erm_dir / "ERModsMergerConfig" / "config.json"

        if not config_file.exists():
            self.log("❌ config.json文件不存在")
            return False

        try:
            import json

            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.log("正在检查config.json配置...")

            # 检查和修正路径配置
            config_modified = False

            # 检查CurrentProfile
            if 'CurrentProfile' in config:
                current_profile = config['CurrentProfile']

                # 检查ModsToMergeFolderPath
                if current_profile.get('ModsToMergeFolderPath') != 'ModsToMerge':
                    self.log(f"修正ModsToMergeFolderPath: {current_profile.get('ModsToMergeFolderPath')} → ModsToMerge")
                    current_profile['ModsToMergeFolderPath'] = 'ModsToMerge'
                    config_modified = True

                # 检查MergedModsFolderPath
                if current_profile.get('MergedModsFolderPath') != 'MergedMods':
                    self.log(f"修正MergedModsFolderPath: {current_profile.get('MergedModsFolderPath')} → MergedMods")
                    current_profile['MergedModsFolderPath'] = 'MergedMods'
                    config_modified = True

            # 检查Profiles数组
            if 'Profiles' in config:
                for i, profile in enumerate(config['Profiles']):
                    # 检查ModsToMergeFolderPath
                    if profile.get('ModsToMergeFolderPath') != 'ModsToMerge':
                        self.log(f"修正Profiles[{i}].ModsToMergeFolderPath: {profile.get('ModsToMergeFolderPath')} → ModsToMerge")
                        profile['ModsToMergeFolderPath'] = 'ModsToMerge'
                        config_modified = True

                    # 检查MergedModsFolderPath
                    if profile.get('MergedModsFolderPath') != 'MergedMods':
                        self.log(f"修正Profiles[{i}].MergedModsFolderPath: {profile.get('MergedModsFolderPath')} → MergedMods")
                        profile['MergedModsFolderPath'] = 'MergedMods'
                        config_modified = True

            # 如果配置被修改，保存文件
            if config_modified:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self.log("✅ config.json配置已修正并保存")
            else:
                self.log("✅ config.json配置路径正确")

            return True

        except Exception as e:
            self.log(f"❌ 检查config.json配置失败: {str(e)}")
            return False

    def showEvent(self, event):
        """页面显示时检查状态"""
        super().showEvent(event)
        self.update_merge_button_state()
