import networkx as nx 
import pandas as pd 
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import folium


"""
    This script encapsulates the Network Analysis we are performing for Metro ATL Public Transit
    Version 1.0
"""

"""
    This function processes all of our data for developing the network model. 
    Args: None
    Returns:
        - all_stops: nx1 dataframe containing all stop/station names across all transit carriers we're analyzing
        - all_connections: dx2 dataframe containing all direct stop connections between stop/stations across all transit carriers we're analyzing
"""
def data_processing():

    # Read data for stops
    xpress_stop_data = pd.read_csv("Xpress\stops.csv", header = 0, usecols = ["stop_id", "stop_name"])
    marta_stop_data = pd.read_csv("MARTA\stops.csv", header = 0, usecols = ["stop_id", "stop_name"])
    clinc_stop_data = pd.read_csv("CobbLinc\stops.csv", header = 0, usecols = ["stop_id", "stop_name"])
    gwinnett_stop_data = pd.read_csv("Gwinnett County Transit\stops.csv", header = 0, usecols = ["stop_id", "stop_name"])
    douglas_stop_data = pd.read_csv("Connect Douglas\stops.csv", header = 0, usecols = ["stop_id", "stop_name"])

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
    all_connections = pd.DataFrame(connections)

    # network(all_connections)
    return all_stops, all_connections
    

"""
    This function creates the network with nodes (bus stops & rail stations) & 
    edges (connections between stops/stations) to be used for network analysis
    Arguments: 
        - connections_df
            - Dataframe containing the edges between stops/stations for all the ATL public transit carriers we're analyzing
    Return:
        network model w/nodes & edges
"""
def network(connections_df):
    
    # Create undirected graph 
    G_undirected = nx.Graph()

    # Create directed graph 
    G_directed = nx.DiGraph()

    # Add edges to these graphs
    for index, row in connections_df.iterrows():

        G_undirected.add_edge(row["stop_1"], row["stop_2"])

        G_directed.add_edge(row["stop_1"], row["stop_2"])
    
    # Set the figure
    plt.figure(figsize = (12, 10))
    
    # Set layout for visualization
    positions_undirected = nx.spring_layout(G_undirected)
    positions_directed = nx.spring_layout(G_directed)

    # Set node & edge options/attributes
    node_options = {"node_color": "blue", "node_size": 20}
    edge_options = {"width": .20, "alpha": .9, "edge_color": "black"}
    
    # Draw nodes, edges, & labels
    nx.draw_networkx_nodes(G_undirected, positions_undirected, **node_options)
    nx.draw_networkx_edges(G_undirected, positions_undirected, **edge_options)

    # Set Title 
    plt.title("Metro ATL Public Transit (Undirected)")

    # Save before showing
    # plt.savefig("undirAtl_transit.png", dpi=300, bbox_inches='tight')

    # Show
    # plt.show()

    # plot(G_undirected, positions_undirected)

    return G_undirected, G_directed


"""
    Function generates plots for passed in networks 
    Arguments: G- graph containing nodes & edges 
    Return: None
"""
def plot(G, positions):

    # Edge traces
    edge_x = []
    edge_y = []

    for edge in G.edges():
        x0, y0 = positions[edge[0]]
        x1, y1 = positions[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='gray'),
        hoverinfo='none',
        mode='lines'
    )

    # Node traces
    node_x = []
    node_y = []
    node_text = []

    for node in G.nodes():
        x, y = positions[node]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        marker=dict(
            showscale=False,
            size=10,
            color='skyblue',
            line=dict(width=1, color='darkblue')
        )
    )

    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Transit Network (Undirected)',
                        title_x=0.5,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                    ))

    fig.show(renderer = "browser")



"""
    Function analyzes the passed in Network, computes an array of metrics, & provides summary outputs. 
    Arguments: 
        - G: Network containing nodes & edges
    Return:
        None
"""
def analysis(G):
    return 


"""
    Function generates the folium map for visualizing the routes & connections over a map of Atlanta. 
    Args: None 
    Return: None
"""
def map(connections_df):

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
            folium.CircleMarker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                color = "blue",
                radius = 1
            ).add_to(map)
        elif row["carrier"] == "clinc":
            folium.CircleMarker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                color = "gray", 
                radius = 1
            ).add_to(map)
        elif row["carrier"] == "gwinnett":
            folium.CircleMarker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                color = "purple",
                radius = 1
            ).add_to(map)
        else:
            folium.CircleMarker(
                location = [row["stop_lat"], row["stop_lon"]],
                popup = row["stop_name"],
                color = "green",
                radius = 1
            ).add_to(map)

    # Loop through Marta for the stations temporarily; There are a lot of bus routes that we will have to condense through the network analysis
    for index, row in marta_stop_data.head(50).iterrows():
        folium.CircleMarker(
            location = [row["stop_lat"], row["stop_lon"]], 
            popup = row["stop_name"],
            color = "red",
            radius = 3
        ).add_to(map)

    # Create a dictionary to store each stop name & its respective lon/lat coords 
    coords_dict = complete_coords.set_index("stop_name")[["stop_lat", "stop_lon"]].apply(list, axis=1).to_dict()

    # Add Edges between markers using the connections_df
    for index, row in connections_df.iterrows():

        start = row["stop_1"]
        end = row["stop_2"]

        if start in coords_dict and end in coords_dict:
            folium.PolyLine(
                locations=[coords_dict[start], coords_dict[end]],
                color="black", weight=1, opacity=.8
            ).add_to(map)


    # Render the map
    map.show_in_browser()
    map.save("ATL_Public_Transit_Map.html")


if __name__ == "__main__":
    stop_names, connections = data_processing()
    map(connections)

