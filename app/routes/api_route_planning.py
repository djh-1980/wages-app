"""
API routes for route planning and optimization.
Uses OpenRouteService API for route optimization.
"""

from flask import Blueprint, jsonify, request
import requests
import math
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
    Optimize waypoint order using nearest neighbor algorithm followed by 2-opt improvement.
    Returns list of indices representing optimal order.
    """
    if len(coordinates) <= 2:
        return list(range(len(coordinates)))
    
    def haversine_distance(coord1, coord2):
        """Calculate distance between two coordinates in km"""
        lat1, lon1 = coord1[1], coord1[0]
        lat2, lon2 = coord2[1], coord2[0]
        
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def calculate_total_distance(order, coords):
        """Calculate total distance for a given route order"""
        total = 0
        for i in range(len(order) - 1):
            total += haversine_distance(coords[order[i]], coords[order[i + 1]])
        return total
    
    def two_opt_improve(order, coords, max_iterations=500):
        """Improve route using 2-opt algorithm to eliminate crossings
        Keep first element (depot) fixed, only optimize jobs after it"""
        best_order = order[:]
        best_distance = calculate_total_distance(best_order, coords)
        improved = True
        
        while improved:
            improved = False
            
            # Try all possible 2-opt swaps, keeping depot at index 0
            # Start from index 1 to allow swapping the first job
            for i in range(1, len(best_order) - 2):
                for j in range(i + 2, len(best_order)):
                    # Create new route by reversing segment between i and j
                    # This keeps depot at position 0
                    new_order = best_order[:i] + best_order[i:j][::-1] + best_order[j:]
                    new_distance = calculate_total_distance(new_order, coords)
                    
                    if new_distance < best_distance:
                        best_order = new_order
                        best_distance = new_distance
                        improved = True
        
        return best_order
    
    # Use angle-based sweep algorithm for better geographic routing
    # This creates a logical flow around the depot instead of just picking nearest
    import math
    
    n = len(coordinates)
    if n <= 1:
        return list(range(n))
    
    depot = coordinates[0]
    
    # Calculate angle from depot to each point
    def calculate_angle(point):
        """Calculate angle from depot to point (in radians)"""
        dx = point[0] - depot[0]  # longitude difference
        dy = point[1] - depot[1]  # latitude difference
        return math.atan2(dy, dx)
    
    # Create list of (index, angle, distance) for all points except depot
    points_with_angles = []
    for i in range(1, n):
        angle = calculate_angle(coordinates[i])
        dist = haversine_distance(depot, coordinates[i])
        points_with_angles.append((i, angle, dist))
    
    # Sort by angle to create a sweep around the depot
    # This creates a logical geographic flow (e.g., clockwise or counterclockwise)
    points_with_angles.sort(key=lambda x: x[1])
    
    # Build initial order: depot first, then points in angular order
    order = [0] + [p[0] for p in points_with_angles]
    
    # Apply 2-opt improvement to eliminate any remaining inefficiencies
    order = two_opt_improve(order, coordinates)
    
    return order

def calculate_route_simple(coordinates, optimization_mode='distance'):
    """
    Calculate route through multiple waypoints using Google Directions API with waypoint optimization.
    Route order: Home → Depot → Optimized Jobs → Home
    Only job waypoints are optimized, home and depot stay fixed.
    Returns route with distance and duration.
    """
    try:
        from ..config import Config
        
        if len(coordinates) < 4:  # Need at least Home + Depot + 1 job + Home return
            return {'success': False, 'error': 'Not enough waypoints for optimization'}
        
        # Structure: [Home, Depot, Job1, Job2, ..., JobN, Home]
        home_start = coordinates[0]
        depot = coordinates[1]
        jobs = coordinates[2:-1]  # All jobs (exclude home start, depot, and home return)
        home_end = coordinates[-1]
        
        # Use Google Directions API with waypoint optimization
        # Set origin as depot (not home) so route starts from depot
        origin = f"{depot[1]},{depot[0]}"  # lat,lng - Start from depot
        destination = f"{home_end[1]},{home_end[0]}"  # lat,lng - End at home
        
        # Only jobs go in waypoints to be optimized (depot is now origin)
        waypoints_list = [f"{job[1]},{job[0]}" for job in jobs]  # Only jobs to optimize
        waypoints_str = '|'.join(waypoints_list)
        
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': origin,
            'destination': destination,
            'waypoints': f'optimize:true|{waypoints_str}',  # optimize:true tells Google to reorder job waypoints
            'key': Config.GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'OK' and data.get('routes'):
            route = data['routes'][0]
            
            # Get optimized waypoint order
            waypoint_order = route.get('waypoint_order', [])
            
            # Rebuild coordinates in optimized order
            # waypoint_order indices refer to jobs array
            optimized_coords = [home_start, depot]  # Always start with home then depot
            
            # Add jobs in Google's optimized order
            for idx in waypoint_order:
                optimized_coords.append(jobs[idx])
            
            optimized_coords.append(home_end)  # End at home
            
            # Extract distance and duration
            total_distance_meters = 0
            total_duration_seconds = 0
            legs = []
            
            for leg in route.get('legs', []):
                dist = leg.get('distance', {}).get('value', 0)
                dur = leg.get('duration', {}).get('value', 0)
                total_distance_meters += dist
                total_duration_seconds += dur
                legs.append({
                    'distance_meters': dist,
                    'duration_seconds': dur,
                    'distance_miles': round(dist * 0.000621371, 2),
                    'duration_minutes': round(dur / 60, 1)
                })
            
            return {
                'success': True,
                'total_distance_meters': total_distance_meters,
                'total_duration_seconds': total_duration_seconds,
                'total_distance_miles': round(total_distance_meters * 0.000621371, 2),
                'total_duration_minutes': round(total_duration_seconds / 60, 1),
                'legs': legs,
                'optimized_coordinates': optimized_coords,
                'waypoint_order': waypoint_order
            }
        
        return {'success': False, 'error': f"Google API error: {data.get('status', 'Unknown')}"}
        
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if any jobs are already completed (to start route from there)
            cursor.execute("""
                SELECT id, job_number, customer, job_address, postcode, activity
                FROM run_sheet_jobs
                WHERE date = ?
                AND status = 'completed'
                ORDER BY id DESC
                LIMIT 1
            """, (date,))
            
            completed_job = None
            completed_row = cursor.fetchone()
            if completed_row:
                completed_job = {
                    'id': completed_row[0],
                    'job_number': completed_row[1],
                    'customer': completed_row[2],
                    'address': completed_row[3],
                    'postcode': completed_row[4],
                    'activity': completed_row[5]
                }
            
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
        
        # Build waypoint list
        waypoints = []
        waypoint_info = []
        
        # Get home coordinates (needed for return journey)
        home_coords = geocode_postcode(HOME_POSTCODE)
        if not home_coords:
            return jsonify({'success': False, 'error': f'Could not geocode home postcode: {HOME_POSTCODE}'}), 400
        
        # Track already-traveled distance for accurate mileage
        already_traveled_miles = 0
        already_traveled_minutes = 0
        already_traveled_legs = []  # Store individual leg distances
        
        # Determine starting point
        if completed_job and completed_job['postcode']:
            # Calculate already-traveled distance: Home → Depot → Completed Job
            depot_coords = geocode_postcode(DEPOT_POSTCODE)
            completed_coords = geocode_postcode(completed_job['postcode'])
            
            if depot_coords and completed_coords:
                # Calculate Home → Depot → Completed Job distance using Google Directions API
                try:
                    from ..config import Config
                    import requests
                    
                    origin = f"{home_coords[1]},{home_coords[0]}"  # lat,lng
                    destination = f"{completed_coords[1]},{completed_coords[0]}"  # lat,lng
                    waypoint = f"{depot_coords[1]},{depot_coords[0]}"  # lat,lng
                    
                    log_settings_action('ROUTE_PLANNING', f'Calculating already-traveled: {HOME_POSTCODE} → {DEPOT_POSTCODE} → {completed_job["postcode"]}')
                    
                    url = "https://maps.googleapis.com/maps/api/directions/json"
                    params = {
                        'origin': origin,
                        'destination': destination,
                        'waypoints': waypoint,
                        'key': Config.GOOGLE_MAPS_API_KEY
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    data = response.json()
                    
                    log_settings_action('ROUTE_PLANNING', f'Google API status: {data.get("status")}')
                    
                    if data.get('status') == 'OK' and data.get('routes'):
                        route = data['routes'][0]
                        legs = route.get('legs', [])
                        
                        # Store individual leg distances
                        for leg in legs:
                            dist_meters = leg.get('distance', {}).get('value', 0)
                            dur_seconds = leg.get('duration', {}).get('value', 0)
                            already_traveled_legs.append({
                                'distance_miles': round(dist_meters * 0.000621371, 2),
                                'duration_minutes': round(dur_seconds / 60, 1)
                            })
                        
                        total_distance_meters = sum(leg.get('distance', {}).get('value', 0) for leg in legs)
                        total_duration_seconds = sum(leg.get('duration', {}).get('value', 0) for leg in legs)
                        
                        already_traveled_miles = round(total_distance_meters * 0.000621371, 2)
                        already_traveled_minutes = round(total_duration_seconds / 60, 1)
                        
                        log_settings_action('ROUTE_PLANNING', f'Already traveled: {already_traveled_miles} miles (Home → Depot → Job {completed_job["job_number"]})')
                    else:
                        log_settings_action('ROUTE_PLANNING', f'Google API error: {data.get("status")} - {data.get("error_message", "No error message")}', 'WARNING')
                except Exception as e:
                    log_settings_action('ROUTE_PLANNING', f'Failed to calculate already-traveled distance: {str(e)}', 'WARNING')
                    import traceback
                    log_settings_action('ROUTE_PLANNING', f'Traceback: {traceback.format_exc()}', 'WARNING')
            
            # Start optimization from completed job location (you're already there)
            start_coords = geocode_postcode(completed_job['postcode'])
            if start_coords:
                waypoints.append(start_coords)
                waypoint_info.append({
                    'type': 'current_location',
                    'label': f"Current Location (Job {completed_job['job_number']})",
                    'postcode': completed_job['postcode'],
                    'job': completed_job
                })
                log_settings_action('ROUTE_PLANNING', f'Starting route optimization from completed job {completed_job["job_number"]} at {completed_job["postcode"]}')
            else:
                # Fallback to home if geocoding completed job fails
                waypoints.append(home_coords)
                waypoint_info.append({
                    'type': 'home',
                    'label': 'Home',
                    'postcode': HOME_POSTCODE
                })
        else:
            # No completed jobs - start from home
            waypoints.append(home_coords)
            waypoint_info.append({
                'type': 'home',
                'label': 'Home',
                'postcode': HOME_POSTCODE
            })
            
            # Add depot if requested and no completed jobs
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
        skipped_jobs = []  # Track jobs that couldn't be geocoded
        
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
                    skipped_jobs.append(job)
            else:
                log_settings_action('ROUTE_PLANNING', f"Job {job['job_number']} has no postcode", 'WARNING')
                skipped_jobs.append(job)
        
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
        
        # Merge duplicate consecutive postcodes before sending to Google
        # Track which jobs share locations so we can expand them back later
        merged_waypoints = []
        merged_waypoint_info = []
        duplicate_groups = []  # Track groups of jobs at same location
        
        i = 0
        while i < len(waypoints):
            merged_waypoints.append(waypoints[i])
            group = [waypoint_info[i]]
            
            # Check if next waypoints have same postcode
            j = i + 1
            while j < len(waypoints) and waypoints[j] == waypoints[i]:
                group.append(waypoint_info[j])
                j += 1
            
            merged_waypoint_info.append(group[0])  # Use first job as representative
            duplicate_groups.append(group)  # Store all jobs at this location
            i = j
        
        log_settings_action('ROUTE_PLANNING', f'Merged {len(waypoints)} waypoints into {len(merged_waypoints)} unique locations')
        
        # Calculate route with merged waypoints (no duplicates)
        route_result = calculate_route_simple(merged_waypoints, optimization_mode=optimization_mode)
        
        if not route_result.get('success'):
            return jsonify({'success': False, 'error': route_result.get('error', 'Route calculation failed')}), 500
        
        # Get optimized coordinates to determine new order
        optimized_coords = route_result.get('optimized_coordinates', waypoints)
        
        # Reorder merged waypoint groups to match optimized coordinates
        reordered_groups = []
        used_indices = set()
        
        for opt_coord in optimized_coords:
            # Find matching merged waypoint by comparing coordinates
            for i, merged_coord in enumerate(merged_waypoints):
                if i not in used_indices and abs(opt_coord[0] - merged_coord[0]) < 0.0001 and abs(opt_coord[1] - merged_coord[1]) < 0.0001:
                    reordered_groups.append(duplicate_groups[i])
                    used_indices.add(i)
                    break
        
        # Expand groups back into individual waypoints
        reordered_waypoint_info = []
        for group in reordered_groups:
            for waypoint in group:
                reordered_waypoint_info.append(waypoint)
        
        # Build response with reordered waypoint details
        optimized_route = []
        
        # If we started from a completed job, add the already-traveled waypoints to the display
        if completed_job and already_traveled_miles > 0:
            # Add Home as first waypoint (with distance to Depot)
            home_to_depot = already_traveled_legs[0] if len(already_traveled_legs) > 0 else {'distance_miles': 0, 'duration_minutes': 0}
            optimized_route.append({
                'sequence': 1,
                'type': 'home',
                'label': 'Home (Start)',
                'postcode': HOME_POSTCODE,
                'job': None,
                'distance_to_next_miles': home_to_depot['distance_miles'],
                'time_to_next_minutes': home_to_depot['duration_minutes'],
                'already_completed': True
            })
            
            # Add Depot as second waypoint (with distance to Completed Job)
            depot_to_completed = already_traveled_legs[1] if len(already_traveled_legs) > 1 else {'distance_miles': 0, 'duration_minutes': 0}
            optimized_route.append({
                'sequence': 2,
                'type': 'depot',
                'label': 'Depot',
                'postcode': DEPOT_POSTCODE,
                'job': None,
                'distance_to_next_miles': depot_to_completed['distance_miles'],
                'time_to_next_minutes': depot_to_completed['duration_minutes'],
                'already_completed': True
            })
            
            # Note: The completed job will be added as "Current Location" in the optimized route below
            # so we don't add it here to avoid duplicates
        
        # Add the optimized remaining route
        sequence_offset = len(optimized_route)
        
        # Important: If we added Home/Depot at the start, reordered_waypoint_info starts with
        # the "Current Location" (completed job), but we've already added Home/Depot to optimized_route.
        # Google's legs[0] is from Current Location to first job, legs[1] is first job to second job, etc.
        # So the leg indices match the waypoint indices in reordered_waypoint_info directly.
        
        log_settings_action('ROUTE_PLANNING', f'Total legs from Google: {len(route_result.get("legs", []))}')
        log_settings_action('ROUTE_PLANNING', f'Total waypoints in optimized route: {len(reordered_waypoint_info)}')
        log_settings_action('ROUTE_PLANNING', f'Already added to display (Home/Depot): {sequence_offset} waypoints')
        
        # Map legs to expanded waypoints
        # Google gave us clean legs for merged waypoints (no duplicates)
        # Now we need to map them to the expanded waypoint list
        # Jobs at the same location get 0 miles between them
        
        leg_index = 0
        group_index = 0
        
        for i, waypoint in enumerate(reordered_waypoint_info):
            # Check if this is the first waypoint in a group
            group_start = sum(len(g) for g in reordered_groups[:group_index])
            group_size = len(reordered_groups[group_index]) if group_index < len(reordered_groups) else 1
            position_in_group = i - group_start
            
            if position_in_group < group_size - 1:
                # Not the last job in this group - show 0 miles to next job at same location
                leg_info = {'distance_miles': 0, 'duration_minutes': 0}
            elif position_in_group == group_size - 1:
                # Last job in this group - use the leg to next different location
                leg_info = route_result['legs'][leg_index] if leg_index < len(route_result['legs']) else None
                leg_index += 1
                group_index += 1
            else:
                leg_info = None
            
            if waypoint.get('job'):
                job_num = waypoint["job"].get("job_number")
                if leg_info:
                    log_settings_action('ROUTE_PLANNING', f'Job {job_num} (waypoint {i}, group {group_index-1}, pos {position_in_group}): {leg_info["distance_miles"]} mi, {leg_info["duration_minutes"]} min')
                else:
                    log_settings_action('ROUTE_PLANNING', f'Job {job_num} (waypoint {i}): NO LEG (last waypoint)', 'INFO')
            
            optimized_route.append({
                'sequence': sequence_offset + i + 1,
                'type': waypoint['type'],
                'label': waypoint['label'],
                'postcode': waypoint['postcode'],
                'job': waypoint.get('job'),
                'distance_to_next_miles': leg_info['distance_miles'] if leg_info else 0,
                'time_to_next_minutes': leg_info['duration_minutes'] if leg_info else 0,
                'already_completed': False
            })
        
        # Add skipped jobs at the end with clear indication
        if skipped_jobs:
            for skipped_job in skipped_jobs:
                optimized_route.append({
                    'sequence': len(optimized_route) + 1,
                    'type': 'skipped_job',
                    'label': f"Job {skipped_job['job_number']} (No Location Data)",
                    'postcode': skipped_job.get('postcode', 'N/A'),
                    'job': skipped_job,
                    'distance_to_next_miles': 0,
                    'time_to_next_minutes': 0,
                    'already_completed': False,
                    'missing_location': True
                })
            log_settings_action('ROUTE_PLANNING', f'Skipped {len(skipped_jobs)} jobs with missing/invalid postcodes')
        
        # Add already-traveled distance to totals for accurate mileage
        total_distance_miles = route_result['total_distance_miles'] + already_traveled_miles
        total_duration_minutes = route_result['total_duration_minutes'] + already_traveled_minutes
        
        log_settings_action('ROUTE_PLANNING', f'Optimized route for {date}: {len(job_waypoints)} jobs, {total_distance_miles} miles (includes {already_traveled_miles} already traveled)')
        
        return jsonify({
            'success': True,
            'date': date,
            'total_distance_miles': total_distance_miles,
            'total_duration_minutes': total_duration_minutes,
            'total_jobs': len(job_waypoints),
            'skipped_jobs': len(skipped_jobs),
            'route': optimized_route,
            'already_traveled_miles': already_traveled_miles,
            'already_traveled_minutes': already_traveled_minutes
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
