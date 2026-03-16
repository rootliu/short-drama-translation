# 短剧翻译Pipeline架构设计

> 中文短剧出海翻译系统 — 概要设计与技术方案讨论
> 目标语言：英文 (EN)、日文 (JA)
> 日期：2026-03-15

---

## 1. 需求概要

| 维度 | 描述 |
|------|------|
| **输入** | 中文短剧视频，每集3-6分钟，每部200-500集，每次发布约50集 |
| **核心目标** | 翻译前的全面提取与分析，确保翻译质量（情感还原、hook连贯、角色一致） |
| **输出** | 结构化剧本、情感分析报告、hook连贯性报告，为后续翻译提供完整上下文 |

### 1.1 提取层次

```
视频输入
  ├── L1: 对白提取 (ASR → SRT字幕)
  ├── L2: 角色提取 (说话人分离 + 角色名识别 + 别名合并)
  ├── L3: 情绪提取 (每句对白的情感分类 + 1-10强度评分)
  ├── L4: 场景描述提取 (环境音 + 视觉场景 + 背景音乐情绪)
  ├── L5: 剧本生成 (按剧本格式整合 + 剧情摘要)
  ├── L6: 情感管理分析 (情感峰值、反转点、波动统计)
  └── L7: Hook提取与连贯性评估 (每集hook + 批次连续性)
```

---

## 2. Pipeline总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Manager Agent (规划调度)                    │
│  - 任务编排与依赖管理                                          │
│  - 进度追踪与异常处理                                          │
│  - 资源调度（GPU/API调用分配）                                  │
└──────────┬──────────────────────────────────┬───────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────────┐
│   Shared Memory     │◄────────►│     QA Agent (质量)      │
│  - 角色知识库        │          │  - 每步结果校验           │
│  - 情感时间线        │          │  - 跨集一致性检查         │
│  - 剧情上下文        │          │  - Benchmark汇总         │
│  - 术语表/别名表     │          │  - 反思与修正建议         │
└─────────────────────┘          └─────────────────────────┘
           │
    ┌──────┴──────────────────────────────────┐
    ▼      ▼      ▼      ▼      ▼      ▼     ▼
  [S1]   [S2]   [S3]   [S4]   [S5]   [S6]  [S7]
  对白    角色    情绪   场景    剧本   情感   Hook
  提取    提取    提取   描述    生成   管理   分析
```

### 2.1 执行顺序与依赖关系

```
S1 (对白提取) ──┬──► S2 (角色提取) ──┐
                │                    │
                ├──► S3 (情绪提取)   ├──► S5 (剧本生成) ──► S6 (情感管理)
                │                    │                        │
                └──► S4 (场景描述) ──┘                        ▼
                                                        S7 (Hook分析)
```

- **S1** 可独立运行，是所有后续步骤的基础
- **S2/S3/S4** 可在S1完成后并行执行
- **S5** 依赖S1-S4全部完成
- **S6/S7** 依赖S5完成，且需要跨集（批次级别）聚合

---

## 3. 各阶段详细设计

### 3.1 S1: 对白提取 (字幕校验 + 说话人标注)

**目标**：基于已有中文字幕，用ASR做质量校验和说话人标注，输出带说话人标签的增强SRT。

> **前提**：输入视频已有中文字幕(SRT)。S1不再从零ASR，而是以现有字幕为基准，ASR用于校验纠错+补充说话人信息。

#### 推荐模型方案

| 模型 | 来源 | 优势 | 劣势 | 推荐度 |
|------|------|------|------|--------|
| **SenseVoice-Small** | FunAudioLLM | CER: AISHELL-1 **2.96**, AISHELL-2 **3.80**; 处理10s音频仅需70ms(15x Whisper); 内置情绪+语言识别+音频事件检测; 支持中/英/日/韩 | 时间戳基于CTC对齐（2024.11新增） | ★★★★★ |
| **Paraformer-large** | FunASR (阿里) | CER: AISHELL-1 **1.95**, AISHELL-2 **2.85**, WenetSpeech **6.97** (业界最优); 220M参数, 60K小时训练; 原生VAD+标点+时间戳+CAM++说话人分离一体化 | FunASR Model License（非OSI） | ★★★★★ |
| **Whisper-large-v3** | OpenAI | CER: AISHELL-1 **5.14**, AISHELL-2 **4.96**; MIT许可; 社区生态强(WhisperX等); v20250625 | 中文准确率明显落后国产方案; 无情绪检测 | ★★★☆☆ |
| **WeNet** | 社区 | Apache 2.0; C++ runtime生产就绪; 支持Paraformer/FireRed等多种模型 | 缺少一体化pipeline; 中文对话场景缺专项优化 | ★★★☆☆ |

#### 推荐方案
**主选：FunASR一体化Pipeline（Paraformer + CAM++ + VAD + 标点）**

FunASR提供了完整的一站式调用接口，单次调用即可完成ASR+说话人分离：
```python
from funasr import AutoModel

# 一体化Pipeline：ASR + VAD + 标点 + 说话人分离
model = AutoModel(
    model="paraformer-zh",          # 中文ASR (CER 1.95)
    vad_model="fsmn-vad",           # 语音活动检测
    punc_model="ct-punc-c",         # 标点恢复
    spk_model="cam++"              # 说话人分离
)
result = model.generate(input="episode_001.wav", batch_size_s=300)
# 输出：带时间戳、标点、说话人标签的转录文本
```

**辅助：SenseVoice-Small 情绪增强通道**
- 对同一音频运行SenseVoice，获取每句对白的情绪标签（为S3提供音频情绪基准）
- 同时获取音频事件检测结果（为S4提供环境音数据，Phase 3启用）

#### 处理流程（已有字幕模式）
```
已有中文字幕(SRT) ──────────────────────────────┐
                                                ├──► 差异比对 → 增强SRT(说话人+精修时间戳)
