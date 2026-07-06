#!/bin/zsh

echo "========================================="
echo "Testing All Endpoints After Fix"
echo "========================================="

BASE_URL="https://capstone-be-yxzd.onrender.com"

# 1. Test Predict with JSON (should work now)
echo -e "\n1. Testing Predict with JSON..."
curl -X POST "$BASE_URL/api/v1/screening/predict" \
  -H "Content-Type: application/json" \
  -d '{"heart_rate": 72, "symptoms": ["chest pain"], "doctor_id": "117085732829392364427"}'
echo -e "\n"

# 2. Test Predict with File
echo -e "\n2. Testing Predict with File Upload..."
if [ -f "test.wav" ]; then
    curl -X POST "$BASE_URL/api/v1/screening/predict" \
      -F "file=@test.wav" \
      -F "doctor_id=117085732829392364427"
else
    echo "test.wav not found"
fi
echo -e "\n"

# 3. Test Validate with JSON
echo -e "\n3. Testing Validate with JSON..."
curl -X POST "$BASE_URL/api/v1/screening/validate" \
  -H "Content-Type: application/json" \
  -d '{"doctor_id": "117085732829392364427", "patient_id": "test_001"}'
echo -e "\n"

# 4. Test Validate with File
echo -e "\n4. Testing Validate with File Upload..."
if [ -f "test.wav" ]; then
    curl -X POST "$BASE_URL/api/v1/screening/validate" \
      -F "file=@test.wav" \
      -F "doctor_id=117085732829392364427"
else
    echo "test.wav not found"
fi
echo -e "\n"

# 5. Test Health
echo -e "\n5. Testing Health..."
curl -X GET "$BASE_URL/api/v1/screening/health"
echo -e "\n"

echo "========================================="
echo "Testing Complete"
echo "========================================="