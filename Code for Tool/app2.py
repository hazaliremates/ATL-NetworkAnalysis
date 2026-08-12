import streamlit as st
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
import route2 as RouteFinder
import pandas as pd
from folium.plugins import FloatImage

def safe_parse(x):
    try:
        return float(x)
    except:
        return 0.0

RAIL_STATIONS = {
    station.upper() for station in [
        "HAMILTON E HOLMES STATION", "WEST LAKE STATION", "EAST LAKE STATION",
        "DECATUR STATION", "EDGEWOOD-CANDLER PARK STATION", "GEORGIA STATE STATION",
        "KENSINGTON STATION", "BANKHEAD STATION", "VINE CITY STATION", "ASHBY STATION",
        "AVONDALE STATION", "GWCC-CNN CENTER STATION", "KING MEMORIAL STATION",
        "INDIAN CREEK STATION", "INMAN PARK/REYNOLDS TOWN STATION", "FIVE POINTS STATION",
        "EAST POINT STATION", "BROOKHAVEN-OGLETHORPE STATION", "ARTS CENTER STATION",
        "MIDTOWN STATION", "DUNWOODY STATION", "LINDBERGH CENTER STATION", "AIRPORT STATION",
        "COLLEGE PARK STATION", "GARNETT STATION", "PEACHTREE CENTER STATION", "CHAMBLEE STATION",
        "SANDY SPRINGS STATION", "NORTH SPRINGS STATION", "OAKLAND CITY STATION",
        "WEST END STATION", "BUCKHEAD STATION", "NORTH AVENUE STATION", "DORAVILLE STATION",
        "MEDICAL CENTER STATION", "CIVIC CENTER STATION", "LENOX STATION", "LAKEWOOD-FT MCPHERSON STATION"
    ]
}

COLOR_DICT = {
    "marta": "red",
    "xpress": "blue",
    "clinc": "gray",
    "gwinnett": "purple",
    "douglas": "green"
}

def create_map(start_coords, end_coords, stops, stop_df=None):
    fmap = folium.Map(location=[(start_coords[0] + end_coords[0]) / 2, (start_coords[1] + end_coords[1]) / 2], zoom_start=13)
    folium.Marker(location=start_coords, popup="Start Location", icon=folium.Icon(color="red", icon="star")).add_to(fmap)
    folium.Marker(location=end_coords, popup="Target Location", icon=folium.Icon(color="green", icon="star")).add_to(fmap)

    if stops:
        folium.PolyLine([start_coords, stops[0]["coords"]], color="gray", dash_array="5,10", tooltip="Walk to Start Station").add_to(fmap)
        folium.PolyLine([stops[-1]["coords"], end_coords], color="gray", dash_array="5,10", tooltip="Walk to Destination").add_to(fmap)
    coords_line = [stop["coords"] for stop in stops]
    folium.PolyLine(coords_line, color="black", weight=3, opacity=0.7, tooltip="Transit Path").add_to(fmap)

    if stop_df is not None:
        stop_df["stop_lat"] = stop_df["stop_lat"].apply(safe_parse)
        stop_df["stop_lon"] = stop_df["stop_lon"].apply(safe_parse)
        carrier_map = stop_df.set_index("stop_name")["carrier"].to_dict()
        latlon_map = stop_df.set_index("stop_name")[["stop_lat", "stop_lon"]]
        route_df = pd.DataFrame(stops)
        route_df["carrier"] = route_df["name"].map(carrier_map)
        route_df = route_df.merge(latlon_map, left_on="name", right_index=True, how="left")

        for _, row in route_df.iterrows():
            carrier = str(row["carrier"]).lower()
            color = COLOR_DICT.get(carrier, "lightgray")
            stop_name = row["name"].upper()
            icon_type = "train" if stop_name in RAIL_STATIONS else "bus"
            folium.Marker(
                location=[row["stop_lat"], row["stop_lon"]],
                popup=row["name"],
                icon=folium.Icon(color=color, icon=icon_type, prefix="fa")
            ).add_to(fmap)

    return fmap

