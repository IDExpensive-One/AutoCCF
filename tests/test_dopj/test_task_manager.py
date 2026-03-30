"""
DoPJ Task Manager Tests

Tests for TaskManager and TaskStatus from DoPJ/cli.py
"""
import json
import pytest
from pathlib import Path
from DoPJ.cli import TaskManager, TaskStatus, Task


class TestTaskStatus:
    """Test TaskStatus constants"""

    def test_status_values(self):
        """Test all task status values"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.SKIPPED == "skipped"


class TestTask:
    """Test Task class"""

    def test_task_creation(self):
        """Test creating a Task"""
        task = Task(
            index=1,
            tid=123456,
            title="Test Title",
            output_dir="output",
            href="https://tieba.baidu.com/p/123456",
            pid=None,
        )
        
        assert task.index == 1
        assert task.tid == 123456
        assert task.title == "Test Title"
        assert task.output_dir == "output"
        assert task.href == "https://tieba.baidu.com/p/123456"
        assert task.pid is None
        assert task.status == TaskStatus.PENDING
        assert task.error_msg == ""
        assert task.retry_count == 0

    def test_task_with_pid(self):
        """Test creating a Task with pid"""
        task = Task(
            index=2,
            tid=999,
            title="Reply Post",
            output_dir="out",
            pid=888,
        )
        assert task.pid == 888


class TestTaskManager:
    """Test TaskManager class"""

    def test_init_empty(self):
        """Test creating an empty TaskManager"""
        tm = TaskManager()
        assert tm.tasks == []
        assert tm.max_retries == 3

    def test_init_with_custom_settings(self, tmp_path):
        """Test creating TaskManager with custom settings"""
        progress_file = str(tmp_path / "custom_progress.json")
        tm = TaskManager(progress_file=progress_file, max_retries=5)
        assert tm.progress_file == progress_file
        assert tm.max_retries == 5

    def test_get_stats_empty(self):
        """Test get_stats on empty TaskManager"""
        tm = TaskManager()
        stats = tm.get_stats()
        assert stats == {
            "total": 0,
            "success": 0,
            "failed": 0,
            "pending": 0,
            "skipped": 0,
        }

    def test_get_stats_with_tasks(self):
        """Test get_stats with tasks in various states"""
        tm = TaskManager()
        
        # Add tasks manually
        task1 = Task(1, 100, "Task 1", "out")
        task1.status = TaskStatus.SUCCESS
        
        task2 = Task(2, 200, "Task 2", "out")
        task2.status = TaskStatus.FAILED
        
        task3 = Task(3, 300, "Task 3", "out")
        task3.status = TaskStatus.PENDING
        
        task4 = Task(4, 400, "Task 4", "out")
        task4.status = TaskStatus.SKIPPED
        
        tm.tasks = [task1, task2, task3, task4]
        
        stats = tm.get_stats()
        assert stats["total"] == 4
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1
        assert stats["skipped"] == 1

    def test_load_from_json(self, tmp_path):
        """Test loading tasks from JSON file"""
        json_file = tmp_path / "posts.json"
        json_data = {
            "posts": [
                {"tid": 111, "title": "First Post", "href": "/p/111"},
                {"tid": 222, "title": "Second Post", "href": "/p/222"},
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")
        
        tm = TaskManager()
        tm.load_from_json(str(json_file), "output")
        
        assert len(tm.tasks) == 2
        assert tm.tasks[0].tid == 111
        assert tm.tasks[0].title == "First Post"
        assert tm.tasks[1].tid == 222

    def test_load_from_json_with_href_extraction(self, tmp_path):
        """Test extracting tid from href when tid not present"""
        json_file = tmp_path / "posts.json"
        json_data = {
            "posts": [
                {"title": "Post A", "href": "/p/333?pid=444"},
                {"title": "Post B", "href": "https://tieba.baidu.com/p/555"},
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")
        
        tm = TaskManager()
        tm.load_from_json(str(json_file), "output")
        
        assert len(tm.tasks) == 2
        assert tm.tasks[0].tid == 333
        assert tm.tasks[1].tid == 555

    def test_load_from_json_with_max_tasks_limit(self, tmp_path):
        """Test loading only first N unique tasks for faster subset crawl."""
        json_file = tmp_path / "posts.json"
        json_data = {
            "posts": [
                {"tid": 1001, "title": "Post 1", "href": "/p/1001"},
                {"tid": 1002, "title": "Post 2", "href": "/p/1002"},
                {"tid": 1003, "title": "Post 3", "href": "/p/1003"},
                {"tid": 1004, "title": "Post 4", "href": "/p/1004"},
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        tm = TaskManager()
        tm.load_from_json(str(json_file), "output", max_tasks=2)

        assert len(tm.tasks) == 2
        assert [task.tid for task in tm.tasks] == [1001, 1002]

    def test_load_from_json_max_tasks_applies_after_deduplicate(self, tmp_path):
        """Test max_tasks counts unique tids instead of raw records."""
        json_file = tmp_path / "posts.json"
        json_data = {
            "posts": [
                {"tid": 2001, "title": "Post 1", "href": "/p/2001"},
                {"tid": 2001, "title": "Post 1 dup", "href": "/p/2001"},
                {"tid": 2002, "title": "Post 2", "href": "/p/2002"},
                {"tid": 2003, "title": "Post 3", "href": "/p/2003"},
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        tm = TaskManager()
        tm.load_from_json(str(json_file), "output", max_tasks=2)

        assert len(tm.tasks) == 2
        assert [task.tid for task in tm.tasks] == [2001, 2002]

    def test_get_next_task(self):
        """Test getting next pending task"""
        tm = TaskManager()
        tm.tasks = [
            Task(1, 100, "Task 1", "out"),
            Task(2, 200, "Task 2", "out"),
        ]
        
        task1 = tm.get_next_task()
        assert task1 is not None
        assert task1.tid == 100
        
        task2 = tm.get_next_task()
        assert task2 is not None
        assert task2.tid == 200
        
        task3 = tm.get_next_task()
        assert task3 is None

    def test_mark_success(self, tmp_path):
        """Test marking a task as successful"""
        progress_file = str(tmp_path / "progress.json")
        tm = TaskManager(progress_file=progress_file)
        
        task = Task(1, 100, "Task 1", "out")
        tm.tasks = [task]
        
        tm.mark_success(task)
        
        assert task.status == TaskStatus.SUCCESS
        # Check progress file was created
        assert Path(progress_file).exists()

    def test_mark_failed(self, tmp_path):
        """Test marking a task as failed"""
        progress_file = str(tmp_path / "progress.json")
        tm = TaskManager(progress_file=progress_file)
        
        task = Task(1, 100, "Task 1", "out")
        tm.tasks = [task]
        
        tm.mark_failed(task, "Network error")
        
        assert task.status == TaskStatus.FAILED
        assert task.error_msg == "Network error"

    def test_retry_failed_task(self):
        """Test that failed tasks get retried"""
        tm = TaskManager(max_retries=3)
        
        task = Task(1, 100, "Task 1", "out")
        task.status = TaskStatus.FAILED
        task.retry_count = 1
        tm.tasks = [task]
        
        # Reset index for retry
        tm._current_index = 0
        
        next_task = tm.get_next_task()
        assert next_task is not None
        assert next_task.tid == 100
        assert next_task.retry_count == 2

    def test_no_retry_when_max_exceeded(self):
        """Test that tasks aren't retried when max_retries exceeded"""
        tm = TaskManager(max_retries=2)
        
        task = Task(1, 100, "Task 1", "out")
        task.status = TaskStatus.FAILED
        task.retry_count = 2  # Already at max
        tm.tasks = [task]
        
        next_task = tm.get_next_task()
        assert next_task is None

    def test_save_and_load_progress(self, tmp_path):
        """Test saving and loading progress"""
        progress_file = str(tmp_path / "progress.json")
        
        # Create manager with tasks
        tm1 = TaskManager(progress_file=progress_file)
        task = Task(1, 100, "Task 1", "out")
        task.status = TaskStatus.SUCCESS
        tm1.tasks = [task]
        tm1.save_progress()
        
        # Load in new manager
        tm2 = TaskManager(progress_file=progress_file)
        tm2.tasks = [Task(1, 100, "Task 1", "out")]
        loaded = tm2.load_progress()
        
        assert loaded is True
        assert tm2.tasks[0].status == TaskStatus.SUCCESS

    def test_load_progress_file_not_exists(self, tmp_path):
        """Test loading progress when file doesn't exist"""
        progress_file = str(tmp_path / "nonexistent.json")
        tm = TaskManager(progress_file=progress_file)
        
        loaded = tm.load_progress()
        assert loaded is False

    def test_load_from_json_deduplicates_tids(self, tmp_path):
        """Test that duplicate tids are removed to prevent SQLite locking issues"""
        json_file = tmp_path / "posts.json"
        json_data = {
            "posts": [
                {"tid": 111, "title": "First Post", "href": "/p/111"},
                {"tid": 222, "title": "Second Post", "href": "/p/222"},
                {"tid": 111, "title": "Duplicate of First", "href": "/p/111"},  # Duplicate!
                {"tid": 333, "title": "Third Post", "href": "/p/333"},
                {"tid": 222, "title": "Duplicate of Second", "href": "/p/222"},  # Duplicate!
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")
        
        tm = TaskManager()
        tm.load_from_json(str(json_file), "output")
        
        # Should only have 3 unique tids
        assert len(tm.tasks) == 3
        
        # Verify tids are unique
        tids = [t.tid for t in tm.tasks]
        assert tids == [111, 222, 333]
        
        # Verify indexes are sequential
        indexes = [t.index for t in tm.tasks]
        assert indexes == [1, 2, 3]
        
        # Verify first occurrence is kept
        assert tm.tasks[0].title == "First Post"
        assert tm.tasks[1].title == "Second Post"
        assert tm.tasks[2].title == "Third Post"
