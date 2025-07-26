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
        app_name = QLabel("Nmodm v3.0.3")
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
        section = QGroupBox("v3.0.3 更新说明")
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

        update_content = """🚀 网络优化功能全面升级
• 网络优化配置完整集成到房间系统
• 房间配置文件现在包含网络优化选项
• 分享房间时自动包含网络优化设置
• 加入房间时自动继承网络优化配置

🔧 配置管理体系完善
• easytier_config.json 现在同步网络优化配置
• 程序重启时自动恢复网络优化设置
• 三层配置管理：全局配置、活动配置、房间配置
• 配置间智能同步，确保一致性

🛡️ 安全保护机制增强
• 网络运行时禁止切换到不同房间
• 删除当前房间时检查网络状态
• 智能提示用户先停止网络再操作
• 允许重新加载当前房间刷新配置

⚡ 网络优化自动提权
• WinIPBroadcast 直接使用管理员权限启动
• 网卡跃点优化自动请求管理员权限
• 简化权限处理逻辑，提高成功率
• 用户无需手动以管理员身份运行

✨ 用户体验优化
• 房间管理更加智能和安全
• 网络优化设置持久化保存
• 清晰的错误提示和操作建议
• 完整的配置继承和同步机制"""

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
