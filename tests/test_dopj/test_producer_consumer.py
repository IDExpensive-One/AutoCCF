"""DoPJ producer-consumer tests."""
import asyncio

from DoPJ.producer_consumer import (
    ProducerConsumerCoordinator,
    ProducerConsumerConfig,
)


class TestProducerConsumerCoordinator:
    """Test producer-consumer coordination behavior."""

    def test_run_processes_all_pages(self):
        """Test coordinator fetches and processes all pages."""
        fetched: list[int] = []
        processed: list[int] = []

        async def fetch_page(page_number: int):
            fetched.append(page_number)
            await asyncio.sleep(0)
            return {"page": page_number}

        async def process_page(page_number: int, page_data):
            assert page_data["page"] == page_number
            processed.append(page_number)
            await asyncio.sleep(0)

        coordinator = ProducerConsumerCoordinator(
            ProducerConsumerConfig(producer_count=2, consumer_count=1, queue_size=8)
        )
        result = asyncio.run(
            coordinator.run(range(2, 7), fetch_page=fetch_page, process_page=process_page)
        )

        assert sorted(fetched) == [2, 3, 4, 5, 6]
        assert sorted(processed) == [2, 3, 4, 5, 6]
        assert result.fetched_pages == [2, 3, 4, 5, 6]
        assert result.processed_pages == [2, 3, 4, 5, 6]
        assert result.errors == []

    def test_run_collects_fetch_errors_and_continues(self):
        """Test coordinator records producer errors and continues processing."""
        processed: list[int] = []

        async def fetch_page(page_number: int):
            if page_number == 3:
                raise RuntimeError("boom")
            return {"page": page_number}

        async def process_page(page_number: int, page_data):
            processed.append(page_data["page"])

        coordinator = ProducerConsumerCoordinator(
            ProducerConsumerConfig(producer_count=2, consumer_count=1, queue_size=8)
        )
        result = asyncio.run(
            coordinator.run(range(2, 5), fetch_page=fetch_page, process_page=process_page)
        )

        assert sorted(processed) == [2, 4]
        assert result.processed_pages == [2, 4]
        assert len(result.errors) == 1
        assert "producer page=3" in result.errors[0]
