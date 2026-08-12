import networkx as nx 
import pandas as pd 
import matplotlib.pyplot as plt
import folium
from math import radians, sin, cos, sqrt, asin
from itertools import permutations
from datetime import datetime, timedelta


"""
    This script encapsulates the Network Analysis we are performing for Metro ATL Public Transit
    Author: Isaiah Coriolan
"""

class ATL_Transit():

    """
        This function processes all of our data for developing the network model. 
        Args: None
        Returns:
            - all_stops: nx1 dataframe containing all stop/station names across all transit carriers we're analyzing
            - all_connections: dx2 dataframe containing all direct stop connections between stop/stations across all transit carriers we're analyzing
    """
    @staticmethod
    def data_processing():

        # Read data for stops
        xpress_stop_data = pd.read_csv("Xpress\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])

        # Add this feature for the carrier of the stop; this will be important when we try to reverse engineer the route from the algorithm
        xpress_stop_data["carrier"] = "xpress"

        marta_stop_data = pd.read_csv("MARTA\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        marta_stop_data["carrier"] = "marta"

        clinc_stop_data = pd.read_csv("CobbLinc\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        clinc_stop_data["carrier"] = "clinc"

        gwinnett_stop_data = pd.read_csv("Gwinnett County Transit\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        gwinnett_stop_data["carrier"] = "gwinnett"

        douglas_stop_data = pd.read_csv("Connect Douglas\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        douglas_stop_data["carrier"] = "douglas"

        # Find all unique stop names to add as nodes within the network 
        all_stops = pd.concat([xpress_stop_data, marta_stop_data, clinc_stop_data, gwinnett_stop_data, douglas_stop_data]).drop_duplicates()
        
        # Read for data for routes 
        xpress_route_data = pd.read_csv("Xpress\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        marta_route_data = pd.read_csv("MARTA\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        clinc_route_data = pd.read_csv("CobbLinc\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        gwinnett_route_data = pd.read_csv("Gwinnett County Transit\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        douglas_route_data = pd.read_csv("Connect Douglas\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])


        # Find routes for each transit carrier
        carriers = ["xpress", "marta", "clinc", "gwinnett", "douglas"]

        # Dictionary for dynnamic referencing of each carriers route_data
        carrier_route_dict = {"xpress": xpress_route_data, 
                            "marta": marta_route_data, 
                            "clinc": clinc_route_data, 
                            "gwinnett":gwinnett_route_data, 
                            "douglas": douglas_route_data}

        # Dictionary for dynamic referencing of each carriers stop_data
        carrier_stop_dict =  {"xpress": xpress_stop_data, 
                            "marta": marta_stop_data, 
                            "clinc": clinc_stop_data, 
                            "gwinnett":gwinnett_stop_data, 
                            "douglas": douglas_stop_data}

        # Temporary list to store all routes for all transit carriers
        all_routes = []

        for carrier in carriers:
            route_stop_data = pd.merge(carrier_route_dict[carrier], carrier_stop_dict[carrier], how = "left", on = "stop_id") # join routes w/stops
            route_stop_data = route_stop_data.sort_values(by = ["trip_id", "stop_sequence"]) # sort by trip_id & sequence
            routes = route_stop_data.groupby("trip_id")["stop_name"].apply(list).tolist() # create a list of lists where each sublist represents the sequence of stops for each unique trip_id
            all_routes.extend(routes) # add these sublists to all_routes 

        # Create a list to store each dictionary representing adjacent stop pairs
        connections = []

        # Loop through all_connections, stop_a = i, stop_b = i + 1
        for sublist in all_routes: # loop through the sublists in all_routes
            for i in range(len(sublist) - 1): # loop through each element in the sublist up to, but not including the last element
                stop_a = sublist[i]
                stop_b = sublist[i + 1]
                connections.append({"stop_1": stop_a, "stop_2": stop_b})
        
        # Create dataframee from list of dictionries
        connections_df = pd.DataFrame(connections)

        # Add bidirectional connections b/w MARTA stations on the red/gold lines & green/blue lines
            # ex. Airport to all stops on red & gold lines but not for stops on green/blue lines

        # Red/Gold Line Connections
        red_gold = [    
                "EAST POINT STATION",
                "BROOKHAVEN-OGLETHORPE STATION",
                "ARTS CENTER STATION",
                "MIDTOWN STATION",
                "DUNWOODY STATION",
                "LINDBERGH CENTER STATION",
                "AIRPORT STATION",
                "COLLEGE PARK STATION",
                "GARNETT STATION",
                "FIVE POINTS STATION",
                "PEACHTREE CENTER STATION",
                "CHAMBLEE STATION",
                "SANDY SPRINGS STATION",
                "NORTH SPRINGS STATION",
                "OAKLAND CITY STATION",
                "WEST END STATION",
                "BUCKHEAD STATION",
                "NORTH AVENUE STATION",
                "DORAVILLE STATION",
                "MEDICAL CENTER STATION",
                "CIVIC CENTER STATION",
                "LENOX STATION",
                "LAKEWOOD-FT MCPHERSON STATION"
        ]
    
        red_gold_connections = [{"stop_1": a, "stop_2": b} for a, b in permutations(red_gold, 2)]

        blue_green = [
                "HAMILTON E HOLMES STATION",
                "WEST LAKE STATION",
                "EAST LAKE STATION",
                "DECATUR STATION",
                "EDGEWOOD-CANDLER PARK STATION",
                "GEORGIA STATE STATION",
                "KENSINGTON STATION",
                "BANKHEAD STATION",
                "VINE CITY STATION",
                "ASHBY STATION", 
                "AVONDALE STATION",
                "GWCC-CNN CENTER STATION",
                "KING MEMORIAL STATION",
                "INDIAN CREEK STATION",
                "INMAN PARK-REYNOLDSTOWN STATION",
                "FIVE POINTS STATION"
        ]

        blue_green_connections = [{"stop_1": a, "stop_2": b} for a, b in permutations(blue_green, 2)]

        # Append the list of dicts to the DataFrame
        connections_df = pd.concat([connections_df, pd.DataFrame(red_gold_connections)], ignore_index=True)
        connections_df = pd.concat([connections_df, pd.DataFrame(blue_green_connections)], ignore_index=True)
    
        # Join w/ATL_Stops.csv to get the (lat, lon) pairs needed for calculating haversine distance 
        stops_df = pd.read_csv("ATL_stops.csv", usecols = ["stop_name", "stop_lat", "stop_lon"])
        connections_df = pd.merge(connections_df, stops_df, left_on = "stop_1", right_on = "stop_name", how = "left")
        connections_df.rename(columns = {"stop_lat": "stop1_lat", "stop_lon": "stop1_lon"}, inplace = True)
        connections_df.drop(columns = ["stop_name"], inplace = True)
        connections_df = pd.merge(connections_df, stops_df, left_on = "stop_2", right_on = "stop_name", how = "left")
        connections_df.drop(columns = ["stop_name"], inplace = True)
        connections_df.rename(columns = {"stop_lat": "stop2_lat", "stop_lon": "stop2_lon"}, inplace = True)

        # Apply the haversine function to get the distance between each of these stations 
        connections_df["hav_distance"] = connections_df.apply(lambda row: haversine(row["stop1_lat"], row["stop1_lon"], row["stop2_lat"], row["stop2_lon"]), axis = 1)

        # Apply function for calculating travel time between connected stations for different weighted network 

        # Drop complete duplicates 
        connections_df = connections_df.drop_duplicates()
        all_stops = all_stops.drop_duplicates()

        # Write to csv for future reference 
        # connections_df.to_csv("ATL_Transit_connections.csv")
        # all_stops.to_csv("ATL_Stops.csv")

        return all_stops, connections_df
    

    """
        Function builds the route information that includes each stop connection & its associated route.
        To be used for finalizing the transfer points & calculating expected fare cost for the recommended route.
    """
    @staticmethod
    def build_route_info():

        # Stop times data 
        xpress_stop_times = pd.read_csv(r"Xpress\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        marta_stop_times = pd.read_csv(r"MARTA\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        clinc_stop_times = pd.read_csv(r"CobbLinc\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        gwinnett_stop_times = pd.read_csv(r"Gwinnett County Transit\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])
        douglas_stop_times = pd.read_csv(r"Connect Douglas\stop_times.csv", header = 0, usecols = ["trip_id", "stop_id", "stop_sequence"])

        # Trips data
        xpress_trips = pd.read_csv(r"Xpress\trips.csv", header = 0, usecols = ["trip_id", "route_id", "direction_id"])
        marta_trips = pd.read_csv(r"MARTA\trips.csv", header = 0, usecols = ["trip_id", "route_id", "direction_id"])
        clinc_trips = pd.read_csv(r"CobbLinc\trips.csv", header = 0, usecols = ["trip_id", "route_id", "direction_id"])
        gwinnett_trips = pd.read_csv(r"Gwinnett County Transit\trips.csv", header = 0, usecols = ["trip_id", "route_id", "direction_id"])
        douglas_trips = pd.read_csv(r"Connect Douglas\trips.csv", header = 0, usecols = ["trip_id", "route_id", "direction_id"])

        # Stops data
        xpress_stops = pd.read_csv(r"Xpress\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        marta_stops = pd.read_csv(r"MARTA\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        clinc_stops = pd.read_csv(r"CobbLinc\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        gwinnett_stops = pd.read_csv(r"Gwinnett County Transit\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
        douglas_stops = pd.read_csv(r"Connect Douglas\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])

        # Routes data
        xpress_routes = pd.read_csv(r"Xpress\routes.csv", header = 0, usecols = ["route_id", "route_short_name", "route_long_name", "agency_id", "route_color"])

        marta_routes = pd.read_csv(r"MARTA\routes.csv", header = 0, usecols = ["route_id", "route_short_name", "route_long_name", "agency_id", "route_color"])

        clinc_routes = pd.read_csv(r"CobbLinc\routes.csv", header = 0, usecols = ["route_id", "route_short_name", "route_long_name", "agency_id", "route_color"])

        gwinnett_routes = pd.read_csv(r"Gwinnett County Transit\routes.csv", header = 0, usecols = ["route_id", "route_short_name", "route_long_name", "agency_id", "route_color"])
        
        douglas_routes = pd.read_csv(r"Connect Douglas\routes.csv", header = 0, usecols = ["route_id", "route_short_name", "route_long_name", "agency_id", "route_color"])

        
        # Load the GTFS files
        stop_times = pd.concat([xpress_stop_times, marta_stop_times, clinc_stop_times, gwinnett_stop_times, douglas_stop_times], ignore_index=True)
        trips = pd.concat([xpress_trips, marta_trips, clinc_trips, gwinnett_trips, douglas_trips], ignore_index = True)
        stops = pd.concat([xpress_stops, marta_stops, clinc_stops, gwinnett_stops, douglas_stops], ignore_index=True)
        routes = pd.concat([xpress_routes, marta_routes, clinc_routes, gwinnett_routes, douglas_routes], ignore_index = True)


        # Merge stop_times with trips to get route_id
        stop_times = stop_times.merge(trips[['trip_id', 'route_id']], on='trip_id')

        # Merge stop_times with stops to get stop names
        stop_times = stop_times.merge(stops[['stop_id', 'stop_name']], on='stop_id')

        # Sort stop_times by trip and stop sequence
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

        # Build consecutive stop pairs for each trip
        connection_rows = []
        for trip_id, group in stop_times.groupby('trip_id'):

            group = group.reset_index(drop=True)

            for i in range(len(group) - 1):
                stop_1 = group.loc[i, 'stop_name'].strip()
                stop_2 = group.loc[i + 1, 'stop_name'].strip()
                route_id = str(group.loc[i, 'route_id'])
            

        # Create DataFrame and remove duplicates
        route_names_df = pd.DataFrame(connection_rows, columns=['stop_1', 'stop_2', 'route_id', 'carrier'])
        route_names_df = route_names_df.drop_duplicates()

        # Map route_id to route_long_name
        routes['route_id'] = routes['route_id'].astype(str)
        route_names_df = route_names_df.merge(routes[['route_id', 'route_long_name']], on='route_id', how='left')

        print("Route Names DF: \n", route_names_df.head())

        # Write to csv
        route_names_df.to_csv("complete_route_names.csv", index=False)
    
    

    """
        This function creates the network with nodes (bus stops & rail stations) & 
        edges (connections between stops/stations) to be used for network analysis
        Arguments: 
            - connections_df
                - Dataframe containing the edges between stops/stations for all the ATL public transit carriers we're analyzing
        Return:
            Weighted, Directed network w/edge weights representing distances between stations 
    """
    def network(self):
        
        # Create directed graph 
        G_directed = nx.DiGraph()

        # Read in connection data frame 
        connections_df = pd.read_csv("ATL_Transit_connections.csv")
       
        # Add edges to this graph
        for index, row in connections_df.iterrows():
            G_directed.add_edge(str(row["stop_1"]), str(row["stop_2"]), weight = row["hav_distance"])

        # Write directed graph to file for future loading 
        edges_df = nx.to_pandas_edgelist(G_directed)
        edges_df.to_csv("ATL_Transit_Edges.csv", index=False)

        print("Successfully created edge list!")
    
        return G_directed
    

"""
    Function creates weighted directed network for the travel times between stations.
"""
def network2():

    # Create directed graph 
    G_dir = nx.DiGraph()

    # Load data 
    travel_times = pd.read_csv("ATL_Travel_Time_Edges2.csv")

    # Drop duplicates
    travel_times = travel_times.drop_duplicates()

    # Add these edges to the network 
    for index, row in travel_times.iterrows():
        G_dir.add_edge(str(row["stop_1"]), str(row["stop_2"]), weight = row["weight"])

    # Write directed graph to file for future loading 
    edges_df = nx.to_pandas_edgelist(G_dir)
    edges_df.to_csv("ATL_Ntwrk_Travelimes.csv")

    print("Successfully created travel times edge list!")

    return


"""
    Function calculates the haversine distance between 2 stations. 
    Used for the weights between connected stations in the directed graph. 
"""
def haversine(lat1, lon1, lat2, lon2):

    R = 3958.8 # Approximate radius of earth in miles 

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    lat1, lat2 = radians(lat1), radians(lat2)

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2 # square of half of the chord length b/w the points (spherical straight line)
    c = 2 * asin(sqrt(a)) # angular distance in radians (how far along the earths surface to travel in radians)

    return round(R * c, 3)

"""
    Function creates a csv with all route names & their associated transit carrier
"""
def route_carrier():

    # Routes data
    xpress_routes = pd.read_csv(r"Xpress\routes.csv", header = 0, usecols = ["route_short_name", "route_long_name"])
    xpress_routes["carrier"] = "xpress"

    marta_routes = pd.read_csv(r"MARTA\routes.csv", header = 0, usecols = ["route_short_name", "route_long_name"])
    marta_routes["carrier"] = "marta"

    clinc_routes = pd.read_csv(r"CobbLinc\routes.csv", header = 0, usecols = ["route_short_name", "route_long_name"])
    clinc_routes["carrier"] = "clinc"

    gwinnett_routes = pd.read_csv(r"Gwinnett County Transit\routes.csv", header = 0, usecols = ["route_short_name", "route_long_name"])
    gwinnett_routes["carrier"] = "gwinnett"
    
    douglas_routes = pd.read_csv(r"Connect Douglas\routes.csv", header = 0, usecols = ["route_short_name", "route_long_name"])
    douglas_routes["carrier"] = "douglas"

    concat_results = pd.concat([xpress_routes, marta_routes, clinc_routes, gwinnett_routes, douglas_routes], ignore_index = True)

    concat_results.to_csv("RouteCarriers.csv")

    print("Wrote to CSV!")


"""
    Function generates the folium map for visualizing all of the stops over a map of Atlanta. 
    Args: None 
    Return: None
"""
def map():

    # Read data 
    xpress_stop_data = pd.read_csv("Xpress\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    xpress_stop_data["carrier"] = "xpress"

    marta_stop_data = pd.read_csv("MARTA\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    marta_stop_data["carrier"] = "marta"

    clinc_stop_data = pd.read_csv("CobbLinc\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    clinc_stop_data["carrier"] = "clinc"

    gwinnett_stop_data = pd.read_csv("Gwinnett County Transit\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    gwinnett_stop_data["carrier"] = "gwinnett"

    douglas_stop_data = pd.read_csv("Connect Douglas\stops.csv", header = 0, usecols = ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    douglas_stop_data["carrier"] = "douglas"

    # Union this data 
    complete_coords = pd.concat([xpress_stop_data, clinc_stop_data, gwinnett_stop_data, douglas_stop_data])

    # Create map w/focus on Atlanta 
    map = folium.Map((33.753746, -84.386330), zoom_start = 10)

    # Plot Markers representing the bus stops/rail stations
    for index, row in complete_coords.iterrows():
        if row["carrier"] == "xpress":
            folium.Marker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                icon = folium.Icon(color = "blue", icon = "bus", prefix = "fa")
            ).add_to(map)
        elif row["carrier"] == "clinc":
            folium.Marker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                icon = folium.Icon(color = "gray", icon = "bus", prefix = "fa")
            ).add_to(map)
        elif row["carrier"] == "gwinnett":
            folium.Marker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                icon = folium.Icon(color = "purple", icon = "bus", prefix = "fa")
            ).add_to(map)
        else:
            folium.Marker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                icon = folium.Icon(color = "green", icon = "bus", prefix = "fa")
            ).add_to(map)


    # Create map for visualizing MARTA stops separately 
    map2 = folium.Map((33.753746, -84.386330), zoom_start = 10)

    # Loop through Marta for the stations temporarily; There are a lot of bus routes that we will have to condense through the network analysis
    for index, row in marta_stop_data.iterrows():
        folium.Marker(
            location = [row["stop_lat"], row["stop_lon"]], 
            popup = row["stop_name"],
            icon = folium.Icon(color = "red", icon = "bus", prefix = "fa")
        ).add_to(map2)

    # Render the map
    map.show_in_browser()
    map2.show_in_browser()
    map.save("ATL_Public_Transit_Map.html")


if __name__ == "__main__":
    # stop_names, connections = ATL_Transit().data_processing()
    # ATL_Transit().network()
    print("Printing this to avoid rerunning code ")
    # network2()
    # ATL_Transit.build_route_info()
    # route_carrier()

