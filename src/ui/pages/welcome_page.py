"""
欢迎页面
展示软件介绍和相关链接
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QGridLayout, QSpacerItem, QSizePolicy, QApplication, QMessageBox)
from PySide6.QtCore import Qt, QUrl, Signal, QTimer
from PySide6.QtGui import QFont, QDesktopServices, QPixmap, QPainter, QColor, QCursor

from .base_page import BasePage
from src.i18n import TLabel, t, TranslationManager


class ClickableLabel(QLabel):
    """可点击的标签"""
    clicked = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class WelcomePage(BasePage):
    """欢迎页面"""
    
    def __init__(self, parent=None):
        super().__init__(t("welcome_page.page_title"), parent)

        # 保存组件引用
        self.feature_cards = []
        self.link_buttons = {}
        self.qq_number_label = None

        self.setup_content()

        # 注册语言切换观察者
        TranslationManager.instance().add_observer(self._on_language_changed)
    
    def setup_content(self):
        """设置页面内容"""
        # 主容器
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # 欢迎标题区域
        self.create_welcome_section(main_layout)

        # 功能介绍区域
        self.create_features_section(main_layout)

        # 链接区域
        self.create_links_section(main_layout)

        # 联系信息区域
        self.create_contact_section(main_layout)

        # 添加弹性空间
        main_layout.addStretch()

        # 添加到BasePage的布局中
        self.add_content(main_widget)
    
    def create_welcome_section(self, layout):
        """创建欢迎区域"""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setSpacing(8)

        # 主标题
        title_label = TLabel("welcome_page.title")
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 26px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(title_label)

        # 副标题
        subtitle_label = TLabel("welcome_page.subtitle")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(subtitle_label)

        layout.addWidget(welcome_widget)
    
    def create_features_section(self, layout):
        """创建功能介绍区域"""
        features_widget = QWidget()
        features_layout = QVBoxLayout(features_widget)
        features_layout.setSpacing(12)

        # 功能标题
        features_title = TLabel("welcome_page.section.features")
        features_title.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        features_layout.addWidget(features_title)

        # 功能网格
        features_grid = QGridLayout()
        features_grid.setSpacing(12)
        features_grid.setContentsMargins(0, 0, 0, 0)

        # 功能列表（使用翻译键）
        features = [
            ("🚀", "quick_launch"),
            ("⚙️", "config"),
            ("📥", "tools"),
            ("🔧", "mods"),
            ("🌐", "lan"),
            ("🌍", "virtual_lan"),
            ("📦", "misc")
        ]

        for i, (icon, feature_id) in enumerate(features):
            feature_widget = self.create_feature_card(icon, feature_id)
            row = i // 2
            col = i % 2
            features_grid.addWidget(feature_widget, row, col)

        features_layout.addLayout(features_grid)
        layout.addWidget(features_widget)
    
    def create_feature_card(self, icon, feature_id):
        """创建功能卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        card.setFixedHeight(60)
        card.setMinimumWidth(200)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: #89b4fa;
            }
        """)
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 文本区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        # 标题
        title_key = f"welcome_page.feature.{feature_id}.title"
        title_label = QLabel(t(title_key))
        title_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        text_layout.addWidget(title_label)

        # 描述
        desc_key = f"welcome_page.feature.{feature_id}.description"
        desc_label = QLabel(t(desc_key))
        desc_label.setStyleSheet("""
            QLabel {
                color: #bac2de;
                font-size: 11px;
            }
        """)
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        layout.addWidget(text_widget)

        # 保存组件引用
        self.feature_cards.append({
            'title_label': title_label,
            'desc_label': desc_label,
            'title_key': title_key,
            'desc_key': desc_key
        })

        return card
    
    def create_links_section(self, layout):
        """创建链接区域"""
        links_widget = QWidget()
        links_layout = QVBoxLayout(links_widget)
        links_layout.setSpacing(10)

        # 链接标题
        links_title = TLabel("welcome_page.section.links")
        links_title.setStyleSheet("""
            QLabel {
                color: #f9e2af;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        links_layout.addWidget(links_title)

        # 链接按钮容器
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        # 项目地址按钮
        github_btn = self.create_link_button(
            "welcome_page.link.github",
            "https://github.com/QykXczj/Nmodm",
            "#a6e3a1"
        )
        buttons_layout.addWidget(github_btn)
        self.link_buttons["welcome_page.link.github"] = github_btn

        # 视频教程按钮
        video_btn = self.create_link_button(
            "welcome_page.link.video",
            "https://www.bilibili.com/video/BV1LK3CztE54",
            "#f38ba8"
        )
        buttons_layout.addWidget(video_btn)
        self.link_buttons["welcome_page.link.video"] = video_btn

        # 最新Mods按钮
        mods_btn = self.create_link_button(
            "welcome_page.link.mods_package",
            "https://pan.quark.cn/s/7360b153d049",
            "#fab387"
        )
        buttons_layout.addWidget(mods_btn)
        self.link_buttons["welcome_page.link.mods_package"] = mods_btn

        links_layout.addLayout(buttons_layout)
        layout.addWidget(links_widget)
    
    def create_link_button(self, text_key, url, color):
        """创建链接按钮"""
        btn = QPushButton(t(text_key))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 110px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
        """)
        btn.clicked.connect(lambda checked=False: self.open_url(url))
        return btn
    
    def create_contact_section(self, layout):
        """创建联系信息区域"""
        contact_widget = QWidget()
        contact_layout = QHBoxLayout(contact_widget)
        contact_layout.setAlignment(Qt.AlignCenter)
        contact_layout.setSpacing(8)

        # QQ群标签
        qq_label = TLabel("welcome_page.contact.qq_group_label")
        qq_label.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        contact_layout.addWidget(qq_label)

        # QQ群号（可点击复制）
        qq_number = ClickableLabel("726070139")
        qq_number.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(137, 180, 250, 0.1);
                border: 1px solid rgba(137, 180, 250, 0.3);
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLabel:hover {
                background-color: rgba(137, 180, 250, 0.2);
                border-color: rgba(137, 180, 250, 0.5);
            }
        """)
        qq_number.setCursor(QCursor(Qt.PointingHandCursor))
        qq_number.setToolTip(t("welcome_page.contact.qq_group_tooltip"))
        qq_number.clicked.connect(lambda checked=False: self.copy_to_clipboard("726070139", t("welcome_page.contact.qq_group_label")))
        contact_layout.addWidget(qq_number)

        # 保存QQ群号标签引用
        self.qq_number_label = qq_number

        layout.addWidget(contact_widget)
    
    def open_url(self, url):
        """打开URL"""
        QDesktopServices.openUrl(QUrl(url))

    def copy_to_clipboard(self, text, description):
        """复制文本到剪切板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # 显示复制成功的提示消息
        self.show_copy_message(t("welcome_page.contact.qq_group_copied"))

    def show_copy_message(self, message):
        """显示复制成功的提示消息"""
        # 创建一个临时的提示标签
        if not hasattr(self, 'copy_message_label'):
            self.copy_message_label = QLabel(self)
            self.copy_message_label.setStyleSheet("""
                QLabel {
                    background-color: #a6e3a1;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            self.copy_message_label.setAlignment(Qt.AlignCenter)
            self.copy_message_label.hide()

        # 设置消息文本
        self.copy_message_label.setText(message)
        self.copy_message_label.adjustSize()

        # 计算位置（居中显示）
        parent_rect = self.rect()
        label_rect = self.copy_message_label.rect()
        x = (parent_rect.width() - label_rect.width()) // 2
        y = parent_rect.height() - 100  # 距离底部100px
        self.copy_message_label.move(x, y)

        # 显示提示
        self.copy_message_label.show()
        self.copy_message_label.raise_()  # 确保在最上层

        # 2秒后隐藏
        QTimer.singleShot(2000, self.copy_message_label.hide)

    def _on_language_changed(self, locale: str):
        """
        语言切换回调

        Args:
            locale: 新的语言代码
        """
        # 更新页面标题
        self.title_label.setText(t("welcome_page.page_title"))

        # 更新功能卡片
        for card_data in self.feature_cards:
            card_data['title_label'].setText(t(card_data['title_key']))
            card_data['desc_label'].setText(t(card_data['desc_key']))

        # 更新链接按钮
        for key, btn in self.link_buttons.items():
            btn.setText(t(key))

        # 更新QQ群提示
        if self.qq_number_label:
            self.qq_number_label.setToolTip(t("welcome_page.contact.qq_group_tooltip"))
