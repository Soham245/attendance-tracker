"""Pluggable recognition backends.

Each backend implements `RecognizerBackend` and returns `Prediction` objects
with a unified similarity metric in [0, 1] (higher = better match).
"""
