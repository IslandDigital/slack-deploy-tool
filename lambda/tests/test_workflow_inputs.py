"""Tests for the modal-selection → workflow_dispatch input mapping."""
import handler


def test_picks_single_app_flag():
    inputs = handler._build_workflow_inputs(environment="dev", app="filing-next", version="__head__")

    assert inputs["deploy_filing"] == "true"
    assert inputs["deploy_calculator"] == "false"
    assert inputs["deploy_home_page"] == "false"
    assert inputs["deploy_invoicing"] == "false"
    assert inputs["deploy_api"] == "false"


def test_head_sentinel_becomes_empty_sha():
    inputs = handler._build_workflow_inputs(environment="dev", app="api", version="__head__")
    assert inputs["sha"] == ""


def test_tag_version_passed_as_sha():
    tag = "filing-next@dev@2026.05.08.4"
    inputs = handler._build_workflow_inputs(environment="dev", app="filing-next", version=tag)
    assert inputs["sha"] == tag


def test_environment_forwarded():
    for env in ("dev", "test"):
        inputs = handler._build_workflow_inputs(environment=env, app="api", version="__head__")
        assert inputs["environment"] == env


def test_auto_detect_and_force_always_disabled():
    inputs = handler._build_workflow_inputs(environment="dev", app="api", version="__head__")
    assert inputs["auto_detect"] == "false"
    assert inputs["force_deploy"] == "false"
    assert inputs["dry_run_tagging"] == "false"


def test_every_known_app_resolves_to_a_flag():
    from app_catalog import APPS

    for app in APPS:
        inputs = handler._build_workflow_inputs(environment="dev", app=app, version="__head__")
        truthy_flags = [k for k, v in inputs.items() if k.startswith("deploy_") and v == "true"]
        assert truthy_flags == [APPS[app]]