视频文件 → FFmpeg提取音轨 → Demucs人声分离 ─┬──► FunASR Pipeline → ASR文本 + 说话人标签
                                            │
                                            └──► SenseVoice → 情绪标签 + 音频事件
```

> 合并策略：以现有字幕文本为主（已经过人工校对），ASR结果用于：
> 1. 补充说话人标签（Speaker_1, Speaker_2...）
> 2. 发现字幕与实际语音的差异（漏句、错字）
> 3. 精修时间戳对齐

#### 关键问题与难点
1. **背景音乐/音效干扰**：短剧常有强背景音乐，需要音源分离预处理
   - 推荐工具：`demucs` (Meta) 或 `UVR5` 进行人声分离
2. **叠音/抢话**：多人同时说话的场景，ASR准确率下降
   - 需结合S2的说话人分离来辅助
3. **方言/口音**：部分短剧角色有方言口音
   - 可能需要方言ASR模型或后处理纠错

---

### 3.2 S2: 角色提取 (Speaker Diarization + Name Resolution)

**目标**：识别每句对白的说话人，映射到剧中角色名称，支持别名合并。

#### 推荐模型方案

| 模型 | 来源 | 优势 | 劣势 |
|------|------|------|------|
| **pyannote.audio v4** | 社区 | MIT许可; 重叠语音检测; 可配置min/max说话人数; AISHELL-4 DER **12.2%**, AliMeeting DER **24.4%** | 中文非主要优化方向 |
| **3D-Speaker + CAM++** | 阿里/ModelScope | 专为中文设计; CAM++ 7.18M参数(ECAPA-TDNN的1/3); VoxCeleb1 EER **0.65%**, CN-Celeb EER **6.78%**; 支持可选重叠检测 | 无直接ASR集成 |
| **FunASR内置CAM++** | 阿里 | 与Paraformer无缝集成 `spk_model="cam++"`, 一行代码开启说话人分离+ASR | 生态相对封闭 |

#### 推荐方案
**3D-Speaker/CAM++ (声纹) + LLM (语义角色推理)**

角色识别分两个层次：
1. **声纹层**：用CAM++提取每段音频的说话人embedding，聚类为Speaker_1, Speaker_2...
2. **语义层**：用LLM分析对白内容，推理角色身份

#### 角色名称识别策略（LLM驱动）

```
输入：带说话人标记的对白文本
  Speaker_1: "李总，这个项目的进度怎么样了？"
  Speaker_2: "王经理放心，下周一定能完成。"
  Speaker_1: "好的，小王你辛苦了。"

LLM推理：
  - Speaker_1 被称为 "李总" → 角色名: 李总 (李XX)
  - Speaker_2 被称为 "王经理"、"小王" → 角色名: 王经理 (王XX)
  - 别名合并: "王经理" = "小王" = Speaker_2
```

#### 别名合并的实现思路（NER + 共指消解 + LLM）

**阶段1：从对白中提取人名/称谓（NER）**
- 使用 `hanlp`（中文NER）或百度 `LAC` 提取人名、职称
- 识别称呼语模式：中文称呼通常出现在句首/句尾（"李总，你好" / "好的，小王"）
- 被称呼者通常是相邻对白轮次的说话人

**阶段2：建立说话人-名称关联图**
- Speaker_A说"李总，你好" → "李总"大概率是Speaker_B（下一个说话人）
- 频率统计：如果Speaker_02被持续称为"李总"，则映射增强
- 中文称谓规律：[姓] + [职位/关系词]（总/董/经理/医生/哥/姐）

**阶段3：共指消解与别名合并**
- 姓氏匹配："李总" = "李明" = "老李" = "李董"（共享"李"）
- 上下文共现：同一场景中从未同时出现的不同称谓大概率指同一人
- 工具：`hanlp` 提供中文共指消解; LLM做最终裁定

**阶段4：跨集一致性维护**
- 建立**角色知识库**（存入Shared Memory），随剧集推进增量更新
- 每集处理完后，LLM基于上下文更新角色关系图
- 同一声纹embedding在不同集中出现时自动关联
- 字幕/片头片尾OCR可直接提供角色名+演员名作为ground truth

#### 关键问题与难点
1. **旁白/画外音**：短剧常有旁白，需区分旁白与角色对白
2. **电话/回忆场景**：音频质量变化导致声纹匹配失败
3. **角色数量变化**：200-500集中角色可能不断增加/退出
4. **同名不同人**：不同场景下"张总"可能指不同人物
5. **称谓随关系变化**：同一角色在不同阶段可能被不同称谓称呼

---

### 3.3 S3: 情绪提取

**目标**：为每句对白标注情感类别和强度评分(1-10)。

#### 推荐模型方案

| 模型 | 通道 | 能力 | 情感类别 |
|------|------|------|----------|
| **emotion2vec+** | 音频 | 语音情感识别，9类情绪 | angry, disgusted, fearful, happy, neutral, other, sad, surprised, unknown |
| **SenseVoice** | 音频 | ASR同时输出情绪 | HAPPY, SAD, ANGRY, NEUTRAL, FEARFUL, DISGUSTED, SURPRISED |
| **LLM (Claude/GPT)** | 文本 | 语义情感分析，支持细粒度情感 | 自定义（平和/嘲讽/愤怒/喜悦/狂喜/暴走等） |
| **Qwen-VL / InternVL** | 视觉 | 面部表情分析 | 需要prompt引导 |

#### 推荐方案：三通道融合

```
               ┌──► emotion2vec+ (音频情绪) ──┐
