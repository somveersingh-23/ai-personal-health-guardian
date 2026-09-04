"""Contract checks for the isolated Member 3 Android client."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MOBILE = ROOT / "mobile" / "android" / "member3"


def test_mobile_module_stays_inside_member3_boundary():
    assert MOBILE.is_dir()
    changed_features = {
        path.name
        for path in (MOBILE / "app" / "src" / "main" / "java" / "com" / "healthguardian" / "member3" / "ui").glob("*Screen.kt")
    }
    assert changed_features == {
        "AlertsScreen.kt",
        "AssistantScreen.kt",
        "EmergencyScreen.kt",
        "InsightsScreen.kt",
    }


def test_mobile_client_uses_member3_api_namespace_and_safe_emergency_contract():
    client = (MOBILE / "app" / "src" / "main" / "java" / "com" / "healthguardian" / "member3" / "data" / "Member3ApiClient.kt").read_text(encoding="utf-8")
    for endpoint in ("assistant/explain", "insights", "alerts", "caregivers", "emergency/workflows"):
        assert f"/api/v1/member3/{endpoint}" in client
    assert '.put("safety_action", "emergency_escalation")' in client
    assert "external_action_performed" not in client


def test_mobile_ui_exposes_loading_offline_and_retry_states():
    sources = "\n".join(path.read_text(encoding="utf-8") for path in MOBILE.rglob("*.kt"))
    assert "LoadState.Loading" in sources
    assert "LoadState.Offline" in sources
    assert "Try again" in sources
    assert "never calls emergency services automatically" in sources
