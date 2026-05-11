# 设计过程记录：AI评书艺人分镜剧本生成系统

> 设计周期：2026-05-10
> 参与者：AI助手 + 项目负责人
> 状态：设计阶段完成，待实现

---

## 1. 设计过程时间线

### 1.1 现有项目评估（14:31 - 14:55）

**工作内容**：全面阅读短剧翻译项目的所有已有artifact，评估现有工作进展。

**阅读材料清单**：
- README.md — 项目概述
- ARCHITECTURE_DESIGN.md (647行) — 翻译Pipeline v2架构设计
- docs/KEY_DECISIONS.md — 技术决策记录
- docs/sample_export.md — 导出样例
- docs/research/LITERATURE_SURVEY.md (749行) — 8篇论文深度综述
- docs/research/NARRATIVE.md (371行) — "评书艺人"产品叙事
- docs/research/RESEARCH_PLAN.md (303行) — 3阶段研究计划
- docs/research/ADAPTATION_PROTOTYPE_UI_PIPELINE.md (295行) — 改编系统UI+Pipeline设计
- docs/research/AGENT_DESIGN_V2.html (543行) — v2 Agent架构HTML展示
- backend/ (6个核心文件) — 翻译Pipeline后端代码
- frontend/src/ (5个页面) — React前端代码
- mvp/ (3个文件) — 早期静态原型

**评估结论**：

| 维度 | 评级 | 说明 |
|------|------|------|
| 研究与理论基础 | ⭐⭐⭐⭐⭐ | 8篇论文综述+信息论度量+爽度值公式，学术深度罕见 |
| 翻译Pipeline原型 | ⭐⭐⭐ | 前后端可运行，但AI阶段较基础 |
| 评书艺人方向 | ⭐⭐ | 设计完整但完全Mock，无真实实现 |
| 早期MVP | ⭐ | 已被React原型取代，建议归档 |

### 1.2 方向确认（14:55 - 15:00）

**决策1**：翻译Pipeline部分冻结，聚焦评书艺人改编系统。

**决策2**：下一步工作方向 — 从网文生成短剧分镜剧本，每集1-3分钟，含环境/角色/动线/镜头/对白/旁白全要素。

**决策3**：建立评估系统（爽度值/Hook强度/角色特质），生成Mock字幕。

**决策4**：构建NotebookLM式三栏交互工作台（左栏输入分析/中栏对话协作/右栏输出展示+工具箱）。

**决策5**：所有设计和思路记录为Markdown文档，便于后续查找和交接。

### 1.3 主设计文档编写（15:00 - 15:48）

**产出**：`docs/SCREENPLAY_GENERATOR_DESIGN.md`（~650行）

**设计要点**：

1. **每集=一个分镜场景**：跳过传统"文学剧本"中间态，直接在分镜级别生成。理由：短剧每集1-3分钟，场景有限，分镜更适合AI约束和评估。

2. **完整的JSON数据模型**：定义了project/character/episode/scene/shot/emotion/hook/mock_subtitle/evaluation的完整Schema，是所有后续工作的数据契约。

3. **评估系统设计**：
   - 爽度值 = |E_release - E_buildup| × trigger_quality × pacing_bonus（镜头级粒度）
   - Hook强度 = 信息悬念(40%) + 情感悬念(35%) + 新悬念(25%)
   - 角色一致性 = 台词风格(30%) + 行为模式(30%) + 情感表达(20%) + 视觉设定(20%)

4. **6阶段Pipeline**：骨架分析→模式映射→分镜生成→Hook工程→评估反馈→角色卡生成，含2个人类审核节点。

5. **三栏工作台UI设计**：详细的左栏/中栏/右栏信息架构和交互规格。

### 1.4 HTML Mock构建（15:48 - 15:53）

**产出**：`screenplay-studio/index.html`（~1200行）

