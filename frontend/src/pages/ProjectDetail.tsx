import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Row, Col, Button, Tag, Table, Statistic, Progress, Space,
  Typography, Tabs, List, Badge, Descriptions, Tooltip, message,
} from 'antd'
import {
  PlayCircleOutlined, CheckCircleOutlined, SyncOutlined,
  ClockCircleOutlined, EyeOutlined, WarningOutlined,
  UploadOutlined, InboxOutlined, RobotOutlined, DownloadOutlined,
} from '@ant-design/icons'
import Dragger from 'antd/es/upload/Dragger'
import ReactEChartsCore from 'echarts-for-react'
import { api, createEventSource } from '../services/api'
import type { Project, BatchInfo, EpisodeListItem, ProjectStats, PipelineLog } from '../types'
import PipelineDAG from '../components/PipelineDAG'

const stageLabels: Record<string, string> = {
  s1: 'S1 Subtitle', s2: 'S2 Character', s3: 'S3 Emotion',
  s5: 'S5 Script', s6: 'S6 Emotion Mgmt', s7: 'S7 Hook', qa: 'QA',
}

const statusIcon = (s: string) => {
  if (s === 'completed') return <CheckCircleOutlined style={{ color: '#52c41a' }} />
  if (s === 'running') return <SyncOutlined spin style={{ color: '#1677ff' }} />
  if (s === 'failed') return <WarningOutlined style={{ color: '#ff4d4f' }} />
  return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const navigate = useNavigate()
  const [project, setProject] = useState<any>(null)
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [episodes, setEpisodes] = useState<EpisodeListItem[]>([])
  const [logs, setLogs] = useState<PipelineLog[]>([])
  const [selectedBatch, setSelectedBatch] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [sysStatus, setSysStatus] = useState<any>(null)
  const esRef = useRef<EventSource | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [p, s, l] = await Promise.all([
        api.getProject(projectId),
        api.getProjectStats(projectId),
        api.getProjectLogs(projectId, 100),
      ])
      setProject(p)
      setStats(s)
      setLogs(l)
      if (p.batches?.length > 0 && !selectedBatch) {
        setSelectedBatch(p.batches[0].id)
      }
    } finally {
      setLoading(false)
    }
  }, [projectId, selectedBatch])

  useEffect(() => { load() }, [load])
  useEffect(() => { api.getSystemStatus().then(setSysStatus).catch(() => {}) }, [])

  // Load episodes when batch is selected
  useEffect(() => {
    if (selectedBatch) {
      api.getBatchEpisodes(projectId, selectedBatch).then(setEpisodes)
    }
  }, [projectId, selectedBatch])

  // SSE for real-time updates
  useEffect(() => {
    const es = createEventSource(projectId)
    esRef.current = es

    const handleUpdate = () => {
      load()
      if (selectedBatch) {
        api.getBatchEpisodes(projectId, selectedBatch).then(setEpisodes)
      }
    }

    es.addEventListener('stage_update', handleUpdate)
    es.addEventListener('episode_complete', handleUpdate)
    es.addEventListener('batch_complete', handleUpdate)
    es.addEventListener('batch_progress', handleUpdate)

    return () => { es.close() }
  }, [projectId, selectedBatch, load])

  const handleStartBatch = async (batchId: number) => {
    try {
      await api.startBatch(projectId, batchId)
      message.success('Batch processing started')
      load()
    } catch (e: any) {
      message.error(e.message)
    }
  }

  if (!project) return null

  const batchColumns = [
    {
      title: 'Batch', dataIndex: 'batch_number', width: 80,
      render: (n: number) => `#${n}`,
    },
    {
      title: 'Episodes', key: 'range', width: 120,
      render: (_: any, r: BatchInfo) => `EP${r.start_episode}-${r.end_episode}`,
    },
    {
      title: 'Progress', key: 'progress', width: 200,
      render: (_: any, r: BatchInfo) => (
        <Progress percent={r.progress} size="small" status={r.status === 'processing' ? 'active' : undefined} />
      ),
    },
    {
      title: 'Status', dataIndex: 'status', width: 120,
      render: (s: string) => (
        <Tag color={s === 'completed' ? 'success' : s === 'processing' ? 'processing' : 'default'}>
          {s.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Actions', key: 'actions', width: 200,
      render: (_: any, r: BatchInfo) => (
        <Space>
          {r.status === 'created' && (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />}
              onClick={() => handleStartBatch(r.id)}>Start</Button>
          )}
          <Button size="small" icon={<EyeOutlined />}
            onClick={() => setSelectedBatch(r.id)}>View</Button>
        </Space>
      ),
    },
  ]

  const episodeColumns = [
    {
      title: 'EP', dataIndex: 'episode_number', width: 60,
      render: (n: number) => `${n}`,
    },
    { title: 'Title', dataIndex: 'title', width: 140, ellipsis: true },
    ...Object.entries(stageLabels).map(([key, label]) => ({
      title: <Tooltip title={label}>{key.toUpperCase()}</Tooltip>,
      dataIndex: `${key}_status`,
      width: 60,
      align: 'center' as const,
      render: (s: string) => statusIcon(s),
    })),
    {
      title: 'QA', key: 'qa_passed', width: 60, align: 'center' as const,
      render: (_: any, r: EpisodeListItem) =>
        r.qa_passed === true ? <Badge status="success" /> :
        r.qa_passed === false ? <Badge status="error" /> :
        <Badge status="default" />,
    },
    {
      title: '', key: 'actions', width: 70,
      render: (_: any, r: EpisodeListItem) => (
        <Button size="small" type="link" disabled={r.status !== 'completed'}
          onClick={() => navigate(`/episode/${r.id}`)}>Detail</Button>
      ),
    },
  ]

  // Stats charts
  const hookChartOption = stats?.hook_type_distribution ? {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: Object.entries(stats.hook_type_distribution).map(([k, v]) => ({
        name: k, value: v,
      })),
      label: { show: true, formatter: '{b}: {c}' },
    }],
  } : null

  const arcChartOption = stats?.arc_type_distribution ? {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: Object.entries(stats.arc_type_distribution).map(([k, v]) => ({
        name: k, value: v,
      })),
      label: { show: true, formatter: '{b}: {c}' },
    }],
  } : null

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* Header */}
        <Col span={24}>
          <Card>
            <Row justify="space-between" align="middle">
              <Col>
                <Typography.Title level={4} style={{ margin: 0 }}>{project.name}</Typography.Title>
                <Typography.Text type="secondary">{project.description}</Typography.Text>
              </Col>
              <Col>
                <Space>
                  <Tag>{project.total_episodes} episodes</Tag>
                  <Tag>Batch size: {project.batch_size}</Tag>
                  <Tag color="blue">Target: {project.target_language.toUpperCase()}</Tag>
                  <Button icon={<DownloadOutlined />} href={api.exportMarkdown(projectId)} target="_blank">
                    Export MD
                  </Button>
                  <Tag color={project.status === 'processing' ? 'processing' : project.status === 'completed' ? 'success' : 'default'}>
                    {project.status.toUpperCase()}
                  </Tag>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* Stats */}
        {stats && stats.completed_episodes > 0 && (
          <>
            <Col span={4}><Card><Statistic title="Completed" value={stats.completed_episodes} suffix={`/ ${stats.total_episodes}`} /></Card></Col>
            <Col span={4}><Card><Statistic title="Processing" value={stats.processing_episodes} valueStyle={{ color: '#1677ff' }} /></Card></Col>
            <Col span={4}><Card><Statistic title="Avg Intensity" value={stats.avg_emotion_intensity} suffix="/ 10" /></Card></Col>
            <Col span={4}><Card><Statistic title="Reversals" value={stats.total_reversals} /></Card></Col>
            <Col span={4}><Card><Statistic title="QA Pass" value={stats.qa_pass_rate} suffix="%" valueStyle={{ color: stats.qa_pass_rate >= 80 ? '#52c41a' : '#ff4d4f' }} /></Card></Col>
            <Col span={4}><Card><Statistic title="Characters" value={project.characters?.length || 0} /></Card></Col>
          </>
        )}

        {/* Pipeline DAG */}
        <Col span={24}>
          <Card title="Pipeline DAG" size="small">
            <PipelineDAG />
          </Card>
        </Col>

        {/* Main Tabs */}
        <Col span={24}>
          <Card>
            <Tabs items={[
              {
                key: 'batches',
                label: 'Batch Management',
                children: (
                  <div>
                    <Table dataSource={project.batches || []} columns={batchColumns}
                      rowKey="id" pagination={false} size="small" />
                  </div>
                ),
              },
              {
                key: 'episodes',
                label: `Episode Monitor${selectedBatch ? '' : ' (select batch)'}`,
                children: (
                  <Table dataSource={episodes} columns={episodeColumns}
                    rowKey="id" pagination={{ pageSize: 20 }} size="small"
                    scroll={{ x: 900 }} />
                ),
              },
              {
                key: 'characters',
                label: `Characters (${project.characters?.length || 0})`,
                children: (
                  <List
                    dataSource={project.characters || []}
                    renderItem={(char: any) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<span>{char.name} <Tag>{char.aliases?.join(', ')}</Tag></span>}
                          description={char.description}
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: 'Characters will appear after batch processing completes.' }}
                  />
                ),
              },
              {
                key: 'analysis',
                label: 'Analysis',
                children: stats && stats.completed_episodes > 0 ? (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title="Hook Type Distribution" size="small">
                        {hookChartOption && <ReactEChartsCore option={hookChartOption} style={{ height: 300 }} />}
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="Emotion Arc Distribution" size="small">
                        {arcChartOption && <ReactEChartsCore option={arcChartOption} style={{ height: 300 }} />}
                      </Card>
                    </Col>
                  </Row>
                ) : <Typography.Text type="secondary">Process episodes to see analysis.</Typography.Text>,
              },
              {
                key: 'upload',
                label: <span><UploadOutlined /> Upload Files</span>,
                children: (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title="Batch Upload Subtitles (SRT/ASS)" size="small">
                        <Dragger
                          multiple
                          accept=".srt,.ass,.ssa,.vtt"
                          customRequest={async ({ file, onSuccess, onError }) => {
                            // Collect files for batch upload
                            try {
                              const result = await api.batchUploadSubtitles(projectId, [file as File])
                              onSuccess?.(result)
                              message.success(`Uploaded: ${(file as File).name}`)
                              load()
                              if (selectedBatch) api.getBatchEpisodes(projectId, selectedBatch).then(setEpisodes)
                            } catch (e: any) {
                              onError?.(e)
                              message.error(e.message)
                            }
                          }}
                          showUploadList
                        >
                          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                          <p className="ant-upload-text">Drop SRT/ASS files here</p>
                          <p className="ant-upload-hint">Files are matched to episodes by filename order</p>
                        </Dragger>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="Upload Video (for ASR)" size="small">
                        <Dragger
                          multiple
                          accept=".mp4,.mkv,.avi,.mov,.webm"
                          customRequest={async ({ file, onSuccess, onError }) => {
                            try {
                              const result = await api.batchUploadSubtitles(projectId, [file as File])
                              onSuccess?.(result)
                              message.success(`Video uploaded: ${(file as File).name}`)
                              load()
                            } catch (e: any) {
                              onError?.(e)
                              message.error(e.message)
                            }
                          }}
                          showUploadList
                        >
                          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                          <p className="ant-upload-text">Drop video files here</p>
                          <p className="ant-upload-hint">Video will be processed with ASR (Whisper)</p>
                        </Dragger>
                      </Card>
                    </Col>
                    <Col span={24} style={{ marginTop: 16 }}>
                      <Card size="small">
                        <Space>
                          <RobotOutlined />
                          <Typography.Text>
                            LLM Status: {sysStatus?.llm_available ?
                              <Tag color="success">Gemini Connected</Tag> :
                              <Tag color="warning">Mock Mode (no API key)</Tag>
                            }
                          </Typography.Text>
                          <Typography.Text type="secondary">
                            Supported: {sysStatus?.supported_formats?.subtitle?.join(', ')}
                          </Typography.Text>
                        </Space>
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'logs',
                label: 'Pipeline Logs',
                children: (
                  <List
                    dataSource={logs}
                    size="small"
                    style={{ maxHeight: 400, overflow: 'auto' }}
                    renderItem={(log: PipelineLog) => (
                      <List.Item style={{ padding: '4px 0' }}>
                        <Typography.Text code style={{ fontSize: 11, minWidth: 150 }}>
                          {log.timestamp.replace('T', ' ').substring(0, 19)}
                        </Typography.Text>
                        <Tag color={log.level === 'error' ? 'red' : log.level === 'warning' ? 'orange' : 'blue'}
                          style={{ marginLeft: 8 }}>{log.stage}</Tag>
                        <Typography.Text style={{ fontSize: 12, marginLeft: 8 }}>{log.message}</Typography.Text>
                      </List.Item>
                    )}
                    locale={{ emptyText: 'No logs yet.' }}
                  />
                ),
              },
            ]} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
