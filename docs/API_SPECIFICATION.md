# AI评书艺人：改编系统 REST API 接口规范

> 改编系统的REST API详细设计（请求/响应Schema、错误处理、SSE事件定义）
> 日期：2026-05-10

---

## 1. API总览

### 1.1 基础信息

| 项目 | 值 |
|------|------|
| Base URL | `/api/adaptation` |
| 认证 | 无（原型阶段） |
| Content-Type | `application/json` |
| 响应格式 | JSON（除文件下载） |
| 实时更新 | SSE (Server-Sent Events) |

### 1.2 API列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/projects` | 创建改编项目 |
| GET | `/projects` | 列出所有项目 |
| GET | `/projects/{id}` | 获取项目详情 |
| POST | `/projects/{id}/upload-novel` | 上传网文原文 |
| POST | `/projects/{id}/analyze` | 运行骨架分析（Phase 1） |
| POST | `/projects/{id}/map-pattern` | 运行模式映射（Phase 2） |
| POST | `/projects/{id}/generate` | 生成分镜剧本（Phase 3） |
| POST | `/projects/{id}/evaluate` | 运行评估（Phase 5） |
| POST | `/projects/{id}/chat` | 对话交互 |
| GET | `/projects/{id}/episodes/{ep}` | 获取单集分镜剧本 |
| PUT | `/projects/{id}/episodes/{ep}` | 更新单集分镜剧本 |
| GET | `/projects/{id}/episodes/{ep}/subtitle` | 获取Mock字幕 |
| GET | `/projects/{id}/characters` | 获取角色卡列表 |
| GET | `/projects/{id}/evaluation` | 获取评估报告 |
| GET | `/projects/{id}/stream` | SSE事件流 |
| GET | `/projects/{id}/export` | 导出剧本包 |

---

## 2. 数据模型

### 2.1 Project（项目）

```json
{
  "id": 1,
  "name": "千金归来",
  "source_novel": "《重生千金：总裁别跑》",
  "pattern": "revenge_ladder",
  "total_episodes": 60,
  "target_audience": "女性18-34",
  "paywall_range": "EP8-10",
  "status": "created|analyzing|mapped|generating|completed",
  "phase": "phase0|phase1|phase2|phase3|phase4|phase5",
  "created_at": "2026-05-10T14:00:00Z",
  "updated_at": "2026-05-10T14:30:00Z",
  "stats": {
    "total_episodes": 60,
    "generated_episodes": 3,
    "evaluated_episodes": 1,
    "avg_shuang_score": 7.2,
    "avg_hook_strength": 4.1,
    "avg_consistency": 0.92,
    "source_ratio": {
      "original": 0.62,
      "augmented": 0.28,
      "adjusted": 0.10
    }
  }
}
```

### 2.2 Episode（分镜剧本）

```json
{
  "id": "EP001",
  "episode_number": 1,
  "title": "命运的转折",
  "project_id": 1,
  "duration_target": "1:30",
  "duration_estimate": "1:25",
  "status": "outline|generating|generated|evaluated|approved",
  "version": 3,
  "emotion_target": {
    "arc_type": "man_in_a_hole",
    "shuang_target": 6.5,
    "hook_type": "suspense",
    "primary_emotion_flow": ["oppression", "catharsis", "surprise"]
  },
  "scenes": [],
  "hook_ending": {},
  "mock_subtitle": [],
  "evaluation": {},
  "source_trace": {},
  "created_at": "",
  "updated_at": ""
}
```

---

## 3. API详细定义

### 3.1 创建项目

**POST `/api/adaptation/projects`**

Request:
```json
{
  "name": "千金归来",
  "source_novel": "《重生千金：总裁别跑》",
  "pattern": "revenge_ladder|identity_onion|romance_rollercoaster|upgrade_monster|mystery_progressive",
  "total_episodes": 60,
  "target_audience": "女性18-34",
  "paywall_start": 8,
  "paywall_end": 10
}
```

Response 201:
```json
{
  "id": 1,
  "name": "千金归来",
  "status": "created",
  "message": "项目创建成功，请上传网文原文"
}
```

