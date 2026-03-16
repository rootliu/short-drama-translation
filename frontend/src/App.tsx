import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Typography } from 'antd'
import {
  DashboardOutlined, ProjectOutlined, PlayCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import Dashboard from './pages/Dashboard'
import ProjectDetail from './pages/ProjectDetail'
import EpisodeDetailPage from './pages/EpisodeDetail'

const { Header, Sider, Content } = Layout

function App() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex', alignItems: 'center', padding: '0 24px',
        background: '#001529',
      }}>
        <Typography.Title level={4} style={{
          color: '#fff', margin: 0, cursor: 'pointer', whiteSpace: 'nowrap',
        }} onClick={() => navigate('/')}>
          Short Drama Pipeline
        </Typography.Title>
        <Menu
          theme="dark" mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ marginLeft: 40, flex: 1 }}
        />
      </Header>
      <Content style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/project/:id" element={<ProjectDetail />} />
          <Route path="/episode/:id" element={<EpisodeDetailPage />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