对白片段 ──────┼──► LLM文本分析 (语义情绪)    ├──► 融合Agent ──► 最终情绪标注
               └──► VLM截帧分析 (视觉情绪)  ──┘
```

#### 情感评分体系设计

| 评分 | 强度描述 | 示例 |
|------|----------|------|
| 1-2 | 微弱 | 略有不满、轻微愉悦 |
| 3-4 | 温和 | 平静陈述中带情绪色彩 |
| 5-6 | 明显 | 可被观众明确感知的情绪 |
| 7-8 | 强烈 | 情绪爆发、语调明显变化 |
| 9-10 | 极端 | 暴走、狂喜、崩溃等极端情绪 |

#### 自定义情感分类映射
短剧的情感粒度需要超越标准SER模型的分类：

```
标准SER → 短剧细粒度映射:
  angry → 不满(3) / 愤怒(6) / 暴怒(8) / 暴走(10)
  happy → 满意(3) / 喜悦(6) / 狂喜(9)
  neutral → 平和(2) / 冷漠(4) / 压抑平静(5)
  其他 → 嘲讽 / 挑衅 / 心碎 / 绝望 / 震惊 / 恐惧...
```

**关键**：标准SER模型输出作为基础参考，由LLM结合对白语义和剧情上下文做细粒度判定。

#### 情绪强度评分实现策略
没有现成模型直接输出1-10强度评分，推荐组合方案：
1. **emotion2vec+ softmax概率**作为强度代理（置信度越高=情绪越强烈）
2. **中文LLM结构化prompt**：输入对白文本+音频情绪标签，要求输出1-10评分
3. 如有标注数据，可在emotion2vec特征之上训练**回归头**做连续强度预测

#### 关键问题与难点
1. **嘲讽检测**：音频模型难以识别嘲讽语气，需要文本语义分析
2. **内心独白**：角色表面平静但内心情绪复杂（短剧常用对比手法）
3. **情绪连续性**：评分需要在集内和跨集保持一致标准
4. **文化差异**：中文情绪表达方式与英文/日文不同（如含蓄的愤怒）

---

### 3.4 S4: 场景描述提取

**目标**：提取每个对白的视觉场景和音频环境信息。

#### 推荐模型方案

| 模型 | 任务 | 说明 |
|------|------|------|
| **Qwen2.5-VL** (3B/7B/72B) | 视频理解 | 强中文双语; 视频OCR/grounding/场景描述; 7B量化版16GB VRAM可用 |
| **InternVL3.5** (1B-78B) | 视频/图像理解 | 最新开源MLLM SOTA; 中文支持优秀; 8B版16GB VRAM |
| **CogVLM2-Video** (19B) | 视频QA | 处理1分钟视频(24帧); 有中文专用版本; Int4量化16GB VRAM |
| **PANNs** (CNN14, ~80M) | 音频事件检测 | AudioSet 527类(语音/音乐/雨声/交通等); CPU可运行; 轻量高效 |
| **CLAP** (LAION) | 音频-文本匹配 | 零样本音频分类——用文本描述查询("海浪声"); 支持音乐情绪; 无需训练 |
| **Essentia** (MTG/UPF) | 音乐信息检索 | 预训练TF模型: 音乐情绪(happy/sad/aggressive); 流派/BPM/调性/乐器 |

#### 推荐方案

```
视频帧（场景切换时采样）→ Qwen2.5-VL-7B → 场景描述文本 ──┐
                                                        ├──► 合并 → 场景描述JSON
音频（Demucs去人声后）──┬─► PANNs → 环境音分类(527类)   ──┤
                       │                                 │
                       └─► CLAP → 零样本音频描述          ──┤
                                                        │
背景音乐段 ──────────────► Essentia → 音乐情绪/流派/BPM ──┘
```

#### 场景描述结构
```json
{
  "timestamp": "00:01:23",
  "visual_scene": "豪华办公室，落地窗外是城市天际线，阳光透过百叶窗",
  "ambient_sound": ["键盘敲击声", "空调声"],
  "background_music": {"mood": "紧张", "intensity": 6},
  "lighting": "明亮，自然光",
  "weather": "晴天"
}
```

#### 关键问题与难点
1. **帧采样策略**：每秒1帧可能遗漏快速场景切换
2. **VLM推理成本**：每集数百帧，使用大模型成本高
3. **音源分离质量**：环境音可能被人声掩盖
4. **场景切换检测**：需要准确识别场景转换的边界

---

### 3.5 S5: 剧本生成与摘要

**目标**：将S1-S4的结构化数据整合为标准剧本格式，并生成摘要。

#### 推荐工具
**LLM（Claude Opus / GPT-4o / Gemini Pro）**：剧本格式化和摘要生成是LLM的强项。

#### 剧本格式

```
第 3 集 - "步步紧逼"

摘要：李总发现财务报表异常，质问王经理。王经理试图掩盖真相，
但被李总识破。紧张的对峙在暴风雨来临时达到高潮。

---

场景一：总裁办公室 / 白天 / 阴天
[背景：低沉的钢琴曲，窗外乌云密布]

