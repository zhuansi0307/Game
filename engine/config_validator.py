"""
内容配置校验
启动时检查 JSON 配置之间的引用，提前暴露缺失资源和断链。
"""


def validate_content_references(asset_manager, scene_manager=None):
    """校验场景、热区、任务、过场和事件配置引用。"""
    warnings = []

    scenes_data = asset_manager.load_scenes()
    dialogues = asset_manager.load_dialogues()
    tasks_data = asset_manager.load_tasks()
    cutscenes_data = asset_manager.load_cutscenes()
    events_data = asset_manager.load_events()

    scenes = scenes_data.get("scenes", [])
    tasks = tasks_data.get("tasks", [])
    cutscenes = cutscenes_data.get("cutscenes", [])
    events = events_data.get("events", [])

    scene_ids = {scene.get("id") for scene in scenes if scene.get("id")}
    dialogue_ids = set(dialogues.keys())
    cutscene_ids = {cutscene.get("id") for cutscene in cutscenes if cutscene.get("id")}
    registered_scene_ids = set(scene_manager.scenes.keys()) if scene_manager else set()
    valid_scene_ids = scene_ids | registered_scene_ids

    for scene in scenes:
        scene_id = scene.get("id", "<unknown>")
        if registered_scene_ids and scene_id not in registered_scene_ids:
            warnings.append(f"场景未注册: {scene_id}")

        for period, bg_path in scene.get("time_variants", {}).items():
            if bg_path and not asset_manager.get_asset_path(bg_path).exists():
                warnings.append(f"场景 {scene_id} 的 {period} 背景不存在: {bg_path}")

        bg_path = scene.get("background")
        if bg_path and not asset_manager.get_asset_path(bg_path).exists():
            warnings.append(f"场景 {scene_id} 背景不存在: {bg_path}")

        for hotspot in scene.get("hotspots", []):
            hotspot_id = hotspot.get("id", "<unknown>")
            target_scene = hotspot.get("target_scene")
            target_dialogue = hotspot.get("target_dialogue")

            if target_scene and target_scene not in valid_scene_ids:
                warnings.append(f"热区 {scene_id}.{hotspot_id} 目标场景不存在: {target_scene}")
            if target_dialogue and target_dialogue not in dialogue_ids:
                warnings.append(f"热区 {scene_id}.{hotspot_id} 目标对话不存在: {target_dialogue}")

    for task in tasks:
        task_id = task.get("id", "<unknown>")
        trigger_scene = task.get("trigger", {}).get("scene")
        if trigger_scene and trigger_scene not in valid_scene_ids:
            warnings.append(f"任务 {task_id} 触发场景不存在: {trigger_scene}")

        for step in task.get("steps", []):
            step_no = step.get("step", "?")
            dialogue_id = step.get("dialogue_id")
            cutscene_id = step.get("cutscene_id")
            target_scene = step.get("target_scene")
            background = step.get("background")

            if dialogue_id and dialogue_id not in dialogue_ids:
                warnings.append(f"任务 {task_id} 第 {step_no} 步对话不存在: {dialogue_id}")
            if cutscene_id and cutscene_id not in cutscene_ids:
                warnings.append(f"任务 {task_id} 第 {step_no} 步过场不存在: {cutscene_id}")
            if target_scene and target_scene not in valid_scene_ids:
                warnings.append(f"任务 {task_id} 第 {step_no} 步目标场景不存在: {target_scene}")
            if background and not asset_manager.get_asset_path(background).exists():
                warnings.append(f"任务 {task_id} 第 {step_no} 步选择背景不存在: {background}")

            for choice in step.get("choices", []):
                choice_cutscene_id = choice.get("cutscene_id")
                if choice_cutscene_id and choice_cutscene_id not in cutscene_ids:
                    warnings.append(f"任务 {task_id} 第 {step_no} 步选项过场不存在: {choice_cutscene_id}")

    for cutscene in cutscenes:
        cutscene_id = cutscene.get("id", "<unknown>")
        audio_path = cutscene.get("audio")
        if audio_path and not asset_manager.get_asset_path(audio_path).exists():
            warnings.append(f"过场 {cutscene_id} 音频不存在: {audio_path}")

        if cutscene.get("type") == "video":
            video_path = cutscene.get("video")
            if video_path and not asset_manager.get_asset_path(video_path).exists():
                warnings.append(f"过场 {cutscene_id} 视频不存在: {video_path}")
        elif cutscene.get("type") == "image":
            for frame in cutscene.get("frames", []):
                image_path = frame.get("image")
                if image_path and not asset_manager.get_asset_path(image_path).exists():
                    warnings.append(f"过场 {cutscene_id} 图片帧不存在: {image_path}")

    for event in events:
        event_id = event.get("id", "<unknown>")
        action = event.get("action", {})
        target_scene = action.get("target_scene")
        dialogue_id = action.get("dialogue_id")

        if target_scene and target_scene not in valid_scene_ids:
            warnings.append(f"事件 {event_id} 目标场景不存在: {target_scene}")
        if dialogue_id and dialogue_id not in dialogue_ids:
            warnings.append(f"事件 {event_id} 目标对话不存在: {dialogue_id}")

    if warnings:
        print(f"[配置校验] 发现 {len(warnings)} 个引用问题：")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("[配置校验] 未发现引用问题")

    return warnings
