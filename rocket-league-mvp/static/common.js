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
