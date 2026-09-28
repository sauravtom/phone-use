"""Reviewer automation must never attach to a personal USB device."""

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location(
    "review_bridge", Path(__file__).resolve().parents[1] / "scripts/review-bridge.py"
)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_review_bridge_rejects_physical_device_before_contacting_it():
    with patch.object(review.Adb, "shell", side_effect=AssertionError("Must not contact phone")):
        with pytest.raises(ValueError, match="restricted to an Android emulator"):
            asyncio.run(review.run("https://relay.example", "physical-usb-phone"))


def test_review_bridge_requires_emulator_property_not_just_serial_name():
    with patch.object(review.Adb, "shell", return_value="0"):
        with pytest.raises(ValueError, match="restricted to an Android emulator"):
            asyncio.run(review.run("https://relay.example", "emulator-5554"))


def test_review_bridge_rejects_unencrypted_origin():
    with pytest.raises(ValueError, match="HTTPS"):
        asyncio.run(review.run("http://relay.example", "emulator-5554"))
