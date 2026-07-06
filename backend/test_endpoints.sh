#!/bin/bash

echo "========================================="
echo "Testing Heart Sound API Endpoints"
echo "========================================="

BASE_URL="https://capstone-be-yxzd.onrender.com"

# 1. Test Predict with JSON
echo -e "\n📝 1. Testing Predict with JSON..."
curl -X POST "$BASE_URL/api/v1/screening/predict" \
  -H "Content-Type: application/json" \
  -d '{"heart_rate": 72, "symptoms": ["chest pain"], "doctor_id": "117085732829392364427"}'
echo -e "\n"

# 2. Test Validate with JSON
echo -e "\n📝 2. Testing Validate with JSON..."
curl -X POST "$BASE_URL/api/v1/screening/validate" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "test_001", "doctor_id": "117085732829392364427"}'
echo -e "\n"

# 3. Test Predict with File Upload (if test.wav exists)
echo -e "\n📝 3. Testing Predict with File Upload..."
if [ -f "test.wav" ]; then
    curl -X POST "$BASE_URL/api/v1/screening/predict" \
      -F "file=@test.wav" \
      -F "doctor_id=117085732829392364427" \
      -F "patient_id=test_001"
else
    echo "⚠️  test.wav file not found. Creating one..."
    
    # Create a test WAV file using Python
    python3 << EOF
import wave
import numpy as np

sample_rate = 44100
duration = 0.5
freq = 440

samples = (np.sin(2 * np.pi * freq * np.arange(sample_rate * duration) / sample_rate) * 32767).astype(np.int16)

with wave.open('test.wav', 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(samples.tobytes())
print('✅ test.wav created successfully')
EOF
    
    # Now upload it
    curl -X POST "$BASE_URL/api/v1/screening/predict" \
      -F "file=@test.wav" \
      -F "doctor_id=117085732829392364427" \
      -F "patient_id=test_001"
fi
echo -e "\n"

# 4. Test Validate with File Upload
echo -e "\n📝 4. Testing Validate with File Upload..."
if [ -f "test.wav" ]; then
    curl -X POST "$BASE_URL/api/v1/screening/validate" \
      -F "file=@test.wav" \
      -F "doctor_id=117085732829392364427"
else
    echo "⚠️  test.wav file not found"
fi
echo -e "\n"

# 5. Test Health Check
echo -e "\n📝 5. Testing Health Check..."
curl -X GET "$BASE_URL/api/v1/screening/health"
echo -e "\n"

# 6. Test CORS
echo -e "\n📝 6. Testing CORS Headers..."
curl -X OPTIONS "$BASE_URL/api/v1/screening/predict" \
  -H "Origin: https://backup-capstone-mbq6.onrender.com" \
  -H "Access-Control-Request-Method: POST" \
  -i | grep -i "access-control"
echo -e "\n"

echo "========================================="
echo "✅ Testing Complete"
echo "========================================="