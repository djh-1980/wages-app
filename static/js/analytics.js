// Analytics Tab Functions

// Global chart variables for analytics
let yearComparisonChart = null;
let forecastChart = null;

// Load analytics when tab is clicked
document.addEventListener('DOMContentLoaded', function() {
    const analyticsTab = document.getElementById('analytics-tab');
    if (analyticsTab) {
        analyticsTab.addEventListener('click', function() {
            loadAnalytics();
        });
    }
});

// Main function to load all analytics
async function loadAnalytics() {
    loadYearComparison();
    loadEarningsForecast();
    loadWeeklyPerformance();
    
    // Populate year filter first, then load heatmap
    await populateHeatmapYearFilter();
    loadClientHeatmap();
}

// Year-over-Year Comparison Chart
async function loadYearComparison() {
    try {
        const response = await fetch('/api/year_comparison');
        const data = await response.json();
        
        const ctx = document.getElementById('yearComparisonChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (yearComparisonChart) {
            yearComparisonChart.destroy();
        }
        
        // Prepare datasets for each year
        const datasets = [];
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#4facfe',
            '#43e97b', '#fa709a', '#fee140', '#30cfd0'
        ];
        
        let colorIndex = 0;
        for (const [year, weekData] of Object.entries(data)) {
            datasets.push({
                label: `Tax Year ${year}`,
                data: weekData.map(w => ({x: w.week, y: w.amount})),
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '20',
                borderWidth: 2,
                tension: 0.4,
                fill: false
            });
            colorIndex++;
        }
        
        yearComparisonChart = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: £${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Week Number'
                        },
                        min: 1,
                        max: 52
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Net Payment (£)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '£' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading year comparison:', error);
    }
}

