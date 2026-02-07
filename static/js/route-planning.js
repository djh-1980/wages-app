/**
 * Route Planning and Optimization
 */

let currentOptimizedRoute = null;
let currentRouteDate = null;

async function optimizeRoute(date) {
    try {
        const button = document.getElementById('optimizeRouteBtn');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Optimizing...';
        button.disabled = true;

        const response = await fetch('/api/route-planning/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                include_depot: true
            })
        });

        const data = await response.json();

        if (data.success) {
            currentOptimizedRoute = data;
            currentRouteDate = date;
            
            // Clear existing map instance so it gets re-initialized
            window.routeMapInlineInstance = null;
            
            // Store route data for later retrieval
            storeRouteData(date, {
                total_distance_miles: data.total_distance_miles,
                total_duration_minutes: data.total_duration_minutes,
                total_jobs: data.total_jobs,
                route: data.route
            });
            
            displayOptimizedRoute(data);
            reorderJobsInModal(data);
            
            // Auto-fill mileage field if it's empty (round up to nearest mile)
            const mileageInput = document.getElementById(`mileage-${date}`);
            if (mileageInput && (!mileageInput.value || mileageInput.value.trim() === '')) {
                const roundedMiles = Math.ceil(data.total_distance_miles);
                mileageInput.value = roundedMiles;
                console.log(`✓ Auto-filled mileage: ${roundedMiles} miles (from ${data.total_distance_miles})`);
            }
            
            // Keep button green and change text
            button.innerHTML = '<i class="bi bi-check-circle-fill"></i> Route Optimized';
            button.classList.remove('btn-success');
            button.classList.add('btn-success');
        } else {
            alert('Route optimization failed: ' + (data.error || 'Unknown error'));
            button.innerHTML = originalText;
        }

        button.disabled = false;

    } catch (error) {
        console.error('Route optimization error:', error);
        alert('Error optimizing route: ' + error.message);
        
        const button = document.getElementById('optimizeRouteBtn');
        button.innerHTML = '<i class="bi bi-map"></i> Optimize Route';
        button.disabled = false;
    }
}

