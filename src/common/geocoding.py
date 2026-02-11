"""
Geocoding service for resolving city/address names to coordinates.

Uses a local lookup table from config.py for common tourism cities.
Implements caching to avoid repeated string parsing.
"""

from typing import TypedDict

from common.config import CITY_COORDINATES


class Coordinates(TypedDict):
    """Geographic coordinates."""

    latitude: float
    longitude: float


# Module-level cache for runtime lookups
_geocode_cache: dict[str, Coordinates | None] = {}


def geocode(location: str) -> Coordinates | None:
    """
    Resolve location string to coordinates.

    Uses local CITY_COORDINATES lookup table from config.
    Caches results to avoid repeated string parsing.
    Falls back to None if city not in lookup table.

    Args:
        location: City name or address string to resolve

    Returns:
        Coordinates dict with latitude/longitude, or None if not found
    """
    if not location:
        return None

    # Normalize the location string for lookup
    normalized = location.strip().lower()

    # Check cache first
    if normalized in _geocode_cache:
        return _geocode_cache[normalized]

    # Look up in the coordinates table
    coords = CITY_COORDINATES.get(normalized)

    if coords is not None:
        result: Coordinates = {"latitude": coords[0], "longitude": coords[1]}
        _geocode_cache[normalized] = result
        return result

    # Cache the miss as well to avoid repeated lookups
    _geocode_cache[normalized] = None
    return None


def clear_cache() -> None:
    """Clear the geocode cache."""
    _geocode_cache.clear()