def main():

    st.set_page_config(layout="wide")
    st.title("\U0001F68D ATL Transit Planner")
    input_col1, input_col2, route_details_col = st.columns([2, 2, 2])

    with input_col1:
        st.subheader("Route Search")
        start_input = st.text_input("Start Location", st.session_state.get("start_input", ""))
        target_input = st.text_input("Target Location", st.session_state.get("target_input", ""))
        mode_input = st.radio("Mode", options=["Distance", "Travel Time"])
        find_route = st.button("Find Route")

    with input_col2:
        st.subheader("Walking Preferences")
        if mode_input == "Distance":
            first_mile = st.number_input("Max Walking Distance to First Station (mi)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
            last_mile = st.number_input("Max Walking Distance from Last Station (mi)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
            frst_walk_time = None
            last_walk_time = None
        else:
            frst_walk_time = st.number_input("Maximum Walking Time to First Station (min)", min_value=1, max_value=60, value=30, step=1)
            last_walk_time = st.number_input("Maximum Walking Time from Last Station (min)", min_value=1, max_value=60, value=30, step=1)
            first_mile = None
            last_mile = None

    with route_details_col:
        if "route_info" in st.session_state:
            info = st.session_state["route_info"]
            st.subheader("\U0001F4CB Route Details")
            st.markdown(f"**Fare:** {info.get('expected_fare', 'N/A')}")
            if mode_input == "Distance":
                st.markdown(f"**Distance:** {info.get('total_distance', 'N/A')}")
            else:
                st.markdown(f"**Travel Time:** {info.get('total_travel_time', 'N/A')}")
            st.markdown(f"**Transfers:** {info.get('transfers', 'N/A')}")

    if find_route and start_input and target_input:
        with st.spinner("\U0001F504 Calculating optimal route..."):
            try:
                st.session_state["start_input"] = start_input
                st.session_state["target_input"] = target_input
                planner = RouteFinder.Route(
                    start=start_input,
                    target=target_input,
                    mode=mode_input,
                    frst_mile_dist=first_mile,
                    last_mile_dist=last_mile,
                    frst_stop_walk_time=frst_walk_time,
                    last_stop_walk_time=last_walk_time
                )
                path, total_cost = planner.feasible_routes()
                stop_df = planner.stops.copy()
                coords_map = {
                    row['stop_name']: (safe_parse(row['stop_lat']), safe_parse(row['stop_lon']))
                    for _, row in stop_df.iterrows()
                }
                stops = [{"name": stop, "coords": coords_map.get(stop, (0, 0))} for stop in path]
                summary, expected_fare_cost, num_transfers = planner.route_info(path)
                route_info = {
                    "expected_fare": f"${expected_fare_cost:.2f}",
                    "total_distance": f"{total_cost:.2f} miles" if mode_input == "Distance" else None,
                    "total_travel_time": f"{total_cost:.2f} minutes" if mode_input == "Travel Time" else None,
                    "transfers": num_transfers
                }
                st.session_state["start_coords"] = (planner.start_lat, planner.start_lon)
                st.session_state["end_coords"] = (planner.target_lat, planner.target_lon)
                st.session_state["stops"] = stops
                st.session_state["route_info"] = route_info
                st.session_state["stop_df"] = stop_df
                st.session_state["summary_df"] = summary
            except Exception as e:
                st.error(f"Could not compute a feasible route: {e}")

    map_col, stops_col = st.columns([2, 2])

    with map_col:
        if all(k in st.session_state for k in ["start_coords", "end_coords", "stops"]):
            st.subheader("\U0001F5FA️ Route Map")
            fmap = create_map(
                st.session_state["start_coords"],
                st.session_state["end_coords"],
                st.session_state["stops"],
                stop_df=st.session_state["stop_df"]
            )
            st_folium(fmap, width=1000, height=700)

    with stops_col:
        if "summary_df" in st.session_state:
            st.subheader("\U0001F6D1 Stops")
            summary = st.session_state["summary_df"]
            for i, row in summary.iterrows():
                from_stop = row["from_stop"]
                to_stop = row["to_stop"]
                route = row.get("route_long_name", "")
                short_name = row.get("route_short_name", "")
                carrier = row.get("carrier", "")

                # Check if this leg is a transfer either by is_transfer field
                # or if the route_long_name changed from the previous step
                is_transfer = row.get("is_transfer", False)
                prev_route = summary.iloc[i - 1]["route_long_name"] if i > 0 else None
                transfer_icon = " \U0001F501" if is_transfer or (i > 0 and prev_route != route) else "" # check if current stop is a transfer to a diff route or if the route is different from previous stop
                st.markdown(f"**{i + 1}.** `{from_stop}` → `{to_stop}` {str(carrier).upper()} Route {short_name}: {route} {transfer_icon}")

if __name__ == "__main__":
    main()
