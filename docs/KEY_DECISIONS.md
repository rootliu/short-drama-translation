# Key Decisions

## Product Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Positioning | Hybrid (real AI + mock fallback) | Use free Gemini API where possible, mock the rest |
| Translation mode | Context-aware | Leverage character/emotion/plot context for higher quality translation |
| Input method | Dual entry: SRT upload + Video upload | SRT for immediate processing, video for ASR pipeline |
| Priority | Core translation + Dashboard in parallel | Ship working pipeline while improving monitoring |
| Export format | Markdown script | Lightweight, includes character/emotion annotations, easy to review |

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | Gemini 2.5 Flash (free tier) | Best available free model; 2.0-flash quota exhausted, 2.5-flash works |
| LLM Fallback | Auto mock when API unavailable | Pipeline never blocks on API failures; graceful degradation |
| Backend | FastAPI + SQLite | Lightweight, async-capable, good for prototype |
| Frontend | React 18 + Ant Design + ECharts | Rich UI components, good charting support |
| Real-time updates | Server-Sent Events (SSE) | Simpler than WebSocket for one-way progress updates |
| Subtitle parsing | Custom SRT/ASS parser | Multi-encoding support (UTF-8/GBK/Big5), speaker extraction |
| File storage | Local uploads/ directory | Simple for prototype, easy to migrate to S3 later |

## Pipeline Design (DAG)

```
S1 (Subtitle Check) --> S2 (Character ID) --|
                    --> S3 (Emotion)     --|-> S5 (Translation) --> S6 (Emotion Arc) --|
                                                                --> S7 (Hook)        --|-> QA
```

- S2 & S3 run in parallel (both depend only on S1)
- S6 & S7 run in parallel (both depend only on S5)
- Max concurrency per batch: 3 episodes simultaneous

## AI Stage Implementation

| Stage | AI (Gemini) | Mock Fallback |
|-------|-------------|---------------|
| S1 Subtitle Check | Skipped (handled by SRT parser/Whisper) | Pre-built dialogue sets |
| S2 Character ID | Analyzes dialogue to identify characters, roles, aliases | Predefined character list |
| S3 Emotion | Labels each line with emotion type + intensity 1-10 | Random emotion assignment |
| S5 Translation | Context-aware CN->EN translation with character voice preservation | Mock script generation |
| S6 Emotion Arc | Identifies arc type, peak, reversals across episode | Random arc assignment |
| S7 Hook Analysis | Evaluates episode-ending hooks, translation risk | Sample hook templates |
| QA Review | Multi-dimensional quality scoring | Random score generation |

## Architecture Diagrams

See `docs/diagrams/` for:
- `system_architecture.drawio` - Overall system architecture
- `pipeline_4rounds.drawio` - Pipeline execution flow
- `model_interactions.drawio` - Model interaction patterns
