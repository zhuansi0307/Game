"""
游戏入口文件
只负责启动游戏应用，不包含业务逻辑
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.app import App


def main():
    """游戏入口函数"""
    print("=" * 50)
    print("  甜妹拯救计划")
    print("  Sweet Girl Rescue Plan")
    print("=" * 50)
    print()

    # 创建并运行应用
    app = App("甜妹拯救计划")
    app.run()


if __name__ == "__main__":
    main()