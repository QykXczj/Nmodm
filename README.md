# Nmodm - 现代化游戏管理工具

<div align="center">

![Nmodm Logo](zwnr.ico)

**专为《艾尔登法环：黑夜君临》设计的现代化游戏管理工具**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)](https://pyside.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://windows.microsoft.com)

[English](README_EN.md) | 中文

</div>

## 📖 项目简介

Nmodm 是一款专为《艾尔登法环：黑夜君临》(Elden Ring: Nightreign) 设计的现代化游戏管理工具。它集成了 Mod 管理、局域网联机、工具下载、配置管理等多项功能，为玩家提供一站式的游戏增强体验。

🔗 **Nexus Mods**: [Nightreign Mod Manager](https://www.nexusmods.com/eldenringnightreign/mods/274)

## ✨ 核心特性

- 🎮 **游戏管理** - 自动检测游戏路径，一键配置启动参数
- 🔧 **ME3 工具集成** - 自动下载和管理 ME3 mod 工具
- 🎯 **智能 Mod 管理** - 自动识别 Mod 类型，实时生成配置文件
- 🌐 **局域网联机** - 基于 EasyTier 的虚拟局域网解决方案
- 🎨 **现代化界面** - 无边框设计，侧边栏导航，实时状态显示

## 🚀 快速开始

### 下载使用（推荐）

1. 访问 [Releases](../../releases) 页面下载最新版本
2. 解压到任意目录（建议英文路径）
3. 双击 `Nmodm.exe` 启动程序

### 从源码运行

```bash
# 克隆项目
git clone https://github.com/your-repo/Nmodm.git
cd Nmodm

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

## 💻 系统要求

- **操作系统**: Windows 10/11 (64位)
- **Python**: 3.8+ (源码运行时需要)
- **内存**: 4GB RAM (推荐 8GB)
- **依赖**: Visual C++ Redistributable 2015-2022, .NET Framework 4.7.2+

## 📚 文档

- 📖 [完整使用文档](docs/zh/USER_GUIDE.md)
- 🔧 [开发者指南](docs/zh/DEVELOPER_GUIDE.md)
- 📊 [版本历史](docs/zh/CHANGELOG.md)
- 🤝 [贡献指南](docs/zh/CONTRIBUTING.md)

## 🛠️ 技术栈

- **界面**: PySide6 (Qt6)
- **语言**: Python 3.8+
- **打包**: Nuitka, PyInstaller
- **集成工具**: ME3, EasyTier, OnlineFix

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！详见 [贡献指南](docs/CONTRIBUTING.md)

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)

## 🙏 致谢

- [ME3 项目](https://me3.readthedocs.io/) - Mod 管理工具
- [PySide6](https://pyside.org/) - GUI 框架
- [EasyTier](https://github.com/EasyTier/EasyTier) - 虚拟局域网
- 感谢所有贡献者和社区支持

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

[![GitHub stars](https://img.shields.io/github/stars/your-repo/Nmodm?style=social)](../../stargazers)
[![GitHub forks](https://img.shields.io/github/forks/your-repo/Nmodm?style=social)](../../network/members)

*"在黑夜君临的世界中，让技术为冒险赋能"*

</div>
