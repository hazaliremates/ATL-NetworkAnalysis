from geopy.geocoders import Nominatim 
import networkx as nx 
import pandas as pd
import ast 
import folium
import math
import numpy as np


"""
    This script determines the public transit route based on their specified start & target locations.
    Doesn't perform the greedy search; to be used for the Project Presentation
    Author: Isaiah Coriolan
"""

# Future Updates: Time of Day Constraints, Dynamic handling of routes that extend into different transit carrier networks, API for up to date route data, using a better geocoder


class Route():

    """
        Initializes class attributes. 
        Args:
            - start: start geographic location passed in by user 
            - target: target geographic location passed in by user 
            - frst_mile_dist: the maximum distance a user is willing to travel by foot to get to the 1st station in a route 
            - last_mile_dist: the maximum distance a user is willing to travel by foot from the last station in the route to their target location
            - mode: specification for whether the user wants to find the route based on minimum expected travel time or minimum traveled distance
            - frst_stop_walk_time: Max time spent walking from start location to first stop
            - last_stop_walk_time: Max time spent walking from last stop to target location
    """
    def __init__(self, start, target, mode, frst_mile_dist = None, last_mile_dist = None, frst_stop_walk_time = None, last_stop_walk_time = None):

        # Required arguments
        self.start = start
        self.target = target 
        self.mode = mode
        
        # Dependent on the mode selected
        self.frst_mile_dist = frst_mile_dist
        self.last_mile_dist = last_mile_dist
        self.frst_stop_walk_time = frst_stop_walk_time # all times are in units of minutes
        self.last_stop_walk_time = last_stop_walk_time
    

    """
        Function determines the geographic coordinates of the passed in start & target locations
        Args: none
        Return:
            - Geospatial coordinates for the start & target locations as a list [()]
    """
    def coords(self):
         
        geolocator = Nominatim(user_agent = "atl-transit-app")
        start = geolocator.geocode(self.start)
        end = geolocator.geocode(self.target)

        print("Start:", start)

        self.start_lon = start.longitude
        self.start_lat = start.latitude
        self.target_lon = end.longitude
        self.target_lat = end.latitude

        # Find Geospatial coordinates for passed in addresses
        start_coords = (start.longitude, start.latitude)
        end_coords = (end.longitude, end.latitude) 

        print(f"Coords for start location: {start_coords} \n Coords for target location: {end_coords}")

        return start_coords, end_coords


    """
        Function finds the nearest stations within a frst_mile_rad of the users start location
        & target location respectively 
        Return:
            - start_stations: df containing information for all of the stations that satisfy the users first mile distance travel constraint 
            - end_stations: df containing information for all of the stations that satisfy the users last mile distance travel constraint 
    """
    def station_finder(self):

        # Retrieve all of the stops & connections
        all_stops = pd.read_csv("ATL_Stops.csv")
        connections = pd.read_csv("ATL_Transit_connections.csv")
        self.connections = connections
        self.stops = all_stops

        # Create subdf containing just the stop_name, stop_lat & stop_lon
        stop_info = all_stops.loc[:, ["stop_name", "stop_lat", "stop_lon"]]

        # Create a tuple w/ (lat, lon) data types
        stop_info["stop_lat"] = stop_info["stop_lat"].apply(safe_parse)
        stop_info["stop_lon"] = stop_info["stop_lon"].apply(safe_parse)

        # Create new column containing format needed for geopy 
        stop_info["complete_coords"] = list(zip(stop_info['stop_lon'], stop_info['stop_lat']))

        # Create new column containing the start_coords & end_coords for the users input
        start_coords, end_coords = self.coords()
        stop_info["start_coords"] = str(start_coords)
        stop_info["end_coords"] = str(end_coords)

        # Convert back to literal (lat, lon)
        stop_info["start_coords"] = stop_info["start_coords"].apply(safe_parse)
        stop_info["end_coords"] = stop_info["end_coords"].apply(safe_parse)
 
        # Calculate the manhattan (walking) distance b/w the complete_coords for each stop & the start/end_coords
        stop_info["start_station_walking_dist"] = stop_info.apply(lambda row: manhattan_distance(row["complete_coords"], row["start_coords"]), axis = 1)
        stop_info["end_station_walking_dist"] = stop_info.apply(lambda row: manhattan_distance(row["complete_coords"], row["end_coords"]), axis = 1)

        # Calculate expected walking time based on the manhattan distance
        # Avg adult walking speed = .05 miles per minute
        stop_info["start_station_walking_time"] = stop_info["start_station_walking_dist"] / .05 
        stop_info["end_station_walking_time"] = stop_info["end_station_walking_dist"] / .05 

        # Check if user specified to minimize either travel time or travel distance 
        if self.mode == "Travel Time":

            # Filter stop_info where the start_station_walking_dist is <= frst_mile_dist or end_station_walking_dist distance is <= last_mile_dist into 2 different df's
            mask1 = stop_info["start_station_walking_time"] <= self.frst_stop_walk_time
            mask2 = stop_info["end_station_walking_time"] <= self.last_stop_walk_time
            start_stations = stop_info[mask1].loc[:, ["stop_name", "start_coords", "complete_coords", "start_station_walking_time"]]
            end_stations = stop_info[mask2].loc[:, ["stop_name", "start_coords", "complete_coords", "end_station_walking_time"]]

        else:

            # Filter stop_info where the start_station_walking_dist is <= frst_mile_dist or end_station_walking_dist distance is <= last_mile_dist into 2 different df's
            mask1 = stop_info["start_station_walking_dist"] <= self.frst_mile_dist
            mask2 = stop_info["end_station_walking_dist"] <= self.last_mile_dist
            start_stations = stop_info[mask1].loc[:, ["stop_name", "start_coords", "complete_coords", "start_station_walking_dist"]]
            end_stations = stop_info[mask2].loc[:, ["stop_name", "start_coords", "complete_coords", "end_station_walking_dist"]]
       
        print("Start Stations within first_mile_dist distance from start location \n", start_stations.head())
        print("End Stations within last_mile_dist distance from target location \n", end_stations.head())

        return start_stations, end_stations
    

    """
        Function finds the best route for the user based on whether they want to minimize expected total travel time 
        or expected total travel distance.
    """
    def feasible_routes(self):
        start_stations, end_stations = self.station_finder()

        # Use top N closest stations to reduce computational expense
        N = 5
        
        if self.mode == "Travel Time":
            start_stations = start_stations.sort_values("start_station_walking_time").iloc[:N].copy()
            end_stations = end_stations.sort_values("end_station_walking_time").iloc[:N].copy()
        else:
            start_stations = start_stations.sort_values("start_station_walking_dist").iloc[:N].copy()
            end_stations = end_stations.sort_values("end_station_walking_dist").iloc[:N].copy()

        # Cross join combinations
        start_stations["key"] = 1
        end_stations["key"] = 1
        start_stations = start_stations.rename(columns = {"stop_name": "start_stop_name"})
        end_stations = end_stations.rename(columns = {"stop_name": "end_stop_name"})
        route_combinations = pd.merge(start_stations, end_stations, on="key")

        # Load graphs (travel distance & travel time)
        dist_edges_df = pd.read_csv("ATL_Transit_edges.csv")
        time_edges_df = pd.read_csv("ATL_Travel_Time_Edges2.csv")

        # List to store all candidate routes & their descriptions
        candidate_routes = []

        if self.mode == "Travel Time":
            G_dir = nx.from_pandas_edgelist(time_edges_df, create_using=nx.DiGraph(), source="stop_1", target="stop_2", edge_attr="weight")

            for _, row in route_combinations.iterrows():
                try:
                    path = nx.shortest_path(G_dir, source=row["start_stop_name"], target=row["end_stop_name"])
                    route_travel_time = sum(G_dir[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))
                    total_travel_time = row["start_station_walking_time"] + route_travel_time + row["end_station_walking_time"]

                    candidate_routes.append({
                        "path": path,
                        "type": "direct",
                        "start_walk_time": row["start_station_walking_time"],
                        "end_walk_time": row["end_station_walking_time"],
                        "bridge_walk": 0,
                        "route_travel_time": route_travel_time,
                        "total_travel_time": total_travel_time
                    })

                except nx.NetworkXNoPath:
                    continue

        else:
            G_dir = nx.from_pandas_edgelist(dist_edges_df, create_using=nx.DiGraph(), source="source", target="target", edge_attr="weight")

            for _, row in route_combinations.iterrows():
                try:
                    path = nx.shortest_path(G_dir, source=row["start_stop_name"], target=row["end_stop_name"])
                    route_distance = sum(G_dir[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))
                    total_distance = row["start_station_walking_dist"] + route_distance + row["end_station_walking_dist"]

                    candidate_routes.append({
                        "path": path,
                        "type": "direct",
                        "start_walk": row["start_station_walking_dist"],
                        "end_walk": row["end_station_walking_dist"],
                        "bridge_walk": 0,
                        "route_dist": route_distance,
                        "total_dist": total_distance
                    })

                except nx.NetworkXNoPath:
                    continue

        # If no direct paths, return nothing
        if not candidate_routes:
            raise Exception("There are no direct paths in this network from the start to end location!")
         
        else:
            # Select the best route
            
            if self.mode == "Travel Time":
                best_route = min(candidate_routes, key = lambda x: x["total_travel_time"])
                print(f"Recommended route: {best_route}")
                return best_route["path"], best_route["total_travel_time"]
            else:
                best_route = min(candidate_routes, key=lambda x: x["total_dist"])
                print(f"Recommended route: {best_route}")
                return best_route["path"], best_route["total_dist"]

    """
        Function visualizes the best route for the user
    """
    def recommended_route(self):

        # Assign colors based on transit provider used 
        COLOR_DICT = {
            "marta": "red",
            "xpress": "blue",
            "clinc": "gray",
            "gwinnett": "purple",
            "douglas": "green"
        }

        # Keep track of rail stations for a different icon than buses
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

        # Get the path & its total distance 
        path, total_distance = self.feasible_routes()

        # Store the path found 
        self.path = path

        # Get the actual route
        summary, fare_cost, num_transfers = self.route_info(path)

        # Create folium map w/focal point on area of map between users start & target locations
        m = folium.Map(location=[(self.start_lat + self.target_lat) / 2, 
                                 (self.start_lon + self.target_lon) / 2], 
                                 zoom_start=11)
        
        # Add markers for where the user is starting & ending 
        folium.Marker(
            [self.start_lat, self.start_lon],
            popup="Start: " + self.start,
            icon=folium.Icon(color="red", icon="star")
        ).add_to(m)

        folium.Marker(
            [self.target_lat, self.target_lon],
            popup="Target: " + self.target,
            icon=folium.Icon(color="green", icon="star")
        ).add_to(m)

        # Read back the stops information for all transit carriers 
        lat_lon_df = self.stops.drop_duplicates("stop_name").set_index("stop_name")[["stop_lat", "stop_lon"]].copy()

        # Get the (lat, lon) of each stop to plot in a dataframe 
        lat_lon_df["stop_lat"] = lat_lon_df["stop_lat"].apply(safe_parse)
        lat_lon_df["stop_lon"] = lat_lon_df["stop_lon"].apply(safe_parse)

        # Create a dictionary of the stops & their respective carrier 
        carrier_map = self.stops.set_index("stop_name")["carrier"].to_dict()

        """
            Helper function retrieves the (lat, lon) coordinates 
        """
        def stop_coords(name):
            return [lat_lon_df.loc[name]["stop_lat"], lat_lon_df.loc[name]["stop_lon"]]

        """
            Helper function returns the kind of icon to be used for the stop based on i
        """
        def get_icon(stop_name):
            return "train" if stop_name.upper() in RAIL_STATIONS else "bus"
        

        # Plot each stop in the path on the map 
        for stop in path:
            lat, lon = stop_coords(stop)
            carrier = carrier_map.get(stop, "")
            icon_type = get_icon(stop)
            folium.Marker(
                [lat, lon],
                popup=stop,
                icon=folium.Icon(color=COLOR_DICT.get(carrier, "lightgray"), icon=icon_type, prefix="fa")
            ).add_to(m)

        # Iterate over the path & plot lines between successive stops
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1] 
            folium.PolyLine([stop_coords(a), stop_coords(b)], color="black", weight=4).add_to(m)

        # Render the map in the browser 
        # m.show_in_browser()


    """
        Function finds necessary route info for users based on the returned path. 
        Info includes transfer stops & expected fare cost 
    """
    def route_info(self, path):

        # Load the connections with route info
        df = pd.read_csv("complete_route_names.csv", header = 0)
        
        # Ensure whitespace is stripped for matching
        df['stop_1'] = df['stop_1'].str.strip()
        df['stop_2'] = df['stop_2'].str.strip()
        
        # Build multimap of (stop1, stop2) to [route names]
        pair_to_routes = {}
        for _, row in df.iterrows():
            key = (row['stop_1'], row['stop_2'])
            if key not in pair_to_routes:
                pair_to_routes[key] = set()
            pair_to_routes[key].add(row['route_long_name'])

        # Now walk through the path
        summary = []
        for i in range(len(path) - 1):
            stop1 = path[i].strip()
            stop2 = path[i+1].strip()
            routes = pair_to_routes.get((stop1, stop2), None)
            if routes is None:
                result = f"{stop1} → {stop2}: [NO DIRECT ROUTE FOUND]"
            else:
                route_list = ', '.join(sorted(routes))
                result = f"{stop1} → {stop2}: [{route_list}]"
            summary.append(result)

        # Logic for finding transfer points to other bus routes
        data = []
        for step in summary:
            # Split on → and then split off the route name
            segment, route_part = step.split(': ')
            from_stop, to_stop = segment.split(' → ')
            route_name = route_part.strip('[]')
            data.append((from_stop, to_stop, route_name))

        transfer_df = pd.DataFrame(data, columns=['from_stop', 'to_stop', 'route_name'])

        # Mark transfer if the route changes
        transfer_df['is_transfer'] = transfer_df['route_name'] != transfer_df['route_name'].shift()

        # First stop can't be a transfer
        transfer_df.loc[0, 'is_transfer'] = False 

        # Read in carriers for route names 
        route_carriers = pd.read_csv("RouteCarriers.csv", header = 0)
        transfer_df = pd.merge(transfer_df, route_carriers, left_on = "route_name", right_on = "route_long_name", how = "inner")

        # Find the total # of transfers for this path 
        num_transfers = len(transfer_df[transfer_df["is_transfer"] == True])

        # Fare Cost 
        fares = {
            "marta": 2.50,
            "xpress": 3.50, 
            "clinc": 2.50, 
            "douglas": 2.50, 
            "gwinnett": 2.50
        }

        # Allotted free transfers 
        free_transfers = {
                "marta": 4,    
                "xpress": 0,
                "clinc": float("inf"),
                "douglas": 0,
                "gwinnett": 3
            }
        
        # Get a summary of the carriers used & the # of transfers that occur with that carrier
        transfer_counts = (
            transfer_df[transfer_df["is_transfer"] == True]
            .groupby("carrier")
            .size()
            .reset_index(name="transfer_count")
        )

        """
            Helper function calculates the expected fare cost, taking into consideration the # of allowed transfers.
        """
        def compute_fare(row):
            carrier = row["carrier"]
            total_transfers = row["transfer_count"]
            free = free_transfers.get(carrier, float('inf'))
            fare = fares.get(carrier, 0)
            paid_rides = max(1, total_transfers + 1 - free)  # +1 to account for the first boarding
            return round(fare * paid_rides, 2)

        transfer_counts["expected_fare"] = transfer_counts.apply(compute_fare, axis=1)
        expected_fare_cost = transfer_counts["expected_fare"].sum()

        print(transfer_df.head())

        return transfer_df, expected_fare_cost, num_transfers

    

