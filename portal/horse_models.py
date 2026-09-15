"""Compatibility exports for horse registry models."""

from .model_modules.horses import (
    Horse,
    HorseCogginsRecord,
    HorseSeasonProfile,
    HorseShowAssignment,
    HorseShowAward,
)
from .model_modules.equine_registry import HorseIdentifier

__all__ = [
    "Horse",
    "HorseIdentifier",
    "HorseCogginsRecord",
    "HorseSeasonProfile",
    "HorseShowAssignment",
    "HorseShowAward",
]
