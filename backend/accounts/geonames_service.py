"""
GeoNames Integration Service
Handles location searches to find cities within a specific radius
Website: http://www.geonames.org/
"""

import requests
from math import radians, sin, cos, sqrt, atan2

# GeoNames API configuration
GEONAMES_API_URL = "http://api.geonames.org/searchJSON"
GEONAMES_USERNAME = "your-geonames-username"  # Get it from: http://www.geonames.org/user/edit


class GeoNamesService:
    """
    Service for handling location searches using GeoNames API
    Finds cities within a specific distance from a state
    """
    
    # Target distance in kilometers (45 minutes ~ approximately 45-60 km depending on speed)
    # We'll use 75 km as the radius for "45 minutes away"
    TARGET_DISTANCE_KM = 75
    TOLERANCE_KM = 15  # +/- 15 km tolerance
    
    # US state centers (latitude, longitude) for reference
    STATE_COORDINATES = {
        'alabama': (32.8067, -86.7113),
        'alaska': (64.2008, -152.2782),
        'arizona': (33.7298, -111.4312),
        'arkansas': (34.9697, -92.3731),
        'california': (36.1163, -119.6674),
        'colorado': (39.0598, -105.3111),
        'connecticut': (41.5978, -72.7554),
        'delaware': (39.3185, -75.4769),
        'florida': (27.9947, -81.7603),
        'georgia': (33.0406, -83.6431),
        'hawaii': (21.0943, -156.4104),
        'idaho': (44.0682, -114.7420),
        'illinois': (40.3495, -88.9861),
        'indiana': (39.8494, -86.2604),
        'iowa': (42.0115, -93.2105),
        'kansas': (38.5266, -96.7265),
        'kentucky': (37.6681, -84.6701),
        'louisiana': (31.1695, -91.8749),
        'maine': (44.6939, -69.3819),
        'maryland': (39.0639, -76.8021),
        'massachusetts': (42.2352, -71.0275),
        'michigan': (43.3266, -84.5361),
        'minnesota': (45.6945, -93.9196),
        'mississippi': (32.7416, -89.6787),
        'missouri': (38.4561, -92.2884),
        'montana': (46.9219, -103.6006),
        'nebraska': (41.4925, -99.9018),
        'nevada': (38.8026, -116.4194),
        'new hampshire': (43.4525, -71.3129),
        'new jersey': (40.2206, -74.7597),
        'new mexico': (34.5199, -106.4373),
        'new york': (42.1657, -74.9481),
        'north carolina': (35.6301, -79.8064),
        'north dakota': (47.5289, -99.784),
        'ohio': (40.3888, -82.7649),
        'oklahoma': (35.5653, -97.4867),
        'oregon': (43.8041, -120.5542),
        'pennsylvania': (40.5908, -77.2098),
        'rhode island': (41.6809, -71.5118),
        'south carolina': (34.0007, -81.1637),
        'south dakota': (44.5998, -103.2191),
        'tennessee': (35.7478, -86.6923),
        'texas': (31.9686, -99.9018),
        'utah': (40.2338, -111.0934),
        'vermont': (43.9695, -72.5698),
        'virginia': (37.4316, -78.6569),
        'washington': (47.7511, -120.7401),
        'west virginia': (38.4912, -82.9006),
        'wisconsin': (44.2685, -89.6165),
        'wyoming': (42.7559, -107.3025),
    }
    
    @staticmethod
    def get_cities_45_mins_away(state_name):
        """
        Find cities within 45 minutes (75 km) from a given state center.
        
        Args:
            state_name: Name of the state (e.g., 'California', 'New York')
        
        Returns:
            {
                'success': bool,
                'cities': [
                    {
                        'name': str,
                        'latitude': float,
                        'longitude': float,
                        'population': int,
                        'distance_km': float,
                        'state': str,
                        'country': str
                    },
                    ...
                ],
                'count': int,
                'state_center': {'lat': float, 'lng': float},
                'search_radius_km': int
            }
        """
        
        try:
            # Get state coordinates
            state_lower = state_name.lower().strip()
            
            if state_lower not in GeoNamesService.STATE_COORDINATES:
                return {
                    'success': False,
                    'error': f'State "{state_name}" not found. Please check spelling.'
                }
            
            state_lat, state_lng = GeoNamesService.STATE_COORDINATES[state_lower]
            
            # Query GeoNames API for cities near the state
            cities = GeoNamesService._query_geonames(
                state_lat,
                state_lng,
                max_rows=200  # Get more results to filter
            )
            
            if not cities:
                return {
                    'success': False,
                    'error': f'No cities found near {state_name}'
                }
            
            # Filter cities by distance (45 min = 75 km)
            filtered_cities = []
            
            for city in cities:
                distance = GeoNamesService._calculate_distance(
                    state_lat, state_lng,
                    float(city['lat']), float(city['lng'])
                )
                
                # Include cities within tolerance range
                if (GeoNamesService.TARGET_DISTANCE_KM - GeoNamesService.TOLERANCE_KM 
                    <= distance <= 
                    GeoNamesService.TARGET_DISTANCE_KM + GeoNamesService.TOLERANCE_KM):
                    
                    city_info = {
                        'name': city['name'],
                        'latitude': float(city['lat']),
                        'longitude': float(city['lng']),
                        'population': int(city.get('population', 0)),
                        'distance_km': round(distance, 2),
                        'state': city.get('adminName1', ''),
                        'country': city.get('countryName', '')
                    }
                    filtered_cities.append(city_info)
            
            # Sort by distance
            filtered_cities.sort(key=lambda x: x['distance_km'])
            
            return {
                'success': True,
                'cities': filtered_cities,
                'count': len(filtered_cities),
                'state_center': {'lat': state_lat, 'lng': state_lng},
                'search_radius_km': GeoNamesService.TARGET_DISTANCE_KM,
                'tolerance_km': GeoNamesService.TOLERANCE_KM
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _query_geonames(latitude, longitude, max_rows=100):
        """
        Query GeoNames API for cities near given coordinates
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            max_rows: Maximum results to return
        
        Returns:
            List of city data from GeoNames
        """
        
        try:
            params = {
                'lat': latitude,
                'lng': longitude,
                'radius': 200,  # Search within 200 km radius
                'featureClass': 'P',  # P = city, villages, towns
                'maxRows': max_rows,
                'username': GEONAMES_USERNAME,
                'style': 'FULL'  # Return full data
            }
            
            response = requests.get(GEONAMES_API_URL, params=params, timeout=5)
            
            if response.status_code != 200:
                raise Exception(f"GeoNames API error: {response.status_code}")
            
            data = response.json()
            return data.get('geonames', [])
        
        except Exception as e:
            print(f"GeoNames Query Error: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        """
        Calculate great-circle distance between two points using Haversine formula
        
        Args:
            lat1, lng1: First coordinate
            lat2, lng2: Second coordinate
        
        Returns:
            Distance in kilometers
        """
        
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert degrees to radians
        lat1_rad = radians(lat1)
        lng1_rad = radians(lng1)
        lat2_rad = radians(lat2)
        lng2_rad = radians(lng2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
