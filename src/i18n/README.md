# i18n 翻译框架

完整的多语言翻译支持框架，提供简单易用的API和自动语言切换功能。

## 📁 目录结构

```
src/i18n/
├── __init__.py              # 导出接口
├── manager.py               # TranslationManager核心类
├── widgets.py               # TLabel, TButton等可翻译Widget
├── README.md                # 本文档
└── locales/                 # 翻译文件目录
    └── zh_CN/               # 简体中文
        ├── common.json      # 通用文本
        ├── main_window.json # 主窗口
        ├── sidebar.json     # 侧边栏
        └── welcome_page.json # 欢迎页
```

## 🚀 快速开始

### 1. 基本使用

```python
# 导入翻译函数
from src.i18n import t

# 使用翻译
text = t('common.button.ok')  # "确定"
title = t('main_window.title')  # "Nmodm - 游戏管理工具"

# 参数化翻译
progress = t('common.message.download_progress', percent=75)  # "下载进度: 75%"
```

### 2. 使用可翻译Widget

```python
from src.i18n import TLabel, TButton

# 使用翻译键
title_label = TLabel("main_window.title")
ok_button = TButton("common.button.ok")

# 带参数的翻译
progress_label = TLabel("common.message.download_progress", percent=75)

# 普通文本（向后兼容）
plain_label = TLabel("这是普通文本")
```

### 3. 切换语言

```python
from src.i18n import set_language, get_language

# 获取当前语言
current = get_language()  # 'zh_CN'

# 切换语言
set_language('en_US')

# 所有使用TLabel、TButton的Widget会自动更新！
```

## 📝 翻译文件格式

翻译文件使用JSON格式，支持嵌套结构：

```json
{
  "button": {
    "ok": "确定",
    "cancel": "取消"
  },
  "message": {
    "download_progress": "下载进度: {percent}%"
  }
}
```

### 访问方式

```python
# 使用点号分隔的键
t('common.button.ok')  # "确定"
t('common.message.download_progress', percent=75)  # "下载进度: 75%"
```

## 🔧 高级用法

### 1. 手动设置翻译

```python
from src.i18n import TranslatableWidget
from PySide6.QtWidgets import QLabel

label = QLabel()
# 混入TranslatableWidget功能
# 注意：这种方式需要手动管理观察者
```

### 2. 自定义可翻译Widget

```python
from src.i18n import translatable
from PySide6.QtWidgets import QWidget

@translatable
class MyCustomWidget(QWidget):
    pass

# 现在MyCustomWidget支持翻译功能
widget = MyCustomWidget()
widget.set_translation('my_module.my_key')
```

### 3. 检查翻译是否存在

```python
from src.i18n import TranslationManager

tm = TranslationManager.instance()
if tm.has_translation('common.button.ok'):
    print("翻译存在")
```

## 🌍 添加新语言

### 1. 创建语言目录

```bash
mkdir -p src/i18n/locales/en_US
```

### 2. 复制翻译文件

```bash
cp src/i18n/locales/zh_CN/*.json src/i18n/locales/en_US/
```

### 3. 翻译文本

编辑 `en_US/*.json` 文件，将中文翻译为英文：

```json
{
  "button": {
    "ok": "OK",
    "cancel": "Cancel"
  }
}
```

### 4. 使用新语言

```python
from src.i18n import set_language

set_language('en_US')
```

## 📋 翻译文件组织建议

### 按模块分文件

- `common.json` - 通用文本（按钮、状态、消息等）
- `main_window.json` - 主窗口相关
- `sidebar.json` - 侧边栏相关
- `welcome_page.json` - 欢迎页相关
- `config_page.json` - 配置页相关
- ...

### 命名规范

- 使用小写字母和下划线
- 语义化命名
- 保持一致性

```json
{
  "button": {
    "confirm": "确认",
    "cancel": "取消"
  },
  "status": {
    "success": "成功",
    "error": "错误"
  }
}
```

## 🎯 迁移现有代码

### 步骤1：识别硬编码文本

```python
# 修改前
self.title_label = QLabel("Nmodm - 游戏管理工具")
```

### 步骤2：添加到翻译文件

```json
// main_window.json
{
  "title": "Nmodm - 游戏管理工具"
}
```

### 步骤3：使用翻译

```python
# 修改后
from src.i18n import TLabel

self.title_label = TLabel("main_window.title")
```

## ⚠️ 注意事项

### 1. 翻译键命名

- 使用英文小写字母和下划线
- 避免使用空格和特殊字符
- 保持语义化

### 2. 参数化翻译

- 使用 `{param}` 格式
- 参数名要有意义
- 避免过多参数

```json
{
  "message": {
    "download_progress": "下载进度: {percent}%",
    "file_info": "文件: {filename}, 大小: {size}"
  }
}
```

### 3. 向后兼容

TLabel和TButton会自动判断是翻译键还是普通文本：

```python
# 翻译键（包含点号，无空格，无中文）
label1 = TLabel("main_window.title")

# 普通文本（包含空格或中文）
label2 = TLabel("这是普通文本")
label3 = TLabel("Plain Text")
```

## 🛠️ 开发工具（待实现）

### 翻译提取工具

```bash
python -m src.i18n.tools.extract_translations
```

### 翻译验证工具

```bash
python -m src.i18n.tools.validate_translations
```

### 翻译统计工具

```bash
python -m src.i18n.tools.stats_translations
```

## 📚 API参考

### 全局函数

- `t(key, **params)` - 翻译函数
- `set_language(locale)` - 设置语言
- `get_language()` - 获取当前语言
- `get_available_languages()` - 获取可用语言列表

### 类

- `TranslationManager` - 翻译管理器（单例）
- `TranslatableWidget` - 可翻译Widget混入类
- `TLabel` - 可翻译的QLabel
- `TButton` - 可翻译的QPushButton

### 装饰器

- `@translatable` - 使任何Widget类可翻译

## 🎨 最佳实践

1. **集中管理翻译文本**
   - 所有文本都放在翻译文件中
   - 避免硬编码

2. **使用可翻译Widget**
   - 优先使用TLabel、TButton
   - 自动响应语言切换

3. **合理组织翻译文件**
   - 按模块分文件
   - 保持文件大小适中

4. **保持翻译一致性**
   - 统一术语
   - 统一风格

5. **测试多语言**
   - 切换语言测试
   - 检查UI布局

## 📄 许可证

本框架是Nmodm项目的一部分，遵循项目许可证。

