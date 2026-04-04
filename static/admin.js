/**
 * Admin Panel Javascript
 * Handles database backups, resets, member management, and log viewing.
 */

async function fetchLogs() {
    const serverLogEl = document.getElementById('serverLog');
    const watcherLogEl = document.getElementById('watcherLog');
    
    serverLogEl.textContent = "Fetching server logs...";
    watcherLogEl.textContent = "Fetching watcher logs...";
    
    try {
        const response = await fetch('/admin/logs');
        const data = await response.json();
        
        serverLogEl.textContent = data.server || "Server log is empty or not found.";
        watcherLogEl.textContent = data.watcher || "Watcher log is empty or not found.";
        
        // Auto-scroll to bottom
        serverLogEl.scrollTop = serverLogEl.scrollHeight;
        watcherLogEl.scrollTop = watcherLogEl.scrollHeight;
    } catch (error) {
        console.error("Error fetching logs:", error);
        serverLogEl.textContent = "Error loading logs.";
    }
}

async function clearLogs() {
    if (!confirm("Voulez-vous vraiment effacer tous les fichiers logs ?")) return;
    
    try {
        const response = await fetch('/admin/logs/clear', { method: 'POST' });
        const data = await response.json();
        alert(data.message);
        fetchLogs();
    } catch (error) {
        alert("Erreur lors de l'effacement des logs.");
    }
}

async function backupDatabase() {
    try {
        const response = await fetch('/admin/backup', { method: 'POST' });
        const data = await response.json();
        alert(data.message);
        
        // Update last backup time (approximate, or we could fetch it)
        const now = new Date();
        document.getElementById('lastBackupTime').textContent = now.toLocaleString('fr-FR');
    } catch (error) {
        alert("Erreur lors de la sauvegarde.");
    }
}

async function resetDatabase() {
    if (!confirm("ATTENTION : Cette action supprimera TOUTES les données (matchs, stats, membres). Voulez-vous vraiment continuer ?")) {
        return;
    }
    
    const confirm2 = prompt("Tapez 'RESET' pour confirmer la suppression définitive :");
    if (confirm2 !== "RESET") {
        alert("Réinitialisation annulée.");
        return;
    }
    
    try {
        const response = await fetch('/admin/reset', { method: 'POST' });
        const data = await response.json();
        alert(data.message);
        window.location.reload();
    } catch (error) {
        alert("Erreur lors de la réinitialisation.");
    }
}

async function addMember() {
    const input = document.getElementById('newMemberName');
    const name = input.value.trim();
    if (!name) return;
    
    try {
        const response = await fetch(`/admin/members?name=${encodeURIComponent(name)}`, { method: 'POST' });
        if (response.ok) {
            input.value = "";
            window.location.reload();
        } else {
            const data = await response.json();
            alert(data.detail || "Erreur lors de l'ajout.");
        }
    } catch (error) {
        alert("Erreur réseau.");
    }
}

async function deleteMember(name) {
    if (!confirm(`Supprimer le membre ${name} du club ?`)) return;
    
    try {
        const response = await fetch(`/admin/members/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (response.ok) {
            window.location.reload();
        } else {
            alert("Erreur lors de la suppression.");
        }
    } catch (error) {
        alert("Erreur réseau.");
    }
}

async function addAlias(memberId) {
    const input = document.getElementById(`aliasInput-${memberId}`);
    const pseudo = input.value.trim();
    if (!pseudo) return;
    
    try {
        const response = await fetch(`/admin/members/${memberId}/aliases?pseudo=${encodeURIComponent(pseudo)}`, { method: 'POST' });
        if (response.ok) {
            input.value = "";
            window.location.reload();
        } else {
            const data = await response.json();
            alert(data.detail || "Erreur lors de l'ajout de l'alias.");
        }
    } catch (error) {
        alert("Erreur réseau.");
    }
}

async function deleteAlias(aliasId) {
    if (!confirm("Supprimer cet alias ?")) return;
    
    try {
        const response = await fetch(`/admin/aliases/${aliasId}`, { method: 'DELETE' });
        if (response.ok) {
            window.location.reload();
        } else {
            alert("Erreur lors de la suppression de l'alias.");
        }
    } catch (error) {
        alert("Erreur réseau.");
    }
}
async function saveGeneralSettings() {
    const clubName = document.getElementById('clubNameInput').value;
    const clubTag = document.getElementById('clubTagInput').value;
    const statusDiv = document.getElementById('settingsStatus');
    
    statusDiv.style.display = 'block';
    statusDiv.style.color = 'rgba(255,255,255,0.7)';
    statusDiv.textContent = 'Enregistrement...';

    try {
        const response = await fetch('/admin/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                club_name: clubName,
                club_tag: clubTag
            })
        });

        if (response.ok) {
            statusDiv.style.color = '#4ade80';
            statusDiv.textContent = 'Paramètres enregistrés avec succès !';
            setTimeout(() => { location.reload(); }, 1000);
        } else {
            throw new Error('Erreur lors de l\'enregistrement');
        }
    } catch (error) {
        statusDiv.style.color = '#f87171';
        statusDiv.textContent = 'Erreur : ' + error.message;
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    fetchLogs();
    
    // Refresh logs every 30 seconds if tab is active
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            fetchLogs();
        }
    }, 30000);
});
