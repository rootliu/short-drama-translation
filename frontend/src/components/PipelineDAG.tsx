import { Tag, Space } from 'antd'

const nodeStyle = (color: string): React.CSSProperties => ({
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  padding: '8px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13,
  background: color, color: '#fff', minWidth: 120, textAlign: 'center',
})

const arrowStyle: React.CSSProperties = {
  fontSize: 18, color: '#999', margin: '0 4px',
}

const parallelBox: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 8,
  border: '1px dashed #d9d9d9', borderRadius: 8, padding: '8px 12px',
}

export default function PipelineDAG() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflowX: 'auto', padding: '8px 0' }}>
      {/* S1 */}
      <div style={nodeStyle('#1677ff')}>
        S1<br/>Subtitle + Speaker
      </div>

      <span style={arrowStyle}>{'\u2192'}</span>

      {/* S2 & S3 parallel */}
      <div style={parallelBox}>
        <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>parallel</Tag>
        <div style={nodeStyle('#13c2c2')}>S2 Character ID</div>
        <div style={nodeStyle('#722ed1')}>S3 Emotion</div>
      </div>

      <span style={arrowStyle}>{'\u2192'}</span>

      {/* S5 */}
      <div style={nodeStyle('#fa8c16')}>
        S5<br/>Script Generation
      </div>

      <span style={arrowStyle}>{'\u2192'}</span>

      {/* S6 & S7 parallel */}
      <div style={parallelBox}>
        <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>parallel</Tag>
        <div style={nodeStyle('#eb2f96')}>S6 Emotion Mgmt</div>
        <div style={nodeStyle('#f5222d')}>S7 Hook Analysis</div>
      </div>

      <span style={arrowStyle}>{'\u2192'}</span>

      {/* QA */}
      <div style={nodeStyle('#52c41a')}>
        QA<br/>Quality Review
      </div>
    </div>
  )
}
