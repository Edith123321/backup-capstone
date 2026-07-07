# backend/services/markov_model.py
"""
Markov transition model for RHD disease progression.

Models progression across three states:

    State 0 -> Normal
    State 1 -> Borderline RHD
    State 2 -> Definite RHD

A monthly transition matrix drives longitudinal projections (state
distribution after N months) and a steady-state (long-run) distribution.
`risk_calculator` combines the current grade, patient clinical factors and the
Markov long-run probability of reaching Definite RHD into a 0-100 risk score.
"""

from datetime import datetime
from typing import Dict, List

import numpy as np


# =========================
# MARKOV MODEL
# =========================
class MarkovModel:
    """Three-state monthly Markov chain for RHD progression."""

    STATES = ['Normal', 'Borderline RHD', 'Definite RHD']

    # Monthly transition matrix WITHOUT secondary prophylaxis.
    # Row = current state, column = next state. Each row sums to 1.
    BASE_MONTHLY = np.array([
        [0.985, 0.012, 0.003],   # Normal
        [0.030, 0.940, 0.030],   # Borderline
        [0.005, 0.015, 0.980],   # Definite
    ])

    # Secondary prophylaxis (penicillin) slows progression and allows some
    # regression from borderline. Applied as a blend towards this matrix.
    TREATED_MONTHLY = np.array([
        [0.990, 0.008, 0.002],   # Normal
        [0.080, 0.910, 0.010],   # Borderline (more regression, less progression)
        [0.010, 0.040, 0.950],   # Definite
    ])

    def transition_matrix(self, treatment: str = 'none', risk_multiplier: float = 1.0) -> np.ndarray:
        """
        Build an effective monthly transition matrix.

        Args:
            treatment: 'none', 'prophylaxis'/'penicillin', or 'partial'.
            risk_multiplier: >1 accelerates progression (clinical risk factors),
                             <1 slows it. Applied to forward-progression cells.
        """
        treated = str(treatment).strip().lower() in ('prophylaxis', 'penicillin', 'secondary_prophylaxis', 'full')
        base = self.TREATED_MONTHLY if treated else self.BASE_MONTHLY
        m = base.copy()

        if risk_multiplier != 1.0:
            # Scale the upper-triangular (progression) probabilities, then
            # renormalise each row so it remains a valid distribution.
            for i in range(3):
                for j in range(i + 1, 3):
                    m[i, j] *= risk_multiplier
                row_off = sum(m[i, k] for k in range(3) if k != i)
                if row_off > 0.999:
                    m[i] = m[i] / (row_off + m[i, i]) if (row_off + m[i, i]) > 0 else m[i]
                m[i, i] = max(0.0, 1.0 - sum(m[i, k] for k in range(3) if k != i))
        return m

    def project(self, current_grade: int, months: int,
                treatment: str = 'none', risk_multiplier: float = 1.0) -> np.ndarray:
        """State distribution after `months`, starting from `current_grade`."""
        state = np.zeros(3)
        state[int(np.clip(current_grade, 0, 2))] = 1.0
        m = self.transition_matrix(treatment, risk_multiplier)
        return state @ np.linalg.matrix_power(m, max(0, int(months)))

    def steady_state(self, treatment: str = 'none', risk_multiplier: float = 1.0) -> np.ndarray:
        """Long-run stationary distribution (left eigenvector for eigenvalue 1)."""
        m = self.transition_matrix(treatment, risk_multiplier)
        vals, vecs = np.linalg.eig(m.T)
        idx = np.argmin(np.abs(vals - 1.0))
        vec = np.real(vecs[:, idx])
        vec = np.abs(vec)
        total = vec.sum()
        return vec / total if total > 0 else np.array([1.0, 0.0, 0.0])