李总（愤怒 7/10）：
"这份报表上的数字，你能解释一下吗？"
[将文件摔在桌上]

王经理（紧张 6/10）：
"李总，这个...可能是财务部那边录入的时候出了点差错。"

[窗外雷声渐近，室内灯光微暗]

李总（冷笑/嘲讽 8/10）：
"差错？连续三个月的差错？"
```

#### 摘要层次
1. **单集摘要**：200字以内，包含主要情节和情感走向
2. **批次摘要**：一次发布(~50集)的整体故事线和发展
3. **全剧摘要**：核心人物关系、主线冲突、故事弧线

---

### 3.6 S6: 情感管理分析

**目标**：建立情感时间线，发现峰值/反转点，为翻译提供情感保障参考。

#### 分析维度

| 分析 | 粒度 | 输出 |
|------|------|------|
| 单集情感曲线 | 每句对白 | 情感折线图 + 峰值时间点 |
| 单集反转点 | 场景级别 | 反转点列表（时间、类型、强度变化） |
| 批次情感波动 | 集级别 | 50集情感热力图 |
| 全局反转点统计 | 批次级别 | 反转点分布、频率、类型统计 |

#### 情感反转的定义
```
反转 = 情感评分在短时间内（≤30秒）变化幅度 ≥ 4分
       或情感类别从正面跳转到负面（反之亦然）

示例：
  00:02:10 喜悦(7) → 00:02:35 震惊(8)  → 反转! (Δ=15, 正→负)
  00:04:50 绝望(9) → 00:05:10 释然(6)  → 反转! (Δ=15, 负→正)
```

#### 输出格式
```json
{
  "episode": 3,
  "emotional_peaks": [
    {"time": "00:02:35", "emotion": "震惊", "score": 8, "context": "发现真相"},
    {"time": "00:05:10", "emotion": "释然", "score": 6, "context": "危机解除"}
  ],
  "reversal_points": [
    {"time": "00:02:30", "from": {"emotion": "喜悦", "score": 7}, "to": {"emotion": "震惊", "score": 8}, "type": "positive_to_negative"}
  ],
  "overall_arc": "tension_buildup_to_release",
  "average_intensity": 5.8
}
```

#### 情感弧线分析方法论
基于Reagan et al.的6种基本故事形状理论，可对短剧情感轨迹进行分类：
1. **Rags to riches** (逆袭上升) — 霸总/逆袭题材常见
2. **Riches to rags** (持续下跌) — 悲剧/虐心集
3. **Man in a hole** (先跌后升) — 单集最常见的微结构
4. **Icarus** (先升后跌) — 反转hook的经典结构
5. **Cinderella** (升-跌-升) — 跨集常见弧线
6. **Oedipus** (跌-升-跌) — 高能虐心集

**反转点检测算法**：对平滑后的情感轨迹求一阶导数，导数过零点且变化幅度大的位置即为反转点。可用变点检测算法(PELT, Bayesian changepoint detection)实现。

**可视化工具**：`syuzhet`(R包) 或自定义Python方案，对逐句情感评分做低通滤波后生成宏观情感弧线。

#### 关键问题与难点
1. **反转 vs 正常情绪波动**：如何区分有意义的情节反转与日常情绪变化
2. **翻译指导的实用性**：分析结果如何具体指导翻译用词
3. **跨文化情感映射**：中文"含蓄的愤怒"如何在英文/日文中等效表达

---

### 3.7 S7: Hook提取与连贯性评估

**目标**：识别每集的叙事钩子(hook/cliffhanger)，评估翻译后hook是否依然有效。

#### Hook类型分类

| 类型 | 描述 | 示例 |
|------|------|------|
| **悬念型** | 关键信息未揭示 | "那个人是谁？" → 下集揭晓 |
| **反转型** | 剧情突变 | 结尾突然出现意外人物/事件 |
| **情感型** | 强烈情绪驱动 | 角色崩溃/告白/背叛 |
| **威胁型** | 危险/冲突升级 | "你有三天时间" |
| **揭秘型** | 部分揭示真相 | 发现关键线索但未完全揭露 |
| **选择型** | 角色面临抉择 | "你选A还是B？" |

#### 推荐方案
**LLM驱动的Hook分析**（无现成专用模型，这是LLM的优势领域）

```
输入：单集完整剧本 + 前后集上下文
Prompt：
  1. 识别本集结尾的hook类型和内容
  2. 评估hook的吸引力（1-10）
  3. 分析hook与下一集开头的衔接
  4. 标注hook中依赖语言特色的元素（双关、谐音、文化梗）
```

#### 连贯性评估

```
批次Hook时间线（50集）:
  EP01 [悬念型-8] → EP02 [反转型-9] → EP03 [情感型-7] → ...
                    ↑                    ↑
                  承接EP01悬念          承接EP02反转

