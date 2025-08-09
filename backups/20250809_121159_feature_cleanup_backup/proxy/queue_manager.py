"""Queue manager for handling request prioritization and rate limiting."""

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Request, Response

from src.config import settings
from src.logger import logger
from src.proxy.interceptor import HTTPInterceptor, InterceptedRequest


class Priority(Enum):
    """Priority levels for requests."""

    HIGH = 0
    NORMAL = 1
    LOW = 2


class QueuedRequest:
    """A request in the queue with metadata."""

    def __init__(
        self,
        request: Request,
        priority: Priority = Priority.NORMAL,
        timeout: Optional[float] = None,
    ):
        """Initialize a queued request.

        Args:
            request: The FastAPI request.
            priority: The priority level of the request.
            timeout: The timeout for the request in seconds.
        """
        self.request = request
        self.priority = priority
        self.timestamp = time.time()
        self.timeout = timeout or settings.proxy.timeout

    def is_expired(self) -> bool:
        """Check if the request has expired.

        Returns:
            True if the request has expired, False otherwise.
        """
        return time.time() - self.timestamp > self.timeout

    def __lt__(self, other: "QueuedRequest") -> bool:
        """Compare requests for priority queue ordering.

        Args:
            other: The other queued request.

        Returns:
            True if this request has higher priority than the other.
        """
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class RequestQueue:
    """Manages request queues with different priority levels."""

    def __init__(self):
        """Initialize the request queue."""
        self.high_priority: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=settings.proxy.request_queue_size
        )
        self.normal_priority: asyncio.Queue = asyncio.Queue(
            maxsize=settings.proxy.request_queue_size
        )
        self.low_priority: asyncio.Queue = asyncio.Queue(
            maxsize=settings.proxy.request_queue_size
        )

        # Track active requests
        self.active_requests = 0
        self.active_requests_lock = asyncio.Lock()

    async def enqueue(self, request: Request, priority: Priority = Priority.NORMAL) -> bool:
        """Enqueue a request with the specified priority.

        Args:
            request: The FastAPI request.
            priority: The priority level of the request.

        Returns:
            True if the request was enqueued successfully, False otherwise.
        """
        queued_request = QueuedRequest(request, priority)

        try:
            if priority == Priority.HIGH:
                await self.high_priority.put(queued_request)
            elif priority == Priority.NORMAL:
                await self.normal_priority.put(queued_request)
            else:
                await self.low_priority.put(queued_request)

            logger.debug(
                f"Enqueued request with priority {priority.name}, "
                f"queue sizes: high={self.high_priority.qsize()}, "
                f"normal={self.normal_priority.qsize()}, "
                f"low={self.low_priority.qsize()}"
            )

            return True
        except asyncio.QueueFull:
            logger.warning(f"Queue is full for priority {priority.name}")
            return False

    async def dequeue(self) -> Optional[Request]:
        """Dequeue a request based on priority.

        Returns:
            The dequeued request, or None if all queues are empty.
        """
        # Check high priority queue first
        if not self.high_priority.empty():
            queued_request = await self.high_priority.get()
            self.high_priority.task_done()

            if queued_request.is_expired():
                logger.warning("Discarded expired high priority request")
                return await self.dequeue()

            return queued_request.request

        # Check normal priority queue next
        if not self.normal_priority.empty():
            queued_request = await self.normal_priority.get()
            self.normal_priority.task_done()

            if queued_request.is_expired():
                logger.warning("Discarded expired normal priority request")
                return await self.dequeue()

            return queued_request.request

        # Check low priority queue last
        if not self.low_priority.empty():
            queued_request = await self.low_priority.get()
            self.low_priority.task_done()

            if queued_request.is_expired():
                logger.warning("Discarded expired low priority request")
                return await self.dequeue()

            return queued_request.request

        # All queues are empty
        return None

    async def increment_active_requests(self) -> bool:
        """Increment the active request counter if below the limit.

        Returns:
            True if the counter was incremented, False if at the limit.
        """
        async with self.active_requests_lock:
            if self.active_requests >= settings.proxy.max_concurrent_requests:
                return False

            self.active_requests += 1
            return True

    async def decrement_active_requests(self) -> None:
        """Decrement the active request counter."""
        async with self.active_requests_lock:
            self.active_requests = max(0, self.active_requests - 1)

    def get_queue_sizes(self) -> Dict[str, int]:
        """Get the current sizes of all queues.

        Returns:
            A dictionary with queue sizes.
        """
        return {
            "high_priority": self.high_priority.qsize(),
            "normal_priority": self.normal_priority.qsize(),
            "low_priority": self.low_priority.qsize(),
            "active_requests": self.active_requests,
        }


class QueueManager:
    """Manages request queuing, prioritization, and processing."""

    def __init__(self):
        """Initialize the queue manager."""
        self.queue = RequestQueue()
        self.interceptor = None
        self.worker_tasks: List[asyncio.Task] = []
        self.running = False

    async def start(self, num_workers: int = 10) -> None:
        """Start the queue manager workers.

        Args:
            num_workers: The number of worker tasks to start.
        """
        if self.running:
            return

        self.running = True

        # Create the interceptor
        from src.proxy.interceptor import HTTPInterceptor
        self.interceptor = HTTPInterceptor()

        # Start worker tasks
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(task)

        logger.info(f"Started {num_workers} queue manager workers")

    async def stop(self) -> None:
        """Stop the queue manager workers."""
        self.running = False

        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()

        # Wait for all tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        # Close the interceptor if it exists
        if self.interceptor is not None:
            await self.interceptor.close()

        logger.info("Stopped queue manager workers")

    async def enqueue_request(
        self, request: Request, priority: Priority = Priority.NORMAL
    ) -> Tuple[bool, Optional[str]]:
        """Enqueue a request for processing.

        Args:
            request: The FastAPI request.
            priority: The priority level of the request.

        Returns:
            A tuple of (success, error_message).
        """
        # Check if queue is full
        if (
            self.queue.high_priority.full()
            and self.queue.normal_priority.full()
            and self.queue.low_priority.full()
        ):
            return False, "All request queues are full"

        # Enqueue the request
        success = await self.queue.enqueue(request, priority)

        if success:
            return True, None
        else:
            return False, f"Failed to enqueue request with priority {priority.name}"

    async def _worker(self, worker_id: int) -> None:
        """Worker task for processing queued requests.

        Args:
            worker_id: The ID of the worker task.
        """
        logger.info(f"Worker {worker_id} started")

        try:
            while self.running:
                # Check if we can process more requests
                can_process = await self.queue.increment_active_requests()

                if not can_process:
                    # Wait and try again
                    await asyncio.sleep(0.1)
                    continue

                try:
                    # Dequeue a request
                    request = await self.queue.dequeue()

                    if request is None:
                        # No requests in queue, wait and try again
                        await asyncio.sleep(0.1)
                        await self.queue.decrement_active_requests()
                        continue

                    # Process the request
                    await self.interceptor.intercept(request)
                finally:
                    # Decrement active requests counter
                    await self.queue.decrement_active_requests()
        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.exception(f"Error in worker {worker_id}: {e}")
        finally:
            logger.info(f"Worker {worker_id} stopped")
