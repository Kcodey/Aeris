import React, { useState, useEffect } from 'react'
import { Drawer, Descriptions, Spin, Table, Tag, Empty, Collapse } from 'antd'
import { AlertCircle, MessageSquare, Zap, Clock, BarChart3 } from 'lucide-react'
import { chatApi } from '../../services/chat'
import { monitoringApi } from '../../services/monitoring'
import { Conversation, Message } from '../../types/chat'
import { LLMTrace } from '../../types/monitoring'

interface ConversationDetailDrawerProps {
  conversation: Conversation | null
  open: boolean
  onClose: () => void
}

function formatBeijingTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  return beijingTime.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).replace(/\//g, '-')
}

const StatItem: React.FC<{
  icon: React.ReactNode
  label: string
  value: string | number
}> = ({ icon, label, value }) => (
  <div className="flex items-center gap-3 p-3 bg-surface-page rounded-xl">
    <div className="w-8 h-8 rounded-lg bg-brand-light flex items-center justify-center text-brand">
      {icon}
    </div>
    <div>
      <div className="text-lg font-semibold text-content-primary">{value}</div>
      <div className="text-[11px] text-content-tertiary">{label}</div>
    </div>
  </div>
)

export const ConversationDetailDrawer: React.FC<ConversationDetailDrawerProps> = ({
  conversation,
  open,
  onClose,
}) => {
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [traces, setTraces] = useState<LLMTrace[]>([])

  useEffect(() => {
    if (!open || !conversation) return

    const load = async () => {
      setLoading(true)
      try {
        const [convRes, tracesRes] = await Promise.all([
          chatApi.getConversation(conversation.id),
          monitoringApi.getTraces({ conversation_id: conversation.id, limit: 50 }),
        ])
        setMessages(convRes.data.messages || [])
        setTraces(tracesRes.data)
      } catch (error) {
        console.error('Failed to load conversation detail:', error)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [open, conversation])

  const totalInputTokens = traces.reduce((sum, t) => sum + (t.input_tokens || 0), 0)
  const totalOutputTokens = traces.reduce((sum, t) => sum + (t.output_tokens || 0), 0)
  const avgLatency = traces.length > 0
    ? Math.round(traces.reduce((sum, t) => sum + (t.latency_ms || 0), 0) / traces.length)
    : 0

  const messageColumns = [
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 80,
      render: (role: string) => {
        const colorMap: Record<string, string> = {
          system: 'blue',
          user: 'green',
          assistant: 'purple',
          tool: 'orange',
        }
        return <Tag color={colorMap[role] || 'default'}>{role}</Tag>
      },
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      render: (content: string | null) => (
        <span className="text-content-secondary text-xs line-clamp-2">
          {content || '(空)'}
        </span>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (v: string) => formatBeijingTime(v),
    },
  ]

  const traceColumns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 150,
      render: (v: string) => formatBeijingTime(v),
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      width: 120,
      render: (v: string, record: LLMTrace) => (
        <span className="text-xs">{record.provider} / {v}</span>
      ),
    },
    {
      title: 'Tokens',
      key: 'tokens',
      width: 100,
      render: (_: any, record: LLMTrace) => (
        <span className="text-xs text-content-secondary">
          {record.input_tokens} / {record.output_tokens}
        </span>
      ),
    },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      width: 80,
      render: (v: number) => `${v}ms`,
    },
    {
      title: '错误',
      dataIndex: 'error_type',
      key: 'error_type',
      width: 80,
      render: (v: string | undefined) =>
        v ? (
          <Tag color="red" icon={<AlertCircle size={12} />}>
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
        maxHeight: 300,
        fontSize: 11,
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  )

  return (
    <Drawer
      title={conversation?.title || '对话详情'}
      placement="right"
      width={640}
      onClose={onClose}
      open={open}
      styles={{ body: { padding: 0 } }}
    >
      <Spin spinning={loading}>
        <div className="p-5">
          {/* 基本信息 */}
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-content-primary mb-3">基本信息</h3>
            <Descriptions size="small" column={2} bordered className="text-xs">
              <Descriptions.Item label="ID">{conversation?.id}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={conversation?.status === 'active' ? 'green' : 'default'}>
                  {conversation?.status || '-'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {formatBeijingTime(conversation?.created_at || null)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间" span={2}>
                {formatBeijingTime(conversation?.updated_at || null)}
              </Descriptions.Item>
            </Descriptions>
          </div>

          {/* 统计卡片 */}
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-content-primary mb-3">统计</h3>
            <div className="grid grid-cols-2 gap-3">
              <StatItem
                icon={<MessageSquare size={16} />}
                label="消息数"
                value={messages.length}
              />
              <StatItem
                icon={<BarChart3 size={16} />}
                label="模型调用"
                value={traces.length}
              />
              <StatItem
                icon={<Zap size={16} />}
                label="总 Tokens"
                value={`${totalInputTokens + totalOutputTokens}`}
              />
              <StatItem
                icon={<Clock size={16} />}
                label="平均延迟"
                value={`${avgLatency}ms`}
              />
            </div>
          </div>

          {/* Token 明细 */}
          {traces.length > 0 && (
            <div className="mb-5">
              <h3 className="text-sm font-semibold text-content-primary mb-3">Token 用量</h3>
              <Descriptions size="small" column={2} bordered className="text-xs">
                <Descriptions.Item label="Input">{totalInputTokens}</Descriptions.Item>
                <Descriptions.Item label="Output">{totalOutputTokens}</Descriptions.Item>
              </Descriptions>
            </div>
          )}

          {/* 消息列表 */}
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-content-primary mb-3">
              消息 ({messages.length})
            </h3>
            {messages.length === 0 ? (
              <Empty description="暂无消息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table
                dataSource={[...messages].reverse()}
                columns={messageColumns}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ y: 240 }}
              />
            )}
          </div>

          {/* Trace 列表 */}
          <div>
            <h3 className="text-sm font-semibold text-content-primary mb-3">
              模型调用记录 ({traces.length})
            </h3>
            {traces.length === 0 ? (
              <Empty description="暂无调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table
                dataSource={traces}
                columns={traceColumns}
                rowKey="trace_id"
                pagination={false}
                size="small"
                scroll={{ y: 240 }}
                expandable={{
                  expandedRowRender: (record: LLMTrace) => {
                    const items = [
                      ...(record.request_payload
                        ? [{ key: 'req', label: '请求', children: renderJson(record.request_payload) }]
                        : []),
                      ...(record.response_payload
                        ? [{ key: 'resp', label: '响应', children: renderJson(record.response_payload) }]
                        : []),
                    ]
                    return items.length > 0 ? (
                      <Collapse items={items} size="small" />
                    ) : null
                  },
                }}
              />
            )}
          </div>
        </div>
      </Spin>
    </Drawer>
  )
}
