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
                    tension: 0.3
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
                    tension: 0.25,
                    spanGaps: true
                });
            }
        } else {
            labels = scoreData.map(x => x.label);
            datasets = [{
                label: "Score",
                data: scoreData.map(x => x.value),
                borderColor: "#3b82f6",
                tension: 0.25
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
                    label: "Matchs",
                    data: matesFrequency.map(x => x.matches)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
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
                    data: matesWinrate.map(x => x.winrate)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // --- ADVANCED BALLCHASING CHARTS ---
    const history = data.history || [];
    const advMatches = history.filter(m => m.boost_collected !== null).slice(-10);

    const boostCanvas = document.getElementById("boostChart");
    if (boostCanvas) {
        if (advMatches.length === 0) {
            const ctx = boostCanvas.getContext("2d");
            ctx.fillStyle = "#94a3b8";
            ctx.font = "14px Arial";
            ctx.textAlign = "center";
            ctx.fillText("Aucune donnée avancée disponible. Cliquez sur Synchroniser.", boostCanvas.width/2, boostCanvas.height/2);
        } else {
            new Chart(boostCanvas, {
                type: "bar",
                data: {
                    labels: advMatches.map(m => m.date),
                    datasets: [
                        { label: "Collecté", data: advMatches.map(m => m.boost_collected), backgroundColor: "#38bdf8" },
                        { label: "Volé", data: advMatches.map(m => m.boost_stolen), backgroundColor: "#f43f5e" }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });
        }
    }

    const posCanvas = document.getElementById("positioningChart");
    if (posCanvas && advMatches.length > 0) {
        new Chart(posCanvas, {
            type: "bar",
            data: {
                labels: advMatches.map(m => m.date),
                datasets: [
                    { label: "Attaque", data: advMatches.map(m => m.time_offensive_third), backgroundColor: "#ef4444" },
                    { label: "Milieu", data: advMatches.map(m => m.time_neutral_third), backgroundColor: "#f59e0b" },
                    { label: "Défense", data: advMatches.map(m => m.time_defensive_third), backgroundColor: "#3b82f6" }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
            }
        });
    }

    // --- SYNC BUTTON LOGIC ---
    const syncBtn = document.getElementById("syncBallchasingBtn");
    if (syncBtn) {
        syncBtn.addEventListener("click", async () => {
            syncBtn.disabled = true;
            syncBtn.style.opacity = "0.7";
            syncBtn.textContent = "⌛ Sync en cours...";
            try {
                const res = await fetch("/api/matches/fetch-all-ballchasing-stats", { method: "POST" });
                const result = await res.json();
                if (result.status === "done") {
                    alert(`Sync Terminée !\nMatchs mis à jour : ${result.matches_updated}`);
                    window.location.reload();
                } else {
                    alert("Erreur lors de la synchronisation.");
                }
            } catch (e) {
                console.error(e);
                alert("Erreur de connexion.");
            } finally {
                syncBtn.disabled = false;
                syncBtn.style.opacity = "1";
                syncBtn.textContent = "🔄 Synchroniser Stats";
            }
        });
    }
}