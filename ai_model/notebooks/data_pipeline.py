"""Reusable, leakage-safe data pipeline for the Saka RHD classifier.

The functions here back `data_imbalance.ipynb`. The whole point of this module is
to enforce one rule that is easy to get wrong in a notebook:

    Split test/validation at the PATIENT level BEFORE augmentation.
    Augment the training split ONLY.

Keeping the logic here (instead of only in cells) means it can be unit-tested and
reused by training scripts without re-running Jupyter.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

import numpy as np
import pandas as pd

RANDOM_STATE = 42


@dataclass
class Split:
    """A train/validation/test split at the patient level."""
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame

    def assert_no_leakage(self, id_col: str = "patient_id") -> None:
        a, b, c = (set(self.train[id_col]), set(self.val[id_col]), set(self.test[id_col]))
        assert a.isdisjoint(c), "LEAKAGE: train ∩ test not empty"
        assert a.isdisjoint(b), "LEAKAGE: train ∩ val not empty"
        assert b.isdisjoint(c), "LEAKAGE: val ∩ test not empty"


def patient_level_split(df: pd.DataFrame, test_frac: float = 0.15,
                        val_frac: float = 0.15, label_col: str = "label",
                        random_state: int = RANDOM_STATE) -> Split:
    """Stratified patient-level split. Runs BEFORE any augmentation."""
    from sklearn.model_selection import train_test_split

    train_val, test = train_test_split(
        df, test_size=test_frac, stratify=df[label_col], random_state=random_state)
    val_rel = val_frac / (1.0 - test_frac)
    train, val = train_test_split(
        train_val, test_size=val_rel, stratify=train_val[label_col],
        random_state=random_state)
    split = Split(train.reset_index(drop=True),
                  val.reset_index(drop=True),
                  test.reset_index(drop=True))
    split.assert_no_leakage()
    return split


def copy_raw(rows: pd.DataFrame, src_root: str, dest_root: str,
             label_col: str = "label", id_col: str = "patient_id") -> int:
    """Copy each patient's raw .wav into dest_root/<label>/ unchanged.

    Used for the held-out test/ and validation/ folders — these are never
    balanced or augmented.
    """
    n = 0
    for _, row in rows.iterrows():
        src = os.path.join(src_root, row[label_col], f"{row[id_col]}.wav")
        if os.path.exists(src):
            dst_dir = os.path.join(dest_root, row[label_col])
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy(src, os.path.join(dst_dir, f"{row[id_col]}.wav"))
            n += 1
    return n


# --------------------------------------------------------------- augmentation
def time_shift(signal: np.ndarray, shift_ms: float, fs: int) -> np.ndarray:
    s = int(shift_ms * fs / 1000)
    if s > 0:
        return np.pad(signal, (s, 0), mode="constant")[: len(signal)]
    return np.pad(signal, (0, -s), mode="constant")[-len(signal):]


def add_noise(signal: np.ndarray, level: float = 0.005) -> np.ndarray:
    return signal + np.random.normal(0, level, len(signal))


def augment_signal(signal: np.ndarray, fs: int):
    """Return list of (name, signal) augmentations. TRAIN split only."""
    import librosa

    out = [("tshift_10", time_shift(signal, 10, fs)),
           ("tshift_-10", time_shift(signal, -10, fs)),
           ("noise", add_noise(signal))]
    st = librosa.effects.time_stretch(signal, rate=1.05)
    st = st[: len(signal)] if len(st) > len(signal) else np.pad(st, (0, len(signal) - len(st)))
    out.append(("stretch", st))
    out.append(("pitch", librosa.effects.pitch_shift(signal, sr=fs, n_steps=1)))
    return out


def assert_augmentation_safe(augmented_ids, held_out_ids, sep: str = "_") -> None:
    """Guard: no augmented clip may derive from a held-out (val/test) patient."""
    origins = {pid.split(sep)[0] for pid in augmented_ids}
    leaked = origins & set(held_out_ids)
    assert not leaked, f"LEAKAGE: augmented clips from held-out patients: {leaked}"
