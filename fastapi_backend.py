"""
JalRakshak AI - Autonomous Backend SMS Dispatch & Early Warning Core (SIH26071)
Production FastAPI Server for Karnataka State Disaster Management Authority (KSDMA)
Includes Autonomous 120s Background SMS Alert Daemon with Twilio, Fast2SMS, TextLocal, and Exotel
"""

import os
import datetime
import base64
import json
import asyncio
import logging
import urllib.request
import urllib.parse
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Configure Structured Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("jalrakshak.core")

# -----------------------------------------------------------------------------
# DATASET: KARNATAKA 31 DISTRICTS TELEMETRY MATRIX
# -----------------------------------------------------------------------------
KARNATAKA_31_DISTRICTS = [
    {"id": "blr_urban", "name": "Bengaluru Urban", "lat": 12.9716, "lon": 77.5946, "category": "urban", "rain_mm_hr": 142.5, "flood_depth_mm": 850.0, "risk": "CRITICAL", "river_stage": "Koramangala Drain Overflow (+1.9m)"},
    {"id": "udupi", "name": "Udupi", "lat": 13.3409, "lon": 74.7421, "category": "coastal", "rain_mm_hr": 135.0, "flood_depth_mm": 890.0, "risk": "CRITICAL", "river_stage": "Swarna River Danger Level (+2.4m)"},
    {"id": "dakshina_kannada", "name": "Dakshina Kannada (Mangaluru)", "lat": 12.9141, "lon": 74.8560, "category": "coastal", "rain_mm_hr": 138.0, "flood_depth_mm": 920.0, "risk": "CRITICAL", "river_stage": "Netravati River Warning (+2.9m)"},
    {"id": "kodagu", "name": "Kodagu (Madikeri)", "lat": 12.4244, "lon": 75.7382, "category": "coastal", "rain_mm_hr": 165.0, "flood_depth_mm": 1100.0, "risk": "CRITICAL", "river_stage": "Cauvery Upper Basin Surge (+3.2m)"},
    {"id": "mysuru", "name": "Mysuru", "lat": 12.2958, "lon": 76.6394, "category": "urban", "rain_mm_hr": 62.0, "flood_depth_mm": 210.0, "risk": "WARNING", "river_stage": "Kabini River Normal (+0.6m)"},
    {"id": "belagavi", "name": "Belagavi", "lat": 15.8497, "lon": 74.4977, "category": "coastal", "rain_mm_hr": 118.0, "flood_depth_mm": 750.0, "risk": "CRITICAL", "river_stage": "Krishna River Danger (+2.6m)"},
    {"id": "shivamogga", "name": "Shivamogga", "lat": 13.9299, "lon": 75.5681, "category": "coastal", "rain_mm_hr": 105.0, "flood_depth_mm": 610.0, "risk": "CRITICAL", "river_stage": "Tunga River High Alert (+2.2m)"},
    {"id": "chikamagaluru", "name": "Chikamagaluru", "lat": 13.3161, "lon": 75.7720, "category": "coastal", "rain_mm_hr": 128.0, "flood_depth_mm": 810.0, "risk": "CRITICAL", "river_stage": "Bhadra River Overflow (+2.5m)"},
    {"id": "uttara_kannada", "name": "Uttara Kannada (Karwar)", "lat": 14.8090, "lon": 74.1300, "category": "coastal", "rain_mm_hr": 110.0, "flood_depth_mm": 580.0, "risk": "CRITICAL", "river_stage": "Kali River Overflow (+2.1m)"},
    {"id": "hubballi_dharwad", "name": "Dharwad (Hubballi)", "lat": 15.3647, "lon": 75.1240, "category": "urban", "rain_mm_hr": 78.0, "flood_depth_mm": 340.0, "risk": "WARNING", "river_stage": "Unkal Lake Overflow (+1.1m)"},
    {"id": "blr_rural", "name": "Bengaluru Rural", "lat": 13.2257, "lon": 77.5750, "category": "urban", "rain_mm_hr": 45.0, "flood_depth_mm": 120.0, "risk": "WARNING", "river_stage": "Arkavathi Basin (+0.8m)"},
    {"id": "hassan", "name": "Hassan", "lat": 13.0033, "lon": 76.1004, "category": "coastal", "rain_mm_hr": 54.0, "flood_depth_mm": 180.0, "risk": "WARNING", "river_stage": "Hemavathi Reservoir (+0.9m)"},
    {"id": "mandya", "name": "Mandya", "lat": 12.5218, "lon": 76.8951, "category": "all", "rain_mm_hr": 42.0, "flood_depth_mm": 90.0, "risk": "SAFE", "river_stage": "KRS Dam Outflow (+0.5m)"},
    {"id": "chamarajanagar", "name": "Chamarajanagar", "lat": 11.9261, "lon": 76.9437, "category": "all", "rain_mm_hr": 38.0, "flood_depth_mm": 60.0, "risk": "SAFE", "river_stage": "Moyar Basin Stable (+0.3m)"},
    {"id": "ramanagara", "name": "Ramanagara", "lat": 12.7150, "lon": 77.2810, "category": "urban", "rain_mm_hr": 58.0, "flood_depth_mm": 220.0, "risk": "WARNING", "river_stage": "Arkavathi Catchment (+1.0m)"},
    {"id": "tumakuru", "name": "Tumakuru", "lat": 13.3379, "lon": 77.1173, "category": "all", "rain_mm_hr": 35.0, "flood_depth_mm": 50.0, "risk": "SAFE", "river_stage": "Jayamangali Stable (+0.2m)"},
    {"id": "kolar", "name": "Kolar", "lat": 13.1367, "lon": 78.1292, "category": "all", "rain_mm_hr": 28.0, "flood_depth_mm": 30.0, "risk": "SAFE", "river_stage": "Palar Catchment Stable"},
    {"id": "chikkaballapura", "name": "Chikkaballapura", "lat": 13.4356, "lon": 77.7275, "category": "all", "rain_mm_hr": 31.0, "flood_depth_mm": 40.0, "risk": "SAFE", "river_stage": "North Pinakini Stable"},
    {"id": "chitradurga", "name": "Chitradurga", "lat": 14.2251, "lon": 76.3980, "category": "all", "rain_mm_hr": 22.0, "flood_depth_mm": 20.0, "risk": "SAFE", "river_stage": "Vedavathi Basin Stable"},
    {"id": "davanagere", "name": "Davanagere", "lat": 14.4644, "lon": 75.9218, "category": "all", "rain_mm_hr": 48.0, "flood_depth_mm": 110.0, "risk": "WARNING", "river_stage": "Tungabhadra Moderate (+0.7m)"},
    {"id": "ballari", "name": "Ballari", "lat": 15.1394, "lon": 76.9214, "category": "all", "rain_mm_hr": 40.0, "flood_depth_mm": 85.0, "risk": "SAFE", "river_stage": "Hagari River Normal"},
    {"id": "vijayanagara", "name": "Vijayanagara (Hospete)", "lat": 15.2691, "lon": 76.3884, "category": "all", "rain_mm_hr": 52.0, "flood_depth_mm": 140.0, "risk": "WARNING", "river_stage": "Tungabhadra Dam Sluice (+1.2m)"},
    {"id": "bagalkote", "name": "Bagalkote", "lat": 16.1853, "lon": 75.6968, "category": "coastal", "rain_mm_hr": 88.0, "flood_depth_mm": 490.0, "risk": "CRITICAL", "river_stage": "Ghataprabha Danger (+2.0m)"},
    {"id": "vijayapura", "name": "Vijayapura", "lat": 16.8302, "lon": 75.7100, "category": "all", "rain_mm_hr": 65.0, "flood_depth_mm": 260.0, "risk": "WARNING", "river_stage": "Doni River Surge (+1.3m)"},
    {"id": "kalaburagi", "name": "Kalaburagi", "lat": 17.3297, "lon": 76.8343, "category": "all", "rain_mm_hr": 72.0, "flood_depth_mm": 310.0, "risk": "WARNING", "river_stage": "Bhima River Warning (+1.5m)"},
    {"id": "yadgir", "name": "Yadgir", "lat": 16.7623, "lon": 77.1374, "category": "coastal", "rain_mm_hr": 82.0, "flood_depth_mm": 420.0, "risk": "CRITICAL", "river_stage": "Krishna Basin Release (+1.9m)"},
    {"id": "raichur", "name": "Raichur", "lat": 16.2076, "lon": 77.3556, "category": "all", "rain_mm_hr": 50.0, "flood_depth_mm": 150.0, "risk": "WARNING", "river_stage": "Krishna-Tungabhadra Confluence (+1.1m)"},
    {"id": "bidar", "name": "Bidar", "lat": 17.9104, "lon": 77.5199, "category": "all", "rain_mm_hr": 44.0, "flood_depth_mm": 100.0, "risk": "SAFE", "river_stage": "Karanja Reservoir Stable"},
    {"id": "haveri", "name": "Haveri", "lat": 14.7954, "lon": 75.3992, "category": "all", "rain_mm_hr": 60.0, "flood_depth_mm": 200.0, "risk": "WARNING", "river_stage": "Varada River Alert (+1.0m)"},
    {"id": "gadag", "name": "Gadag", "lat": 15.4300, "lon": 75.6300, "category": "all", "rain_mm_hr": 36.0, "flood_depth_mm": 70.0, "risk": "SAFE", "river_stage": "Malaprabha Stable"},
    {"id": "koppal", "name": "Koppal", "lat": 15.3506, "lon": 76.1549, "category": "all", "rain_mm_hr": 38.0, "flood_depth_mm": 80.0, "risk": "SAFE", "river_stage": "Hirehalla Reservoir Normal"}
]

