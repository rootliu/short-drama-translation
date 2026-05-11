# AI评书艺人：评估引擎实现设计

> 爽度值/Hook强度/角色一致性的完整计算逻辑（Python伪代码）
> 日期：2026-05-10

---

## 1. 概述

评估引擎是改编系统的核心量化组件，负责对分镜剧本进行多维度自动化评估。基于以下理论支撑：

- **爽度值**：Zimmerman(2026) Volume + 自定义公式
- **Pivot强度**：Schulz(2024) JSD散度
- **Hook强度**：Schulz(2024) Suspense信息熵
- **角色一致性**：Goldfarb-Tarrant(2020) Character Consistency
- **对白自然度**：规则+LLM混合评估

---

## 2. 数据结构定义

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math

class EmotionDimension(str, Enum):
    """8维情感模型"""
    ANGER = "anger"
    SADNESS = "sadness"
    JOY = "joy"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    OPPRESSION = "oppression"   # 短剧特有：蓄压维度
    CATHARSIS = "catharsis"     # 短剧特有：释放维度

# 情感分组（用于爽度值计算）
BUILDUP_DIMENSIONS = {EmotionDimension.OPPRESSION, EmotionDimension.ANGER,
                      EmotionDimension.SADNESS, EmotionDimension.DISGUST}
RELEASE_DIMENSIONS = {EmotionDimension.JOY, EmotionDimension.CATHARSIS,
                      EmotionDimension.SURPRISE}

@dataclass
class EmotionVector:
    """8维情感向量"""
    anger: float = 0.0
    sadness: float = 0.0
    joy: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    oppression: float = 0.0
    catharsis: float = 0.0

    def to_dict(self) -> dict:
        return {dim.value: getattr(self, dim.value) for dim in EmotionDimension}

    def to_list(self) -> list[float]:
        return [getattr(self, dim.value) for dim in EmotionDimension]

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionVector":
        return cls(**{k: d.get(k, 0.0) for k in [e.value for e in EmotionDimension]})

    @property
    def buildup_intensity(self) -> float:
        """蓄压维度强度"""
        return sum(getattr(self, d.value) for d in BUILDUP_DIMENSIONS)

    @property
    def release_intensity(self) -> float:
        """释放维度强度"""
        return sum(getattr(self, d.value) for d in RELEASE_DIMENSIONS)

    @property
    def total_intensity(self) -> float:
        """总情感强度"""
        return sum(self.to_list())

    def dominant_emotion(self) -> tuple[str, float]:
        """主导情感"""
        d = self.to_dict()
        key = max(d, key=d.get)
        return key, d[key]


@dataclass
class ShotData:
    """单个镜头数据"""
    shot_id: str
    duration: float               # 秒
    shot_size: str                # extreme_long..insert
    camera_move: str              # static..orbit
    angle: str                    # eye_level..bird_eye
    subject: str
    action: str
    dialogue: Optional[str] = None
    narration: Optional[str] = None
    emotion_tag: EmotionVector = field(default_factory=EmotionVector)
    time_start: float = 0.0       # 在集内的起始秒
    time_end: float = 0.0


@dataclass
class SceneData:
    """场景数据"""
    scene_id: str
    scene_name: str
    time_range: str
    location: str
    shots: list[ShotData] = field(default_factory=list)


@dataclass
class EpisodeData:
    """单集数据"""
    episode_number: int
    title: str
    duration_target: str
    scenes: list[SceneData] = field(default_factory=list)
    hook_ending: dict = field(default_factory=dict)
    mock_subtitle: list[dict] = field(default_factory=list)

    @property
    def all_shots(self) -> list[ShotData]:
        """所有镜头的扁平列表"""
        shots = []
        for scene in self.scenes:
            shots.extend(scene.shots)
        return shots
