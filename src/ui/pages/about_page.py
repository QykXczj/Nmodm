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
        app_name = QLabel("Nmodm v3.0.0")
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
        section = QGroupBox("v3.0.0 更新说明")
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

        update_content = """🎨 用户界面优化
• 功能介绍卡片简化，移除边框和悬停效果
• QQ群号可点击复制到剪切板，提供复制成功提示
• 界面更加简洁美观，减少视觉干扰

⚡ 性能大幅提升
• 彻底解决工具下载页面卡顿问题
• 状态检查和更新检查改为异步后台执行
• 页面切换立即响应，不再阻塞UI线程
• 网络请求失败不影响基本功能使用

🔧 技术架构改进
• 双线程架构：状态检查和更新检查分离
• 完善的错误处理和状态提示机制
• 修复EasyTier工具状态显示问题
• 改进线程管理和资源释放

✨ 用户体验提升
• 操作反馈更加及时明确
• 错误信息具体清晰，便于理解
• 不同状态用颜色区分，视觉层次清晰"""

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
