import pytest
from pydantic import ValidationError
from datetime import datetime
from app.models.task import Task, TaskStatus, TaskCreate, validate_transition

def test_task_status_values():
    """Verify all status enum values."""
    assert TaskStatus.QUEUED == "QUEUED"
    assert TaskStatus.RUNNING == "RUNNING"
    assert TaskStatus.COMPLETED == "COMPLETED"
    assert TaskStatus.FAILED == "FAILED"
    assert TaskStatus.CANCELLED == "CANCELLED"
    assert TaskStatus.DLQ == "DLQ"
    assert TaskStatus.PENDING == "PENDING"
    assert TaskStatus.RETRYING == "RETRYING"

def test_task_create_defaults():
    """Verify default priority=5, max_retries=3."""
    task = TaskCreate(task_type="test_type", payload={"data": 123})
    assert task.priority == 5
    assert task.max_retries == 3

def test_task_create_validation():
    """Priority must be 1-10, max_retries 0-20."""
    task = TaskCreate(
        task_type="test", 
        payload={}, 
        priority=1, 
        max_retries=0
    )
    assert task.priority == 1
    assert task.max_retries == 0

    task2 = TaskCreate(
        task_type="test", 
        payload={}, 
        priority=10, 
        max_retries=20
    )
    assert task2.priority == 10
    assert task2.max_retries == 20

def test_task_create_invalid_priority():
    """Priority 0, 11 should fail validation."""
    with pytest.raises(ValidationError):
        TaskCreate(task_type="test", payload={}, priority=0)
    with pytest.raises(ValidationError):
        TaskCreate(task_type="test", payload={}, priority=11)
    with pytest.raises(ValidationError):
        TaskCreate(task_type="test", payload={}, max_retries=-1)
    with pytest.raises(ValidationError):
        TaskCreate(task_type="test", payload={}, max_retries=21)

def test_valid_transitions():
    """Test each valid transition returns True."""
    # QUEUED -> RUNNING
    assert validate_transition(TaskStatus.QUEUED, TaskStatus.RUNNING) is True
    
    # RUNNING -> COMPLETED, FAILED, RETRYING
    assert validate_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED) is True
    assert validate_transition(TaskStatus.RUNNING, TaskStatus.FAILED) is True
    assert validate_transition(TaskStatus.RUNNING, TaskStatus.RETRYING) is True

    # PENDING -> QUEUED, CANCELLED
    assert validate_transition(TaskStatus.PENDING, TaskStatus.QUEUED) is True
    assert validate_transition(TaskStatus.PENDING, TaskStatus.CANCELLED) is True

    # RETRYING -> QUEUED, CANCELLED
    assert validate_transition(TaskStatus.RETRYING, TaskStatus.QUEUED) is True
    assert validate_transition(TaskStatus.RETRYING, TaskStatus.CANCELLED) is True

def test_invalid_transitions():
    """COMPLETED->RUNNING, CANCELLED->QUEUED, etc. return False."""
    # COMPLETED
    assert validate_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING) is False
    assert validate_transition(TaskStatus.COMPLETED, TaskStatus.QUEUED) is False
    
    # CANCELLED
    assert validate_transition(TaskStatus.CANCELLED, TaskStatus.QUEUED) is False
    
    # QUEUED -> COMPLETED
    assert validate_transition(TaskStatus.QUEUED, TaskStatus.COMPLETED) is False

def test_terminal_states():
    """COMPLETED, CANCELLED, DLQ have no valid outbound transitions except manual DLQ->QUEUED."""
    for status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
        for next_status in TaskStatus:
            if next_status == status:
                continue
            assert validate_transition(status, next_status) is False

    for next_status in TaskStatus:
        if next_status == TaskStatus.QUEUED:
            assert validate_transition(TaskStatus.DLQ, next_status) is True
        elif next_status != TaskStatus.DLQ:
            assert validate_transition(TaskStatus.DLQ, next_status) is False
