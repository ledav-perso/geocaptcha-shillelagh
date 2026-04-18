"""
Shillelagh adapter for the GeoCaptcha REST API.

Exposes GeoCaptcha admin endpoints as virtual SQL tables that can be
queried from Apache Superset (or any other shillelagh-compatible tool).
"""

from geocaptcha_shillelagh.session import GeocaptchaSessionAdapter
from geocaptcha_shillelagh.cuser import GeocaptchaCuserAdapter
from geocaptcha_shillelagh.kingpin import GeocaptchaKingpinAdapter

__all__ = ["GeoCaptchaSessionAdapter",
           "GeoCaptchaCUserAdapter",
           "GeoCaptchaKingpinAdapter"]
