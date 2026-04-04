function initDashboardCharts(data) {
    const ratingData = data.rating || [];
    const scoreData = data.score || [];
    const matchesByPlaylist = data.matches_by_playlist || [];
    const matesFrequency = data.mates_frequency || [];
    const matesWinrate = data.winrate_with_mates || [];

    // Shared playlist color mapping
    const playlistColors = ["#ef4444", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4"];
    const allPlaylists = new Set();
    if (data.score_by_playlist) Object.keys(data.score_by_playlist).forEach(p => allPlaylists.add(p));
    if (data.matches_by_playlist) data.matches_by_playlist.forEach(p => allPlaylists.add(p.playlist));
    
    // Sort playlists alphabetically to ensure consistent color assignment
    const sortedPlaylists = Array.from(allPlaylists).sort();
    const playlistColorMap = {};
    sortedPlaylists.forEach((name, i) => {
        playlistColorMap[name] = playlistColors[i % playlistColors.length];
    });

    const ratingCanvas = document.getElementById("ratingChart");
    if (ratingCanvas) {
        new Chart(ratingCanvas, {
            type: "line",
            data: {
                labels: ratingData.map(x => x.label),
                datasets: [{
                    label: "Rating",
                    data: ratingData.map(x => x.value),
                    borderColor: "#3b82f6",
                    backgroundColor: "rgba(59, 130, 246, 0.1)",
                    fill: true,
                    tension: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    const scoreCanvas = document.getElementById("scoreChart");
    if (scoreCanvas) {
        let datasets = [];
        let labels = [];

        if (data.score_by_playlist && Object.keys(data.score_by_playlist).length > 0) {
            // Collect all unique labels (timestamps) sorted
            const allLabels = new Set();
            for (const playlist in data.score_by_playlist) {
                data.score_by_playlist[playlist].forEach(pt => allLabels.add(pt.label));
            }
            labels = Array.from(allLabels);

            for (const playlist in data.score_by_playlist) {
                const color = playlistColorMap[playlist] || "#3b82f6";
                const playlistPoints = data.score_by_playlist[playlist];
                
                // Map to the global labels to handle gaps if any
                const chartData = labels.map(lbl => {
                    const found = playlistPoints.find(pt => pt.label === lbl);
                    return found ? found.value : null;
                });

                datasets.push({
                    label: playlist,
                    data: chartData,
                    borderColor: color,
                    backgroundColor: color + "1a", // subtle fill
                    tension: 0,
                    spanGaps: true
                });
            }
        } else {
            labels = scoreData.map(x => x.label);
            datasets = [{
                label: "Score",
                data: scoreData.map(x => x.value),
                borderColor: "#3b82f6",
                tension: 0
            }];
        }

        const chart = new Chart(scoreCanvas, {
            type: "line",
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false, // Hide default legend, we use our custom filters
                    }
                }
            }
        });

        // Setup custom filters
        const filterContainer = document.getElementById("scoreChartFilters");
        if (filterContainer && data.score_by_playlist) {
            filterContainer.innerHTML = ""; // Clear
            
            // "Toutes" button
            const btnAll = document.createElement("button");
            btnAll.className = "chart-filter-btn active";
            btnAll.textContent = "Toutes";
            btnAll.onclick = () => {
                document.querySelectorAll("#scoreChartFilters .chart-filter-btn").forEach(b => b.classList.remove("active"));
                btnAll.classList.add("active");
                chart.data.datasets.forEach((ds, i) => {
                    chart.setDatasetVisibility(i, true);
                });
                chart.update();
            };
            filterContainer.appendChild(btnAll);

            datasets.forEach((ds, i) => {
                const btn = document.createElement("button");
                btn.className = "chart-filter-btn";
                btn.textContent = ds.label;
                btn.style.borderLeft = `4px solid ${ds.borderColor}`;
                btn.onclick = () => {
                    // Exclusive selection: deselect all and select this one
                    document.querySelectorAll("#scoreChartFilters .chart-filter-btn").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");

                    // Set visibility: only this dataset is visible
                    chart.data.datasets.forEach((dataset, idx) => {
                        chart.setDatasetVisibility(idx, idx === i);
                    });
                    
                    chart.update();
                };
                filterContainer.appendChild(btn);
            });
        }
    }

    const playlistCanvas = document.getElementById("playlistChart");
    if (playlistCanvas) {
        const labels = matchesByPlaylist.map(x => x.playlist);
        const bgColors = labels.map(name => (playlistColorMap[name] || "#3b82f6"));
        const borderColors = labels.map(name => (playlistColorMap[name] || "#3b82f6"));

        new Chart(playlistCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Matchs",
                    data: matchesByPlaylist.map(x => x.matches),
                    backgroundColor: bgColors.map(c => c + "33"), // 20% opacity
                    borderColor: borderColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    const matesCanvas = document.getElementById("matesChart");
    if (matesCanvas) {
        new Chart(matesCanvas, {
            type: "bar",
            data: {
                labels: matesFrequency.map(x => x.name),
                datasets: [{
                    label: "Matchs total",
                    data: matesFrequency.map(x => x.matches),
                    backgroundColor: "rgba(59, 130, 246, 0.6)",
                    borderColor: "#3b82f6",
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    const matesWinrateCanvas = document.getElementById("matesWinrateChart");
    if (matesWinrateCanvas) {
        new Chart(matesWinrateCanvas, {
            type: "bar",
            data: {
                labels: matesWinrate.map(x => x.name),
                datasets: [{
                    label: "Winrate %",
                    data: matesWinrate.map(x => x.winrate),
                    backgroundColor: "rgba(16, 185, 129, 0.6)",
                    borderColor: "#10b981",
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}