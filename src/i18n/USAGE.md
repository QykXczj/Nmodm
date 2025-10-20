# 语言切换UI组件使用指南

## 📦 已实现的组件

### 1. LanguageSwitcher - 语言切换器

位置：`src/i18n/language_switcher.py`

**功能**：
- ✅ 显示当前语言
- ✅ 提供语言切换下拉框
- ✅ 自动保存用户偏好到 `~/.nmodm/preferences.json`
- ✅ 发送语言切换信号
- ✅ 支持紧凑模式（适合标题栏）和正常模式（适合侧边栏）

**已集成位置**：
- ✅ 主窗口标题栏（紧凑模式）

## 🚀 使用方法

### 在标题栏中使用（已实现）

```python
from src.i18n.language_switcher import LanguageSwitcher

# 创建紧凑模式的语言切换器（适合标题栏）
self.language_switcher = LanguageSwitcher(self, show_icon=True, compact=True)
self.language_switcher.language_changed.connect(self.on_language_changed)

# 添加到布局
layout.addWidget(self.language_switcher)
```

### 在侧边栏中使用（可选）

```python
from src.i18n.language_switcher import LanguageSwitcher

# 创建正常模式的语言切换器（适合侧边栏）
self.language_switcher = LanguageSwitcher(self, show_icon=True, compact=False)
self.language_switcher.language_changed.connect(self.on_language_changed)

# 添加到布局
layout.addWidget(self.language_switcher)
```

### 在应用启动时加载语言偏好

在 `main.py` 或应用入口处添加：

```python
from src.i18n import set_language
from src.i18n.language_switcher import load_language_preference

# 加载用户保存的语言偏好
preferred_language = load_language_preference()
set_language(preferred_language)
```

## 📝 完整示例

### 应用启动流程

```python
# main.py
from PySide6.QtWidgets import QApplication
import sys

from src.i18n import set_language
from src.i18n.language_switcher import load_language_preference
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 1. 加载语言偏好（在创建UI之前）
    preferred_language = load_language_preference()
    set_language(preferred_language)
    
    # 2. 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

### 语言切换回调

```python
def on_language_changed(self, locale: str):
    """
    语言切换回调
    
    Args:
        locale: 新的语言代码（如 'zh_CN', 'en_US'）
    """
    print(f"语言已切换到: {locale}")
    
    # 可以在这里添加额外的处理
    # 例如：
    # - 更新窗口标题
    # - 刷新某些特殊的UI元素
    # - 记录日志
    # - 等等
```

## 🎨 样式说明

### 紧凑模式（compact=True）

适合标题栏等空间有限的地方：
- 较小的字体（12px）
- 较小的内边距（4px 8px）
- 最小宽度 80px
- 较小的图标（14px）

### 正常模式（compact=False）

适合侧边栏等空间充足的地方：
- 正常字体（13px）
- 正常内边距（6px 10px）
- 最小宽度 100px
- 正常图标（16px）

## 🌍 支持的语言

当前框架支持以下语言（需要创建对应的翻译文件）：

| 语言代码 | 显示名称 | 状态 |
|---------|---------|------|
| zh_CN   | 简体中文 | ✅ 已实现 |
| zh_TW   | 繁體中文 | ⏳ 待添加 |
| en_US   | English  | ⏳ 待添加 |
| ja_JP   | 日本語   | ⏳ 待添加 |
| ko_KR   | 한국어   | ⏳ 待添加 |
| fr_FR   | Français | ⏳ 待添加 |
| de_DE   | Deutsch  | ⏳ 待添加 |
| es_ES   | Español  | ⏳ 待添加 |
| ru_RU   | Русский  | ⏳ 待添加 |

## 📂 用户偏好保存位置

语言偏好保存在：
```
~/.nmodm/preferences.json
```

文件格式：
```json
{
  "language": "zh_CN"
}
```

## 🔧 自定义语言映射

如果需要添加新语言，编辑 `src/i18n/language_switcher.py`：

```python
language_names = {
    'zh_CN': '简体中文',
    'zh_TW': '繁體中文',
    'en_US': 'English',
    # 添加新语言
    'pt_BR': 'Português (Brasil)',
    'it_IT': 'Italiano',
}
```

## ⚠️ 注意事项

1. **语言切换器会自动检测可用语言**
   - 只显示 `src/i18n/locales/` 目录下存在的语言
   - 如果只有 `zh_CN`，下拉框只会显示简体中文

2. **语言偏好自动保存**
   - 用户切换语言后自动保存到配置文件
   - 下次启动时自动加载

3. **所有TLabel和TButton会自动更新**
   - 使用翻译键的Widget会自动响应语言切换
   - 无需手动刷新

4. **建议在应用启动时加载偏好**
   - 在创建UI之前调用 `load_language_preference()`
   - 确保UI创建时就使用正确的语言

## 🎯 下一步

### 可选的增强功能

1. **添加更多语言**
   - 创建 `en_US`, `ja_JP` 等翻译文件
   - 翻译所有文本

2. **在设置页面添加语言选项**
   - 提供更详细的语言设置
   - 显示语言完成度

3. **首次启动语言选择**
   - 检测系统语言
   - 提供语言选择对话框

4. **语言包管理**
   - 在线下载语言包
   - 社区贡献翻译

## 📚 相关文档

- [翻译框架README](./README.md) - 核心框架文档
- [API参考](./README.md#api参考) - 详细API说明
- [最佳实践](./README.md#最佳实践) - 使用建议

