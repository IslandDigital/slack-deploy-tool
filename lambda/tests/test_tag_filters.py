"""Tests for the pure tag-filtering functions in github_tags.

Two tag conventions coexist in the real repo:
- 3-segment (env-aware, newer):  `<app>@<env>@YYYY.MM.DD.N`
- 2-segment (legacy):            `<app>@<version>`
"""
from github_tags import apps_with_tags_for_env, tags_for_app_env

# Mix of both formats, like IslandDigital/tax-web has today.
MIXED_TAGS = [
    # 3-seg env-aware
    "filing-next@dev@2026.05.08.4",
    "filing-next@dev@2026.05.08.3",
    "filing-next@test@2026.05.01.1",
    "api@dev@2026.04.27.3",
    "home-page@dev@2026.05.08.1",
    "invoicing-next@test@2026.04.20.2",
    # 2-seg legacy
    "api@1.0.0",
    "api@2026.02.26.1",
    "api@2026.02.27.2",
    "calculator-next@2026.04.01.1",
    "vat-next@2026.03.01.1",
]

ALL_APPS = ["calculator-next", "filing-next", "home-page", "invoicing-next", "api"]


def test_three_seg_filtered_strictly_by_env():
    out = tags_for_app_env(MIXED_TAGS, "filing-next", "dev")
    # Picks the two filing-next@dev@ tags, plus filing-next has no 2-seg legacy in fixture.
    assert "filing-next@dev@2026.05.08.4" in out
    assert "filing-next@dev@2026.05.08.3" in out
    # test-env tag should not appear under dev
    assert "filing-next@test@2026.05.01.1" not in out


def test_two_seg_legacy_appears_for_any_env():
    out = tags_for_app_env(MIXED_TAGS, "api", "dev")
    # Legacy 2-seg tags show under dev (and would under test too)
    assert "api@1.0.0" in out
    assert "api@2026.02.26.1" in out
    # 3-seg api@dev tag also included
    assert "api@dev@2026.04.27.3" in out


def test_two_seg_legacy_also_for_test_env():
    out = tags_for_app_env(MIXED_TAGS, "api", "test")
    assert "api@1.0.0" in out  # legacy shows for any env
    assert "api@dev@2026.04.27.3" not in out  # dev-specific does not


def test_no_tags_for_unknown_app():
    assert tags_for_app_env(MIXED_TAGS, "ghost-app", "dev") == []


def test_apps_with_three_seg_for_env_filters_strictly():
    out = apps_with_tags_for_env(MIXED_TAGS, "dev", ALL_APPS)
    assert set(out) == {"filing-next", "api", "home-page"}
    assert "invoicing-next" not in out  # has test tag only
    assert "calculator-next" not in out  # has only 2-seg legacy


def test_apps_with_three_seg_for_env_test():
    out = apps_with_tags_for_env(MIXED_TAGS, "test", ALL_APPS)
    assert set(out) == {"filing-next", "invoicing-next"}


def test_apps_fallback_when_no_three_seg_tags_for_env():
    # Only legacy tags — apps_with_tags_for_env returns ALL candidates.
    legacy_only = ["api@1.0.0", "calculator-next@2026.04.01.1"]
    out = apps_with_tags_for_env(legacy_only, "dev", ALL_APPS)
    assert out == ALL_APPS


def test_apps_fallback_when_no_tags_at_all():
    assert apps_with_tags_for_env([], "dev", ALL_APPS) == ALL_APPS


def test_apps_preserves_input_order():
    out = apps_with_tags_for_env(MIXED_TAGS, "dev", ALL_APPS)
    assert out == [a for a in ALL_APPS if a in out]