// Earnings Forecast Chart
async function loadEarningsForecast() {
    try {
        const response = await fetch('/api/earnings_forecast');
        const data = await response.json();
        
        if (data.error) {
            console.error('Forecast error:', data.error);
            return;
        }
        
        // Update summary cards
        document.getElementById('forecastYear').textContent = data.current_year;
        document.getElementById('forecastWeeksWorked').textContent = data.weeks_worked;
        document.getElementById('forecastTotalEarned').textContent = '£' + data.total_earned.toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('forecastProjected').textContent = '£' + data.projected_year_end.toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        
        // Set trend badge
        const trendBadge = document.getElementById('forecastTrend');
        const trendClass = data.trend === 'increasing' ? 'success' : data.trend === 'decreasing' ? 'danger' : 'secondary';
        const trendIcon = data.trend === 'increasing' ? '↑' : data.trend === 'decreasing' ? '↓' : '→';
        trendBadge.innerHTML = `<span class="badge bg-${trendClass}">${trendIcon} ${data.trend}</span>`;
        
        // Create forecast chart
        const ctx = document.getElementById('forecastChart').getContext('2d');
        
        if (forecastChart) {
            forecastChart.destroy();
        }
        
        // Prepare data - actual weeks + forecast weeks
        const actualWeeks = Array.from({length: data.weeks_worked}, (_, i) => i + 1);
        const forecastWeeks = data.forecast.map(f => f.week);
        const allWeeks = [...actualWeeks, ...forecastWeeks];
        
        // We don't have actual historical data in this response, so we'll just show forecast
        // In a real scenario, you'd fetch historical data too
        const forecastData = data.forecast.map(f => f.predicted_amount);
        
        forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: forecastWeeks,
                datasets: [{
                    label: 'Predicted Earnings',
                    data: forecastData,
                    borderColor: '#43e97b',
                    backgroundColor: 'rgba(67, 233, 123, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const forecast = data.forecast[context.dataIndex];
                                return [
                                    `Predicted: £${context.parsed.y.toFixed(2)}`,
                                    `Confidence: ${forecast.confidence}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Week Number'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Predicted Amount (£)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '£' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading forecast:', error);
    }
}

// Client Activity Heatmap
async function loadClientHeatmap(taxYear = '') {
    try {
        const url = taxYear ? `/api/client_heatmap?tax_year=${taxYear}` : '/api/client_heatmap';
        const response = await fetch(url);
        const data = await response.json();
        
        const container = document.getElementById('heatmapContainer');
        
        // Create heatmap table
        const topClients = data.top_clients.slice(0, 10); // Top 10 clients
        const months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        
        // Build data structure
        const heatmapData = {};
        topClients.forEach(client => {
            heatmapData[client] = {};
            months.forEach(month => {
                heatmapData[client][month] = 0;
            });
        });
        
        // Fill in the data
        data.heatmap_data.forEach(row => {
            if (heatmapData[row.client] && row.month >= 1 && row.month <= 12) {
                heatmapData[row.client][row.month] = row.total_amount;
            }
        });
        
        // Find max value for color scaling
        let maxValue = 0;
        Object.values(heatmapData).forEach(clientData => {
            Object.values(clientData).forEach(value => {
                if (value > maxValue) maxValue = value;
            });
        });
        
        // Generate HTML table
        let html = `
            <table class="table table-bordered table-sm" style="min-width: 800px;">
                <thead>
                    <tr>
                        <th style="min-width: 200px;">Client</th>
                        ${months.map(m => `<th class="text-center">M${m}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
        `;
        
        topClients.forEach(client => {
            html += `<tr><td class="fw-bold">${client.substring(0, 30)}${client.length > 30 ? '...' : ''}</td>`;
            months.forEach(month => {
                const value = heatmapData[client][month];
                const intensity = maxValue > 0 ? (value / maxValue) : 0;
                const bgColor = value > 0 
                    ? `rgba(102, 126, 234, ${0.2 + (intensity * 0.8)})` 
                    : '#f8f9fa';
                const textColor = intensity > 0.5 ? '#fff' : '#000';
                html += `
                    <td class="text-center" style="background-color: ${bgColor}; color: ${textColor};" 
                        title="${client} - Month ${month}: £${value.toFixed(2)}">
                        ${value > 0 ? '£' + value.toFixed(0) : '-'}
                    </td>
                `;
            });
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        
        if (topClients.length === 0) {
            html = '<div class="alert alert-info">No client data available</div>';
        }
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading client heatmap:', error);
        document.getElementById('heatmapContainer').innerHTML = 
            '<div class="alert alert-danger">Error loading heatmap</div>';
    }
}

// Weekly Performance Analysis
async function loadWeeklyPerformance() {
    try {
        const response = await fetch('/api/weekly_performance');
        const data = await response.json();
        
        // Update average
        document.getElementById('avgWeeklyEarnings').textContent = 
            '£' + data.average.toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        
        // Populate best weeks table
        const bestTable = document.getElementById('bestWeeksTable');
        let bestHtml = '';
        data.best_weeks.forEach((week, index) => {
            const percentAbove = ((week.net_payment - data.average) / data.average * 100).toFixed(1);
            bestHtml += `
                <tr>
                    <td><span class="badge bg-success">${index + 1}</span></td>
                    <td>${week.tax_year} W${week.week_number}</td>
                    <td class="fw-bold text-success">£${week.net_payment.toLocaleString('en-GB', {minimumFractionDigits: 2})}</td>
                    <td>${week.job_count}</td>
                </tr>
            `;
        });
        bestTable.innerHTML = bestHtml;
        
        // Populate worst weeks table
        const worstTable = document.getElementById('worstWeeksTable');
        let worstHtml = '';
        data.worst_weeks.forEach((week, index) => {
            const percentBelow = ((data.average - week.net_payment) / data.average * 100).toFixed(1);
            worstHtml += `
                <tr>
                    <td><span class="badge bg-danger">${index + 1}</span></td>
                    <td>${week.tax_year} W${week.week_number}</td>
                    <td class="fw-bold text-danger">£${week.net_payment.toLocaleString('en-GB', {minimumFractionDigits: 2})}</td>
                    <td>${week.job_count}</td>
                </tr>
            `;
        });
        worstTable.innerHTML = worstHtml;
        
    } catch (error) {
        console.error('Error loading weekly performance:', error);
    }
}

// Populate heatmap year filter
async function populateHeatmapYearFilter() {
    try {
        const response = await fetch('/api/tax_years');
        const years = await response.json();
        
        const select = document.getElementById('heatmapYearFilter');
        select.innerHTML = '<option value="">All Years</option>';
        years.forEach(year => {
            select.innerHTML += `<option value="${year}">${year}</option>`;
        });
    } catch (error) {
        console.error('Error loading years for heatmap filter:', error);
    }
}
