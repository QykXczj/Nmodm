#!/usr/bin/env python3
"""
Nmodm - 现代化游戏管理工具
主入口文件
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from src.i18n import set_language
from src.i18n.language_switcher import load_language_preference


def main():
    """主函数"""
    try:
        # 加载用户保存的语言偏好
        preferred_language = load_language_preference()
        set_language(preferred_language)

        # 创建并运行应用
        app = create_app()
        sys.exit(app.run())
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()