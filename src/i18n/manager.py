"""
翻译管理器
提供多语言翻译支持的核心类
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable


class TranslationManager:
    """
    翻译管理器（单例模式）
    
    功能：
    - 加载和管理翻译文件
    - 提供翻译查询接口
    - 支持语言切换
    - 缓存机制
    - 观察者模式（通知UI更新）
    
    使用示例：
        tm = TranslationManager.instance()
        tm.set_locale('en_US')
        text = tm.translate('common.button.ok')
    """
    
    _instance: Optional['TranslationManager'] = None
    
    def __init__(self):
        """初始化翻译管理器"""
        self._current_locale = 'zh_CN'  # 当前语言
        self._fallback_locale = 'zh_CN'  # 回退语言
        self._translations: Dict[str, Dict[str, Any]] = {}  # 翻译缓存
        self._locale_dir = Path(__file__).parent / 'locales'  # 翻译文件目录
        self._observers: List[Callable] = []  # 语言切换观察者列表
        
        # 加载默认语言
        self.load_locale(self._current_locale)
    
    @classmethod
    def instance(cls) -> 'TranslationManager':
        """
        获取单例实例
        
        Returns:
            TranslationManager: 单例实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_locale(self, locale: str) -> bool:
        """
        加载指定语言的所有翻译文件
        
        Args:
            locale: 语言代码，如 'zh_CN', 'en_US'
        
        Returns:
            bool: 加载是否成功
        """
        locale_path = self._locale_dir / locale
        if not locale_path.exists():
            print(f"警告: 语言目录不存在: {locale_path}")
            return False
        
        translations = {}
        
        # 加载所有JSON文件
        for json_file in locale_path.glob('*.json'):
            module_name = json_file.stem
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    translations[module_name] = json.load(f)
            except Exception as e:
                print(f"警告: 加载翻译文件失败: {json_file}, 错误: {e}")
        
        if translations:
            self._translations[locale] = translations
            return True
        
        return False
    
    def set_locale(self, locale: str) -> bool:
        """
        切换语言

        Args:
            locale: 语言代码

        Returns:
            bool: 切换是否成功
        """
        # 如果语言未加载，先加载
        if locale not in self._translations:
            if not self.load_locale(locale):
                return False

        self._current_locale = locale

        # 通知所有观察者
        self._notify_observers()
        return True
    
    def get_current_locale(self) -> str:
        """
        获取当前语言
        
        Returns:
            str: 当前语言代码
        """
        return self._current_locale
    
    def get_available_locales(self) -> List[str]:
        """
        获取可用的语言列表
        
        Returns:
            List[str]: 可用语言代码列表
        """
        if not self._locale_dir.exists():
            return []
        return [d.name for d in self._locale_dir.iterdir() if d.is_dir()]
    
    def translate(self, key: str, locale: str = None, **params) -> str:
        """
        翻译函数
        
        Args:
            key: 翻译键，格式：'module.nested.key' 或 'module:nested.key'
            locale: 指定语言（可选，默认使用当前语言）
            **params: 参数化翻译的参数
        
        Returns:
            str: 翻译后的文本
        
        使用示例：
            t('common.button.ok')
            t('common.message.download_progress', percent=75)
        """
        if locale is None:
            locale = self._current_locale
        
        # 解析键
        parts = key.replace(':', '.').split('.')
        if len(parts) < 2:
            return f"[Missing: {key}]"
        
        module_name = parts[0]
        nested_keys = parts[1:]
        
        # 获取翻译
        translation = self._get_nested_value(
            self._translations.get(locale, {}),
            module_name,
            nested_keys
        )
        
        # 如果找不到，尝试回退语言
        if translation is None and locale != self._fallback_locale:
            translation = self._get_nested_value(
                self._translations.get(self._fallback_locale, {}),
                module_name,
                nested_keys
            )
        
        # 仍然找不到，返回缺失标记
        if translation is None:
            return f"[Missing: {key}]"
        
        # 参数化替换
        if params:
            translation = self._format_translation(translation, params)
        
        return translation
    
    def _get_nested_value(self, translations: dict, module: str, keys: list) -> Optional[str]:
        """
        获取嵌套的翻译值
        
        Args:
            translations: 翻译字典
            module: 模块名
            keys: 嵌套键列表
        
        Returns:
            Optional[str]: 翻译文本，如果不存在则返回None
        """
        if module not in translations:
            return None
        
        value = translations[module]
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def _format_translation(self, text: str, params: dict) -> str:
        """
        格式化翻译文本（替换参数）
        
        Args:
            text: 原始文本
            params: 参数字典
        
        Returns:
            str: 格式化后的文本
        """
        # 支持 {param} 格式
        for key, value in params.items():
            text = text.replace(f'{{{key}}}', str(value))
        return text
    
    def has_translation(self, key: str, locale: str = None) -> bool:
        """
        检查翻译是否存在
        
        Args:
            key: 翻译键
            locale: 语言代码（可选）
        
        Returns:
            bool: 翻译是否存在
        """
        if locale is None:
            locale = self._current_locale
        
        parts = key.replace(':', '.').split('.')
        if len(parts) < 2:
            return False
        
        module_name = parts[0]
        nested_keys = parts[1:]
        
        translation = self._get_nested_value(
            self._translations.get(locale, {}),
            module_name,
            nested_keys
        )
        
        return translation is not None
    
    def add_observer(self, callback: Callable):
        """
        添加语言切换观察者
        
        Args:
            callback: 回调函数，接收一个参数（新语言代码）
        """
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable):
        """
        移除语言切换观察者
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self):
        """通知所有观察者语言已切换"""
        print(f"\n🔔 通知观察者：语言已切换到 {self._current_locale}")
        print(f"📌 观察者数量: {len(self._observers)}")

        for i, callback in enumerate(self._observers):
            try:
                print(f"  ✅ 通知观察者 #{i+1}")
                callback(self._current_locale)
            except Exception as e:
                print(f"  ❌ 观察者 #{i+1} 回调失败: {e}")


# 全局便捷函数

def t(key: str, **params) -> str:
    """
    全局翻译函数
    
    Args:
        key: 翻译键
        **params: 参数化翻译的参数
    
    Returns:
        str: 翻译后的文本
    
    使用示例：
        t('common.button.ok')
        t('common.message.download_progress', percent=75)
        t('main_window.title')
    """
    return TranslationManager.instance().translate(key, **params)


def set_language(locale: str) -> bool:
    """
    设置语言

    Args:
        locale: 语言代码

    Returns:
        bool: 设置是否成功
    """
    return TranslationManager.instance().set_locale(locale)


def get_language() -> str:
    """
    获取当前语言
    
    Returns:
        str: 当前语言代码
    """
    return TranslationManager.instance().get_current_locale()


def get_available_languages() -> List[str]:
    """
    获取可用的语言列表
    
    Returns:
        List[str]: 可用语言代码列表
    """
    return TranslationManager.instance().get_available_locales()

