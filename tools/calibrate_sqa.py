#!/usr/bin/env python3
"""
Calibrate the Signal Quality Assessment (SQA) thresholds against REAL recordings.

The thresholds in backend/api/v1/screening/signal_quality.py (and the mirrored
on-device ones in iot/src/Config.h) ship as conservative defaults validated on
synthetic audio. This tool re-derives them from real field recordings so the
gate is tuned to your actual microphone, patients and clinics.

It reuses the *real* SQA functions (no re-implementation), so what it measures is
exactly what the deployed gate measures.

--------------------------------------------------------------------------------
TWO MODES
--------------------------------------------------------------------------------
1. PROFILE (default, runnable today)
   Point it at a folder of KNOWN-GOOD recordings (e.g. the training clips, which
   are all genuine heartbeats). It profiles the distribution of each metric on
   clips that *should pass*, recommends thresholds as safe percentiles, and — the
   key output — reports how many of your good clips the CURRENT thresholds would
   wrongly BLOCK.

2. SEPARATE (when you collect bad-quality samples)
   Put recordings in subfolders whose names indicate quality, e.g.
       data/good/   data/faint/   data/noise/   data/garbage/   data/short/
   It then recommends thresholds that best SEPARATE good from bad, and reports
   the current confusion (good wrongly blocked / bad wrongly passed).

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------
    python tools/calibrate_sqa.py <data_dir> [--out report.json] [--limit N]

    # profile the existing training data (all real heartbeats)
    python tools/calibrate_sqa.py ai_model/data/test

Requires: numpy, scipy, soundfile (already backend deps).
"""

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

# Make the real SQA module importable.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQA_DIR = os.path.join(REPO, 'backend', 'api', 'v1', 'screening')
sys.path.insert(0, SQA_DIR)

import signal_quality as SQA  # noqa: E402  (the authoritative gate)


# Folder-name keywords -> semantic quality class.
GOOD_KEYS = ('good', 'normal', 'rhd', 'heart', 'clean', 'valid', 'pass')
FAINT_KEYS = ('faint', 'silent', 'silence', 'quiet', 'weak')
NOISE_KEYS = ('noise', 'noisy', 'ambient', 'chaos')
GARBAGE_KEYS = ('garbage', 'speech', 'music', 'talk', 'cry', 'junk')
SHORT_KEYS = ('short', 'fragment', 'clip')


def classify_folder(name: str) -> str:
    n = name.lower()
    for keys, label in ((FAINT_KEYS, 'faint'), (NOISE_KEYS, 'noise'),
                        (GARBAGE_KEYS, 'garbage'), (SHORT_KEYS, 'short'),
                        (GOOD_KEYS, 'good')):
        if any(k in n for k in keys):
            return label
    return 'good'  # default assumption: unlabeled == a real recording


def load_wav(path, sr=SQA.SR):
    """Load a WAV to mono float at the SQA sample rate (numba-free)."""
    import soundfile as sf
    from scipy.signal import resample
    y, native = sf.read(path)
    if getattr(y, 'ndim', 1) > 1:
        y = np.mean(y, axis=1)
    y = np.asarray(y, dtype=float)
    if native != sr and len(y) > 1:
        y = resample(y, int(sr * len(y) / native))
    return y, sr


def metrics_for(y, sr=SQA.SR):
    """Compute the raw SQA metrics for one clip (same math as the gate)."""
    duration = len(y) / float(sr)
    rms = float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0
    rms_dbfs = 20.0 * np.log10(rms + 1e-9)
    low_e = SQA._band_energy(y, SQA.LOW_FREQ_BAND[0], SQA.LOW_FREQ_BAND[1], sr) if len(y) > 16 else 0.0
    total_e = SQA._band_energy(y, SQA.LOW_FREQ_BAND[0], 1000.0, sr) if len(y) > 16 else 0.0
    high_e = SQA._band_energy(y, SQA.LOW_FREQ_BAND[1], 1000.0, sr) if len(y) > 16 else 0.0
    low_ratio = low_e / (total_e + 1e-9)
    noise_ratio = high_e / (total_e + 1e-9)
    env = SQA._envelope(y, sr) if len(y) > sr // 2 else np.zeros(1)
    rhythm, bpm = SQA._rhythm_strength_and_bpm(env, sr)
    return {
        'duration_s': duration, 'rms_dbfs': rms_dbfs, 'low_freq_ratio': low_ratio,
        'noise_ratio': noise_ratio, 'rhythm': rhythm, 'bpm': bpm,
    }


def pct(values, p):
    return float(np.percentile(values, p)) if values else float('nan')


