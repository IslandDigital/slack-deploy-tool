"""Tests for the pure tag-filtering functions in github_tags."""
from github_tags import apps_with_tags_for_env, tags_for_app_env

ALL_TAGS = [
    "filing-next@dev@2026.05.08.4",
    "filing-next@dev@2026.05.08.3",
    "filing-next@test@2026.05.01.1",
    "api@dev@2026.05.08.3",
    "api@dev@2026.05.08.2",
    "home-page@dev@2026.05.08.1",
    "calculator-next@dev@2026.05.07.1",
    "invoicing-next@test@2026.04.20.2",
    # legacy / non-conforming
    "vat-next/1.0.0",
    "invoicing-next/2026.04.14.1",
]

ALL_APPS = ["calculator-next", "filing-next", "home-page", "invoicing-next", "api"]


def test_tags_for_app_env_filters_strictly():
    out = tags_for_app_env(ALL_TAGS, "filing-next", "dev")
    assert out == [
        "filing-next@dev@2026.05.08.4",
        "filing-next@dev@2026.05.08.3",
    ]


def test_tags_for_app_env_other_env_excluded():
    out = tags_for_app_env(ALL_TAGS, "filing-next", "test")
    assert out == ["filing-next@test@2026.05.01.1"]


def test_tags_for_app_env_no_matches_returns_empty():
    assert tags_for_app_env(ALL_TAGS, "filing-next", "prod") == []


def test_tags_for_app_env_ignores_legacy_format():
    assert tags_for_app_env(ALL_TAGS, "vat-next", "dev") == []


def test_apps_with_tags_for_env_dev():
    out = apps_with_tags_for_env(ALL_TAGS, "dev", ALL_APPS)
    assert set(out) == {"filing-next", "api", "home-page", "calculator-next"}
    assert "invoicing-next" not in out  # only has test tags


def test_apps_with_tags_for_env_test():
    out = apps_with_tags_for_env(ALL_TAGS, "test", ALL_APPS)
    assert set(out) == {"filing-next", "invoicing-next"}


def test_apps_with_tags_for_env_unknown_env():
    assert apps_with_tags_for_env(ALL_TAGS, "prod", ALL_APPS) == []


def test_apps_with_tags_preserves_input_order():
    out = apps_with_tags_for_env(ALL_TAGS, "dev", ALL_APPS)
    assert out == [a for a in ALL_APPS if a in out]