function displayOptimizedRoute(data) {
    const container = document.getElementById('optimizedRouteContainer');
    
    if (!container) {
        console.error('Route container not found');
        return;
    }

    let html = `
        <div class="alert alert-success mt-3">
            <h6 class="mb-2">
                <i class="bi bi-check-circle-fill"></i> Route Optimized!
            </h6>
            <div class="row">
                <div class="col-md-4">
                    <strong>Total Distance:</strong> ${data.total_distance_miles} miles
                </div>
                <div class="col-md-4">
                    <strong>Estimated Time:</strong> ${Math.floor(data.total_duration_minutes / 60)}h ${Math.round(data.total_duration_minutes % 60)}m
                </div>
                <div class="col-md-4">
                    <strong>Jobs:</strong> ${data.total_jobs}
                </div>
            </div>
        </div>

        <div class="card mt-3">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center" style="cursor: pointer;" onclick="toggleRouteDetails()">
                <h6 class="mb-0">
                    <i class="bi bi-signpost-2"></i> Optimized Route Order
                </h6>
                <i class="bi bi-chevron-down" id="routeToggleIcon"></i>
            </div>
            <div class="card-body p-0" id="routeDetailsBody" style="display: none;">
                <!-- Map container at the top - responsive height -->
                <div id="routeMapInline" style="height: 300px; width: 100%; border-bottom: 1px solid #dee2e6;"></div>
                
                <div class="list-group list-group-flush">
    `;

    data.route.forEach((waypoint, index) => {
        let icon = 'bi-geo-alt-fill';
        let badgeClass = 'bg-secondary';
        let label = waypoint.label;

        if (waypoint.type === 'home') {
            icon = 'bi-house-fill';
            badgeClass = 'bg-success';
        } else if (waypoint.type === 'depot') {
            icon = 'bi-building';
            badgeClass = 'bg-info';
        } else if (waypoint.type === 'job') {
            icon = 'bi-briefcase-fill';
            badgeClass = 'bg-primary';
            label = `${waypoint.job.customer} - ${waypoint.job.activity}`;
        }

        html += `
            <div class="list-group-item">
                <div class="d-flex align-items-start">
                    <div class="me-3">
                        <span class="badge ${badgeClass} rounded-circle" style="width: 35px; height: 35px; display: flex; align-items: center; justify-content: center; font-size: 1rem;">
                            ${waypoint.sequence}
                        </span>
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">
                                    <i class="bi ${icon}"></i> ${waypoint.label}
                                </h6>
                                ${waypoint.type === 'job' ? `
                                    <small class="text-muted d-block">Job #${waypoint.job.job_number}</small>
                                    <small class="text-muted d-block">${waypoint.job.address}</small>
                                ` : ''}
                                <small class="text-muted"><i class="bi bi-pin-map"></i> ${waypoint.postcode}</small>
                            </div>
                            ${waypoint.distance_to_next_miles > 0 ? `
                                <div class="text-end">
                                    <small class="text-primary fw-bold d-block">
                                        <i class="bi bi-arrow-down"></i> ${waypoint.distance_to_next_miles} mi
                                    </small>
                                    <small class="text-muted">${waypoint.time_to_next_minutes} min</small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;
    container.style.display = 'block';
    
    // Store route data globally for map display
    window.currentRouteData = data;
    
    // Create map modal if it doesn't exist
    if (!document.getElementById('routeMapModal')) {
        const mapModalHTML = `
            <div class="modal fade" id="routeMapModal" tabindex="-1" aria-labelledby="routeMapModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-fullscreen">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title" id="routeMapModalLabel">
                                <i class="bi bi-map"></i> Route Map
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body p-0">
                            <div id="routeMap" style="height: 100%; width: 100%;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', mapModalHTML);
    }
}

function reorderJobsInModal(data) {
    if (!data || !data.route || !window.currentRunsheetJobs) {
        console.error('Missing data for reordering');
        return;
    }
    
    console.log('Reordering jobs based on optimized route...');
    console.log('Route waypoints:', data.route.length);
    
    // Create a map of job IDs to their route order
    const routeOrderMap = new Map();
    let orderIndex = 1;
    
    data.route.forEach(waypoint => {
        if (waypoint.type === 'job' && waypoint.job) {
            console.log(`Route position ${orderIndex}: Job ${waypoint.job.job_number} (ID: ${waypoint.job.id})`);
            routeOrderMap.set(waypoint.job.id, orderIndex++);
        }
    });
    
    console.log('Route order map size:', routeOrderMap.size);
    
    // Sort jobs by optimized route order
    const sortedJobs = [...window.currentRunsheetJobs].sort((a, b) => {
        const orderA = routeOrderMap.get(a.id) || 999;
        const orderB = routeOrderMap.get(b.id) || 999;
        return orderA - orderB;
    });
    
    console.log('Jobs reordered. First 3 jobs:', sortedJobs.slice(0, 3).map(j => j.job_number));
    
    // Update global jobs array
    window.currentRunsheetJobs = sortedJobs;
    
    // Re-render the job table with sorted jobs
    reRenderJobTable(sortedJobs);
}

function reRenderJobTable(jobs) {
    // Desktop table - must be inside the modal
    const desktopTableBody = document.querySelector('#runsheetJobsModal .table-responsive tbody');
    if (desktopTableBody) {
        desktopTableBody.innerHTML = jobs.map((job, index) => {
            const status = job.status || 'pending';
            const statusBadge = getStatusBadge(status);
            const mappedCustomer = window.customerMapping ? 
                window.customerMapping.getMappedCustomer(job.customer) : 
                job.customer;
            
            return `
                <tr id="job-row-${job.id}" data-status="${status}" title="Original: ${job.customer}">
                    <td><strong>${job.job_number}</strong></td>
                    <td>${mappedCustomer || 'N/A'}</td>
                    <td><span class="badge bg-info">${job.activity || 'N/A'}</span></td>
                    <td>
                        <small>${job.job_address || 'N/A'}, ${job.postcode || ''}</small>
                        ${job.notes ? `<div class="mt-1"><span class="badge bg-warning text-dark" style="cursor: pointer; white-space: normal; text-align: left; display: block;" onclick="openJobNotesModal(${job.id}, '${job.job_number.replace(/'/g, "\\'")}')" title="Click to edit note"><i class="bi bi-sticky-fill me-1"></i>${job.notes}</span></div>` : `<div class="mt-1"><small class="text-muted" style="cursor: pointer;" onclick="openJobNotesModal(${job.id}, '${job.job_number.replace(/'/g, "\\'")}')" title="Click to add note"><i class="bi bi-plus-circle me-1"></i>Add note</small></div>`}
                    </td>
                    <td>
                        <span class="status-badge ${status === 'extra' ? 'cursor-pointer' : ''}" id="status-${job.id}" ${status === 'extra' ? `onclick="editExtraJob(${job.id}, '${job.date}')" title="Click to edit"` : ''}>${statusBadge}</span>
                        ${job.price_agreed && job.price_agreed > 0 ? `<div class="mt-1"><span class="badge bg-warning text-dark"><i class="bi bi-currency-pound"></i> ${CurrencyFormatter.format(job.price_agreed)}</span></div>` : ''}
                    </td>
                    <td class="text-end">
                        ${job.pay_amount ? `<strong class="${job.price_agreed && job.pay_amount < job.price_agreed ? 'text-danger' : 'text-success'}">${CurrencyFormatter.format(job.pay_amount)}${job.price_agreed && job.pay_amount < job.price_agreed ? ' <i class="bi bi-exclamation-triangle-fill"></i>' : ''}</strong>` : '<span class="text-muted">No pay data</span>'}
                    </td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm" role="group">
                            <button class="btn btn-outline-success" onclick="updateJobStatus(${job.id}, 'completed')" title="Completed">
                                <i class="bi bi-check-circle"></i>
                            </button>
                            <button class="btn btn-outline-danger" onclick="updateJobStatus(${job.id}, 'missed')" title="Missed">
                                <i class="bi bi-x-circle"></i>
                            </button>
                            <button class="btn btn-outline-warning" onclick="updateJobStatus(${job.id}, 'DNCO')" title="DNCO">
                                <i class="bi bi-exclamation-circle"></i>
                            </button>
                            <button class="btn btn-outline-info" onclick="updateJobStatus(${job.id}, 'extra')" title="Extra">
                                <i class="bi bi-plus-circle"></i>
                            </button>
                            <button class="btn btn-outline-secondary" onclick="deleteJob(${job.id}, '${job.date}')" title="Delete Job">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    // Mobile cards - must be inside the modal
    const mobileCardsContainer = document.querySelector('#runsheetJobsModal .d-md-none');
    if (mobileCardsContainer) {
        mobileCardsContainer.innerHTML = jobs.map((job, index) => {
            const status = job.status || 'pending';
            const statusBadge = getStatusBadge(status);
            const mappedCustomer = window.customerMapping ? 
                window.customerMapping.getMappedCustomer(job.customer) : 
                job.customer;
            
            return `
                <div class="card mb-3" id="job-card-${job.id}" data-status="${status}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <strong>${job.job_number}</strong>
                            ${statusBadge}
                        </div>
                        <h6 class="card-title mb-2">${mappedCustomer || 'N/A'}</h6>
                        <p class="card-text mb-2">
                            <span class="badge bg-info">${job.activity || 'N/A'}</span>
                        </p>
                        <p class="card-text mb-2">
                            <small class="text-muted">${job.job_address || 'N/A'}, ${job.postcode || ''}</small>
                        </p>
                        ${job.notes ? `<div class="mb-2"><span class="badge bg-warning text-dark" style="cursor: pointer; white-space: normal; text-align: left; display: block;" onclick="openJobNotesModal(${job.id}, '${job.job_number.replace(/'/g, "\\'")}')" title="Click to edit note"><i class="bi bi-sticky-fill me-1"></i>${job.notes}</span></div>` : `<div class="mb-2"><small class="text-muted" style="cursor: pointer;" onclick="openJobNotesModal(${job.id}, '${job.job_number.replace(/'/g, "\\'")}')" title="Click to add note"><i class="bi bi-plus-circle me-1"></i>Add note</small></div>`}
                        <div class="mb-2">
                            <strong>Pay:</strong> ${job.pay_amount ? CurrencyFormatter.format(job.pay_amount) : '<small class="text-muted">No pay data</small>'}
                        </div>
                        <div class="d-flex gap-1 flex-wrap">
                            <button class="btn btn-sm btn-icon" onclick="updateJobStatus(${job.id}, 'completed')" title="Completed">
                                <i class="bi bi-check-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-icon" onclick="updateJobStatus(${job.id}, 'missed')" title="Missed">
                                <i class="bi bi-x-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-icon" onclick="updateJobStatus(${job.id}, 'dnco')" title="DNCO">
                                <i class="bi bi-exclamation-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-icon" onclick="updateJobStatus(${job.id}, 'extra')" title="Extra">
                                <i class="bi bi-plus-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-icon" onclick="deleteJob(${job.id})" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function toggleRouteDetails() {
    const body = document.getElementById('routeDetailsBody');
    const icon = document.getElementById('routeToggleIcon');
    
    if (body && icon) {
        if (body.style.display === 'none') {
            body.style.display = 'block';
            icon.classList.remove('bi-chevron-down');
            icon.classList.add('bi-chevron-up');
            
            // Initialize inline map when expanded
            if (!window.routeMapInlineInstance) {
                setTimeout(() => {
                    initializeInlineRouteMap();
                }, 100);
            }
        } else {
            body.style.display = 'none';
            icon.classList.remove('bi-chevron-up');
            icon.classList.add('bi-chevron-down');
        }
    }
}

function initializeInlineRouteMap() {
    if (!window.currentRouteData || !window.currentRouteData.route) {
        console.error('No route data available for inline map');
        return;
    }
    
    const mapElement = document.getElementById('routeMapInline');
    if (!mapElement) {
        console.error('Inline map element not found');
        return;
    }
    
    // Check if Google Maps is loaded
    if (typeof google === 'undefined' || !google.maps) {
        console.error('Google Maps not loaded');
        return;
    }
    
    const route = window.currentRouteData.route;
    
    // Initialize map
    const map = new google.maps.Map(mapElement, {
        zoom: 10,
        center: { lat: 53.4808, lng: -2.2426 }, // Manchester center
        mapTypeId: 'roadmap'
    });
    
    const directionsService = new google.maps.DirectionsService();
    const directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: true,
        polylineOptions: {
            strokeColor: '#4285F4',
            strokeOpacity: 0.8,
            strokeWeight: 5
        }
    });
    
    // Collect waypoints
    const waypoints = [];
    
    route.forEach((waypoint, index) => {
        if (index > 0 && index < route.length - 1) {
            waypoints.push({
                location: waypoint.postcode,
                stopover: true
            });
        }
    });
    
    // Use Google Directions API
    if (route.length >= 2) {
        const origin = route[0].postcode;
        const destination = route[route.length - 1].postcode;
        
        const request = {
            origin: origin,
            destination: destination,
            waypoints: waypoints,
            travelMode: 'DRIVING',
            optimizeWaypoints: false
        };
        
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                directionsRenderer.setDirections(result);
                
                // Add custom markers
                route.forEach((waypoint, index) => {
                    const geocoder = new google.maps.Geocoder();
                    
                    geocoder.geocode({ address: waypoint.postcode }, (results, status) => {
                        if (status === 'OK' && results[0]) {
                            const position = results[0].geometry.location;
                            
                            let markerLabel = waypoint.sequence.toString();
                            
                            if (waypoint.type === 'home') {
                                markerLabel = 'H';
                            } else if (waypoint.type === 'depot') {
                                markerLabel = 'D';
                            }
                            
                            const marker = new google.maps.Marker({
                                position: position,
                                map: map,
                                label: {
                                    text: markerLabel,
                                    color: 'white',
                                    fontWeight: 'bold'
                                },
                                title: waypoint.label,
                                zIndex: 1000
                            });
                            
                            const infoContent = `
                                <div style="padding: 10px;">
                                    <h6>${waypoint.label}</h6>
                                    <p style="margin: 5px 0;"><strong>Postcode:</strong> ${waypoint.postcode}</p>
                                    ${waypoint.type === 'job' ? `
                                        <p style="margin: 5px 0;"><strong>Job:</strong> #${waypoint.job.job_number}</p>
                                        <p style="margin: 5px 0;"><strong>Activity:</strong> ${waypoint.job.activity}</p>
                                    ` : ''}
                                    ${waypoint.distance_to_next_miles > 0 ? `
                                        <p style="margin: 5px 0; color: #1a73e8;">
                                            <strong>Next:</strong> ${waypoint.distance_to_next_miles} mi (${waypoint.time_to_next_minutes} min)
                                        </p>
                                    ` : ''}
                                </div>
                            `;
                            
                            const infoWindow = new google.maps.InfoWindow({
                                content: infoContent
                            });
                            
                            marker.addListener('click', () => {
                                infoWindow.open(map, marker);
                            });
                        }
                    });
                });
            } else {
                console.error('Directions request failed:', status);
            }
        });
    }
    
    window.routeMapInlineInstance = map;
}

