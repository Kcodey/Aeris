import React, { useState, useEffect } from 'react'
import {
  Table,
  Select,
  Spin,
  Modal,
  Pagination,
  Tag,
  Descriptions,
  Collapse,
} from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { StatCard } from '../components/Monitoring/StatCard'
import { TokenTrendChart } from '../components/Monitoring/TokenTrendChart'
import { ModelPieChart } from '../components/Monitoring/ModelPieChart'
import { LatencyBarChart } from '../components/Monitoring/LatencyBarChart'
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

  // Demo data for charts - replace with real API data
  const [tokenTrendData] = useState([
    { date: '4/28', tokens: 45000 },
    { date: '4/29', tokens: 62000 },
    { date: '4/30', tokens: 58000 },
    { date: '5/1', tokens: 81000 },
    { date: '5/2', tokens: 75000 },
    { date: '5/3', tokens: 92000 },
    { date: '5/4', tokens: 88000 },
    { date: '5/5', tokens: 105000 },
    { date: '5/6', tokens: 98000 },
  ])

  const [modelPieData] = useState([
    { name: 'Qwen2.5-72B', value: 60 },
    { name: 'GPT-4o', value: 20 },
    { name: 'Claude-3', value: 12 },
    { name: '其他', value: 8 },
  ])

  const [latencyData] = useState([
    { range: '0-200ms', count: 45 },
    { range: '200-500ms', count: 32 },
    { range: '500-1s', count: 18 },
    { range: '1-2s', count: 8 },
    { range: '>2s', count: 3 },
  ])

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
      console.error('Failed to load monitoring data:', error)
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
      console.error('Failed to load traces:', error)
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
      console.error('Failed to load trace detail:', error)
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
    <div className="h-full overflow-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-title text-content-primary">监控仪表板</h1>
        <Select
          value={days}
          onChange={setDays}
          style={{ width: 120 }}
          options={[
            { value: 7, label: '最近7天' },
            { value: 14, label: '最近14天' },
            { value: 30, label: '最近30天' },
          ]}
        />
      </div>

      <Spin spinning={loading}>
        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard
            label="消息数"
            value={stats?.total_messages || 0}
            trend={{ value: 12.5, isPositive: true, label: '较上周' }}
          />
          <StatCard
            label="对话数"
            value={stats?.total_conversations || 0}
            trend={{ value: 8.3, isPositive: true, label: '较上周' }}
          />
          <StatCard
            label="Token 用量"
            value={stats?.total_tokens || 0}
            suffix=""
            highlight
            trend={{ value: 23.1, isPositive: false, label: '较上周' }}
          />
          <StatCard
            label="平均延迟"
            value={stats?.avg_latency_ms || 0}
            suffix="ms"
            trend={{ value: 5.2, isPositive: true, label: '较上周' }}
          />
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="col-span-2">
            <TokenTrendChart data={tokenTrendData} />
          </div>
          <div>
            <ModelPieChart data={modelPieData} />
          </div>
        </div>

        {/* Charts row 2 */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <LatencyBarChart data={latencyData} />
        </div>

        {/* Model usage table */}
        <div className="bg-surface-card rounded-2xl border border-[#f0f0f0] shadow-subtle p-5 mb-6">
          <div className="text-heading font-semibold text-content-primary mb-4">模型使用量</div>
          <Table
            dataSource={modelUsage}
            columns={modelColumns}
            rowKey={(record) => `${record.provider}-${record.model}`}
            pagination={false}
          />
        </div>

        {/* Trace table */}
        <div className="bg-surface-card rounded-2xl border border-[#f0f0f0] shadow-subtle p-5">
          <div className="text-heading font-semibold text-content-primary mb-4">LLM Traces</div>
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
            <div className="flex justify-end mt-4">
              <Pagination
                current={tracePage}
                pageSize={PAGE_SIZE}
                total={traceTotal}
                onChange={setTracePage}
                showSizeChanger={false}
              />
            </div>
          </Spin>
        </div>
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