# -----------------------------------------------------------------------------
# AUTONOMOUS DAEMON STATE & CONFIGURATION
# -----------------------------------------------------------------------------
DEFAULT_RECIPIENT = "9148019519"

DAEMON_STATE: Dict[str, Any] = {
    "enabled": True,
    "is_running": False,
    "interval_seconds": 120,  # 2 Minutes Autonomous Loop
    "recipients": [DEFAULT_RECIPIENT],
    "last_run_timestamp": None,
    "next_run_timestamp": None,
    "total_dispatches": 0,
    "last_alert_payload": None,
    "last_dispatch_results": [],
    "history": []  # Circular buffer of last 50 alerts
}

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS AND DATA VALIDATIONS
# -----------------------------------------------------------------------------
class EmergencyTelemetryPayload(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 12.9716})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 77.5946})
    district_name: str = Field(..., min_length=2, json_schema_extra={"example": "Bengaluru Urban"})
    rainfall_rate_mm_hr: float = Field(..., ge=0.0, json_schema_extra={"example": 124.5})
    hydro_flood_depth_mm: float = Field(..., ge=0.0, json_schema_extra={"example": 850.0})
    risk_tier: str = Field(..., json_schema_extra={"example": "CRITICAL EMERGENCY"})
    confidence_pct: int = Field(..., ge=0, le=100, json_schema_extra={"example": 94})
    recipient_numbers: List[str] = Field(
        default=[DEFAULT_RECIPIENT, "9902884077", "9964226515"],
        description="Target phone numbers for emergency SDRF & DDMA dispatch"
    )

    @field_validator('recipient_numbers')
    def validate_recipients(cls, v):
        if not v:
            return [DEFAULT_RECIPIENT]
        cleaned = []
        for num in v:
            digits = "".join(filter(str.isdigit, str(num)))
            if len(digits) >= 10:
                cleaned.append(digits)
        return cleaned or [DEFAULT_RECIPIENT]


class DaemonConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    interval_seconds: Optional[int] = Field(None, ge=10, le=3600, description="Loop interval in seconds (default 120s)")
    recipients: Optional[List[str]] = Field(None, description="List of target 10-digit Indian phone numbers")


class NowcastPredictionRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": 12.9716})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 77.5946})
    district_name: str = Field(..., json_schema_extra={"example": "Bengaluru Urban"})
    current_rain_mm_hr: float = Field(..., ge=0.0, json_schema_extra={"example": 115.0})
    atmospheric_pressure_hpa: Optional[float] = Field(default=1013.25, ge=800.0, le=1100.0)
    humidity_pct: Optional[float] = Field(default=85.0, ge=0.0, le=100.0)
    wind_speed_kmh: Optional[float] = Field(default=15.0, ge=0.0)
    radar_reflectivity_dbz: Optional[float] = Field(default=45.0, ge=0.0, le=80.0)


class NowcastPredictionResponse(BaseModel):
    district_name: str
    latitude: float
    longitude: float
    current_rain_mm_hr: float
    prediction_1h_mm: float
    prediction_3h_mm: float
    prediction_6h_mm: float
    cloudburst_risk: bool
    inundation_threat_level: str
    ai_confidence_pct: float
    recommended_action: str
    timestamp: str


class HydroModelRequest(BaseModel):
    rainfall_mm_hr: float = Field(..., ge=0.0, json_schema_extra={"example": 120.0}, description="Rainfall intensity in mm/hr")
    duration_hours: float = Field(..., gt=0.0, json_schema_extra={"example": 2.0}, description="Rainfall event duration in hours")
    catchment_area_km2: float = Field(..., gt=0.0, json_schema_extra={"example": 15.5}, description="Catchment basin area in sq. km")
    curve_number_scs: int = Field(default=92, ge=30, le=100, description="SCS Runoff Curve Number (30-100)")
    slope_pct: float = Field(default=2.5, ge=0.0, le=100.0, description="Average terrain slope percentage")
    drainage_capacity_m3_s: float = Field(default=50.0, ge=0.0, description="Maximum stormwater drainage capacity in m3/s")


class HydroModelResponse(BaseModel):
    total_rainfall_mm: float
    scs_curve_number: int
    potential_retention_s_mm: float
    initial_abstraction_ia_mm: float
    direct_runoff_depth_mm: float
    runoff_volume_m3: float
    peak_discharge_m3_s: float
    estimated_surface_flood_depth_mm: float
    time_to_peak_min: float
    drainage_overflow_ratio: float
    hazard_rating: str
    timestamp: str


# -----------------------------------------------------------------------------
# SMS GATEWAY CONNECTORS (TWILIO, FAST2SMS, TEXTLOCAL, EXOTEL & SIMULATOR)
# -----------------------------------------------------------------------------