function initializeRouteMap() {
    if (!window.currentRouteData || !window.currentRouteData.route) {
        console.error('No route data available for map');
        return;
    }
    
    const mapElement = document.getElementById('routeMap');
    if (!mapElement) {
        console.error('Map element not found');
        return;
    }
    
    // Check if Google Maps is loaded
    if (typeof google === 'undefined' || !google.maps) {
        alert('Google Maps is loading... Please try again in a moment.');
        return;
    }
    
    const route = window.currentRouteData.route;
    
    // Initialize map
    const map = new google.maps.Map(mapElement, {
        zoom: 10,
        center: { lat: 53.4808, lng: -2.2426 }, // Manchester center
        mapTypeId: 'roadmap'
    });
    
    const bounds = new google.maps.LatLngBounds();
    const directionsService = new google.maps.DirectionsService();
    const directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: true, // We'll add custom markers
        polylineOptions: {
            strokeColor: '#4285F4',
            strokeOpacity: 0.8,
            strokeWeight: 5
        }
    });
    
    // Collect all waypoints with their postcodes
    const waypoints = [];
    const waypointData = [];
    
    route.forEach((waypoint, index) => {
        waypointData.push(waypoint);
        if (index > 0 && index < route.length - 1) {
            // Middle waypoints for Directions API
            waypoints.push({
                location: waypoint.postcode,
                stopover: true
            });
        }
    });
    
    // Use Google Directions API to get actual road route
    if (route.length >= 2) {
        const origin = route[0].postcode;
        const destination = route[route.length - 1].postcode;
        
        const request = {
            origin: origin,
            destination: destination,
            waypoints: waypoints,
            travelMode: 'DRIVING',
            optimizeWaypoints: false // We already optimized
        };
        
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                directionsRenderer.setDirections(result);
                
                // Add custom markers for each waypoint
                route.forEach((waypoint, index) => {
                    const geocoder = new google.maps.Geocoder();
                    
                    geocoder.geocode({ address: waypoint.postcode }, (results, status) => {
                        if (status === 'OK' && results[0]) {
                            const position = results[0].geometry.location;
                            bounds.extend(position);
                            
                            let markerLabel = waypoint.sequence.toString();
                            let markerColor = '#4285F4';
                            
                            if (waypoint.type === 'home') {
                                markerLabel = 'H';
                                markerColor = '#34A853';
                            } else if (waypoint.type === 'depot') {
                                markerLabel = 'D';
                                markerColor = '#4285F4';
                            }
                            
                            const marker = new google.maps.Marker({
                                position: position,
                                map: map,
                                label: {
                                    text: markerLabel,
                                    color: 'white',
                                    fontWeight: 'bold'
                                },
                                title: waypoint.label,
                                zIndex: 1000
                            });
                            
                            const infoContent = `
                                <div style="padding: 10px;">
                                    <h6>${waypoint.label}</h6>
                                    <p style="margin: 5px 0;"><strong>Postcode:</strong> ${waypoint.postcode}</p>
                                    ${waypoint.type === 'job' ? `
                                        <p style="margin: 5px 0;"><strong>Job:</strong> #${waypoint.job.job_number}</p>
                                        <p style="margin: 5px 0;"><strong>Activity:</strong> ${waypoint.job.activity}</p>
                                        <p style="margin: 5px 0;"><small>${waypoint.job.address}</small></p>
                                    ` : ''}
                                    ${waypoint.distance_to_next_miles > 0 ? `
                                        <p style="margin: 5px 0; color: #1a73e8;">
                                            <strong>Next:</strong> ${waypoint.distance_to_next_miles} mi (${waypoint.time_to_next_minutes} min)
                                        </p>
                                    ` : ''}
                                </div>
                            `;
                            
                            const infoWindow = new google.maps.InfoWindow({
                                content: infoContent
                            });
                            
                            marker.addListener('click', () => {
                                infoWindow.open(map, marker);
                            });
                        }
                    });
                });
            } else {
                console.error('Directions request failed:', status);
                alert('Could not load route on map. Error: ' + status);
            }
        });
    }
    
    window.routeMapInstance = map;
}

