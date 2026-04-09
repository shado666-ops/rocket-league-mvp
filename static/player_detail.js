let chartInstances = {};

function initPlayerDetailCharts(data) {
    // Nettoyage des graphiques existants pour éviter les superpositions lors du changement d'onglet
    Object.values(chartInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartInstances = {};

    // Data extraction
    const ratingByPlaylist = data.rating_by_playlist || {};
    const scoreByPlaylist = data.score_by_playlist || {};
    const playerName = data.player_name || "Joueur";

    // Colors
    const playlistColors = ["#38bdf8", "#4ade80", "#fb7185", "#fbbf24", "#a78bfa", "#2dd4bf", "#f472b6", "#818cf8", "#c084fc", "#fb923c"];
    const allPlaylists = Array.from(new Set([...Object.keys(ratingByPlaylist), ...Object.keys(scoreByPlaylist)])).sort();
    const getPlaylistColor = (pName) => playlistColors[allPlaylists.indexOf(pName) % playlistColors.length];

    // 1. Rating Chart
    const ratingCtx = document.getElementById('ratingChart');
    if (ratingCtx) {
        const datasets = allPlaylists.map(playlist => ({
            label: playlist,
            data: (ratingByPlaylist[playlist] || []).map(d => ({ x: d.label, y: d.value })),
            borderColor: getPlaylistColor(playlist),
            backgroundColor: getPlaylistColor(playlist) + "20",
            fill: true,
            tension: 0,
            spanGaps: false
        }));
        chartInstances.rating = new Chart(ratingCtx, {
            type: 'line',
            data: { datasets },
            options: { responsive: true, plugins: { legend: { display: false } },
                scales: {
                    x: { type: 'category', ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    // 2. Score Chart
    const scoreCtx = document.getElementById('scoreChart');
    if (scoreCtx) {
        const datasets = allPlaylists.map(playlist => ({
            label: playlist,
            data: (scoreByPlaylist[playlist] || []).map(d => ({ x: d.label, y: d.value })),
            borderColor: getPlaylistColor(playlist),
            backgroundColor: getPlaylistColor(playlist) + "20",
            fill: true,
            tension: 0,
            spanGaps: false
        }));
        chartInstances.score = new Chart(scoreCtx, {
            type: 'line',
            data: { datasets },
            options: { responsive: true, plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    // Small charts
    const renderSmallChart = (canvasId, label, chartData, color) => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !chartData || chartData.length === 0) return;
        chartInstances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.map(d => d.label),
                datasets: [{ label: label, data: chartData.map(d => d.value), borderColor: color, backgroundColor: color + "20", fill: true, tension: 0 }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } } } }
        });
    };

    renderSmallChart('goalsChart', 'Buts', data.goals, "#4ade80");
    renderSmallChart('shotsChart', 'Tirs', data.shots, "#3b82f6");
    renderSmallChart('assistsChart', 'Passes', data.assists, "#f59e0b");
    renderSmallChart('savesChart', 'Arrêts', data.saves, "#a78bfa");
    renderSmallChart('boostChart', 'Boost', data.boost, "#ef4444");
    renderSmallChart('possessionChart', 'Possession', data.possession, "#06b6d4");
    renderSmallChart('demolishesChart', 'Démos', data.demolishes, "#94a3b8");

    // Init advanced history for all tables
    setupAdvancedHistory("history-recent", "historyTableBodyRecent", { total: "historyCountRecent", wins: "historyWinsRecent", losses: "historyLossesRecent" });
    setupAdvancedHistory("history-global", "historyTableBodyGlobal", { total: "historyCountGlobal", wins: "historyWinsGlobal", losses: "historyLossesGlobal" });
    setupAdvancedHistory("history-ranked", "historyTableBodyRanked", { total: "historyCountRanked", wins: "historyWinsRanked", losses: "historyLossesRanked" });
    setupAdvancedHistory("history-private", "historyTableBodyPrivate", { total: "historyCountPrivate", wins: "historyWinsPrivate", losses: "historyLossesPrivate" });
    setupAdvancedHistory("history-tournament", "historyTableBodyTournament", { total: "historyCountTournament", wins: "historyWinsTournament", losses: "historyLossesTournament" });

    // Chart Filters
    if (chartInstances.rating) {
        chartInstances.rating._originalData = { labels: [...chartInstances.rating.data.labels], datasets: [...chartInstances.rating.data.datasets.map(ds => ({...ds}))] };
        createChartFilters(chartInstances.rating, 'ratingChartFilters', allPlaylists, ratingByPlaylist);
    }
    if (chartInstances.score) {
        chartInstances.score._originalData = { labels: [...chartInstances.score.data.labels], datasets: [...chartInstances.score.data.datasets.map(ds => ({...ds}))] };
        createChartFilters(chartInstances.score, 'scoreChartFilters', allPlaylists, scoreByPlaylist);
    }
}

// Redundant functions removed (now in common.js)

function createChartFilters(chart, containerId, playlists, playlistDataMap) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    const btnAll = document.createElement('button');
    btnAll.className = 'chart-filter-btn active';
    btnAll.textContent = 'Tous';
    btnAll.onclick = () => {
        container.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
        btnAll.classList.add('active');
        chart.data.labels = [];
        chart.data.datasets = [...chart._originalData.datasets.map(ds => ({...ds}))];
        chart.data.datasets.forEach(ds => { ds.hidden = false; });
        if (chart.options.scales && chart.options.scales.x) { delete chart.options.scales.x.min; delete chart.options.scales.x.max; }
        chart.update();
    };
    container.appendChild(btnAll);

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
            chart.data.labels = pData.map(d => d.label);
            chart.data.datasets = [{ ...originalDs, hidden: false, data: pData.map(d => ({ x: d.label, y: d.value })) }];
            if (chart.options.scales && chart.options.scales.x) { delete chart.options.scales.x.min; delete chart.options.scales.x.max; }
            chart.update();
        };
        container.appendChild(btn);
    });
}

// Global UI Initialization
document.addEventListener("DOMContentLoaded", () => {
    setupToggle("toggleHistoryRecent", "historyContainerRecent", "btnTextRecent");
    setupToggle("toggleHistoryGlobal", "historyContainerGlobal", "btnTextGlobal");
    setupToggle("toggleHistoryRanked", "historyContainerRanked", "btnTextRanked");
    setupToggle("toggleHistoryPrivate", "historyContainerPrivate", "btnTextPrivate");
    setupToggle("toggleHistoryTournament", "historyContainerTournament", "btnTextTournament");
});
