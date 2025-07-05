# Nmodm - Modern ME3 Mod Manager

![Nmodm Logo](zwnr.png)

一个基于 PySide6 的现代化 ME3 Mod 管理器，专为《艾尔登法环：夜之王朝》设计。

## ✨ 特性

- 🎨 **现代化界面**: 基于 PySide6 的无边框设计，支持窗口拖拽
- 📦 **智能 Mod 管理**: 支持内部和外部 Mod，智能类型检测
- 🔧 **ME3 集成**: 完整的 ME3 配置文件生成和游戏启动
- 🌐 **多镜像下载**: 支持 GitHub 代理镜像，解决网络问题
- 📋 **配置管理**: 可视化的 Mod 配置和启动参数管理
- 🚀 **一键启动**: 快速启动界面，显示当前配置信息
- 💾 **外部 Mod 支持**: 支持添加任意路径的 Mod 文件
- 🏷️ **Mod 备注**: 为 Mod 添加自定义备注，便于管理
- 🔍 **智能检测**: 自动识别文件夹型、DLL型和混合型 Mod
- 📱 **右键菜单**: 支持右键管理单个 Mod 项目

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows 10/11
- 《艾尔登法环：夜之王朝》游戏

### 安装依赖

```bash
# 自动安装所有依赖
python install_dependencies.py

# 或手动安装
pip install -r requirements.txt
```

### 运行应用

```bash
python main.py
```

## 📦 打包部署

### 自动打包

```bash
# 使用统一管理器
python build_manager.py

# 选择打包工具和模式
# 1. PyInstaller (推荐，兼容性好)
# 2. Nuitka (性能更好，体积更小)
```

### 手动打包

```bash
# PyInstaller 打包
python build_pyinstaller.py

# Nuitka 打包
python build_nuitka.py
```

## 🏗️ 项目结构

```
Nmodm/
├── main.py                    # 应用入口
├── src/                       # 源代码
│   ├── app.py                # 应用主类
│   ├── config/               # 配置管理
│   │   ├── config_manager.py # 游戏配置管理
│   │   └── mod_config_manager.py # Mod配置管理
│   ├── ui/                   # 用户界面
│   │   ├── main_window.py    # 主窗口
│   │   ├── sidebar.py        # 侧边栏
│   │   └── pages/            # 页面组件
│   └── utils/                # 工具类
│       └── download_manager.py # 下载管理
├── OnlineFix/                # 在线修复文件
├── Mods/                     # Mod 文件夹
├── me3p/                     # ME3 工具
├── Builds/                   # 打包输出
├── build_*.py                # 打包脚本
└── docs/                     # 文档
```

## 🛠️ 技术栈

- **界面框架**: PySide6 (Qt6)
- **编程语言**: Python 3.8+
- **配置格式**: JSON, TOML
- **打包工具**: PyInstaller, Nuitka
- **网络请求**: requests
- **文件处理**: pathlib, zipfile

## 📖 使用指南

### 基础配置

1. **设置游戏路径**: 在配置页面选择 `nightreign.exe` 文件
2. **下载 ME3 工具**: 应用会自动下载最新版本的 ME3
3. **应用破解文件**: 一键应用 OnlineFix 破解文件

### Mod 管理

1. **内部 Mod**: 将 Mod 文件夹放入 `Mods/` 目录
2. **外部 Mod**: 使用右键菜单添加任意路径的 Mod
3. **Mod 配置**: 在 Mod 页面启用/禁用 Mod，添加备注
4. **启动游戏**: 在快速启动页面一键启动游戏

### 高级功能

- **自定义启动参数**: 编辑 ME3 启动参数
- **配置文件管理**: 查看和编辑生成的配置文件
- **外部 Mod 管理**: 支持添加、移除、备注外部 Mod
- **智能类型检测**: 自动识别不同类型的 Mod

## 🔧 开发

### 环境准备

```bash
# 克隆仓库
git clone https://github.com/QykXczj/Nmodm.git
cd Nmodm

# 安装依赖
python install_dependencies.py

# 运行开发版本
python main.py
```

### 代码结构

- **模块化设计**: 每个功能模块独立，便于维护
- **信号-槽模式**: 使用 Qt 信号槽进行组件通信
- **无模态对话框**: 避免使用弹窗，采用内联状态显示
- **配置管理**: 使用 JSON/TOML 格式存储配置

## 📚 文档

- [📖 软件使用指南](软件使用指南.md) - 详细的用户使用说明
- [🔧 项目使用指南](项目使用指南.md) - 开发者和贡献者指南
- [📦 打包使用说明](打包脚本更新说明.md) - 应用打包和部署指南

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [ME3](https://github.com/garyttierney/me3) - FROMSOFTWARE mod loader
- [PySide6](https://doc.qt.io/qtforpython/) - Python Qt bindings
- [PyDracula](https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6) - Modern GUI design inspiration

## 📞 支持

如果你觉得这个项目有用，请给它一个 ⭐️！

如果遇到问题，请在 [Issues](https://github.com/QykXczj/Nmodm/issues) 页面报告。