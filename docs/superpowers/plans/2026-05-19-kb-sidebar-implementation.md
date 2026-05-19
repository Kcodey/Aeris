# 知识库标签页实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在侧边栏「对话」和「监控」之间新增「知识库」标签页，展示知识库列表并提供 Toggle 开关控制当前对话是否启用该知识库。

**架构：** 前端改动为主，后端只需扩展 ConversationUpdate schema 支持 knowledge_base_ids 字段。前端采用 React + Ant Design Modal 实现确认框交互。

**涉及：** 后端 1 个文件，前端 5 个文件

---

## Task 1: 后端 - 扩展 ConversationUpdate 支持 knowledge_base_ids

**Files:**
- Modify: `meditatio/schemas/chat.py:30-32`
- Modify: `meditatio/services/chat_service.py:207-224`

- [ ] **Step 1: 检查当前 ConversationUpdate**

```python
# meditatio/schemas/chat.py:30-32
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
```

- [ ] **Step 2: 添加 knowledge_base_ids 字段**

```python
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    knowledge_base_ids: Optional[List[int]] = None  # 支持 KB 多选
```

- [ ] **Step 3: 检查 update_conversation 方法**

读取 `meditatio/services/chat_service.py` 的 `update_conversation` 方法（约 line 207-224）

- [ ] **Step 4: 扩展 update_conversation 支持 knowledge_base_ids**

在 `update_conversation` 方法中添加：

```python
if data.knowledge_base_ids is not None:
    conversation.knowledge_base_ids = json.dumps(data.knowledge_base_ids) if data.knowledge_base_ids else None
    conversation.updated_at = datetime.utcnow()
```

- [ ] **Step 5: 验证改动**

```bash
source /home/skdy/miniconda3/etc/profile.d/conda.sh && conda activate meditatio && python -c "from meditatio.schemas.chat import ConversationUpdate; print(ConversationUpdate.model_fields.keys())"
```

预期输出包含 `knowledge_base_ids`

- [ ] **Step 6: 提交**

```bash
git add meditatio/schemas/chat.py meditatio/services/chat_service.py && git commit -m "feat: support knowledge_base_ids in ConversationUpdate"
```

---

## Task 2: 前端 - 创建 rag.ts Service

**Files:**
- Create: `frontend/src/services/rag.ts`

- [ ] **Step 1: 创建 rag.ts**

```typescript
import { api } from './api'

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  collection_name: string
  created_by: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export const ragApi = {
  getKnowledgeBases() {
    return api.get<KnowledgeBase[]>('/rag/kb')
  },
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/services/rag.ts && git commit -m "feat(frontend): add rag API service"
```

---

## Task 3: 前端 - 扩展 chat.ts 的 updateConversation

**Files:**
- Modify: `frontend/src/services/chat.ts`

- [ ] **Step 1: 检查当前 chatApi**

读取 `frontend/src/services/chat.ts` 了解当前 updateConversation 签名

- [ ] **Step 2: 更新 updateConversation 支持 knowledge_base_ids**

```typescript
updateConversation(id: number, data: { title?: string; knowledge_base_ids?: number[] }) {
  return api.patch(`/conversations/${id}`, data)
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/services/chat.ts && git commit -m "feat(frontend): updateConversation supports knowledge_base_ids"
```

---

## Task 4: 前端 - Sidebar 添加知识库 NavItem

**Files:**
- Modify: `frontend/src/components/Layout/Sidebar.tsx:179-182`

- [ ] **Step 1: 检查 navItems 定义**

当前：
```typescript
const navItems = [
  { key: '/', label: '对话', icon: MessageSquare },
  { key: '/monitoring', label: '监控', icon: BarChart3 },
]
```

- [ ] **Step 2: 添加 BookOpen icon 和知识库 navItem**

```typescript
import { MessageSquare, BarChart3, LogOut, Plus, X, Edit2, Check, Trash2, Info, BookOpen } from 'lucide-react'

const navItems = [
  { key: '/', label: '对话', icon: MessageSquare },
  { key: '/kb', label: '知识库', icon: BookOpen },
  { key: '/monitoring', label: '监控', icon: BarChart3 },
]
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Layout/Sidebar.tsx && git commit -m "feat(frontend): add KB nav item to Sidebar"
```

---

## Task 5: 前端 - AppLayout 添加 /kb 路由

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.tsx:125`

- [ ] **Step 1: 添加 KnowledgeBasePage import 和路由**

```typescript
import KnowledgeBasePage from '../../pages/KnowledgeBasePage'

// 在 Routes 中添加
<Route path="/kb" element={<KnowledgeBasePage />} />
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/Layout/AppLayout.tsx && git commit -m "feat(frontend): add /kb route to AppLayout"
```

---

## Task 6: 前端 - 创建 KnowledgeBasePage 组件

**Files:**
- Create: `frontend/src/pages/KnowledgeBasePage.tsx`

- [ ] **Step 1: 创建 KnowledgeBasePage 组件**

```typescript
import React, { useEffect, useState } from 'react'
import { Switch, message } from 'antd'
import { BookOpen } from 'lucide-react'
import { ragApi, KnowledgeBase } from '../services/rag'
import { chatApi } from '../services/chat'
import { Conversation } from '../types/chat'

interface KnowledgeBasePageProps {
  conversations?: Conversation[]
  selectedConversationId?: number | null
  onRefreshConversations?: () => void
}

