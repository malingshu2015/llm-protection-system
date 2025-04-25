"""Tests for the health API module."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.health_api import (
    router,
    ServiceStatus,
    HealthStatus,
    check_ollama_status,
    get_health_status,
)


@pytest.fixture
def app():
    """Create a FastAPI app with the API router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_get_health_status(client):
    """Test getting health status."""
    response = client.get("/api/v1/health/status")
    assert response.status_code == 200

    # Verify response structure
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "timestamp" in data

    # Verify status
    assert data["status"] == "normal"

    # Verify services
    services = data["services"]
    assert len(services) == 4

    # Verify service structure
    for service in services:
        assert "name" in service
        assert "status" in service
        assert "response_time" in service
        assert "last_check" in service
        assert "details" in service


def test_get_health_status_direct():
    """Test getting health status directly."""
    # Call the function directly
    import asyncio
    response = asyncio.run(get_health_status())

    # Verify response structure
    assert "status" in response
    assert "services" in response
    assert "timestamp" in response

    # Verify status
    assert response["status"] == "normal"

    # Verify services
    services = response["services"]
    assert len(services) == 4

    # Verify service structure
    for service in services:
        assert "name" in service
        assert "status" in service
        assert "response_time" in service
        assert "last_check" in service
        assert "details" in service


def test_check_ollama_status_normal():
    """Test checking Ollama status with normal status."""
    # Mock random.choice to always return "normal"
    with patch("random.choice", return_value="normal"):
        # Mock random.uniform to return a fixed value
        with patch("random.uniform", return_value=50.0):
            # Call the function
            status = check_ollama_status()

            # Verify status
            assert status.name == "Ollama 集成"
            assert status.status == "normal"
            assert status.response_time == 50.0
            assert isinstance(status.last_check, datetime)
            assert status.details == "Ollama 服务运行正常"


def test_check_ollama_status_warning():
    """Test checking Ollama status with warning status."""
    # Mock random.choice to always return "warning"
    with patch("random.choice", return_value="warning"):
        # Mock random.uniform to return a fixed value
        with patch("random.uniform", return_value=150.0):
            # Call the function
            status = check_ollama_status()

            # Verify status
            assert status.name == "Ollama 集成"
            assert status.status == "warning"
            assert status.response_time == 150.0
            assert isinstance(status.last_check, datetime)
            assert status.details == "Ollama 服务响应较慢"


def test_check_ollama_status_error():
    """Test checking Ollama status with error status."""
    # Mock random.choice to always return "error"
    with patch("random.choice", return_value="error"):
        # Mock random.uniform to return a fixed value
        with patch("random.uniform", return_value=300.0):
            # Call the function
            status = check_ollama_status()

            # Verify status
            assert status.name == "Ollama 集成"
            assert status.status == "error"
            assert status.response_time == 300.0
            assert isinstance(status.last_check, datetime)
            assert status.details == "Ollama 服务连接异常"


def test_check_ollama_status_exception():
    """Test checking Ollama status with exception."""
    # Mock random.choice to raise an exception
    with patch("random.choice", side_effect=Exception("Test exception")):
        # Call the function
        status = check_ollama_status()

        # Verify status
        assert status.name == "Ollama 集成"
        assert status.status == "error"
        assert status.response_time == 0
        assert isinstance(status.last_check, datetime)
        assert "检查 Ollama 状态失败" in status.details
        assert "Test exception" in status.details


def test_service_status_model():
    """Test the ServiceStatus model."""
    # Create a ServiceStatus instance
    status = ServiceStatus(
        name="Test Service",
        status="normal",
        response_time=50.0,
        last_check=datetime.now(),
        details="Test service is running normally"
    )

    # Verify attributes
    assert status.name == "Test Service"
    assert status.status == "normal"
    assert status.response_time == 50.0
    assert isinstance(status.last_check, datetime)
    assert status.details == "Test service is running normally"

    # Test JSON serialization
    json_data = status.model_dump_json()
    data = json.loads(json_data)
    assert data["name"] == "Test Service"
    assert data["status"] == "normal"
    assert data["response_time"] == 50.0
    assert "last_check" in data
    assert data["details"] == "Test service is running normally"


def test_health_status_model():
    """Test the HealthStatus model."""
    # Create a ServiceStatus instance
    service = ServiceStatus(
        name="Test Service",
        status="normal",
        response_time=50.0,
        last_check=datetime.now(),
        details="Test service is running normally"
    )

    # Create a HealthStatus instance
    health = HealthStatus(
        status="normal",
        services=[service],
        timestamp=datetime.now()
    )

    # Verify attributes
    assert health.status == "normal"
    assert len(health.services) == 1
    assert health.services[0].name == "Test Service"
    assert isinstance(health.timestamp, datetime)

    # Test JSON serialization
    json_data = health.model_dump_json()
    data = json.loads(json_data)
    assert data["status"] == "normal"
    assert len(data["services"]) == 1
    assert data["services"][0]["name"] == "Test Service"
    assert "timestamp" in data
