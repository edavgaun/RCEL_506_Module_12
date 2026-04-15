import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests

# 1. Setup Page Config
st.set_page_config(layout="wide")

# --- ROW 1: Title and Caption ---
st.title("🚲 EcoBici Station Finder: CDMX")
st.caption("Created by: Edgar Avalos Gauna, 2026")

st.divider()

# --- ROW 2: Controls and Map ---
# Create two columns with different widths (1:3 ratio)
col1, col2 = st.columns([1, 3])

url='https://gbfs.mex.lyftbikes.com/gbfs/gbfs.json'
website_data=requests.get(url).json()
urls=website_data['data']['en']['feeds']
url_data=[u['url'] for u in urls if 'station' in u['url']]
data1=requests.get(url_data[0]).json()
df1=pd.DataFrame(data1['data']['stations'])
st.write(df1.columns)
df1=df1[['station_id', 'lat', 'lon', 'capacity']]
data2=requests.get(url_data[1]).json()
df2=pd.DataFrame(data2['data']['stations'])
df2=df2[['station_id', 'num_bikes_available', 
         'num_bikes_disabled', 'num_docks_available', 
         'num_docks_disabled']]
df=pd.merge(df1, df2, on='station_id')

def bike_share_system_cdmx_plot(station_number):
    # Note: Using your mean logic for centering
    m = folium.Map([df['lat'].mean(), df['lon'].mean()], 
                   zoom_start=13) # We handle size via Streamlit container

    for n in range(len(df)):
        folium.Marker(
            location=[df['lat'][n], df['lon'][n]],
            tooltip=df['station_id'][n],
            icon=folium.Icon(color="red"),
        ).add_to(m)

    temp = df[df['station_id'] == str(station_number)]
    if not temp.empty:
        folium.Marker(
            location=[temp['lat'].iloc[0], temp['lon'].iloc[0]],
            tooltip=f"Selected: {temp['station_id'].values[0]}",
            icon=folium.Icon(icon="cloud", color="blue"),
        ).add_to(m)
    
    return m

with col1:
    st.subheader("Filters")
    # Dropdown menu using station IDs from your dataframe
    station_list = df['station_id'].unique().tolist()
    selected_station = st.selectbox("Select a Station ID:", station_list)
    
    st.info(f"Showing details for Station {selected_station}")

with col2:
    # Generate the map object
    map_object = bike_share_system_cdmx_plot(selected_station)
    
    # Render the map in Streamlit
    # use_container_width=True makes it responsive to the column size
    st_folium(map_object, use_container_width=True, height=500)