```

---

## 3. 爽度值计算引擎

### 3.1 核心公式

```python
def calculate_shuang(episode: EpisodeData) -> dict:
    """
    计算集级爽度值。
    
    shuang(t) = |E_release(t) - E_buildup(t-δ)| × trigger_quality(t) × pacing_bonus(t)
    
    其中:
      E_release(t) = 释放维度情感强度 at shot t
      E_buildup(t-δ) = 蓄压维度情感强度 at shot t-δ
      trigger_quality = Plot Twist质量（JSD度量）
      pacing_bonus = 节奏奖励（反转间隔在最优范围内时）
      δ = 蓄压到释放的镜头间隔
    """
    shots = episode.all_shots
    if len(shots) < 2:
        return {"shuang_score": 0, "pivot_points": [], "avg_delta": 0}
    
    pivot_points = []
    max_shuang = 0
    
    for i in range(1, len(shots)):
        current = shots[i]
        # 在当前镜头之前的镜头中寻找蓄压峰值
        search_start = max(0, i - 8)  # 最多回溯8个镜头
        buildup_shots = shots[search_start:i]
        
        if not buildup_shots:
            continue
        
        # 找到蓄压最高的镜头
        max_buildup_idx = max(
            range(len(buildup_shots)),
            key=lambda j: buildup_shots[j].emotion_tag.buildup_intensity
        )
        buildup_shot = buildup_shots[max_buildup_idx]
        delta = i - (search_start + max_buildup_idx)
        
        # 计算情感落差
        e_release = current.emotion_tag.release_intensity
        e_buildup = buildup_shot.emotion_tag.buildup_intensity
        emotion_delta = abs(e_release - e_buildup)
        
        # Trigger质量（简化版：基于情感突变程度）
        trigger_quality = calculate_trigger_quality(
            buildup_shot.emotion_tag, current.emotion_tag
        )
        
        # 节奏奖励
        pacing_bonus = calculate_pacing_bonus(delta)
        
        # 爽度值
        shuang = emotion_delta * trigger_quality * pacing_bonus
        
        if shuang > max_shuang:
            max_shuang = shuang
        
        if emotion_delta >= 3.0:  # 阈值：认为是有效的Pivot点
            pivot_points.append({
                "shot_index": i,
                "shot_id": current.shot_id,
                "time": f"{int(current.time_start // 60)}:{int(current.time_start % 60):02d}",
                "from_emotion": buildup_shot.emotion_tag.dominant_emotion(),
                "to_emotion": current.emotion_tag.dominant_emotion(),
                "e_buildup": round(e_buildup, 1),
                "e_release": round(e_release, 1),
                "delta": round(emotion_delta, 1),
                "trigger_quality": round(trigger_quality, 2),
                "pacing_bonus": round(pacing_bonus, 2),
                "shuang_value": round(shuang, 1),
            })
    
    # 集级爽度值 = 最大单次爽度 + 所有Pivot的加权平均
    avg_pivot_shuang = (
        sum(p["shuang_value"] for p in pivot_points) / len(pivot_points)
        if pivot_points else 0
    )
    
    # 最终爽度值（0-10分制）
    raw_score = max_shuang * 0.6 + avg_pivot_shuang * 0.4
    normalized_score = min(10.0, raw_score / 3.0)  # 归一化到0-10
    
    return {
        "shuang_score": round(normalized_score, 1),
        "max_single_shuang": round(max_shuang, 1),
        "avg_pivot_shuang": round(avg_pivot_shuang, 1),
        "pivot_count": len(pivot_points),
        "pivot_points": pivot_points,
    }
```

### 3.2 Trigger质量计算

```python
def calculate_trigger_quality(before: EmotionVector, after: EmotionVector) -> float:
    """
    计算trigger质量，基于两个情感分布之间的JSD散度。
    
    JSD(P ‖ Q) = 0.5 * KL(P ‖ M) + 0.5 * KL(Q ‖ M)
    其中 M = 0.5 * (P + Q)
    
    值域 [0, 1]，越大表示情感变化越大（trigger质量越高）。
    """
    p = normalize_distribution(before.to_list())
    q = normalize_distribution(after.to_list())
    
    # M = 0.5 * (P + Q)
    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]
    
    # JSD
    jsd = 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)
    
    # 归一化到 [0, 1]（使用log2时JSD最大值为1）
    return min(1.0, jsd)


