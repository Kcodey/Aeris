import React, { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Table, Select, Spin, message } from 'antd'
import {
  MessageOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { monitoringApi } from '../services/monitoring'
import { DashboardStats, ModelUsage } from '../types/monitoring'

const MonitoringPage: React.FC = () => {
  const [days, setDays] = useState(7)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsRes, usageRes] = await Promise.all([
        monitoringApi.getDashboard(days),
        monitoringApi.getModelUsage(days),
      ])
      setStats(statsRes.data)
      setModelUsage(usageRes.data)
    } catch (error) {
      message.error('加载监控数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [days])

  const columns = [
    { title: 'Provider', dataIndex: 'provider', key: 'provider' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    { title: '调用次数', dataIndex: 'count', key: 'count' },
    { title: 'Input Tokens', dataIndex: 'input_tokens', key: 'input_tokens' },
    { title: 'Output Tokens', dataIndex: 'output_tokens', key: 'output_tokens' },
    { title: '平均延迟(ms)', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms' },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <h2 style={{ margin: 0 }}>监控仪表板</h2>
        <Select value={days} onChange={setDays} style={{ width: 120 }}>
          <Select.Option value={7}>最近7天</Select.Option>
          <Select.Option value={14}>最近14天</Select.Option>
          <Select.Option value={30}>最近30天</Select.Option>
        </Select>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="消息数"
                value={stats?.total_messages || 0}
                prefix={<MessageOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="对话数"
                value={stats?.total_conversations || 0}
                prefix={<RobotOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Token 用量"
                value={stats?.total_tokens || 0}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="平均延迟"
                value={stats?.avg_latency_ms || 0}
                suffix="ms"
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Card title="模型使用量" style={{ marginTop: 24 }}>
          <Table
            dataSource={modelUsage}
            columns={columns}
            rowKey={(record) => `${record.provider}-${record.model}`}
            pagination={false}
          />
        </Card>
      </Spin>
    </div>
  )
}

export default MonitoringPage
