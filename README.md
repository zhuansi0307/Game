# 甜妹拯救计划

现代都市写实恋爱视觉小说/互动探索游戏原型

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动游戏

```bash
python main.py
```

## 项目目录说明

```
game/
├── main.py                 # 游戏入口
├── requirements.txt         # 依赖列表
│
├── engine/                  # 游戏引擎核心
│   ├── __init__.py
│   ├── constants.py         # 常量定义（窗口尺寸、颜色等）
│   ├── app.py               # 应用主类
│   ├── scene_manager.py     # 场景管理器
│   ├── asset_manager.py     # 资源管理器
│   ├── save_system.py       # 存档系统
│   ├── game_state.py        # 游戏全局状态/时间系统
│   ├── time_system.py       # 时间检查辅助函数
│   ├── ui.py                # UI组件
│   ├── hotspot.py           # 热区系统
│   └── dialogue.py          # 对话系统
│
├── scenes/                  # 游戏场景
│   ├── __init__.py
│   ├── main_menu_scene.py   # 主菜单
│   ├── explore_scene.py     # 探索场景
│   ├── dialogue_scene.py   # 对话场景
│   ├── save_menu_scene.py   # 存档菜单
│   └── settings_scene.py   # 设置菜单
│
├── data/                    # 游戏数据
│   ├── scenes.json          # 场景配置
│   ├── dialogues.json      # 对话内容
│   ├── events.json          # 事件触发配置
│   └── save_default.json   # 默认存档模板
│
└── assets/                  # 资源文件
    ├── bg/                  # 背景图
    ├── ui/                  # UI图片
    ├── fonts/               # 字体
    └── audio/               # 音频
```

## 操作说明

### 鼠标操作
- **鼠标悬停**：查看热区提示
- **鼠标左键点击**：与热区交互/推进对话/切换时间按钮

### 快捷键
| 按键 | 功能 |
|------|------|
| `空格键` | 推进对话 |
| `ESC` | 返回主菜单/跳过对话 |
| `T` | 切换时间时段（探索场景） |
| `回车键` | 推进对话 |

### 时间系统
- 时间循环：`早上 → 中午 → 下午 → 晚上 → (循环)`
- 一周循环：`Monday → Sunday`
- 点击HUD中的时间按钮也可切换时段

## 新增场景指南

### 1. 在 scenes.json 中添加场景配置

```json
{
  "id": "new_scene",
  "title": "新场景标题",
  "background": "bg/your_image.png",
  "hotspots": [
    {
      "id": "hotspot_1",
      "rect": [x, y, width, height],
      "title": "热区标题",
      "desc": "热区描述",
      "target_scene": "another_scene",
      "target_dialogue": "dialogue_id",
      "discovered": false,
      "hidden": false
    }
  ]
}
```

### 2. 在 app.py 中注册新场景

```python
from scenes.explore_scene import ExploreScene

# 在 _register_scenes 方法中添加
self.scene_manager.register("new_scene", 
    ExploreScene(self.scene_manager, self.asset_manager, "new_scene"))
```

## 新增热区指南

在 `data/scenes.json` 中为现有场景添加热区：

```json
{
  "id": "your_hotspot",
  "rect": [x, y, width, height],
  "title": "显示标题",
  "desc": "悬停时显示的描述",
  "target_scene": "切换到其他场景",
  "target_dialogue": "或进入对话ID",
  "discovered": false,
  "hidden": false
}
```

热区配置说明：
- `rect`: 热区位置和大小 `[x, y, width, height]`
- `title`: 悬停时显示的标题
- `desc`: 悬停时显示的描述文字
- `target_scene`: 点击后切换到的场景ID
- `target_dialogue`: 点击后进入的对话ID
- `discovered`: 是否已发现（影响热区颜色）
- `hidden`: 是否隐藏（低透明度）

## 新增对话指南

### 1. 在 dialogues.json 中添加对话

```json
{
  "your_dialogue_id": [
    {"speaker": "角色名", "text": "对话内容1"},
    {"speaker": "角色名", "text": "对话内容2"}
  ]
}
```

### 2. 在热区配置中引用对话

```json
{
  "target_dialogue": "your_dialogue_id"
}
```

## 热区视觉风格

采用「光点式热区」设计：
- 默认只显示一个小型香槟金发光圆点，带呼吸闪烁效果
- 悬停时光点放大，显示标题小标签
- 悬停时在上方显示说明卡片（标题和描述）
- 已发现的热区圆点为淡绿色
- 隐藏热区默认透明度更低

## 时间系统使用

### 1. 配置场景不同时段背景

在 `data/scenes.json` 中：
```json
{
  "id": "living_room",
  "title": "大客厅",
  "time_variants": {
    "morning": "bg/大客厅早上.png",
    "noon": "bg/大客厅中午.png",
    "afternoon": "bg/大客厅下午.png",
    "evening": "bg/大客厅晚上.png"
  }
}
```

### 2. 事件条件触发

在 `data/events.json` 中配置：
```json
{
  "id": "special_event",
  "condition": {"time": "Monday_evening"},
  "action": {"type": "scene", "target_scene": "secret_room"}
}
```

条件类型：
- `time`: 具体时间键，如 `"Monday_noon"` 或 `["Monday", "Friday"]`
- `day`: 星期索引 0-6
- `period`: 时段索引 0-3
- `flag`: 需要设置的标记

## 技术规格

- 窗口分辨率：1920 x 1080
- 帧率：60 FPS
- Python 版本：3.8+
- 依赖库：pygame >= 2.5.0

## 开发说明

- 代码模块化设计，便于后续扩展
- 中文支持，使用 NotoSansSC 字体（如不存在则使用系统字体）
- 资源不存在时自动使用占位图，不会导致程序崩溃
- 所有核心模块都有中文注释

## 项目状态

当前版本为最小可玩闭环（MVP），包含：
- ✅ 主菜单界面
- ✅ 探索场景与热区交互
- ✅ 对话系统
- ✅ 场景切换
- ⏳ 存档系统（接口已实现，UI 待完善）
- ⏳ 设置系统（占位界面）

---

*愿这个项目能帮助你实现心中的故事。*