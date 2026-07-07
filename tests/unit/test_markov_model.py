# Unit tests for the Markov prognosis model (backend/services/markov_model.py)
import numpy as np
import pytest
from services.markov_model import markov_model, risk_calculator


@pytest.mark.unit
class TestMarkovModel:
    def test_transition_rows_are_stochastic(self):
        for treatment in ('none', 'prophylaxis'):
            m = markov_model.transition_matrix(treatment)
            assert m.shape == (3, 3)
            assert np.allclose(m.sum(axis=1), 1.0), f'{treatment} rows must sum to 1'
            assert (m >= 0).all()

    def test_steady_state_is_distribution(self):
        ss = markov_model.steady_state('none')
        assert np.isclose(ss.sum(), 1.0)
        assert (ss >= -1e-9).all()

    def test_projection_is_distribution(self):
        dist = markov_model.project(0, 24)
        assert np.isclose(dist.sum(), 1.0)
        assert len(dist) == 3

    def test_treatment_lowers_definite_risk(self):
        untreated = markov_model.steady_state('none')[2]
        treated = markov_model.steady_state('prophylaxis')[2]
        assert treated <= untreated

    def test_risk_score_bounds_and_level(self):
        res = risk_calculator.calculate_risk('p1', {
            'current_grade': 2, 'age': 12, 'gender': 'female',
            'risk_factors': ['history_of_rhd'], 'treatment': 'none',
        })
        score = res['prognosis']['risk_score']
        assert 0 <= score <= 100
        assert res['prognosis']['risk_level'] in ('Low', 'Moderate', 'High', 'Critical')

    def test_higher_grade_gives_higher_risk(self):
        low = risk_calculator.calculate_risk('a', {'current_grade': 0})['prognosis']['risk_score']
        high = risk_calculator.calculate_risk('b', {'current_grade': 2})['prognosis']['risk_score']
        assert high > low
