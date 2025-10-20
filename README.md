# Nmodm - 现代化游戏管理工具

<div align="center">

![Nmodm Logo](zwnr.png)

**专为《艾尔登法环：黑夜君临》设计的现代化游戏管理工具**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)](https://pyside.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://windows.microsoft.com)
[![Version](https://img.shields.io/badge/Version-v3.0.7-brightgreen.svg)](../../releases)

</div>

## 📖 项目简介

Nmodm 是一款专为《艾尔登法环：黑夜君临》(Elden Ring: Nightreign) 设计的现代化游戏管理工具。它集成了 Mod 管理、局域网联机、工具下载、配置管理等多项功能，为玩家提供一站式的游戏增强体验。

### 🎯 设计理念

- **用户友好**: 现代化无边框界面设计，操作简单直观
- **功能完整**: 涵盖游戏增强的各个方面，无需额外工具
- **智能化**: 自动检测、智能配置，减少用户手动操作
- **可扩展**: 模块化架构设计，便于功能扩展和维护

## ✨ 核心特性

### 🎮 游戏管理
- **一键配置**: 自动检测游戏路径，快速配置启动参数
- **多版本支持**: 同时支持艾尔登法环和黑夜君临版本
- **启动优化**: 智能启动参数配置，提升游戏性能

### 🔧 ME3 工具集成
- **自动下载**: 从官方源自动下载最新版本 ME3 工具
- **版本管理**: 智能版本检测和更新提醒
- **镜像切换**: 支持多个下载镜像，确保下载稳定性

### 🎯 智能 Mod 管理
- **类型识别**: 自动识别文件夹型和 DLL 型 Mod
- **内外部支持**: 支持内置 Mod 和外部 Mod 文件
- **配置生成**: 实时生成 ME3 兼容的配置文件
- **注释系统**: 为每个 Mod 添加自定义说明和注释

### 🌐 局域网联机
- **EasyTier 集成**: 基于 EasyTier 的虚拟局域网解决方案
- **房间管理**: 创建、加入、管理联机房间
- **网络优化**: 内置网络加速和优化功能
- **一键启动**: 配置完成后一键启动联机模式

### 🎨 现代化界面
- **无边框设计**: 现代化的无边框窗口界面
- **侧边栏导航**: 清晰的功能分类和导航
- **实时状态**: 实时显示各项功能的运行状态
- **响应式布局**: 适配不同分辨率和窗口大小

## � 系统要求

### 最低配置要求
- **操作系统**: Windows 10 (64位) 或更高版本
- **Python**: 3.8+ (源码运行时需要)
- **内存**: 4GB RAM
- **存储空间**: 500MB 可用空间
- **网络**: 互联网连接 (用于下载工具和更新)

### 推荐配置
- **操作系统**: Windows 11 (64位)
- **内存**: 8GB RAM 或更高
- **存储空间**: 2GB 可用空间
- **网络**: 稳定的宽带连接

### 依赖组件
- **Visual C++ Redistributable**: 2015-2022 (x64)
- **Microsoft Edge WebView2**: 自动安装
- **.NET Framework**: 4.7.2 或更高版本

## 🚀 安装指南

### 方式一：直接使用（推荐新手）

1. **下载程序**
   ```
   访问 Releases 页面下载最新版本
   选择 Nmodm_v3.0.5_Windows_x64.zip
   ```

2. **解压安装**
   ```
   解压到任意目录（建议英文路径）
   确保有足够的磁盘空间
   ```

3. **运行程序**
   ```
   双击 Nmodm.exe 启动程序
   首次运行会自动初始化必要组件
   ```

### 方式二：源码运行（推荐开发者）

1. **环境准备**
   ```bash
   # 确保已安装 Python 3.8+
   python --version

   # 创建虚拟环境（推荐）
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **获取源码**
   ```bash
   # 克隆项目
   git clone https://github.com/your-repo/Nmodm.git
   cd Nmodm
   ```

3. **安装依赖**
   ```bash
   # 安装运行依赖
   pip install -r requirements.txt

   # 安装开发依赖（可选）
   pip install -r requirements-dev.txt
   ```

4. **运行程序**
   ```bash
   # 启动应用
   python main.py
   ```

## 📖 快速开始

### 首次使用配置

1. **配置游戏路径**
   - 打开"基础配置"页面
   - 点击"浏览"选择 `nightreign.exe` 文件位置
   - 确认路径正确后点击"保存"

2. **下载 ME3 工具**
   - 切换到"工具下载"页面
   - 选择合适的下载镜像
   - 点击"下载 ME3 工具"等待完成

3. **配置在线修复**
   - 在"基础配置"页面启用"在线修复"
   - 程序会自动解压必要的修复文件

### 基础使用流程

1. **管理 Mod**
   ```
   进入"Mod配置"页面
   → 添加内部或外部 Mod
   → 配置 Mod 参数和注释
   → 生成配置文件
   ```

2. **配置局域网联机**
   ```
   进入"局域网联机"页面
   → 创建或加入房间
   → 配置网络参数
   → 启动虚拟局域网
   ```

3. **启动游戏**
   ```
   进入"快速启动"页面
   → 检查配置概览
   → 点击"启动游戏"
   ```

## � 配置选项

### 基础配置
- **游戏路径**: 设置 nightreign.exe 的完整路径
- **在线修复**: 启用/禁用在线修复功能
- **启动参数**: 自定义游戏启动参数

### ME3 工具配置
- **下载镜像**: 选择最佳的下载源
- **版本检测**: 自动检测和更新工具版本
- **工具路径**: 自定义 ME3 工具安装位置

### Mod 配置
- **内部 Mod**: 管理 Mods 文件夹中的 Mod
- **外部 Mod**: 添加任意位置的 Mod 文件
- **Mod 注释**: 为每个 Mod 添加自定义说明
- **配置生成**: 实时生成 ME3 兼容配置

### 网络配置
- **房间管理**: 创建和管理联机房间
- **网络优化**: 配置网络加速参数
- **高级设置**: 压缩算法、加密设置等

## � 功能详解

### 🎮 快速启动页面
显示当前配置概览，包括：
- 游戏路径状态
- ME3 工具状态
- Mod 配置状态
- 网络连接状态
- 一键启动游戏功能

### 🔧 基础配置页面
- **游戏路径设置**: 浏览并选择游戏可执行文件
- **在线修复开关**: 启用后自动解压修复文件
- **配置验证**: 实时验证配置的有效性

### 📥 工具下载页面
- **镜像选择**: 多个下载源确保稳定性
- **版本管理**: 自动检测最新版本
- **下载进度**: 实时显示下载进度和状态

### 🎯 Mod 配置页面
- **Mod 列表**: 显示所有可用的 Mod
- **类型识别**: 自动识别 Mod 类型（文件夹/DLL）
- **参数配置**: 为特定 Mod 配置参数
- **注释系统**: 添加自定义说明和备注

### 🌐 局域网联机页面
- **房间创建**: 创建新的联机房间
- **房间加入**: 加入现有房间
- **网络状态**: 实时显示网络连接状态
- **高级设置**: 网络优化和安全配置

## �️ 技术架构

### 核心技术栈
- **界面框架**: PySide6 (Qt6) - 现代化跨平台 GUI 框架
- **编程语言**: Python 3.8+ - 高效的开发语言
- **配置格式**: JSON, TOML - 灵活的配置文件格式
- **打包工具**: PyInstaller, Nuitka - 多种打包方案支持
- **网络库**: requests - HTTP 请求处理
- **文件处理**: pathlib, zipfile - 现代化文件操作
- **进程管理**: psutil - 系统进程监控和管理

### 集成工具
- **ME3 工具**: Mod 管理和配置生成
- **EasyTier**: 虚拟局域网解决方案
- **OnlineFix**: 游戏在线修复工具

### 架构设计
- **模块化设计**: 清晰的功能模块划分
- **配置驱动**: 基于配置文件的灵活架构
- **事件驱动**: 响应式的用户界面更新
- **异步处理**: 非阻塞的网络和文件操作

## 📁 项目结构

```
Nmodm/
├── 📄 main.py                    # 应用程序入口点
├── 📁 src/                       # 源代码目录
│   ├── 📄 app.py                # 应用程序主类
│   ├── 📁 config/               # 配置管理模块
│   │   ├── config_manager.py    # 主配置管理器
│   │   ├── mod_config_manager.py # Mod 配置管理
│   │   └── network_optimization_config.py # 网络优化配置
│   ├── 📁 ui/                   # 用户界面模块
│   │   ├── main_window.py       # 主窗口
│   │   ├── sidebar.py           # 侧边栏导航
│   │   ├── 📁 components/       # UI 组件
│   │   └── 📁 pages/            # 功能页面
│   └── 📁 utils/                # 工具类模块
│       ├── download_manager.py  # 下载管理器
│       ├── tool_manager.py      # 工具管理器
│       ├── easytier_manager.py  # EasyTier 管理
│       └── network_optimizer.py # 网络优化
├── 📁 OnlineFix/                # 在线修复文件
│   ├── OnlineFix64.dll         # 主修复库
│   ├── esl2.zip                # ESL 工具包
│   └── tool.zip                # 辅助工具包
├── 📁 Mods/                     # Mod 文件目录
│   ├── 📁 Ascension/           # 上升 Mod
│   ├── 📁 SeamlessCoop/        # 无缝合作 Mod
│   ├── 📁 Unlock/              # 解锁 Mod
│   └── current.me3             # 当前配置文件
├── 📁 ESR/                      # EasyTier 工具
│   ├── easytier-core.exe       # 核心程序
│   ├── easytier.toml           # 配置文件
│   └── 📁 rooms_config/        # 房间配置
├── 📁 me3p/                     # ME3 工具包
│   ├── 📁 bin/                 # 可执行文件
│   ├── eldenring-default.me3   # 默认配置
│   └── version.json            # 版本信息
├── 📁 Builds/                   # 打包输出目录
├── 📄 build_manager.py          # 统一打包管理
├── 📄 build_pyinstaller.py      # PyInstaller 打包
├── 📄 build_nuitka.py           # Nuitka 打包
├── 📄 requirements.txt          # Python 依赖
└── 📄 README.md                 # 项目说明文档
```

## 🔧 API 文档

### 核心类和方法

#### ConfigManager
```python
class ConfigManager:
    """配置管理器 - 处理应用程序配置"""

    def load_config(self) -> dict:
        """加载配置文件"""

    def save_config(self, config: dict) -> bool:
        """保存配置文件"""

    def get_game_path(self) -> str:
        """获取游戏路径"""

    def set_game_path(self, path: str) -> bool:
        """设置游戏路径"""
```

#### ToolManager
```python
class ToolManager:
    """工具管理器 - 处理外部工具的下载和管理"""

    def download_me3_tools(self, mirror: str = "default") -> bool:
        """下载 ME3 工具"""

    def check_tool_version(self) -> str:
        """检查工具版本"""

    def extract_tools(self) -> bool:
        """解压工具文件"""
```

#### EasyTierManager
```python
class EasyTierManager:
    """EasyTier 管理器 - 处理虚拟局域网功能"""

    def create_room(self, room_config: dict) -> bool:
        """创建联机房间"""

    def join_room(self, room_id: str) -> bool:
        """加入联机房间"""

    def start_network(self) -> bool:
        """启动虚拟网络"""

    def stop_network(self) -> bool:
        """停止虚拟网络"""
```

## 🔧 开发指南

### 开发环境搭建

1. **环境要求**
   ```bash
   # 检查 Python 版本
   python --version  # 需要 3.8+

   # 检查 pip 版本
   pip --version
   ```

2. **创建开发环境**
   ```bash
   # 克隆项目
   git clone https://github.com/your-repo/Nmodm.git
   cd Nmodm

   # 创建虚拟环境
   python -m venv .venv

   # 激活虚拟环境
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   # 安装运行时依赖
   pip install -r requirements.txt

   # 安装开发依赖（可选）
   pip install -r requirements-dev.txt
   ```

### 开发工作流

1. **运行开发版本**
   ```bash
   # 直接运行
   python main.py

   # 或使用模块方式
   python -m src.app
   ```

2. **代码规范**
   ```bash
   # 代码格式化
   black src/

   # 代码检查
   flake8 src/

   # 类型检查
   mypy src/
   ```

3. **测试**
   ```bash
   # 运行单元测试
   pytest tests/

   # 运行集成测试
   pytest tests/integration/

   # 生成覆盖率报告
   pytest --cov=src tests/
   ```

### 打包部署

1. **使用统一管理器**
   ```bash
   # 交互式打包
   python build_manager.py

   # 选择打包工具和模式
   # 1. PyInstaller (推荐)
   # 2. Nuitka (高性能)
   ```

2. **单独打包**
   ```bash
   # PyInstaller 打包
   python build_pyinstaller.py

   # Nuitka 打包
   python build_nuitka.py
   ```

3. **打包配置**
   - **单文件模式**: 生成单个可执行文件
   - **目录模式**: 生成包含依赖的目录
   - **优化选项**: 大小优化、性能优化

### 调试技巧

1. **日志配置**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **性能分析**
   ```bash
   # 使用 cProfile
   python -m cProfile -o profile.stats main.py

   # 分析结果
   python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
   ```

3. **内存分析**
   ```bash
   # 使用 memory_profiler
   pip install memory_profiler
   python -m memory_profiler main.py
   ```

## 🤝 贡献指南

我们欢迎所有形式的贡献！无论是报告 Bug、提出功能建议、改进文档还是提交代码，都对项目的发展有重要意义。

### 贡献方式

#### 🐛 报告问题
1. **搜索现有 Issues**: 确认问题尚未被报告
2. **使用 Issue 模板**: 提供详细的问题描述
3. **包含环境信息**: 操作系统、Python 版本、软件版本等
4. **提供复现步骤**: 详细的操作步骤和预期结果

#### 💡 功能建议
1. **描述使用场景**: 说明功能的实际应用价值
2. **提供设计思路**: 如有可能，提供初步的实现思路
3. **考虑兼容性**: 确保建议与现有功能兼容

#### 📝 改进文档
1. **修正错误**: 修复文档中的错误或过时信息
2. **补充内容**: 添加缺失的使用说明或示例
3. **翻译工作**: 帮助翻译文档到其他语言

#### 💻 代码贡献

1. **Fork 项目**
   ```bash
   # Fork 项目到你的 GitHub 账户
   # 然后克隆到本地
   git clone https://github.com/your-username/Nmodm.git
   cd Nmodm
   ```

2. **创建开发分支**
   ```bash
   # 创建并切换到功能分支
   git checkout -b feature/amazing-feature

   # 或修复分支
   git checkout -b fix/bug-description
   ```

3. **开发和测试**
   ```bash
   # 设置开发环境
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

   # 进行开发
   # ... 编写代码 ...

   # 运行测试
   python -m pytest tests/

   # 代码格式化
   black src/
   flake8 src/
   ```

4. **提交更改**
   ```bash
   # 添加更改
   git add .

   # 提交更改（使用清晰的提交信息）
   git commit -m "feat: add amazing feature

   - Add new functionality for X
   - Improve performance of Y
   - Fix issue with Z"
   ```

5. **推送和创建 PR**
   ```bash
   # 推送到你的 Fork
   git push origin feature/amazing-feature

   # 在 GitHub 上创建 Pull Request
   ```

### 代码规范

#### 编码标准
- **Python 风格**: 遵循 PEP 8 编码规范
- **命名约定**: 使用有意义的变量和函数名
- **注释规范**: 为复杂逻辑添加清晰的注释
- **文档字符串**: 为所有公共函数和类添加文档字符串

#### 提交信息规范
使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**类型说明**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

#### 代码审查
- **自我审查**: 提交前仔细检查代码
- **测试覆盖**: 确保新代码有适当的测试
- **文档更新**: 如需要，更新相关文档
- **向后兼容**: 避免破坏性更改

### 开发环境

#### 推荐工具
- **IDE**: VS Code, PyCharm
- **代码格式化**: Black, isort
- **代码检查**: flake8, pylint
- **类型检查**: mypy
- **测试框架**: pytest

#### 环境配置
```bash
# 安装开发工具
pip install black flake8 mypy pytest

# 配置 pre-commit hooks
pip install pre-commit
pre-commit install
```

## � 安全说明

### 安全特性
- **本地运行**: 所有核心功能在本地执行，保护用户隐私
- **开源透明**: 源代码完全开放，可审查安全性
- **无恶意代码**: 不包含任何恶意软件或后门
- **权限最小化**: 仅请求必要的系统权限

### 安全建议
- **下载来源**: 仅从官方 Releases 页面下载
- **杀毒软件**: 某些杀毒软件可能误报，请添加白名单
- **防火墙**: 联机功能需要网络访问权限
- **管理员权限**: 某些功能可能需要管理员权限

### 隐私保护
- **数据收集**: 不收集任何用户个人信息
- **网络通信**: 仅用于下载工具和联机功能
- **配置文件**: 所有配置文件存储在本地
- **日志记录**: 日志文件仅包含技术信息

## 🚨 常见问题

### 安装和运行问题

**Q: 程序无法启动，提示缺少 DLL 文件**
A: 安装 Visual C++ Redistributable 2015-2022 (x64) 和 .NET Framework 4.7.2+

**Q: 杀毒软件报告病毒**
A: 这是误报，请将程序添加到杀毒软件白名单

**Q: 程序启动后界面显示异常**
A: 确保系统支持 DirectX 11，更新显卡驱动程序

### 功能使用问题

**Q: 无法检测到游戏路径**
A: 手动浏览选择 nightreign.exe 文件，确保路径正确

**Q: ME3 工具下载失败**
A: 尝试切换下载镜像，检查网络连接和防火墙设置

**Q: Mod 配置不生效**
A: 确保 ME3 工具已正确安装，检查 Mod 文件完整性

**Q: 局域网联机连接失败**
A: 检查防火墙设置，确保相关端口未被阻止

### 性能优化问题

**Q: 程序运行缓慢**
A: 关闭不必要的后台程序，确保有足够的内存空间

**Q: 游戏启动慢**
A: 优化启动参数，关闭不需要的 Mod

## 📊 版本历史

### v3.0.5 (2025-01-06)
- 🐛 修复 Mod 配置页面显示问题
- 🐛 修复虚拟局域网高级设置保存问题
- 🐛 修复 TOML 配置文件同步问题
- 🐛 修复进程管理和网络停止卡顿问题
- 🔧 统一更新版本号到 3.0.5

### v3.0.3 (Previous)
- ✨ 新增现代化无边框界面设计
- ✨ 集成 EasyTier 虚拟局域网功能
- ✨ 添加智能 Mod 管理系统
- 🔧 优化打包配置和部署流程

## �📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

### 许可证摘要
- ✅ **商业使用**: 允许商业使用
- ✅ **修改**: 允许修改源代码
- ✅ **分发**: 允许分发软件
- ✅ **私人使用**: 允许私人使用
- ❗ **责任**: 软件按"原样"提供，不提供任何担保

## 🙏 致谢

### 开源项目
- [ME3 项目](https://me3.readthedocs.io/) - 提供强大的 Mod 管理工具
- [PySide6](https://pyside.org/) - 优秀的 Python GUI 框架
- [EasyTier](https://github.com/EasyTier/EasyTier) - 高性能虚拟局域网解决方案
- [PyDracula](https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6) - 现代化界面设计灵感

### 社区贡献
- 感谢所有提交 Issue 和 PR 的贡献者
- 感谢 Beta 测试用户的反馈和建议
- 感谢艾尔登法环社区的支持和推广

### 特别感谢
- **FromSoftware** - 创造了精彩的艾尔登法环世界
- **Bandai Namco** - 游戏发行和支持
- **Mod 开发者们** - 为游戏带来更多可能性

## 📞 支持与联系

### 获取帮助
- 📖 **文档**: 查看项目 Wiki 和 README
- 🐛 **问题报告**: [GitHub Issues](../../issues)
- 💬 **讨论交流**: [GitHub Discussions](../../discussions)
- 📧 **邮件联系**: [project-email@example.com](mailto:project-email@example.com)

### 社区资源
- 🎮 **游戏社区**: 加入艾尔登法环玩家群
- 📺 **视频教程**: 观看使用教程和技巧分享
- 📝 **博客文章**: 阅读开发日志和技术文章

### 反馈渠道
- ⭐ **GitHub Star**: 如果项目对你有帮助
- 🔄 **分享推荐**: 向朋友推荐这个工具
- 📝 **使用体验**: 分享你的使用心得

---

<div align="center">

![Nmodm Logo](zwnr.png)

**⭐ 如果这个项目对你有帮助，请给个 Star！**

**🎮 Made with ❤️ for Elden Ring: Nightreign Community 🎮**

[![GitHub stars](https://img.shields.io/github/stars/your-repo/Nmodm?style=social)](../../stargazers)
[![GitHub forks](https://img.shields.io/github/forks/your-repo/Nmodm?style=social)](../../network/members)
[![GitHub issues](https://img.shields.io/github/issues/your-repo/Nmodm)](../../issues)

---

*"在黑夜君临的世界中，让技术为冒险赋能"*

</div>
