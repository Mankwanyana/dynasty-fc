// ============================================================
// API BASE
// ============================================================
const API_BASE = '/api';

// ============================================================
// LOAD DASHBOARD
// ============================================================
async function loadDashboard() {
    try {
        const playersRes = await fetch(`${API_BASE}/players`);
        const players = await playersRes.json();

        const staffRes = await fetch(`${API_BASE}/staff`);
        const staff = await staffRes.json();

        const teamsRes = await fetch(`${API_BASE}/teams`);
        const teams = await teamsRes.json();

        const financeRes = await fetch(`${API_BASE}/finance`);
        const finance = await financeRes.json();

        let totalIncome = 0, totalExpenses = 0;
        finance.forEach(row => {
            totalIncome += parseFloat(row.income || 0);
            totalExpenses += parseFloat(row.expenses || 0);
        });

        const cards = document.getElementById('dashboardCards');
        if (cards) {
            cards.innerHTML = `
                <div class="dash-card"><h3>Players</h3><div class="number">${players.length}</div></div>
                <div class="dash-card"><h3>Staff</h3><div class="number">${staff.length}</div></div>
                <div class="dash-card"><h3>Teams</h3><div class="number">${teams.length}</div></div>
                <div class="dash-card"><h3>Income</h3><div class="number">R${totalIncome.toFixed(2)}</div></div>
                <div class="dash-card"><h3>Expenses</h3><div class="number">R${totalExpenses.toFixed(2)}</div></div>
                <div class="dash-card"><h3>Net</h3><div class="number">R${(totalIncome - totalExpenses).toFixed(2)}</div></div>
            `;
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// ============================================================
// LOAD PLAYERS
// ============================================================
async function loadPlayers() {
    try {
        const res = await fetch(`${API_BASE}/players`);
        const players = await res.json();
        const tbody = document.getElementById('playersBody');
        if (tbody) {
            tbody.innerHTML = players.map(p => `
                <tr>
                    <td>${p.first_name || ''} ${p.last_name || ''}</td>
                    <td>${p.position || '-'}</td>
                    <td>${p.team_name || '-'}</td>
                    <td>${p.age || '-'}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading players:', error);
    }
}

// ============================================================
// LOAD DONORS
// ============================================================
async function loadDonors() {
    try {
        const res = await fetch(`${API_BASE}/donors`);
        const donors = await res.json();
        const container = document.getElementById('donorsGrid');
        if (container) {
            container.innerHTML = donors.map(d => `
                <div class="donor-card" onclick="viewDonor('${d.donor_name}')">
                    <div class="donor-logo"><i class="fas fa-handshake"></i></div>
                    <div class="donor-name">${d.donor_name}</div>
                    <div class="donor-type">${d.donor_type}</div>
                    <div class="donor-amount">R${parseFloat(d.total_amount || 0).toFixed(2)}</div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading donors:', error);
    }
}

// ============================================================
// VIEW DONOR
// ============================================================
function viewDonor(name) {
    alert(`Viewing donor profile: ${name}`);
}

// ============================================================
// RUN ON PAGE LOAD
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadPlayers();
    loadDonors();
});