async function saveRouteOrder() {
    if (!currentOptimizedRoute || !currentRouteDate || !window.currentRunsheetJobs) {
        return { success: true }; // Nothing to save
    }
    
    try {
        // Extract job IDs in current order
        const jobOrder = window.currentRunsheetJobs.map(job => job.id);
        
        const response = await fetch('/api/route-planning/save-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: currentRouteDate,
                job_order: jobOrder,
                route_data: {
                    total_distance_miles: currentOptimizedRoute.total_distance_miles,
                    total_duration_minutes: currentOptimizedRoute.total_duration_minutes,
                    total_jobs: currentOptimizedRoute.total_jobs,
                    route: currentOptimizedRoute.route || []
                }
            })
        });
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('Failed to save route order:', error);
        return { success: false, error: error.message };
    }
}

function getStoredRouteData(date) {
    // Try to get stored route data from localStorage
    const key = `route_data_${date}`;
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : null;
}

function storeRouteData(date, routeData) {
    // Store route data in localStorage
    const key = `route_data_${date}`;
    localStorage.setItem(key, JSON.stringify(routeData));
}

// Make functions globally available
window.optimizeRoute = optimizeRoute;
window.displayOptimizedRoute = displayOptimizedRoute;
window.reorderJobsInModal = reorderJobsInModal;
window.toggleRouteDetails = toggleRouteDetails;
window.saveRouteOrder = saveRouteOrder;
window.getStoredRouteData = getStoredRouteData;
window.storeRouteData = storeRouteData;