连贯性评分 = Σ(hook_i 与 ep_{i+1}开头的关联度) / N
```

#### 翻译风险标注
```json
{
  "episode": 15,
  "hook": {
    "type": "wordplay",
    "original": "他说'我会让你好看的'——双关：让你变美/给你好看",
    "translation_risk": "HIGH",
    "risk_reason": "中文双关语，直译丧失悬念效果",
    "suggestion": "需要创译(transcreation)，在目标语言中找到等效双关或改用其他hook手法"
  }
}
```

#### 学术参考
- **Papalampidi et al. (EMNLP 2019)** "Movie Plot Analysis via Turning Point Identification" — 定义了5类叙事转折点(change of plans, major setback, climax等)，构建了剧本标注数据集，可迁移到短剧hook检测
- **Reagan et al. (2016)** "The Emotional Arcs of Stories Are Dominated by Six Basic Shapes" — 用情感分析和矩阵分解发现6种基本故事情感弧线形状，特定弧线与更高的读者参与度相关
- **Chu & Roy (2017)** "Audio-Visual Sentiment Analysis for Learning Emotional Arcs in Movies" — 多模态(音频+视觉)构建电影情感弧线，发现不同弧线类别可预测观众参与度
- **DITING (Zhang et al. 2025)** "A Multi-Agent Evaluation Framework for Benchmarking Web Novel Translation" — 6维度评估框架(成语/歧义/术语/时态/零代词/文化安全)，18K+中英标注句对
- **TPMaven (Ho et al. 2024)** "MTP: A Dataset for Multi-Modal Turning Points in Casual Conversations" — 多模态转折点检测框架，结合视觉-语言模型识别情绪爆发和决策变化

#### 关键问题与难点
1. **Hook检测无标准数据集**：可参考Papalampidi的转折点数据集做迁移，但短剧节奏远快于电影
2. **文化相关hook**：中国社会背景相关的hook（如"逼婚""重男轻女"）在海外文化中可能缺乏共鸣
3. **连贯性量化**：如何定义和度量"连贯性"是一个开放问题
4. **双关语/谐音梗**：中文特有的语言hook在翻译中几乎必然损失

---

## 4. Agent架构设计

### 4.1 Manager Agent

**职责**：全局任务编排、资源调度、异常处理

```python
# 概念设计
class ManagerAgent:
    def plan_pipeline(self, drama_batch: DramaBatch):
        """为一个发布批次（~50集）生成执行计划"""
        # 1. 预扫描：评估视频质量、音频质量、预估工作量
        # 2. 生成DAG：基于S1-S7的依赖关系生成执行图
        # 3. 资源分配：GPU任务 vs API任务 vs CPU任务
        # 4. 启动执行：按DAG拓扑序调度

    def handle_exception(self, step, error):
        """异常处理：重试/降级/人工介入"""

    def checkpoint(self, step, results):
        """断点保存：支持中断后恢复"""
```

#### 编排框架选型

| 框架 | 优势 | 劣势 | 推荐度 |
|------|------|------|--------|
| **LangGraph** | 状态机+图执行，灵活的条件分支，原生LLM集成 | 学习曲线较陡 | ★★★★★ |
| **CrewAI** | 角色定义直观，多Agent协作简单 | 复杂DAG支持弱 | ★★★☆☆ |
| **Prefect / Airflow** | 成熟的工作流编排，断点恢复，监控 | 偏重数据工程，LLM集成需自行实现 | ★★★★☆ |
| **MetaGPT** | 多Agent软件开发导向 | 不太适合多媒体处理场景 | ★★☆☆☆ |

**推荐：LangGraph (Agent逻辑) + Prefect/Celery (任务调度)**
- LangGraph处理Agent间的推理和决策
- Prefect/Celery处理大规模批量任务的调度和监控

### 4.2 QA Agent

**职责**：每步质量校验、跨集一致性检查、Benchmark汇总

```
QA检查点:
  S1后 → ASR质量检查（抽样人工比对、置信度分布）
  S2后 → 角色一致性检查（同一声纹是否被分配了不同角色？）
  S3后 → 情绪评分校准（同类场景的评分是否一致？）
  S4后 → 场景描述合理性（与视觉内容是否匹配？）
  S5后 → 剧本完整性（对白是否遗漏？角色是否正确？）
  S6后 → 情感曲线合理性（反转点是否与剧本事件对应？）
  S7后 → Hook连贯性评分（是否存在断裂？）
```

#### QA反思循环
```
结果 → QA评估 → 发现问题 → 生成修正建议 → 重新执行相关步骤 → 再次QA
                                    ↑                        |
                                    └────────────────────────┘
                                    (最多3次迭代)
```

### 4.3 Shared Memory

**用途**：跨Agent、跨集、跨步骤的知识共享

#### 存储结构
```
shared_memory/
  ├── character_db/           # 角色知识库
  │   ├── profiles.json       # 角色档案（名称、别名、关系、性格）
  │   ├── voice_embeddings/   # 声纹向量
  │   └── character_graph.json # 角色关系图
  ├── episode_data/           # 集级别数据
  │   ├── ep001/
  │   │   ├── srt/            # 字幕文件
  │   │   ├── script.md       # 剧本
  │   │   ├── emotions.json   # 情感标注
  │   │   ├── scenes.json     # 场景描述
  │   │   └── hooks.json      # Hook分析
  │   └── ...
  ├── batch_reports/          # 批次级别报告
  │   ├── emotional_analysis.json
  │   ├── hook_continuity.json
  │   └── qa_summary.json
  └── glossary/               # 术语与翻译记忆
      ├── terms.json          # 专有名词
      └── translation_memory.json  # 翻译记忆（为后续翻译步骤准备）
