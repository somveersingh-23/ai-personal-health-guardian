"""Tests for Member 2 camera capture quality and waveform SQI pipelines."""

from __future__ import annotations

import math
from fastapi.testclient import TestClient
import pytest

from app.schemas.member2 import (
    CameraFrameQualityRequest,
    SignalQualityStatus,
    WaveformQualityAssessmentRequest,
)
from app.services.sensors import assess_camera_frame_quality, assess_waveform_quality


@pytest.fixture
def test_client(app_factory, tmp_path):
    app = app_factory(f"sqlite+aiosqlite:///{tmp_path / 'quality_test.db'}")
    with TestClient(app) as client:
        yield client


class TestCameraQualityEngine:
    def test_acceptable_frame(self):
        req = CameraFrameQualityRequest(
            mean_luminance=120.0,
            luminance_stddev=35.0,
            blur_variance=250.0,
            motion_score=0.05,
            clipped_dark_fraction=0.02,
            clipped_bright_fraction=0.02,
        )
        resp = assess_camera_frame_quality(req)
        assert resp.accepted is True
        assert resp.score >= 0.70
        assert resp.non_diagnostic is True
        assert resp.policy_version == "camera-capture-quality-v1"
        assert len(resp.reasons) == 0

    def test_underexposed_frame(self):
        req = CameraFrameQualityRequest(
            mean_luminance=20.0,
            luminance_stddev=10.0,
            blur_variance=50.0,
            motion_score=0.05,
            clipped_dark_fraction=0.15,
            clipped_bright_fraction=0.0,
        )
        resp = assess_camera_frame_quality(req)
        assert resp.accepted is False
        assert "underexposed" in resp.reasons
        assert "insufficient contrast" in resp.reasons
        assert "blurred" in resp.reasons
        assert any("lighting" in g.lower() for g in resp.guidance)

    def test_overexposed_glare_frame(self):
        req = CameraFrameQualityRequest(
            mean_luminance=230.0,
            luminance_stddev=25.0,
            blur_variance=200.0,
            motion_score=0.05,
            clipped_dark_fraction=0.0,
            clipped_bright_fraction=0.25,
        )
        resp = assess_camera_frame_quality(req)
        assert resp.accepted is False
        assert "overexposed" in resp.reasons
        assert "pixel clipping" in resp.reasons
        assert any("glare" in g.lower() for g in resp.guidance)

    def test_excessive_motion_frame(self):
        req = CameraFrameQualityRequest(
            mean_luminance=120.0,
            luminance_stddev=10.0,  # low contrast
            blur_variance=150.0,
            motion_score=0.45,  # excessive motion
            clipped_dark_fraction=0.02,
            clipped_bright_fraction=0.02,
        )
        resp = assess_camera_frame_quality(req)
        assert resp.accepted is False
        assert "excessive motion" in resp.reasons
        assert any("still" in g.lower() for g in resp.guidance)


class TestWaveformQualityEngine:
    def test_clean_waveform(self):
        # 128 samples of clean sine wave
        samples = [50.0 + 20.0 * math.sin(i * 0.2) for i in range(128)]
        req = WaveformQualityAssessmentRequest(
            samples=samples,
            sampling_rate_hz=50.0,
        )
        resp = assess_waveform_quality(req)
        assert resp.usable is True
        assert resp.signal_quality_status == SignalQualityStatus.GOOD
        assert resp.signal_quality_score >= 0.80
        assert resp.non_diagnostic is True

    def test_flatline_waveform(self):
        samples = [42.0] * 128
        req = WaveformQualityAssessmentRequest(
            samples=samples,
            sampling_rate_hz=50.0,
        )
        resp = assess_waveform_quality(req)
        assert resp.usable is False
        assert resp.signal_quality_status == SignalQualityStatus.POOR
        assert resp.signal_quality_score == 0.0

    def test_motion_correlated_waveform(self):
        samples = [50.0 + 10.0 * math.sin(i * 0.2) for i in range(128)]
        motion = [math.sin(i * 0.2) for i in range(128)]
        req = WaveformQualityAssessmentRequest(
            samples=samples,
            sampling_rate_hz=50.0,
            motion_reference=motion,
        )
        resp = assess_waveform_quality(req)
        assert resp.motion_correlation is not None
        assert abs(resp.motion_correlation - 1.0) < 1e-4
        assert resp.signal_quality_score < 1.0


class TestQualityEndpoints:
    def test_local_camera_quality_requires_profile(self, test_client):
        payload = {
            "mean_luminance": 120.0,
            "luminance_stddev": 35.0,
            "blur_variance": 250.0,
            "motion_score": 0.05,
            "clipped_dark_fraction": 0.02,
            "clipped_bright_fraction": 0.02,
        }
        res = test_client.post("/api/v1/member2/quality/camera?user_id=99999", json=payload)
        assert res.status_code == 404

    def test_local_camera_quality_with_profile(self, test_client):
        # Create health profile for user 10
        profile_res = test_client.post(
            "/api/v1/member1/health-profile",
            json={"user_id": 10},
        )
        assert profile_res.status_code in (200, 201)

        payload = {
            "mean_luminance": 120.0,
            "luminance_stddev": 35.0,
            "blur_variance": 250.0,
            "motion_score": 0.05,
            "clipped_dark_fraction": 0.02,
            "clipped_bright_fraction": 0.02,
        }
        res = test_client.post("/api/v1/member2/quality/camera?user_id=10", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["accepted"] is True
        assert data["non_diagnostic"] is True

    def test_local_waveform_quality_with_profile(self, test_client):
        # Create health profile for user 11
        test_client.post(
            "/api/v1/member1/health-profile",
            json={"user_id": 11},
        )

        samples = [50.0 + 20.0 * math.sin(i * 0.2) for i in range(128)]
        payload = {
            "samples": samples,
            "sampling_rate_hz": 50.0,
        }
        res = test_client.post("/api/v1/member2/quality/waveform?user_id=11", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["usable"] is True
        assert data["signal_quality_status"] == "good"
