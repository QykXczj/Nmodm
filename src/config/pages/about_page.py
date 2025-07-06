"""
关于页面
应用程序信息和版权声明
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QGroupBox, QTextEdit)
from PySide6.QtCore import Qt
from .base_page import BasePage


class AboutPage(BasePage):
    """关于页面"""
    
    def __init__(self, parent=None):
        super().__init__("关于 Nmodm", parent)
        self.setup_content()
    
    def setup_content(self):
        """设置页面内容"""
        # 应用信息
        self.create_app_info()
        
        # 功能介绍
        self.create_features_info()
        
        # 版权信息
        self.create_copyright_info()
        
        self.add_stretch()
    
    def create_app_info(self):
        """创建应用信息区域"""
        section = QGroupBox("应用信息")
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
        
        # 应用名称和版本
        app_name = QLabel("Nmodm v1.0.1")
        app_name.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        
        # 副标题
        subtitle = QLabel("现代化游戏管理工具")
        subtitle.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 16px;
                margin-bottom: 15px;
            }
        """)
        
        # 描述
        description = QLabel(
            "基于PySide6开发的现代化GUI应用程序，专为游戏管理和模组配置而设计。"
            "采用无边框设计和现代化UI风格，提供直观易用的用户体验。"
        )
        description.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        description.setWordWrap(True)
        
        layout.addWidget(app_name)
        layout.addWidget(subtitle)
        layout.addWidget(description)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def create_features_info(self):
        """创建功能介绍区域"""
        section = QGroupBox("主要功能")
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
        
        features_text = QTextEdit()
        features_text.setFixedHeight(150)
        features_text.setReadOnly(True)
        features_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #bac2de;
                font-size: 13px;
                padding: 10px;
                line-height: 1.4;
            }
        """)
        
        features_content = """• 游戏路径配置和验证
• OnlineFix破解文件管理
• ME3工具自动下载和更新
• 多镜像源支持，解决网络访问问题
• 现代化无边框UI设计
• 模块化架构，易于扩展
• Mod配置管理（开发中）"""
        
        features_text.setText(features_content)
        layout.addWidget(features_text)
        
        section.setLayout(layout)
        self.add_content(section)
    
    def create_copyright_info(self):
        """创建版权信息区域"""
        section = QGroupBox("技术信息")
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
        
        tech_info = QTextEdit()
        tech_info.setFixedHeight(120)
        tech_info.setReadOnly(True)
        tech_info.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #bac2de;
                font-size: 12px;
                padding: 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        
        tech_content = """开发框架: PySide6 (Qt for Python)
UI风格: 参考PyDracula现代化设计
架构模式: 模块化设计
网络库: requests
文件处理: pathlib, zipfile
配置管理: 自定义ConfigManager

GitHub镜像源:
- gh-proxy.com
- ghproxy.net  
- ghfast.top"""
        
        tech_info.setText(tech_content)
        layout.addWidget(tech_info)
        
        section.setLayout(layout)
        self.add_content(section)
