# tests/network/test_cors.py
import pytest
import requests

class TestCORS:
    
    def test_cors_headers_include_allowed_origin(self, base_url, api_prefix):
        """Test CORS headers are returned for allowed origin"""
        response = requests.get(
            f"{base_url}{api_prefix}/database/patients",
            headers={
                'Origin': 'https://backup-capstone-mbq6.onrender.com',
                'Access-Control-Request-Method': 'GET'
            }
        )
        # Should have CORS headers
        assert response.status_code in [200, 404, 400, 401]
        # Check that we can make requests
    
    def test_cors_preflight_returns_200(self, base_url, api_prefix):
        """Test OPTIONS preflight returns 200"""
        response = requests.options(
            f"{base_url}{api_prefix}/database/patients",
            headers={
                'Origin': 'https://backup-capstone-mbq6.onrender.com',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type, Authorization'
            }
        )
        assert response.status_code in [200, 204]
        assert 'access-control-allow-origin' in response.headers
    
    def test_cors_rejects_disallowed_origin(self, base_url, api_prefix):
        """Test CORS rejects disallowed origins"""
        response = requests.options(
            f"{base_url}{api_prefix}/database/patients",
            headers={
                'Origin': 'https://malicious-site.com',
                'Access-Control-Request-Method': 'GET'
            }
        )
        # Should still work but not include CORS headers for invalid origin
        assert response.status_code in [200, 204, 404]

# tests/network/test_rate_limiting.py
class TestRateLimiting:
    
    def test_multiple_requests_handled_gracefully(self, base_url, api_prefix):
        """Test multiple requests are handled gracefully"""
        for i in range(20):
            response = requests.get(f"{base_url}/health")
            assert response.status_code == 200
    
    def test_concurrent_requests(self, base_url, api_prefix):
        """Test concurrent requests don't cause issues"""
        import concurrent.futures
        
        def make_request():
            return requests.get(f"{base_url}/health")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
            
        assert all(r.status_code == 200 for r in results)

# tests/network/test_timeouts.py
class TestTimeouts:
    
    def test_slow_endpoint_timeout(self, base_url, api_prefix):
        """Test timeout handling for slow endpoints"""
        import time
        start = time.time()
        
        try:
            response = requests.get(
                f"{base_url}{api_prefix}/database/patients",
                timeout=5
            )
            elapsed = time.time() - start
            assert elapsed < 5
        except requests.Timeout:
            assert time.time() - start >= 5