**实现的功能**：
- 三栏布局（280px | flex | 380px）
- 左栏：网文骨架分析(5个情节点)、3个角色卡(点击展开完整设定)、4个场景/道具、ECharts情感目标迷你图
- 中栏：预置对话(4条消息展示生成/修改/评估流程)、可交互输入框、4个快捷操作按钮
- 右栏4个Tab：分镜(Canvas场景图+8个镜头卡片)、评估(ECharts雷达图+5维指标)、字幕(9行预览+统计)、工具箱(动线演示+分镜草图)
- 顶部：项目信息栏+集数选择器

**技术选型**：单文件HTML + TailwindCSS CDN + ECharts CDN + Canvas 2D（零依赖，可直接浏览器打开）

### 1.5 Agent Prompt工程（15:53 - 15:59）

**产出**：`docs/AGENT_PROMPTS.md`（~450行）

**设计原则**：
- 结构约束优先（必须按JSON Schema输出）
- 情感约束解码（Brahman 2020，每句对白必须与情感目标一致）
- TOT骨架引导（Wang 2025，生成时必须知道前情/当前位置/后续目标）
- 角色卡锚定（对白风格必须符合角色卡）
- 短剧法则（黄金3秒、15秒反转、付费卡点）

**6个Agent的Prompt设计**：
1. SkeletonAgent — 网文骨架提取（情节点/角色/世界观/情感弧线）
2. PatternMapper — 模式映射（5种模式模板+Gap识别+情感目标分配）
3. ScreenplayAgent — 分镜生成（最核心，含景别/运镜/动线/对白/Mock字幕）
4. HookEngineer — Hook工程（集尾Hook+集内反转点设计）
5. EvaluatorAgent — 评估反馈（5维评分+定向反馈到具体镜头）
6. CharacterCardAgent — 角色卡生成（外形/说话风格/情感表达/服装变化线/道具关联）

### 1.6 API接口规范（15:59 - 16:00）

**产出**：`docs/API_SPECIFICATION.md`（~350行）

**设计决策**：
- 复用现有FastAPI框架和文件系统存储模式
- 16个REST端点 + 10种SSE事件
- 异步任务模式：POST请求返回202，通过SSE推送进度
- 对话交互端点支持上下文（当前集/场景/镜头）

### 1.7 评估引擎实现（16:00 - 16:03）

**产出**：`docs/EVALUATION_ENGINE.md`（~500行）

**实现的计算逻辑**：
- EmotionVector数据结构（8维情感向量，含蓄压/释放强度属性）
- 爽度值计算（Pivot识别 + JSD散度trigger质量 + 节奏奖励 + 归一化）
- Hook强度（信息悬念/情感悬念/新悬念三维加权）
- 角色一致性（台词风格/行为模式/情感表达/视觉设定四维加权）
- 对白自然度（句子长度/旁白占比/对白节奏统计）
- 视觉可行性（场景数量/镜头运动难度/景别多样性）
- 综合评估引擎（达标阈值检查 + 定向改进建议生成）
- 全局评估（跨集爽度分布/付费卡点质量/Hook连贯性/模式匹配度）

---

## 2. 关键设计决策

| # | 决策项 | 结论 | 理由 | 理论支撑 |
|---|--------|------|------|---------|
| D1 | 每集粒度 | 1个分镜场景（2-4个子场景） | 短剧1-3分钟，场景有限，直接分镜级 | — |
| D2 | 生成方式 | TOT骨架→分镜，不经过文学剧本 | 减少信息损失，更适合AI约束 | Wang 2025 |
| D3 | 交互模式 | NotebookLM三栏式 | 集成输入/对话/输出，减少上下文切换 | Yao 2024 |
| D4 | 评估粒度 | 镜头级（非集级） | 1-3分钟内情感变化极快 | Schulz 2024 |
| D5 | 情感模型 | 8维（6基础+oppression+catharsis） | 短剧独有蓄压/释放维度 | RESEARCH_PLAN.md |
| D6 | 爽度公式 | 情感落差×JSD×节奏奖励 | 多因子加权比单一delta更准确 | Schulz 2024 + Zimmerman 2026 |
| D7 | 角色卡 | 独立生成，含服装变化线 | 服务于道具/服装/演员团队 | — |
| D8 | Mock字幕 | 自动生成SRT | 为后续配音/字幕团队提供参考 | — |
| D9 | 工具箱 | 分步实现，Canvas优先 | Three.js复杂度高，先用2D验证 | — |
| D10 | 对话集成 | 中栏对话直接调用LLM | 实时协作，非离线生成 | — |
| D11 | 翻译Pipeline | 冻结，基础设施可复用 | 聚焦评书艺人方向 | — |
| D12 | mvp/目录 | 建议归档 | 已被React原型完全取代 | — |
| D13 | LLM策略 | Gemini做标注+Claude做生成+混合评估 | 标注控成本，生成需质量，评估需一致性 | — |

