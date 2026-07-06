# test_endpoints.py
import requests
import json

BASE_URL = "https://capstone-be-yxzd.onrender.com"

def test_validation():
    url = f"{BASE_URL}/api/v1/screening/validate"
    data = {"test": "data"}
    
    try:
        response = requests.post(url, json=data)
        print(f"✅ Validation test: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_prediction():
    url = f"{BASE_URL}/api/v1/screening/predict"
    data = {"test": "data"}
    
    try:
        response = requests.post(url, json=data)
        print(f"✅ Prediction test: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Prediction test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing endpoints...")
    test_validation()
    test_prediction()