def normalize_distribution(values: list[float]) -> list[float]:
    """将非负值列表归一化为概率分布"""
    total = sum(values)
    if total == 0:
        n = len(values)
        return [1.0 / n] * n
    return [v / total for v in values]


def kl_divergence(p: list[float], q: list[float]) -> float:
    """KL散度，D_KL(P ‖ Q)"""
    eps = 1e-10  # 避免log(0)
    return sum(pi * math.log2((pi + eps) / (qi + eps)) for pi, qi in zip(p, q))
```

### 3.3 节奏奖励

```python
def calculate_pacing_bonus(delta: int) -> float:
    """
    节奏奖励：反转间隔在最优范围内给额外加分。
    
    最优间隔：3-5个镜头（对应短剧中10-20秒）
    太快（1-2个镜头）：观众来不及感受蓄压 → bonus降低
    太慢（>7个镜头）：节奏拖沓 → bonus降低
    
    返回 [0.5, 1.5]
    """
    if delta <= 0:
        return 0.5
    elif delta <= 2:
        return 0.8   # 太快
    elif 3 <= delta <= 5:
        return 1.5   # 最优区间
    elif delta == 6:
        return 1.2
    elif delta == 7:
        return 1.0
    else:
        return 0.7   # 太慢
```

---

## 4. Hook强度计算引擎

### 4.1 Suspense（悬念）度量

```python
def calculate_hook_strength(episode: EpisodeData) -> dict:
    """
    基于Schulz(2024)的Suspense度量计算Hook强度。
    
    Suspense(t) = H(P(s_{t+1}|S_t))
    
    在短剧中，我们评估集尾Hook的3个维度：
    1. 信息悬念：未解决冲突的信息量
    2. 情感悬念：集尾情感是否在高位被截断
    3. 新悬念：是否引入了新信息
    """
    hook = episode.hook_ending
    shots = episode.all_shots
    
    if not hook or not shots:
        return {"hook_strength": 0, "dimensions": {}}
    
    # 1. 信息悬念 (0-5)
    info_suspense = calculate_information_suspense(hook)
    
    # 2. 情感悬念 (0-5)
    emotional_suspense = calculate_emotional_suspense(shots)
    
    # 3. 新悬念 (0-5)
    novelty_suspense = calculate_novelty_suspense(hook)
    
    # 综合Hook强度 = 加权平均
    hook_strength = (
        info_suspense * 0.4 +
        emotional_suspense * 0.35 +
        novelty_suspense * 0.25
    )
    
    return {
        "hook_strength": round(hook_strength, 1),
        "hook_type": hook.get("type", "unknown"),
        "dimensions": {
            "information_suspense": round(info_suspense, 1),
            "emotional_suspense": round(emotional_suspense, 1),
            "novelty_suspense": round(novelty_suspense, 1),
        },
        "cut_point": hook.get("cut_point", ""),
        "continuity_to_next": hook.get("continuity_to_next", ""),
    }


def calculate_information_suspense(hook: dict) -> float:
    """
    信息悬念：未解决冲突数量 × 每个冲突的信息量
    高分 = 多个未解决的冲突/问题
    """
    unresolved = hook.get("information_unresolved", [])
    count = len(unresolved)
    
    if count == 0:
        return 1.0
    elif count == 1:
        return 2.5
    elif count == 2:
        return 3.5
    elif count >= 3:
        return 4.5
    
    return 2.0


def calculate_emotional_suspense(shots: list[ShotData]) -> float:
    """
    情感悬念：集尾最后几个镜头的情感强度是否在高位被截断。
    
    理想状态：集尾情感强度 ≥ 6/10 时截断 → 高悬念
    """
    if not shots:
        return 0
    
    # 取最后3个镜头的平均情感强度
    last_n = min(3, len(shots))
    last_shots = shots[-last_n:]
    avg_intensity = sum(s.emotion_tag.total_intensity for s in last_shots) / last_n
    
    # 归一化到 0-5
    # 完全无情感 (0) → 0分
    # 情感极强 (max ~40) → 5分
    normalized = min(5.0, avg_intensity / 8.0)
    
    return normalized


