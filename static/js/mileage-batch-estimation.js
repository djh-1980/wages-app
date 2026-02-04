/**
 * Batch Mileage Estimation
 * Automatically estimate mileage for days with missing records
 */

let estimationResults = [];

async function startBatchEstimation() {
    const yearSelect = document.getElementById('batchEstimateYear');
    const year = yearSelect.value;
    
    if (!year) {
        alert('Please select a year');
        return;
    }
    
    const btn = document.getElementById('batchEstimateBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Finding missing days...';
    
    try {
        // Find all days with missing mileage
        const response = await fetch('/api/route-planning/batch-estimate-mileage', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ year: year })
        });
        
        const data = await response.json();
        
        if (!data.success || data.dates.length === 0) {
            alert(data.message || `No missing mileage found for ${year}`);
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Estimate All Missing';
            return;
        }
        
        // Show progress bar
        document.getElementById('batchEstimationProgress').style.display = 'block';
        document.getElementById('estimationPreview').style.display = 'none';
        
        // Estimate each day
        estimationResults = [];
        const total = data.dates.length;
        let successCount = 0;
        let failCount = 0;
        
        for (let i = 0; i < data.dates.length; i++) {
            const dateInfo = data.dates[i];
            updateProgress(i + 1, total);
            
            try {
                // Optimize route for this date with timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
                
                const routeResponse = await fetch('/api/route-planning/optimize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        date: dateInfo.date,
                        include_depot: true
                    }),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                const routeData = await routeResponse.json();
                
                if (routeData.success) {
                    estimationResults.push({
                        date: dateInfo.date,
                        job_count: dateInfo.job_count,
                        estimated_miles: routeData.total_distance_miles,
                        estimated_time: routeData.total_duration_minutes
                    });
                    successCount++;
                    console.log(`✓ Estimated ${dateInfo.date}: ${routeData.total_distance_miles} miles`);
                } else {
                    failCount++;
                    console.error(`✗ Failed ${dateInfo.date}: ${routeData.error}`);
                }
            } catch (error) {
                failCount++;
                console.error(`✗ Error estimating ${dateInfo.date}:`, error.message);
                // Continue to next day even if this one fails
            }
            
            // Small delay between requests to avoid overwhelming the API
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        console.log(`Batch estimation complete: ${successCount} succeeded, ${failCount} failed`);
        
        // Hide progress, show preview
        document.getElementById('batchEstimationProgress').style.display = 'none';
        displayEstimationPreview();
        
    } catch (error) {
        console.error('Batch estimation error:', error);
        alert('Error during batch estimation: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Estimate All Missing';
    }
}

function updateProgress(current, total) {
    const percentage = Math.round((current / total) * 100);
    document.getElementById('progressText').textContent = `${current} / ${total}`;
    document.getElementById('progressBar').style.width = `${percentage}%`;
}

function displayEstimationPreview() {
    const tbody = document.getElementById('estimationPreviewBody');
    
    tbody.innerHTML = estimationResults.map(result => {
        const hours = Math.floor(result.estimated_time / 60);
        const minutes = Math.round(result.estimated_time % 60);
        
        return `
            <tr>
                <td><strong>${result.date}</strong></td>
                <td><span class="badge bg-info">${result.job_count} jobs</span></td>
                <td class="text-end"><strong>${result.estimated_miles} miles</strong></td>
                <td class="text-end">${hours}h ${minutes}m</td>
                <td class="text-center">
                    <input type="number" class="form-control form-control-sm" 
                           value="${result.estimated_miles}" 
                           step="0.1" 
                           style="width: 100px; display: inline-block;"
                           onchange="updateEstimate('${result.date}', this.value)">
                </td>
            </tr>
        `;
    }).join('');
    
    document.getElementById('estimationPreview').style.display = 'block';
}

function updateEstimate(date, newMiles) {
    const result = estimationResults.find(r => r.date === date);
    if (result) {
        result.estimated_miles = parseFloat(newMiles);
    }
}

async function saveBatchEstimation() {
    if (estimationResults.length === 0) {
        alert('No estimates to save');
        return;
    }
    
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';
    
    try {
        let savedCount = 0;
        
        for (const result of estimationResults) {
            const response = await fetch('/api/runsheets/update-statuses', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    date: result.date,
                    updates: [],
                    mileage: result.estimated_miles,
                    fuel_cost: null
                })
            });
            
            const data = await response.json();
            if (data.success) {
                savedCount++;
            }
        }
        
        alert(`Successfully saved ${savedCount} mileage estimates!`);
        
        // Clear preview and reload data
        cancelBatchEstimation();
        loadMileageData();
        loadMissingMileageReport();
        
    } catch (error) {
        console.error('Save error:', error);
        alert('Error saving estimates: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save"></i> Save All Estimates';
    }
}

function cancelBatchEstimation() {
    document.getElementById('estimationPreview').style.display = 'none';
    document.getElementById('batchEstimationProgress').style.display = 'none';
    estimationResults = [];
}

// Make functions globally available
window.startBatchEstimation = startBatchEstimation;
window.updateEstimate = updateEstimate;
window.saveBatchEstimation = saveBatchEstimation;
window.cancelBatchEstimation = cancelBatchEstimation;
