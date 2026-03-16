"""Realistic mock data for Chinese short drama pipeline prototype."""

import random

DRAMA_TITLES = [
    "逆袭千金：总裁别跑",
    "重生之都市修仙",
    "闪婚后大佬夫人马甲藏不住了",
]

EPISODE_TITLES = [
    "命运的转折", "真相浮出水面", "暗流涌动", "步步紧逼", "绝地反击",
    "破碎的谎言", "意外重逢", "危机四伏", "风暴前夕", "终极对决",
    "隐藏的秘密", "王者归来", "阴谋败露", "爱恨交织", "巅峰时刻",
    "黎明之前", "背叛与救赎", "命悬一线", "反转人生", "最终审判",
]

CHARACTERS = [
    {
        "name": "苏晚晴",
        "aliases": ["晚晴", "苏小姐", "苏总"],
        "description": "女主角，表面柔弱实则心思缜密的千金小姐，被陷害后逆袭归来",
        "role": "protagonist"
    },
    {
        "name": "陆景深",
        "aliases": ["陆总", "景深", "陆先生"],
        "description": "男主角，冷面总裁，外冷内热，暗中守护女主",
        "role": "protagonist"
    },
    {
        "name": "苏雅琪",
        "aliases": ["雅琪", "苏二小姐"],
        "description": "女配角/反派，苏晚晴同父异母的妹妹，心机深沉",
        "role": "antagonist"
    },
    {
        "name": "林浩宇",
        "aliases": ["林总", "浩宇"],
        "description": "男配角，苏晚晴前男友，后悔莫及",
        "role": "supporting"
    },
    {
        "name": "王妈",
        "aliases": ["王阿姨", "王妈妈"],
        "description": "苏家老仆人，忠心耿耿，知道很多秘密",
        "role": "supporting"
    },
    {
        "name": "陈秘书",
        "aliases": ["小陈", "陈助理"],
        "description": "陆景深的秘书，高效干练",
        "role": "minor"
    },
]

EMOTION_TYPES = [
    "平和", "愉悦", "喜悦", "狂喜", "满意",
    "不满", "愤怒", "暴怒", "暴走",
    "悲伤", "心碎", "绝望",
    "紧张", "恐惧", "震惊",
    "嘲讽", "轻蔑", "挑衅",
    "感动", "释然", "坚定",
]

HOOK_TYPES = [
    {"type": "suspense", "label": "悬念型", "desc": "关键信息未揭示"},
    {"type": "reversal", "label": "反转型", "desc": "剧情突变"},
    {"type": "emotional", "label": "情感型", "desc": "强烈情绪驱动"},
    {"type": "threat", "label": "威胁型", "desc": "危险/冲突升级"},
    {"type": "reveal", "label": "揭秘型", "desc": "部分揭示真相"},
    {"type": "choice", "label": "选择型", "desc": "角色面临抉择"},
]

