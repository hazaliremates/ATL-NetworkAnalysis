#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
import json
import networkx as nx
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import heapq
from datetime import datetime, timedelta
import logging
import folium
from pathlib import Path
import os
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class EnhancedAtlantaTransitAPI:
    """Enhanced API with comprehensive analysis data loading"""
    
    def __init__(self, 
                 db_path="/Users/iremates/Desktop/ISYE4803Proj/processed_data/atlanta_transit.db",
                 analysis_path="/Users/iremates/Desktop/ISYE4803Proj/backend/analysis"):
        self.db_path = db_path
        self.analysis_path = analysis_path
        self.graph = None
        self.stops_data = None
        self.routes_data = None
        self.geocoder = Nominatim(user_agent="atlanta-transit-app")
        
        # Analysis data containers
        self.network_properties = {}
        self.centrality_data = None
        self.community_data = None
        self.geographic_data = {}
        self.robustness_data = {}
        
        self.load_data()
        self.load_analysis_data()
    
    def load_data(self):
        """Load basic transit data and build graph"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            self.stops_data = pd.read_sql_query("SELECT * FROM stops", conn)
            self.routes_data = pd.read_sql_query("SELECT * FROM routes", conn)
            connections_data = pd.read_sql_query("SELECT * FROM connections", conn)
            
            conn.close()
            
            logger.info(f"Loaded {len(self.stops_data)} stops and {len(connections_data)} connections")
            
            # Build graph
            self.graph = nx.Graph()
            
            # Add stops as nodes
            for _, stop in self.stops_data.iterrows():
                self.graph.add_node(
                    stop['stop_id_full'],
                    name=stop['stop_name'],
                    lat=stop['stop_lat'],
                    lon=stop['stop_lon'],
                    agency=stop['agency_name']
                )
            
            # Add connections as edges
            for _, conn in connections_data.iterrows():
                self.graph.add_edge(
                    conn['from_stop'],
                    conn['to_stop'],
                    weight=conn['travel_time'],
                    route=conn['route_id'],
                    agency=conn['agency']
                )
            
        except Exception as e:
            logger.error(f"Error loading basic data: {e}")
            # Initialize empty structures
            self.stops_data = pd.DataFrame()
            self.routes_data = pd.DataFrame()
            self.graph = nx.Graph()
    
    def load_analysis_data(self):
        """Load comprehensive analysis data from your analysis files"""
        try:
            # Load network properties
            network_props_file = os.path.join(self.analysis_path, "network_properties.json")
            if os.path.exists(network_props_file):
                with open(network_props_file, 'r') as f:
                    self.network_properties = json.load(f)
                logger.info("Loaded network properties")
            
            # Load geographic coverage
            geo_file = os.path.join(self.analysis_path, "geographic_coverage.json")
            if os.path.exists(geo_file):
                with open(geo_file, 'r') as f:
                    self.geographic_data = json.load(f)
                logger.info("Loaded geographic coverage data")
            
            # Load robustness analysis
            robustness_file = os.path.join(self.analysis_path, "robustness_analysis.json")
            if os.path.exists(robustness_file):
                with open(robustness_file, 'r') as f:
                    self.robustness_data = json.load(f)
                logger.info("Loaded robustness analysis")
            
            # Load centrality data
            centrality_file = os.path.join(self.analysis_path, "centrality_analysis.csv")
            if os.path.exists(centrality_file):
                self.centrality_data = pd.read_csv(centrality_file)
                logger.info(f"Loaded centrality data for {len(self.centrality_data)} stops")
            
            # Load community detection data
            community_file = os.path.join(self.analysis_path, "community_detection.csv")
            if os.path.exists(community_file):
                self.community_data = pd.read_csv(community_file)
                logger.info(f"Loaded community data for {len(self.community_data)} stops")
                
        except Exception as e:
            logger.error(f"Error loading analysis data: {e}")
    
    def get_comprehensive_network_stats(self):
        """Get comprehensive network statistics"""
        stats = {
            'total_stops': self.network_properties.get('num_nodes', len(self.graph.nodes)),
            'total_connections': self.network_properties.get('num_edges', len(self.graph.edges)),
            'network_density': self.network_properties.get('density', 0),
            'connected_components': self.network_properties.get('num_connected_components', 1),
            'avg_degree': self.network_properties.get('avg_degree', 0),
            'max_degree': self.network_properties.get('max_degree', 0),
            'avg_path_length': self.network_properties.get('avg_path_length', 0),
            'diameter': self.network_properties.get('diameter', 0),
            'avg_clustering': self.network_properties.get('avg_clustering', 0),
            'agencies': self.network_properties.get('agency_distribution', {})
        }
        
        # Add top hubs from centrality analysis
        if self.centrality_data is not None:
            top_hubs = self.centrality_data.nlargest(20, 'pagerank')[
                ['stop_name', 'agency_name', 'pagerank', 'betweenness', 'degree', 'closeness']
            ].to_dict('records')
            stats['top_hubs'] = top_hubs
        
        return stats
    
    def get_centrality_analysis(self):
        """Get detailed centrality analysis"""
        if self.centrality_data is None:
            return {'error': 'Centrality data not available'}
        
        return {
            'top_pagerank': self.centrality_data.nlargest(20, 'pagerank').to_dict('records'),
            'top_betweenness': self.centrality_data.nlargest(20, 'betweenness').to_dict('records'),
            'top_degree': self.centrality_data.nlargest(20, 'degree').to_dict('records'),
            'top_closeness': self.centrality_data.nlargest(20, 'closeness').to_dict('records'),
            'statistics': {
                'avg_pagerank': self.centrality_data['pagerank'].mean(),
                'avg_betweenness': self.centrality_data['betweenness'].mean(),
                'avg_degree': self.centrality_data['degree'].mean(),
                'avg_closeness': self.centrality_data['closeness'].mean()
            }
        }
    
    def get_robustness_analysis(self):
        """Get network robustness analysis"""
        if not self.robustness_data:
            return {'error': 'Robustness data not available'}
        
        # Convert robustness data to chart format
        connectivity_loss = []
        for i in range(11):  # 0 to 10 hubs removed
            key = f'removed_{i}' if i > 0 else 'original'
            if key in self.robustness_data:
                data_point = self.robustness_data[key]
                connectivity_loss.append({
                    'hubs_removed': i,
                    'connectivity': data_point.get('connectivity_ratio', 1.0),
                    'components': data_point.get('components', 1),
                    'largest_cc_size': data_point.get('largest_cc_size', 0)
                })
        
        return {
            'connectivity_loss': connectivity_loss,
            'summary': {
                'original_components': self.robustness_data.get('original', {}).get('components', 1),
                'original_largest_cc': self.robustness_data.get('original', {}).get('largest_cc_size', 0),
                'final_connectivity': connectivity_loss[-1]['connectivity'] if connectivity_loss else 1.0
            }
        }
    
    def get_geographic_coverage(self):
        """Get geographic coverage analysis"""
        if not self.geographic_data:
            return {'error': 'Geographic data not available'}
        
        return {
            'bounds': self.geographic_data.get('bounds', {}),
            'coverage_area_km2': self.geographic_data.get('coverage_area_km2', 0),
            'agency_coverage': self.geographic_data.get('agency_coverage', {}),
            'summary': {
                'total_area': self.geographic_data.get('coverage_area_km2', 0),
                'lat_range': (
                    self.geographic_data.get('bounds', {}).get('max_lat', 0) - 
                    self.geographic_data.get('bounds', {}).get('min_lat', 0)
                ),
                'lon_range': (
                    self.geographic_data.get('bounds', {}).get('max_lon', 0) - 
                    self.geographic_data.get('bounds', {}).get('min_lon', 0)
                )
            }
        }
    
    def get_community_analysis(self):
        """Get community detection analysis"""
        if self.community_data is None:
            return {'error': 'Community data not available'}
        
        # Calculate community statistics
        community_stats = self.community_data.groupby('community').size().sort_values(ascending=False)
        
        return {
            'num_communities': len(community_stats),
            'largest_community': int(community_stats.iloc[0]) if len(community_stats) > 0 else 0,
            'smallest_community': int(community_stats.iloc[-1]) if len(community_stats) > 0 else 0,
            'avg_community_size': float(community_stats.mean()),
            'community_distribution': community_stats.head(20).to_dict(),
            'communities_by_agency': self.community_data.groupby(['community', 'agency_name']).size().to_dict()
        }
    
    def get_degree_distribution(self):
        """Calculate degree distribution for chart"""
        if self.centrality_data is None:
            return {'error': 'Centrality data not available'}
        
        degree_counts = self.centrality_data['degree'].value_counts().sort_index()
        
        return {
            'labels': [str(int(degree)) for degree in degree_counts.index],
            'data': degree_counts.values.tolist(),
            'statistics': {
                'max_degree': int(self.centrality_data['degree'].max()),
                'min_degree': int(self.centrality_data['degree'].min()),
                'avg_degree': float(self.centrality_data['degree'].mean())
            }
        }
    
    # NEW ADVANCED ANALYSIS METHODS
    def get_advanced_centrality_analysis(self):
        """Get advanced centrality analysis including PageRank and betweenness"""
        if self.graph is None or len(self.graph.nodes()) == 0:
            return {'error': 'No graph data available'}
        
        try:
            # Calculate different centrality measures
            pagerank = nx.pagerank(self.graph, weight='weight')
            betweenness = nx.betweenness_centrality(self.graph, weight='weight')
            closeness = nx.closeness_centrality(self.graph, distance='weight')
            degree_centrality = nx.degree_centrality(self.graph)
            
            # Create combined dataframe
            centrality_data = []
            for node in self.graph.nodes():
                node_data = self.graph.nodes[node]
                centrality_data.append({
                    'stop_name': node_data.get('name', node),
                    'agency': node_data.get('agency', 'Unknown'),
                    'pagerank': pagerank.get(node, 0),
                    'betweenness': betweenness.get(node, 0),
                    'closeness': closeness.get(node, 0),
                    'degree_centrality': degree_centrality.get(node, 0),
                    'degree': self.graph.degree(node)
                })
            
            # Sort by PageRank
            centrality_data.sort(key=lambda x: x['pagerank'], reverse=True)
            
            return {
                'centrality_data': centrality_data[:50],  # Top 50
                'top_pagerank': centrality_data[:20],
                'statistics': {
                    'avg_pagerank': sum(d['pagerank'] for d in centrality_data) / len(centrality_data),
                    'avg_betweenness': sum(d['betweenness'] for d in centrality_data) / len(centrality_data),
                    'avg_closeness': sum(d['closeness'] for d in centrality_data) / len(centrality_data),
                    'max_degree': max(d['degree'] for d in centrality_data),
                    'avg_degree': sum(d['degree'] for d in centrality_data) / len(centrality_data)
                }
            }
        except Exception as e:
            logger.error(f"Error in advanced centrality analysis: {e}")
            return {'error': str(e)}

    def get_network_robustness_analysis(self):
        """Simulate network attacks and measure robustness"""
        if self.graph is None or len(self.graph.nodes()) == 0:
            return {'error': 'No graph data available'}
        
        try:
            # Convert to undirected for robustness analysis
            G = self.graph.to_undirected() if self.graph.is_directed() else self.graph.copy()
            
            # Calculate initial metrics
            initial_components = nx.number_connected_components(G)
            initial_largest = len(max(nx.connected_components(G), key=len))
            
            # Get degree centrality for targeted attack
            degree_centrality = nx.degree_centrality(G)
            sorted_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)
            
            # Simulate attack by removing high-degree nodes
            attack_results = []
            G_attack = G.copy()
            
            for i, (node, centrality) in enumerate(sorted_nodes):
                if i > 50:  # Limit to first 50 nodes for performance
                    break
                    
                if node in G_attack:
                    G_attack.remove_node(node)
                    
                    if len(G_attack.nodes()) == 0:
                        break
                        
                    components = list(nx.connected_components(G_attack))
                    largest_component_size = len(max(components, key=len)) if components else 0
                    
                    attack_results.append({
                        'nodes_removed': i + 1,
                        'nodes_remaining': len(G_attack.nodes()),
                        'components': len(components),
                        'largest_component_size': largest_component_size,
                        'connectivity_ratio': largest_component_size / len(G_attack.nodes()) if len(G_attack.nodes()) > 0 else 0,
                        'removed_node': node,
                        'removed_centrality': centrality
                    })
            
            return {
                'initial_stats': {
                    'total_nodes': len(G.nodes()),
                    'total_edges': len(G.edges()),
                    'components': initial_components,
                    'largest_component': initial_largest
                },
                'attack_results': attack_results,
                'vulnerability_score': len([r for r in attack_results if r['connectivity_ratio'] < 0.5]) / len(attack_results) if attack_results else 0
            }
            
        except Exception as e:
            logger.error(f"Error in robustness analysis: {e}")
            return {'error': str(e)}

    def get_degree_distribution_analysis(self):
        """Analyze degree distribution patterns"""
        if self.graph is None or len(self.graph.nodes()) == 0:
            return {'error': 'No graph data available'}
        
        try:
            # Get degrees
            if self.graph.is_directed():
                in_degrees = [d for n, d in self.graph.in_degree()]
                out_degrees = [d for n, d in self.graph.out_degree()]
                total_degrees = [in_degrees[i] + out_degrees[i] for i in range(len(in_degrees))]
            else:
                degrees = [d for n, d in self.graph.degree()]
                total_degrees = degrees
            
            # Count occurrences
            degree_counts = Counter(total_degrees)
            total_nodes = len(total_degrees)
            
            # Create distribution data
            distribution_data = []
            for degree, count in sorted(degree_counts.items()):
                distribution_data.append({
                    'degree': degree,
                    'count': count,
                    'probability': count / total_nodes,
                    'cumulative': sum(degree_counts[d] for d in range(degree + 1)) / total_nodes
                })
            
            return {
                'distribution': distribution_data,
                'statistics': {
                    'max_degree': max(total_degrees),
                    'min_degree': min(total_degrees),
                    'avg_degree': sum(total_degrees) / len(total_degrees),
                    'median_degree': sorted(total_degrees)[len(total_degrees)//2],
                    'std_degree': (sum((d - sum(total_degrees)/len(total_degrees))**2 for d in total_degrees) / len(total_degrees))**0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error in degree distribution analysis: {e}")
            return {'error': str(e)}

    def get_community_detection_analysis(self):
        """Perform community detection using multiple algorithms"""
        if self.graph is None or len(self.graph.nodes()) == 0:
            return {'error': 'No graph data available'}
        
        try:
            # Convert to undirected for community detection
            G = self.graph.to_undirected() if self.graph.is_directed() else self.graph.copy()
            
            # Louvain community detection
            try:
                louvain_communities = nx.community.louvain_communities(G, weight='weight')
                louvain_modularity = nx.community.modularity(G, louvain_communities, weight='weight')
            except:
                louvain_communities = []
                louvain_modularity = 0
            
            # Label propagation
            try:
                label_communities = list(nx.community.label_propagation_communities(G))
                label_modularity = nx.community.modularity(G, label_communities, weight='weight')
            except:
                label_communities = []
                label_modularity = 0
            
            # Prepare community data
            community_data = []
            if louvain_communities:
                for i, community in enumerate(louvain_communities):
                    community_nodes = []
                    for node in community:
                        node_data = self.graph.nodes.get(node, {})
                        community_nodes.append({
                            'node': node,
                            'name': node_data.get('name', node),
                            'agency': node_data.get('agency', 'Unknown')
                        })
                    
                    community_data.append({
                        'community_id': i,
                        'size': len(community),
                        'nodes': community_nodes[:10],  # Limit for response size
                        'agencies': list(set(n['agency'] for n in community_nodes))
                    })
            
            return {
                'louvain': {
                    'num_communities': len(louvain_communities),
                    'modularity': louvain_modularity,
                    'communities': community_data
                },
                'label_propagation': {
                    'num_communities': len(label_communities),
                    'modularity': label_modularity
                },
                'statistics': {
                    'largest_community': max(len(c) for c in louvain_communities) if louvain_communities else 0,
                    'smallest_community': min(len(c) for c in louvain_communities) if louvain_communities else 0,
                    'avg_community_size': sum(len(c) for c in louvain_communities) / len(louvain_communities) if louvain_communities else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in community detection: {e}")
            return {'error': str(e)}

    def get_network_efficiency_analysis(self):
        """Calculate network efficiency metrics"""
        if self.graph is None or len(self.graph.nodes()) == 0:
            return {'error': 'No graph data available'}
        
        try:
            G = self.graph.to_undirected() if self.graph.is_directed() else self.graph.copy()
            
            # Global efficiency
            try:
                global_efficiency = nx.global_efficiency(G)
            except:
                global_efficiency = 0
            
            # Local efficiency
            try:
                local_efficiency = nx.local_efficiency(G)
            except:
                local_efficiency = 0
            
            # Average path length for largest component
            largest_cc = max(nx.connected_components(G), key=len)
            largest_subgraph = G.subgraph(largest_cc)
            
            try:
                avg_path_length = nx.average_shortest_path_length(largest_subgraph, weight='weight')
                diameter = nx.diameter(largest_subgraph)
                radius = nx.radius(largest_subgraph)
            except:
                avg_path_length = 0
                diameter = 0
                radius = 0
            
            # Clustering coefficient
            try:
                avg_clustering = nx.average_clustering(G, weight='weight')
            except:
                avg_clustering = nx.average_clustering(G)
            
            return {
                'global_efficiency': global_efficiency,
                'local_efficiency': local_efficiency,
                'avg_path_length': avg_path_length,
                'diameter': diameter,
                'radius': radius,
                'clustering_coefficient': avg_clustering,
                'small_world_coefficient': avg_clustering / (avg_path_length / len(G.nodes())) if avg_path_length > 0 else 0,
                'network_density': nx.density(G),
                'largest_component_size': len(largest_cc),
                'largest_component_ratio': len(largest_cc) / len(G.nodes())
            }
            
        except Exception as e:
            logger.error(f"Error in efficiency analysis: {e}")
            return {'error': str(e)}
    
    def analyze_route_impact(self, route_data):
        """Analyze the impact of a specific route on the network"""
        if not route_data or 'steps' not in route_data:
            return {'error': 'Invalid route data'}
        
        # Extract stops and agencies used in the route
        stops_used = set()
        agencies_used = set()
        
        for step in route_data['steps']:
            if step.get('type') == 'transit':
                if step.get('agency'):
                    agencies_used.add(step['agency'])
                if step.get('stops'):
                    for stop in step['stops']:
                        stops_used.add(stop.get('stop_id', ''))
        
        # Calculate impact metrics
        total_stops = len(self.graph.nodes)
        network_utilization = (len(stops_used) / total_stops * 100) if total_stops > 0 else 0
        
        # Find affected hubs
        affected_hubs = []
        if self.centrality_data is not None:
            for stop_id in stops_used:
                hub_data = self.centrality_data[
                    self.centrality_data['stop_id_full'] == stop_id
                ]
                if not hub_data.empty:
                    hub_info = hub_data.iloc[0]
                    if hub_info['pagerank'] > self.centrality_data['pagerank'].quantile(0.9):
                        affected_hubs.append({
                            'stop_name': hub_info['stop_name'],
                            'agency': hub_info['agency_name'],
                            'pagerank': hub_info['pagerank'],
                            'importance': 'high' if hub_info['pagerank'] > self.centrality_data['pagerank'].quantile(0.95) else 'medium'
                        })
        
        return {
            'stops_used': len(stops_used),
            'agencies_used': list(agencies_used),
            'network_utilization_percent': round(network_utilization, 2),
            'affected_hubs': affected_hubs,
            'route_efficiency': self.calculate_route_efficiency(route_data),
            'connectivity_impact': self.assess_connectivity_impact(stops_used)
        }
    
    def calculate_route_efficiency(self, route_data):
        """Calculate route efficiency score"""
        base_score = 100
        
        # Penalize for long travel times
        time_penalty = max(0, (route_data.get('total_time_minutes', 0) - 30) * 0.5)
        
        # Penalize for transfers
        transfer_penalty = route_data.get('transfers', 0) * 5
        
        # Bonus for using multiple agencies (multimodal efficiency)
        agencies = set()
        for step in route_data.get('steps', []):
            if step.get('type') == 'transit' and step.get('agency'):
                agencies.add(step['agency'])
        multimodal_bonus = (len(agencies) - 1) * 2
        
        score = max(20, base_score - time_penalty - transfer_penalty + multimodal_bonus)
        return round(score)
    
    def assess_connectivity_impact(self, stops_used):
        """Assess the connectivity impact of using specific stops"""
        if not self.centrality_data is not None:
            return 'low'
        
        total_pagerank = 0
        for stop_id in stops_used:
            stop_data = self.centrality_data[
                self.centrality_data['stop_id_full'] == stop_id
            ]
            if not stop_data.empty:
                total_pagerank += stop_data.iloc[0]['pagerank']
        
        # Classify impact based on cumulative PageRank
        if total_pagerank > 0.01:
            return 'high'
        elif total_pagerank > 0.005:
            return 'medium'
        else:
            return 'low'
    
    # Include all the original methods for geocoding, route planning, etc.
    def geocode_address(self, address):
        """Convert address to coordinates with enhanced handling"""
        try:
            location = self.geocoder.geocode(address, timeout=10)
            
            if not location and "atlanta" not in address.lower() and "ga" not in address.lower():
                address_with_atlanta = address + ", Atlanta, GA"
                location = self.geocoder.geocode(address_with_atlanta, timeout=10)
            
            if not location and "ga" not in address.lower() and "georgia" not in address.lower():
                address_with_ga = address + ", GA"
                location = self.geocoder.geocode(address_with_ga, timeout=10)
            
            if not location:
                import re
                simplified_address = re.sub(r'^\d+\s+', '', address)
                location = self.geocoder.geocode(simplified_address + ", Atlanta, GA", timeout=10)
            
            if location:
                return {
                    'lat': location.latitude,
                    'lon': location.longitude,
                    'formatted_address': location.address
                }
                
        except Exception as e:
            logger.error(f"Geocoding error for '{address}': {e}")
        
        return None
    
    def find_nearby_stops(self, lat, lon, max_distance_km=1.0, max_results=10):
        """Find transit stops near given coordinates"""
        nearby_stops = []
        
        for _, stop in self.stops_data.iterrows():
            if pd.notna(stop['stop_lat']) and pd.notna(stop['stop_lon']):
                distance = geodesic((lat, lon), (stop['stop_lat'], stop['stop_lon'])).kilometers
                
                if distance <= max_distance_km:
                    nearby_stops.append({
                        'stop_id': stop['stop_id_full'],
                        'name': stop['stop_name'],
                        'agency': stop['agency_name'],
                        'lat': stop['stop_lat'],
                        'lon': stop['stop_lon'],
                        'distance_km': distance
                    })
        
        nearby_stops.sort(key=lambda x: x['distance_km'])
        return nearby_stops[:max_results]
    
    def plan_route(self, origin_lat, origin_lon, dest_lat, dest_lon, 
                   max_walking_km=0.5, preferences=None):
        """Plan route between two locations"""
        if preferences is None:
            preferences = {'optimize': 'time', 'max_transfers': 3}
        
        if 'max_walking_km' in preferences:
            max_walking_km = preferences['max_walking_km']
        
        origin_stops = self.find_nearby_stops(origin_lat, origin_lon, max_walking_km)
        dest_stops = self.find_nearby_stops(dest_lat, dest_lon, max_walking_km)
        
        if not origin_stops or not dest_stops:
            return {'error': 'No nearby transit stops found'}
        
        best_routes = []
        
        for origin_stop in origin_stops[:3]:
            for dest_stop in dest_stops[:3]:
                try:
                    path = nx.shortest_path(
                        self.graph, 
                        origin_stop['stop_id'], 
                        dest_stop['stop_id'],
                        weight='weight'
                    )
                    
                    total_time = nx.shortest_path_length(
                        self.graph,
                        origin_stop['stop_id'],
                        dest_stop['stop_id'],
                        weight='weight'
                    )
                    
                    walking_to_transit = (origin_stop['distance_km'] / 5.0) * 3600
                    walking_from_transit = (dest_stop['distance_km'] / 5.0) * 3600
                    total_time += walking_to_transit + walking_from_transit
                    
                    route_details = self.build_route_details(
                        path, origin_lat, origin_lon, dest_lat, dest_lon,
                        origin_stop, dest_stop, walking_to_transit, walking_from_transit
                    )
                    
                    route_data = {
                        'total_time_minutes': total_time / 60,
                        'total_distance_km': sum([step.get('distance_km', 0) for step in route_details]),
                        'transfers': len(set([step.get('agency', '') for step in route_details if step.get('agency')])) - 1,
                        'steps': route_details,
                        'path_coordinates': self.get_path_coordinates(path, origin_lat, origin_lon, dest_lat, dest_lon)
                    }
                    
                    best_routes.append(route_data)
                    
                except nx.NetworkXNoPath:
                    continue
                except Exception as e:
                    logger.error(f"Error planning route: {e}")
                    continue
        
        if preferences['optimize'] == 'time':
            best_routes.sort(key=lambda x: x['total_time_minutes'])
        elif preferences['optimize'] == 'transfers':
            best_routes.sort(key=lambda x: (x['transfers'], x['total_time_minutes']))
        
        return {'routes': best_routes[:5]}
    
    def build_route_details(self, path, origin_lat, origin_lon, dest_lat, dest_lon,
                           origin_stop, dest_stop, walking_to_time, walking_from_time):
        """Build detailed route instructions"""
        details = []
        
        # Walking to transit
        details.append({
            'type': 'walk',
            'instruction': f"Walk to {origin_stop['name']}",
            'duration_minutes': walking_to_time / 60,
            'distance_km': origin_stop['distance_km'],
            'from_lat': origin_lat,
            'from_lon': origin_lon,
            'to_lat': self.graph.nodes[origin_stop['stop_id']]['lat'],
            'to_lon': self.graph.nodes[origin_stop['stop_id']]['lon']
        })
        
        # Transit segments
        current_route = None
        current_agency = None
        segment_stops = []
        
        for i in range(len(path) - 1):
            current_stop = path[i]
            next_stop = path[i + 1]
            
            edge_data = self.graph[current_stop][next_stop]
            route = edge_data.get('route', 'Unknown')
            agency = edge_data.get('agency', 'Unknown')
            
            if route != current_route or agency != current_agency:
                if segment_stops:
                    details.append({
                        'type': 'transit',
                        'route': current_route,
                        'agency': current_agency,
                        'instruction': f"Take {current_route} ({current_agency})",
                        'stops': segment_stops,
                        'duration_minutes': sum([s.get('travel_time', 0) for s in segment_stops]) / 60
                    })
                
                current_route = route
                current_agency = agency
                segment_stops = []
            
            stop_data = self.graph.nodes[current_stop]
            segment_stops.append({
                'stop_id': current_stop,
                'name': stop_data['name'],
                'lat': stop_data['lat'],
                'lon': stop_data['lon'],
                'travel_time': edge_data.get('weight', 0)
            })
        
        if segment_stops:
            details.append({
                'type': 'transit',
                'route': current_route,
                'agency': current_agency,
                'instruction': f"Take {current_route} ({current_agency})",
                'stops': segment_stops,
                'duration_minutes': sum([s.get('travel_time', 0) for s in segment_stops]) / 60
            })
        
        # Walking from transit
        details.append({
            'type': 'walk',
            'instruction': f"Walk from {dest_stop['name']} to destination",
            'duration_minutes': walking_from_time / 60,
            'distance_km': dest_stop['distance_km'],
            'from_lat': self.graph.nodes[dest_stop['stop_id']]['lat'],
            'from_lon': self.graph.nodes[dest_stop['stop_id']]['lon'],
            'to_lat': dest_lat,
            'to_lon': dest_lon
        })
        
        return details
    
    def get_path_coordinates(self, path, origin_lat, origin_lon, dest_lat, dest_lon):
        """Get coordinates for route visualization"""
        coordinates = [(origin_lat, origin_lon)]
        
        for stop_id in path:
            stop_data = self.graph.nodes[stop_id]
            coordinates.append((stop_data['lat'], stop_data['lon']))
        
        coordinates.append((dest_lat, dest_lon))
        return coordinates

# Initialize enhanced API
transit_api = EnhancedAtlantaTransitAPI()

app = Flask(__name__)
CORS(app)

# Main Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    """Enhanced analysis dashboard"""
    return render_template('analysis.html')

@app.route('/map')
def map_page():
    """Map page"""
    return render_template('map.html')

# Enhanced API Endpoints
@app.route('/api/network-analysis')
def enhanced_network_analysis():
    """Get comprehensive network analysis"""
    stats = transit_api.get_comprehensive_network_stats()
    return jsonify(stats)

@app.route('/api/centrality-analysis')
def centrality_analysis():
    """Get detailed centrality analysis"""
    analysis = transit_api.get_centrality_analysis()
    return jsonify(analysis)

@app.route('/api/robustness-analysis')
def robustness_analysis():
    """Get network robustness analysis"""
    analysis = transit_api.get_robustness_analysis()
    return jsonify(analysis)

@app.route('/api/geographic-coverage')
def geographic_coverage():
    """Get geographic coverage analysis"""
    analysis = transit_api.get_geographic_coverage()
    return jsonify(analysis)

@app.route('/api/community-analysis')
def community_analysis():
    """Get community detection analysis"""
    analysis = transit_api.get_community_analysis()
    return jsonify(analysis)

@app.route('/api/degree-distribution')
def degree_distribution():
    """Get degree distribution for charts"""
    distribution = transit_api.get_degree_distribution()
    return jsonify(distribution)

# NEW ADVANCED API ENDPOINTS
@app.route('/api/advanced-centrality')
def advanced_centrality():
    """Get advanced centrality analysis including PageRank"""
    analysis = transit_api.get_advanced_centrality_analysis()
    return jsonify(analysis)

@app.route('/api/network-robustness')
def network_robustness():
    """Get network robustness and attack simulation"""
    analysis = transit_api.get_network_robustness_analysis()
    return jsonify(analysis)

@app.route('/api/degree-distribution-detailed')
def degree_distribution_detailed():
    """Get detailed degree distribution analysis"""
    analysis = transit_api.get_degree_distribution_analysis()
    return jsonify(analysis)

@app.route('/api/community-detection')
def community_detection():
    """Get community detection analysis"""
    analysis = transit_api.get_community_detection_analysis()
    return jsonify(analysis)

@app.route('/api/network-efficiency')
def network_efficiency():
    """Get network efficiency metrics"""
    analysis = transit_api.get_network_efficiency_analysis()
    return jsonify(analysis)

@app.route('/api/route-impact', methods=['POST'])
def analyze_route_impact():
    """Analyze the impact of a specific route on the network"""
    data = request.get_json()
    route_data = data.get('route', {})
    
    impact_analysis = transit_api.analyze_route_impact(route_data)
    return jsonify(impact_analysis)

# Original API endpoints (keeping for compatibility)
@app.route('/api/geocode', methods=['POST'])
def geocode():
    """Geocode an address"""
    data = request.get_json()
    address = data.get('address', '')
    
    result = transit_api.geocode_address(address)
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Address not found'}), 404

@app.route('/api/stops/nearby', methods=['GET'])
def nearby_stops():
    """Find nearby transit stops"""
    lat = float(request.args.get('lat', 0))
    lon = float(request.args.get('lon', 0))
    max_distance = float(request.args.get('max_distance', 10))
    
    stops = transit_api.find_nearby_stops(lat, lon, max_distance)
    return jsonify({'stops': stops})

@app.route('/api/plan-trip', methods=['POST'])
def plan_trip():
    """Plan a trip between two locations with enhanced analysis"""
    data = request.get_json()
    
    origin = data.get('origin', {})
    destination = data.get('destination', {})
    preferences = data.get('preferences', {})
    
    origin_lat = origin.get('lat')
    origin_lon = origin.get('lon')
    dest_lat = destination.get('lat')
    dest_lon = destination.get('lon')
    
    if not origin_lat and origin.get('address'):
        geocoded = transit_api.geocode_address(origin['address'])
        if geocoded:
            origin_lat, origin_lon = geocoded['lat'], geocoded['lon']
    
    if not dest_lat and destination.get('address'):
        geocoded = transit_api.geocode_address(destination['address'])
        if geocoded:
            dest_lat, dest_lon = geocoded['lat'], geocoded['lon']
    
    if not all([origin_lat, origin_lon, dest_lat, dest_lon]):
        return jsonify({'error': 'Invalid origin or destination coordinates'}), 400
    
    result = transit_api.plan_route(origin_lat, origin_lon, dest_lat, dest_lon, preferences=preferences)
    
    # Add impact analysis for each route
    if 'routes' in result:
        for route in result['routes']:
            route['network_impact'] = transit_api.analyze_route_impact(route)
    
    return jsonify(result)

@app.route('/api/map-data', methods=['GET'])
def get_map_data():
    """Get data for map visualization"""
    try:
        if transit_api.stops_data.empty:
            return jsonify({
                'error': 'No transit data available',
                'stops': [],
                'center': {'lat': 33.7490, 'lon': -84.3880}
            })
        
        # Find coordinate columns
        lat_col = None
        lon_col = None
        
        lat_options = ['stop_lat', 'lat', 'latitude', 'stop_latitude', 'Lat', 'y']
        lon_options = ['stop_lon', 'lon', 'longitude', 'stop_longitude', 'Lon', 'lng', 'x']
        
        for col in lat_options:
            if col in transit_api.stops_data.columns:
                lat_col = col
                break
        
        for col in lon_options:
            if col in transit_api.stops_data.columns:
                lon_col = col
                break
        
        if not lat_col or not lon_col:
            return jsonify({
                'error': 'Latitude/longitude columns not found',
                'available_columns': list(transit_api.stops_data.columns),
                'stops': [],
                'center': {'lat': 33.7490, 'lon': -84.3880}
            }), 500
        
        stops_data = transit_api.stops_data.dropna(subset=[lat_col, lon_col])
        
        if stops_data.empty:
            return jsonify({
                'error': 'No valid coordinate data available',
                'stops': [],
                'center': {'lat': 33.7490, 'lon': -84.3880}
            })
        
        stops_list = []
        for _, stop in stops_data.iterrows():
            stop_name = (stop.get('stop_name') or 
                        stop.get('name') or 
                        stop.get('stop_id') or 
                        stop.get('stop_id_full') or
                        'Unknown Stop')
            
            agency_name = (stop.get('agency_name') or 
                          stop.get('agency') or 
                          stop.get('agency_id') or 
                          'Unknown Agency')
            
            try:
                stops_list.append({
                    'id': stop.get('stop_id_full', stop.get('stop_id', '')),
                    'name': str(stop_name),
                    'lat': float(stop[lat_col]),
                    'lon': float(stop[lon_col]),
                    'agency': str(agency_name)
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing stop {stop.get('stop_id', 'unknown')}: {e}")
                continue
        
        try:
            center_lat = float(stops_data[lat_col].mean())
            center_lon = float(stops_data[lon_col].mean())
        except:
            center_lat, center_lon = 33.7490, -84.3880
        
        map_data = {
            'stops': stops_list,
            'center': {
                'lat': center_lat,
                'lon': center_lon
            },
            'total_stops': len(stops_list)
        }
        
        return jsonify(map_data)
        
    except Exception as e:
        logger.error(f"Error in get_map_data: {str(e)}")
        return jsonify({
            'error': str(e),
            'stops': [],
            'center': {'lat': 33.7490, 'lon': -84.3880}
        }), 500
    
    # Add these new API endpoints to your Flask app (flask_app.py)

@app.route('/api/analysis-results')
def get_analysis_results():
    """Get all analysis results generated by the notebook script"""
    results_dir = "static/analysis_results/data"
    results = {}
    
    try:
        # Load basic metrics
        with open(f"{results_dir}/basic_metrics.json", 'r') as f:
            results['basic_metrics'] = json.load(f)
    except FileNotFoundError:
        results['basic_metrics'] = None
    
    try:
        # Load centrality analysis
        centrality_df = pd.read_csv(f"{results_dir}/centrality_analysis.csv")
        results['centrality'] = {
            'top_pagerank': centrality_df.nlargest(20, 'pagerank').to_dict('records'),
            'top_betweenness': centrality_df.nlargest(20, 'betweenness').to_dict('records'),
            'total_nodes': len(centrality_df)
        }
    except FileNotFoundError:
        results['centrality'] = None
    
    try:
        # Load degree distribution
        with open(f"{results_dir}/degree_distribution.json", 'r') as f:
            results['degree_distribution'] = json.load(f)
    except FileNotFoundError:
        results['degree_distribution'] = None
    
    try:
        # Load attack simulation results
        with open(f"{results_dir}/attack_simulation.json", 'r') as f:
            results['attack_simulation'] = json.load(f)
    except FileNotFoundError:
        results['attack_simulation'] = None
    
    try:
        # Load summary text
        with open(f"{results_dir}/analysis_summary.txt", 'r') as f:
            results['summary'] = f.read()
    except FileNotFoundError:
        results['summary'] = "Analysis summary not available"
    
    try:
        # Load centrality text output
        with open(f"{results_dir}/centrality_text_output.txt", 'r') as f:
            results['centrality_text'] = f.read()
    except FileNotFoundError:
        results['centrality_text'] = "Centrality text output not available"
    
    try:
        # Load connectivity analysis
        with open(f"{results_dir}/connectivity_analysis.txt", 'r') as f:
            results['connectivity_text'] = f.read()
    except FileNotFoundError:
        results['connectivity_text'] = "Connectivity analysis not available"
    
    return jsonify(results)

@app.route('/api/analysis-images')
def get_analysis_images():
    """Get list of available analysis images"""
    images_dir = "static/analysis_results/images"
    available_images = []
    
    image_files = [
        'pagerank_visualization.png',
        'degree_distribution.png', 
        'network_attacks.png',
        'network_after_degree_attack.png',
        'network_after_closeness_attack.png',
        'full_network.png'
    ]
    
    for image_file in image_files:
        image_path = f"{images_dir}/{image_file}"
        if os.path.exists(image_path):
            available_images.append({
                'filename': image_file,
                'title': image_file.replace('_', ' ').replace('.png', '').title(),
                'url': f"/static/analysis_results/images/{image_file}"
            })
    
    return jsonify({'images': available_images})

@app.route('/run-analysis', methods=['POST'])
def run_analysis():
    """Trigger the analysis script to run"""
    try:
        # Import and run the analysis
        import subprocess
        import sys
        
        # Run the analysis script
        result = subprocess.run([
            sys.executable, 'network_analysis_generator.py'
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'Analysis completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Analysis failed',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'Analysis timed out (>30 minutes)'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error running analysis: {str(e)}'
        }), 500

# Health check and status endpoints
@app.route('/health')
def health_check():
    """Enhanced health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'data_loaded': len(transit_api.stops_data) > 0,
        'analysis_loaded': {
            'network_properties': bool(transit_api.network_properties),
            'centrality_data': transit_api.centrality_data is not None,
            'community_data': transit_api.community_data is not None,
            'geographic_data': bool(transit_api.geographic_data),
            'robustness_data': bool(transit_api.robustness_data)
        },
        'total_stops': len(transit_api.stops_data),
        'total_connections': len(transit_api.graph.edges()) if transit_api.graph else 0,
        'version': '4.0 - Advanced Network Analysis'
    })

