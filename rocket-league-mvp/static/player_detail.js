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

    // Shared playlist color mapping
    const playlistColors = ["#ef4444", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4"];
    const allPlaylists = Object.keys(ratingByPlaylist).sort();

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
                tension: 0
            };
        });

        chartInstances.rating = new Chart(ratingCtx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#e2e8f0' } }
                },
                scales: {
                    x: {
                        type: 'category',
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
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
                tension: 0
            };
        });

        chartInstances.score = new Chart(scoreCtx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#e2e8f0' } }
                },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
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
}
