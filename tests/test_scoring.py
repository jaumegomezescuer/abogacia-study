import math

from services.scoring_service import calculate_mock_exam_score, calculate_score


def test_only_correct():
    assert calculate_score(correct=10, incorrect=0, blank=0) == 10.0


def test_only_incorrect():
    score = calculate_score(correct=0, incorrect=6, blank=0)
    assert math.isclose(score, -2.0, rel_tol=1e-9)


def test_only_blank():
    assert calculate_score(correct=0, incorrect=0, blank=10) == 0.0


def test_mixed_answers():
    # 8 aciertos, 4 errores, 3 blancos, penalización 1/3
    score = calculate_score(correct=8, incorrect=4, blank=3)
    assert math.isclose(score, 8 - 4 / 3, rel_tol=1e-9)


def test_decimal_penalty():
    score = calculate_score(correct=5, incorrect=3, blank=0, incorrect_penalty=0.25)
    assert math.isclose(score, 5 - 0.75, rel_tol=1e-9)


def test_custom_blank_score():
    score = calculate_score(correct=0, incorrect=0, blank=4, blank_score=0.1)
    assert math.isclose(score, 0.4, rel_tol=1e-9)


def test_mock_exam_weighting_common_and_criminal():
    result = calculate_mock_exam_score(
        common_correct=45, common_incorrect=5, common_blank=0,
        criminal_correct=20, criminal_incorrect=5, criminal_blank=0,
    )
    # comprobar cada parte por separado
    expected_common_raw = 45 - 5 * (1 / 3)
    expected_criminal_raw = 20 - 5 * (1 / 3)
    assert math.isclose(result.common.raw_score, expected_common_raw, rel_tol=1e-9)
    assert math.isclose(result.criminal.raw_score, expected_criminal_raw, rel_tol=1e-9)

    expected_common_norm = expected_common_raw / 50 * 10
    expected_criminal_norm = expected_criminal_raw / 25 * 10
    assert math.isclose(result.common.normalized_0_10, expected_common_norm, rel_tol=1e-9)
    assert math.isclose(result.criminal.normalized_0_10, expected_criminal_norm, rel_tol=1e-9)

    expected_total = expected_common_norm * (2 / 3) + expected_criminal_norm * (1 / 3)
    assert math.isclose(result.total_score_0_10, expected_total, rel_tol=1e-9)


def test_mock_exam_with_no_answers_in_a_part_does_not_divide_by_zero():
    result = calculate_mock_exam_score(
        common_correct=0, common_incorrect=0, common_blank=0,
        criminal_correct=10, criminal_incorrect=0, criminal_blank=0,
    )
    assert result.common.normalized_0_10 == 0.0
    assert result.criminal.normalized_0_10 == 10.0
