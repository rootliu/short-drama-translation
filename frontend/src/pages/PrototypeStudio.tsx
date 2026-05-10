import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  List,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Steps,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from 'antd'
import ReactEChartsCore from 'echarts-for-react'

type PatternId = 'revenge' | 'identity' | 'romance' | 'upgrade' | 'mystery'

type PatternProfile = {
  id: PatternId
  name: string
  rhythm: string
  paywall: string
  shuangType: string
  shuangCurve: number[]
  hookCurve: number[]
}

const PATTERNS: PatternProfile[] = [
  {
    id: 'revenge',
    name: '复仇阶梯',
    rhythm: '每3-5集形成一次压抑到释放循环，强度递增',
    paywall: 'EP8-10',
    shuangType: '均匀高频',
    shuangCurve: [2.2, 3.5, 4.8, 7.4, 8.0, 7.6, 8.2, 8.5, 8.4, 8.8, 9.1],
    hookCurve: [3.1, 4.0, 4.6, 6.9, 7.2, 7.4, 7.7, 8.1, 8.0, 8.3, 8.6],
  },
  {
    id: 'identity',
    name: '身份剥洋葱',
    rhythm: '每次身份揭露带来更高一级冲突',
    paywall: 'EP10-12',
    shuangType: '递增式',
    shuangCurve: [1.8, 2.6, 3.5, 5.0, 6.4, 7.0, 7.6, 8.2, 8.8, 9.1, 9.4],
    hookCurve: [2.8, 3.4, 4.0, 5.8, 6.7, 7.1, 7.8, 8.3, 8.7, 8.9, 9.2],
  },
  {
    id: 'romance',
    name: '虐恋过山车',
    rhythm: '甜虐交替，后段波动幅度放大',
    paywall: 'EP9-11',
    shuangType: '高幅振荡',
    shuangCurve: [3.2, 5.2, 3.8, 6.6, 4.1, 7.3, 5.4, 8.0, 6.1, 8.5, 7.2],
    hookCurve: [4.0, 5.1, 4.3, 6.2, 5.0, 7.0, 6.2, 7.8, 7.0, 8.2, 7.8],
  },
  {
    id: 'upgrade',
    name: '升级打怪',
    rhythm: '修炼-挑战-突破固定循环',
    paywall: 'EP8-10',
    shuangType: '脉冲式',
    shuangCurve: [2.0, 2.8, 6.4, 3.4, 7.0, 4.0, 7.8, 4.5, 8.2, 5.0, 8.8],
    hookCurve: [2.9, 3.6, 5.8, 4.2, 6.5, 4.8, 7.1, 5.2, 7.6, 5.9, 8.0],
  },
  {
    id: 'mystery',
    name: '悬疑递进',
    rhythm: '每次信息释放都打开新谜题',
    paywall: 'EP10-12',
    shuangType: '阶梯式',
    shuangCurve: [1.6, 2.4, 2.8, 4.1, 4.4, 5.8, 6.0, 7.2, 7.5, 8.6, 9.0],
    hookCurve: [3.8, 4.4, 4.9, 5.7, 6.2, 6.9, 7.5, 8.0, 8.3, 8.8, 9.1],
  },
]

const STAGES = [
  'B1 情感标注',
  'B2 弧线拟合',
  'B3 爽度计算',
  'B4 Hook评分',
  'M1 骨架提取',
  'M2 模式映射',
  'M3 空白识别',
  'A1 SkeletonAgent',
  'A2 AugmentorAgent',
  'A3 HookEngineer',
  'A4 EvaluatorAgent',
]

const curveXAxis = ['EP1', 'EP3', 'EP5', 'EP8', 'EP10', 'EP14', 'EP18', 'EP24', 'EP32', 'EP40', 'EP50']

function riskColor(level: string): 'green' | 'orange' | 'red' {
  if (level === 'HIGH') return 'red'
  if (level === 'MEDIUM') return 'orange'
  return 'green'
}