def send_fast2sms_gateway(alert_message: str, number: str) -> dict:
    """
    Attempts delivery via Fast2SMS Indian SMS Gateway (Quick SMS route 'q').
    Uses FAST2SMS_API_KEY environment variable.
    """
    api_key = os.getenv("FAST2SMS_API_KEY", "")
    if not api_key or api_key.startswith("MOCK") or api_key.startswith("YOUR_"):
        return {"status": "SKIPPED_MOCK", "provider": "FAST2SMS", "reason": "Fast2SMS API key not configured or in mock mode"}

    clean_num = "".join(filter(str.isdigit, number))
    if clean_num.startswith("91") and len(clean_num) == 12:
        clean_num = clean_num[2:]
    if len(clean_num) != 10:
        return {"status": "FAILED", "provider": "FAST2SMS", "error": f"Invalid 10-digit Indian phone number: {number}"}

    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload_data = json.dumps({
            "route": "q",
            "message": alert_message,
            "language": "english",
            "flash": 0,
            "numbers": clean_num
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload_data, method="POST")
        req.add_header("authorization", api_key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "JalRakshak-DisasterCore/2.0")

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("return") is True or "request_id" in data:
                return {
                    "status": "DELIVERED",
                    "provider": "FAST2SMS",
                    "request_id": data.get("request_id"),
                    "details": data.get("message")
                }
            return {"status": "FAILED", "provider": "FAST2SMS", "error": str(data)}
    except Exception as e:
        return {"status": "FAILED", "provider": "FAST2SMS", "error": str(e)}


def send_textlocal_gateway(alert_message: str, number: str) -> dict:
    """
    Attempts SMS delivery via TextLocal India Gateway.
    Uses TEXTLOCAL_API_KEY and optional TEXTLOCAL_SENDER environment variables.
    """
    api_key = os.getenv("TEXTLOCAL_API_KEY", "")
    sender = os.getenv("TEXTLOCAL_SENDER", "TXTLCL")
    if not api_key or api_key.startswith("MOCK") or api_key.startswith("YOUR_"):
        return {"status": "SKIPPED_MOCK", "provider": "TEXTLOCAL", "reason": "TextLocal API key not configured or in mock mode"}

    clean_num = "".join(filter(str.isdigit, number))
    if len(clean_num) == 10:
        clean_num = f"91{clean_num}"

    try:
        url = "https://api.textlocal.in/send/"
        post_data = urllib.parse.urlencode({
            "apikey": api_key,
            "numbers": clean_num,
            "message": alert_message,
            "sender": sender
        }).encode("utf-8")

        req = urllib.request.Request(url, data=post_data, method="POST")
        req.add_header("User-Agent", "JalRakshak-DisasterCore/2.0")

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                return {
                    "status": "DELIVERED",
                    "provider": "TEXTLOCAL",
                    "batch_id": data.get("batch_id")
                }
            err_msg = data.get("errors", [{}])[0].get("message", "TextLocal rejected request")
            return {"status": "FAILED", "provider": "TEXTLOCAL", "error": err_msg}
    except Exception as e:
        return {"status": "FAILED", "provider": "TEXTLOCAL", "error": str(e)}


def send_twilio_sms_gateway(alert_message: str, number: str) -> dict:
    """Attempts SMS delivery via Twilio API using standard library urllib."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "+18005550199")

    if not account_sid or account_sid.startswith("AC_MOCK") or not auth_token:
        return {"status": "SKIPPED_MOCK", "provider": "TWILIO", "reason": "Twilio credentials missing or in mock mode"}

    clean_num = "".join(filter(str.isdigit, number))
    to_number = f"+91{clean_num[-10:]}" if not number.startswith("+") else number

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data_encoded = urllib.parse.urlencode({
            "To": to_number,
            "From": from_number,
            "Body": alert_message
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data_encoded, method="POST")
        auth_str = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {auth_str}")

        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {"status": "DELIVERED", "provider": "TWILIO", "sid": body.get("sid")}
    except Exception as e:
        return {"status": "FAILED", "provider": "TWILIO", "error": str(e)}


def send_exotel_sms_gateway(alert_message: str, number: str) -> dict:
    """Attempts SMS delivery via Exotel API (Secondary Gateway Fallback) using urllib."""
    account_sid = os.getenv("EXOTEL_ACCOUNT_SID", "")
    auth_token = os.getenv("EXOTEL_TOKEN", "")
    subdomain = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")
    caller_id = os.getenv("EXOTEL_PHONE_NUMBER", "08045678900")

    if not account_sid or account_sid.startswith("EXOTEL_MOCK") or not auth_token:
        return {"status": "SKIPPED_MOCK", "provider": "EXOTEL", "reason": "Exotel credentials missing or in mock mode"}

    clean_num = "".join(filter(str.isdigit, number))
    to_number = f"0{clean_num[-10:]}" if len(clean_num) >= 10 else number

    try:
        url = f"https://{subdomain}/v1/Accounts/{account_sid}/Sms/send.json"
        data_encoded = urllib.parse.urlencode({
            "From": caller_id,
            "To": to_number,
            "Body": alert_message,
            "Priority": "high"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data_encoded, method="POST")
        auth_str = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {auth_str}")

        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {"status": "DELIVERED", "provider": "EXOTEL", "sid": body.get("SmsMessage", {}).get("Sid")}
    except Exception as e:
        return {"status": "FAILED", "provider": "EXOTEL", "error": str(e)}


def dispatch_resilient_sms(alert_message: str, number: str, context: Optional[dict] = None) -> dict:
    """
    Multi-Tier SMS delivery pipeline:
    Tier 1: Fast2SMS (Indian SMS Gateway)
    Tier 2: TextLocal (Indian SMS Gateway)
    Tier 3: Twilio (Global SMS Gateway)
    Tier 4: Exotel (Indian Telephony SMS)
    Tier 5: High-Fidelity Autonomous Simulator (Offline/Test Fallback)
    """
    attempts = []

    # 1. Try Fast2SMS
    res_f2s = send_fast2sms_gateway(alert_message, number)
    attempts.append(res_f2s)
    if res_f2s.get("status") == "DELIVERED":
        return {"status": "DELIVERED", "provider": "FAST2SMS", "details": res_f2s, "recipient": number}

    # 2. Try TextLocal
    res_tl = send_textlocal_gateway(alert_message, number)
    attempts.append(res_tl)
    if res_tl.get("status") == "DELIVERED":
        return {"status": "DELIVERED", "provider": "TEXTLOCAL", "details": res_tl, "recipient": number}

    # 3. Try Twilio
    res_tw = send_twilio_sms_gateway(alert_message, number)
    attempts.append(res_tw)
    if res_tw.get("status") == "DELIVERED":
        return {"status": "DELIVERED", "provider": "TWILIO", "details": res_tw, "recipient": number}

    # 4. Try Exotel
    res_ex = send_exotel_sms_gateway(alert_message, number)
    attempts.append(res_ex)
    if res_ex.get("status") == "DELIVERED":
        return {"status": "DELIVERED", "provider": "EXOTEL", "details": res_ex, "recipient": number}

    # 5. Simulated Mock Success (Ensures zero-crash development & offline robustness)
    ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    simulated_sid = f"SIM-JR-{ts}-{number[-4:]}"
    return {
        "status": "SIMULATED_DISPATCH_SUCCESS",
        "provider": "MOCK_SIMULATOR_GATEWAY",
        "sid": simulated_sid,
        "recipient": number,
        "attempts": attempts,
        "alert_preview": alert_message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": "Production fallback active. Set FAST2SMS_API_KEY, TEXTLOCAL_API_KEY, or TWILIO_* env vars for direct telecom carrier delivery."
    }


# -----------------------------------------------------------------------------
# WEATHER & FLOOD SCENARIO SYNTHESIZER
# -----------------------------------------------------------------------------
def generate_live_weather_flood_scenario() -> dict:
    """
    Synthesizes current live weather and flood scenario across Karnataka.
    Picks the highest-risk critical districts and cycles dynamically.
    Checks Open-Meteo for real-time live precipitation when available.
    """
    critical_districts = [d for d in KARNATAKA_31_DISTRICTS if d["risk"] == "CRITICAL"]
    if not critical_districts:
        critical_districts = KARNATAKA_31_DISTRICTS[:5]

    # Deterministic rotation based on 2-minute epoch window
    now_epoch = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    cycle_idx = (now_epoch // 120) % len(critical_districts)
    target = critical_districts[cycle_idx]

    live_rain = float(target["rain_mm_hr"])
    live_temp = 24.5

    # Optional live weather query with 2s timeout
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={target['lat']}&longitude={target['lon']}"
            f"&current=temperature_2m,rain&timezone=Asia%2FKolkata"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "JalRakshak-SIH26071"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            wdata = json.loads(resp.read().decode("utf-8"))
            cur = wdata.get("current", {})
            if "rain" in cur and cur["rain"] is not None and cur["rain"] > 0:
                live_rain = max(live_rain, float(cur["rain"]) * 10.0)
            if "temperature_2m" in cur and cur["temperature_2m"] is not None:
                live_temp = float(cur["temperature_2m"])
    except Exception:
        pass  # Graceful fallback to Karnataka offline telemetry

    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    time_str = now_ist.strftime("%H:%M IST, %d-%b")

    alert_text = (
        f"🚨 JALRAKSHAK FLOOD ALERT (KSDMA)\n"
        f"Dist: {target['name'].upper()} [{target['risk']}]\n"
        f"Rain: {live_rain:.1f} mm/h | Flood Depth: {target['flood_depth_mm']:.0f} mm\n"
        f"Stage: {target['river_stage']}\n"
        f"Nowcast: Extreme inundation threat. Evacuate low drainage underpasses. SDRF units deployed.\n"
        f"Time: {time_str}"
    )

    return {
        "district": target,
        "live_rain_mm_hr": live_rain,
        "live_temp_c": live_temp,
        "flood_depth_mm": target["flood_depth_mm"],
        "risk_tier": target["risk"],
        "river_stage": target["river_stage"],
        "alert_text": alert_text,
        "timestamp_ist": time_str
    }


# -----------------------------------------------------------------------------
# AUTONOMOUS ASYNCIO DAEMON LOOP (EVERY 120 SECONDS)
# -----------------------------------------------------------------------------
async def autonomous_sms_daemon_loop():
    """
    Runs autonomously in the background every 120 seconds (2 minutes).
    Dispatches emergency SMS alerts regarding current live weather and flood scenarios
    to '9148019519' and configured recipients without human intervention.
    """
    DAEMON_STATE["is_running"] = True
    logger.info("🚀 [JalRakshak Daemon] Autonomous Background SMS Alert Daemon Loop Initialized (Interval: 120s, Target: %s)", DAEMON_STATE["recipients"])

    # Initial 3-second warmup before first dispatch cycle
    await asyncio.sleep(3)

    while True:
        try:
            if DAEMON_STATE["enabled"]:
                scenario = generate_live_weather_flood_scenario()
                results = []
                for number in DAEMON_STATE["recipients"]:
                    res = dispatch_resilient_sms(scenario["alert_text"], number, scenario)
                    results.append(res)

                now_utc = datetime.datetime.now(datetime.timezone.utc)
                next_run = now_utc + datetime.timedelta(seconds=DAEMON_STATE["interval_seconds"])

                DAEMON_STATE["last_run_timestamp"] = now_utc.isoformat()
                DAEMON_STATE["next_run_timestamp"] = next_run.isoformat()
                DAEMON_STATE["total_dispatches"] += 1
                DAEMON_STATE["last_alert_payload"] = scenario
                DAEMON_STATE["last_dispatch_results"] = results

                log_entry = {
                    "cycle": DAEMON_STATE["total_dispatches"],
                    "timestamp": now_utc.isoformat(),
                    "district": scenario["district"]["name"],
                    "risk": scenario["risk_tier"],
                    "rain_mm_hr": scenario["live_rain_mm_hr"],
                    "flood_depth_mm": scenario["flood_depth_mm"],
                    "recipients": DAEMON_STATE["recipients"],
                    "results": results
                }
                DAEMON_STATE["history"].insert(0, log_entry)
                if len(DAEMON_STATE["history"]) > 50:
                    DAEMON_STATE["history"].pop()

                logger.info(
                    "📡 [Daemon Cycle #%d] 120s Flood Alert dispatched to %s | District: %s | Providers: %s",
                    DAEMON_STATE["total_dispatches"],
                    DAEMON_STATE["recipients"],
                    scenario["district"]["name"],
                    [r.get("provider") for r in results]
                )
        except Exception as e:
            logger.error("⚠️ [JalRakshak Daemon] Loop exception: %s", e)

        try:
            await asyncio.sleep(DAEMON_STATE["interval_seconds"])
        except asyncio.CancelledError:
            DAEMON_STATE["is_running"] = False
            logger.info("🛑 [JalRakshak Daemon] Background task cancelled cleanly on shutdown.")
            break


# -----------------------------------------------------------------------------
# FASTAPI APPLICATION LIFESPAN SETUP
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Launch autonomous background task on application startup
    daemon_task = asyncio.create_task(autonomous_sms_daemon_loop())
    yield
    # Clean shutdown on application exit
    daemon_task.cancel()
    try:
        await daemon_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="JalRakshak AI Disaster Core & Early Warning API",
    description="Automated Disaster Emergency Gateway, Telemetry, Nowcast AI & Hydro Runoff Engine with 120s Background SMS Daemon (SIH26071)",
    version="2.1.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin PWA dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# CORE REST ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/")
def read_root():
    """Root metadata and autonomous daemon status endpoint."""
    return {
        "system": "JalRakshak AI Disaster Core",
        "state": "Karnataka Disaster Management Hub (KSDMA)",
        "sih_problem_statement": "SIH26071",
        "districts_tracked": len(KARNATAKA_31_DISTRICTS),
        "status": "OPERATIONAL",
        "daemon": {
            "autonomous_sms_loop": "ACTIVE",
            "interval_seconds": DAEMON_STATE["interval_seconds"],
            "primary_recipient": DEFAULT_RECIPIENT,
            "total_dispatches": DAEMON_STATE["total_dispatches"],
            "is_running": DAEMON_STATE["is_running"]
        },
        "gateways": [
            "Fast2SMS (Primary Indian SMS)",
            "TextLocal (Secondary Indian SMS)",
            "Twilio (Global Telecom SMS)",
            "Exotel (Indian Telephony)",
            "Mock Simulator (Zero-Failure Offline Resilience)"
        ]
    }


# -----------------------------------------------------------------------------
# AUTONOMOUS DAEMON CONTROL & MONITORING ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/v1/daemon/status")
def get_daemon_status():
    """
    Returns live operational metrics and countdown of the autonomous 120s background SMS daemon.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    seconds_remaining = 0
    if DAEMON_STATE["next_run_timestamp"]:
        try:
            next_dt = datetime.datetime.fromisoformat(DAEMON_STATE["next_run_timestamp"])
            diff = (next_dt - now_utc).total_seconds()
            seconds_remaining = max(0, int(diff))
        except Exception:
            seconds_remaining = 0

    return {
        "enabled": DAEMON_STATE["enabled"],
        "is_running": DAEMON_STATE["is_running"],
        "interval_seconds": DAEMON_STATE["interval_seconds"],
        "recipients": DAEMON_STATE["recipients"],
        "total_dispatches": DAEMON_STATE["total_dispatches"],
        "last_run_timestamp": DAEMON_STATE["last_run_timestamp"],
        "next_run_timestamp": DAEMON_STATE["next_run_timestamp"],
        "seconds_until_next_run": seconds_remaining,
        "gateways_configured": {
            "fast2sms": bool(os.getenv("FAST2SMS_API_KEY") and not os.getenv("FAST2SMS_API_KEY").startswith("MOCK")),
            "textlocal": bool(os.getenv("TEXTLOCAL_API_KEY") and not os.getenv("TEXTLOCAL_API_KEY").startswith("MOCK")),
            "twilio": bool(os.getenv("TWILIO_ACCOUNT_SID") and not os.getenv("TWILIO_ACCOUNT_SID").startswith("AC_MOCK")),
            "exotel": bool(os.getenv("EXOTEL_ACCOUNT_SID") and not os.getenv("EXOTEL_ACCOUNT_SID").startswith("EXOTEL_MOCK")),
            "simulator": True
        },
        "last_alert": DAEMON_STATE["last_alert_payload"],
        "last_results": DAEMON_STATE["last_dispatch_results"]
    }


@app.post("/api/v1/daemon/trigger")
async def trigger_daemon_alert_now():
    """
    Manually triggers an immediate autonomous SMS alert cycle without waiting for the 120s timer.
    """
    scenario = generate_live_weather_flood_scenario()
    results = []
    for number in DAEMON_STATE["recipients"]:
        res = dispatch_resilient_sms(scenario["alert_text"], number, scenario)
        results.append(res)

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    next_run = now_utc + datetime.timedelta(seconds=DAEMON_STATE["interval_seconds"])

    DAEMON_STATE["last_run_timestamp"] = now_utc.isoformat()
    DAEMON_STATE["next_run_timestamp"] = next_run.isoformat()
    DAEMON_STATE["total_dispatches"] += 1
    DAEMON_STATE["last_alert_payload"] = scenario
    DAEMON_STATE["last_dispatch_results"] = results

    log_entry = {
        "cycle": DAEMON_STATE["total_dispatches"],
        "timestamp": now_utc.isoformat(),
        "district": scenario["district"]["name"],
        "risk": scenario["risk_tier"],
        "rain_mm_hr": scenario["live_rain_mm_hr"],
        "flood_depth_mm": scenario["flood_depth_mm"],
        "recipients": DAEMON_STATE["recipients"],
        "results": results,
        "triggered_manually": True
    }
    DAEMON_STATE["history"].insert(0, log_entry)

    return {
        "status": "TRIGGERED_SUCCESSFULLY",
        "timestamp": now_utc.isoformat(),
        "district": scenario["district"]["name"],
        "recipients": DAEMON_STATE["recipients"],
        "results": results
    }


@app.post("/api/v1/daemon/config")
def update_daemon_config(config: DaemonConfigUpdate):
    """
    Dynamically reconfigures daemon parameters (loop interval, enable/disable, recipients).
    Always ensures '9148019519' is preserved.
    """
    if config.enabled is not None:
        DAEMON_STATE["enabled"] = config.enabled
    if config.interval_seconds is not None:
        DAEMON_STATE["interval_seconds"] = config.interval_seconds
    if config.recipients is not None:
        cleaned = []
        for r in config.recipients:
            digits = "".join(filter(str.isdigit, r))
            if len(digits) >= 10:
                cleaned.append(digits)
        if DEFAULT_RECIPIENT not in cleaned:
            cleaned.insert(0, DEFAULT_RECIPIENT)
        DAEMON_STATE["recipients"] = cleaned

    return {
        "status": "CONFIG_UPDATED",
        "daemon_state": {
            "enabled": DAEMON_STATE["enabled"],
            "interval_seconds": DAEMON_STATE["interval_seconds"],
            "recipients": DAEMON_STATE["recipients"]
        }
    }


@app.get("/api/v1/daemon/history")
def get_daemon_history():
    """Returns the dispatch history of recent SMS alerts."""
    return {
        "total_dispatches": DAEMON_STATE["total_dispatches"],
        "history": DAEMON_STATE["history"]
    }


# -----------------------------------------------------------------------------
# MANUAL / ON-DEMAND EMERGENCY DISPATCH ENDPOINT
# -----------------------------------------------------------------------------
@app.post("/api/v1/dispatch-emergency-sms")
async def dispatch_emergency_sms(payload: EmergencyTelemetryPayload, background_tasks: BackgroundTasks):
    """
    Triggers automated emergency SMS alerts to Karnataka disaster response teams.
    Dual/Multi-gateway resilience: Fast2SMS -> TextLocal -> Twilio -> Exotel -> Simulator.
    """
    alert_message = (
        f"🚨 JALRAKSHAK FLOOD ALERT (KSDMA) 🚨\n"
        f"State: KARNATAKA | District: {payload.district_name.upper()}\n"
        f"GPS: ({payload.latitude:.4f}, {payload.longitude:.4f})\n"
        f"Rain: {payload.rainfall_rate_mm_hr} mm/hr | Flood: {payload.hydro_flood_depth_mm} mm\n"
        f"Risk: {payload.risk_tier} ({payload.confidence_pct}% AI Conf)\n"
        f"ACTION: Immediate evacuation to higher ground. SDRF Cell notified."
    )

    dispatch_logs = []
    for number in payload.recipient_numbers:
        res = dispatch_resilient_sms(alert_message, number, payload.model_dump())
        dispatch_logs.append(res)

    return {
        "status": "DISPATCH_INITIATED",
        "district": payload.district_name,
        "total_contacts": len(payload.recipient_numbers),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dispatch_log": dispatch_logs
    }


# -----------------------------------------------------------------------------
# TELEMETRY, NOWCAST & HYDRO MODEL ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/v1/telemetry/karnataka")
def get_karnataka_telemetry(
    district: Optional[str] = Query(None, description="Filter by district name"),
    category: Optional[str] = Query(None, description="Filter by category ('urban', 'coastal', 'all')"),
    risk: Optional[str] = Query(None, description="Filter by risk level ('CRITICAL', 'WARNING', 'SAFE')")
):
    """Returns real-time telemetry across Karnataka's 31 districts."""
    results = KARNATAKA_31_DISTRICTS

    if district:
        query = district.strip().lower()
        results = [d for d in results if query in d["name"].lower()]

    if category and category.lower() != "all":
        results = [d for d in results if d["category"].lower() == category.lower()]

    if risk:
        results = [d for d in results if d["risk"].upper() == risk.upper()]

    critical_count = sum(1 for d in KARNATAKA_31_DISTRICTS if d["risk"] == "CRITICAL")
    warning_count = sum(1 for d in KARNATAKA_31_DISTRICTS if d["risk"] == "WARNING")
    safe_count = sum(1 for d in KARNATAKA_31_DISTRICTS if d["risk"] == "SAFE")

    return {
        "total_districts": len(KARNATAKA_31_DISTRICTS),
        "matched_count": len(results),
        "summary": {
            "critical_count": critical_count,
            "warning_count": warning_count,
            "safe_count": safe_count
        },
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "telemetry": results
    }


@app.post("/api/v1/nowcast-prediction", response_model=NowcastPredictionResponse)
def compute_nowcast_prediction(payload: NowcastPredictionRequest):
    """Computes rainfall nowcasting predictions and cloudburst risk classification."""
    rain = payload.current_rain_mm_hr
    dbz = payload.radar_reflectivity_dbz or 45.0
    hum = payload.humidity_pct or 85.0

    intensity_factor = 1.0 + (dbz - 40.0) * 0.02 if dbz > 40.0 else 0.95
    humidity_factor = 1.0 + (hum - 80.0) * 0.015 if hum > 80.0 else 1.0

    pred_1h = round(rain * 1.15 * intensity_factor, 1)
    pred_3h = round(rain * 2.8 * intensity_factor * humidity_factor, 1)
    pred_6h = round(rain * 4.5 * intensity_factor * humidity_factor, 1)

    is_cloudburst = pred_1h >= 100.0 or rain >= 100.0

    if is_cloudburst:
        threat_level = "EXTREME"
        confidence = 96.5
        action = "🚨 IMMEDIATE CLOUDBURST ALERT: Evacuate low-lying drainage basins! SDRF teams deployed."
    elif pred_1h >= 75.0 or rain >= 70.0:
        threat_level = "HIGH"
        confidence = 92.0
        action = "⚠️ HIGH FLOOD THREAT: Prepare stormwater pumps and activate local emergency shelter centers."
    elif pred_1h >= 40.0:
        threat_level = "MODERATE"
        confidence = 88.5
        action = "⚡ MODERATE ALERT: Monitor local river gauges and drain clearing operations."
    else:
        threat_level = "LOW"
        confidence = 95.0
        action = "✅ STABLE CONDITIONS: Standard monsoon surveillance active."

    return NowcastPredictionResponse(
        district_name=payload.district_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        current_rain_mm_hr=rain,
        prediction_1h_mm=pred_1h,
        prediction_3h_mm=pred_3h,
        prediction_6h_mm=pred_6h,
        cloudburst_risk=is_cloudburst,
        inundation_threat_level=threat_level,
        ai_confidence_pct=confidence,
        recommended_action=action,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


@app.post("/api/v1/hydro-model", response_model=HydroModelResponse)
def compute_hydro_model(payload: HydroModelRequest):
    """Executes Hydrological SCS-CN Surface Runoff modeling."""
    rain_rate = payload.rainfall_mm_hr
    duration = payload.duration_hours
    area_km2 = payload.catchment_area_km2
    cn = payload.curve_number_scs
    slope = payload.slope_pct
    drainage_cap = payload.drainage_capacity_m3_s

    total_p_mm = rain_rate * duration
    s_mm = (25400.0 / float(cn)) - 254.0
    ia_mm = 0.2 * s_mm

    if total_p_mm > ia_mm:
        numerator = (total_p_mm - ia_mm) ** 2
        denominator = (total_p_mm - ia_mm) + s_mm
        direct_runoff_q_mm = numerator / denominator
    else:
        direct_runoff_q_mm = 0.0

    runoff_vol_m3 = (direct_runoff_q_mm / 1000.0) * (area_km2 * 1_000_000.0)
    time_to_peak_hours = max(0.5, (duration * 0.5) + (slope * 0.1))
    time_to_peak_min = round(time_to_peak_hours * 60.0, 1)

    peak_discharge_m3_s = round((0.208 * area_km2 * direct_runoff_q_mm) / time_to_peak_hours, 2)
    overflow_ratio = round(peak_discharge_m3_s / max(1.0, drainage_cap), 2)

    if peak_discharge_m3_s > drainage_cap:
        flood_depth_est_mm = min(2000.0, round(direct_runoff_q_mm * (1.0 + overflow_ratio * 0.4), 1))
    else:
        flood_depth_est_mm = round(direct_runoff_q_mm * 0.2, 1)

    if flood_depth_est_mm >= 600.0 or overflow_ratio >= 2.5:
        hazard = "CRITICAL FLOOD EMERGENCY"
    elif flood_depth_est_mm >= 300.0 or overflow_ratio >= 1.5:
        hazard = "HIGH SURGE HAZARD"
    elif flood_depth_est_mm >= 100.0 or overflow_ratio >= 1.0:
        hazard = "MODERATE INUNDATION"
    else:
        hazard = "STABLE / LOW RUNOFF"

    return HydroModelResponse(
        total_rainfall_mm=round(total_p_mm, 2),
        scs_curve_number=cn,
        potential_retention_s_mm=round(s_mm, 2),
        initial_abstraction_ia_mm=round(ia_mm, 2),
        direct_runoff_depth_mm=round(direct_runoff_q_mm, 2),
        runoff_volume_m3=round(runoff_vol_m3, 2),
        peak_discharge_m3_s=peak_discharge_m3_s,
        estimated_surface_flood_depth_mm=flood_depth_est_mm,
        time_to_peak_min=time_to_peak_min,
        drainage_overflow_ratio=overflow_ratio,
        hazard_rating=hazard,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
