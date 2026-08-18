from app.utils.name_matching import normalize_company_name


def test_strips_common_suffixes_and_punctuation():
    assert normalize_company_name("Technocrats Plasma Systems Ltd.") == normalize_company_name(
        "TECHNOCRATS PLASMA SYSTEMS LIMITED"
    )


def test_strips_ipo_and_private_pvt():
    assert normalize_company_name("Gaja Alternative Asset Management Pvt Ltd") == normalize_company_name(
        "Gaja Alternative Asset Management Private Limited IPO"
    )


def test_collapses_whitespace_and_case():
    assert normalize_company_name("  Sham   Foam  LTD ") == normalize_company_name("SHAM FOAM")


def test_different_companies_stay_different():
    assert normalize_company_name("Alpha Ltd") != normalize_company_name("Beta Ltd")
