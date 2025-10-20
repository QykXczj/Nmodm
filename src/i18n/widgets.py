"""
可翻译的Qt Widget组件
提供自动响应语言切换的Widget类
"""
from PySide6.QtWidgets import QLabel, QPushButton, QWidget
from PySide6.QtCore import QObject

from .manager import TranslationManager, t


class TranslatableWidget:
    """
    可翻译Widget混入类
    
    功能：
    - 自动响应语言切换
    - 支持参数化翻译
    - 向后兼容普通文本
    
    使用示例：
        class MyLabel(QLabel, TranslatableWidget):
            def __init__(self, text="", parent=None):
                QLabel.__init__(self, parent)
                TranslatableWidget.__init__(self)
                self.set_translation(text)
    """
    
    def __init__(self):
        """初始化可翻译Widget"""
        super().__init__()
        self._translation_key = None
        self._translation_params = {}
        
        # 注册到翻译管理器
        TranslationManager.instance().add_observer(self._on_language_changed)
    
    def set_translation(self, key: str, **params):
        """
        设置翻译键
        
        Args:
            key: 翻译键
            **params: 参数化翻译的参数
        
        使用示例：
            label.set_translation('common.button.ok')
            label.set_translation('common.message.download_progress', percent=75)
        """
        self._translation_key = key
        self._translation_params = params
        self.update_translation()
    
    def update_translation(self):
        """更新翻译文本"""
        if self._translation_key:
            text = t(self._translation_key, **self._translation_params)
            if hasattr(self, 'setText'):
                self.setText(text)
    
    def _on_language_changed(self, locale: str):
        """
        语言切换回调

        Args:
            locale: 新的语言代码
        """
        if self._translation_key:
            print(f"    🔄 更新Widget翻译: {self._translation_key} → {locale}")
        self.update_translation()
    
    def __del__(self):
        """析构函数，移除观察者"""
        try:
            TranslationManager.instance().remove_observer(self._on_language_changed)
        except:
            pass


class TLabel(QLabel, TranslatableWidget):
    """
    可翻译的QLabel
    
    功能：
    - 自动判断是翻译键还是普通文本
    - 自动响应语言切换
    - 支持参数化翻译
    
    使用示例：
        # 使用翻译键
        title = TLabel("main_window.title")
        
        # 带参数的翻译
        progress = TLabel("common.message.download_progress", percent=75)
        
        # 普通文本（向后兼容）
        plain = TLabel("这是普通文本")
    """
    
    def __init__(self, text_or_key: str = "", parent=None, **params):
        """
        初始化TLabel
        
        Args:
            text_or_key: 翻译键或普通文本
            parent: 父Widget
            **params: 参数化翻译的参数
        """
        QLabel.__init__(self, parent)
        TranslatableWidget.__init__(self)
        
        # 判断是翻译键还是普通文本
        if self._is_translation_key(text_or_key):
            # 看起来像翻译键
            self.set_translation(text_or_key, **params)
        else:
            # 普通文本
            self.setText(text_or_key)
    
    def _is_translation_key(self, text: str) -> bool:
        """
        判断是否为翻译键
        
        Args:
            text: 文本
        
        Returns:
            bool: 是否为翻译键
        """
        # 简单的启发式判断：
        # 1. 包含点号（嵌套键）
        # 2. 不以 [ 开头（避免误判缺失标记）
        # 3. 不包含空格（翻译键通常不含空格）
        # 4. 不包含中文字符（翻译键通常是英文）
        if not text:
            return False
        
        if text.startswith('['):
            return False
        
        if ' ' in text:
            return False
        
        # 检查是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return False
        
        # 包含点号，可能是翻译键
        return '.' in text


class TButton(QPushButton, TranslatableWidget):
    """
    可翻译的QPushButton
    
    功能：
    - 自动判断是翻译键还是普通文本
    - 自动响应语言切换
    - 支持参数化翻译
    
    使用示例：
        # 使用翻译键
        ok_btn = TButton("common.button.ok")
        
        # 普通文本（向后兼容）
        custom_btn = TButton("自定义按钮")
    """
    
    def __init__(self, text_or_key: str = "", parent=None, **params):
        """
        初始化TButton
        
        Args:
            text_or_key: 翻译键或普通文本
            parent: 父Widget
            **params: 参数化翻译的参数
        """
        QPushButton.__init__(self, parent)
        TranslatableWidget.__init__(self)
        
        # 判断是翻译键还是普通文本
        if self._is_translation_key(text_or_key):
            # 看起来像翻译键
            self.set_translation(text_or_key, **params)
        else:
            # 普通文本
            self.setText(text_or_key)
    
    def _is_translation_key(self, text: str) -> bool:
        """
        判断是否为翻译键
        
        Args:
            text: 文本
        
        Returns:
            bool: 是否为翻译键
        """
        # 同TLabel的判断逻辑
        if not text:
            return False
        
        if text.startswith('['):
            return False
        
        if ' ' in text:
            return False
        
        # 检查是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return False
        
        # 包含点号，可能是翻译键
        return '.' in text


# 便捷的翻译装饰器（高级用法）

def translatable(widget_class):
    """
    使任何Widget类可翻译的装饰器
    
    Args:
        widget_class: 要装饰的Widget类
    
    Returns:
        type: 可翻译的Widget类
    
    使用示例：
        @translatable
        class MyCustomWidget(QWidget):
            pass
        
        # 现在MyCustomWidget支持翻译功能
        widget = MyCustomWidget()
        widget.set_translation('my_module.my_key')
    """
    class TranslatableVersion(widget_class, TranslatableWidget):
        def __init__(self, *args, **kwargs):
            widget_class.__init__(self, *args, **kwargs)
            TranslatableWidget.__init__(self)
    
    # 保留原类名
    TranslatableVersion.__name__ = widget_class.__name__
    TranslatableVersion.__qualname__ = widget_class.__qualname__
    
    return TranslatableVersion

