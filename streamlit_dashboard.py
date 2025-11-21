# streamlit_dashboard.py (updated to show last_sms)
import streamlit as st
import requests
import time
import pandas as pd
import pydeck as pdk
from datetime import datetime

BACKEND_DEVICES_URL = "https://unfarmed-maximo-overheady.ngrok-free.dev/devices"  # update

st.set_page_config(page_title="Live SOS Tracker", page_icon="🆘", layout="wide")
st.title("🆘 Live SOS Detection Dashboard")
st.write("Real-time locations. Red = distress. 'Last SMS' shows when SMS was last sent (epoch seconds).")

with st.sidebar:
    st.header("Controls")
    refresh_seconds = st.slider("Refresh interval (seconds)", 1, 5, 2)
    show_table = st.checkbox("Show device table", True)
    show_map = st.checkbox("Show map", True)

placeholder = st.empty()

def fetch_devices():
    try:
        r = requests.get(BACKEND_DEVICES_URL, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"__error__": str(e)}

def make_dataframe(devices_dict):
    rows = []
    for device_id, info in devices_dict.items():
        if device_id == "__error__": continue
        lat = info.get("lat")
        lon = info.get("lon")
        ts = info.get("ts")
        distress = bool(info.get("distress", False))
        last_sms = info.get("last_sms")  # epoch seconds or None
        rows.append({
            "device_id": device_id,
            "latitude": lat,
            "longitude": lon,
            "timestamp": ts,
            "distress": distress,
            "last_sms": last_sms
        })
    return pd.DataFrame(rows)

while True:
    data = fetch_devices()
    with placeholder.container():
        if "__error__" in data:
            st.error(f"Error fetching devices: {data['__error__']}")
        else:
            df = make_dataframe(data)
            total = 0 if df.empty else len(df)
            distress_count = 0 if df.empty else int(df['distress'].sum())

            col1, col2, col3 = st.columns([1,1,2])
            col1.metric("Active devices", total)
            col2.metric("Distress alerts", distress_count)
            col3.write("Last update: " + time.strftime("%Y-%m-%d %H:%M:%S"))

            if distress_count > 0:
                st.error(f"⚠️ Distress detected for {distress_count} device(s)!")

            if show_table:
                if df.empty:
                    st.info("No active devices yet.")
                else:
                    # format timestamp and last_sms for readability
                    if "timestamp" in df.columns:
                        try:
                            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
                        except Exception:
                            pass
                    def fmt_last_sms(x):
                        return datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S") if x else ""
                    df["last_sms_readable"] = df["last_sms"].apply(lambda v: fmt_last_sms(v) if pd.notnull(v) else "")

                    styled = df.style.apply(lambda r: ['background-color: salmon' if r['distress'] else '' for _ in r], axis=1)
                    st.subheader("📍 Device list")
                    st.dataframe(styled, use_container_width=True)

            if show_map:
                st.subheader("🗺 Live Map")
                if df.empty:
                    st.info("No coordinates to display.")
                else:
                    df = df.dropna(subset=["latitude", "longitude"])
                    df["latitude"] = pd.to_numeric(df["latitude"])
                    df["longitude"] = pd.to_numeric(df["longitude"])
                    def color_row(is_distress):
                        return [255, 80, 80] if is_distress else [24, 150, 24]
                    df["color"] = df["distress"].apply(color_row)
                    midpoint = (df["latitude"].mean(), df["longitude"].mean())
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=df,
                        get_position=["longitude", "latitude"],
                        get_fill_color="color",
                        get_radius=100,
                        radius_scale=10,
                        radius_min_pixels=5,
                        radius_max_pixels=50,
                        pickable=True
                    )
                    view_state = pdk.ViewState(longitude=midpoint[1], latitude=midpoint[0], zoom=11, pitch=0)
                    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text":"{device_id}\n{latitude}, {longitude}\nDistress: {distress}\nLast SMS: {last_sms}"})
                    st.pydeck_chart(r)

            with st.expander("Raw backend JSON"):
                st.write(data)

    time.sleep(refresh_seconds)
