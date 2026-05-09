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
  Drawer,
  Card,
  Statistic,
} from 'antd'
import { AlertCircle } from 'lucide-react'
import { StatCard } from '../components/Monitoring/StatCard'
import { TokenTrendChart } from '../components/Monitoring/TokenTrendChart'
import { ModelPieChart } from '../components/Monitoring/ModelPieChart'
import { LatencyBarChart } from '../components/Monitoring/LatencyBarChart'
import { ConversationDetailDrawer } from '../components/Chat/ConversationDetailDrawer'
import { monitoringApi } from '../services/monitoring'
import { chatApi } from '../services/chat'
import { DashboardStats, ModelUsage, LLMTrace, SkillUsageStat, SkillUsageRecord } from '../types/monitoring'
import { Conversation } from '../types/chat'

const PAGE_SIZE = 20

const MonitoringPage: React.FC = () => {
  const [hours, setHours] = useState(168)
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

  const [dailyTokens, setDailyTokens] = useState<{ date: string; tokens: number }[]>([])
  const [latencyData, setLatencyData] = useState<{ range: string; count: number }[]>([])

  // 对话列表 Drawer 状态
  const [conversationsDrawerOpen, setConversationsDrawerOpen] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationsLoading, setConversationsLoading] = useState(false)
  const [conversationsPage, setConversationsPage] = useState(1)
  const [conversationsTotal, setConversationsTotal] = useState(0)
  const CONV_PAGE_SIZE = 20

  // 单个对话详情 Drawer 状态
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [conversationDetailOpen, setConversationDetailOpen] = useState(false)

  // Skill 使用监控状态
  const [skillStats, setSkillStats] = useState<SkillUsageStat[]>([])
  const [recentSkillUsage, setRecentSkillUsage] = useState<SkillUsageRecord[]>([])
  const [skillLoading, setSkillLoading] = useState(false)

  const loadStats = async () => {
    try {
      const res = await monitoringApi.getDashboard(720)
      setStats(res.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const loadCharts = async () => {
    setLoading(true)
    try {
      const [usageRes, dailyRes] = await Promise.all([
        monitoringApi.getModelUsage(hours),
        monitoringApi.getDailyStats(hours),
      ])
      setModelUsage(usageRes.data)
      setDailyTokens(dailyRes.data.daily_tokens)
      setLatencyData(dailyRes.data.latency_distribution)
    } catch (error) {
      console.error('Failed to load chart data:', error)
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
    loadCharts()
  }, [hours])

  useEffect(() => {
    loadTraces(tracePage)
  }, [tracePage])

  const loadConversations = async (page: number) => {
    setConversationsLoading(true)
    try {
      const skip = (page - 1) * CONV_PAGE_SIZE
      const res = await chatApi.getConversations({ skip, limit: CONV_PAGE_SIZE })
      setConversations(res.data)
      // 后端返回的是数组，没有总数，这里做个简单估算
      if (res.data.length < CONV_PAGE_SIZE) {
        setConversationsTotal(skip + res.data.length)
      } else {
        setConversationsTotal(skip + CONV_PAGE_SIZE + 1)
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
    } finally {
      setConversationsLoading(false)
    }
  }

  const handleOpenConversationsDrawer = () => {
    setConversationsDrawerOpen(true)
    loadConversations(1)
  }

  const handleConversationClick = (conv: Conversation) => {
    setSelectedConversation(conv)
    setConversationDetailOpen(true)
  }

  // 加载技能使用数据
  const loadSkillUsage = async () => {
    setSkillLoading(true)
    try {
      const [statsRes, recentRes] = await Promise.all([
        monitoringApi.getSkillUsageStats(720),
        monitoringApi.getRecentSkillUsage(10),
      ])
      setSkillStats(statsRes.data.stats)
      setRecentSkillUsage(recentRes.data)
    } catch (error) {
      console.error('Failed to load skill usage:', error)
    } finally {
      setSkillLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
    loadSkillUsage()
  }, [])

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
    { title: '首 Token 延迟(ms)', dataIndex: 'avg_first_token_ms', key: 'avg_first_token_ms' },
    { title: 'Tokens/s', dataIndex: 'avg_tokens_per_second', key: 'avg_tokens_per_second' },
  ]

  const traceColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (v: string) => {
        const date = new Date(v)
        // 转换为北京时间 (UTC+8)
        const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
        return beijingTime.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }).replace(/\//g, '-')
      },
    },
    { title: 'Provider', dataIndex: 'provider', key: 'provider' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    { title: 'Input Tokens', dataIndex: 'input_tokens', key: 'input_tokens' },
    { title: 'Output Tokens', dataIndex: 'output_tokens', key: 'output_tokens' },
    {
      title: '首 Token',
      dataIndex: 'first_token_ms',
      key: 'first_token_ms',
      render: (v: number | undefined) => v ? `${v}ms` : '-',
    },
    {
      title: 'Tokens/s',
      dataIndex: 'tokens_per_second',
      key: 'tokens_per_second',
      render: (v: number | undefined) => v ? v.toFixed(1) : '-',
    },
    {
      title: '错误',
      dataIndex: 'error_type',
      key: 'error_type',
      render: (v: string | undefined) =>
        v ? (
          <Tag color="red" icon={<AlertCircle size={14} />}>
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
      <Spin spinning={loading}>
        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard label="消息数" value={stats?.total_messages || 0} />
          <StatCard
            label="对话数"
            value={stats?.total_conversations || 0}
            onClick={handleOpenConversationsDrawer}
          />
          <StatCard label="Token 用量" value={stats?.total_tokens || 0} suffix="" highlight />
          <StatCard label="平均延迟" value={stats?.avg_latency_ms || 0} suffix="ms" />
        </div>

        {/* Charts section with time filter */}
        <div className="bg-gray-50 rounded-2xl p-5 mb-6">
          <div className="flex justify-end mb-4">
            <Select
              value={hours}
              onChange={setHours}
              style={{ width: 130 }}
              options={[
                { value: 168, label: '最近7天' },
                { value: 336, label: '最近14天' },
                { value: 720, label: '最近30天' },
              ]}
            />
          </div>

          <div className="mb-4">
            <TokenTrendChart data={dailyTokens} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <LatencyBarChart data={latencyData} />
            <ModelPieChart
              data={modelUsage.map((m) => ({
                name: `${m.provider} ${m.model}`,
                value: m.input_tokens + m.output_tokens,
              }))}
            />
          </div>
        </div>

        {/* Model usage table */}
        <div className="bg-surface-card rounded-2xl shadow-elevated p-5 mb-6">
          <div className="text-heading font-semibold text-content-primary mb-4">模型使用量</div>
          <Table
            dataSource={modelUsage}
            columns={modelColumns}
            rowKey={(record) => `${record.provider}-${record.model}`}
            pagination={false}
          />
        </div>

        {/* Skill usage stats */}
        <div className="bg-surface-card rounded-2xl shadow-elevated p-5 mb-6">
          <div className="text-heading font-semibold text-content-primary mb-4">技能使用统计</div>
          <Spin spinning={skillLoading}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {skillStats.slice(0, 4).map((stat) => (
                <Card key={stat.skill_name} size="small" className="bg-surface-page">
                  <Statistic
                    title={stat.skill_name}
                    value={stat.call_count}
                    suffix="次"
                  />
                </Card>
              ))}
            </div>
            <Table
              dataSource={skillStats}
              columns={[
                { title: '技能名称', dataIndex: 'skill_name', key: 'skill_name' },
                { title: '调用次数', dataIndex: 'call_count', key: 'call_count', width: 200 },
              ]}
              rowKey="skill_name"
              pagination={false}
              size="small"
            />
          </Spin>
        </div>

        {/* Recent skill usage */}
        <div className="bg-surface-card rounded-2xl shadow-elevated p-5 mb-6">
          <div className="text-heading font-semibold text-content-primary mb-4">最近技能调用</div>
          <Spin spinning={skillLoading}>
            <Table
              dataSource={recentSkillUsage}
              columns={[
                { title: '技能名称', dataIndex: 'skill_name', key: 'skill_name' },
                {
                  title: '时间',
                  dataIndex: 'timestamp',
                  key: 'timestamp',
                  width: 200,
                  render: (v: string) => {
                    const date = new Date(v)
                    const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
                    return beijingTime.toLocaleString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    }).replace(/\//g, '-')
                  },
                },
              ]}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Spin>
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
                  {(() => {
                    const date = new Date(selectedTrace.timestamp)
                    const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
                    return beijingTime.toLocaleString('zh-CN', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    }).replace(/\//g, '-')
                  })()}
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
                  <Tag color="red" icon={<AlertCircle size={14} />}>
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

      {/* 对话列表 Drawer */}
      <Drawer
        title="对话列表"
        placement="right"
        width={600}
        onClose={() => setConversationsDrawerOpen(false)}
        open={conversationsDrawerOpen}
      >
        <Spin spinning={conversationsLoading}>
          <Table
            dataSource={conversations}
            rowKey="id"
            size="small"
            pagination={false}
            onRow={(record) => ({
              onClick: () => handleConversationClick(record),
              style: { cursor: 'pointer' },
            })}
            columns={[
              {
                title: 'ID',
                dataIndex: 'id',
                key: 'id',
                width: 60,
              },
              {
                title: '标题',
                dataIndex: 'title',
                key: 'title',
                render: (title: string | null) => title || '新对话',
              },
              {
                title: '状态',
                dataIndex: 'status',
                key: 'status',
                width: 80,
                render: (status: string) => (
                  <Tag color={status === 'active' ? 'green' : 'default'}>
                    {status}
                  </Tag>
                ),
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                key: 'created_at',
                width: 160,
                render: (v: string) => {
                  const date = new Date(v)
                  const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
                  return beijingTime.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  }).replace(/\//g, '-')
                },
              },
              {
                title: '更新时间',
                dataIndex: 'updated_at',
                key: 'updated_at',
                width: 160,
                render: (v: string | null) => {
                  if (!v) return '-'
                  const date = new Date(v)
                  const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
                  return beijingTime.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  }).replace(/\//g, '-')
                },
              },
            ]}
          />
          <div className="flex justify-end mt-4">
            <Pagination
              current={conversationsPage}
              pageSize={CONV_PAGE_SIZE}
              total={conversationsTotal}
              onChange={(page) => {
                setConversationsPage(page)
                loadConversations(page)
              }}
              showSizeChanger={false}
            />
          </div>
        </Spin>
      </Drawer>

      {/* 单个对话详情 Drawer */}
      <ConversationDetailDrawer
        conversation={selectedConversation}
        open={conversationDetailOpen}
        onClose={() => setConversationDetailOpen(false)}
      />
    </div>
  )
}

export default MonitoringPage
