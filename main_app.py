import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="EcoBici Real-Time CDMX", layout="wide")

@st.cache_data(ttl=60)
def load_ecobici_data():
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_information.json"
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"
    res_info = requests.get(url_info).json()
    df_info = pd.DataFrame(res_info['data']['stations'])
    res_status = requests.get(url_status).json()
    df_status = pd.DataFrame(res_status['data']['stations'])
    df = pd.merge(df_info[['station_id', 'name', 'lat', 'lon']], 
                  df_status[['station_id', 'num_bikes_available', 'num_docks_available']], on='station_id')
    df['total_cap'] = df['num_bikes_available'] + df['num_docks_available']
    return df

try:
    df_ecobici = load_ecobici_data()

    # --- ROW 1: Header ---
    st.title("🚲 EcoBici Smart Finder")
    st.caption(f"Updated: {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}")

    # --- ROW 2: Layout ---
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("I want to...")
        status_filter = st.radio(
            "Select your goal:",
            ["Show All", "Find a Bike", "Park my Bike"]
        )

        # 1. Apply Filter First
        if status_filter == "Find a Bike":
            df_filtered = df_ecobici[df_ecobici['num_bikes_available'] > 0].copy()
            # Score = Bikes (Blue = Many bikes)
            df_filtered['display_score'] = (df_filtered['num_bikes_available'] / df_filtered['total_cap']) * 100
            label_score = "% Bikes"
        elif status_filter == "Park my Bike":
            df_filtered = df_ecobici[df_ecobici['num_docks_available'] > 0].copy()
            # Score = Docks (Blue = Many docks)
            df_filtered['display_score'] = (df_filtered['num_docks_available'] / df_filtered['total_cap']) * 100
            label_score = "% Empty Docks"
        else:
            df_filtered = df_ecobici.copy()
            df_filtered['display_score'] = (df_filtered['num_bikes_available'] / df_filtered['total_cap']) * 100
            label_score = "% Bikes"

        # 2. Update Dropdown based on Filtered List
        station_options = ["None"] + sorted(df_filtered['station_id'].unique(), key=int)
        selected_id = st.selectbox("Filtered Station List:", station_options)
        
        zoom_val = st.slider("Map Zoom:", 10, 18, 13)

        # 3. Handle Centering
        if selected_id != "None":
            selected_row = df_filtered[df_filtered['station_id'] == selected_id].iloc[0]
            lat_map, lon_map = selected_row['lat'], selected_row['lon']
            df_filtered['is_selected'] = df_filtered['station_id'] == selected_id
        else:
            lat_map, lon_map = df_filtered['lat'].mean(), df_filtered['lon'].mean()
            df_filtered['is_selected'] = False

    with col2:
        # Define the size of markers
        df_filtered['marker_size'] = df_filtered['is_selected'].map({True: 35, False: 10})

        fig = px.scatter_mapbox(
            df_filtered,
            lat="lat", 
            lon="lon",
            hover_name="name",
            color="display_score",
            color_continuous_scale="RdYlBu", 
            size="marker_size",
            size_max=20, 
            zoom=zoom_val,
            center={"lat": lat_map, "lon": lon_map},
            height=600,
            labels={"display_score": label_score}
        )

        # FIX: We removed the fig.update_traces(marker=dict(line=...)) block 
        # because scatter_mapbox markers do not support the 'line' property.

        fig.update_layout(
            mapbox_style="carto-positron", 
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        st.plotly_chart(fig, use_container_width=True)    # --- TABLE ---
    with st.expander("Detailed Statistics"):
        st.dataframe(
            df_filtered[['station_id', 'name', 'num_bikes_available', 'num_docks_available', 'display_score']]
            .style.background_gradient(cmap='RdYlGn', subset=['display_score'])
            .format({'display_score': '{:.1f}%'}), 
            use_container_width=True
        )

except Exception as e:
    st.error(f"Application Error: {e}")
