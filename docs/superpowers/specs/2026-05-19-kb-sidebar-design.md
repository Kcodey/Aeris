# 知识库标签页 - 前端设计

> 日期：2026-05-19
> 状态：已确认

## 概述

在侧边栏「对话」和「监控」之间新增「知识库」标签页，用于展示当前账号可访问的知识库列表，并提供 Toggle 开关控制当前对话是否启用该知识库。

## 交互流程

```
用户点击 Toggle
    ↓
检查是否有选中的对话
    ↓
├── 没有 → Toast 提示"请先选择一个对话"，禁用操作
└── 有 → 弹出确认框
              ↓
         ┌─────────────────────────────┐
         │ 启用"产品文档"知识库？      │
         │                             │
         │ 将为此对话开启 RAG 检索     │
         │                             │
         │ [取消]        [确认]        │
         └─────────────────────────────┘
              ↓
         用户点击确认 → 调用 API 更新对话的 knowledge_base_ids
              ↓
         更新成功 → Toast "已启用产品文档"
         更新失败 → Toast "操作失败，请重试"
```

## 后端改动

### API 1: ConversationUpdate Schema 扩展

**文件：** `meditatio/schemas/chat.py`

```python
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    knowledge_base_ids: Optional[List[int]] = None  # 新增
```

**文件：** `meditatio/services/chat_service.py`

在 `update_conversation` 方法中处理 `knowledge_base_ids` 更新：

```python
if data.knowledge_base_ids is not None:
    conversation.knowledge_base_ids = json.dumps(data.knowledge_base_ids) if data.knowledge_base_ids else None
    conversation.updated_at = datetime.utcnow()
```

## 前端改动

### 1. Sidebar navItems 扩展

**文件：** `frontend/src/components/Layout/Sidebar.tsx`

```typescript
const navItems = [
  { key: '/', label: '对话', icon: MessageSquare },
  { key: '/kb', label: '知识库', icon: BookOpen },
  { key: '/monitoring', label: '监控', icon: BarChart3 },
]
```

### 2. AppLayout 路由扩展

**文件：** `frontend/src/components/Layout/AppLayout.tsx`

```typescript
<Route path="/kb" element={<KnowledgeBasePage conversations={conversations} />} />
```

### 3. KnowledgeBasePage 组件

**文件：** `frontend/src/pages/KnowledgeBasePage.tsx`

**Props:**
- `conversations: Conversation[]` - 用于获取当前选中的对话

**功能：**
1. 挂载时从 `/api/v1/rag/kb` 获取知识库列表
2. 获取当前选中对话的 `knowledge_base_ids`
3. 渲染知识库列表，每个 KB 有一个 Toggle 开关
4. Toggle 状态 = 当前对话的 `knowledge_base_ids` 是否包含该 KB id

**UI 结构：**
```
┌─────────────────────────────────────┐
│ 我的知识库                    [?]   │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 📚 产品文档                    [○]│  ← Toggle 关闭
│ │    最后更新: 2024-01-15         │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 📚 常见问题 FAQ                [●]│  ← Toggle 开启
│ │    最后更新: 2024-01-10         │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 4. 确认框组件

使用 Ant Design Modal 或类似组件：

```typescript
const showConfirm = (kb: KnowledgeBase, enabled: boolean) => {
  Modal.confirm({
    title: enabled ? '启用知识库' : '禁用知识库',
    content: `${enabled ? '启用' : '禁用'}后将${enabled ? '为此对话启用' : '关闭'}「${kb.name}」检索`,
    okText: enabled ? '启用' : '禁用',
    cancelText: '取消',
    onOk: () => handleToggle(kb, enabled),
  })
}
```

### 5. Toggle 操作处理函数

```typescript
const handleToggle = async (kb: KnowledgeBase, enabled: boolean) => {
  if (!selectedConversationId) {
    message.warning('请先选择一个对话')
    return;
  }

  // 获取当前对话的 knowledge_base_ids
  const currentConv = conversations.find(c => c.id === selectedConversationId);
  const currentIds = currentConv?.knowledge_base_ids || [];

  // 计算新的 ids
  let newIds: number[];
  if (enabled) {
    newIds = [...currentIds, kb.id];
  } else {
    newIds = currentIds.filter(id => id !== kb.id);
  }

  // 调用 API 更新
  try {
    await chatApi.updateConversation(selectedConversationId, {
      knowledge_base_ids: newIds
    });
    message.success(enabled ? `已启用${kb.name}` : `已禁用${kb.name}`);
    // 刷新对话列表
    await refreshConversations();
  } catch (error) {
    message.error('操作失败，请重试');
  }
}
```

### 6. API Service 扩展

**文件：** `frontend/src/services/chat.ts`

```typescript
export const chatApi = {
  // ... existing methods
  updateConversation(id: number, data: { title?: string; knowledge_base_ids?: number[] }) {
    return api.patch(`/conversations/${id}`, data)
  }
}
```

**文件：** `frontend/src/services/api.ts` (或新建 `services/rag.ts`)

```typescript
export const ragApi = {
  getKnowledgeBases() {
    return api.get('/rag/kb')
  }
}
```

## 数据流

```
用户点击 Toggle
    ↓
前端检查 selectedConversationId
    ↓ (有对话)
弹出确认框 → 用户确认
    ↓
计算新的 knowledge_base_ids
    ↓
PATCH /conversations/{id}
    ↓
后端更新 conversation.knowledge_base_ids
    ↓
前端 refreshConversations() 更新侧边栏对话列表
    ↓
ChatService.send_message() 时读取 conversation.knowledge_base_ids
    ↓
触发 _get_rag_context() 注入 RAG 上下文
```

## 错误处理

| 场景 | 处理 |
|------|------|
| 没有选中的对话 | Toast "请先选择一个对话"，不弹确认框 |
| API 调用失败 | Toast "操作失败，请重试"，不更新 UI |
| 获取 KB 列表失败 | 显示空状态 + 重试按钮 |
| 更新后刷新对话失败 | UI 已更新，下次刷新时会同步 |

## 涉及文件清单

**后端 (1 个文件)：**
- `meditatio/services/chat_service.py` - update_conversation 支持 knowledge_base_ids

**前端 (5 个文件)：**
- `frontend/src/components/Layout/Sidebar.tsx` - 添加知识库 navItem
- `frontend/src/components/Layout/AppLayout.tsx` - 添加 /kb 路由
- `frontend/src/pages/KnowledgeBasePage.tsx` - 新建，知识库列表页面
- `frontend/src/services/chat.ts` - updateConversation 支持 knowledge_base_ids
- `frontend/src/services/rag.ts` - 新建，ragApi.getKnowledgeBases