# =========================
# RISK CALCULATOR
# =========================
class RiskCalculator:
    """Turns a Markov projection + clinical context into a risk assessment."""

    def __init__(self, model: MarkovModel):
        self.model = model

    # ---- clinical risk multiplier ----------------------------------------
    def _risk_multiplier(self, clinical_data: Dict) -> (float, List[str]):
        multiplier = 1.0
        factors: List[str] = []

        age = clinical_data.get('age', 30) or 30
        if 5 <= age <= 15:
            multiplier *= 1.4
            factors.append('High-risk age band (5-15 years)')
        elif age <= 25:
            multiplier *= 1.15
            factors.append('Elevated-risk age band (<25 years)')

        risk_factors = clinical_data.get('risk_factors') or []
        rf = {str(f).strip().lower() for f in risk_factors}
        if rf & {'history_of_rhd', 'rheumatic_fever_history', 'prior_rheumatic_fever'}:
            multiplier *= 1.5
            factors.append('Prior rheumatic fever / RHD history')
        if 'recurrent_strep' in rf or 'strep_throat' in rf:
            multiplier *= 1.25
            factors.append('Recurrent streptococcal infection')
        if 'family_history' in rf:
            multiplier *= 1.1
            factors.append('Family history of RHD')

        return multiplier, factors

    def _risk_level(self, score: float) -> str:
        if score >= 75:
            return 'Critical'
        if score >= 50:
            return 'High'
        if score >= 25:
            return 'Moderate'
        return 'Low'

    def _recommendations(self, current_grade: int, risk_level: str, treatment: str) -> List[str]:
        recs: List[str] = []
        if current_grade >= 2:
            recs.append('Refer for echocardiography and cardiology review')
        elif current_grade == 1:
            recs.append('Repeat auscultation screening in 3 months')
            recs.append('Consider echocardiography to confirm findings')

        treated = str(treatment).strip().lower() in ('prophylaxis', 'penicillin', 'secondary_prophylaxis', 'full')
        if not treated and current_grade >= 1:
            recs.append('Initiate secondary prophylaxis (benzathine penicillin) per WHO guidance')

        if risk_level in ('High', 'Critical'):
            recs.append('Prioritise follow-up; monitor for symptom progression')
        else:
            recs.append('Continue routine longitudinal monitoring')
        return recs

    # ---- public API -------------------------------------------------------
    def calculate_risk(self, patient_id: str, clinical_data: Dict) -> Dict:
        """
        Compute a prognostic risk assessment for a patient.

        Returns a dict with 'prognosis' (risk_score, risk_level, recommendations,
        progression_probabilities) and 'trend' (direction from history).
        """
        current_grade = int(clinical_data.get('current_grade', 0) or 0)
        treatment = clinical_data.get('treatment', 'none')
        multiplier, factors = self._risk_multiplier(clinical_data)

        # Long-run probability of Definite RHD, blended with current severity.
        steady = self.model.steady_state(treatment, multiplier)
        p_definite = float(steady[2])
        # Score: weight current state heavily, then long-run definite risk.
        score = 100.0 * (0.55 * (current_grade / 2.0) + 0.45 * p_definite)
        score = float(np.clip(score, 0, 100))
        risk_level = self._risk_level(score)

        # 24-month projection for context.
        proj_24 = self.model.project(current_grade, 24, treatment, multiplier)

        history = self._get_grade_history(patient_id)
        direction = self._trend_direction(history)

        return {
            'success': True,
            'patient_id': patient_id,
            'prognosis': {
                'risk_score': round(score, 1),
                'risk_level': risk_level,
                'current_grade': current_grade,
                'p_definite_longrun': round(p_definite, 4),
                'progression_probabilities': {
                    'normal': round(float(proj_24[0]), 4),
                    'borderline': round(float(proj_24[1]), 4),
                    'definite': round(float(proj_24[2]), 4),
                },
                'contributing_factors': factors,
                'recommendations': self._recommendations(current_grade, risk_level, treatment),
            },
            'trend': {
                'direction': direction,
                'assessments': len(history),
            },
            'steady_state': {
                'normal': round(float(steady[0]), 4),
                'borderline': round(float(steady[1]), 4),
                'definite': round(float(steady[2]), 4),
            },
            'timestamp': datetime.now().isoformat(),
        }

    def get_longitudinal_prediction(self, patient_id: str, months: int = 24) -> Dict:
        """Project state distribution monthly out to `months` for a patient."""
        history = self._get_grade_history(patient_id)
        current_grade = history[0]['grade'] if history else 0

        checkpoints = sorted({m for m in (3, 6, 12, 18, 24, months) if 0 < m <= months})
        timeline = []
        for m in checkpoints:
            dist = self.model.project(current_grade, m)
            timeline.append({
                'month': m,
                'normal': round(float(dist[0]), 4),
                'borderline': round(float(dist[1]), 4),
                'definite': round(float(dist[2]), 4),
            })

        return {
            'success': True,
            'patient_id': patient_id,
            'current_grade': current_grade,
            'horizon_months': months,
            'timeline': timeline,
        }

    # ---- history helpers --------------------------------------------------
    def _get_grade_history(self, patient_id: str) -> List[Dict]:
        """Ordered (newest-first) severity-grade history from the DB."""
        try:
            from services.database import db
            rows = db.get_severity_history(patient_id, limit=50)
            return [
                {
                    'grade': r.get('severity_grade', 0),
                    'label': r.get('severity_label', 'Unknown'),
                    'confidence': r.get('confidence'),
                    'assessed_at': r.get('assessed_at'),
                }
                for r in rows
            ]
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ grade history unavailable: {e}")
            return []

    def _trend_direction(self, history: List[Dict]) -> str:
        if len(history) < 2:
            return 'insufficient_data'
        current = history[0]['grade']
        previous = history[1]['grade']
        if current > previous:
            return 'worsening'
        if current < previous:
            return 'improving'
        return 'stable'


# Singletons used across the app.
markov_model = MarkovModel()
risk_calculator = RiskCalculator(markov_model)
