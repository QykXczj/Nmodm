"""
基础配置页面
游戏路径配置和破解功能管理
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QFileDialog, QFrame,
                               QGroupBox, QTextEdit)
from PySide6.QtCore import Qt, Signal
from .base_page import BasePage
from ...config.config_manager import ConfigManager


class ConfigSection(QGroupBox):
    """配置区域组件"""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
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


class ConfigPage(BasePage):
    """基础配置页面"""
    
    # 状态更新信号
    status_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__("基础配置", parent)
        self.config_manager = ConfigManager()
        self.setup_content()
        self.load_current_config()
    
    def setup_content(self):
        """设置页面内容"""
        # 页面描述
        desc_label = QLabel("配置游戏路径和管理破解文件")
        desc_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 14px;
                margin-bottom: 20px;
            }
        """)
        self.add_content(desc_label)

        # 通用状态显示区域
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #fab387;
                font-size: 13px;
                padding: 10px;
                background-color: #313244;
                border-radius: 6px;
                border: 1px solid #fab387;
                margin-bottom: 15px;
            }
        """)
        self.status_label.setVisible(False)
        self.add_content(self.status_label)

        # 游戏路径配置
        self.create_game_path_section()

        # 破解管理
        self.create_crack_section()

        self.add_stretch()
    
    def create_game_path_section(self):
        """创建游戏路径配置区域"""
        section = ConfigSection("游戏路径配置")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 说明文本
        info_label = QLabel("请选择 nightreign.exe 游戏文件的路径")
        info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(info_label)
        
        # 路径输入区域
        path_container = QWidget()
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(10)
        
        # 路径输入框
        self.game_path_input = QLineEdit()
        self.game_path_input.setPlaceholderText("请选择游戏文件路径...")
        self.game_path_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #64a8d8;
            }
        """)
        browse_btn.clicked.connect(self.browse_game_path)
        
        path_layout.addWidget(self.game_path_input)
        path_layout.addWidget(browse_btn)
        path_container.setLayout(path_layout)
        layout.addWidget(path_container)
        
        # 保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #94d3a2;
            }
            QPushButton:pressed {
                background-color: #82c3a3;
            }
        """)
        save_btn.clicked.connect(self.save_game_path)
        layout.addWidget(save_btn)
        
        # 状态显示
        self.path_status_label = QLabel()
        self.path_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.path_status_label)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def create_crack_section(self):
        """创建破解管理区域"""
        section = ConfigSection("破解文件管理")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 说明文本
        info_label = QLabel("管理OnlineFix破解文件的应用和移除")
        info_label.setStyleSheet("""
            QLabel {
                color: #6c7086;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(info_label)
        
        # 破解状态显示
        self.crack_status_label = QLabel()
        self.crack_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.crack_status_label)
        
        # 按钮区域
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        # 应用破解按钮
        self.apply_crack_btn = QPushButton("应用破解")
        self.apply_crack_btn.setFixedWidth(120)
        self.apply_crack_btn.setStyleSheet("""
            QPushButton {
                background-color: #f9e2af;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #f7d794;
            }
            QPushButton:pressed {
                background-color: #f5cc79;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.apply_crack_btn.clicked.connect(self.apply_crack)
        
        # 移除破解按钮
        self.remove_crack_btn = QPushButton("移除破解")
        self.remove_crack_btn.setFixedWidth(120)
        self.remove_crack_btn.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                border: none;
                border-radius: 6px;
                color: #1e1e2e;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #f17497;
            }
            QPushButton:pressed {
                background-color: #ef5d86;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.remove_crack_btn.clicked.connect(self.remove_crack)
        
        button_layout.addWidget(self.apply_crack_btn)
        button_layout.addWidget(self.remove_crack_btn)
        button_layout.addStretch()
        
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        # 破解文件列表
        files_label = QLabel("破解文件列表:")
        files_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
                margin-top: 15px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(files_label)
        
        self.files_display = QTextEdit()
        self.files_display.setFixedHeight(100)
        self.files_display.setReadOnly(True)
        self.files_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #bac2de;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                padding: 8px;
            }
        """)
        layout.addWidget(self.files_display)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def browse_game_path(self):
        """浏览游戏路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择游戏文件",
            "",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        
        if file_path:
            self.game_path_input.setText(file_path)
    
    def save_game_path(self):
        """保存游戏路径"""
        game_path = self.game_path_input.text().strip()

        if not game_path:
            self.show_status("请先选择游戏文件路径", "warning")
            return

        if not game_path.lower().endswith('nightreign.exe'):
            self.show_status("请选择 nightreign.exe 文件", "warning")
            return

        if not os.path.exists(game_path):
            self.show_status("选择的文件不存在", "warning")
            return

        if self.config_manager.set_game_path(game_path):
            self.show_status("游戏路径保存成功", "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status("保存游戏路径失败", "error")
    
    def apply_crack(self):
        """应用破解"""
        if not self.config_manager.validate_game_path():
            self.show_status("请先配置有效的游戏路径", "warning")
            return

        if self.config_manager.apply_crack():
            self.show_status("破解文件应用成功", "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status("应用破解失败", "error")
    
    def remove_crack(self):
        """移除破解"""
        if not self.config_manager.validate_game_path():
            self.show_status("请先配置有效的游戏路径", "warning")
            return

        # 直接执行移除操作，不需要确认对话框
        if self.config_manager.remove_crack():
            self.show_status("破解文件移除成功", "success")
            self.update_status_display()
            self.status_updated.emit()
        else:
            self.show_status("移除破解失败", "error")
    
    def load_current_config(self):
        """加载当前配置"""
        game_path = self.config_manager.get_game_path()
        if game_path:
            self.game_path_input.setText(game_path)
        
        self.update_status_display()
        self.load_crack_files_list()
    
    def update_status_display(self):
        """更新状态显示"""
        # 更新游戏路径状态
        if self.config_manager.validate_game_path():
            self.path_status_label.setText("✅ 游戏路径配置正确")
            self.path_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 12px; margin-top: 5px; }")
        else:
            self.path_status_label.setText("❌ 游戏路径无效或未配置")
            self.path_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 12px; margin-top: 5px; }")
        
        # 更新破解状态
        is_applied = self.config_manager.is_crack_applied()
        game_valid = self.config_manager.validate_game_path()
        
        if is_applied:
            self.crack_status_label.setText("✅ 破解已应用")
            self.crack_status_label.setStyleSheet("QLabel { color: #a6e3a1; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")
        else:
            self.crack_status_label.setText("❌ 破解未应用")
            self.crack_status_label.setStyleSheet("QLabel { color: #f38ba8; font-size: 14px; font-weight: bold; margin-bottom: 10px; }")
        
        # 更新按钮状态
        self.apply_crack_btn.setEnabled(game_valid and not is_applied)
        self.remove_crack_btn.setEnabled(game_valid and is_applied)
    
    def load_crack_files_list(self):
        """加载破解文件列表"""
        try:
            files = []
            for file_path in self.config_manager.onlinefix_dir.iterdir():
                if file_path.name != "gconfig.ini" and file_path.is_file():
                    files.append(file_path.name)
            
            if files:
                self.files_display.setText("\n".join(files))
            else:
                self.files_display.setText("未找到破解文件")
        except Exception as e:
            self.files_display.setText(f"读取文件列表失败: {e}")
    
    def show_status(self, message, status_type="info"):
        """显示状态信息"""
        if status_type == "success":
            color = "#a6e3a1"
            bg_color = "#1e1e2e"
        elif status_type == "warning":
            color = "#fab387"
            bg_color = "#313244"
        elif status_type == "error":
            color = "#f38ba8"
            bg_color = "#313244"
        else:  # info
            color = "#89b4fa"
            bg_color = "#313244"

        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                padding: 10px;
                background-color: {bg_color};
                border-radius: 6px;
                border: 1px solid {color};
                margin-bottom: 15px;
            }}
        """)
        self.status_label.setVisible(True)

        # 3秒后自动隐藏
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setVisible(False))
