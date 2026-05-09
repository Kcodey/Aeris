import time
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from collections import deque
import logging
import json
from contextlib import asynccontextmanager

logger = logging.getLogger("aeris.timing")


@dataclass
class TimingEvent:
    """单个耗时事件"""
    trace_id: str
    stage: str  # 如: "ws_received", "api_connect", "first_token"
    timestamp: float  # 时间戳（秒）
    duration_ms: Optional[int] = None  # 如果是区间事件
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingTrace:
    """完整的追踪记录"""
    trace_id: str
    conversation_id: int
    user_id: int
    message_id: Optional[int] = None
    events: List[TimingEvent] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_event(self, stage: str, timestamp: float = None,
                  duration_ms: Optional[int] = None,
                  metadata: Optional[Dict] = None):
        """添加事件"""
        self.events.append(TimingEvent(
            trace_id=self.trace_id,
            stage=stage,
            timestamp=timestamp or time.time(),
            duration_ms=duration_ms,
            metadata=metadata or {}
        ))

    def calculate_deltas(self) -> Dict[str, Any]:
        """计算各阶段耗时"""
        if not self.events:
            return {}

        # 按时间排序
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        deltas = {}
        base_time = sorted_events[0].timestamp

        for i, event in enumerate(sorted_events):
            # 绝对时间（从起点）
            deltas[f"{event.stage}_abs_ms"] = int((event.timestamp - base_time) * 1000)
            # 区间耗时（如果有）
            if event.duration_ms:
                deltas[f"{event.stage}_ms"] = event.duration_ms

        # 计算关键派生指标
        if len(sorted_events) >= 2:
            deltas["total_ms"] = int((sorted_events[-1].timestamp - base_time) * 1000)

        return deltas

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        deltas = self.calculate_deltas()
        return {
            "trace_id": self.trace_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "events": [
                {
                    "stage": e.stage,
                    "ts": round(e.timestamp, 6),
                    "dur": e.duration_ms,
                    "meta": e.metadata
                }
                for e in self.events
            ],
            "deltas": deltas,
            "created_at": self.created_at
        }


class TimingCollector:
    """高性能追踪收集器 - 生产安全"""

    def __init__(self, max_queue_size: int = 10000):
        self.enabled = False
        self.full_mode = False  # False=仅关键指标, True=全量
        self.target_conversations: set = set()  # 指定追踪的对话
        self.target_users: set = set()  # 指定追踪的用户
        self.slow_threshold_ms = 3000  # 慢请求阈值

        # 环形缓冲区（内存安全）
        self._queue: deque = deque(maxlen=max_queue_size)
        self._save_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # 最近完成的追踪记录（用于查询）
        self._recent_traces: deque = deque(maxlen=100)

    def configure(self, settings: Dict[str, Any]):
        """配置收集器"""
        self.enabled = settings.get("ENABLE_TIMING_TRACE", False)
        self.full_mode = settings.get("TIMING_FULL_MODE", False)
        self.slow_threshold_ms = settings.get("TIMING_SLOW_THRESHOLD_MS", 3000)
        max_size = settings.get("TIMING_QUEUE_SIZE", 10000)
        self._queue = deque(maxlen=max_size)

        logger.info(f"TimingCollector configured (enabled={self.enabled}, full_mode={self.full_mode}, "
                   f"slow_threshold={self.slow_threshold_ms}ms)")

    def should_collect(self, conversation_id: int, user_id: int) -> bool:
        """判断是否收集 - 支持全量/采样/指定目标"""
        if not self.enabled:
            return False

        # 指定目标优先
        if conversation_id in self.target_conversations:
            return True
        if user_id in self.target_users:
            return True

        # 全量模式（仅开发/测试）
        if self.full_mode:
            return True

        return False

    def start_collecting(self):
        """启动后台保存任务"""
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(self._background_save())
            logger.info("TimingCollector background task started")

    def stop_collecting(self):
        """停止收集"""
        self._stop_event.set()
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

    async def submit(self, trace: TimingTrace):
        """提交追踪记录（非阻塞）"""
        # 队列满时自动丢弃最旧（deque 行为）
        self._queue.append(trace)

    async def _background_save(self):
        """后台保存循环"""
        while not self._stop_event.is_set():
            try:
                # 批量保存
                batch = []
                while self._queue and len(batch) < 100:
                    batch.append(self._queue.popleft())

                if batch:
                    await self._persist_batch(batch)
                else:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=0.1
                    )

            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Timing save error: {e}")
                await asyncio.sleep(1)

        # 退出前保存剩余数据
        remaining = list(self._queue)
        if remaining:
            await self._persist_batch(remaining)

    async def _persist_batch(self, batch: List[TimingTrace]):
        """持久化一批追踪数据"""
        for trace in batch:
            try:
                data = trace.to_dict()

                # 保存到最近记录
                self._recent_traces.append(data)

                # 检查是否为慢请求
                total_ms = data.get("deltas", {}).get("total_ms", 0)
                is_slow = total_ms > self.slow_threshold_ms

                # 输出到日志
                if is_slow:
                    logger.warning(f"[TIMING_SLOW] {json.dumps(data, ensure_ascii=False)}")
                else:
                    logger.info(f"[TIMING_TRACE] {json.dumps(data, ensure_ascii=False)}")

            except Exception as e:
                logger.error(f"Failed to persist trace {trace.trace_id}: {e}")

    @asynccontextmanager
    async def trace_scope(self, trace_id: str, conversation_id: int,
                          user_id: int, message_id: Optional[int] = None):
        """上下文管理器 - 自动收集"""
        trace = TimingTrace(
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
            message_id=message_id
        )

        try:
            yield trace
        finally:
            # 上下文退出时自动提交
            await self.submit(trace)

    # 管理 API
    def enable_for_conversation(self, conversation_id: int):
        """为特定对话开启追踪"""
        self.target_conversations.add(conversation_id)
        logger.info(f"Timing trace enabled for conversation {conversation_id}")

    def disable_for_conversation(self, conversation_id: int):
        """为特定对话关闭追踪"""
        self.target_conversations.discard(conversation_id)
        logger.info(f"Timing trace disabled for conversation {conversation_id}")

    def enable_for_user(self, user_id: int):
        """为特定用户开启追踪"""
        self.target_users.add(user_id)
        logger.info(f"Timing trace enabled for user {user_id}")

    def disable_for_user(self, user_id: int):
        """为特定用户关闭追踪"""
        self.target_users.discard(user_id)
        logger.info(f"Timing trace disabled for user {user_id}")

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "enabled": self.enabled,
            "full_mode": self.full_mode,
            "queue_size": len(self._queue),
            "target_conversations": list(self.target_conversations),
            "target_users": list(self.target_users),
            "slow_threshold_ms": self.slow_threshold_ms
        }


# 全局单例
_collector: Optional[TimingCollector] = None


def get_collector() -> TimingCollector:
    """获取收集器实例"""
    global _collector
    if _collector is None:
        _collector = TimingCollector()
    return _collector


def init_collector(settings: Optional[Dict[str, Any]] = None):
    """初始化收集器"""
    global _collector
    if _collector is None:
        _collector = TimingCollector()

    if settings:
        _collector.configure(settings)

    return _collector
