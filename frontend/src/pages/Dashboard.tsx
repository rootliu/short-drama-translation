import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card, Button, Table, Tag, Modal, Form, Input, InputNumber, Select,
  Row, Col, Statistic, Space, Typography, Empty,
} from 'antd'
import { PlusOutlined, PlayCircleOutlined, EyeOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { Project } from '../types'

const statusColors: Record<string, string> = {
  created: 'default', processing: 'processing', paused: 'warning', completed: 'success',
}

export default function Dashboard() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.listProjects()
      setProjects(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (values: any) => {
    await api.createProject(values)
    setModalOpen(false)
    form.resetFields()
    load()
  }

  const columns = [
    {
      title: 'Project', dataIndex: 'name', key: 'name',
      render: (name: string, record: any) => (
        <a onClick={() => navigate(`/project/${record.id}`)}>{name}</a>
      ),
    },
    { title: 'Episodes', dataIndex: 'total_episodes', key: 'total_episodes', width: 100 },
    { title: 'Batch Size', dataIndex: 'batch_size', key: 'batch_size', width: 100 },
    {
      title: 'Progress', key: 'progress', width: 160,
      render: (_: any, r: any) => {
        const pct = r.total_eps > 0 ? Math.round(r.completed_eps / r.total_eps * 100) : 0
        return <span>{r.completed_eps}/{r.total_eps} ({pct}%)</span>
      },
    },
    {
      title: 'Status', dataIndex: 'status', key: 'status', width: 120,
      render: (s: string) => <Tag color={statusColors[s]}>{s.toUpperCase()}</Tag>,
    },
    {
      title: 'Target', dataIndex: 'target_language', key: 'target_language', width: 80,
      render: (l: string) => l === 'en' ? 'EN' : 'JA',
    },
    {
      title: 'Actions', key: 'actions', width: 100,
      render: (_: any, r: any) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/project/${r.id}`)}>
          Detail
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Row justify="space-between" align="middle">
              <Col>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  Pipeline Dashboard
                </Typography.Title>
                <Typography.Text type="secondary">
                  Short Drama Translation Pipeline - Planning & Monitoring
                </Typography.Text>
              </Col>
              <Col>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                  New Project
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>

        {projects.length > 0 && (
          <>
            <Col span={6}>
              <Card><Statistic title="Total Projects" value={projects.length} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="Processing" value={projects.filter(p => p.status === 'processing').length} valueStyle={{ color: '#1677ff' }} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="Completed" value={projects.filter(p => p.status === 'completed').length} valueStyle={{ color: '#52c41a' }} /></Card>
            </Col>
            <Col span={6}>
              <Card><Statistic title="Total Episodes" value={projects.reduce((s, p) => s + p.total_episodes, 0)} /></Card>
            </Col>
          </>
        )}

        <Col span={24}>
          <Card title="Projects">
            <Table
              dataSource={projects} columns={columns}
              rowKey="id" loading={loading}
              pagination={false}
              locale={{ emptyText: <Empty description="No projects yet. Create one to get started." /> }}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title="Create New Project" open={modalOpen}
        onCancel={() => setModalOpen(false)} footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={{ total_episodes: 20, batch_size: 10, target_language: 'en' }}>
          <Form.Item name="name" label="Drama Name" rules={[{ required: true }]}>
            <Input placeholder="e.g. Flash Marriage CEO" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Brief description of the drama" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="total_episodes" label="Total Episodes" rules={[{ required: true }]}>
                <InputNumber min={1} max={500} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="batch_size" label="Batch Size" rules={[{ required: true }]}>
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="target_language" label="Target Language">
                <Select options={[
                  { value: 'en', label: 'English' },
                  { value: 'ja', label: 'Japanese (later)' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>Create Project</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
