"""
i18n模块
提供多语言翻译支持

主要功能：
- 翻译管理（TranslationManager）
- 可翻译Widget（TLabel, TButton）
- 便捷函数（t, set_language, get_language）

使用示例：
    # 方式1：使用全局翻译函数
    from src.i18n import t
    text = t('common.button.ok')
    
    # 方式2：使用可翻译Widget
    from src.i18n import TLabel, TButton
    label = TLabel("main_window.title")
    button = TButton("common.button.confirm")
    
    # 方式3：切换语言
    from src.i18n import set_language
    set_language('en_US')
"""

from .manager import (
    TranslationManager,
    t,
    set_language,
    get_language,
    get_available_languages
)

from .widgets import (
    TranslatableWidget,
    TLabel,
    TButton,
    translatable
)

from .language_switcher import (
    LanguageSwitcher,
    load_language_preference
)

__all__ = [
    # 核心类
    'TranslationManager',

    # 便捷函数
    't',
    'set_language',
    'get_language',
    'get_available_languages',

    # 可翻译Widget
    'TranslatableWidget',
    'TLabel',
    'TButton',
    'translatable',

    # 语言切换组件
    'LanguageSwitcher',
    'load_language_preference',
]

__version__ = '1.0.0'

