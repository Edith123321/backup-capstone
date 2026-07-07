# backend/services/severity_grading.py
"""
Severity grading service for the SAKA RHD detection system.

Maps the binary AI classifier output ('Normal' / 'RHD') plus confidence,
auscultation point and optional clinical context into a clinical severity
grade used across the platform:

    Grade 0 -> Normal
    Grade 1 -> Borderline RHD
    Grade 2 -> Definite RHD

Longitudinal history/trend reads are delegated to the database layer so the
whole platform shares a single source of truth (the `severity_history` table).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# =========================
# GRADE DEFINITIONS
# =========================
# Color-coded, one entry per grade. Colors match the frontend palette.
GRADE_DEFINITIONS = {
    0: {
        'label': 'Normal',
        'color': '#10b981',      # green
        'bg_color': '#d1fae5',
        'recommendation': 'No pathological murmur detected. Continue routine monitoring.'
    },
    1: {
        'label': 'Borderline RHD',
        'color': '#f59e0b',      # amber
        'bg_color': '#fef3c7',
        'recommendation': 'Borderline findings. Repeat screening in 3 months and consider echocardiography.'
    },
    2: {
        'label': 'Definite RHD',
        'color': '#ef4444',      # red
        'bg_color': '#fee2e2',
        'recommendation': 'Pathological murmur consistent with RHD. Refer for echocardiography and cardiology review.'
    },
}

# Confidence at/above this splits Borderline (grade 1) from Definite (grade 2)
# when the classifier flags 'RHD'.
DEFINITE_CONFIDENCE_THRESHOLD = 0.85

# Mitral / aortic points carry more diagnostic weight for RHD murmurs.
HIGH_WEIGHT_POINTS = {'mitral', 'aortic', 'mitral_valve', 'aortic_valve'}


@dataclass
class SeverityResult:
    """Result of grading a single prediction."""
    grade: int
    label: str
    color: str
    bg_color: str
    confidence: float
    recommendation: str
    prediction: Optional[str] = None
    auscultation_point: Optional[str] = None
    factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'grade': self.grade,
            'label': self.label,
            'color': self.color,
            'bg_color': self.bg_color,
            'confidence': round(float(self.confidence), 4),
            'recommendation': self.recommendation,
            'prediction': self.prediction,
            'auscultation_point': self.auscultation_point,
            'factors': self.factors,
        }


class SeverityGrader:
    """Grades predictions and exposes longitudinal history/trend helpers."""

    def grade_from_prediction(
        self,
        prediction: str,
        confidence: float,
        auscultation_point: Optional[str] = None,
        clinical_data: Optional[Dict] = None,
    ) -> SeverityResult:
        """
        Convert an AI prediction into a clinical severity grade.

        Args:
            prediction: 'Normal' or 'RHD' (case-insensitive).
            confidence: model confidence in [0, 1].
            auscultation_point: e.g. 'mitral', 'aortic'.
            clinical_data: optional dict with keys such as
                'age', 'symptoms', 'risk_factors', 'triage_color'.
        """
        clinical_data = clinical_data or {}
        confidence = float(confidence or 0.0)
        factors: List[str] = []

        normal = str(prediction).strip().lower() in ('normal', 'no', '0', 'negative')

        if normal:
            grade = 0
        else:
            # RHD detected: severity scales with confidence + clinical context.
            grade = 2 if confidence >= DEFINITE_CONFIDENCE_THRESHOLD else 1
            factors.append(f'AI classified RHD (confidence {confidence:.0%})')

            # High-weight auscultation points push a borderline case to definite.
            if auscultation_point and str(auscultation_point).strip().lower() in HIGH_WEIGHT_POINTS:
                factors.append(f'High-weight auscultation point: {auscultation_point}')
                if grade == 1 and confidence >= 0.75:
                    grade = 2

            # Clinical red flags escalate a borderline case.
            triage_color = str(clinical_data.get('triage_color', '')).strip().lower()
            if grade == 1 and triage_color in ('red', 'orange'):
                factors.append(f'Escalated by triage colour: {triage_color}')
                grade = 2

            symptoms = clinical_data.get('symptoms') or []
            if grade == 1 and len(symptoms) >= 2:
                factors.append('Multiple presenting symptoms')
                grade = 2

        definition = GRADE_DEFINITIONS[grade]
        return SeverityResult(
            grade=grade,
            label=definition['label'],
            color=definition['color'],
            bg_color=definition['bg_color'],
            confidence=confidence,
            recommendation=definition['recommendation'],
            prediction='Normal' if normal else 'RHD',
            auscultation_point=auscultation_point,
            factors=factors,
        )

    def get_severity_history(self, patient_id: str, limit: int = 20) -> List[Dict]:
        """Longitudinal severity history for a patient (delegates to DB)."""
        try:
            from services.database import db
            return db.get_severity_history(patient_id, limit=limit)
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ severity history unavailable: {e}")
            return []

    def get_severity_trend(self, patient_id: str) -> Dict:
        """Trend analysis over a patient's severity history (delegates to DB)."""
        try:
            from services.database import db
            return db.get_severity_trend(patient_id)
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ severity trend unavailable: {e}")
            return {
                'trend': 'No data',
                'current_grade': 0,
                'previous_grade': 0,
                'change': 0,
                'direction': 'stable',
                'history': [],
            }

    def track_severity_history(self, patient_id: str, severity: SeverityResult,
                               recording_id: Optional[str] = None) -> bool:
        """
        Persist a grading result to the longitudinal history table.

        Recording saves already write history inline, so this is mainly for
        gradings produced outside the recording flow. Safe no-op on failure.
        """
        try:
            from services.database import db
            conn = db.get_connection()
            db._save_severity_history(
                conn,
                patient_id,
                recording_id or f'adhoc-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                severity.grade,
                severity.label,
                severity.prediction,
                severity.confidence,
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ could not track severity history: {e}")
            return False


# Singleton used across the app.
severity_grader = SeverityGrader()
