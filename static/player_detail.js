function initPlayerDetailCharts(data) {
    const ratingData = data.rating || [];
    const scoreData = data.score || [];
    const goalsSavesData = data.goals_saves || [];
    const radarData = data.radar || [];
    const pieData = data.pie || [];
    const playerName = data.player_name || "Joueur";

    // Shared playlist color mapping
    const playlistColors = ["#ef4444", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4"];
    const allPlaylists = new Set();
    if (data.score_by_playlist) Object.keys(data.score_by_playlist).forEach(p => allPlaylists.add(p));
    
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
            const allLabels = new Set();
            for (const playlist in data.score_by_playlist) {
                data.score_by_playlist[playlist].forEach(pt => allLabels.add(pt.label));
            }
            labels = Array.from(allLabels);

            for (const playlist in data.score_by_playlist) {
                const color = playlistColorMap[playlist] || "#3b82f6";
                const playlistPoints = data.score_by_playlist[playlist];
                
                const chartData = labels.map(lbl => {
                    const found = playlistPoints.find(pt => pt.label === lbl);
                    return found ? found.value : null;
                });

                datasets.push({
                    label: playlist,
                    data: chartData,
                    borderColor: color,
                    backgroundColor: color + "1a",
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
                        display: false,
                    }
                }
            }
        });

        const filterContainer = document.getElementById("scoreChartFilters");
        if (filterContainer && data.score_by_playlist) {
            filterContainer.innerHTML = "";
            
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
                    btn.classList.toggle("active");
                    btnAll.classList.remove("active");

                    const anyActive = Array.from(filterContainer.querySelectorAll(".chart-filter-btn:not(:first-child)")).some(b => b.classList.contains("active"));
                    
                    if (!anyActive) {
                        btnAll.click();
                        return;
                    }

                    chart.data.datasets.forEach((dataset, idx) => {
                        const targetBtn = Array.from(filterContainer.querySelectorAll(".chart-filter-btn")).find(b => b.textContent === dataset.label);
                        chart.setDatasetVisibility(idx, targetBtn && targetBtn.classList.contains("active"));
                    });
                    
                    chart.update();
                };
                filterContainer.appendChild(btn);
            });
        }
    }

    const goalsSavesCanvas = document.getElementById("goalsSavesChart");
    if (goalsSavesCanvas) {
        new Chart(goalsSavesCanvas, {
            type: "bar",
            data: {
                labels: goalsSavesData.map(x => x.label),
                datasets: [
                    {
                        label: "Buts",
                        data: goalsSavesData.map(x => x.goals)
                    },
                    {
                        label: "Saves",
                        data: goalsSavesData.map(x => x.saves)
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    const radarCanvas = document.getElementById("radarChart");
    if (radarCanvas) {
        new Chart(radarCanvas, {
            type: "radar",
            data: {
                labels: ["Buts", "Assists", "Saves", "Shots", "Score"],
                datasets: [{
                    label: playerName,
                    data: radarData
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    const pieCanvas = document.getElementById("pieChart");
    if (pieCanvas) {
        new Chart(pieCanvas, {
            type: "pie",
            data: {
                labels: ["Victoires", "Défaites"],
                datasets: [{
                    data: pieData
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}