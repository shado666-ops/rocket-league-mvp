// --- AUTO-REFRESH LOGIC (Common) ---
document.addEventListener('DOMContentLoaded', function() {
    let latestMatchId = 0;
    const refreshToggle = document.getElementById("autoRefreshToggle");
    
    if (!refreshToggle) return;

    // Load state immediately
    if (localStorage.getItem("autoRefreshEnabled") === "true") {
        refreshToggle.checked = true;
    } else if (localStorage.getItem("autoRefreshEnabled") === "false") {
        refreshToggle.checked = false;
    }

    // Initialize latestMatchId on load
    fetch("/api/latest-match-id").then(res => res.json()).then(data => {
        latestMatchId = data.latest_id;
        console.log("Common: Current latest match ID:", latestMatchId);
    }).catch(err => console.error("Common: Error fetching latest match ID", err));

    refreshToggle.addEventListener("change", () => {
        localStorage.setItem("autoRefreshEnabled", refreshToggle.checked);
        console.log("Common: Auto-refresh " + (refreshToggle.checked ? "enabled" : "disabled"));
    });

    // WebSocket for real-time refresh
    function setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        const socket = new WebSocket(wsUrl);

        socket.onopen = function() {
            console.log("Common: WebSocket connected!");
        };

        socket.onmessage = function(event) {
            if (event.data === "refresh") {
                if (refreshToggle.checked) {
                    console.log("Common: New match detected via WS! Reloading...");
                    window.location.reload();
                }
            }
        };

        socket.onclose = function() {
            console.log("Common: WebSocket closed. Reconnecting in 5s...");
            setTimeout(setupWebSocket, 5000);
        };
    }

    setupWebSocket();

    // Fallback Polling (15s)
    setInterval(async () => {
        if (!refreshToggle.checked) return;
        try {
            const res = await fetch("/api/latest-match-id");
            if (!res.ok) return;
            const data = await res.json();
            if (data.latest_id > latestMatchId) {
                console.log(`Common: New match detected via polling (${data.latest_id} > ${latestMatchId})! Reloading...`);
                window.location.reload();
            }
        } catch (e) {
            console.warn("Common: Polling failed:", e);
        }
    }, 15000);
});

// --- SHARED HISTORY TABLES LOGIC ---

function setupToggle(btnId, containerId, textId) {
    const toggleBtn = document.getElementById(btnId);
    const container = document.getElementById(containerId);
    const btnText = document.getElementById(textId);
    if (toggleBtn && container) {
        toggleBtn.addEventListener("click", () => {
            const isExpanded = container.classList.toggle("expanded");
            toggleBtn.classList.toggle("active");
            if (btnText) btnText.textContent = isExpanded ? "Réduire le tableau" : "Afficher les matchs";
        });
    }
}