@app.route('/api/status')
def api_status():
    """Enhanced API status"""
    return jsonify({
        'status': 'operational',
        'version': '4.0',
        'interface': 'advanced_network_analysis',
        'capabilities': {
            'route_planning': True,
            'geocoding': True,
            'map_visualization': True,
            'network_analysis': True,
            'centrality_analysis': True,
            'robustness_analysis': True,
            'community_detection': True,
            'geographic_coverage': True,
            'route_impact_analysis': True,
            'multi_modal': True,
            'advanced_centrality': True,
            'network_efficiency': True,
            'degree_distribution': True,
            'vulnerability_assessment': True
        },
        'agencies': ['MARTA', 'CobbLinc', 'Gwinnett County Transit', 'Connect Douglas'],
        'data_stats': {
            'total_stops': len(transit_api.stops_data),
            'total_connections': len(transit_api.graph.edges()) if transit_api.graph else 0,
            'agencies_count': len(transit_api.stops_data['agency_name'].unique()) if not transit_api.stops_data.empty else 0,
            'analysis_files_loaded': sum([
                bool(transit_api.network_properties),
                transit_api.centrality_data is not None,
                transit_api.community_data is not None,
                bool(transit_api.geographic_data),
                bool(transit_api.robustness_data)
            ])
        }
    })

