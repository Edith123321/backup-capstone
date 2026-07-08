// src/SignalQuality.cpp
#include "SignalQuality.h"
#include <math.h>

SignalQuality::SignalQuality() {
    reset();
}

void SignalQuality::reset() {
    _sumSq = 0.0;
    _totalSamples = 0;
    _clipCount = 0;
    _maxAbs = 0.0f;
    _sampleRate = SAMPLE_RATE;

    _subSumSq = 0.0;
    _subCount = 0;
    _subLen = (int)(SAMPLE_RATE * (SQA_SUBFRAME_MS / 1000.0f));
    if (_subLen < 1) _subLen = 1;
    _baseline = 0.0f;
    _refractory = 0;
    // Refractory in sub-frames (min gap between beats).
    _refractorySub = (int)(SQA_BEAT_REFRACT_MS / (float)SQA_SUBFRAME_MS);
    if (_refractorySub < 1) _refractorySub = 1;
    _beatCount = 0;
}

void SignalQuality::feed(const int16_t* buffer, int n, int sampleRate) {
    if (sampleRate > 0) _sampleRate = sampleRate;

    for (int i = 0; i < n; i++) {
        float s = (float)buffer[i] / 32768.0f;
        float a = fabsf(s);

        // Loudness / clipping stats.
        _sumSq += (double)s * s;
        _totalSamples++;
        if (a > _maxAbs) _maxAbs = a;
        if (a >= SQA_CLIP_LEVEL) _clipCount++;

        // Accumulate into the current sub-frame for beat detection.
        _subSumSq += (double)s * s;
        _subCount++;
        if (_subCount >= _subLen) {
            float subRms = sqrtf((float)(_subSumSq / _subCount));
            _processSubframe(subRms);
            _subSumSq = 0.0;
            _subCount = 0;
        }
    }
}

void SignalQuality::_processSubframe(float rms) {
    // Cheap Lub-Dub proxy: a beat is a sub-frame whose energy jumps well above a
    // slowly-adapting baseline, with a refractory gap so one S1/S2 burst counts
    // once. This is a presence/rate test, not a clinical segmentation.
    if (_baseline <= 0.0f) {
        _baseline = rms;         // seed on first sub-frame
    }

    bool aboveFaint = rms > SQA_FAINT_RMS;
    if (_refractory == 0 && aboveFaint && rms > _baseline * SQA_BEAT_FACTOR) {
        _beatCount++;
        _refractory = _refractorySub;
    } else if (_refractory > 0) {
        _refractory--;
    }

    // EMA baseline tracks the ambient level so the detector adapts to the room.
    _baseline = 0.95f * _baseline + 0.05f * rms;
}

float SignalQuality::_rmsLinear() const {
    if (_totalSamples == 0) return 0.0f;
    return sqrtf((float)(_sumSq / _totalSamples));
}

float SignalQuality::_clipRatio() const {
    if (_totalSamples == 0) return 0.0f;
    return (float)_clipCount / (float)_totalSamples;
}

float SignalQuality::_durationS() const {
    if (_sampleRate <= 0) return 0.0f;
    return (float)_totalSamples / (float)_sampleRate;
}

int SignalQuality::estimatedBpm() const {
    float dur = _durationS();
    if (dur < 1.0f || _beatCount == 0) return 0;
    return (int)roundf(_beatCount * 60.0f / dur);
}

bool SignalQuality::isBlocked() const {
    // Faint / silent -> cannot trust "no murmur".
    if (_rmsLinear() < SQA_FAINT_RMS) return true;
    // No plausible heartbeat activity once we have enough audio to judge.
    if (_durationS() >= 2.0f && _beatCount < (uint32_t)SQA_MIN_BEATS) return true;
    return false;
}

const char* SignalQuality::primaryCode() const {
    if (_rmsLinear() < SQA_FAINT_RMS) return "too_faint";
    if (_durationS() >= 2.0f && _beatCount < (uint32_t)SQA_MIN_BEATS) return "no_heartbeat";
    if (_clipRatio() > SQA_CLIP_RATIO_WARN) return "clipping";
    return "ok";
}

int SignalQuality::qualityScore() const {
    // Combine loudness headroom, cleanliness (low clipping) and beat presence.
    float rms = _rmsLinear();
    float loud = rms <= SQA_FAINT_RMS ? 0.0f
               : fminf(1.0f, (rms - SQA_FAINT_RMS) / (0.3f - SQA_FAINT_RMS));
    float clean = fmaxf(0.0f, 1.0f - _clipRatio() / SQA_CLIP_RATIO_WARN);
    if (clean > 1.0f) clean = 1.0f;
    float beats = fminf(1.0f, _beatCount / (float)(SQA_MIN_BEATS * 2));
    int score = (int)(100.0f * (0.4f * beats + 0.35f * loud + 0.25f * clean));
    if (score < 0) score = 0;
    if (score > 100) score = 100;
    return score;
}

String SignalQuality::toJson(bool final) const {
    // Duration gate only applies to the final summary (a live report early in a
    // recording is legitimately short).
    bool tooShort = final && _durationS() < SQA_MIN_DURATION_S;
    bool blocked = isBlocked() || tooShort;
    const char* code = tooShort ? "too_short" : primaryCode();

    // 20*log10 for dBFS; guard log(0).
    float rms = _rmsLinear();
    float dbfs = 20.0f * log10f(rms + 1e-9f);

    String out = "{";
    out += "\"type\":\"signal_quality\"";
    out += ",\"final\":" + String(final ? "true" : "false");
    out += ",\"quality\":" + String(qualityScore());
    out += ",\"blocked\":" + String(blocked ? "true" : "false");
    out += ",\"code\":\"" + String(code) + "\"";
    out += ",\"rms_dbfs\":" + String(dbfs, 1);
    out += ",\"clip_ratio\":" + String(_clipRatio(), 3);
    out += ",\"bpm\":" + String(estimatedBpm());
    out += ",\"duration_s\":" + String(_durationS(), 1);

    // Human-readable message so the UI can display it directly.
    const char* msg;
    if (tooShort)                         msg = "Recording too short - hold steady for the full 10s.";
    else if (strcmp(code, "too_faint")==0) msg = "Sound too faint - press the diaphragm more firmly on the skin.";
    else if (strcmp(code, "no_heartbeat")==0) msg = "No heartbeat detected - reposition over the heart.";
    else if (strcmp(code, "clipping")==0) msg = "Signal clipping/jitter - check placement and battery.";
    else                                  msg = "Good signal.";
    out += ",\"message\":\"" + String(msg) + "\"";
    out += "}";
    return out;
}