"""
    Helper function calculates the manhattan distance given 2 geospatial coordinates.
"""
def manhattan_distance(coord1, coord2):

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Approximate miles per degree
    miles_per_deg_lat = 69.0  # constant across latitudes

    avg_lat_rad = math.radians((lat1 + lat2) / 2)
    miles_per_deg_lon = 69.0 * math.cos(avg_lat_rad)  

    delta_lat_miles = abs(lat1 - lat2) * miles_per_deg_lat
    delta_lon_miles = abs(lon1 - lon2) * miles_per_deg_lon

    return round(delta_lat_miles + delta_lon_miles, 3)  # Total Manhattan distance in miles
    

"""
    Function returns a tuple of the (lat, lon) pairs
"""
def safe_parse(coord):
    if isinstance(coord, str):
        return ast.literal_eval(coord)
    return coord  # already a tuple


if __name__ == "__main__":
    
    # route = Route("225 North Ave NW, Atlanta, GA", "1345 Piedmont Ave NE, Atlanta, GA", .2, .5, "distance") # Tech to Botanical Gardens
    # route = Route("800 Cherokee Ave SE, Atlanta, GA", "1345 Piedmont Ave NE, Atlanta, GA", "Distance", .5,.5, 30, 30) # Zoo Atlanta to Botanical Gardens
    # route = Route("99 S Park Square NE, Marietta, GA", "306 Cobb Pkwy SE South, Marietta, GA", "Distance", .5, .5, 30, 30)
    
    route = Route("3393 Peachtree Rd NE, Atlanta, GA", "1364 Clifton Rd NE, Atlanta, GA", "Distance", .5, .5, 30,30) # Lenox Mall to Emory Hospital
    # route = Route("990 State St NW, Atlanta, GA", "700 Grayson Pkwy, Grayson, GA", .5, 2, "time") # Papa Johns to Grayson Library (Example of crossing transit carriers)
    # route = Route("55 Trinity Ave SW, Atlanta, GA", "660 Peachtree St NE, Atlanta, GA", .5, 2, "distance") # Underground Atlanta to Capitol
    
    route.recommended_route()
