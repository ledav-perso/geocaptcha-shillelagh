"""
Shillelagh adapter for the GeoCaptcha REST API.

Exposes GeoCaptcha admin endpoints as virtual SQL tables that can be
queried from Apache Superset (or any other shillelagh-compatible tool).
"""

from geocaptcha_shillelagh.adapter import GeocaptchaAdapter

__all__ = ["GeocaptchaAdapter"]