### 3.2 上传网文

**POST `/api/adaptation/projects/{id}/upload-novel`**

Content-Type: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 网文原文文件（.txt/.epub） |
| encoding | string | 编码（可选，默认UTF-8） |

Response 200:
```json
{
  "message": "网文上传成功",
  "file_info": {
    "filename": "novel.txt",
    "size_bytes": 204800,
    "encoding": "UTF-8",
    "estimated_chapters": 200,
    "word_count": 500000
  }
}
```

### 3.3 运行骨架分析

**POST `/api/adaptation/projects/{id}/analyze`**

启动Phase 1：SkeletonAgent分析网文骨架。异步执行，通过SSE推送进度。

Response 202:
```json
{
  "message": "骨架分析已启动",
  "task_id": "task_001",
  "estimated_duration": "2-5分钟",
  "sse_endpoint": "/api/adaptation/projects/1/stream"
}
```

SSE事件：
```
event: phase_start
data: {"phase": "skeleton", "status": "running"}

event: phase_progress
data: {"phase": "skeleton", "step": "extracting_plot_points", "progress": 30}

event: phase_complete
data: {"phase": "skeleton", "status": "completed", "result_summary": {"plot_points": 12, "characters": 6, "world_rules": 8}}
```

### 3.4 运行模式映射

**POST `/api/adaptation/projects/{id}/map-pattern`**

Request (可选，覆盖创建时的设置):
```json
{
  "pattern": "revenge_ladder",
  "total_episodes": 60,
  "paywall_start": 8,
  "paywall_end": 10,
  "custom_adjustments": [
    {"episode": 5, "change": "增加一个身份揭露场景"}
  ]
}
```

Response 202:
```json
{
  "message": "模式映射已启动",
  "task_id": "task_002",
  "estimated_duration": "3-5分钟"
}
```

### 3.5 生成分镜剧本

**POST `/api/adaptation/projects/{id}/generate`**

Request:
```json
{
  "episode_numbers": [1, 2, 3],
  "regenerate": false,
  "custom_instructions": "EP1的苏晚晴台词增加嘲讽感"
}
```

Response 202:
```json
{
  "message": "分镜生成已启动",
  "episodes": [1, 2, 3],
  "task_id": "task_003",
  "estimated_duration": "每集1-3分钟"
}
```

### 3.6 运行评估

**POST `/api/adaptation/projects/{id}/evaluate`**

Request:
```json
{
  "episode_numbers": [1, 2, 3],
  "dimensions": ["shuang", "hook", "consistency", "dialogue", "feasibility"]
}
```

Response 202:
```json
{
  "message": "评估已启动",
  "task_id": "task_004"
}
```

### 3.7 对话交互

**POST `/api/adaptation/projects/{id}/chat`**

Request:
```json
{
  "message": "苏晚晴在EP1 S02的台词太直白了，增加嘲讽感",
  "context": {
    "current_episode": 1,
    "current_scene": "S02",
    "current_shot": "S02-02"
  }
}
```

Response 200:
```json
{
  "response": "已修改S02-02的苏晚晴台词...",
  "changes": [
    {
      "type": "dialogue_update",
      "location": "S02-02",
      "old_value": "找谁？我回自己的公司，还需要找谁？",
      "new_value": "找谁？",
      "additional": "（停顿1.5秒）不用找了。我自己进去。",
      "emotion_impact": {
        "sarcasm": {"old": 3, "new": 6},
        "oppression": {"old": 4, "new": 6}
      },
      "shuang_impact": {"old": 6.2, "new": 6.8}
    }
  ],
  "auto_evaluation": {
    "shuang_score": 6.8,
    "consistency_check": "passed",
    "notes": "符合角色卡嘲讽模式"
  }
}
```

### 3.8 获取单集分镜

**GET `/api/adaptation/projects/{id}/episodes/{ep}`**

Response 200: 完整的episode JSON（参见SCREENPLAY_GENERATOR_DESIGN.md中的数据模型）

Query参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| version | int | 指定版本（默认最新） |
| include | string | 逗号分隔：scenes,evaluation,subtitle,hook |

