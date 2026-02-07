"""
Outils météo basés sur l'API Open-Meteo (gratuite, sans clé API).
Fournit la météo du jour et de la semaine à venir.
- get_weather_formatted: formatage direct depuis l'API (sans agent IA).
- WeatherTools: toolkit Agno pour les agents configurables.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from agno.tools import Toolkit, tool

logger = logging.getLogger(__name__)

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Codes WMO simplifiés pour la description en français
WMO_DESCRIPTIONS = {
    0: "Ciel dégagé",
    1: "Principalement dégagé",
    2: "Partiellement nuageux",
    3: "Nuageux",
    45: "Brouillard",
    48: "Brouillard givrant",
    51: "Bruine légère",
    53: "Bruine modérée",
    55: "Bruine dense",
    56: "Bruine verglaçante légère",
    57: "Bruine verglaçante dense",
    61: "Pluie légère",
    63: "Pluie modérée",
    65: "Pluie forte",
    66: "Pluie verglaçante légère",
    67: "Pluie verglaçante forte",
    71: "Chute de neige légère",
    73: "Chute de neige modérée",
    75: "Chute de neige forte",
    77: "Grains de neige",
    80: "Averses de pluie légères",
    81: "Averses de pluie modérées",
    82: "Averses de pluie violentes",
    85: "Averses de neige légères",
    86: "Averses de neige fortes",
    95: "Orage",
    96: "Orage avec grêle légère",
    99: "Orage avec grêle forte",
}


def _weather_desc(code: int) -> str:
    return WMO_DESCRIPTIONS.get(code, f"Conditions (code {code})")


def _geocode(location: str) -> Optional[Dict[str, Any]]:
    """Retourne le premier résultat de géocodage Open-Meteo pour une localisation."""
    try:
        r = requests.get(
            GEOCODING_URL,
            params={"name": location.strip(), "count": 1, "language": "fr"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if not results:
            return None
        return results[0]
    except Exception as e:
        logger.warning("[WeatherTools] Géocodage échoué pour %s: %s", location, e)
        return None


def _fetch_forecast(lat: float, lon: float, timezone: str = "auto") -> Optional[Dict[str, Any]]:
    """Récupère la prévision 7 jours via Open-Meteo."""
    try:
        r = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "timezone": timezone,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("[WeatherTools] Prévision échouée: %s", e)
        return None


def _format_date_short(iso_date: str) -> str:
    """Formate une date ISO en 'Lundi 2 février'."""
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d")
        return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"
    except Exception:
        return iso_date


def get_weather_formatted(location: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Récupère la météo du jour et de la semaine à venir et la retourne en texte formaté.
    Aucun agent IA : formatage direct à partir des réponses Open-Meteo.

    Returns:
        (texte_formaté, données_brutes) ou (message_erreur, None)
    """
    if not location or not location.strip():
        return "Indiquez une ville ou un lieu (ex: Paris, Lyon).", None

    geo = _geocode(location.strip())
    if not geo:
        return f"Lieu non trouvé : {location}. Essayez un autre nom de ville.", None

    lat = geo["latitude"]
    lon = geo["longitude"]
    tz = geo.get("timezone", "auto")
    name = geo.get("name", location)
    country = geo.get("country", "")
    lieu = f"{name}, {country}" if country else name

    forecast = _fetch_forecast(lat, lon, tz)
    if not forecast or "daily" not in forecast:
        return "Impossible de récupérer la prévision pour ce lieu.", None

    daily = forecast["daily"]
    times: List[str] = daily.get("time", [])
    max_t: List[Optional[float]] = daily.get("temperature_2m_max", [])
    min_t: List[Optional[float]] = daily.get("temperature_2m_min", [])
    precip: List[Optional[float]] = daily.get("precipitation_sum", [])
    codes: List[int] = daily.get("weathercode", [])

    lines: List[str] = [f"Météo à {lieu}", "", f"**Aujourd'hui ({_format_date_short(times[0])})**"]
    if times:
        t_max = max_t[0] if max_t else None
        t_min = min_t[0] if min_t else None
        p = precip[0] if precip else None
        w = _weather_desc(codes[0]) if codes else ""
        parts = []
        if t_max is not None:
            parts.append(f"{t_max:.0f}°C max")
        if t_min is not None:
            parts.append(f"{t_min:.0f}°C min")
        if w:
            parts.append(w)
        if p is not None and p > 0:
            parts.append(f"{p:.1f} mm de précipitations")
        lines.append(", ".join(parts) if parts else "—")
        lines.append("")

    for i in range(1, min(len(times), 8)):
        t_max = max_t[i] if i < len(max_t) else None
        t_min = min_t[i] if i < len(min_t) else None
        p = precip[i] if i < len(precip) else None
        w = _weather_desc(codes[i]) if i < len(codes) else ""
        parts = []
        if t_max is not None:
            parts.append(f"{t_max:.0f}°C max")
        if t_min is not None:
            parts.append(f"{t_min:.0f}°C min")
        if w:
            parts.append(w)
        if p is not None and p > 0:
            parts.append(f"{p:.1f} mm")
        lines.append(f"**{_format_date_short(times[i])}** : " + (", ".join(parts) if parts else "—"))

    raw = {
        "lieu": lieu,
        "daily": [
            {
                "date": times[i],
                "temperature_max_c": max_t[i] if i < len(max_t) else None,
                "temperature_min_c": min_t[i] if i < len(min_t) else None,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "temps": _weather_desc(codes[i]) if i < len(codes) else None,
            }
            for i in range(min(len(times), 8))
        ],
    }
    return "\n".join(lines), raw