SAMPLE_DIALOGUES = [
    [
        {"speaker": "苏晚晴", "text": "三年了，我终于回来了。", "emotion": "坚定", "score": 7},
        {"speaker": "旁白", "text": "苏晚晴站在苏氏集团大楼前，目光如炬。", "emotion": "平和", "score": 2},
        {"speaker": "陈秘书", "text": "苏小姐，陆总在三楼会议室等您。", "emotion": "平和", "score": 3},
        {"speaker": "苏晚晴", "text": "让他等着吧，我先去看看我的公司还剩下什么。", "emotion": "嘲讽", "score": 6},
    ],
    [
        {"speaker": "陆景深", "text": "苏晚晴，你以为回来就能改变什么？", "emotion": "平和", "score": 4},
        {"speaker": "苏晚晴", "text": "陆总，我不是来改变什么的。我是来拿回属于我的东西。", "emotion": "坚定", "score": 8},
        {"speaker": "陆景深", "text": "......", "emotion": "震惊", "score": 5},
        {"speaker": "苏雅琪", "text": "姐姐，你回来了？我还以为你再也不会回来了呢。", "emotion": "嘲讽", "score": 7},
        {"speaker": "苏晚晴", "text": "怎么，怕了？", "emotion": "挑衅", "score": 6},
    ],
    [
        {"speaker": "林浩宇", "text": "晚晴，对不起，当年是我错了。", "emotion": "悲伤", "score": 7},
        {"speaker": "苏晚晴", "text": "林浩宇，你的对不起不值一分钱。", "emotion": "愤怒", "score": 8},
        {"speaker": "林浩宇", "text": "我知道我没资格求你原谅，但是....", "emotion": "绝望", "score": 8},
        {"speaker": "苏晚晴", "text": "没有但是。你和苏雅琪联手害我的时候，想过今天吗？", "emotion": "暴怒", "score": 9},
        {"speaker": "王妈", "text": "小姐，别激动，他不值得。", "emotion": "心碎", "score": 6},
    ],
    [
        {"speaker": "陆景深", "text": "这份文件你看看。苏雅琪三年前伪造的证据，全在这里。", "emotion": "平和", "score": 3},
        {"speaker": "苏晚晴", "text": "你一直都知道？", "emotion": "震惊", "score": 8},
        {"speaker": "陆景深", "text": "我用了三年时间收集证据。", "emotion": "坚定", "score": 7},
        {"speaker": "苏晚晴", "text": "为什么帮我？", "emotion": "感动", "score": 7},
        {"speaker": "陆景深", "text": "因为......算了，你不需要知道原因。", "emotion": "紧张", "score": 5},
    ],
]

SAMPLE_HOOKS = [
    {
        "type": "suspense",
        "content": "苏晚晴打开保险箱，发现里面是一封来自已故母亲的信...",
        "attraction_score": 8,
        "translation_risk": "LOW",
        "risk_reason": "",
    },
    {
        "type": "reversal",
        "content": "陆景深突然出现在门口：'苏雅琪，游戏结束了。'",
        "attraction_score": 9,
        "translation_risk": "LOW",
        "risk_reason": "",
    },
    {
        "type": "emotional",
        "content": "苏晚晴跪在雨中，看着曾经的家化为灰烬...",
        "attraction_score": 7,
        "translation_risk": "MEDIUM",
        "risk_reason": "跪地场景在西方文化中情感冲击力不同",
    },
    {
        "type": "threat",
        "content": "'你只有24小时。过了明天，苏氏集团将不复存在。'",
        "attraction_score": 9,
        "translation_risk": "LOW",
        "risk_reason": "",
    },
    {
        "type": "reveal",
        "content": "DNA报告显示：苏晚晴才是苏家的亲生女儿，而苏雅琪...",
        "attraction_score": 10,
        "translation_risk": "LOW",
        "risk_reason": "",
    },
    {
        "type": "choice",
        "content": "苏晚晴看着桌上的两份协议：一份是和解，一份是开战。",
        "attraction_score": 8,
        "translation_risk": "LOW",
        "risk_reason": "",
    },
]

SCENE_DESCRIPTIONS = [
    "苏氏集团总部大楼，大理石大厅，金色灯光",
    "总裁办公室，落地窗外是城市夜景，暗色调",
    "豪华别墅客厅，水晶吊灯，紧张的气氛",
    "雨中的街道，霓虹灯倒影，悲伤的钢琴曲",
    "高级餐厅包厢，烛光摇曳，低声的爵士乐",
    "法庭内部，庄严肃穆，旁听席座无虚席",
    "医院走廊，白色灯光，紧急广播声",
    "苏家老宅花园，阳光明媚，鸟鸣声",
]


