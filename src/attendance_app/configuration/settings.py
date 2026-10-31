"""Central paths and shell defaults; no attendance policy is defined here."""
from dataclasses import dataclass
from pathlib import Path
import os
import sys


@dataclass(frozen=True)
class AppConfig:
    title: str = "سامانه حضور و غیاب"
    width: int = 1280
    height: int = 820
    minimum_width: int = 960
    minimum_height: int = 640

    @property
    def data_dir(self) -> Path:
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "SmartAttendance"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "smart_attendance.db"

    @property
    def font_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets" / "fonts"

    @property
    def model_dir(self) -> Path:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "assets" / "models"
        return Path(__file__).resolve().parents[3] / "assets" / "models"


@dataclass(frozen=True)
class EnrollmentConfig:
    # Initial capture-quality gates, NOT identity acceptance thresholds.
    samples_required: int = 3
    min_face_pixels: int = 80
    min_blur_variance: float = 60.0
    min_brightness: float = 40.0
    max_brightness: float = 215.0
    detector_score: float = 0.9
    sample_interval_seconds: float = 0.5


@dataclass(frozen=True)
class RecognitionConfig:
    cosine_threshold: float = 0.5
    ambiguity_margin: float = 0.08
    consistent_frames: int = 3
    overlap_threshold: float = 0.4
