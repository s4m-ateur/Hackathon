import math

# ---- CONFIG (Hackathon-friendly thresholds) ----
THRESH_G = 18.0          # Required impact (m/s²)
THRESH_FLIPS = 2         # Required rotation events
THRESH_TIME = 1.0        # Required chaos duration (seconds)
THRESH_DIST = 15.0       # Required distance travelled (meters)

def calculate_haversine(lat1, lon1, lat2, lon2):
    """Returns distance between two lat/lon points in meters."""
    if None in (lat1, lon1, lat2, lon2):
        return 0.0

    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def analyze_crash_logic(payload):
    """
    Analyzes impact, rotation, duration, and GPS distance to confirm a crash.
    """
    sensor_data = payload.get('sensor_data', [])
    gps_start = payload.get('gps_start', {})
    gps_end = payload.get('gps_end', {})
    start_ts = payload.get('start_ts', 0)
    end_ts = payload.get('end_ts', 0)

    max_g = 0
    flips = 0
    last_vec = None

    # ---- Impact + rotation ----
    for reading in sensor_data:
        x, y, z = reading["x"], reading["y"], reading["z"]

        g = math.sqrt(x**2 + y**2 + z**2)
        if g > max_g:
            max_g = g

        if last_vec:
            dot = x * last_vec["x"] + y * last_vec["y"] + z * last_vec["z"]
            mag_a = math.sqrt(x**2 + y**2 + z**2)
            mag_b = math.sqrt(last_vec["x"]**2 + last_vec["y"]**2 + last_vec["z"]**2)

            if mag_a * mag_b > 0:
                cos_theta = dot / (mag_a * mag_b)
                cos_theta = max(-1.0, min(1.0, cos_theta))
                angle = math.degrees(math.acos(cos_theta))

                if angle > 45:
                    flips += 1

        last_vec = {"x": x, "y": y, "z": z}

    # ---- Duration of chaos ----
    duration = (end_ts - start_ts) / 1000

    # ---- Distance ----
    distance = calculate_haversine(
        gps_start.get("lat"), gps_start.get("lon"),
        gps_end.get("lat"), gps_end.get("lon")
    )

    is_crash = (
        max_g > THRESH_G and
        flips >= THRESH_FLIPS and
        duration > THRESH_TIME and
        distance > THRESH_DIST
    )

    stats = {
        "max_g": round(max_g, 1),
        "flips": flips,
        "dist": round(distance, 1),
        "time": round(duration, 1)
    }

    message = (
        f"CRASH CONFIRMED! G:{stats['max_g']} Flips:{flips} Dist:{stats['dist']}m"
        if is_crash else
        f"Ignored: G:{stats['max_g']} Flips:{flips} Dist:{stats['dist']}m"
    )

    return is_crash, message, stats
