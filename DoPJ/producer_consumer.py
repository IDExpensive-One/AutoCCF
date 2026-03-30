"""
DoPJ 生产者-消费者并发协调器。

用于将分页拉取（producer）与页面处理（consumer）解耦。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable


@dataclass
class ProducerConsumerConfig:
    """协调器配置。"""

    producer_count: int = 3
    consumer_count: int = 1
    queue_size: int = 16


@dataclass
class ProducerConsumerResult:
    """协调器执行结果。"""

    fetched_pages: list[int] = field(default_factory=list)
    processed_pages: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ProducerConsumerCoordinator:
    """分页抓取与处理协调器。"""

    def __init__(self, config: ProducerConsumerConfig | None = None):
        self.config = config or ProducerConsumerConfig()

    async def run(
        self,
        page_numbers: Iterable[int],
        fetch_page: Callable[[int], Awaitable[Any]],
        process_page: Callable[[int, Any], Awaitable[None]],
    ) -> ProducerConsumerResult:
        """执行生产者-消费者流程。"""
        page_queue: asyncio.Queue[int | None] = asyncio.Queue(maxsize=self.config.queue_size)
        result_queue: asyncio.Queue[tuple[int, Any] | None] = asyncio.Queue(maxsize=self.config.queue_size)
        result = ProducerConsumerResult()

        for page_number in page_numbers:
            await page_queue.put(page_number)

        for _ in range(self.config.producer_count):
            await page_queue.put(None)

        async def producer() -> None:
            while True:
                page_number = await page_queue.get()
                try:
                    if page_number is None:
                        return

                    page_data = await fetch_page(page_number)
                    if page_data is not None:
                        result.fetched_pages.append(page_number)
                        await result_queue.put((page_number, page_data))
                except Exception as exc:
                    result.errors.append(f"producer page={page_number}: {exc}")
                finally:
                    page_queue.task_done()

        async def consumer() -> None:
            while True:
                item = await result_queue.get()
                try:
                    if item is None:
                        return

                    page_number, page_data = item
                    await process_page(page_number, page_data)
                    result.processed_pages.append(page_number)
                except Exception as exc:
                    result.errors.append(f"consumer page={item[0] if item else 'unknown'}: {exc}")
                finally:
                    result_queue.task_done()

        producer_tasks = [asyncio.create_task(producer()) for _ in range(self.config.producer_count)]
        consumer_tasks = [asyncio.create_task(consumer()) for _ in range(self.config.consumer_count)]

        await page_queue.join()
        await asyncio.gather(*producer_tasks)

        for _ in range(self.config.consumer_count):
            await result_queue.put(None)

        await result_queue.join()
        await asyncio.gather(*consumer_tasks)

        result.fetched_pages.sort()
        result.processed_pages.sort()
        return result


__all__ = [
    "ProducerConsumerConfig",
    "ProducerConsumerResult",
    "ProducerConsumerCoordinator",
]
