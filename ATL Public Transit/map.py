import pandas as pd 
import numpy as np 
import folium 
from folium import plugins


def transit_data():

    # Read data 
    xpress_stop_data = pd.read_csv("Xpress\stops.csv", header = 0)
    marta_stop_data = pd.read_csv("MARTA\stops.csv", header = 0)
    clinc_stop_data = pd.read_csv("CobbLinc\stops.csv", header = 0)
    gwinnett_stop_data = pd.read_csv("Gwinnett County Transit\stops.csv", header = 0)
    douglas_stop_data = pd.read_csv("Connect Douglas\stops.csv", header = 0)

    # Find coordinates for bus stops 
    xpress_stop_coords = xpress_stop_data.loc[:, ["stop_id", "stop_name", "stop_lat", "stop_lon"]]
    xpress_stop_coords["carrier"] = "xpress"

    marta_stop_coords = marta_stop_data.loc[:, ["stop_id", "stop_name", "stop_lat", "stop_lon"]]
    marta_stop_coords["carrier"] = "marta"
    
    # Need to reduce the # of stops 
    marta_stop_coords = marta_stop_coords.drop_duplicates(subset = ["stop_name"])

    clinc_stop_coords = clinc_stop_data.loc[:, ["stop_id", "stop_name", "stop_lat", "stop_lon"]]
    clinc_stop_coords["carrier"] = "clinc"
    
    gwinnett_stop_coords = gwinnett_stop_data.loc[:, ["stop_id", "stop_name", "stop_lat", "stop_lon"]]
    gwinnett_stop_coords["carrier"] = "gwinnett"
    
    douglas_stop_coords = douglas_stop_data.loc[:, ["stop_id", "stop_name", "stop_lat", "stop_lon"]]
    douglas_stop_coords["carrier"] = "douglas"

    # Union this data 
    complete_coords = pd.concat([xpress_stop_coords, clinc_stop_coords, gwinnett_stop_coords, douglas_stop_coords])

    # Create map w/focus on Atlanta 
    map = folium.Map((33.753746, -84.386330), zoom_start = 10)

    # # Plot Markers representing the bus stops/rail stations
    # for index, row in complete_coords.iterrows():
    #     if row["carrier"] == "xpress":
    #         folium.Marker(
    #             location = [row["stop_lat"], row["stop_lon"]],
    #             popup = row["stop_name"],
    #             icon = folium.Icon(color = "blue")
    #         ).add_to(map)
    #     elif row["carrier"] == "clinc":
    #         folium.Marker(
    #             location = [row["stop_lat"], row["stop_lon"]],
    #             popup = row["stop_name"],
    #             icon = folium.Icon(color = "gray")
    #         ).add_to(map)
    #     elif row["carrier"] == "gwinnett":
    #         folium.Marker(
    #             location = [row["stop_lat"], row["stop_lon"]],
    #             popup = row["stop_name"],
    #             icon = folium.Icon(color = "purple")
    #         ).add_to(map)
    #     else:
    #         folium.Marker(
    #             location = [row["stop_lat"], row["stop_lon"]],
    #             popup = row["stop_name"],
    #             icon = folium.Icon(color = "green")
    #         ).add_to(map)

    # # Loop through Marta for the stations for now; There are a lot of bus routes that we will have to condense
    for index, row in marta_stop_coords.iterrows():
        folium.Marker(
            location = [row["stop_lat"], row["stop_lon"]], 
            popup = row["stop_name"],
            icon = folium.Icon(color = "red")
        ).add_to(map)



    # Render Map
    map.show_in_browser()

if __name__ == "__main__":
    transit_data()