class WeatherTools(Toolkit):
    """
    Toolkit météo (Open-Meteo, gratuit sans clé).
    Donne la météo du jour et de la semaine à venir pour une localisation.
    """

    def __init__(self, **kwargs):
        super().__init__(name="weather_tools", tools=[self.get_weather_forecast], **kwargs)

    @tool(
        description="Récupère la météo du jour et de la semaine à venir pour une ville ou un lieu. Utilise cet outil avec le nom de la ville (ex: Paris, Lyon, Londres)."
    )
    def get_weather_forecast(self, location: str) -> str:
        """
        Météo du jour et des 7 prochains jours pour une localisation.

        Args:
            location: Ville ou lieu (ex: Paris, Lyon, Bordeaux, Londres).

        Returns:
            JSON avec météo du jour et prévisions quotidiennes (températures, précipitations, temps).
        """
        if not location or not location.strip():
            return json.dumps({"error": "Indiquez une ville ou un lieu (ex: Paris)."}, ensure_ascii=False)

        geo = _geocode(location.strip())
        if not geo:
            return json.dumps(
                {"error": f"Lieu non trouvé: {location}. Essayez un autre nom de ville."},
                ensure_ascii=False,
            )

        lat = geo["latitude"]
        lon = geo["longitude"]
        tz = geo.get("timezone", "auto")
        name = geo.get("name", location)
        country = geo.get("country", "")

        forecast = _fetch_forecast(lat, lon, tz)
        if not forecast or "daily" not in forecast:
            return json.dumps(
                {"error": "Impossible de récupérer la prévision pour ce lieu."},
                ensure_ascii=False,
            )

        daily = forecast["daily"]
        times: List[str] = daily.get("time", [])
        max_t: List[Optional[float]] = daily.get("temperature_2m_max", [])
        min_t: List[Optional[float]] = daily.get("temperature_2m_min", [])
        precip: List[Optional[float]] = daily.get("precipitation_sum", [])
        codes: List[int] = daily.get("weathercode", [])

        days_list: List[Dict[str, Any]] = []
        for i in range(min(len(times), 8)):  # aujourd'hui + 7 jours
            days_list.append({
                "date": times[i],
                "temperature_max_c": max_t[i] if i < len(max_t) else None,
                "temperature_min_c": min_t[i] if i < len(min_t) else None,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "temps": _weather_desc(codes[i]) if i < len(codes) else None,
            })

        result = {
            "lieu": f"{name}, {country}" if country else name,
            "aujourd_hui": days_list[0] if days_list else None,
            "semaine": days_list,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