def calculate_novelty_suspense(hook: dict) -> float:
    """
    新悬念：集尾是否引入了新信息/新冲突。
    """
    new_info = hook.get("new_information", "")
    
    if not new_info:
        return 0.5
    
    # 简单规则：有新信息基础分2.5，根据信息量加权
    score = 2.5
    if len(new_info) > 20:  # 较长的描述通常意味着更多信息
        score = 3.5
    if len(new_info) > 50:
        score = 4.5
    
    return score
```

---

## 5. 角色一致性计算引擎

```python
def calculate_character_consistency(
    episode: EpisodeData,
    character_cards: list[dict]
) -> dict:
    """
    角色一致性检查：检查剧本中每个角色的言行是否符合角色卡定义。
    
    consistency = 
      0.3 × speech_style_match  (台词风格)
      + 0.3 × behavior_match    (行为模式)
      + 0.2 × emotion_match     (情感表达)
      + 0.2 × visual_match      (视觉设定)
    """
    results = {}
    
    for card in character_cards:
        char_name = card["name"]
        char_aliases = card.get("aliases", [])
        all_names = [char_name] + char_aliases
        
        # 收集该角色的所有镜头
        char_shots = []
        for shot in episode.all_shots:
            if shot.subject in all_names:
                char_shots.append(shot)
            elif shot.dialogue and any(name in shot.dialogue for name in all_names):
                char_shots.append(shot)
        
        if not char_shots:
            continue
        
        # 1. 台词风格匹配 (基于规则)
        speech_score = evaluate_speech_consistency(char_shots, card)
        
        # 2. 行为模式匹配 (基于规则)
        behavior_score = evaluate_behavior_consistency(char_shots, card)
        
        # 3. 情感表达匹配 (基于规则)
        emotion_score = evaluate_emotion_consistency(char_shots, card)
        
        # 4. 视觉设定匹配 (基于规则)
        visual_score = evaluate_visual_consistency(char_shots, card)
        
        overall = (
            speech_score * 0.3 +
            behavior_score * 0.3 +
            emotion_score * 0.2 +
            visual_score * 0.2
        )
        
        results[char_name] = {
            "overall": round(overall, 2),
            "speech_style": round(speech_score, 2),
            "behavior": round(behavior_score, 2),
            "emotion_expression": round(emotion_score, 2),
            "visual": round(visual_score, 2),
            "shot_count": len(char_shots),
            "issues": collect_consistency_issues(char_shots, card),
        }
    
    # 整体一致性 = 所有角色的加权平均
    if results:
        avg_consistency = sum(r["overall"] for r in results.values()) / len(results)
    else:
        avg_consistency = 0
    
    return {
        "character_consistency": round(avg_consistency, 2),
        "per_character": results,
    }


def evaluate_speech_consistency(shots: list[ShotData], card: dict) -> float:
    """
    台词风格一致性检查（规则引擎）。
    
    检查项：
    - 对白长度是否符合角色（总裁角色通常用短句，配角可以用长句）
    - 是否包含角色的口头禅
    - 对白风格是否符合定义（如"嘲讽时嘴角微挑，声音变甜"）
    
    返回 0-1
    """
    score = 0.8  # 基础分
    speech_style = card.get("speech_style", {})
    catchphrases = speech_style.get("catchphrases", [])
    
    dialogue_shots = [s for s in shots if s.dialogue]
    if not dialogue_shots:
        return 0.7  # 无台词，默认通过
    
    # 检查1：对白长度（总裁/主角通常用短句）
    avg_len = sum(len(s.dialogue) for s in dialogue_shots) / len(dialogue_shots)
    if card.get("role") == "protagonist":
        if avg_len <= 15:
            score += 0.1  # 短句加分
        elif avg_len > 25:
            score -= 0.15  # 太长扣分
    
    # 检查2：口头禅出现
    for cp in catchphrases:
        for s in dialogue_shots:
            if cp in s.dialogue:
                score += 0.05
                break
    
    # 检查3：dialogue_style标记是否与角色卡一致
    # （需要LLM辅助，规则引擎先给基础分）
    
    return min(1.0, max(0.0, score))


