import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# 1. Page Config
st.set_page_config(page_title="EcoBici Real-Time CDMX", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def load_ecobici_data():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    
    res_info = requests.get(url_info).json()
    df_info = pd.DataFrame(res_info['data']['stations'])
    res_status = requests.get(url_status).json()
    df_status = pd.DataFrame(res_status['data']['stations'])
    
    df = pd.merge(
        df_info[['station_id', 'name', 'lat', 'lon']], 
        df_status[['station_id', 'num_bikes_available', 'num_docks_available']], 
        on='station_id'
    )
    
    df['total_cap'] = df['num_bikes_available'] + df['num_docks_available']
    df['availability_pct'] = (df['num_bikes_available'] / df['total_cap']).fillna(0) * 100
    
    return df

try:
    df_ecobici = load_ecobici_data()

    # --- ROW 1: Header ---
    st.title("🚲 EcoBici Station Finder: CDMX")
    st.caption(f"Created by: Edgar Avalos Gauna | Data updated: {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Stations", len(df_ecobici))
    m2.metric("Available Bikes", df_ecobici['num_bikes_available'].sum())
    m3.metric("Free Docks", df_ecobici['num_docks_available'].sum())

    st.divider()

    # --- ROW 2: Layout ---
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Controls")
        
        station_list = ["None"] + sorted(df_ecobici['station_id'].unique(), key=int)
        selected_id = st.selectbox("Select a Station (ID):", station_list)
        
        st.write("---")
        st.markdown("### 🚨 Quick Filters")
        status_filter = st.radio(
            "I am looking to:",
            ["Show All", "Find a Bike (Stations with Bikes)", "Park my Bike (Stations with Docks)"]
        )
    
        # Handle Filtering
        if status_filter == "Find a Bike (Stations with Bikes)":
            df_filtered = df_ecobici[df_ecobici['num_bikes_available'] > 0].copy()
            st.warning(f"Showing {len(df_filtered)} stations with bikes.")
        elif status_filter == "Park my Bike (Stations with Docks)":
            df_filtered = df_ecobici[df_ecobici['num_docks_available'] > 0].copy()
            st.success(f"Showing {len(df_filtered)} stations with docks.")
        else:
            df_filtered = df_ecobici.copy()
    
        zoom_val = st.slider("Map Zoom Level:", 10, 18, 13)

        # Highlight & Center Logic
        if selected_id != "None":
            selected_row = df_ecobici[df_ecobici['station_id'] == selected_id].iloc[0]
            lat_map, lon_map = selected_row['lat'], selected_row['lon']
            # Create the missing 'is_selected' column
            df_filtered['is_selected'] = df_filtered['station_id'] == selected_id
            st.info(f"📍 Selected: {selected_row['name']}")
        else:
            lat_map, lon_map = df_ecobici['lat'].mean(), df_ecobici['lon'].mean()
            df_filtered['is_selected'] = False

    with col2:
        # Create marker size based on selection
        df_filtered['marker_size'] = df_filtered['is_selected'].map({True: 30, False: 10})

        fig = px.scatter_mapbox(
            df_filtered,
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
                "marker_size": False,
                "is_selected": False
            },
            color="availability_pct",
            color_continuous_scale="RdYlBu",
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

    # --- 5. DATA TABLE ---
    with st.expander("View Station Details"):
        display_df = df_ecobici[df_ecobici['station_id'] == selected_id] if selected_id != "None" else df_filtered

        st.dataframe(
            display_df[['station_id', 'name', 'availability_pct', 'num_bikes_available', 'num_docks_available']]
            .style.background_gradient(cmap='RdYlGn', subset=['availability_pct'])
            .format({'availability_pct': '{:.1f}%'}), 
            use_container_width=True
        )

except Exception as e:
    st.error(f"Error loading application: {e}")