export default function KnowledgeBasePage({
  conversations = [],
  selectedConversationId = null,
  onRefreshConversations,
}: KnowledgeBasePageProps) {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadKnowledgeBases()
  }, [])

  const loadKnowledgeBases = async () => {
    try {
      setLoading(true)
      const response = await ragApi.getKnowledgeBases()
      setKnowledgeBases(response.data)
    } catch (error) {
      console.error('Failed to load knowledge bases:', error)
      message.error('加载知识库失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取当前对话的 KB ids
  const getCurrentKBIds = (): number[] => {
    if (!selectedConversationId) return []
    const conv = conversations.find(c => c.id === selectedConversationId)
    return conv?.knowledge_base_ids || []
  }

  // 判断某个 KB 是否启用
  const isKBEnabled = (kbId: number): boolean => {
    return getCurrentKBIds().includes(kbId)
  }

  // 处理 Toggle 切换
  const handleToggle = async (kb: KnowledgeBase, enabled: boolean) => {
    if (!selectedConversationId) {
      message.warning('请先选择一个对话')
      return
    }

    const currentIds = getCurrentKBIds()
    let newIds: number[]
    if (enabled) {
      newIds = [...currentIds, kb.id]
    } else {
      newIds = currentIds.filter(id => id !== kb.id)
    }

    try {
      await chatApi.updateConversation(selectedConversationId, {
        knowledge_base_ids: newIds
      })
      message.success(enabled ? `已启用${kb.name}` : `已禁用${kb.name}`)
      onRefreshConversations?.()
    } catch (error) {
      console.error('Failed to update conversation:', error)
      message.error('操作失败，请重试')
    }
  }

  // 确认框
  const showConfirm = (kb: KnowledgeBase, enabled: boolean) => {
    const title = enabled ? '启用知识库' : '禁用知识库'
    const content = `${enabled ? '启用' : '禁用'}后将${enabled ? '为此对话启用' : '关闭'}「${kb.name}」检索`

    if (!selectedConversationId) {
      message.warning('请先选择一个对话')
      return
    }

    // 使用 antd Modal.confirm
    import('antd').then(({ Modal }) => {
      Modal.confirm({
        title,
        content,
        okText: enabled ? '启用' : '禁用',
        cancelText: '取消',
        onOk: () => handleToggle(kb, enabled),
      })
    })
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <BookOpen size={20} className="text-brand" />
        <h1 className="text-lg font-semibold text-content-primary">我的知识库</h1>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-content-tertiary">加载中...</span>
        </div>
      ) : knowledgeBases.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-content-tertiary">
          <BookOpen size={48} className="opacity-20 mb-3" />
          <p>暂无知识库</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto space-y-3">
          {knowledgeBases.map(kb => (
            <div
              key={kb.id}
              className="flex items-center justify-between p-4 bg-surface-page rounded-lg hover:bg-[#F5F5F5] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-light flex items-center justify-center">
                  <BookOpen size={20} className="text-brand" />
                </div>
                <div>
                  <div className="font-medium text-content-primary">{kb.name}</div>
                  <div className="text-xs text-content-tertiary">
                    最后更新: {kb.updated_at ? new Date(kb.updated_at).toLocaleDateString('zh-CN') : '-'}
                  </div>
                </div>
              </div>
              <Switch
                checked={isKBEnabled(kb.id)}
                onChange={(checked) => showConfirm(kb, checked)}
                disabled={!selectedConversationId}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/KnowledgeBasePage.tsx && git commit -m "feat(frontend): add KnowledgeBasePage component"
```

---

## Task 7: 前端 - AppLayout 传递 props 给 KnowledgeBasePage

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.tsx:125`

- [ ] **Step 1: 更新 /kb 路由传递 props**

```typescript
<Route path="/kb" element={
  <KnowledgeBasePage
    conversations={conversations}
    selectedConversationId={selectedConversationId}
    onRefreshConversations={refreshConversations}
  />
} />
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/Layout/AppLayout.tsx && git commit -m "feat(frontend): pass props to KnowledgeBasePage"
```

---

## Task 8: 前端 - 修改 Conversation 类型定义

**Files:**
- Modify: `frontend/src/types/chat.ts`

- [ ] **Step 1: 检查当前 Conversation 类型**

读取 `frontend/src/types/chat.ts`

- [ ] **Step 2: 添加 knowledge_base_ids 字段**

```typescript
export interface Conversation {
  id: number
  user_id: number
  title: string | null
  status: string
  created_at: string
  updated_at: string | null
  last_message_preview?: string | null
  knowledge_base_ids?: number[]  // 新增
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/types/chat.ts && git commit -m "feat(frontend): add knowledge_base_ids to Conversation type"
```

---

## Task 9: 验证 - 前端构建测试

**Files:**
- None (验证步骤)

- [ ] **Step 1: 检查依赖是否安装**

```bash
cd frontend && npm ls antd 2>/dev/null | head -5
```

- [ ] **Step 2: 构建测试**

```bash
cd frontend && npm run build 2>&1 | tail -30
```

预期：构建成功，无 error

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "test: verify KB sidebar feature builds successfully"
```

---

## 执行选项

**1. Subagent-Driven (recommended)** - 每个任务派发一个 subagent，任务间审查，快速迭代

**2. Inline Execution** - 在本会话中逐步执行，带检查点

**选择哪个方式？**