def generate_episode_data(episode_num: int) -> dict:
    """Generate realistic mock data for one episode."""
    dialogue_set = SAMPLE_DIALOGUES[episode_num % len(SAMPLE_DIALOGUES)]
    hook = SAMPLE_HOOKS[episode_num % len(SAMPLE_HOOKS)]
    scene = SCENE_DESCRIPTIONS[episode_num % len(SCENE_DESCRIPTIONS)]
    title = EPISODE_TITLES[episode_num % len(EPISODE_TITLES)]

    # Generate subtitle data
    subtitle_data = {
        "total_lines": len(dialogue_set),
        "duration": random.randint(180, 360),
        "asr_match_rate": round(random.uniform(0.92, 0.99), 3),
        "speakers_detected": len(set(d["speaker"] for d in dialogue_set)),
        "dialogues": dialogue_set,
    }

    # Generate character data for this episode
    ep_characters = list(set(d["speaker"] for d in dialogue_set if d["speaker"] != "旁白"))
    characters = []
    for name in ep_characters:
        char = next((c for c in CHARACTERS if c["name"] == name), None)
        if char:
            characters.append(char)
        else:
            characters.append({"name": name, "aliases": [], "description": "", "role": "unknown"})

    # Generate emotion data
    emotions = {
        "dialogues": [
            {
                "index": i,
                "speaker": d["speaker"],
                "text": d["text"],
                "emotion": d["emotion"],
                "score": d["score"],
                "audio_emotion": d["emotion"],
                "text_emotion": d["emotion"],
                "confidence": round(random.uniform(0.75, 0.98), 2),
            }
            for i, d in enumerate(dialogue_set)
        ],
        "peak_emotion": max(dialogue_set, key=lambda x: x["score"]),
        "average_intensity": round(sum(d["score"] for d in dialogue_set) / len(dialogue_set), 1),
    }

    # Detect reversal points
    reversals = []
    for i in range(1, len(dialogue_set)):
        prev = dialogue_set[i - 1]
        curr = dialogue_set[i]
        if abs(curr["score"] - prev["score"]) >= 3:
            reversals.append({
                "index": i,
                "from_emotion": prev["emotion"],
                "from_score": prev["score"],
                "to_emotion": curr["emotion"],
                "to_score": curr["score"],
                "delta": abs(curr["score"] - prev["score"]),
            })

    emotion_analysis = {
        "arc_type": random.choice(["man_in_a_hole", "icarus", "cinderella", "rags_to_riches"]),
        "peak_time": f"00:0{random.randint(2,4)}:{random.randint(10,50):02d}",
        "reversals": reversals,
        "average_intensity": emotions["average_intensity"],
    }

    # Generate script
    script_lines = [f"第 {episode_num + 1} 集 - \"{title}\"\n"]
    script_lines.append(f"场景：{scene}\n")
    script_lines.append("---\n")
    for d in dialogue_set:
        if d["speaker"] == "旁白":
            script_lines.append(f"[{d['text']}]\n")
        else:
            script_lines.append(f"{d['speaker']}（{d['emotion']} {d['score']}/10）：")
            script_lines.append(f"\"{d['text']}\"\n")
    script = "\n".join(script_lines)

    summary = f"第{episode_num + 1}集：{title}。" + "。".join(
        [f"{d['speaker']}{'说' if d['speaker'] != '旁白' else '：'}\"{d['text'][:10]}...\"" for d in dialogue_set[:2]]
    )

    hooks = {
        **hook,
        "episode": episode_num + 1,
        "continuity_score": round(random.uniform(6.0, 9.5), 1),
        "connects_to_next": True,
    }

    qa_result = {
        "overall_score": round(random.uniform(7.0, 9.5), 1),
        "asr_quality": round(random.uniform(8.0, 9.8), 1),
        "character_consistency": round(random.uniform(7.5, 9.5), 1),
        "emotion_calibration": round(random.uniform(7.0, 9.0), 1),
        "issues": [],
        "passed": True,
    }
    if random.random() < 0.2:
        qa_result["issues"].append("角色别名可能存在混淆，建议人工复核")
        qa_result["passed"] = False

    return {
        "title": title,
        "duration_seconds": subtitle_data["duration"],
        "subtitle_data": subtitle_data,
        "characters": characters,
        "emotions": emotions,
        "script": script,
        "summary": summary,
        "emotion_analysis": emotion_analysis,
        "hooks": hooks,
        "qa_result": qa_result,
    }
