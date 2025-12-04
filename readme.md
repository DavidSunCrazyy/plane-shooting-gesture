Plane Shooting (Gesture Controlled)
=================================

简要说明
--------
这是一个使用 MediaPipe 手部追踪与 Pygame 结合的手势控制射击小游戏。玩家通过摄像头手势控制飞机的左右移动和开火：
- 拇指与食指靠近会加快射速（按拇指-食指距离映射）
- 张开手掌：允许开火；握拳：停止开火
- 每次开火为三连发（向左、中、右）；击倒敌人会恢复弹药

主要特性
--------
- 弹药系统（自动补充 + 击杀恢复）
- 三种敌人（weak / normal / tank），具有血量与分数
- 敌人上方显示血条
- 射速由拇指-食指间距控制（更接近 → 更快）

依赖
--------
- Python 3.8-3.12
- opencv-python
- mediapipe
- pygame

建议安装命令（PowerShell）
---------------------------
# 在项目根目录创建并激活虚拟环境（可选）
python -m venv .venv
& ./.venv/Scripts/Activate.ps1

# 安装依赖
pip install opencv-python mediapipe pygame

运行
----
在项目根目录执行：

```powershell
& ./.venv/Scripts/Activate.ps1
python main.py
```

（如果你习惯直接指定虚拟环境解释器，也可以使用：）

```powershell
& D:/Code/Python/plane-shooting/.venv/Scripts/python.exe d:/Code/Python/plane-shooting/main.py
```

主要文件说明
---------------
- `main.py` - 程序入口，初始化、主循环、渲染与碰撞逻辑。
- `entities.py` - 游戏实体：`Player`, `Enemy`, `Bullet`。
- `hand_utils.py` - 包含 `count_fingers`, `palm_openness`, `fingertip_distance`。
- `constants.py` - 屏幕尺寸与颜色等常量。

常用可调参数
--------------
- 射速映射：在 `main.py` 中修改 `min_cooldown`, `max_cooldown`、`tip_min_dist`, `tip_max_dist`。
- 弹药：`max_ammo`, `ammo_refill_rate`
- 敌人配置：在 `entities.py` 的 `enemy_types` 列表中调整每类的大小、血量、速度与分值。
- 三连发样式：在 `entities.Player.shoot_multiple` 修改 `patterns` 中的 `(vx, vy)` 值。

调试/常见问题
----------------
- 如果程序无法打开摄像头，确认其它应用（例如浏览器）未占用摄像头，或尝试 `cap = cv2.VideoCapture(0)` 中使用其它索引（0、1）。
- 若 MediaPipe 跟踪不稳定，调整 `min_detection_confidence` 和 `min_tracking_confidence` 值。
- 若子弹方向/速度不合适，修改 `shoot_multiple` 的速度向量，或在 `Bullet.update` 中使用浮点位置累积以获得更平滑轨迹。

下一步建议
-----------
- 我可以帮你把 `enemy_types` 提取到 `constants.py` 以方便调参。
- 如果想把 README 改为中英双语或包含运行演示 GIF，我也可以添加。

作者注
------
这是一个实验/学习项目。修改代码时请在虚拟环境中运行测试。欢迎告诉我你想调整的具体参数或新增玩法（如敌人发射、子弹穿透等）。
