import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# 1. Page Config
st.set_page_config(page_title="EcoBici Real-Time CDMX", layout="wide")

# --- DATA FETCHING (OPTIMIZED WITH CACHING) ---
@st.cache_data(ttl=60) # Only fetches data once per minute
def load_ecobici_data():
    # URLs for Station Info and Real-time Status
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    
    # Requesting data
    res_info = requests.get(url_info).json()
    df_info = pd.DataFrame(res_info['data']['stations'])
    
    res_status = requests.get(url_status).json()
    df_status = pd.DataFrame(res_status['data']['stations'])
    
    # Merging and cleaning
    df = pd.merge(
        df_info[['station_id', 'name', 'lat', 'lon']], 
        df_status[['station_id', 'num_bikes_available', 'num_docks_available']], 
        on='station_id'
    )
    
    # Normalization Logic
    df['total_cap'] = df['num_bikes_available'] + df['num_docks_available']
    df['availability_pct'] = (df['num_bikes_available'] / df['total_cap']).fillna(0) * 100
    
    return df

# Load the data
try:
    df_ecobici = load_ecobici_data()

    # --- ROW 1: Header ---
    st.title("🚲 EcoBici Station Finder: CDMX")
    st.caption(f"Created by: Edgar Avalos Gauna | Data updated: {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}")

    # Quick Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Stations", len(df_ecobici))
    m2.metric("Available Bikes", df_ecobici['num_bikes_available'].sum())
    m3.metric("Free Docks", df_ecobici['num_docks_available'].sum())

    st.divider()

    # --- ROW 2: Layout ---
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Controls")
        
        # Station Selector
        station_list = sorted(df_ecobici['station_id'].unique(), key=int)
        selected_id = st.selectbox("Select a Station (ID):", ["None"] + station_list)
        
        # Zoom Control
        zoom_val = st.slider("Map Zoom Level:", 10, 18, 13)

        # Highlight logic
        if selected_id != "None":
            selected_row = df_ecobici[df_ecobici['station_id'] == selected_id].iloc[0]
            lat_map, lon_map = selected_row['lat'], selected_row['lon']
            df_ecobici['is_selected'] = df_ecobici['station_id'] == selected_id
            st.success(f"Selected: {selected_row['name']}")
        else:
            lat_map, lon_map = df_ecobici['lat'].mean(), df_ecobici['lon'].mean()
            df_ecobici['is_selected'] = False

        # Legend Note
        st.info("🔵 Blue: Full of bikes\n\n\n🔴 Red: Empty/Few bikes")

    with col2:
        # Markers size logic: Selected station becomes much larger
        df_ecobici['marker_size'] = df_ecobici['is_selected'].map({True: 50, False: 10})

        fig = px.scatter_mapbox(
            df_ecobici,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={
                "station_id": True,
                "num_bikes_available": True,
                "num_docks_available": True,
                "availability_pct": ":.2f",
                "lat": False,
                "lon": False,
                "marker_size": False
            },
            color="availability_pct",
            color_continuous_scale="RdYlBu", # Red (Empty) to Blue (Full)
            size="marker_size",
            size_max=15,
            zoom=zoom_val,
            center={"lat": lat_map, "lon": lon_map},
            height=600,
            labels={"availability_pct": "Availability %"}
        )

        fig.update_layout(
            mapbox_style="carto-positron",
            margin={"r":0,"t":0,"l":0,"b":0}
        )

        st.plotly_chart(fig, use_container_width=True)

    # Optional Table
    with st.expander("View Raw Calculation Data"):
        st.write(df_ecobici[['station_id', 'name', 'availability_pct', 'total_cap']])

except Exception as e:
    st.error(f"Error loading application: {e}")
