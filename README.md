# Short Drama Translation Pipeline

AI-powered pipeline for Chinese short drama pre-translation analysis, targeting overseas audiences (English first, Japanese later).

## Overview

This system performs comprehensive pre-translation analysis of Chinese short dramas through a 7-stage pipeline:

| Stage | Name | Description |
|-------|------|-------------|
| S1 | Subtitle Verification | Subtitle + speaker diarization verification |
| S2 | Character ID | Character identification and tracking |
| S3 | Emotion Extraction | Dual-channel emotion analysis (audio + text) |
| S4 | Scene Description | Visual scene understanding (Phase 3) |
| S5 | Script Generation | Translation-ready script generation |
| S6 | Emotion Management | Emotional arc analysis and reversal detection |
| S7 | Hook Analysis | Narrative hook extraction with translation risk |

Stages S2/S3 run in parallel, as do S6/S7. A QA Agent performs 3-iteration reflection loops for quality assurance.

## Architecture

See [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md) for the full design document covering:
- Model selection benchmarks (FunASR, SenseVoice, emotion2vec+, etc.)
- Agent architecture (LangGraph + Prefect/Celery)
- Shared memory design (PostgreSQL + ChromaDB + Redis)
- Cost estimates and phased roadmap

## Prototype

The current prototype includes a **Planning & Monitoring Dashboard** with:
- Project management with batch processing
- Real-time pipeline progress via SSE
- 7-stage pipeline visualization (DAG view)
- Episode detail with emotion charts, hook analysis, QA scores
- Mock data simulating a CEO revenge drama scenario

### Quick Start

```bash
# Install dependencies
cd backend && pip3 install -r requirements.txt
cd ../frontend && npm install

# Start both services
chmod +x start.sh
./start.sh
```

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Ant Design + ECharts
- **Backend**: Python FastAPI + SQLAlchemy + SQLite
- **Real-time**: Server-Sent Events (SSE)

## Project Structure

```
short-drama-translation/
├── ARCHITECTURE_DESIGN.md    # Full architecture design
├── start.sh                  # One-click startup
├── backend/
│   ├── main.py               # FastAPI routes + SSE
│   ├── database.py           # SQLAlchemy models
│   ├── pipeline.py           # DAG-based pipeline orchestration
│   ├── mock_data.py          # Realistic Chinese drama mock data
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Project list + stats
│   │   │   ├── ProjectDetail.tsx   # Batch mgmt + episode monitor
│   │   │   └── EpisodeDetail.tsx   # Full episode analysis view
│   │   ├── components/
│   │   │   └── PipelineDAG.tsx     # Visual pipeline DAG
│   │   ├── services/api.ts         # API client + SSE
│   │   └── types/index.ts          # TypeScript types
│   └── package.json
└── mvp/                      # Early static MVP prototype
```

## Development Phases

1. **Phase 1** (Current): S1→S2→S3→S5 minimum loop, deliver translation pack to human translators
2. **Phase 2**: Add S6, S7, full QA agent, cross-episode character tracking
3. **Phase 3**: Add S4 (visual scene), video understanding, multi-language support

## License

MIT