if __name__ == '__main__':
    print("ATLANTA TRANSIT NETWORK - ADVANCED ANALYSIS PLATFORM")
    print()
    print("MAIN INTERFACES:")
    print("   • Main Application: http://localhost:4455")
    print("   • Advanced Analysis: http://localhost:4455/analysis")
    print("   • Interactive Map: http://localhost:4455/map")
    print()
    print("NEW ADVANCED FEATURES:")
    print("   • Real-time Centrality Calculations (PageRank, Betweenness)")
    print("   • Network Robustness & Attack Simulations")
    print("   • Community Detection (Louvain & Label Propagation)")
    print("   • Degree Distribution Analysis")
    print("   • Network Efficiency Metrics")
    print("   • Vulnerability Assessment")
    print()
    print("API ENDPOINTS:")
    print("   • /api/advanced-centrality - Real-time centrality analysis")
    print("   • /api/network-robustness - Attack simulation results")
    print("   • /api/community-detection - Community structure analysis")
    print("   • /api/network-efficiency - Efficiency & performance metrics")
    print("   • /api/degree-distribution-detailed - Advanced degree analysis")
    print()
    print("ORIGINAL FEATURES:")
    print("   • Multi-modal route planning")
    print("   • Interactive network visualization")
    print("   • Geographic coverage analysis")
    print("   • Route impact assessment")
    print()
    print("SYSTEM STATUS:")
    print("   • Health Check: http://localhost:4455/health")
    print("   • API Status: http://localhost:4455/api/status")
    
    app.run(host='0.0.0.0', port=4455, debug=False)