from app.utils import sentiment


def test_positive_headline_scores_above_zero():
    score = sentiment.score_headline("Company reports strong growth and record profits")
    assert score > 0


def test_negative_headline_scores_below_zero():
    score = sentiment.score_headline("IPO faces massive losses amid fraud allegations")
    assert score < 0


def test_score_headlines_averages_across_multiple():
    positive = sentiment.score_headline("great news, strong demand")
    negative = sentiment.score_headline("terrible losses, fraud scandal")

    averaged = sentiment.score_headlines(["great news, strong demand", "terrible losses, fraud scandal"])

    assert averaged == (positive + negative) / 2


def test_score_headlines_returns_none_for_empty_list():
    assert sentiment.score_headlines([]) is None
