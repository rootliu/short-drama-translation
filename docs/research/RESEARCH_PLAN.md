# 研究计划：AI评书艺人 — 网文到短剧的智能改编系统

## 一句话描述

像评书艺人将杨家将改编为长篇连播一样，AI系统将网文改编为高转化率的短剧剧本。

---

## Phase 0: 数据准备与定义 (前置条件)

### 0.1 情感维度体系定义

8维情感模型（6基础 + 2短剧特有）：

| 维度 | 说明 | 爽度关联 |
|------|------|---------|
| anger (愤怒) | 角色或观众的愤怒 | 反转前的蓄压维度 |
| sadness (悲伤) | 悲情、委屈、不公 | 反转前的蓄压维度 |
| joy (快乐) | 成功、团聚、甜蜜 | 反转后的释放维度 |
| fear (恐惧) | 危险、威胁 | 悬念驱动维度 |
| surprise (惊讶) | 意外发现、身份揭露 | trigger维度 |
| disgust (厌恶) | 对反派的厌恶 | 反转前的蓄压维度 |
| **oppression (压抑)** | 被欺负、隐忍、不得志 | **核心蓄压维度** |
| **catharsis (爽/解气)** | 逆袭、复仇、翻盘 | **核心释放维度** |

### 0.2 爽度值公式（初始定义，待验证）

```
shuang_value(t) = |E_release(t) - E_buildup(t-delta)| * trigger_quality(t) * pacing_bonus(t)

其中:
  E_release(t)     = 释放维度情感强度 (joy + catharsis + surprise) at time t
  E_buildup(t-d)   = 蓄压维度情感强度 (oppression + anger + sadness + disgust) at time t-delta
  trigger_quality   = trigger事件的合理性和意外性 (0-1)
  pacing_bonus      = 节奏奖励：反转间隔在最优范围内给额外加分
  delta             = 蓄压到释放的时间间隔
```

### 0.3 需要收集的数据

| 数据类型 | 数量 | 来源 | 优先级 |
|---------|------|------|-------|
| 高转化短剧字幕 | 5部以上 | 平台热门榜/付费榜 | P0 |
| 低转化短剧字幕 | 5部以上 | 同类型但表现差的 | P0 |
| 已改编网文+短剧对照 | 2-3对 | 有原著网文的短剧 | P1 |
| 留存率/转化率数据 | 间接指标即可 | 平台评分/弹幕热度/付费集数 | P1 |
| 同类型网文流行桥段库 | 按类型分 | 起点/晋江热门排行 | P2 |

---

## Phase 1: Shuang Benchmark (2-3周)

### 1.1 情感标注管线

用LLM对短剧剧本逐台词标注8维情感：

```python
# 每句台词 -> 8维情感向量
{
  "line_id": 42,
  "speaker": "苏晚晴",
  "text": "三年了，我终于回来了。",
  "emotions": {
    "anger": 0.3, "sadness": 0.2, "joy": 0.1,
    "fear": 0.0, "surprise": 0.0, "disgust": 0.0,
    "oppression": 0.1, "catharsis": 0.6
  },
  "dominant": "catharsis",
  "intensity": 7.2
}
```

### 1.2 爽度值计算

在情感时序上识别反转点，计算每次反转的爽度值。

反转点识别规则：
1. 蓄压维度的累计强度达到阈值
2. 随后在N句内出现释放维度的峰值
3. 存在明确的trigger事件

### 1.3 Hook评分

每集结尾的Hook评分基于：
- 未解决冲突的信息量（信息论度量）
- 情感状态的"未完成感"（是否在高位被截断）
- 新悬念的引入（是否提出了新问题）

### 1.4 弧线拟合与模式匹配

将整部剧的情感时序与8种标准弧线拟合，计算匹配度。同时识别"爽度值分布模式"（均匀高频/递增式/高幅振荡/脉冲式/阶梯式）。

### 1.5 验证

对高转化和低转化短剧分别评分，检验：
- 两组的Benchmark得分是否有统计显著差异
- 哪些维度的区分度最高
- 调整权重以最大化区分度

**交付物**：
- `benchmark/` 模块代码
- 10部短剧的评分报告
- Benchmark框架有效性验证文档

---

## Phase 2: 改编框架 — 模式库 (2-3周)

### 2.1 从Benchmark结果中提炼模式

分析Phase 1中高转化短剧的共性，提炼模式模板：

```yaml
# 示例：复仇阶梯模式
pattern_name: revenge_ladder
suitable_genres: [逆袭, 重生, 复仇, 赘婿]
episode_count: 60-80
structure:
  act_1 (ep 1-5):   # 建立压抑
    emotion_target: oppression_high
    shuang_target: 0  # 纯蓄压，不释放
    hook_strategy: "揭示主角的隐藏能力/背景线索"
  act_2 (ep 6-10):  # 首次小反转
    emotion_target: first_catharsis
    shuang_target: 6-7
    paywall_point: ep 8-10  # 付费卡点
    hook_strategy: "反转后暴露更大的威胁"
  act_3 (ep 11-40): # 循环升级
    cycle_length: 3-5 episodes
    cycle_pattern: [buildup, trigger, release]
    shuang_target: 7-8 (gradually increasing)
    hook_strategy: alternating [cliffhanger, revelation]
  act_4 (ep 41-55): # 高潮蓄力
    emotion_target: maximum_oppression
    shuang_target: 5-6 (deliberately lower to build tension)
  act_5 (ep 56-60+): # 终极爽感
    shuang_target: 9-10
    hook_strategy: "每集一个重大反转"
```

