import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Row, Col, Tag, Typography, Descriptions, Steps, Table, Button,
  Space, Badge, Divider, Alert,
} from 'antd'
import { ArrowLeftOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import ReactEChartsCore from 'echarts-for-react'
import { api } from '../services/api'
import type { EpisodeDetail } from '../types'

const stageNames: Record<string, string> = {
  s1: 'S1 Subtitle Check', s2: 'S2 Character ID', s3: 'S3 Emotion',
  s5: 'S5 Script Gen', s6: 'S6 Emotion Mgmt', s7: 'S7 Hook Analysis', qa: 'QA Review',
}

const hookTypeLabels: Record<string, string> = {
  suspense: 'Suspense', reversal: 'Reversal', emotional: 'Emotional',
  threat: 'Threat', reveal: 'Reveal', choice: 'Choice',
}

const riskColors: Record<string, string> = {
  LOW: 'green', MEDIUM: 'orange', HIGH: 'red',
}

export default function EpisodeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [ep, setEp] = useState<EpisodeDetail | null>(null)

  useEffect(() => {
    api.getEpisode(Number(id)).then(setEp)
  }, [id])

  if (!ep) return null

  // Emotion chart
  const emotionChartOption = ep.emotions ? {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ep.emotions.dialogues.map((d, i) => `${d.speaker}`),
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: { type: 'value', min: 0, max: 10, name: 'Intensity' },
    series: [{
      type: 'line',
      data: ep.emotions.dialogues.map(d => d.score),
      smooth: true,
      areaStyle: { opacity: 0.15 },
      markPoint: {
        data: [
          { type: 'max', name: 'Peak' },
          { type: 'min', name: 'Low' },
        ],
      },
      markLine: {
        data: [{ type: 'average', name: 'Avg' }],
      },
      itemStyle: {
        color: (params: any) => {
          const score = params.value
          if (score >= 8) return '#ff4d4f'
          if (score >= 6) return '#fa8c16'
          if (score >= 4) return '#1677ff'
          return '#52c41a'
        },
      },
    }],
    grid: { left: 50, right: 20, bottom: 60, top: 30 },
  } : null

  const dialogueColumns = [
    { title: '#', dataIndex: 'index', width: 40, render: (_: any, __: any, i: number) => i + 1 },
    {
      title: 'Speaker', dataIndex: 'speaker', width: 100,
      render: (s: string) => <Tag color={s === '旁白' ? 'default' : 'blue'}>{s}</Tag>,
    },
    { title: 'Dialogue', dataIndex: 'text', ellipsis: true },
    {
      title: 'Emotion', dataIndex: 'emotion', width: 100,
      render: (e: string) => <Tag>{e}</Tag>,
    },
    {
      title: 'Score', dataIndex: 'score', width: 70, align: 'center' as const,
      render: (s: number) => (
        <span style={{ color: s >= 8 ? '#ff4d4f' : s >= 6 ? '#fa8c16' : s >= 4 ? '#1677ff' : '#52c41a', fontWeight: 600 }}>
          {s}/10
        </span>
      ),
    },
    {
      title: 'Confidence', dataIndex: 'confidence', width: 90, align: 'center' as const,
      render: (c: number) => c ? `${Math.round(c * 100)}%` : '-',
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* Header */}
        <Col span={24}>
          <Card>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>Back</Button>
              <Typography.Title level={4} style={{ margin: 0 }}>
                EP{ep.episode_number} - {ep.title || 'Untitled'}
              </Typography.Title>
              <Tag color={ep.status === 'completed' ? 'success' : ep.status === 'running' ? 'processing' : 'default'}>
                {ep.status.toUpperCase()}
              </Tag>
            </Space>
          </Card>
        </Col>

        {/* Pipeline Stages */}
        <Col span={24}>
          <Card title="Pipeline Stages" size="small">
            <Steps
              size="small" current={-1}
              items={Object.entries(stageNames).map(([key, name]) => ({
                title: name,
                status: ep.stages[key] === 'completed' ? 'finish' :
                        ep.stages[key] === 'running' ? 'process' :
                        ep.stages[key] === 'failed' ? 'error' : 'wait',
              }))}
            />
          </Card>
        </Col>

        {/* S1: Subtitle Data */}
        {ep.subtitle_data && (
          <Col span={12}>
            <Card title="S1 - Subtitle Verification" size="small">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="Lines">{ep.subtitle_data.total_lines}</Descriptions.Item>
                <Descriptions.Item label="Duration">{ep.subtitle_data.duration}s</Descriptions.Item>
                <Descriptions.Item label="ASR Match">
                  <span style={{ color: ep.subtitle_data.asr_match_rate > 0.95 ? '#52c41a' : '#fa8c16' }}>
                    {(ep.subtitle_data.asr_match_rate * 100).toFixed(1)}%
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="Speakers">{ep.subtitle_data.speakers_detected}</Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        )}

        {/* S2: Characters */}
        {ep.characters && (
          <Col span={12}>
            <Card title="S2 - Characters Detected" size="small">
              {ep.characters.map((c: any, i: number) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <Tag color="blue">{c.name}</Tag>
                  {c.aliases?.map((a: string, j: number) => <Tag key={j}>{a}</Tag>)}
                  {c.role && <Tag color={c.role === 'protagonist' ? 'gold' : c.role === 'antagonist' ? 'red' : 'default'}>{c.role}</Tag>}
                </div>
              ))}
            </Card>
          </Col>
        )}

        {/* S3: Emotion Chart */}
        {emotionChartOption && (
          <Col span={24}>
            <Card title="S3 - Emotion Arc" size="small"
              extra={<span>Avg Intensity: <strong>{ep.emotions?.average_intensity}/10</strong></span>}>
              <ReactEChartsCore option={emotionChartOption} style={{ height: 280 }} />
            </Card>
          </Col>
        )}

        {/* S3: Dialogue Table */}
        {ep.emotions && (
          <Col span={24}>
            <Card title="Dialogue with Emotion Annotations" size="small">
              <Table dataSource={ep.emotions.dialogues} columns={dialogueColumns}
                rowKey={(_, i) => String(i)} pagination={false} size="small" />
            </Card>
          </Col>
        )}

        {/* S5: Script */}
        {ep.script && (
          <Col span={16}>
            <Card title="S5 - Generated Script" size="small">
              <pre style={{
                whiteSpace: 'pre-wrap', fontFamily: 'inherit',
                fontSize: 13, lineHeight: 1.8, maxHeight: 400, overflow: 'auto',
                background: '#fafafa', padding: 16, borderRadius: 6,
              }}>
                {ep.script}
              </pre>
            </Card>
          </Col>
        )}

        {/* S6 + S7: Emotion Analysis & Hook */}
        <Col span={8}>
          {ep.emotion_analysis && (
            <Card title="S6 - Emotion Analysis" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Arc Type">
                  <Tag color="purple">{ep.emotion_analysis.arc_type}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Peak Time">{ep.emotion_analysis.peak_time}</Descriptions.Item>
                <Descriptions.Item label="Reversals">{ep.emotion_analysis.reversals.length}</Descriptions.Item>
              </Descriptions>
              {ep.emotion_analysis.reversals.map((r, i) => (
                <div key={i} style={{ marginTop: 8, padding: 8, background: '#fff7e6', borderRadius: 4, fontSize: 12 }}>
                  Reversal: {r.from_emotion}({r.from_score}) {'\u2192'} {r.to_emotion}({r.to_score}) [delta={r.delta}]
                </div>
              ))}
            </Card>
          )}

          {ep.hooks && (
            <Card title="S7 - Hook Analysis" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Type">
                  <Tag color="geekblue">{hookTypeLabels[ep.hooks.type] || ep.hooks.type}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Attraction">
                  <span style={{ fontWeight: 600, color: ep.hooks.attraction_score >= 8 ? '#ff4d4f' : '#1677ff' }}>
                    {ep.hooks.attraction_score}/10
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="Continuity">{ep.hooks.continuity_score}/10</Descriptions.Item>
                <Descriptions.Item label="Translation Risk">
                  <Tag color={riskColors[ep.hooks.translation_risk]}>{ep.hooks.translation_risk}</Tag>
                </Descriptions.Item>
              </Descriptions>
              <div style={{ marginTop: 8, padding: 8, background: '#f0f5ff', borderRadius: 4, fontSize: 13 }}>
                "{ep.hooks.content}"
              </div>
              {ep.hooks.risk_reason && (
                <Alert type="warning" message={ep.hooks.risk_reason} style={{ marginTop: 8 }} showIcon />
              )}
            </Card>
          )}

          {/* QA */}
          {ep.qa_result && (
            <Card title="QA Review" size="small"
              extra={ep.qa_result.passed ?
                <Tag icon={<CheckCircleOutlined />} color="success">PASSED</Tag> :
                <Tag icon={<WarningOutlined />} color="error">NEEDS REVIEW</Tag>
              }>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Overall">{ep.qa_result.overall_score}/10</Descriptions.Item>
                <Descriptions.Item label="ASR Quality">{ep.qa_result.asr_quality}/10</Descriptions.Item>
                <Descriptions.Item label="Character">{ep.qa_result.character_consistency}/10</Descriptions.Item>
                <Descriptions.Item label="Emotion Cal.">{ep.qa_result.emotion_calibration}/10</Descriptions.Item>
              </Descriptions>
              {ep.qa_result.issues.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {ep.qa_result.issues.map((issue, i) => (
                    <Alert key={i} type="warning" message={issue} style={{ marginTop: 4 }} showIcon />
                  ))}
                </div>
              )}
            </Card>
          )}
        </Col>

        {/* Summary */}
        {ep.summary && (
          <Col span={24}>
            <Card title="Episode Summary" size="small">
              <Typography.Paragraph>{ep.summary}</Typography.Paragraph>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  )
}
