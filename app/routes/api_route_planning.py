"""
API routes for route planning and optimization.
Uses OpenRouteService API for route optimization.
"""

from flask import Blueprint, jsonify, request
import requests
from ..utils.logging_utils import log_settings_action
from ..database import get_db_connection

route_planning_bp = Blueprint('route_planning_api', __name__, url_prefix='/api/route-planning')

# OpenRouteService API endpoint (free, no API key needed for basic usage)
ORS_API_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
ORS_OPTIMIZATION_URL = "https://api.openrouteservice.org/optimization"

# User's home and depot postcodes
HOME_POSTCODE = "M44HX"
DEPOT_POSTCODE = "WA5 7TN"


def geocode_postcode(postcode):
    """
    Convert UK postcode to lat/lon coordinates using Nominatim (free).
    Returns [longitude, latitude] or None if failed.
    """
    try:
        # Clean and format postcode properly
        postcode = postcode.strip().upper()
        # Remove extra spaces
        postcode = ' '.join(postcode.split())
        
        # Add space if missing (e.g., M44HX -> M4 4HX)
        if ' ' not in postcode and len(postcode) >= 5:
            # Insert space before last 3 characters
            postcode = postcode[:-3] + ' ' + postcode[-3:]
        
        # Use Nominatim API (free, no key needed)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f'{postcode}, United Kingdom',
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'TVS-Wages-App/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data and len(data) > 0:
            # Return as [lon, lat] for OSRM
            return [float(data[0]['lon']), float(data[0]['lat'])]
        
        return None
        
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Geocoding failed for {postcode}: {str(e)}', 'ERROR')
        return None


def optimize_waypoint_order(coordinates, optimization_mode='distance'):
    """
    Optimize waypoint order using nearest-neighbor algorithm to minimize crisscrossing.
    Returns optimized order of indices.
    """
    import math
    
    if len(coordinates) <= 2:
        return list(range(len(coordinates)))
    
    # Calculate distance between two points (Haversine formula)
    def haversine_distance(coord1, coord2):
        lon1, lat1 = coord1
        lon2, lat2 = coord2
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    # Nearest neighbor algorithm
    n = len(coordinates)
    visited = [False] * n
    order = []
    
    # Start from first point (home)
    current = 0
    order.append(current)
    visited[current] = True
    
    # Visit remaining points in nearest-neighbor order
    for _ in range(n - 1):
        nearest_dist = float('inf')
        nearest_idx = -1
        
        for i in range(n):
            if not visited[i]:
                dist = haversine_distance(coordinates[current], coordinates[i])
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i
        
        if nearest_idx != -1:
            order.append(nearest_idx)
            visited[nearest_idx] = True
            current = nearest_idx
    
    return order

def calculate_route_simple(coordinates, optimization_mode='distance'):
    """
    Calculate route through multiple waypoints using OpenRouteService.
    Route order: Home → Depot → Optimized Jobs → Home
    Only job waypoints are optimized, home and depot stay fixed.
    Returns route with distance and duration.
    """
    try:
        # Optimize job waypoints only
        # Structure: [Home, Depot, Job1, Job2, ..., JobN, Home]
        # Keep: Home (index 0), Depot (index 1), Home (index -1) fixed
        # Optimize: Jobs (indices 2 to -2)
        
        if len(coordinates) > 4:  # Home + Depot + at least 1 job + Home return
            home_start = coordinates[0]
            depot = coordinates[1]
            jobs = coordinates[2:-1]  # All jobs (exclude home start, depot, and home return)
            home_end = coordinates[-1]
            
            # Optimize job order starting from depot location
            jobs_with_depot = [depot] + jobs
            optimized_order = optimize_waypoint_order(jobs_with_depot, optimization_mode)
            
            # Rebuild coordinates: Home → Depot → Optimized Jobs → Home
            # Skip first item in optimized_order (it's the depot)
            optimized_jobs = [jobs_with_depot[i] for i in optimized_order[1:]]
            coordinates = [home_start, depot] + optimized_jobs + [home_end]
        
        # Use OSRM API (free, no key needed)
        # Format: lon,lat;lon,lat;...
        coords_str = ';'.join([f"{coord[0]},{coord[1]}" for coord in coordinates])
        
        url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            
            # Extract leg information (segments between waypoints)
            legs = []
            for leg in route.get('legs', []):
                legs.append({
                    'distance_meters': leg.get('distance', 0),
                    'duration_seconds': leg.get('duration', 0),
                    'distance_miles': round(leg.get('distance', 0) * 0.000621371, 2),
                    'duration_minutes': round(leg.get('duration', 0) / 60, 1)
                })
            
            return {
                'success': True,
                'total_distance_meters': route.get('distance', 0),
                'total_duration_seconds': route.get('duration', 0),
                'total_distance_miles': round(route.get('distance', 0) * 0.000621371, 2),
                'total_duration_minutes': round(route.get('duration', 0) / 60, 1),
                'legs': legs,
                'optimized_coordinates': coordinates  # Return optimized order
            }
        
        return {'success': False, 'error': 'No route found'}
        
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Route calculation failed: {str(e)}', 'ERROR')
        return {'success': False, 'error': str(e)}


