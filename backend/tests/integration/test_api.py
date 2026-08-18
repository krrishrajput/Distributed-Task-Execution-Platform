import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """GET /health returns 200"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_liveness(async_client: AsyncClient):
    """GET /live returns 200"""
    response = await async_client.get("/live")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_readiness(async_client: AsyncClient):
    """GET /ready returns 200 when Redis is connected"""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    assert response.json()["redis"] == "ok"

@pytest.mark.asyncio
async def test_create_task(async_client: AsyncClient):
    """POST /api/v1/tasks, verify 201 and response body"""
    payload = {
        "task_type": "test_api",
        "payload": {"key": "value"}
    }
    response = await async_client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ("QUEUED", "PENDING")

@pytest.mark.asyncio
async def test_get_task(async_client: AsyncClient):
    """create then GET /api/v1/tasks/{id}"""
    # Create
    payload = {"task_type": "test_api", "payload": {}}
    create_resp = await async_client.post("/api/v1/tasks", json=payload)
    task_id = create_resp.json()["task_id"]
    
    # Get
    get_resp = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == task_id
    assert data["task_type"] == "test_api"

@pytest.mark.asyncio
async def test_list_tasks(async_client: AsyncClient):
    """create multiple, GET /api/v1/tasks, verify list"""
    for _ in range(3):
        await async_client.post("/api/v1/tasks", json={"task_type": "test_list", "payload": {}})
        
    resp = await async_client.get("/api/v1/tasks?task_type=test_list")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 3

@pytest.mark.asyncio
async def test_create_task_invalid_type(async_client: AsyncClient):
    """invalid task_type returns 422 or 400"""
    payload = {
        # missing task_type
        "payload": {}
    }
    response = await async_client.post("/api/v1/tasks", json=payload)
    assert response.status_code in (422, 400)

@pytest.mark.asyncio
async def test_create_task_invalid_priority(async_client: AsyncClient):
    """priority out of range returns 422"""
    payload = {
        "task_type": "test",
        "payload": {},
        "priority": 100
    }
    response = await async_client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_idempotency(async_client: AsyncClient):
    """POST same idempotency_key twice, second returns 200 with same task_id"""
    ikey = str(uuid4())
    payload = {
        "task_type": "test",
        "payload": {},
        "idempotency_key": ikey
    }
    
    r1 = await async_client.post("/api/v1/tasks", json=payload)
    assert r1.status_code == 201
    task_id = r1.json()["task_id"]
    
    r2 = await async_client.post("/api/v1/tasks", json=payload)
    assert r2.status_code == 200  # API usually returns 200 for idempotent match
    assert r2.json()["task_id"] == task_id

@pytest.mark.asyncio
async def test_cancel_task(async_client: AsyncClient):
    """create task, POST cancel, verify CANCELLED"""
    payload = {"task_type": "test_cancel", "payload": {}}
    create_resp = await async_client.post("/api/v1/tasks", json=payload)
    task_id = create_resp.json()["task_id"]
    
    cancel_resp = await async_client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    
    get_resp = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.json()["status"] == "CANCELLED"
