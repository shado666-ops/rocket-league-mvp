let chartInstances = {};

function initPlayerDetailCharts(data) {
    // Nettoyage des graphiques existants pour éviter les superpositions lors du changement d'onglet
    Object.values(chartInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartInstances = {};

    // Data extraction based on stats_service.py structure
    const ratingByPlaylist = data.rating_by_playlist || {};
    const scoreByPlaylist = data.score_by_playlist || {};
    const radarData = data.radar || [];
    const pieData = data.pie || [];
    const playerName = data.player_name || "Joueur";

    // Shared playlist color mapping - Expanded palette for better distinction
    const playlistColors = [
        "#38bdf8", // Sky Blue
        "#4ade80", // Green
        "#fb7185", // Rose
        "#fbbf24", // Amber
        "#a78bfa", // Violet
        "#2dd4bf", // Teal
        "#f472b6", // Pink
        "#818cf8", // Indigo
        "#c084fc", // Purple
        "#fb923c"  // Orange
    ];
    
    // Union of all playlists from both sources to ensure color consistency across charts
    const allPlaylists = Array.from(new Set([
        ...Object.keys(ratingByPlaylist),
        ...Object.keys(scoreByPlaylist)
    ])).sort();

    const getPlaylistColor = (pName) => {
        const idx = allPlaylists.indexOf(pName);
        return playlistColors[idx % playlistColors.length];
    };

    // 1. Rating Chart
    const ratingCtx = document.getElementById('ratingChart');
    if (ratingCtx) {
        const datasets = allPlaylists.map(playlist => {
            const pData = ratingByPlaylist[playlist] || [];
            return {
                label: playlist,
                data: pData.map(d => ({ x: d.label, y: d.value })),
                borderColor: getPlaylistColor(playlist),
                backgroundColor: getPlaylistColor(playlist) + "20",
                fill: true,
                tension: 0,
                spanGaps: false
            };
        });

        chartInstances.rating = new Chart(ratingCtx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        type: 'category',
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    }

    // 2. Score Chart
    const scoreCtx = document.getElementById('scoreChart');
    if (scoreCtx) {
        const datasets = allPlaylists.map(playlist => {
            const pData = scoreByPlaylist[playlist] || [];
            return {
                label: playlist,
                data: pData.map(d => ({ x: d.label, y: d.value })),
                borderColor: getPlaylistColor(playlist),
                backgroundColor: getPlaylistColor(playlist) + "20",
                fill: true,
                tension: 0,
                spanGaps: false
            };
        });

        chartInstances.score = new Chart(scoreCtx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    // Small evolution charts
    const renderSmallChart = (canvasId, label, chartData, color) => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !chartData || chartData.length === 0) return;
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.map(d => d.label),
                datasets: [{
                    label: label,
                    data: chartData.map(d => d.value),
                    borderColor: color,
                    backgroundColor: color + "20",
                    fill: true,
                    tension: 0
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    };

    renderSmallChart('goalsChart', 'Buts', data.goals, "#4ade80");
    renderSmallChart('shotsChart', 'Tirs', data.shots, "#3b82f6");
    renderSmallChart('assistsChart', 'Passes', data.assists, "#f59e0b");
    renderSmallChart('savesChart', 'Arrêts', data.saves, "#a78bfa");
    renderSmallChart('boostChart', 'Boost', data.boost, "#ef4444");
    renderSmallChart('possessionChart', 'Possession', data.possession, "#06b6d4");
    renderSmallChart('demolishesChart', 'Démos', data.demolishes, "#94a3b8");

    // Radar Chart
    const radarCtx = document.getElementById('radarChart');
    if (radarCtx && radarData.length === 4) {
        chartInstances.radar = new Chart(radarCtx, {
            type: 'radar',
            data: {
                labels: ["Buts", "Arrêts", "Tirs", "Passes"],
                datasets: [{
                    label: playerName,
                    data: radarData,
                    backgroundColor: 'rgba(56, 189, 248, 0.2)',
                    borderColor: '#38bdf8',
                    pointBackgroundColor: '#38bdf8'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.1)' },
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        pointLabels: { color: '#94a3b8' },
                        ticks: { display: false },
                        suggestedMin: 0,
                        suggestedMax: 2
                    }
                }
            }
        });
    }

    // Pie Chart (Win/Loss)
    const pieCtx = document.getElementById('pieChart');
    if (pieCtx && pieData.length === 2) {
        chartInstances.pie = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Victoires', 'Défaites'],
                datasets: [{
                    data: pieData,
                    backgroundColor: ['#22c55e', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#e2e8f0' } }
                }
            }
        });
    }

    // Initialize custom filters for main interactive charts
    if (chartInstances.rating) {
        chartInstances.rating._originalData = {
            labels: [...chartInstances.rating.data.labels],
            datasets: [...chartInstances.rating.data.datasets.map(ds => ({...ds}))]
        };
        createChartFilters(chartInstances.rating, 'ratingChartFilters', allPlaylists, ratingByPlaylist);
    }
    if (chartInstances.score) {
        chartInstances.score._originalData = {
            labels: [...chartInstances.score.data.labels],
            datasets: [...chartInstances.score.data.datasets.map(ds => ({...ds}))]
        };
        createChartFilters(chartInstances.score, 'scoreChartFilters', allPlaylists, scoreByPlaylist);
    }
}

/**
 * Creates custom filter buttons for a chart to allow exclusive selection and auto-scaling.
 */
function createChartFilters(chart, containerId, playlists, playlistDataMap) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    // "Tous" Button (Reset)
    const btnAll = document.createElement('button');
    btnAll.className = 'chart-filter-btn active';
    btnAll.textContent = 'Tous';
    btnAll.onclick = () => {
        container.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
        btnAll.classList.add('active');
        
        // Restore original datasets
        chart.data.labels = []; // Empty labels to let auto-inference happen (original behavior)
        chart.data.datasets = [...chart._originalData.datasets.map(ds => ({...ds}))];
        chart.data.datasets.forEach(ds => { ds.hidden = false; });
        
        // Reset scale options
        if (chart.options.scales && chart.options.scales.x) {
            delete chart.options.scales.x.min;
            delete chart.options.scales.x.max;
        }
        
        chart.update();
    };
    container.appendChild(btnAll);

    // Individual Playlist Buttons
    playlists.forEach(playlist => {
        const originalDs = chart._originalData.datasets.find(ds => ds.label === playlist);
        const color = originalDs ? originalDs.borderColor : '#3b82f6';
        
        const btn = document.createElement('button');
        btn.className = 'chart-filter-btn';
        btn.innerHTML = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${color}; margin-right:6px;"></span>${playlist}`;
        
        btn.onclick = () => {
            container.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const pData = playlistDataMap[playlist] || [];
            
            // Set labels to ONLY this playlist's dates (removes gaps)
            chart.data.labels = pData.map(d => d.label);
            
            // Set datasets to ONLY this single playlist dataset
            chart.data.datasets = [{
                ...originalDs,
                hidden: false,
                data: pData.map(d => ({ x: d.label, y: d.value }))
            }];
            
            // Reset scale options (they will auto-adjust to the new labels/data)
            if (chart.options.scales && chart.options.scales.x) {
                delete chart.options.scales.x.min;
                delete chart.options.scales.x.max;
            }

            chart.update();
        };
        container.appendChild(btn);
    });
}