def evaluate_behavior_consistency(shots: list[ShotData], card: dict) -> float:
    """行为模式一致性（规则引擎基础版）"""
    # 基础分：假设一致
    score = 0.85
    personality = card.get("personality", [])
    
    # 如果角色是"隐忍"型但行动描述中有"大声斥责"，扣分
    action_keywords = set()
    for s in shots:
        if s.action:
            action_keywords.update(s.action.split())
    
    # 简单关键词匹配（实际应用中使用LLM评估）
    if "隐忍" in personality and "暴怒" in str(action_keywords):
        score -= 0.1
    if "高冷" in personality and "热情" in str(action_keywords):
        score -= 0.1
    
    return min(1.0, max(0.0, score))


def evaluate_emotion_consistency(shots: list[ShotData], card: dict) -> float:
    """情感表达一致性"""
    emotion_expr = card.get("emotion_expression", {})
    if not emotion_expr:
        return 0.8  # 无定义，默认通过
    
    # 检查情感标签中的描述是否与角色卡一致
    # 基础版：检查情感强度是否在合理范围内
    score = 0.85
    return min(1.0, max(0.0, score))


def evaluate_visual_consistency(shots: list[ShotData], card: dict) -> float:
    """视觉设定一致性（检查道具等）"""
    appearance = card.get("appearance", {})
    if not appearance:
        return 0.8
    
    score = 0.85
    # 检查props_in_frame是否包含角色的标志性道具
    return min(1.0, max(0.0, score))


def collect_consistency_issues(shots: list[ShotData], card: dict) -> list[str]:
    """收集一致性问题"""
    issues = []
    
    dialogue_shots = [s for s in shots if s.dialogue]
    if dialogue_shots:
        avg_len = sum(len(s.dialogue) for s in dialogue_shots) / len(dialogue_shots)
        if card.get("role") == "protagonist" and avg_len > 25:
            issues.append(f"{card['name']}的对白平均长度{avg_len:.0f}字，偏长（建议≤15字）")
    
    return issues
```

---

## 6. 对白自然度评估

```python
def evaluate_dialogue_naturalness(episode: EpisodeData) -> dict:
    """
    对白自然度评估（规则引擎 + 指标统计）。
    
    评估维度：
    - 句子长度分布
    - 对白节奏（间隔）
    - 金句密度
    - 旁白占比
    """
    shots = episode.all_shots
    dialogue_shots = [s for s in shots if s.dialogue]
    narration_shots = [s for s in shots if s.narration]
    
    if not dialogue_shots:
        return {"dialogue_naturalness": 5.0, "notes": "无对白"}
    
    # 1. 句子长度分析
    lengths = [len(s.dialogue) for s in dialogue_shots]
    avg_length = sum(lengths) / len(lengths)
    max_length = max(lengths)
    
    length_score = 10.0
    if avg_length > 20:
        length_score -= 2.0
    if avg_length > 30:
        length_score -= 3.0
    if max_length > 40:
        length_score -= 1.0
    
    # 2. 旁白占比
    total_comm = len(dialogue_shots) + len(narration_shots)
    narration_ratio = len(narration_shots) / total_comm if total_comm > 0 else 0
    
    narration_score = 10.0
    if narration_ratio > 0.4:
        narration_score -= 2.0  # 旁白过多
    if narration_ratio > 0.6:
        narration_score -= 3.0
    
    # 3. 对白节奏（短句间隔是否紧凑）
    rhythm_score = 8.0  # 基础分
    for i in range(1, len(dialogue_shots)):
        gap = dialogue_shots[i].time_start - dialogue_shots[i-1].time_end
        if gap > 5.0:  # 对白间隔超过5秒
            rhythm_score -= 0.5
    rhythm_score = max(3.0, rhythm_score)
    
    # 综合
    naturalness = (length_score * 0.4 + narration_score * 0.3 + rhythm_score * 0.3)
    
    return {
        "dialogue_naturalness": round(min(10, naturalness), 1),
        "avg_sentence_length": round(avg_length, 1),
        "max_sentence_length": max_length,
        "dialogue_count": len(dialogue_shots),
        "narration_count": len(narration_shots),
        "narration_ratio": round(narration_ratio, 2),
        "notes": generate_dialogue_notes(avg_length, narration_ratio, max_length),
    }


