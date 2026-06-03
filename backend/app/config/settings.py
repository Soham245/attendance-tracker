from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file: backend/app/config/settings.py
#   -> parents[0]: config, [1]: app, [2]: backend, [3]: repo root
# Anchoring to __file__ keeps the loader working regardless of where the
# process is started from (helpful for Electron, services, and CI).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "VisionAttend"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/attendai"
    )

    # Security / JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — JSON array in .env, parsed natively by pydantic-settings
    CORS_ORIGINS: List[str] = Field(default_factory=list)

    # Storage
    STORAGE_DIR: str = "./data/storage"

    # Dataset uploads
    UPLOAD_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
    IMAGE_MIN_DIMENSION: int = 64

    # Recognition backend selection: "lbph" or "arcface".
    # Changing this requires a retrain/re-enroll so the active model matches.
    RECOGNITION_BACKEND: str = "lbph"

    # ArcFace embedding recognition settings.
    # Model: MobileFaceNet trained on WebFace600K (~12 MB ONNX). Auto-downloaded
    # on first enrollment. Input 112x112 RGB, output 512-d embedding.
    ARCFACE_MODEL_NAME: str = "w600k_mbf"  # "w600k_mbf" (fast) or "w600k_r50" (accurate)
    ARCFACE_SIMILARITY_THRESHOLD: float = 0.45  # cosine similarity floor [0, 1]

    # Model registry: how many model versions to keep on disk. Oldest beyond
    # this limit are pruned on each promotion. Minimum 1 (always keep active).
    MODEL_MAX_RETAINED_VERSIONS: int = 3

    # Detection backend: "haar" (cascade, zero-dependency) or "yunet" (DNN,
    # higher accuracy, provides 5-point landmarks for ArcFace alignment).
    # YuNet uses cv2.FaceDetectorYN — no extra pip dependency, just the ONNX
    # model file which is auto-downloaded on first use (~340 KB).
    DETECTION_BACKEND: str = "haar"
    YUNET_SCORE_THRESHOLD: float = 0.7    # min detector confidence [0, 1]
    YUNET_NMS_THRESHOLD: float = 0.3      # non-max suppression overlap
    YUNET_INPUT_SIZE: int = 320            # internal resize for inference

    # Recognition runtime
    RECOGNITION_CAMERA_INDEX: int = 0
    RECOGNITION_CONFIDENCE_THRESHOLD: float = 70.0  # LBPH distance; lower = stronger match
    RECOGNITION_DETECT_SCALE_FACTOR: float = 1.1
    RECOGNITION_DETECT_MIN_NEIGHBORS: int = 5
    RECOGNITION_FRAME_INTERVAL_SECONDS: float = 0.1
    RECOGNITION_EVENT_BUFFER: int = 20
    # Per-student cooldown for emitting recognition events. Affects the SAME
    # student only; other students keep being recognized immediately. Purely
    # runtime-scoped (in-memory) — attendance persistence has its own rules.
    RECOGNITION_COOLDOWN_SECONDS: float = 8.0
    # Lazy pruning bound: stale cooldown entries older than this are dropped
    # opportunistically during checks. Keeps the dict from growing unbounded
    # without spawning a background worker.
    RECOGNITION_COOLDOWN_PRUNE_SECONDS: float = 60.0

    # LBPH metric normalisation: maps raw distance [0, SCALE] to similarity
    # [1, 0]. Used by the LBPH backend adapter to produce unified [0,1] scores.
    LBPH_DISTANCE_SCALE: float = 200.0

    # Unified similarity threshold (backend-agnostic). Predictions with
    # similarity below this floor are treated as unknown. Overrides the legacy
    # per-backend threshold when the abstraction layer is active.
    RECOGNITION_SIMILARITY_THRESHOLD: float = 0.65

    # Face preprocessing (shared across capture, training, recognition).
    # CLAHE is adaptive per-tile contrast normalization. When disabled, the
    # simpler equalizeHist is used instead — known to work well with LBPH.
    # Toggle this ON only after verifying it improves YOUR camera+lighting.
    CLAHE_ENABLED: bool = False
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_SIZE: int = 8

    # Multi-frame recognition confirmation
    RECOGNITION_CONFIRM_WINDOW: int = 5    # sliding window size (frames)
    RECOGNITION_CONFIRM_REQUIRED: int = 3  # min matches within window to confirm
    RECOGNITION_SMOOTHING_ALPHA: float = 0.4  # EMA weight for newest distance

    # MJPEG preview stream
    PREVIEW_JPEG_QUALITY: int = 70        # 0-100; lower = smaller frames
    PREVIEW_MAX_FPS: float = 12.0         # cap stream framerate
    PREVIEW_MAX_WIDTH: int = 640          # downscale for bandwidth

    # Dataset capture runtime
    CAPTURE_CAMERA_INDEX: int = 0
    CAPTURE_DEFAULT_TARGET_SAMPLES: int = 20
    CAPTURE_MIN_TARGET_SAMPLES: int = 1
    CAPTURE_MAX_TARGET_SAMPLES: int = 50
    CAPTURE_FRAME_INTERVAL_SECONDS: float = 0.1
    CAPTURE_SAMPLE_THROTTLE_SECONDS: float = 0.4  # min gap between accepted samples
    CAPTURE_FACE_SIZE: int = 200  # px (square) — written to disk
    CAPTURE_DETECT_SCALE_FACTOR: float = 1.1
    CAPTURE_DETECT_MIN_NEIGHBORS: int = 5
    CAPTURE_DETECT_MIN_FACE_FRACTION: float = 0.08  # min face side / frame side
    CAPTURE_MAX_DURATION_SECONDS: float = 120.0  # hard ceiling so runaway stops

    # Guided enrollment phases + quality gating
    CAPTURE_SAMPLES_PER_PHASE: int = 5          # good samples before phase advances
    CAPTURE_QUALITY_MIN_FACE_RATIO: float = 0.12  # face area / frame area
    CAPTURE_QUALITY_MAX_CENTER_OFFSET: float = 0.2  # max face-center drift from frame center (0-1)
    CAPTURE_QUALITY_STABILITY_FRAMES: int = 3   # consecutive stable detections before accepting
    CAPTURE_QUALITY_STABILITY_THRESH: float = 30.0  # max bbox jitter (px) for "stable"
    CAPTURE_QUALITY_MIN_SHARPNESS: float = 25.0   # Laplacian variance floor (below = blurry)
    CAPTURE_QUALITY_MIN_BRIGHTNESS: float = 40.0   # grayscale mean floor
    CAPTURE_QUALITY_MAX_BRIGHTNESS: float = 220.0  # grayscale mean ceiling
    CAPTURE_QUALITY_MIN_POSE_SHIFT: float = 0.06   # face-center-x shift as fraction of frame width

    # Capture preview stream
    CAPTURE_PREVIEW_JPEG_QUALITY: int = 70
    CAPTURE_PREVIEW_MAX_FPS: float = 12.0
    CAPTURE_PREVIEW_MAX_WIDTH: int = 640

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