def summarize(values):
    if not values:
        return {}
    return {
        'n': len(values), 'min': float(np.min(values)), 'p1': pct(values, 1),
        'p5': pct(values, 5), 'median': pct(values, 50), 'p95': pct(values, 95),
        'p99': pct(values, 99), 'max': float(np.max(values)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('data_dir', help='folder of recordings (optionally in quality-named subfolders)')
    ap.add_argument('--out', help='write the full JSON report here')
    ap.add_argument('--limit', type=int, default=0, help='cap files per class (0 = all)')
    args = ap.parse_args()

    # Gather wavs grouped by semantic class (from their immediate parent folder).
    by_class = defaultdict(list)
    for root, _dirs, files in os.walk(args.data_dir):
        cls = classify_folder(os.path.basename(root))
        for f in files:
            if f.lower().endswith(('.wav', '.flac', '.ogg', '.mp3')):
                by_class[cls].append(os.path.join(root, f))
    if not by_class:
        print(f'❌ No audio files found under {args.data_dir}')
        sys.exit(1)

    # Compute metrics + run the CURRENT gate on every file.
    per_class_metrics = defaultdict(lambda: defaultdict(list))
    current_block = defaultdict(lambda: {'blocked': 0, 'passed': 0, 'codes': defaultdict(int)})
    total = 0
    for cls, paths in by_class.items():
        if args.limit:
            paths = paths[:args.limit]
        for p in paths:
            try:
                y, sr = load_wav(p)
                if len(y) < 100:
                    continue
                m = metrics_for(y, sr)
                for k, v in m.items():
                    if np.isfinite(v):
                        per_class_metrics[cls][k].append(v)
                report = SQA.assess_signal_quality(y, sr)
                bucket = current_block[cls]
                if report.blocked:
                    bucket['blocked'] += 1
                    bucket['codes'][report.code] += 1
                else:
                    bucket['passed'] += 1
                total += 1
            except Exception as e:
                print(f'  ⚠️ skip {os.path.basename(p)}: {e}')

    classes = sorted(per_class_metrics.keys())
    has_bad = any(c in ('faint', 'noise', 'garbage', 'short') for c in classes)
    mode = 'SEPARATE' if has_bad else 'PROFILE'

    # ---- Recommend thresholds ------------------------------------------------
    good = per_class_metrics.get('good', {})
    rec = {}
    if good.get('rms_dbfs'):
        floor = pct(good['rms_dbfs'], 1) - 3  # 3 dB margin below the quietest good clips
        if 'faint' in per_class_metrics and per_class_metrics['faint'].get('rms_dbfs'):
            faint_top = pct(per_class_metrics['faint']['rms_dbfs'], 95)
            floor = (pct(good['rms_dbfs'], 1) + faint_top) / 2  # midpoint separation
        rec['TOO_FAINT_DBFS'] = round(floor, 1)
    if good.get('noise_ratio'):
        cut = pct(good['noise_ratio'], 95)
        if 'noise' in per_class_metrics and per_class_metrics['noise'].get('noise_ratio'):
            cut = (pct(good['noise_ratio'], 95) + pct(per_class_metrics['noise']['noise_ratio'], 50)) / 2
        rec['NOISE_RATIO_WARN'] = round(cut, 3)
    if good.get('rhythm'):
        r = pct(good['rhythm'], 5)
        if 'garbage' in per_class_metrics and per_class_metrics['garbage'].get('rhythm'):
            r = (pct(good['rhythm'], 5) + pct(per_class_metrics['garbage']['rhythm'], 95)) / 2
        rec['RHYTHM_STRENGTH_MIN'] = round(r, 3)
    if good.get('low_freq_ratio'):
        rec['LOW_FREQ_ENERGY_MIN'] = round(pct(good['low_freq_ratio'], 5), 3)
    if good.get('bpm'):
        bpms = [b for b in good['bpm'] if b > 0]
        if bpms:
            rec['HR_MIN_BPM'] = round(max(40, pct(bpms, 1)), 0)
            rec['HR_MAX_BPM'] = round(min(220, pct(bpms, 99)), 0)

    # ---- Print human-readable report ----------------------------------------
    print('\n' + '=' * 70)
    print(f'  SQA CALIBRATION REPORT   ({mode} mode, {total} clips)')
    print('=' * 70)

    for cls in classes:
        mm = per_class_metrics[cls]
        cb = current_block[cls]
        n = cb['blocked'] + cb['passed']
        print(f'\n▶ class "{cls}"  ({n} clips)')
        for key in ('duration_s', 'rms_dbfs', 'noise_ratio', 'rhythm', 'bpm', 'low_freq_ratio'):
            s = summarize(mm.get(key, []))
            if s:
                print(f'   {key:15} p5={s["p5"]:.3f}  median={s["median"]:.3f}  p95={s["p95"]:.3f}')
        # Current gate behaviour on this class.
        codes = ', '.join(f'{k}:{v}' for k, v in cb['codes'].items()) or '—'
        expected = 'PASS' if cls == 'good' else 'BLOCK'
        print(f'   current gate: {cb["passed"]} passed / {cb["blocked"]} blocked  '
              f'(expected: {expected}; block codes: {codes})')

    print('\n' + '-' * 70)
    print('  RECOMMENDED THRESHOLDS (paste into signal_quality.py / Config.h)')
    print('-' * 70)
    if rec:
        for k, v in rec.items():
            cur = getattr(SQA, k, None)
            arrow = '' if cur is None else f'   (current: {cur})'
            print(f'   {k:22} = {v}{arrow}')
    else:
        print('   (need a "good" class with valid clips to recommend thresholds)')

    # Headline sanity check.
    g = current_block.get('good')
    if g and (g['blocked'] + g['passed']):
        rate = 100.0 * g['blocked'] / (g['blocked'] + g['passed'])
        print(f'\n  ⚠️ CURRENT thresholds block {rate:.1f}% of your GOOD recordings '
              f'({g["blocked"]}/{g["blocked"] + g["passed"]}).')
        if rate > 5:
            print('     -> Consider loosening the thresholds above.')
        else:
            print('     -> Good — the gate rarely rejects real heartbeats.')

    if args.out:
        payload = {
            'mode': mode, 'total_clips': total,
            'metrics': {c: {k: summarize(v) for k, v in per_class_metrics[c].items()}
                        for c in classes},
            'current_gate': {c: {'blocked': current_block[c]['blocked'],
                                 'passed': current_block[c]['passed'],
                                 'codes': dict(current_block[c]['codes'])} for c in classes},
            'recommended': rec,
        }
        with open(args.out, 'w') as fh:
            json.dump(payload, fh, indent=2)
        print(f'\n📄 Full report written to {args.out}')


if __name__ == '__main__':
    main()
