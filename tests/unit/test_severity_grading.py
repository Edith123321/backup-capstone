# Unit tests for the severity grading service (backend/services/severity_grading.py)
import pytest
from services.severity_grading import severity_grader, SeverityResult


@pytest.mark.unit
class TestSeverityGrading:
    def test_normal_is_grade_0(self):
        r = severity_grader.grade_from_prediction('Normal', 0.95)
        assert r.grade == 0
        assert r.label == 'Normal'

    def test_rhd_high_confidence_is_definite(self):
        r = severity_grader.grade_from_prediction('RHD', 0.95)
        assert r.grade == 2
        assert 'RHD' in r.label

    def test_rhd_low_confidence_is_borderline(self):
        r = severity_grader.grade_from_prediction('RHD', 0.60)
        assert r.grade == 1

    def test_mitral_point_escalates_borderline(self):
        # A borderline-confidence RHD at the mitral valve should escalate.
        r = severity_grader.grade_from_prediction('RHD', 0.80, auscultation_point='mitral')
        assert r.grade == 2

    def test_to_dict_shape(self):
        d = severity_grader.grade_from_prediction('RHD', 0.9).to_dict()
        for key in ('grade', 'label', 'color', 'confidence', 'recommendation'):
            assert key in d
        assert d['color'].startswith('#')

    @pytest.mark.parametrize('pred,conf,expected', [
        ('Normal', 0.99, 0),
        ('normal', 0.5, 0),
        ('RHD', 0.99, 2),
        ('RHD', 0.55, 1),
    ])
    def test_grade_matrix(self, pred, conf, expected):
        assert severity_grader.grade_from_prediction(pred, conf).grade == expected