def generate_dialogue_notes(avg_len: float, narration_ratio: float, max_len: int) -> list[str]:
    notes = []
    if avg_len > 20:
        notes.append(f"平均句长{avg_len:.0f}字，建议控制在15字以内")
    if narration_ratio > 0.4:
        notes.append(f"旁白占比{narration_ratio:.0%}，偏高，建议用画面替代")
    if max_len > 40:
        notes.append(f"最长句子{max_len}字，考虑拆分")
    if not notes:
        notes.append("对白节奏良好")
    return notes
```

---

## 7. 视觉可行性评估

```python
def evaluate_visual_feasibility(episode: EpisodeData) -> dict:
    """
    视觉可行性评估：评估分镜在低成本拍摄条件下的可实现性。
    
    评估项：
    - 场景数量（越少越容易拍）
    - 特殊镜头难度（环绕/手持跟踪等）
    - 道具复杂度
    - 换场频率
    """
    shots = episode.all_shots
    scenes = episode.scenes
    
    score = 10.0
    
    # 1. 场景数量
    scene_count = len(scenes)
    if scene_count > 5:
        score -= 1.0
    if scene_count > 8:
        score -= 2.0
    
    # 2. 镜头运动难度
    difficult_moves = {"tracking", "orbit", "crane_up", "crane_down", "handheld"}
    difficult_count = sum(1 for s in shots if s.camera_move in difficult_moves)
    if difficult_count > len(shots) * 0.3:
        score -= 1.5
    
    # 3. 景别多样性（适中最好）
    sizes = set(s.shot_size for s in shots)
    if len(sizes) < 3:
        score -= 0.5  # 太单调
    if len(sizes) > 6:
        score -= 0.5  # 太复杂
    
    # 4. 大特写/插入镜头数量（需要特殊设备）
    close_ups = sum(1 for s in shots if s.shot_size in {"extreme_close", "insert"})
    if close_ups > len(shots) * 0.4:
        score -= 0.5
    
    score = max(3.0, min(10.0, score))
    
    return {
        "visual_feasibility": round(score, 1),
        "scene_count": scene_count,
        "difficult_shots": difficult_count,
        "shot_variety": len(sizes),
        "notes": generate_feasibility_notes(scene_count, difficult_count, len(shots)),
    }


def generate_feasibility_notes(scenes: int, difficult: int, total: int) -> list[str]:
    notes = []
    if scenes > 5:
        notes.append(f"{scenes}个场景，换场成本高，建议合并")
    if total > 0 and difficult / total > 0.3:
        notes.append(f"复杂运镜占比{difficult}/{total}，建议简化部分镜头")
    if not notes:
        notes.append("拍摄可行性良好")
    return notes