```

#### 存储技术选型
- **结构化数据**：SQLite / PostgreSQL（角色档案、情感数据、关系表）
- **向量数据**：ChromaDB / Qdrant（声纹embedding、语义搜索）
- **文件存储**：本地文件系统 / S3（SRT、剧本、报告）
- **缓存**：Redis（Agent间实时通信、中间结果缓存）

---

## 5. 技术选型汇总

### 5.1 专用模型（本地部署）

| 任务 | 模型 | 参数量 | GPU需求 | 部署方式 |
|------|------|--------|---------|----------|
| 中文ASR | SenseVoice-Small | ~234M | 单卡4GB+ | FunASR框架 |
| 精确ASR | Paraformer-large | ~220M | 单卡4GB+ | FunASR框架 |
| 人声分离 | Demucs v4 | ~83M | 单卡4GB+ | PyTorch |
| 说话人分离 | pyannote v4 | ~5M | CPU可用 | pip install |
| 声纹提取 | CAM++ | 7.2M | CPU可用 | 3D-Speaker |
| 语音情绪 | emotion2vec+ large | ~300M | 单卡8GB+ | FunASR框架 |
| 视频理解 | InternVL3.5-8B / Qwen2.5-VL-7B | 7-8B | 单卡24GB | vLLM/Transformers |
| 音频事件 | BEATs / PANNs | ~90M | 单卡4GB+ | PyTorch |

### 5.2 大语言模型（API调用）

| 任务 | 推荐模型 | 备选 | 理由 |
|------|----------|------|------|
| 角色名推理 | Claude Opus | GPT-4o | 复杂推理，需要理解中文文化 |
| 细粒度情绪判定 | Claude Opus | Gemini Pro | 需要理解嘲讽等微妙情绪 |
| 剧本生成 | Claude Opus / GPT-4o | Gemini Pro | 长文本生成质量 |
| Hook分析 | Claude Opus | GPT-4o | 叙事理解与文化理解 |
| 情感管理报告 | GPT-4o | Claude Opus | 结构化分析 |
| QA校验 | Claude Opus | GPT-4o | 反思与纠错能力 |

### 5.3 基础设施

| 组件 | 推荐 | 用途 |
|------|------|------|
| 任务调度 | Prefect / Celery + Redis | 批量任务编排 |
| Agent框架 | LangGraph | Agent间协作逻辑 |
| 向量数据库 | ChromaDB | 声纹存储与检索 |
| 关系数据库 | PostgreSQL | 角色、情感、元数据 |
| 对象存储 | MinIO / 本地FS | 视频、音频、SRT文件 |
| 监控 | Prometheus + Grafana | Pipeline运行监控 |
| 前端 | Streamlit / Gradio | 人工审核界面 |

---

## 6. 待讨论问题

### 6.1 核心设计决策

1. **ASR双通道是否必要？** SenseVoice + Paraformer双通道验证会增加成本，是否单用SenseVoice即可？
2. **VLM场景描述的性价比**：每帧都过VLM成本很高，是否只在场景切换时提取？
3. **情绪评分校准标准**：1-10分制如何在200+集中保持一致？是否需要校准集？
4. **Hook分析的自动化程度**：是全自动还是LLM生成初步结果后人工审核？
5. **Shared Memory的持久化策略**：每次处理新集时，角色知识库如何增量更新而不覆盖？

### 6.2 工程难点

6. **规模化处理**：50集/批次 × 500集/部，如何保证Pipeline稳定运行？断点续跑策略？
7. **GPU资源规划**：本地部署多个专用模型的GPU memory管理（time-sharing vs model-sharing）
8. **API成本控制**：大量LLM API调用的成本估算和优化（batching、caching、降级策略）
9. **多语言输出一致性**：英文和日文的分析报告格式如何统一？
10. **人工介入接口**：何时需要人工审核？如何设计人机协作界面？

### 6.3 质量保障难点

11. **ASR质量的边界**：短剧音质参差不齐，如何定义可接受的ASR质量下限？
12. **角色识别的准确率**：跨集角色追踪在500集中是否会退化？如何定期校准？
13. **情感分析的主观性**：不同标注者对"嘲讽7分"可能有不同理解，如何标准化？
14. **Hook连贯性无ground truth**：连贯性评估缺乏客观指标，如何验证分析的有效性？

### 6.4 翻译准备阶段的遗留问题

15. **翻译记忆如何初始化？** 是否需要先翻译几集作为种子来建立风格基准？
16. **文化适配的边界**：有些短剧题材（如宫斗、修仙）在海外市场可能需要额外的文化注释
17. **英文 vs 日文的差异化处理**：日文有敬语体系，角色的社会地位需要额外映射
18. **与已有字幕的兼容**：如果部分剧集已有人工字幕，如何与自动提取结果对齐？

---

## 7. 成本与资源估算（粗略）

### 单集处理（假设5分钟/集）

| 步骤 | 计算资源 | 预估耗时 | API成本 |
|------|----------|----------|---------|
| S1 ASR | GPU (本地) | ~30s | $0 |
| S2 说话人分离 | GPU/CPU | ~20s | $0 |
| S2 角色推理 | LLM API | ~10s | ~$0.05 |
| S3 情绪(音频) | GPU (本地) | ~15s | $0 |
| S3 情绪(LLM) | LLM API | ~10s | ~$0.03 |
| S4 场景描述 | GPU (VLM) | ~60s | $0 |
| S5 剧本生成 | LLM API | ~20s | ~$0.10 |
| S6 情感分析 | LLM API | ~15s | ~$0.05 |
| S7 Hook分析 | LLM API | ~15s | ~$0.05 |
| QA | LLM API | ~15s | ~$0.05 |
| **合计/集** | | **~3.5min** | **~$0.33** |

### 批次处理（50集）
- 总耗时：约3小时（考虑并行和排队）
- API成本：约$16.5/批次
- GPU需求：1×A100 40GB（或2×RTX 4090）

### 全剧处理（500集）
- 总耗时：约30小时
- API成本：约$165/部
- GPU累计：约30 GPU-hours

---

## 8. 设计决策记录

基于讨论确定的关键决策：

| # | 决策项 | 结论 | 影响 |
|---|--------|------|------|
| Q1 | S1/S2粒度 | 概念分离、工程合并，QA分别检查 | FunASR一步出ASR+说话人，但质量分开评估 |
| Q2 | 翻译包消费者 | 人工翻译团队 | 输出格式侧重可读性，非机器可解析 |
| Q3 | 交付节奏 | 50集滚动交付，边提取边翻译 | 角色知识库必须增量模式 |
| Q4 | S3视觉通道 | 先音频+文本双通道，视觉与S4一起后补 | 初期Pipeline更轻量 |
| Q5 | 情绪评分校准 | 锚点校准——每部剧开头5集建基线 | 不需要人工标注金标准 |
| Q6 | FunASR License | POC优先效果，风险后评 | 直接用Paraformer |
| Q7 | GPU资源 | 云GPU按需调用 | Pipeline需支持远程GPU调度 |
| Q8 | LLM API策略 | 按任务选最优模型 | 需维护多供应商集成 |
| Q9 | 目标语言 | 先英文，日文延后 | 初期不考虑敬语映射 |
| Q10 | 已有资产 | 带现成中文字幕的视频 | S1大幅简化为字幕校验+说话人标注 |

### 决策带来的架构调整

**S1重新定义：字幕校验+增强（而非从零ASR）**
```
已有中文字幕(SRT) ─┬─► 字幕质量校验（与ASR结果比对，标记差异）
                   │
