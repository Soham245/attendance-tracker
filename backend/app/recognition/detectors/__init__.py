"""Pluggable face detection backends.

Each backend implements `FaceDetectorBackend` and returns `DetectionResult`
objects carrying a bounding box, detector confidence, and optional landmarks.
"""
