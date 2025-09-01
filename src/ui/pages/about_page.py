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
        
        # 更新说明
        self.create_update_info()
        
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
        app_name = QLabel("Nmodm v3.0.8")
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
    
    def create_update_info(self):
        """创建更新说明区域"""
        section = QGroupBox("v3.0.8 更新说明")
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
                color: #a6e3a1;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        update_text = QTextEdit()
        update_text.setFixedHeight(200)
        update_text.setReadOnly(True)
        update_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #bac2de;
                font-size: 13px;
                padding: 12px;
                line-height: 1.5;
            }
        """)

        update_content = """🔧 破解功能重要修复
• 修复应用破解时复制多余文件的问题
• 改为白名单模式，只复制必需的4个破解文件
• 不再意外复制OnlineFix.zip和标志文件
• 破解应用和移除逻辑完全一致

✅ 精确破解文件管理
• OnlineFix.ini - 破解配置文件
• OnlineFix64.dll - 主破解DLL
• dlllist.txt - DLL列表文件
• winmm.dll - Windows多媒体API钩子

🎯 技术改进
• 白名单模式更安全可靠
• 避免复制工具包和压缩文件
• 完善的文件验证机制
• 统一的错误处理和日志输出

🚀 网络优化功能（v3.0.6继承）
• 网络优化配置完整集成到房间系统
• 三层配置管理体系完善
• 安全保护机制和自动提权
• 智能的用户体验优化"""

        update_text.setText(update_content)
        layout.addWidget(update_text)

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
