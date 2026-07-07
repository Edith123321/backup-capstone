# tests/functional/test_health.py
import pytest
import requests

class TestHealthEndpoints:
    
    def test_health_check(self, base_url):
        """Test health check endpoint"""
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'
    
    def test_root_endpoint(self, base_url):
        """Test root endpoint returns routes"""
        response = requests.get(f"{base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert 'routes' in data
        assert 'login' in data['routes']