@route_planning_bp.route('/optimize', methods=['POST'])
def optimize_route_for_date():
    """
    Optimize route for a specific date's jobs.
    Expects: { "date": "DD/MM/YYYY", "include_depot": true/false, "optimization_mode": "distance"|"time" }
    Returns optimized job order with distances and times.
    """
    try:
        data = request.get_json() or {}
        date = data.get('date')
        include_depot = data.get('include_depot', True)
        optimization_mode = data.get('optimization_mode', 'distance')  # 'distance' or 'time'
        
        if not date:
            return jsonify({'success': False, 'error': 'Date is required'}), 400
        
        # Get jobs for this date
        # Only optimize pending jobs - exclude completed, DNCO, and missed
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Only include pending jobs for route optimization
            cursor.execute("""
                SELECT id, job_number, customer, job_address, postcode, activity
                FROM run_sheet_jobs
                WHERE date = ?
                AND status NOT IN ('deleted', 'dnco', 'DNCO', 'completed', 'missed')
                ORDER BY id
            """, (date,))
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'id': row[0],
                    'job_number': row[1],
                    'customer': row[2],
                    'address': row[3],
                    'postcode': row[4],
                    'activity': row[5]
                })
        
        if not jobs:
            return jsonify({'success': False, 'error': 'No jobs found for this date'}), 404
        
        # Build waypoint list: Home -> [Depot] -> Jobs -> Home
        waypoints = []
        waypoint_info = []
        
        # 1. Start at home
        home_coords = geocode_postcode(HOME_POSTCODE)
        if not home_coords:
            return jsonify({'success': False, 'error': f'Could not geocode home postcode: {HOME_POSTCODE}'}), 400
        
        waypoints.append(home_coords)
        waypoint_info.append({
            'type': 'home',
            'label': 'Home',
            'postcode': HOME_POSTCODE
        })
        
        # 2. Add depot if requested
        if include_depot:
            depot_coords = geocode_postcode(DEPOT_POSTCODE)
            if depot_coords:
                waypoints.append(depot_coords)
                waypoint_info.append({
                    'type': 'depot',
                    'label': 'Depot',
                    'postcode': DEPOT_POSTCODE
                })
        
        # 3. Add all job postcodes
        job_waypoints = []
        for job in jobs:
            if job['postcode']:
                coords = geocode_postcode(job['postcode'])
                if coords:
                    waypoints.append(coords)
                    waypoint_info.append({
                        'type': 'job',
                        'job': job,
                        'label': f"Job {job['job_number']}",
                        'postcode': job['postcode']
                    })
                    job_waypoints.append(job)
                else:
                    log_settings_action('ROUTE_PLANNING', f"Could not geocode job {job['job_number']} postcode: {job['postcode']}", 'WARNING')
        
        # 4. Return to home
        waypoints.append(home_coords)
        waypoint_info.append({
            'type': 'home',
            'label': 'Home (Return)',
            'postcode': HOME_POSTCODE
        })
        
        if len(waypoints) < 3:
            return jsonify({'success': False, 'error': 'Not enough valid postcodes to create route'}), 400
        
        # Store original waypoints and info for reordering
        original_waypoints = waypoints.copy()
        original_waypoint_info = waypoint_info.copy()
        
        # Calculate route with optimization mode (this reorders waypoints internally)
        route_result = calculate_route_simple(waypoints, optimization_mode=optimization_mode)
        
        if not route_result.get('success'):
            return jsonify({'success': False, 'error': route_result.get('error', 'Route calculation failed')}), 500
        
        # Get optimized coordinates to determine new order
        optimized_coords = route_result.get('optimized_coordinates', waypoints)
        
        # Reorder waypoint_info to match optimized coordinates
        reordered_waypoint_info = []
        used_indices = set()  # Track which waypoints we've already matched
        
        for opt_coord in optimized_coords:
            # Find matching waypoint info by comparing coordinates
            for i, orig_coord in enumerate(original_waypoints):
                if i not in used_indices and abs(opt_coord[0] - orig_coord[0]) < 0.0001 and abs(opt_coord[1] - orig_coord[1]) < 0.0001:
                    reordered_waypoint_info.append(original_waypoint_info[i])
                    used_indices.add(i)
                    break
        
        # Build response with reordered waypoint details
        optimized_route = []
        for i, waypoint in enumerate(reordered_waypoint_info):
            leg_info = route_result['legs'][i] if i < len(route_result['legs']) else None
            
            optimized_route.append({
                'sequence': i + 1,
                'type': waypoint['type'],
                'label': waypoint['label'],
                'postcode': waypoint['postcode'],
                'job': waypoint.get('job'),
                'distance_to_next_miles': leg_info['distance_miles'] if leg_info else 0,
                'time_to_next_minutes': leg_info['duration_minutes'] if leg_info else 0
            })
        
        log_settings_action('ROUTE_PLANNING', f'Optimized route for {date}: {len(job_waypoints)} jobs, {route_result["total_distance_miles"]} miles')
        
        return jsonify({
            'success': True,
            'date': date,
            'total_distance_miles': route_result['total_distance_miles'],
            'total_duration_minutes': route_result['total_duration_minutes'],
            'total_jobs': len(job_waypoints),
            'route': optimized_route
        })
        
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Route optimization failed: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500


