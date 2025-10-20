"""
语言切换组件
提供简洁的语言切换UI
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from .manager import TranslationManager


class LanguageSwitcher(QWidget):
    """
    语言切换组件
    
    功能：
    - 显示当前语言
    - 提供语言切换下拉框
    - 自动保存用户偏好
    - 发送语言切换信号
    
    使用示例：
        switcher = LanguageSwitcher()
        switcher.language_changed.connect(on_language_changed)
        layout.addWidget(switcher)
    """
    
    language_changed = Signal(str)  # 语言切换信号
    
    def __init__(self, parent=None, show_icon=True, compact=False):
        """
        初始化语言切换器
        
        Args:
            parent: 父Widget
            show_icon: 是否显示地球图标
            compact: 是否使用紧凑模式（适合标题栏）
        """
        super().__init__(parent)
        self.show_icon = show_icon
        self.compact = compact
        self.setup_ui()
        self.load_languages()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        
        if self.compact:
            # 紧凑模式（适合标题栏）
            layout.setContentsMargins(8, 0, 8, 0)
            layout.setSpacing(6)
        else:
            # 正常模式（适合侧边栏）
            layout.setContentsMargins(15, 8, 15, 8)
            layout.setSpacing(8)
        
        # 地球图标（可选）
        if self.show_icon:
            icon_label = QLabel("🌍")
            if self.compact:
                icon_label.setStyleSheet("""
                    QLabel {
                        color: #89b4fa;
                        font-size: 14px;
                    }
                """)
            else:
                icon_label.setStyleSheet("""
                    QLabel {
                        color: #89b4fa;
                        font-size: 16px;
                    }
                """)
            layout.addWidget(icon_label)
        
        # 语言下拉框
        self.language_combo = QComboBox()
        
        if self.compact:
            # 紧凑样式（适合标题栏）- 简化版，无下拉箭头
            self.language_combo.setStyleSheet("""
                QComboBox {
                    background-color: transparent;
                    border: 1px solid #313244;
                    border-radius: 2px;
                    padding: 4px 8px;
                    color: #cdd6f4;
                    font-size: 12px;
                    min-width: 70px;
                }
                QComboBox:hover {
                    border-color: #89b4fa;
                    background-color: rgba(137, 180, 250, 0.1);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 0px;
                }
                QComboBox::down-arrow {
                    image: none;
                    width: 0px;
                    height: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 2px;
                    selection-background-color: #89b4fa;
                    selection-color: #1e1e2e;
                    color: #cdd6f4;
                    padding: 4px;
                    outline: none;
                }
            """)
        else:
            # 正常样式（适合侧边栏）
            self.language_combo.setStyleSheet("""
                QComboBox {
                    background-color: transparent;
                    border: 1px solid #313244;
                    border-radius: 2px;
                    padding: 6px 10px;
                    color: #cdd6f4;
                    font-size: 13px;
                    min-width: 100px;
                }
                QComboBox:hover {
                    border-color: #89b4fa;
                    background-color: #313244;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #cdd6f4;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 2px;
                    selection-background-color: #89b4fa;
                    selection-color: #1e1e2e;
                    color: #cdd6f4;
                    padding: 4px;
                    outline: none;
                }
            """)
        
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        layout.addWidget(self.language_combo)
        
        self.setLayout(layout)
    
    def load_languages(self):
        """加载可用语言"""
        tm = TranslationManager.instance()

        # 语言映射（locale -> 显示名称）
        language_names = {
            'zh_CN': '简体中文',
            'zh_TW': '繁體中文',
            'en_US': 'English',
            'ja_JP': '日本語',
            'ko_KR': '한국어',
            'fr_FR': 'Français',
            'de_DE': 'Deutsch',
            'es_ES': 'Español',
            'ru_RU': 'Русский',
        }

        # 获取可用语言
        available_locales = tm.get_available_locales()

        # 临时断开信号，避免在初始化时触发语言切换
        self.language_combo.currentTextChanged.disconnect(self.on_language_changed)

        # 添加到下拉框
        for locale in available_locales:
            display_name = language_names.get(locale, locale)
            self.language_combo.addItem(display_name, locale)

        # 设置当前语言（不会触发信号）
        current_locale = tm.get_current_locale()
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_locale:
                self.language_combo.setCurrentIndex(i)
                break

        # 重新连接信号
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
    
    def on_language_changed(self, display_name):
        """
        语言切换处理

        Args:
            display_name: 显示名称
        """
        locale = self.language_combo.currentData()
        if locale:
            print(f"\n🌍 用户切换语言: {display_name} ({locale})")
            tm = TranslationManager.instance()
            if tm.set_locale(locale):
                # 发送信号
                self.language_changed.emit(locale)

                # 保存偏好
                self.save_language_preference(locale)

                print(f"✅ 语言已切换到: {display_name} ({locale})\n")
    
    def save_language_preference(self, locale: str):
        """
        保存语言偏好
        
        Args:
            locale: 语言代码
        """
        try:
            import json
            from pathlib import Path
            
            # 配置文件路径
            config_file = Path.home() / '.nmodm' / 'preferences.json'
            config_file.parent.mkdir(exist_ok=True)
            
            # 读取现有配置
            prefs = {}
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        prefs = json.load(f)
                except:
                    pass
            
            # 更新语言偏好
            prefs['language'] = locale
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"警告: 保存语言偏好失败: {e}")


def detect_system_language() -> str:
    """
    检测系统语言

    规则：
    - 中文系统 → zh_CN
    - 英语系统 → en_US
    - 其他语言 → en_US（默认英语）

    Returns:
        str: 语言代码
    """
    try:
        import locale
        import os

        # 方法1: 尝试从环境变量获取（Linux/macOS）
        lang_env = os.environ.get('LANG', '')
        if lang_env:
            if lang_env.lower().startswith('zh'):
                return 'zh_CN'
            if lang_env.lower().startswith('en'):
                return 'en_US'

        # 方法2: 使用locale.getdefaultlocale()
        system_lang, _ = locale.getdefaultlocale()

        if system_lang:
            system_lang_lower = system_lang.lower()

            # 检查是否为中文
            if system_lang_lower.startswith('zh'):
                return 'zh_CN'

            # 检查是否为英语
            if system_lang_lower.startswith('en'):
                return 'en_US'

        # 方法3: Windows特殊处理
        if os.name == 'nt':  # Windows
            try:
                import ctypes
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()

                # 中文语言ID
                # 0x0804 = 简体中文（中国）
                # 0x0404 = 繁体中文（台湾）
                # 0x0C04 = 繁体中文（香港）
                # 0x1004 = 繁体中文（新加坡）
                chinese_ids = [0x0804, 0x0404, 0x0C04, 0x1004]

                if lang_id in chinese_ids:
                    return 'zh_CN'

                # 英语语言ID
                # 0x0409 = 英语（美国）
                # 0x0809 = 英语（英国）
                english_ids = [0x0409, 0x0809]

                if lang_id in english_ids:
                    return 'en_US'

            except:
                pass

    except:
        pass

    # 其他语言默认使用英语
    return 'en_US'


def load_language_preference() -> str:
    """
    加载语言偏好

    优先级：
    1. 用户保存的偏好
    2. 系统语言

    Returns:
        str: 语言代码
    """
    try:
        import json
        from pathlib import Path

        config_file = Path.home() / '.nmodm' / 'preferences.json'

        # 1. 尝试读取用户保存的偏好
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    saved_lang = prefs.get('language')
                    if saved_lang:
                        return saved_lang
            except:
                pass

        # 2. 如果没有保存的偏好，检测系统语言
        return detect_system_language()

    except:
        # 发生异常时使用系统语言检测
        return detect_system_language()