function setupAdvancedHistory(sectionId, tableBodyId, counterIds) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    const tableBody = document.getElementById(tableBodyId);
    const rows = Array.from(tableBody.querySelectorAll("tr:not(.empty-row)"));
    
    let currentPlaylistFilter = "all";
    let currentResultFilter = "all";
    let currentSortCriteria = "date";
    let isAsc = false;

    function updateUI() {
        rows.forEach(row => {
            const p = row.dataset.playlist || "";
            const res = row.dataset.result || "";
            let showP = (currentPlaylistFilter === "all");
            if (currentPlaylistFilter === "ranked") showP = p.includes("classé") || p.includes("ranked");
            if (currentPlaylistFilter === "private") showP = p.includes("privé") || p.includes("private");
            if (currentPlaylistFilter === "tournament") showP = p.includes("tournoi") || p.includes("tournament");
            let showR = (currentResultFilter === "all") || (res === currentResultFilter);
            row.classList.toggle("hidden-row", !(showP && showR));
        });

        const visible = rows.filter(r => !r.classList.contains("hidden-row"));
        if (document.getElementById(counterIds.total)) document.getElementById(counterIds.total).textContent = visible.length;
        if (document.getElementById(counterIds.wins)) document.getElementById(counterIds.wins).textContent = visible.filter(r => r.dataset.result === "win").length;
        if (document.getElementById(counterIds.losses)) document.getElementById(counterIds.losses).textContent = visible.filter(r => r.dataset.result === "loss").length;

        let empty = tableBody.querySelector(".empty-row");
        if (visible.length === 0) {
            if (!empty) {
                empty = document.createElement("tr");
                empty.className = "empty-row";
                empty.innerHTML = `<td colspan="10" class="muted" style="text-align:center; padding: 20px;">Aucun match ne correspond.</td>`;
                tableBody.appendChild(empty);
            }
        } else if (empty) empty.remove();
    }

    function applySort() {
        rows.sort((a, b) => {
            let valA = a.dataset[currentSortCriteria];
            let valB = b.dataset[currentSortCriteria];
            if (currentSortCriteria !== 'date' && currentSortCriteria !== 'playlist' && currentSortCriteria !== 'players') {
                valA = parseFloat(valA) || 0;
                valB = parseFloat(valB) || 0;
            }
            if (valA < valB) return isAsc ? -1 : 1;
            if (valA > valB) return isAsc ? 1 : -1;
            return 0;
        });
        rows.forEach(row => tableBody.appendChild(row));
        updateUI();
    }

    const pBtn = section.querySelector('[data-filter-type="playlist"]');
    if (pBtn) {
        pBtn.addEventListener("click", () => {
            const states = ["all", "ranked", "private", "tournament"];
            const labels = ["TOUS", "CLASSÉ", "PRIVÉ", "TOURNOI"];
            let idx = (states.indexOf(currentPlaylistFilter) + 1) % states.length;
            currentPlaylistFilter = states[idx];
            pBtn.textContent = labels[idx];
            pBtn.classList.toggle("active", currentPlaylistFilter !== "all");
            updateUI();
        });
    }

    const rBtn = section.querySelector('[data-filter-type="result"]');
    if (rBtn) {
        rBtn.addEventListener("click", () => {
            const states = ["all", "win", "loss"];
            const labels = ["TOUS", "WIN", "LOSS"];
            let idx = (states.indexOf(currentResultFilter) + 1) % states.length;
            currentResultFilter = states[idx];
            rBtn.textContent = labels[idx];
            rBtn.classList.toggle("active", currentResultFilter !== "all");
            updateUI();
        });
    }

    section.querySelectorAll("[data-sort]").forEach(btn => {
        btn.addEventListener("click", () => {
            const crit = btn.dataset.sort;
            if (currentSortCriteria === crit) isAsc = !isAsc;
            else { currentSortCriteria = crit; isAsc = false; }
            section.querySelectorAll("[data-sort]").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            section.querySelectorAll(".sort-icon").forEach(i => i.textContent = "▼");
            const icon = btn.querySelector(".sort-icon");
            if (icon) icon.textContent = isAsc ? "▲" : "▼";
            applySort();
        });
    });

    const resetBtn = section.querySelector('[data-action="reset"]');
    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            currentPlaylistFilter = "all";
            currentResultFilter = "all";
            if (pBtn) { pBtn.textContent = "TOUS"; pBtn.classList.remove("active"); }
            if (rBtn) { rBtn.textContent = "TOUS"; rBtn.classList.remove("active"); }
            currentSortCriteria = "date";
            isAsc = false;
            section.querySelectorAll("[data-sort]").forEach(b => {
                b.classList.remove("active");
                if (b.dataset.sort === "date") b.classList.add("active");
            });
            section.querySelectorAll(".sort-icon").forEach(i => i.textContent = "▼");
            const dateHeader = section.querySelector('[data-sort="date"]');
            const dateIcon = dateHeader ? dateHeader.querySelector(".sort-icon") : null;
            if (dateIcon) dateIcon.textContent = "▼";
            applySort();
        });
    }

    updateUI();
}
