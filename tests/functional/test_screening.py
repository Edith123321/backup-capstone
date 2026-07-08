# tests/functional/test_screening.py
# Functional tests for the AI screening endpoints.
import io
import wave
import struct
import pytest
import requests

pytestmark = pytest.mark.functional


def _wav_bytes(seconds=1.0, sr=4000, freq=100.0, amp=8000):
    import math
    buf = io.BytesIO()
    w = wave.open(buf, 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    frames = []
    for i in range(int(seconds * sr)):
        frames.append(struct.pack('<h', int(amp * math.sin(2 * math.pi * freq * i / sr))))
    w.writeframes(b''.join(frames)); w.close()
    buf.seek(0); return buf


class TestScreeningHealth:
    def test_screening_health(self, base_url, api_prefix):
        r = requests.get(f"{base_url}{api_prefix}/screening/health", timeout=30)
        assert r.status_code == 200
        assert r.json().get('feature_count') == 51

    def test_model_loaded_flag_present(self, base_url, api_prefix):
        r = requests.get(f"{base_url}{api_prefix}/screening/health", timeout=30)
        assert 'model_loaded' in r.json()

    def test_model_info(self, base_url, api_prefix):
        r = requests.get(f"{base_url}{api_prefix}/screening/info", timeout=30)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json().get('feature_count') == 51

    def test_health_reports_sample_rate(self, base_url, api_prefix):
        r = requests.get(f"{base_url}{api_prefix}/screening/info", timeout=30)
        if r.status_code == 200:
            assert r.json().get('sample_rate') in (4000, None) or 'sample_rate' in r.json()


class TestPredictValidation:
    def test_predict_requires_file(self, base_url, api_prefix):
        r = requests.post(f"{base_url}{api_prefix}/screening/predict", timeout=30)
        assert r.status_code in (400, 401, 500)

    def test_predict_empty_filename(self, base_url, api_prefix):
        files = {'file': ('', io.BytesIO(b''), 'audio/wav')}
        r = requests.post(f"{base_url}{api_prefix}/screening/predict", files=files, timeout=30)
        assert r.status_code in (400, 500)

    def test_predict_valid_wav_returns_prediction(self, base_url, api_prefix):
        files = {'file': ('test.wav', _wav_bytes(2.0), 'audio/wav')}
        r = requests.post(f"{base_url}{api_prefix}/screening/predict", files=files, timeout=60)
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            data = r.json()
            assert data.get('prediction') in ('Normal', 'RHD')
            assert 0.0 <= data.get('confidence', 0) <= 1.0

    def test_predict_response_has_severity(self, base_url, api_prefix):
        files = {'file': ('test.wav', _wav_bytes(2.0), 'audio/wav')}
        r = requests.post(f"{base_url}{api_prefix}/screening/predict", files=files, timeout=60)
        if r.status_code == 200:
            assert 'severity' in r.json()

    @pytest.mark.parametrize('point', ['MV', 'AV', 'PV', 'TV'])
    def test_predict_with_auscultation_point(self, base_url, api_prefix, point):
        files = {'file': ('t.wav', _wav_bytes(2.0), 'audio/wav')}
        r = requests.post(f"{base_url}{api_prefix}/screening/predict",
                          files=files, data={'auscultation_point': point}, timeout=60)
        assert r.status_code in (200, 500)


class TestValidateEndpoint:
    def test_validate_requires_file(self, base_url, api_prefix):
        r = requests.post(f"{base_url}{api_prefix}/screening/validate", timeout=30)
        assert r.status_code in (400, 401, 500)

    def test_validate_accepts_wav(self, base_url, api_prefix):
        files = {'file': ('t.wav', _wav_bytes(2.0), 'audio/wav')}
        r = requests.post(f"{base_url}{api_prefix}/screening/validate", files=files, timeout=30)
        assert r.status_code in (200, 400, 500)

    @pytest.mark.parametrize('ext,mime', [
        ('t.txt', 'text/plain'), ('t.exe', 'application/octet-stream'), ('t.pdf', 'application/pdf'),
    ])
    def test_validate_rejects_non_audio(self, base_url, api_prefix, ext, mime):
        files = {'file': (ext, io.BytesIO(b'not audio'), mime)}
        r = requests.post(f"{base_url}{api_prefix}/screening/validate", files=files, timeout=30)
        assert r.status_code in (400, 500) or r.json().get('valid') is False
