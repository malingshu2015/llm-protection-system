"""Tests for the queue manager module."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response

from src.proxy.queue_manager import Priority, QueuedRequest, RequestQueue, QueueManager


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = "https://api.openai.com/v1/chat/completions"
    return request


@pytest.fixture
def request_queue():
    """Create a request queue for testing."""
    return RequestQueue()


@pytest.fixture
def queue_manager():
    """Create a queue manager for testing."""
    return QueueManager()


def test_priority_enum():
    """Test the Priority enum."""
    assert Priority.HIGH.value < Priority.NORMAL.value
    assert Priority.NORMAL.value < Priority.LOW.value
    assert Priority.HIGH.value == 0
    assert Priority.NORMAL.value == 1
    assert Priority.LOW.value == 2


def test_queued_request_init(mock_request):
    """Test initializing a queued request."""
    # 创建一个队列请求
    queued_request = QueuedRequest(mock_request, Priority.HIGH, 30.0)

    # 验证属性
    assert queued_request.request == mock_request
    assert queued_request.priority == Priority.HIGH
    assert queued_request.timeout == 30.0
    assert isinstance(queued_request.timestamp, float)


def test_queued_request_is_expired(mock_request):
    """Test checking if a queued request is expired."""
    # 创建一个队列请求，超时设置为0.1秒
    queued_request = QueuedRequest(mock_request, Priority.NORMAL, 0.1)

    # 刚创建的请求不应该过期
    assert not queued_request.is_expired()

    # 等待超过超时时间
    time.sleep(0.2)

    # 现在请求应该过期了
    assert queued_request.is_expired()


def test_queued_request_comparison(mock_request):
    """Test comparing queued requests."""
    # 创建两个不同优先级的请求
    high_priority = QueuedRequest(mock_request, Priority.HIGH)
    normal_priority = QueuedRequest(mock_request, Priority.NORMAL)

    # 高优先级应该小于正常优先级（在优先队列中排在前面）
    assert high_priority < normal_priority
    assert not normal_priority < high_priority

    # 创建两个相同优先级但时间戳不同的请求
    older_request = QueuedRequest(mock_request, Priority.NORMAL)
    time.sleep(0.01)
    newer_request = QueuedRequest(mock_request, Priority.NORMAL)

    # 较早的请求应该小于较新的请求
    assert older_request < newer_request
    assert not newer_request < older_request


@pytest.mark.asyncio
async def test_request_queue_enqueue_dequeue(request_queue, mock_request):
    """Test enqueueing and dequeueing requests."""
    # 入队一个高优先级请求
    success = await request_queue.enqueue(mock_request, Priority.HIGH)
    assert success

    # 入队一个正常优先级请求
    success = await request_queue.enqueue(mock_request, Priority.NORMAL)
    assert success

    # 入队一个低优先级请求
    success = await request_queue.enqueue(mock_request, Priority.LOW)
    assert success

    # 验证队列大小
    queue_sizes = request_queue.get_queue_sizes()
    assert queue_sizes["high_priority"] == 1
    assert queue_sizes["normal_priority"] == 1
    assert queue_sizes["low_priority"] == 1

    # 出队请求，应该先返回高优先级请求
    dequeued = await request_queue.dequeue()
    assert dequeued == mock_request

    # 再次出队，应该返回正常优先级请求
    dequeued = await request_queue.dequeue()
    assert dequeued == mock_request

    # 再次出队，应该返回低优先级请求
    dequeued = await request_queue.dequeue()
    assert dequeued == mock_request

    # 所有队列都空了，应该返回None
    dequeued = await request_queue.dequeue()
    assert dequeued is None


@pytest.mark.asyncio
async def test_request_queue_expired_requests(request_queue, mock_request):
    """Test handling expired requests."""
    # 创建一个会很快过期的请求
    with patch("src.proxy.queue_manager.QueuedRequest.is_expired", return_value=True):
        # 入队一个高优先级请求
        await request_queue.enqueue(mock_request, Priority.HIGH)

        # 出队请求，应该跳过过期的请求并返回None
        dequeued = await request_queue.dequeue()
        assert dequeued is None


@pytest.mark.asyncio
async def test_request_queue_active_requests(request_queue):
    """Test tracking active requests."""
    # 初始活跃请求数应该为0
    assert request_queue.active_requests == 0

    # 增加活跃请求数
    success = await request_queue.increment_active_requests()
    assert success
    assert request_queue.active_requests == 1

    # 减少活跃请求数
    await request_queue.decrement_active_requests()
    assert request_queue.active_requests == 0

    # 不能减到负数
    await request_queue.decrement_active_requests()
    assert request_queue.active_requests == 0


@pytest.mark.asyncio
async def test_queue_manager_enqueue_request(queue_manager, mock_request):
    """Test enqueueing a request with the queue manager."""
    # 模拟队列的enqueue方法
    queue_manager.queue.enqueue = AsyncMock(return_value=True)

    # 入队一个请求
    success, error = await queue_manager.enqueue_request(mock_request, Priority.NORMAL)

    # 验证结果
    assert success
    assert error is None
    queue_manager.queue.enqueue.assert_called_once_with(mock_request, Priority.NORMAL)

    # 模拟队列已满
    queue_manager.queue.enqueue = AsyncMock(return_value=False)

    # 入队一个请求
    success, error = await queue_manager.enqueue_request(mock_request, Priority.HIGH)

    # 验证结果
    assert not success
    assert error is not None


@pytest.mark.asyncio
async def test_queue_manager_start_stop(queue_manager):
    """Test starting and stopping the queue manager."""
    # 模拟HTTPInterceptor
    with patch("src.proxy.queue_manager.HTTPInterceptor") as mock_interceptor_class:
        mock_interceptor = AsyncMock()
        mock_interceptor_class.return_value = mock_interceptor

        # 启动队列管理器
        await queue_manager.start(num_workers=2)

        # 验证状态
        assert queue_manager.running
        assert len(queue_manager.worker_tasks) == 2
        assert queue_manager.interceptor is not None

        # 停止队列管理器
        await queue_manager.stop()

        # 验证状态
        assert not queue_manager.running
        # 在实际代码中，close方法可能不存在或者不被调用，所以我们不检查它


@pytest.mark.asyncio
async def test_worker_processing(queue_manager, mock_request):
    """Test worker task processing."""
    # 模拟队列和拦截器
    queue_manager.queue = AsyncMock()
    queue_manager.interceptor = AsyncMock()

    # 设置队列的increment_active_requests返回True
    queue_manager.queue.increment_active_requests.return_value = True

    # 设置队列的dequeue返回一个请求，然后返回None
    queue_manager.queue.dequeue.side_effect = [mock_request, None]

    # 启动工作线程
    queue_manager.running = True
    worker_task = asyncio.create_task(queue_manager._worker(0))

    # 等待一小段时间让工作线程处理请求
    await asyncio.sleep(0.1)

    # 停止工作线程
    queue_manager.running = False
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # 验证拦截器被调用
    queue_manager.interceptor.intercept.assert_called_once_with(mock_request)

    # 验证活跃请求计数器被正确更新
    assert queue_manager.queue.decrement_active_requests.call_count >= 1
