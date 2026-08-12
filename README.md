This repo contains the work for our Network Analysis project on ATL Public Transit.

project_research.ipynb: Jupyter notebook used for the general analytics section of the report 

Sum25NetworkProject.ipynb: The other Jupyter notebook used for network research section of the report

network.py: Data preprocessing script that created our weighted directed network & other files needed for the tool 

ATL Public Transit: Folder containing the data we collected from our data source

/ATL Public Transit/map.py: Creates the maps of the transit carrier networks used for our report

/Code For Tool/route2.py: script that finds the optimal route for user specified parametsr 

/Code For Tool/app2.py: script that programs the streamlit app for user interactivity for route finding 

/Code For Tool/requirements.txt: txt file containing packages & their versions needed to run the app in a Virtual Environment

/Summary Files/ATL_Stops.csv: Contains information for all of the stops for all of the transit carriers we researched 

/Summary Files/ATL_Transit_Edges.csv: Edge list used for loading the directed network with edge weights representing haversine distance between stops 

/Summary Files/ATL_Transit_Connection.csv: csv file with direct connections between stops & information for each stop respectively 

/Summary Files/Route_Carriers.csv: csv file containing the routes and their respective carrier.

/Summary Files/complete_route_names.csv: The direct connections between stops & the associated route. Used for mapping the returned path to its corresponding route for the tool 

/Summary Files/Network_Travel_Time_Edges2.csv: Not contained in this repo because it was too large of a file, but this was the weighted network with the travel time between each directly connected station in minutes

/Tool 2/analysis/network_analysis.ipynb: Notebook performing full network analytics and visualization

/Tool 2/processed_data/atlanta_transit.db: SQLite database used in the web tool (not included in repo due to file size limitations)

/Tool 2/frontend/flask_app.py: Flask backend for interactive web tool and API support

/Tool 2/frontend/static/analysis_results/: Folder containing exported analysis results used by the web interface

/Tool 2/frontend/templates/: HTML files for the web app interface (index.html, map.html, and analysis.html)

/Tool 2/data/: Raw GTFS and other transit data for MARTA, CobbLinc, Connect Douglas, and Gwinnett County Transit

