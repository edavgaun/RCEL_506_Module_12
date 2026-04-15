import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime

# 1. Page Config
st.set_page_config(page_title="EcoBici Interactive", layout="wide")

@st.cache_data(ttl=60)
def load_ecobici_data():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    res_info = requests.get(url_info).json()
    df_info = pd.DataFrame(res_info['data']['stations'])
    res_status = requests.get(url_status).json()
    df_status = pd.DataFrame(res_status['data']['stations'])
    df = pd.merge(df_info[['station_id', 'name', 'lat', 'lon']], 
                  df_status[['station_id', 'num_bikes_available', 'num_docks_available']], 
                  on='station_id')
    df['total_cap'] = df['num_bikes_available'] + df['num_docks_available']
    df['availability_pct'] = (df['num_bikes_available'] / df['total_cap']).fillna(0) * 100
    return df

try:
    df_ecobici = load_ecobici_data()

    # --- SESSION STATE INITIALIZATION ---
    # This stores the "selected station" so both the map and dropdown can talk to it
    if 'selected_station' not in st.session_state:
        st.session_state.selected_station = "None"

    # --- ROW 1: Header ---
    st.title("🚲 EcoBici Live Sync")
    st.caption(f"Edgar Avalos Gauna | {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}")

    st.divider()

    # --- ROW 2: Layout ---
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Controls")
        
        station_list = ["None"] + sorted(df_ecobici['station_id'].unique(), key=int)
        
        # We link the selectbox to our session state
        selected_id = st.selectbox(
            "Select Station (ID):", 
            station_list, 
            key="station_selector",
            index=station_list.index(st.session_state.selected_station) 
            if st.session_state.selected_station in station_list else 0
        )

        # Update session state if dropdown changes
        st.session_state.selected_station = selected_id

        if st.session_state.selected_station != "None":
            sel_row = df_ecobici[df_ecobici['station_id'] == st.session_state.selected_station].iloc[0]
            st.success(f"📍 {sel_row['name']}")
            st.metric("Bikes Available", sel_row['num_bikes_available'])
        else:
            st.info("Click a marker on the map or use the dropdown.")

    with col2:
        # Define the Map
        center_lat = df_ecobici['lat'].mean()
        center_lon = df_ecobici['lon'].mean()
        
        # If a station is selected, center the map on it
        if st.session_state.selected_station != "None":
            sel_row = df_ecobici[df_ecobici['station_id'] == st.session_state.selected_station].iloc[0]
            center_lat, center_lon = sel_row['lat'], sel_row['lon']

        m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles="cartodbpositron")

        # Add all markers
        for _, row in df_ecobici.iterrows():
            # Color logic
            color = "blue" if row['availability_pct'] > 50 else "red"
            # Special icon if selected
            icon_type = "star" if str(row['station_id']) == str(st.session_state.selected_station) else "info-sign"
            
            folium.Marker(
                location=[row['lat'], row['lon']],
                # Tooltip is what st_folium "reads" when clicked
                tooltip=str(row['station_id']), 
                icon=folium.Icon(color=color, icon=icon_type)
            ).add_to(m)

        # RENDER MAP AND CATCH CLICK
        map_data = st_folium(m, width=900, height=500, use_container_width=True)

        # Logic: If user clicks a marker, update session state and rerun
        if map_data['last_object_clicked_tooltip']:
            clicked_id = map_data['last_object_clicked_tooltip']
            if clicked_id != st.session_state.selected_station:
                st.session_state.selected_station = clicked_id
                st.rerun()

    # --- TABLE ---
    st.subheader("Station Statistics")
    if st.session_state.selected_station != "None":
        display_df = df_ecobici[df_ecobici['station_id'] == st.session_state.selected_station]
    else:
        display_df = df_ecobici

    st.dataframe(display_df, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