视频音轨 ──────────┼─► FunASR Pipeline → ASR文本 + 说话人标签 + 时间戳
                   │
                   └─► 合并：以现有字幕为基准，ASR补充说话人信息和时间戳精修
```

**最小闭环（Phase 1）**
```
S1(字幕校验+说话人) → S2(角色识别) → S3(音频+文本双通道情绪) → S5(剧本包)
                                                                    ↓
                                                          交付人工翻译团队
```

**增强阶段（Phase 2）**
```
+ S6(情感管理) + S7(Hook分析) → 作为翻译约束附加到剧本包中
```

**完整阶段（Phase 3）**
```
+ S4(场景描述) + S3视觉通道 → 完整剧本包
```

**滚动交付模式**
```
批次1 (EP01-50):
  处理 → 建立角色知识库v1 + 情绪基线 → 交付翻译
批次2 (EP51-100):
  处理 → 更新角色知识库v2（新角色/新别名）→ 交付翻译
  ...滚动推进
```

**翻译输入包格式（面向人工翻译团队）**
```
translation_pack_batch_01/
  ├── character_guide.md          # 角色表：名称、别名、关系、性格描述
  ├── glossary.md                 # 术语表：专有名词、常用表达的建议译法
  ├── episodes/
  │   ├── ep001_script.md         # 剧本：角色+对白+情绪标注+场景
  │   ├── ep001_emotions.md       # 情绪概要：峰值、反转点（Phase 2）
  │   ├── ep001_hooks.md          # Hook分析：类型、翻译风险（Phase 2）
  │   └── ...
  ├── batch_summary.md            # 本批次剧情摘要
  └── translation_notes.md        # 翻译注意事项：文化梗、双关语、特殊表达
