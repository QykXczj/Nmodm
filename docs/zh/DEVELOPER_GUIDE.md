# Nmodm 开发者指南

[返回主页](../../README.md) | [English](../en/DEVELOPER_GUIDE.md)

## 目录

- [开发环境搭建](#开发环境搭建)
- [项目架构深度解析](#项目架构深度解析)
- [核心组件详解](#核心组件详解)
- [开发规范](#开发规范)
- [构建与打包](#构建与打包)
- [调试与测试](#调试与测试)
- [常见开发任务](#常见开发任务)

---

## 开发环境搭建

### 环境要求

- **Python**: 3.8+ (推荐 3.11)
- **pip**: 最新版本
- **Git**: 用于版本控制
- **IDE**: VS Code 或 PyCharm（推荐）
- **操作系统**: Windows 10/11 (64-bit)

### 克隆项目

```bash
git clone https://github.com/your-repo/Nmodm.git
cd Nmodm
```

### 创建虚拟环境

**Windows**:
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac** (实验性支持):
```bash
python -m venv .venv
source .venv/bin/activate
```

### 安装依赖

```bash
# 核心依赖
pip install -r requirements.txt

# 开发工具（可选）
pip install black flake8 mypy pytest
```

### 验证安装

```bash
# 检查Python版本
python --version

# 验证核心模块导入
python -c "from src.app import NmodmApp; print('✓ 核心模块正常')"

# 验证PySide6
python -c "from PySide6.QtWidgets import QApplication; print('✓ PySide6正常')"
```

### 运行程序

```bash
# 开发模式运行
python main.py

# 查看详细日志（如果需要）
python main.py --verbose
```

### IDE 配置建议

**VS Code**:
```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black"
}
```

**PyCharm**:
- 设置项目解释器为 `.venv/Scripts/python.exe`
- 启用 PEP 8 代码检查
- 配置 Black 作为代码格式化工具

---

## 项目架构深度解析

### 整体架构模式

Nmodm 采用 **MVC + 单例 + 观察者** 混合架构模式：

- **Model**: 配置管理器（`src/config/`）
- **View**: UI 组件（`src/ui/`）
- **Controller**: 应用控制器（`src/app.py`）+ 工具管理器（`src/utils/`）

### 完整目录结构

```
Nmodm/
├── main.py                      # 应用入口点
├── src/                         # 源代码根目录
│   ├── app.py                   # 主应用类 (NmodmApp)
│   ├── version.json             # 版本信息
│   ├── config/                  # 配置管理层
│   │   ├── config_manager.py   # 游戏路径、破解管理
│   │   ├── mod_config_manager.py
│   │   └── network_optimization_config.py
│   ├── ui/                      # 用户界面层
│   │   ├── main_window.py      # 主窗口 + 自定义标题栏
│   │   ├── sidebar.py          # 侧边栏导航
│   │   ├── components/         # 可复用UI组件
│   │   │   ├── dialogs.py      # 现代化对话框
│   │   │   ├── notification_dialog.py
│   │   │   └── ...
│   │   └── pages/              # 功能页面（懒加载）
│   │       ├── base_page.py    # 页面基类
│   │       ├── welcome_page.py
│   │       ├── quick_launch_page.py  # 最复杂页面 (2764行)
│   │       ├── config_page.py
│   │       ├── me3_page.py
│   │       ├── mods_page.py
│   │       ├── lan_gaming_page.py
│   │       ├── virtual_lan_page.py
│   │       └── misc_page.py
│   ├── utils/                   # 工具模块层
│   │   ├── download_manager.py # 多线程下载管理
│   │   ├── easytier_manager.py # 虚拟局域网管理
│   │   ├── tool_manager.py     # 外部工具管理
│   │   ├── dll_manager.py      # DLL隔离技术
│   │   ├── network_optimizer.py
│   │   ├── lan_mode_detector.py
│   │   └── version_loader.py
│   └── i18n/                    # 国际化支持
│       ├── manager.py          # 翻译管理器
│       └── locales/            # 语言文件
├── OnlineFix/                   # 在线修复文件（运行时下载）
├── ESR/                         # EasyTier 配置和可执行文件
├── ESL/                         # ESL 局域网工具
├── me3p/                        # ME3 工具（便携版）
├── Mods/                        # 用户 Mod 目录
├── Builds/                      # 构建输出目录
│   ├── Nuitka/
│   └── PyInstaller/
├── tests/                       # 测试文件
├── docs/                        # 项目文档
├── .serena/                     # Serena AI 记忆
├── .kiro/                       # Kiro 配置
├── build_nuitka.py             # Nuitka 打包脚本
├── build_pyinstaller.py        # PyInstaller 打包脚本
├── build_manager.py            # 统一构建管理器
├── requirements.txt            # Python 依赖
└── README.md                   # 项目说明
```

### 核心架构组件

#### 1. 应用程序入口 - NmodmApp 类

**文件**: `src/app.py`  
**设计模式**: 单例 + 延迟初始化

```python
class NmodmApp:
    """主应用程序类 - 应用生命周期管理"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        # 延迟初始化策略（性能优化）
        self.config_manager = None
        self.download_manager = None
        self._pages_cache = {}  # 页面缓存机制
        
        # 创建主窗口
        self.main_window = MainWindow(app_instance=self)
        
        # 延迟初始化非关键组件
        QTimer.singleShot(100, self.delayed_initialization)
```

**核心特性**:
- **延迟初始化**: 非关键组件延迟 100ms 加载，启动速度 < 3秒
- **页面缓存**: 避免重复创建 UI 组件，优化内存使用
- **局域网检测**: 自动检测并适配局域网环境
- **异步初始化**: 使用 QTimer 实现非阻塞初始化

#### 2. 主窗口架构 - MainWindow + TitleBar

**文件**: `src/ui/main_window.py`

**TitleBar 类** - 自定义标题栏:
```python
class TitleBar(QWidget):
    """自定义标题栏 - 无边框窗口控制"""
    
    # 信号定义（观察者模式）
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
```

**技术亮点**:
- **无边框设计**: 现代化 UI 体验
- **拖拽支持**: 自定义窗口拖拽逻辑
- **信号槽机制**: 解耦窗口控制逻辑

**MainWindow 类** - 主窗口容器:
```python
class MainWindow(QMainWindow):
    """主窗口类 - UI 容器和布局管理"""
    
    def __init__(self, app_instance=None):
        # 保存 App 实例引用，实现组件间通信
        self.app_instance = app_instance
        self.is_maximized = False
        self.normal_geometry = None
```

#### 3. 页面系统 - BasePage 继承体系

**文件**: `src/ui/pages/base_page.py`

```python
class BasePage(QWidget):
    """基础页面类 - 页面标准化基础"""
    
    def __init__(self, title="页面", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()  # 子类实现具体UI
```

**页面懒加载机制**:
```python
# 在 NmodmApp 中
def get_or_create_page(self, page_name):
    """按需创建页面，提升启动性能"""
    if page_name not in self._pages_cache:
        self._pages_cache[page_name] = self._create_page(page_name)
    return self._pages_cache[page_name]
```

### 设计模式应用

#### 1. 单例模式 (Singleton)

**应用场景**: 全局唯一的管理器类

```python
class ToolManager:
    """工具管理器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # 初始化逻辑
            self._initialized = True
```

**使用单例的类**:
- `ToolManager`: 全局工具管理
- `ConfigManager`: 配置统一管理
- `DLLManager`: 系统级 DLL 操作
- `TranslationManager`: 翻译管理

#### 2. 观察者模式 (Observer)

**应用场景**: Qt 信号槽机制

```python
class DownloadManager(QObject):
    """下载管理器 - 使用信号通知观察者"""
    
    # 定义信号
    progress = Signal(int)  # 下载进度
    finished = Signal(bool, str)  # 完成状态
    error_occurred = Signal(str)  # 错误信息
    
    def download_file(self, url):
        # 下载过程中发送进度
        self.progress.emit(50)
        # 完成时通知
        self.finished.emit(True, "下载成功")
```

**连接信号槽**:
```python
# 在 UI 组件中
download_manager.progress.connect(self.update_progress_bar)
download_manager.finished.connect(self.on_download_finished)
download_manager.error_occurred.connect(self.show_error_message)
```

#### 3. 工厂模式 (Factory)

**应用场景**: 页面动态创建

```python
def _create_page(self, page_name):
    """页面工厂方法"""
    if page_name == "welcome":
        return WelcomePage()
    elif page_name == "quick_launch":
        return QuickLaunchPage()
    elif page_name == "config":
        return ConfigPage()
    # ... 其他页面
```

#### 4. 上下文管理器模式 (Context Manager)

**应用场景**: DLL 隔离安全管理

```python
class DllDirectoryContext:
    """DLL 目录上下文管理器 - 安全的游戏启动"""
    
    def __enter__(self):
        # 设置 DLL 搜索路径
        # 隔离 PySide6 DLL
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始 DLL 路径
        # 清理临时设置
        pass

# 使用方式
with DllDirectoryContext():
    # 在隔离环境中启动游戏
    subprocess.Popen([game_exe])
```

### 性能优化策略

#### 1. 延迟初始化 (Lazy Initialization)

```python
# 分阶段初始化，避免启动阻塞
QTimer.singleShot(100, self.delayed_initialization)  # 100ms后
QTimer.singleShot(200, self.init_download_manager)   # 200ms后
QTimer.singleShot(500, self.setup_status_timer)      # 500ms后
```

#### 2. 页面缓存 (Page Caching)

```python
# 页面只创建一次，后续直接从缓存获取
self._pages_cache = {}

def get_page(self, page_name):
    if page_name not in self._pages_cache:
        self._pages_cache[page_name] = self.create_page(page_name)
    return self._pages_cache[page_name]
```

#### 3. 异步操作 (Asynchronous Operations)

```python
class DownloadWorker(QThread):
    """下载工作线程 - 避免阻塞 UI"""
    
    def run(self):
        # 在后台线程执行下载
        self.download_file()
```

#### 4. 智能资源管理

- **进程清理**: 自动清理僵尸进程
- **DLL 隔离**: 避免 DLL 冲突
- **内存优化**: 页面缓存和延迟加载

---

## 核心组件详解

### 配置管理层

#### 1. ConfigManager - 配置管理器

**文件**: `src/config/config_manager.py`  
**职责**: 游戏路径配置、破解文件管理、系统信息检测

```python
class ConfigManager:
    """配置管理器类 - 单例模式"""
    
    def __init__(self):
        # 智能路径处理（开发/打包环境自适应）
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent  # 打包环境
        else:
            self.root_dir = Path(__file__).parent.parent.parent  # 开发环境
```

**核心方法**:
- `get_game_path()`: 游戏路径获取与验证
- `set_game_path(path)`: 路径设置与安全检查
- `apply_crack()`: 破解文件应用逻辑
- `get_game_info()`: 游戏信息深度检测
- `validate_game_path(path)`: 路径有效性验证

**技术特色**:
- **路径智能处理**: 自动适配开发/打包环境
- **中文路径检测**: 识别并警告中文路径问题
- **安全验证**: 多层次路径和文件验证

#### 2. ModConfigManager - Mod 配置管理器

**文件**: `src/config/mod_config_manager.py`  
**职责**: Mod 扫描识别、配置文件生成、外部 Mod 管理

**数据模型设计**:
```python
@dataclass
class ModPackage:
    """Mod 包配置 - 数据类设计"""
    id: str
    source: str
    load_after: Optional[List[Dict[str, Any]]] = None
    load_before: Optional[List[Dict[str, Any]]] = None
    enabled: bool = True
    is_external: bool = False
    comment: str = ""

@dataclass
class ModNative:
    """Native DLL 配置 - 数据类设计"""
    path: str
    optional: bool = False
    enabled: bool = True
    initializer: Optional[str] = None
    comment: str = ""
```

**核心管理逻辑**:
```python
class ModConfigManager:
    """Mod 配置管理器 - 复杂业务逻辑处理"""
    
    def scan_mods_directory(self) -> Dict[str, List[str]]:
        """智能 Mod 扫描 - 类型自动识别"""
        # 扫描内部 Mods 目录
        # 整合外部 Mod 路径
        # 智能类型检测（文件夹型/DLL型）
```

**技术亮点**:
- **TOML 配置格式**: 人类可读的配置文件
- **智能类型检测**: 自动识别 Mod 类型
- **外部 Mod 支持**: 灵活的外部 Mod 路径管理
- **备注系统**: 用户友好的 Mod 管理

### 工具管理层

#### 1. DownloadManager - 下载管理器

**文件**: `src/utils/download_manager.py`  
**职责**: 多线程下载、进度管理、多镜像支持

**工作线程设计**:
```python
class DownloadWorker(QThread):
    """下载工作线程 - 异步下载处理"""
    progress = Signal(int)  # 下载进度信号
    finished = Signal(bool, str)  # 完成信号
    
    def run(self):
        # 分块下载逻辑
        # 进度回调处理
        # 异常处理机制
```

**主管理器**:
```python
class DownloadManager(QObject):
    """下载管理器 - 多镜像下载策略"""
    
    DEFAULT_PROXY_URLS = [
        "https://gh-proxy.com/",
        "https://ghproxy.net/",
        "https://ghfast.top/"
    ]
    
    def download_with_mirrors(self, url, save_path):
        """多镜像下载，自动切换"""
        for mirror in self.DEFAULT_PROXY_URLS:
            try:
                return self.download(mirror + url, save_path)
            except:
                continue  # 尝试下一个镜像
```

**技术特色**:
- **多镜像支持**: GitHub 加速镜像自动切换
- **断点续传**: 支持下载中断恢复
- **进度监控**: 实时下载进度反馈
- **版本管理**: 自动版本检测和更新

#### 2. EasyTierManager - 虚拟局域网管理器

**文件**: `src/utils/easytier_manager.py`  
**职责**: 虚拟局域网管理、网络优化、进程控制

**多线程架构**:
```python
class EasyTierStartWorker(QThread):
    """EasyTier 启动工作线程"""
    start_finished = Signal(bool, str, object)

class NetworkOptimizationWorker(QThread):
    """网络优化工作线程"""
    optimization_finished = Signal(bool, str)

class EasyTierManager(QObject):
    """EasyTier 管理器 - 主控制器"""
    network_status_changed = Signal(bool)
    peer_list_updated = Signal(list)
    connection_info_updated = Signal(dict)
    error_occurred = Signal(str)
```

**核心功能**:
- **进程生命周期管理**: 启动、监控、停止
- **网络状态监控**: 实时连接状态检测
- **节点管理**: 对等节点发现和管理
- **配置生成**: 动态配置文件生成

**管理员权限处理**:
```python
class AdminProcess:
    """管理员进程包装器 - 权限提升处理"""
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None
        # 管理员进程特殊处理逻辑
```

#### 3. DLLManager - DLL 管理器

**文件**: `src/utils/dll_manager.py`  
**职责**: DLL 冲突检测、进程隔离、Steam 清理

```python
class DLLManager:
    """DLL 管理器 - 系统级 DLL 操作"""
    
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.psapi = ctypes.windll.psapi
    
    def is_dll_loaded(self, dll_name: str) -> bool:
        """检查 DLL 是否已加载到当前进程"""
        # Windows API 调用
        # 进程模块枚举
```

**DLL 隔离上下文管理器**:
```python
class DllDirectoryContext:
    """DLL 目录上下文管理器 - 安全的游戏启动"""
    
    def __enter__(self):
        # 设置 DLL 搜索路径
        # 隔离 PySide6 DLL
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始 DLL 路径
        # 清理临时设置
```

**技术亮点**:
- **DLL 冲突解决**: PySide6 与游戏进程的 DLL 隔离
- **上下文管理**: 安全的资源管理模式
- **Steam 进程清理**: 智能 Steam 进程检测和清理

### UI 组件层

#### 1. 快速启动页面 - QuickLaunchPage

**文件**: `src/ui/pages/quick_launch_page.py`  
**复杂度**: 最高（2764 行代码）

**核心组件类**:
```python
class PresetManager:
    """预设方案管理器 - 简化版本"""

class StatusBar(QFrame):
    """紧凑状态栏组件"""

class PresetCard(QFrame):
    """预设方案卡片 - 简化版本"""

class QuickLaunchPage(BasePage):
    """快速启动页面 - 重构版本"""
    navigate_to = Signal(str)  # 页面切换信号

class LaunchParamsConfigDialog(QDialog):
    """启动参数配置对话框"""

class PresetEditorDialog(QDialog):
    """预设方案编辑对话框"""
    presets_changed = Signal()
```

**技术特色**:
- **组件化设计**: 高度模块化的 UI 组件
- **信号槽通信**: 组件间松耦合通信
- **状态管理**: 复杂的 UI 状态同步
- **无边框对话框**: 现代化对话框设计

#### 2. 对话框组件 - ModernDialog 系列

**文件**: `src/ui/components/dialogs.py`

```python
class ModernDialog(QDialog):
    """现代化对话框基类"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        # 无边框设计
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        # 自定义拖拽
        # 现代化样式

class NotificationDialog(ModernDialog):
    """通知对话框"""

class ConfirmDialog(ModernDialog):
    """确认对话框"""
    confirmed = Signal()
```

### 异常处理机制

#### 1. 分层异常处理

```python
try:
    # 业务逻辑
    result = self.perform_operation()
except SpecificException as e:
    # 特定异常处理
    self.handle_specific_error(e)
except Exception as e:
    # 通用异常处理
    self.error_occurred.emit(f"操作失败: {e}")
    return False
```

#### 2. 信号驱动错误处理

```python
# 错误信号定义
error_occurred = Signal(str)

# 错误处理连接
self.manager.error_occurred.connect(self.show_error_message)
```

#### 3. 用户友好错误提示

- **本地化错误消息**: 中文错误提示
- **错误分类**: 不同类型错误的不同处理
- **恢复建议**: 提供解决方案建议

---

## 开发规范

### 代码风格

遵循 **PEP 8** 规范：

```bash
# 格式化代码
black src/

# 检查代码
flake8 src/

# 类型检查
mypy src/
```

### 命名约定

- **类名**: PascalCase (`ConfigManager`)
- **函数名**: snake_case (`get_game_path`)
- **常量**: UPPER_CASE (`DEFAULT_PORT`)
- **私有方法**: `_method_name`

### 文档字符串

使用 Google 风格的文档字符串：

```python
def download_file(url: str, save_path: str) -> bool:
    """下载文件到指定路径
    
    Args:
        url: 下载链接
        save_path: 保存路径
        
    Returns:
        bool: 下载是否成功
        
    Raises:
        ValueError: URL 无效时抛出
    """
    pass
```

### 提交规范

使用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**:
```
feat(mod): 添加 Mod 自动更新功能

- 实现版本检测
- 添加自动下载
- 更新 UI 提示

Closes #123
```

---

## 构建与打包

### 构建系统概览

Nmodm 支持两种打包方案：

| 特性 | Nuitka | PyInstaller |
|------|--------|-------------|
| **性能** | ⭐⭐⭐⭐⭐ 编译为C代码 | ⭐⭐⭐ 解释执行 |
| **体积** | ⭐⭐⭐⭐ 较小 | ⭐⭐⭐ 较大 |
| **兼容性** | ⭐⭐⭐ 需要C编译器 | ⭐⭐⭐⭐⭐ 开箱即用 |
| **构建速度** | ⭐⭐ 较慢 | ⭐⭐⭐⭐ 快速 |
| **推荐场景** | 生产发布 | 开发测试 |

### 使用 Nuitka（推荐生产）

#### 1. 安装 Nuitka

```bash
pip install nuitka
```

#### 2. 安装 C 编译器

**Windows**:
- 下载并安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
- 或使用 MinGW-w64

#### 3. 构建选项

**单文件模式**（推荐发布）:
```bash
python build_nuitka.py
# 选择: 1. 单文件模式 (onefile)
```

**特点**:
- 单个 `.exe` 文件
- 便于分发
- 首次启动稍慢（需解压）

**目录模式**（推荐开发）:
```bash
python build_nuitka.py
# 选择: 2. 独立模式 (standalone)
```

**特点**:
- 目录结构清晰
- 启动速度快
- 便于调试

#### 4. 构建配置

**编辑 `build_nuitka.py`**:

```python
class NuitkaBuilder:
    def __init__(self):
        self.version = "3.1.1"  # 版本号
        self.project_root = Path(__file__).parent
        
        # 版本信息配置
        self.version_info = {
            "product_name": "Nmodm",
            "product_version": f"{self.version}.0",
            "file_version": f"{self.version}.0",
            "file_description": "Nmodm - 游戏模组管理器",
            "copyright": "Copyright © 2025",
        }
```

**关键构建参数**:
```python
nuitka_args = [
    "--standalone",  # 或 --onefile
    "--windows-disable-console",  # 无控制台窗口
    "--enable-plugin=pyside6",  # PySide6 插件
    "--include-data-dir=src/i18n/locales=src/i18n/locales",  # 包含翻译文件
    "--windows-icon-from-ico=zwnr.png",  # 应用图标
    "--company-name=Nmodm Team",
    "--product-name=Nmodm",
    f"--product-version={self.version}",
]
```

### 使用 PyInstaller（快速测试）

#### 1. 安装 PyInstaller

```bash
pip install pyinstaller
```

#### 2. 构建

```bash
python build_pyinstaller.py
```

#### 3. 构建配置

**编辑 `build_pyinstaller.py`**:

```python
class PyInstallerBuilder:
    def __init__(self):
        self.version = "3.1.1"
        
    def build(self, mode="onefile"):
        pyinstaller_args = [
            "main.py",
            "--name=Nmodm",
            "--windowed",  # 无控制台
            "--icon=zwnr.png",
            "--add-data=src/i18n/locales;src/i18n/locales",
            f"--{mode}",  # onefile 或 onedir
        ]
```

### 统一构建管理器

**使用 `build_manager.py`**:

```bash
python build_manager.py
```

**交互式菜单**:
```
=== Nmodm 构建管理器 ===
1. Nuitka 单文件构建
2. Nuitka 目录构建
3. PyInstaller 单文件构建
4. PyInstaller 目录构建
5. 清理构建文件
6. 退出
```

### 版本管理

#### 版本号统一管理

**主版本文件**: `src/version.json`

```json
{
  "version": "3.1.1"
}
```

#### 更新版本流程

1. **修改版本号**:
```bash
# 编辑 src/version.json
{
  "version": "3.1.2"
}
```

2. **同步到构建脚本**:
```python
# build_nuitka.py 会自动读取
self.version = self._load_version_from_src() or "3.1.1"
```

3. **提交代码**:
```bash
git add src/version.json
git commit -m "chore: bump version to 3.1.2"
```

4. **创建 Git Tag**:
```bash
git tag -a v3.1.2 -m "Release v3.1.2"
git push origin v3.1.2
```

### 构建输出

#### 目录结构

```
Builds/
├── Nuitka/
│   ├── Nmodm_v3.1.1_onefile/
│   │   └── Nmodm_v3.1.1_onefile.exe
│   └── Nmodm_v3.1.1_standalone/
│       ├── Nmodm.exe
│       ├── _internal/
│       └── ...
└── PyInstaller/
    ├── dist/
    │   ├── Nmodm.exe  # onefile
    │   └── Nmodm/     # onedir
    └── build/
```

### 构建优化技巧

#### 1. 减小体积

```python
# 排除不必要的模块
"--nofollow-import-to=tkinter",
"--nofollow-import-to=matplotlib",
```

#### 2. 加快构建速度

```python
# 使用缓存
"--assume-yes-for-downloads",
```

#### 3. 调试构建问题

```bash
# 启用详细输出
python build_nuitka.py --verbose

# 保留控制台窗口（调试用）
# 注释掉 --windows-disable-console
```

### 发布检查清单

构建发布版本前确认：

- [ ] 版本号已更新（`src/version.json`）
- [ ] 所有功能测试通过
- [ ] 更新日志已编写（`docs/zh/CHANGELOG.md`）
- [ ] 文档已更新
- [ ] 构建脚本版本号同步
- [ ] 测试打包后的程序
- [ ] 创建 Git Tag
- [ ] 准备 Release Notes

---

## 调试与测试

### 开发调试

#### 1. 基础调试

**启用详细日志**:
```python
# 在 main.py 中添加
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**使用 print 调试**:
```python
# 快速调试
print(f"[DEBUG] 变量值: {variable}")

# 使用 Qt 调试
from PySide6.QtCore import qDebug
qDebug("调试信息")
```

#### 2. UI 调试

**检查信号槽连接**:
```python
# 验证信号是否正确连接
self.button.clicked.connect(lambda: print("按钮被点击"))
```

**UI 组件检查**:
```python
# 检查组件是否正确创建
print(f"组件可见性: {self.widget.isVisible()}")
print(f"组件大小: {self.widget.size()}")
```

#### 3. 性能分析

**使用 cProfile**:
```bash
# 生成性能报告
python -m cProfile -o profile.stats main.py

# 分析结果
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

**使用 line_profiler**:
```bash
pip install line_profiler

# 在代码中添加 @profile 装饰器
@profile
def slow_function():
    pass

# 运行分析
kernprof -l -v main.py
```

#### 4. 内存分析

```bash
pip install memory_profiler

# 运行内存分析
python -m memory_profiler main.py
```

### 测试策略

#### 1. 手动测试

**功能测试清单**:
```
□ 游戏路径配置
  □ 浏览选择路径
  □ 路径验证
  □ 中文路径警告
  
□ Mod 管理
  □ Mod 扫描
  □ Mod 启用/禁用
  □ 配置文件生成
  
□ 工具下载
  □ ME3 工具下载
  □ 镜像切换
  □ 进度显示
  
□ 虚拟局域网
  □ 房间创建
  □ 房间加入
  □ 网络状态监控
```

#### 2. 单元测试（可选）

**使用 pytest**:
```bash
pip install pytest pytest-qt

# 运行测试
pytest tests/
```

**测试示例**:
```python
# tests/test_config.py
import pytest
from src.config.config_manager import ConfigManager

def test_config_manager_singleton():
    """测试配置管理器单例模式"""
    manager1 = ConfigManager()
    manager2 = ConfigManager()
    assert manager1 is manager2

def test_game_path_validation():
    """测试游戏路径验证"""
    manager = ConfigManager()
    # 测试有效路径
    assert manager.validate_game_path("C:/Games/nightreign.exe")
    # 测试无效路径
    assert not manager.validate_game_path("invalid/path")
```

#### 3. 集成测试

**完整流程测试**:
```python
def test_mod_workflow():
    """测试 Mod 完整工作流程"""
    # 1. 初始化管理器
    mod_manager = ModConfigManager()
    
    # 2. 扫描 Mod
    mods = mod_manager.scan_mods_directory()
    assert len(mods) > 0
    
    # 3. 生成配置
    result = mod_manager.generate_config()
    assert result is True
    
    # 4. 验证配置文件
    config_file = Path("Mods/current.me3")
    assert config_file.exists()
```

### 调试打包后的程序

#### 1. 启用控制台窗口

**临时启用**:
```python
# 在 build_nuitka.py 中注释掉
# "--windows-disable-console",
```

#### 2. 日志文件

**添加文件日志**:
```python
import logging
from pathlib import Path

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "nmodm.log"),
        logging.StreamHandler()
    ]
)
```

#### 3. 异常捕获

**全局异常处理**:
```python
import sys
import traceback

def exception_hook(exctype, value, tb):
    """全局异常处理"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(error_msg)
    # 写入日志文件
    with open("crash.log", "w") as f:
        f.write(error_msg)

sys.excepthook = exception_hook
```

---

## 常见开发任务

### 1. 添加新页面

**步骤**:

1. **创建页面文件**:
```python
# src/ui/pages/new_page.py
from .base_page import BasePage
from PySide6.QtWidgets import QVBoxLayout, QLabel

class NewPage(BasePage):
    """新页面"""
    
    def __init__(self):
        super().__init__(title="新页面")
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("这是新页面"))
```

2. **在 App 中注册页面**:
```python
# src/app.py
def _create_page(self, page_name):
    if page_name == "new_page":
        from .ui.pages.new_page import NewPage
        return NewPage()
    # ... 其他页面
```

3. **添加侧边栏导航**:
```python
# src/ui/sidebar.py
self.add_nav_item("🆕 新页面", "new_page")
```

### 2. 添加新配置项

**步骤**:

1. **在配置管理器中添加方法**:
```python
# src/config/config_manager.py
def get_new_config(self):
    """获取新配置"""
    return self.config.get("new_config", default_value)

def set_new_config(self, value):
    """设置新配置"""
    self.config["new_config"] = value
    self.save_config()
```

2. **在 UI 中添加控件**:
```python
# src/ui/pages/config_page.py
self.new_config_input = QLineEdit()
self.new_config_input.setText(self.config_manager.get_new_config())
```

3. **连接保存逻辑**:
```python
def save_config(self):
    value = self.new_config_input.text()
    self.config_manager.set_new_config(value)
```

### 3. 添加新的下载任务

**步骤**:

1. **使用下载管理器**:
```python
from src.utils.download_manager import DownloadManager

download_manager = DownloadManager()

# 创建下载任务
download_manager.download_file(
    url="https://example.com/file.zip",
    save_path="downloads/file.zip",
    on_progress=self.update_progress,
    on_finished=self.on_download_finished
)
```

2. **处理下载回调**:
```python
def update_progress(self, progress):
    """更新进度条"""
    self.progress_bar.setValue(progress)

def on_download_finished(self, success, message):
    """下载完成处理"""
    if success:
        print("下载成功")
    else:
        print(f"下载失败: {message}")
```

### 4. 添加新的信号槽

**步骤**:

1. **定义信号**:
```python
from PySide6.QtCore import Signal

class MyWidget(QWidget):
    # 定义自定义信号
    data_changed = Signal(str)  # 带参数的信号
    action_triggered = Signal()  # 无参数的信号
```

2. **发送信号**:
```python
def update_data(self, new_data):
    self.data = new_data
    self.data_changed.emit(new_data)  # 发送信号
```

3. **连接信号槽**:
```python
# 在其他组件中
widget.data_changed.connect(self.on_data_changed)

def on_data_changed(self, data):
    print(f"数据已更新: {data}")
```

### 5. 国际化支持

**添加新的翻译**:

1. **在翻译文件中添加**:
```json
// src/i18n/locales/zh_CN.json
{
  "new_feature": "新功能",
  "new_button": "新按钮"
}
```

2. **在代码中使用**:
```python
from src.i18n import t

label = QLabel(t("new_feature"))
button = QPushButton(t("new_button"))
```

### 6. 添加新的管理器

**步骤**:

1. **创建管理器类**:
```python
# src/utils/new_manager.py
from PySide6.QtCore import QObject, Signal

class NewManager(QObject):
    """新管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            # 初始化逻辑
```

2. **在 App 中使用**:
```python
# src/app.py
from src.utils.new_manager import NewManager

self.new_manager = NewManager()
```

---

## 贡献流程

### 1. Fork 和克隆

```bash
# Fork 项目到你的 GitHub 账号
# 然后克隆
git clone https://github.com/your-username/Nmodm.git
cd Nmodm
```

### 2. 创建功能分支

```bash
# 功能分支
git checkout -b feature/amazing-feature

# 修复分支
git checkout -b fix/bug-description

# 文档分支
git checkout -b docs/improve-readme
```

### 3. 开发和测试

```bash
# 进行开发
# 运行测试
python main.py

# 检查代码
black src/
flake8 src/
```

### 4. 提交更改

```bash
git add .
git commit -m "feat: add amazing feature"
```

### 5. 推送和创建 PR

```bash
git push origin feature/amazing-feature
# 在 GitHub 上创建 Pull Request
```

详见 [贡献指南](CONTRIBUTING.md)

---

## 常见问题解答

### 开发环境问题

**Q: 虚拟环境激活失败**

A: Windows PowerShell 可能需要修改执行策略：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Q: PySide6 导入失败**

A: 确保安装了正确版本：
```bash
pip uninstall PySide6
pip install PySide6==6.6.0
```

### 功能开发问题

**Q: 如何调试信号槽不触发？**

A: 
1. 检查信号槽连接是否正确
2. 使用 lambda 添加调试输出
3. 确认对象生命周期

**Q: 如何处理跨线程 UI 更新？**

A: 使用信号槽机制：
```python
class Worker(QThread):
    update_ui = Signal(str)
    
    def run(self):
        # 在工作线程中
        self.update_ui.emit("更新UI")

# 在主线程中连接
worker.update_ui.connect(self.update_label)
```

### 打包问题

**Q: 打包后程序无法启动**

A:
1. 检查是否包含所有依赖
2. 使用目录模式调试
3. 查看错误日志

**Q: 打包体积过大**

A:
1. 排除不必要的模块
2. 使用 Nuitka 优化
3. 压缩资源文件

---

## 资源链接

- 📖 [用户指南](USER_GUIDE.md)
- 🤝 [贡献指南](CONTRIBUTING.md)
- 📝 [更新日志](CHANGELOG.md)
- 🐛 [问题追踪](https://github.com/your-repo/Nmodm/issues)
- 💬 [讨论区](https://github.com/your-repo/Nmodm/discussions)

---

**最后更新**: 2025-01-20  
**文档版本**: v3.1.1