@route_planning_bp.route('/save-order', methods=['POST'])
def save_route_order():
    """
    Save optimized route order and full route data to database.
    Expects: { "date": "DD/MM/YYYY", "job_order": [job_id1, job_id2, ...], "route_data": {...} }
    """
    try:
        data = request.get_json() or {}
        date = data.get('date')
        job_order = data.get('job_order', [])
        route_data = data.get('route_data', {})
        
        if not date or not job_order:
            return jsonify({'success': False, 'error': 'Date and job_order required'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update route_order for each job
            for order_index, job_id in enumerate(job_order, start=1):
                cursor.execute("""
                    UPDATE run_sheet_jobs
                    SET route_order = ?
                    WHERE id = ? AND date = ?
                """, (order_index, job_id, date))
            
            # Save full route data to runsheet_daily_data table
            if route_data:
                import json
                cursor.execute("""
                    INSERT INTO runsheet_daily_data 
                    (date, route_data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(date) DO UPDATE SET
                        route_data = excluded.route_data,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    date,
                    json.dumps(route_data)
                ))
            
            conn.commit()
        
        log_settings_action('ROUTE_PLANNING', f'Saved route order and data for {date}: {len(job_order)} jobs')
        
        return jsonify({
            'success': True,
            'message': f'Route order and data saved for {len(job_order)} jobs'
        })
        
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Failed to save route order: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500


@route_planning_bp.route('/get-saved-route/<date>', methods=['GET'])
def get_saved_route(date):
    """
    Get saved route optimization data for a specific date.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT route_data
                FROM runsheet_daily_data
                WHERE date = ?
            """, (date,))
            
            row = cursor.fetchone()
            
            if row and row[0]:
                import json
                route_data = json.loads(row[0])
                return jsonify({
                    'success': True,
                    'total_distance_miles': route_data.get('total_distance_miles'),
                    'total_duration_minutes': route_data.get('total_duration_minutes'),
                    'total_jobs': route_data.get('total_jobs'),
                    'route': route_data.get('route', [])
                })
            else:
                return jsonify({'success': False, 'error': 'No saved route found'}), 404
                
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Failed to get saved route: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500


@route_planning_bp.route('/batch-estimate-mileage', methods=['POST'])
def batch_estimate_mileage():
    """
    Batch estimate mileage for all days with missing mileage in a given year.
    Expects: { "year": "2025" }
    Returns: List of dates with estimated mileage
    """
    try:
        data = request.get_json() or {}
        year = data.get('year')
        
        if not year:
            return jsonify({'success': False, 'error': 'Year is required'}), 400
        
        # Find all dates with jobs but no mileage
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT r.date, COUNT(r.id) as job_count
                FROM run_sheet_jobs r
                LEFT JOIN runsheet_daily_data m ON r.date = m.date
                WHERE r.date LIKE ?
                AND m.mileage IS NULL
                AND r.status != 'deleted'
                GROUP BY r.date
                ORDER BY r.date
            """, (f'%/{year}',))
            
            missing_dates = []
            for row in cursor.fetchall():
                missing_dates.append({
                    'date': row[0],
                    'job_count': row[1]
                })
        
        if not missing_dates:
            return jsonify({
                'success': True,
                'message': f'No missing mileage found for {year}',
                'dates': []
            })
        
        log_settings_action('ROUTE_PLANNING', f'Found {len(missing_dates)} days with missing mileage in {year}')
        
        return jsonify({
            'success': True,
            'dates': missing_dates,
            'total': len(missing_dates)
        })
        
    except Exception as e:
        log_settings_action('ROUTE_PLANNING', f'Failed to find missing mileage: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500


@route_planning_bp.route('/geocode', methods=['POST'])
def geocode_postcode_api():
    """Test endpoint to geocode a postcode."""
    try:
        data = request.get_json()
        postcode = data.get('postcode')
        
        if not postcode:
            return jsonify({'success': False, 'error': 'Postcode required'}), 400
        
        coords = geocode_postcode(postcode)
        
        if coords:
            return jsonify({
                'success': True,
                'postcode': postcode,
                'longitude': coords[0],
                'latitude': coords[1]
            })
        else:
            return jsonify({'success': False, 'error': 'Could not geocode postcode'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