```

---

## 8. 综合评估引擎

```python
def run_full_evaluation(
    episode: EpisodeData,
    character_cards: list[dict],
    emotion_target: dict
) -> dict:
    """
    运行完整的多维度评估。
    
    达标阈值：
    - shuang_score >= 7.0
    - hook_strength >= 3.5
    - character_consistency >= 0.85
    - dialogue_naturalness >= 6.0
    - visual_feasibility >= 6.0
    """
    THRESHOLDS = {
        "shuang_score": 7.0,
        "hook_strength": 3.5,
        "character_consistency": 0.85,
        "dialogue_naturalness": 6.0,
        "visual_feasibility": 6.0,
    }
    
    # 各维度评估
    shuang_result = calculate_shuang(episode)
    hook_result = calculate_hook_strength(episode)
    consistency_result = calculate_character_consistency(episode, character_cards)
    dialogue_result = evaluate_dialogue_naturalness(episode)
    visual_result = evaluate_visual_feasibility(episode)
    
    # 综合评分
    dimensions = {
        "shuang_score": shuang_result["shuang_score"],
        "hook_strength": hook_result["hook_strength"],
        "character_consistency": consistency_result["character_consistency"],
        "dialogue_naturalness": dialogue_result["dialogue_naturalness"],
        "visual_feasibility": visual_result["visual_feasibility"],
    }
    
    # 检查是否达标
    suggestions = []
    all_passed = True
    
    for dim, value in dimensions.items():
        threshold = THRESHOLDS[dim]
        if value < threshold:
            all_passed = False
            suggestions.append(generate_suggestion(dim, value, threshold))
    
    # 总体评分 = 加权平均（归一化到0-10）
    overall = (
        dimensions["shuang_score"] * 0.25 +
        dimensions["hook_strength"] * 2.0 * 0.20 +  # hook满分5，归一化到10
        dimensions["character_consistency"] * 10.0 * 0.20 +  # 0-1 → 0-10
        dimensions["dialogue_naturalness"] * 0.15 +
        dimensions["visual_feasibility"] * 0.20
    )
    
    return {
        "overall_score": round(overall, 1),
        "passed": all_passed,
        "dimensions": {
            "shuang": {
                "value": shuang_result["shuang_score"],
                "threshold": THRESHOLDS["shuang_score"],
                "passed": shuang_result["shuang_score"] >= THRESHOLDS["shuang_score"],
                "details": shuang_result,
            },
            "hook": {
                "value": hook_result["hook_strength"],
                "threshold": THRESHOLDS["hook_strength"],
                "passed": hook_result["hook_strength"] >= THRESHOLDS["hook_strength"],
                "details": hook_result,
            },
            "consistency": {
                "value": consistency_result["character_consistency"],
                "threshold": THRESHOLDS["character_consistency"],
                "passed": consistency_result["character_consistency"] >= THRESHOLDS["character_consistency"],
                "details": consistency_result,
            },
            "dialogue": {
                "value": dialogue_result["dialogue_naturalness"],
                "threshold": THRESHOLDS["dialogue_naturalness"],
                "passed": dialogue_result["dialogue_naturalness"] >= THRESHOLDS["dialogue_naturalness"],
                "details": dialogue_result,
            },
            "visual": {
                "value": visual_result["visual_feasibility"],
                "threshold": THRESHOLDS["visual_feasibility"],
                "passed": visual_result["visual_feasibility"] >= THRESHOLDS["visual_feasibility"],
                "details": visual_result,
            },
        },
        "suggestions": suggestions,
    }


def generate_suggestion(dimension: str, value: float, threshold: float) -> dict:
    """生成改进建议"""
    gap = threshold - value
    suggestions_map = {
        "shuang_score": {
            "target_agent": "screenplay",
            "issue": f"爽度值{value:.1f}，低于阈值{threshold}",
            "suggestion": "增加Pivot点的delta值，或在蓄压阶段加深oppression强度",
        },
        "hook_strength": {
            "target_agent": "hook",
            "issue": f"Hook强度{value:.1f}，低于阈值{threshold}",
            "suggestion": "增加未解决冲突数量，或在集尾引入新悬念",
        },
        "character_consistency": {
            "target_agent": "screenplay",
            "issue": f"角色一致性{value:.2f}，低于阈值{threshold}",
            "suggestion": "检查对白是否符合角色卡的说话风格和口头禅",
        },
        "dialogue_naturalness": {
            "target_agent": "screenplay",
            "issue": f"对白自然度{value:.1f}，低于阈值{threshold}",
            "suggestion": "缩短长句至15字以内，减少旁白占比",
        },
        "visual_feasibility": {
            "target_agent": "screenplay",
            "issue": f"视觉可行性{value:.1f}，低于阈值{threshold}",
            "suggestion": "合并场景，简化复杂运镜",
        },
    }
    
    return suggestions_map.get(dimension, {
        "target_agent": "unknown",
        "issue": f"{dimension}未达标",
        "suggestion": "请人工检查",
    })
