"""
常量定义模块
包含游戏窗口尺寸、帧率、颜色等基础常量
"""

# 窗口尺寸
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# 帧率
FPS = 60

# 颜色定义 - 现代都市写实恋爱视觉小说风格
# 深色系背景
COLOR_BG_DARK = (20, 22, 28)           # 深灰蓝背景
COLOR_BG_PANEL = (30, 32, 40)          # 面板背景

# 文本颜色
COLOR_TEXT = (245, 240, 235)           # 暖白色文字
COLOR_TEXT_MUTED = (140, 145, 155)     # 柔和灰色文字
COLOR_TEXT_DIALOGUE = (255, 255, 255)  # 对话框纯白文字

# 香槟金色系 - 现代优雅
COLOR_CHAMPAGNE = (207, 183, 152)      # 香槟金主色
COLOR_CHAMPAGNE_BRIGHT = (220, 198, 170)  # 香槟金亮色（hover状态）
COLOR_CHAMPAGNE_DIM = (160, 145, 120)  # 香槟金暗色

# 面板颜色
COLOR_PANEL = (25, 27, 35)            # 深色面板
COLOR_PANEL_BORDER = (60, 62, 72)      # 面板边框

# 热区颜色
COLOR_HOTSPOT_DEFAULT = (207, 183, 152, 150)   # 默认热区线（半透明）
COLOR_HOTSPOT_HOVER = (220, 198, 170, 255)      # 悬停热区线
COLOR_HOTSPOT_DISCOVERED = (150, 200, 150, 150) # 已发现热区（淡绿色）
COLOR_HOTSPOT_HIDDEN = (207, 183, 152, 50)      # 隐藏热区（低透明度）

# 对话框
COLOR_DIALOGUE_BG = (15, 17, 22)       # 对话框背景
COLOR_DIALOGUE_BORDER = (207, 183, 152)  # 对话框边框