```

---

## 9. Benchmark 与评估（QA输入）

### Phase 1 指标
1. **S1 字幕校验**：现有字幕与ASR差异率、说话人标注准确率（抽样5集人工核对）
2. **S2 角色识别**：别名合并准确率、跨集声纹一致率
3. **S3 情绪提取**：锚点校准后的评分稳定性、音频/文本双通道一致性
4. **S5 剧本包**：对白完整性、角色归属正确率、翻译团队可用性反馈

### Phase 2 指标
5. **S6 情感管理**：峰值/反转点稳定性、跨集情感波动趋势一致性
6. **S7 Hook分析**：hook类型一致性、翻译风险标注的有效性

### Phase 3 指标
7. **S4 场景描述**：关键帧召回率、环境音识别覆盖率、人工可读性评分
8. **S3 视觉通道**：与音频/文本通道的一致性提升度

---

## 10. 下一步行动（POC计划）

### POC目标
选取一部短剧的**前5集**（有字幕），跑通Phase 1最小闭环。

### POC步骤
1. **环境搭建**：云GPU实例 + FunASR + SenseVoice + emotion2vec+ 部署
2. **S1验证**：用FunASR处理5集音频，对比现有字幕差异，验证说话人分离质量
3. **S2验证**：NER提取角色称谓 + LLM推理角色身份，输出角色表
4. **S3验证**：emotion2vec+音频情绪 + LLM文本情绪，用锚点法校准5集评分
5. **S5验证**：LLM整合为剧本格式，输出翻译包样例
6. **人工评审**：让翻译团队试用翻译包，收集反馈
7. **迭代**：根据反馈调整格式、评分标准、角色识别策略

---

## 附录A: 参考资源

### 开源模型 — 语音/ASR
- SenseVoice: https://github.com/FunAudioLLM/SenseVoice (HF: FunAudioLLM/SenseVoiceSmall)
- FunASR/Paraformer: https://github.com/modelscope/FunASR (MS: damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn)
- Whisper: https://github.com/openai/whisper (v20250625, MIT) + WhisperX: https://github.com/m-bain/whisperX
- WeNet: https://github.com/wenet-e2e/wenet (Apache 2.0)
- Demucs: https://github.com/facebookresearch/demucs (人声分离)
- Silero VAD: https://github.com/snakers4/silero-vad (<1ms/chunk, CPU)

### 开源模型 — 说话人/情绪
- emotion2vec: https://github.com/ddlBoJack/emotion2vec (HF: emotion2vec/emotion2vec_plus_large)
- pyannote.audio: https://github.com/pyannote/pyannote-audio (v4.0.4, MIT, HF: pyannote/speaker-diarization-3.1)
- 3D-Speaker/CAM++: https://github.com/modelscope/3D-Speaker (MS: damo/speech_campplus_sv_zh-cn_16k-common)

### 开源模型 — 视觉/视频
- Qwen2.5-VL: https://github.com/QwenLM/Qwen2.5-VL (3B/7B/72B)
- InternVL: https://github.com/OpenGVLab/InternVL (InternVL3.5系列, 1B-241B)
- CogVLM2-Video: https://github.com/THUDM/CogVLM2 (19B, 中文版)
- Video-LLaVA: https://github.com/PKU-YuanGroup/Video-LLaVA (HF: LanguageBind/Video-LLaVA-7B)

### 开源模型 — 音频事件/音乐
- PANNs: https://github.com/qiuqiangkong/panns_inference (AudioSet 527类, ~80M)
- CLAP: https://github.com/LAION-AI/CLAP (零样本音频分类)
- Essentia: https://github.com/MTG/essentia (音乐情绪/流派/BPM)
- HTS-AT: https://github.com/RetroCirce/HTS-Audio-Transformer (AudioSet SOTA, 30M)

### 开源模型 — 中文NLP
- HanLP: https://github.com/hankcs/HanLP (NER + 共指消解 + 依存句法)
- LAC: https://github.com/baidu/lac (百度中文词法分析)
- LLaMA-Factory: https://github.com/hiyouga/LLaMA-Factory (LoRA微调框架)

### 框架与工具
- LangGraph: https://github.com/langchain-ai/langgraph (Agent编排)
- Prefect: https://github.com/PrefectHQ/prefect (任务调度)
- ChromaDB: https://github.com/chroma-core/chroma (向量数据库)
- CrewAI: https://github.com/crewAIInc/crewAI (多Agent协作)
- AutoGen: https://github.com/microsoft/autogen (微软多Agent框架)

### 字幕翻译工具参考
- subtitle-translator-electron: https://github.com/gnehs/subtitle-translator-electron (1.7k stars, LLM字幕翻译)
- yuisub: https://github.com/EutropicAI/yuisub (动漫LLM翻译pipeline)

### 行业参考
- **ReelShort** (枫叶互动/中文在线) — 短剧出海头部平台，频登美区App Store榜首
- **DramaBox** (九州文化) / **ShortTV** / **FlexTV** / **GoodShort** — 主要竞品
- 短剧出海的核心模式：按集付费(pay-per-episode)，用户用虚拟币解锁下一集
- **付费墙hook是核心变现点**：翻译质量在付费边界处直接影响收入
- 短剧翻译 vs 影视翻译的关键差异：
  - 节奏极快（每集1-6分钟），每句对白情感密度极高
  - Hook密度远超传统影视（每集必须有cliffhanger）
  - 口语化/网络用语多（霸总、逆袭、打脸等题材专用词）
  - 制作周期短（天到周级别），翻译必须跟上产能
  - 成功出海的短剧往往采用"重拍"而非纯字幕翻译，但字幕翻译是快速测试市场的第一步
- 中文翻译难点（DITING框架总结）：成语翻译、词汇歧义、术语本地化、时态一致性、零代词消解、文化安全

### 学术论文
- Papalampidi et al. (EMNLP 2019) — 电影转折点检测
- Reagan et al. (2016) — 故事情感弧线的6种基本形状
- Chu & Roy (2017) — 视听情感弧线分析
- Zhang et al. (2025) DITING — 网文翻译多Agent评估框架
- Ho et al. (2024) TPMaven — 多模态转折点检测
- Zhang et al. (2026) — LLM中英翻译自动评估
- Shen et al. (2025) — 文化绑定术语的机器翻译

### 论文与数据集（新增参考）
- FunAudioLLM (SenseVoice): https://arxiv.org/abs/2407.04051
- FunASR / Paraformer: https://arxiv.org/abs/2305.11013
- BEATs (音频事件/场景): https://arxiv.org/abs/2212.09058
- PANNs (音频事件基座): https://arxiv.org/abs/1912.10211
- emotion2vec (语音情绪表征): https://arxiv.org/abs/2312.15185
- pyannote.audio (说话人分离): https://arxiv.org/abs/1911.01255
- Qwen2.5-VL (长视频理解): https://arxiv.org/abs/2502.13923
- InternVL3.5 (多模态理解): https://arxiv.org/abs/2508.18265
- Narrative Arc (结构性情感曲线): https://doi.org/10.1126/sciadv.aba2196
- Spoiler/Plot Twist Detection (hook代理任务): https://aclanthology.org/P19-1248/
- Emotional Arc for Narrative (情感弧线): https://arxiv.org/abs/2508.02132
- AudioSet (音频事件基准): https://research.google.com/audioset/dataset/
- Narrative Dialogue Dataset (speaker+emotion): https://www.nature.com/articles/s41597-026-06891-3

---

> **文档状态**: 初始设计讨论稿，待团队评审后进入POC阶段