```

---

## 9. 全局评估（跨集）

```python
def evaluate_series(
    episodes: list[EpisodeData],
    character_cards: list[dict],
    pattern: str
) -> dict:
    """
    全局评估：评估整部剧的质量。
    
    维度：
    - 爽度分布（是否符合模式目标）
    - Hook连贯性（集间是否有断裂）
    - 角色发展弧度
    - 付费卡点质量
    """
    episode_evals = []
    for ep in episodes:
        eval_result = run_full_evaluation(ep, character_cards, {})
        episode_evals.append(eval_result)
    
    # 爽度分布
    shuang_curve = [e["dimensions"]["shuang"]["value"] for e in episode_evals]
    hook_curve = [e["dimensions"]["hook"]["value"] for e in episode_evals]
    
    # 付费卡点检查（EP8-10）
    paywall_shuang = shuang_curve[7:10] if len(shuang_curve) >= 10 else []
    paywall_quality = sum(paywall_shuang) / len(paywall_shuang) if paywall_shuang else 0
    
    # Hook连贯性
    hook_continuity = check_hook_continuity(episodes)
    
    return {
        "series_score": round(sum(e["overall_score"] for e in episode_evals) / len(episode_evals), 1),
        "shuang_distribution": {
            "curve": shuang_curve,
            "avg": round(sum(shuang_curve) / len(shuang_curve), 1) if shuang_curve else 0,
            "min": round(min(shuang_curve), 1) if shuang_curve else 0,
            "max": round(max(shuang_curve), 1) if shuang_curve else 0,
            "pattern_match": calculate_pattern_match(shuang_curve, pattern),
        },
        "hook_continuity": hook_continuity,
        "paywall_quality": {
            "episodes": "EP8-10",
            "avg_shuang": round(paywall_quality, 1),
            "passed": paywall_quality >= 8.0,
        },
        "per_episode": [
            {
                "episode": episodes[i].episode_number,
                "overall_score": episode_evals[i]["overall_score"],
                "passed": episode_evals[i]["passed"],
            }
            for i in range(len(episodes))
        ],
    }


def check_hook_continuity(episodes: list[EpisodeData]) -> dict:
    """检查集间Hook衔接"""
    breaks = []
    for i in range(len(episodes) - 1):
        current_hook = episodes[i].hook_ending
        next_outline = episodes[i+1].title  # 简化检查
        
        if current_hook.get("continuity_to_next") and not next_outline:
            breaks.append({
                "between": f"EP{episodes[i].episode_number}-EP{episodes[i+1].episode_number}",
                "issue": "Hook有衔接描述但下集缺少对应开头",
            })
    
    return {
        "total_transitions": max(0, len(episodes) - 1),
        "breaks": breaks,
        "continuity_score": max(0, 10 - len(breaks) * 3),
    }


def calculate_pattern_match(shuang_curve: list[float], pattern: str) -> float:
    """计算爽度分布与目标模式的匹配度"""
    if not shuang_curve:
        return 0
    
    # 各模式的理想爽度分布特征
    pattern_features = {
        "revenge_ladder": {"type": "uniform_high", "target_avg": 7.0, "target_variance": 1.5},
        "identity_onion": {"type": "ascending", "target_avg": 7.5, "target_variance": 2.0},
        "romance_rollercoaster": {"type": "oscillating", "target_avg": 6.5, "target_variance": 3.0},
        "upgrade_monster": {"type": "pulsing", "target_avg": 7.0, "target_variance": 2.5},
        "mystery_progressive": {"type": "stepped", "target_avg": 7.0, "target_variance": 1.8},
    }
    
    target = pattern_features.get(pattern, pattern_features["revenge_ladder"])
    
    # 计算匹配度（简化版）
    actual_avg = sum(shuang_curve) / len(shuang_curve)
    avg_diff = abs(actual_avg - target["target_avg"])
    
    match_score = max(0, 10 - avg_diff * 2)
    return round(match_score, 1)
```

---

> **文档状态**: v1.0 Python伪代码，可直接转为后端实现
> **依赖**: math标准库（无外部依赖）