### 2.2 网文骨架提取方法

将网文分解为结构化元素：

```json
{
  "characters": [...],
  "relationships": [...],
  "plot_points": [
    {"id": 1, "type": "setup", "content": "...", "emotion": "oppression"},
    {"id": 2, "type": "trigger", "content": "...", "emotion": "surprise"},
    {"id": 3, "type": "reversal", "content": "...", "emotion": "catharsis"}
  ],
  "world_rules": [...],
  "conflicts": [...]
}
```

### 2.3 映射算法

将网文骨架的情节点对齐到模式模板的时间轴上。标记三类区域：
- **直接映射** — 原故事情节可直接使用
- **需要压缩** — 原故事内容过多，需精简
- **需要增补** — 模板要求有情感内容但原故事中缺失（"穆桂英挂帅"式空白）

**交付物**：
- 5种模式模板YAML定义
- 骨架提取prompt设计
- 映射算法实现
- 2-3个网文→模式的映射示例

---

## Phase 3: AI评书艺人Agent (3-4周)

### 3.1 系统架构

```
                    Orchestrator
                    (流程编排)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  SkeletonAgent    AugmentorAgent   HookEngineer
  (骨架提取+映射)   (增补填充)       (钩子设计)
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                  EvaluatorAgent
                  (Benchmark评分)
                        │
                   达标？──否──→ 反馈循环
                        │
                       是
                        ▼
                  最终剧本输出
```

### 3.2 各Agent职责

**SkeletonAgent（骨架师）**
- 读入网文全文
- 提取情节点、角色、冲突
- 映射到目标模式模板
- 输出: skeleton.json + mapping.json + gaps.json

**AugmentorAgent（增补师）— 核心**
- 读入gaps.json（空白区域清单）
- 对每个空白，生成符合以下约束的增补内容：
  1. 不违背原故事世界观
  2. 服务于模板要求的情感目标
  3. 增补内容有因果链（trigger有伏笔）
  4. 参考同类型流行桥段
- 输出: augmented_outline.json

**HookEngineer（钩子师）**
- 读入augmented_outline.json
- 对每集设计：
  - 集内高潮（反转点位置和方式）
  - 集尾钩子（悬念类型和强度）
- 确保50+集跨度的爽度值分布符合模式目标
- 输出: hooked_outline.json

**EvaluatorAgent（评审）**
- 用Phase 1的Benchmark对hooked_outline评分
- 检查: 爽度值分布、Hook质量、情感连贯性、节奏
- 如果不达标，生成具体的修改建议反馈给前三个Agent
- 输出: evaluation.json + feedback.json

### 3.3 增补策略的知识来源

AugmentorAgent增补内容时的参考来源：
1. **原网文** — 可能有被省略但可用的情节
2. **同类型网文** — 流行的情节模式和桥段
3. **短剧行业惯例** — 已验证的反转套路
4. **互联网热点** — 当下观众关注的话题和情绪

### 3.4 输出格式

```markdown
# 第X集 (1:30)

## 情感目标
- 蓄压: oppression 7/10
- 释放: catharsis 8/10
- 爽度值: 8.2

## 场景

### 场景1 (0:00-0:25) [来源: 原著第3章]
[苏晚晴站在公司门口，被保安拦住]
保安: 你已经不是苏氏的人了，请离开。
苏晚晴: (压抑) 我只是来拿我母亲的遗物。
[苏雅琪从楼上走出，一脸嘲讽]
苏雅琪: 姐姐，你还有脸回来？

### 场景2 (0:25-1:00) [来源: 增补 - 基于原著角色关系推演]
[王妈偷偷把一个信封塞给苏晚晴]
王妈: 小姐，这是老爷生前留给你的...
[苏晚晴打开信封，瞳孔猛然放大]

### 场景3 (1:00-1:25) [来源: 原著第5章，提前使用]
[苏晚晴直接走向董事会议室]
苏晚晴: (从压抑转为自信) 苏氏53%的股权，从今天起，由我说了算。
[全场震惊]

## 集尾Hook (1:25-1:30) [增补]
[苏雅琪拨通电话]
苏雅琪: (阴冷) 是我。她回来了...比我们预想的要快。
[画面切到一个男人的背影，手中握着另一份文件]

## 标注
- 反转类型: 身份/权力反转
- trigger: 王妈递信封
- Hook类型: 悬念(新威胁引入)
- 映射: 场景1=原著, 场景2=增补, 场景3=原著(时间线调整), Hook=增补
```

---

## 实现依赖

### 技术栈
- LLM: Gemini 2.5 Flash (免费API) + Claude (高质量评估)
- 后端: 复用现有FastAPI + file-based store
- 前端: 复用现有React dashboard (展示Benchmark结果和改编可视化)

### 需要人工提供的输入
- [ ] 5-10部短剧字幕文件 (Phase 1)
- [ ] 至少1部网文全文 (Phase 2-3的测试用例)
- [ ] 情感维度体系的确认/调整 (Phase 0)
- [ ] 爽度值公式的确认/调整 (Phase 0)
- [ ] 目标模式类型的优先级排序 (Phase 2)

### 里程碑

| 里程碑 | 交付物 | 依赖 |
|--------|-------|------|
| M0: 数据就绪 | 标注数据集 + 情感定义 | 人工收集字幕 |
| M1: Benchmark v1 | 能对短剧评分的工具 | M0 |
| M2: 模式库 v1 | 3+种改编模式模板 | M1 |
| M3: Agent v1 | 能将网文改编为剧本大纲 | M2 |
| M4: 端到端验证 | 完整剧本 + 评分 | M3 |
