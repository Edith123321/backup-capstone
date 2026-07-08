// src/SignalQuality.h
//
// On-device Signal Quality Assessment for the SAKA stethoscope.
//
// This is the firmware counterpart of backend/api/v1/screening/signal_quality.py.
// It runs cheap, streaming checks directly on the ESP32 while audio is captured,
// so a garbage / silent / clipped / too-short recording is flagged AT THE SOURCE
// — before it is streamed over BLE/WebSocket and before the backend gate sees it.
//
// It intentionally implements a lighter subset than the backend (no FFT): it
// covers loudness (faint), clipping/jitter, silence, minimum duration, and a
// beat-activity proxy (a cheap Lub-Dub presence test). The backend remains the
// authoritative gate; this just gives the nurse instant feedback and saves
// bandwidth. Thresholds live in Config.h.
#ifndef SIGNAL_QUALITY_H
#define SIGNAL_QUALITY_H

#include <Arduino.h>
#include "Config.h"

class SignalQuality {
public:
    SignalQuality();

    // Call when a recording starts to clear all running state.
    void reset();

    // Feed one captured audio chunk (int16 PCM). Updates running statistics
    // and the beat detector. `sampleRate` is samples/second (SAMPLE_RATE).
    void feed(const int16_t* buffer, int n, int sampleRate);

    // Overall gradeability score 0-100 based on the data seen so far.
    int qualityScore() const;

    // True if the recording currently fails a HARD gate (faint / no heartbeat /
    // too short) and should not be trusted for diagnosis.
    bool isBlocked() const;

    // Machine code of the primary issue: "ok" | "too_faint" | "clipping" |
    // "no_heartbeat" | "too_short".
    const char* primaryCode() const;

    // Estimated heart rate (BPM) from the beat detector, 0 if unknown.
    int estimatedBpm() const;

    // Serialise a report as JSON for the WebSocket clients. `final` marks the
    // end-of-recording summary (enforces the min-duration gate).
    String toJson(bool final = false) const;

private:
    // Running loudness / clipping stats.
    double  _sumSq;
    uint32_t _totalSamples;
    uint32_t _clipCount;
    float   _maxAbs;
    int     _sampleRate;

    // Beat detector (sub-frame energy threshold-crossing).
    double  _subSumSq;      // accumulator for the current sub-frame
    int     _subCount;      // samples accumulated in the current sub-frame
    int     _subLen;        // sub-frame length in samples
    float   _baseline;      // EMA baseline of sub-frame RMS
    int     _refractory;    // sub-frames remaining before another beat may fire
    int     _refractorySub; // refractory length in sub-frames
    uint32_t _beatCount;

    float _rmsLinear() const;      // overall RMS across the whole recording
    float _clipRatio() const;      // fraction of clipped samples
    float _durationS() const;      // elapsed seconds
    void  _processSubframe(float rms);
};

#endif // SIGNAL_QUALITY_H