### 3.9 更新单集

**PUT `/api/adaptation/projects/{id}/episodes/{ep}`**

Request: 部分更新的episode数据
```json
{
  "scenes": [...],
  "version_comment": "修改了S02的对白"
}
```

Response 200:
```json
{
  "message": "已保存",
  "version": 4,
  "auto_evaluation": {
    "shuang_score": 6.8,
    "consistency": 0.93
  }
}
```

### 3.10 SSE事件流

**GET `/api/adaptation/projects/{id}/stream`**

事件类型：

| 事件 | 数据 | 说明 |
|------|------|------|
| `phase_start` | `{phase, status}` | 阶段开始 |
| `phase_progress` | `{phase, step, progress(0-100)}` | 阶段进度 |
| `phase_complete` | `{phase, status, result_summary}` | 阶段完成 |
| `phase_error` | `{phase, error, retry_available}` | 阶段错误 |
| `episode_generated` | `{episode_number, version}` | 单集生成完成 |
| `evaluation_result` | `{episode_number, scores}` | 评估完成 |
| `chat_response` | `{message, changes}` | 对话响应 |
| `version_created` | `{episode_number, version, comment}` | 版本创建 |
| `quality_alert` | `{episode_number, dimension, value, threshold}` | 质量警告 |
| `heartbeat` | `{ts}` | 心跳（每30秒） |

### 3.11 导出剧本包

**GET `/api/adaptation/projects/{id}/export`**

Query参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| format | string | `zip`（默认）, `markdown`, `pdf` |
| include | string | `screenplay,character_cards,evaluation,subtitle` |
| episodes | string | `all` 或 `1,2,3,...` |

Response 200: 二进制文件流（Content-Disposition: attachment）

---

## 4. 错误处理

### 4.1 错误响应格式

```json
{
  "error": {
    "code": "NOVEL_NOT_UPLOADED",
    "message": "请先上传网文原文",
    "details": "项目ID=1当前状态为'created'，需要先上传网文文件",
    "suggestion": "调用 POST /projects/1/upload-novel"
  }
}
```

### 4.2 错误码

| HTTP状态码 | 错误码 | 说明 |
|-----------|--------|------|
| 400 | INVALID_PATTERN | 不支持的改编模式 |
| 400 | INVALID_EPISODE_RANGE | 集数范围无效 |
| 404 | PROJECT_NOT_FOUND | 项目不存在 |
| 404 | EPISODE_NOT_FOUND | 集不存在 |
| 409 | PHASE_IN_PROGRESS | 阶段正在进行中 |
| 409 | NOVEL_NOT_UPLOADED | 网文未上传 |
| 422 | LLM_GENERATION_FAILED | LLM生成失败 |
| 422 | INVALID_JSON_RESPONSE | LLM返回非JSON |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

---

## 5. 后端文件存储结构

```
data/adaptation_projects/{project_id}/
├── project.json                    # 项目元数据
├── novel/                          # 网文原文
│   ├── raw.txt
│   └── chunks/                     # 分章文件
│       ├── chapter_001.txt
│       └── ...
├── skeleton/                       # Phase 1 输出
│   ├── skeleton.json
│   ├── character_registry.json
│   └── world_rules.json
├── mapping/                        # Phase 2 输出
│   ├── toc_skeleton.json
│   └── gap_analysis.json
├── episodes/                       # Phase 3 输出
│   ├── ep001/
│   │   ├── screenplay.json         # 完整分镜剧本
│   │   ├── screenplay_v1.json      # 历史版本
│   │   ├── screenplay_v2.json
│   │   ├── mock_subtitle.srt       # Mock字幕
│   │   ├── evaluation.json         # 评估报告
│   │   └── hooks.json              # Hook数据
│   └── ...
├── characters/                     # Phase 6 输出
│   ├── char_001_card.json
│   └── ...
├── evaluation/                     # 全局评估
│   ├── benchmark_report.json
│   └── pattern_fit.json
├── chat/                           # 对话历史
│   └── history.jsonl
└── logs/
    └── pipeline.log
```

---

> **文档状态**: v1.0，待后端实现时迭代