---

## 3. 产出物清单

| 产出物 | 路径 | 行数 | 状态 |
|--------|------|------|------|
| 主设计文档 | `docs/SCREENPLAY_GENERATOR_DESIGN.md` | ~650 | ✅ 完成 |
| Agent Prompt设计 | `docs/AGENT_PROMPTS.md` | ~450 | ✅ 完成 |
| API接口规范 | `docs/API_SPECIFICATION.md` | ~350 | ✅ 完成 |
| 评估引擎实现 | `docs/EVALUATION_ENGINE.md` | ~500 | ✅ 完成 |
| 三栏HTML Mock | `screenplay-studio/index.html` | ~1200 | ✅ 完成 |
| 设计过程记录 | `docs/DESIGN_PROCESS_LOG.md` | 本文件 | ✅ 完成 |

---

## 4. 与已有文档的关系

```
已有研究基础（8篇论文+3个研究文档）
    ↓ 理论支撑
SCREENPLAY_GENERATOR_DESIGN.md（主设计）
    ├→ AGENT_PROMPTS.md（Agent实现层：Prompt工程）
    ├→ API_SPECIFICATION.md（接口层：REST API）
    ├→ EVALUATION_ENGINE.md（计算层：评估算法）
    └→ screenplay-studio/index.html（展示层：交互Mock）
```

---

## 5. 实现路线图（待执行）

### Phase 0: 数据准备（1-2天）
- [ ] 收集3-5部短剧SRT字幕
- [ ] 准备1部网文全文
- [ ] 确认8维情感标注规范

### Phase 1: 最小可用原型（2-3周）
- [ ] 创建 `backend/adaptation/` 模块骨架
- [ ] 实现 skeleton_agent.py（骨架提取）
- [ ] 实现 pattern_mapper.py（模式映射）
- [ ] 实现 screenplay_agent.py（分镜生成，核心）
- [ ] 实现 evaluator_agent.py（基础评估）
- [ ] 对接HTML Mock的对话框到真实LLM API

### Phase 2: 评估系统（2周）
- [ ] 将 EVALUATION_ENGINE.md 中的伪代码转为Python模块
- [ ] 实现爽度值/Hook/角色一致性计算
- [ ] 构建评估仪表盘前端（对接ECharts）

### Phase 3: 工具箱（2-3周）
- [ ] 分镜草图生成（Canvas 2D）
- [ ] 动线演示（SVG俯视图）
- [ ] Mock字幕编辑器
- [ ] 分镜时间线组件

### Phase 4: 高级功能（3-4周）
- [ ] 场景3D展示（Three.js）
- [ ] Mock动画（Canvas动画）
- [ ] 版本管理和对比
- [ ] PDF/ZIP导出

---

## 6. 风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM生成的分镜质量不稳定 | 对白/镜头设计可能有明显问题 | EvaluatorAgent自动检查 + 人类审核节点 |
| 8维情感标注缺乏Ground Truth | 评估引擎的准确度无法验证 | Phase 0需要人工标注种子数据 |
| 竖屏分镜设计经验不足 | AI可能生成不适合竖屏的构图 | Prompt中明确约束 + 视觉可行性评估 |
| 数据瓶颈 | 无真实短剧数据，所有设计停留在Mock | 优先收集数据（Phase 0） |
| 上下文窗口限制 | 60集的跨集一致性难以保证 | TOT骨架传递摘要而非全文 |

---

> **文档版本**: v1.0
> **最后更新**: 2026-05-10 15:04 (Asia/Shanghai)