export default function PrototypeStudio() {
  const [form] = Form.useForm()
  const [running, setRunning] = useState(false)
  const [stageIndex, setStageIndex] = useState(-1)
  const [logs, setLogs] = useState<string[]>([
    'v0 创建项目：千金归来（复仇阶梯）',
    '等待执行 Benchmark 与 Mapping ...',
  ])
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current)
      }
    }
  }, [])

  const projectConfig = Form.useWatch([], form) as {
    projectName?: string
    pattern?: PatternId
    audience?: string
    episodes?: number
    paywallStart?: number
    paywallEnd?: number
  }

  const selectedPattern = useMemo(() => {
    const id = projectConfig?.pattern || 'revenge'
    return PATTERNS.find((item) => item.id === id) || PATTERNS[0]
  }, [projectConfig?.pattern])

  const completion = ((stageIndex + 1) / STAGES.length) * 100

  const metrics = useMemo(() => {
    const factor = Math.max(0, stageIndex + 1) / STAGES.length
    const patternBoost: Record<PatternId, number> = {
      revenge: 4,
      identity: 3,
      romance: 2,
      upgrade: 1,
      mystery: 3,
    }

    const boost = patternBoost[selectedPattern.id]

    return {
      shuang: Math.round(58 + factor * 18 + boost),
      hook: Math.round(55 + factor * 20 + (selectedPattern.id === 'mystery' ? 4 : 1)),
      fit: Math.round(62 + factor * 22 + (selectedPattern.id === 'identity' ? 3 : 0)),
      retention: Math.round(31 + factor * 12 + (selectedPattern.id === 'revenge' ? 2 : 0)),
      consistency: Math.round(68 + factor * 20),
    }
  }, [selectedPattern.id, stageIndex])

  const curveOption = useMemo(() => {
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 48, right: 24, bottom: 36, top: 40 },
      xAxis: {
        type: 'category',
        data: curveXAxis,
      },
      yAxis: { type: 'value', max: 10, name: 'Score' },
      series: [
        {
          name: 'Shuang',
          type: 'line',
          smooth: true,
          data: selectedPattern.shuangCurve,
          areaStyle: { opacity: 0.18 },
          lineStyle: { width: 3 },
          itemStyle: { color: '#cf1322' },
        },
        {
          name: 'Hook Health',
          type: 'line',
          smooth: true,
          data: selectedPattern.hookCurve,
          lineStyle: { width: 2, type: 'dashed' },
          itemStyle: { color: '#1677ff' },
        },
      ],
    }
  }, [selectedPattern])

  const mappingRows = useMemo(() => {
    return [
      { key: 'm1', source: '原著第1章：家族压制', target: 'EP1-EP2', type: 'Direct', note: '用于建立压抑场' },
      { key: 'm2', source: '原著第3章：股权线索', target: 'EP8', type: 'Compress', note: '提前触发付费卡点' },
      { key: 'm3', source: '原著第7章：反派内斗', target: 'EP14', type: 'Gap', note: '需增补触发事件' },
      { key: 'm4', source: '原著第12章：身份揭露', target: 'EP20', type: 'Direct', note: '保留为中段大反转' },
      { key: 'm5', source: '原著第15章：旧案重开', target: 'EP28', type: 'Gap', note: '补前置伏笔' },
    ]
  }, [])

  const episodeRows = useMemo(() => {
    const rows = [
      {
        key: 'ep08',
        episode: 'EP08',
        goal: '压抑高位 + 首次释放',
        trigger: '遗嘱真实性公开',
        hook: 'reveal',
        source: '原著60% / 增补40%',
        risk: 'MEDIUM',
      },
      {
        key: 'ep09',
        episode: 'EP09',
        goal: '短回落后再蓄压',
        trigger: '反派反制升级',
        hook: 'threat',
        source: '原著75% / 增补25%',
        risk: 'LOW',
      },
      {
        key: 'ep10',
        episode: 'EP10',
        goal: '付费卡点峰值',
        trigger: '隐藏身份二次揭露',
        hook: 'suspense',
        source: '原著55% / 增补45%',
        risk: 'LOW',
      },
      {
        key: 'ep11',
        episode: 'EP11',
        goal: '高位维持',
        trigger: '旧敌出现',
        hook: 'choice',
        source: '原著70% / 增补30%',
        risk: 'MEDIUM',
      },
      {
        key: 'ep12',
        episode: 'EP12',
        goal: '第二波释放预热',
        trigger: '关键证据缺失',
        hook: 'suspense',
        source: '原著68% / 增补32%',
        risk: 'HIGH',
      },
    ]

    if (selectedPattern.id === 'mystery') {
      rows[0].hook = 'suspense'
      rows[2].trigger = '谜底1揭晓但引出新谜底'
      rows[4].risk = 'MEDIUM'
    }

    if (selectedPattern.id === 'romance') {
      rows[1].goal = '甜后回虐'
      rows[3].hook = 'emotional'
    }

    return rows
  }, [selectedPattern.id])

  const runMockPipeline = () => {
    if (running) return

    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }

    setRunning(true)
    setStageIndex(-1)
    setLogs([
      `v1 运行开始：模式=${selectedPattern.name}，目标受众=${projectConfig?.audience || '女性18-34'}`,
      '初始化 Benchmark 规则与模板参数 ...',
    ])

    let idx = -1
    timerRef.current = window.setInterval(() => {
      idx += 1
      if (idx < STAGES.length) {
        setStageIndex(idx)
        setLogs((prev) => [`完成 ${STAGES[idx]}`, ...prev].slice(0, 8))
      } else {
        if (timerRef.current) {
          window.clearInterval(timerRef.current)
          timerRef.current = null
        }
        setRunning(false)
        setLogs((prev) => [
          `v2 通过质量门槛：Shuang=${metrics.shuang} Hook=${metrics.hook} Fit=${metrics.fit}%`,
          ...prev,
        ].slice(0, 8))
      }
    }, 650)
  }

  const resetPipeline = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    setRunning(false)
    setStageIndex(-1)
    setLogs([
      'v0 创建项目：千金归来（复仇阶梯）',
      '等待执行 Benchmark 与 Mapping ...',
    ])
  }

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card>
          <Row justify="space-between" align="middle">
            <Col>
              <Typography.Title level={4} style={{ margin: 0 }}>
                AI评书艺人 Mock Prototype
              </Typography.Title>
              <Typography.Text type="secondary">
                可交互原型：项目配置、模式映射、Agent闭环、Benchmark评分
              </Typography.Text>
            </Col>
            <Col>
              <Space>
                <Tag color="processing">Phase 1 Benchmark</Tag>
                <Tag color="purple">Phase 2 Mapping</Tag>
                <Tag color="volcano">Phase 3 Agent Loop</Tag>
              </Space>
            </Col>
          </Row>
        </Card>
      </Col>

      <Col span={5}>
        <Card><Statistic title="Shuang Score" value={metrics.shuang} suffix="/100" valueStyle={{ color: '#cf1322' }} /></Card>
      </Col>
      <Col span={5}>
        <Card><Statistic title="Hook Health" value={metrics.hook} suffix="/100" valueStyle={{ color: '#1677ff' }} /></Card>
      </Col>
      <Col span={5}>
        <Card><Statistic title="模式匹配" value={metrics.fit} suffix="%" valueStyle={{ color: '#389e0d' }} /></Card>
      </Col>
      <Col span={5}>
        <Card><Statistic title="角色一致性" value={metrics.consistency} suffix="%" valueStyle={{ color: '#722ed1' }} /></Card>
      </Col>
      <Col span={4}>
        <Card><Statistic title="预测留存" value={metrics.retention} suffix="%" /></Card>
      </Col>

      <Col span={10}>
        <Card title="项目配置" size="small">
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              projectName: '千金归来',
              pattern: 'revenge',
              audience: '女性18-34',
              episodes: 60,
              paywallStart: 8,
              paywallEnd: 10,
            }}
          >
            <Form.Item name="projectName" label="项目名称">
              <Input placeholder="输入网文改编项目名" />
            </Form.Item>
            <Form.Item name="pattern" label="改编模式">
              <Select
                options={PATTERNS.map((item) => ({ value: item.id, label: item.name }))}
              />
            </Form.Item>
            <Form.Item name="audience" label="目标受众">
              <Select
                options={[
                  { value: '女性18-34', label: '女性 18-34' },
                  { value: '男性18-30', label: '男性 18-30' },
                  { value: '泛都市用户', label: '泛都市用户' },
                  { value: '海外华语用户', label: '海外华语用户' },
                ]}
              />
            </Form.Item>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item name="episodes" label="总集数">
                  <InputNumber min={30} max={120} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="paywallStart" label="卡点起始">
                  <InputNumber min={5} max={30} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="paywallEnd" label="卡点结束">
                  <InputNumber min={6} max={35} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Space>
              <Button type="primary" onClick={runMockPipeline} loading={running}>
                运行 Mock Pipeline
              </Button>
              <Button onClick={resetPipeline}>重置</Button>
            </Space>
          </Form>
        </Card>
      </Col>

      <Col span={14}>
        <Card
          title="Pipeline 执行状态"
          size="small"
          extra={<Badge status={running ? 'processing' : 'default'} text={running ? 'Running' : 'Idle'} />}
        >
          <Alert
            type="info"
            showIcon
            message={`当前模式：${selectedPattern.name}`}
            description={`${selectedPattern.rhythm}；付费卡点建议：${selectedPattern.paywall}；爽度分布：${selectedPattern.shuangType}`}
            style={{ marginBottom: 12 }}
          />

          <Progress percent={Math.round(completion)} status={running ? 'active' : 'normal'} />

          <div style={{ marginTop: 12 }}>
            <Steps
              size="small"
              current={stageIndex}
              items={STAGES.map((stage, idx) => ({
                title: stage,
                status: idx < stageIndex ? 'finish' : idx === stageIndex ? 'process' : 'wait',
              }))}
            />
          </div>
        </Card>
      </Col>

      <Col span={24}>
        <Card>
          <Tabs
            items={[
              {
                key: 'planner',
                label: 'Episode Planner',
                children: (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={episodeRows}
                    columns={[
                      { title: '集数', dataIndex: 'episode', width: 80 },
                      { title: '情感目标', dataIndex: 'goal' },
                      { title: 'Trigger', dataIndex: 'trigger' },
                      {
                        title: 'Hook',
                        dataIndex: 'hook',
                        width: 110,
                        render: (value: string) => <Tag color="geekblue">{value}</Tag>,
                      },
                      { title: '内容来源', dataIndex: 'source', width: 180 },
                      {
                        title: '风险',
                        dataIndex: 'risk',
                        width: 90,
                        render: (value: string) => <Tag color={riskColor(value)}>{value}</Tag>,
                      },
                    ]}
                  />
                ),
              },
              {
                key: 'benchmark',
                label: 'Benchmark',
                children: (
                  <Row gutter={[16, 16]}>
                    <Col span={16}>
                      <Card title="爽度与Hook曲线" size="small">
                        <ReactEChartsCore option={curveOption} style={{ height: 310 }} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card title="指标解释" size="small">
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="Volume">情感振幅，越大越容易拉高留存</Descriptions.Item>
                          <Descriptions.Item label="Pivot">反转瞬时强度，对应单次爽感</Descriptions.Item>
                          <Descriptions.Item label="Suspense">集尾不确定性，决定追更驱动力</Descriptions.Item>
                          <Descriptions.Item label="PlotTwist">观众预期偏离，衡量trigger质量</Descriptions.Item>
                        </Descriptions>
                        <Alert
                          type="warning"
                          showIcon
                          style={{ marginTop: 8 }}
                          message="Mock建议"
                          description="EP11-EP14出现释放衰减，建议补一次身份揭露或权力反转。"
                        />
                      </Card>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'mapping',
                label: 'Story Mapping',
                children: (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={mappingRows}
                    columns={[
                      { title: '原著情节点', dataIndex: 'source' },
                      { title: '目标槽位', dataIndex: 'target', width: 120 },
                      {
                        title: '映射类型',
                        dataIndex: 'type',
                        width: 100,
                        render: (value: string) => (
                          <Tag color={value === 'Direct' ? 'green' : value === 'Compress' ? 'gold' : 'volcano'}>{value}</Tag>
                        ),
                      },
                      { title: '说明', dataIndex: 'note' },
                    ]}
                  />
                ),
              },
              {
                key: 'loop',
                label: 'Iteration Log',
                children: (
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Card title="版本日志" size="small">
                        <List
                          size="small"
                          dataSource={logs}
                          renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="反馈闭环" size="small">
                        <Timeline
                          items={[
                            { color: 'blue', children: 'SkeletonAgent 输出 mapping + gaps' },
                            { color: 'purple', children: 'AugmentorAgent 填充 Gap 并标注来源' },
                            { color: 'orange', children: 'HookEngineer 生成集尾钩子与承接点' },
                            { color: 'red', children: 'Evaluator 评分，不达标回灌 A2/A3' },
                            { color: 'green', children: '达标后输出剧本包 + benchmark_report' },
                          ]}
                        />
                      </Card>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  )
}
