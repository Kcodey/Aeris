import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Select,
  Spin,
  message,
  Modal,
  Pagination,
  Tag,
  Descriptions,
  Collapse,
} from 'antd'
import {
  MessageOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { monitoringApi } from '../services/monitoring'
import { DashboardStats, ModelUsage, LLMTrace } from '../types/monitoring'

const PAGE_SIZE = 20

const MonitoringPage: React.FC = () => {
  const [days, setDays] = useState(7)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([])
  const [loading, setLoading] = useState(false)

  const [traces, setTraces] = useState<LLMTrace[]>([])
  const [traceLoading, setTraceLoading] = useState(false)
  const [tracePage, setTracePage] = useState(1)
  const [traceTotal, setTraceTotal] = useState(0)

  const [selectedTrace, setSelectedTrace] = useState<LLMTrace | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)

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

  const loadTraces = async (page: number) => {
    setTraceLoading(true)
    try {
      const skip = (page - 1) * PAGE_SIZE
      const res = await monitoringApi.getTraces({ skip, limit: PAGE_SIZE })
      setTraces(res.data)
      if (res.data.length < PAGE_SIZE) {
        setTraceTotal(skip + res.data.length)
      } else {
        setTraceTotal(skip + PAGE_SIZE + 1)
      }
    } catch (error) {
      message.error('加载 Trace 列表失败')
    } finally {
      setTraceLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [days])

  useEffect(() => {
    loadTraces(tracePage)
  }, [tracePage])

  const handleTraceClick = async (trace: LLMTrace) => {
    setModalVisible(true)
    setModalLoading(true)
    try {
      const res = await monitoringApi.getTraceDetail(trace.trace_id)
      setSelectedTrace(res.data)
    } catch (error) {
      message.error('加载 Trace 详情失败')
      setModalVisible(false)
    } finally {
      setModalLoading(false)
    }
  }

  const modelColumns = [
    { title: 'Provider', dataIndex: 'provider', key: 'provider' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    { title: '调用次数', dataIndex: 'count', key: 'count' },
    { title: 'Input Tokens', dataIndex: 'input_tokens', key: 'input_tokens' },
    { title: 'Output Tokens', dataIndex: 'output_tokens', key: 'output_tokens' },
    { title: '平均延迟(ms)', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms' },
  ]

  const traceColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    { title: 'Provider', dataIndex: 'provider', key: 'provider' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    { title: 'Input Tokens', dataIndex: 'input_tokens', key: 'input_tokens' },
    { title: 'Output Tokens', dataIndex: 'output_tokens', key: 'output_tokens' },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      render: (v: number) => `${v}ms`,
    },
    {
      title: '错误',
      dataIndex: 'error_type',
      key: 'error_type',
      render: (v: string | undefined) =>
        v ? (
          <Tag color="red" icon={<ExclamationCircleOutlined />}>
            {v}
          </Tag>
        ) : (
          '-'
        ),
    },
  ]

  const renderJson = (data: any) => (
    <pre
      style={{
        background: '#f6f8fa',
        padding: 12,
        borderRadius: 6,
        overflow: 'auto',
        maxHeight: 400,
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  )

  const collapseItems = [
    ...(selectedTrace?.request_payload
      ? [
          {
            key: 'request',
            label: '请求 Payload',
            children: renderJson(selectedTrace.request_payload),
          },
        ]
      : []),
    ...(selectedTrace?.response_payload
      ? [
          {
            key: 'response',
            label: '响应 Payload',
            children: renderJson(selectedTrace.response_payload),
          },
        ]
      : []),
    ...(selectedTrace?.tool_calls?.length
      ? [
          {
            key: 'tool_calls',
            label: `Tool Calls (${selectedTrace.tool_calls.length})`,
            children: renderJson(selectedTrace.tool_calls),
          },
        ]
      : []),
    ...(selectedTrace?.tool_results?.length
      ? [
          {
            key: 'tool_results',
            label: `Tool Results (${selectedTrace.tool_results.length})`,
            children: renderJson(selectedTrace.tool_results),
          },
        ]
      : []),
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
            columns={modelColumns}
            rowKey={(record) => `${record.provider}-${record.model}`}
            pagination={false}
          />
        </Card>

        <Card title="LLM Traces" style={{ marginTop: 24 }}>
          <Spin spinning={traceLoading}>
            <Table
              dataSource={traces}
              columns={traceColumns}
              rowKey="trace_id"
              pagination={false}
              onRow={(record) => ({
                onClick: () => handleTraceClick(record),
                style: { cursor: 'pointer' },
              })}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <Pagination
                current={tracePage}
                pageSize={PAGE_SIZE}
                total={traceTotal}
                onChange={setTracePage}
                showSizeChanger={false}
              />
            </div>
          </Spin>
        </Card>
      </Spin>

      <Modal
        title="Trace 详情"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
      >
        <Spin spinning={modalLoading}>
          {selectedTrace && (
            <>
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="Trace ID" span={2}>
                  {selectedTrace.trace_id}
                </Descriptions.Item>
                <Descriptions.Item label="时间">
                  {new Date(selectedTrace.timestamp).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Provider">
                  {selectedTrace.provider}
                </Descriptions.Item>
                <Descriptions.Item label="Model">
                  {selectedTrace.model}
                </Descriptions.Item>
                <Descriptions.Item label="延迟">
                  {selectedTrace.latency_ms}ms
                </Descriptions.Item>
                <Descriptions.Item label="首 Token 延迟">
                  {selectedTrace.first_token_ms != null
                    ? `${selectedTrace.first_token_ms}ms`
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Input Tokens">
                  {selectedTrace.input_tokens}
                </Descriptions.Item>
                <Descriptions.Item label="Output Tokens">
                  {selectedTrace.output_tokens}
                </Descriptions.Item>
                {selectedTrace.tokens_per_second != null && (
                  <Descriptions.Item label="Tokens/s">
                    {selectedTrace.tokens_per_second}
                  </Descriptions.Item>
                )}
                {selectedTrace.iteration_count != null && (
                  <Descriptions.Item label="迭代次数">
                    {selectedTrace.iteration_count}
                  </Descriptions.Item>
                )}
              </Descriptions>

              {selectedTrace.error_type && (
                <div style={{ marginTop: 16 }}>
                  <Tag color="red" icon={<ExclamationCircleOutlined />}>
                    {selectedTrace.error_type}
                  </Tag>
                  {selectedTrace.error_message && (
                    <pre
                      style={{
                        marginTop: 8,
                        background: '#fff1f0',
                        padding: 12,
                        borderRadius: 6,
                        color: '#cf1322',
                      }}
                    >
                      {selectedTrace.error_message}
                    </pre>
                  )}
                </div>
              )}

              {collapseItems.length > 0 && (
                <Collapse items={collapseItems} style={{ marginTop: 16 }} />
              )}
            </>
          )}
        </Spin>
      </Modal>
    </div>
  )
}

export default MonitoringPage
