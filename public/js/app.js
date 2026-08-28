// Initialize Lucide icons
lucide.createIcons();

// Tab-based navigation for sidebar links
document.querySelectorAll('.nav-item').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        // Remove active class from all sidebar items
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        // Add to clicked
        this.classList.add('active');

        const targetId = this.getAttribute('href').substring(1);
        
        // Hide all sections
        document.querySelectorAll('.research-section').forEach(section => {
            section.classList.remove('active-section');
        });
        
        // Show target section
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            targetElement.classList.add('active-section');
            // Re-render chart if it's the correlation lab to fix canvas sizing issues on display: none
            if (targetId === 'correlation') {
                renderRollingCorrChart();
            }
        }
    });
});

// Set initial active section on load
document.addEventListener('DOMContentLoaded', () => {
    const firstSection = document.querySelector('.research-section');
    if (firstSection) {
        firstSection.classList.add('active-section');
    }
});

// Chart.js Default Configurations
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = "#cbd5e1"; // Light text for dark mode
Chart.defaults.borderColor = "#334155"; // Dark grid lines
Chart.defaults.elements.point.radius = 0; // Hide points on dense time series

const ASSET_COLORS = {
    'NIFTY_50': '#38bdf8', // Neon Sky Blue (Primary)
    'SP_500': '#34d399', // Neon Emerald
    'Gold': '#fbbf24', // Bright Gold
    'Brent_Crude': '#f87171', // Bright Red
    'NASDAQ_100': '#a78bfa', // Neon Purple
    'USD_INR': '#f472b6', // Bright Pink
    'India_VIX': '#94a3b8' // Subtle Grey
};

const FRIENDLY_NAMES = {
    'NIFTY_50': 'NIFTY 50',
    'SP_500': 'S&P 500',
    'NASDAQ_100': 'NASDAQ-100',
    'Brent_Crude': 'Brent Crude',
    'Gold': 'Gold',
    'USD_INR': 'USD/INR',
    'India_VIX': 'India VIX',
    'US_VIX': 'US VIX',
    'NIFTY_IT': 'NIFTY IT',
    'NIFTY_Bank': 'NIFTY Bank',
    'Prev_NIFTY_50': 'Previous NIFTY 50',
    'Prev_India_VIX_Change': 'Previous India VIX'
};

let globalRollingCorrData = null;
let rollingCorrChartInstance = null;

async function fetchData() {
    try {
        const [descStats, corrData, rollCorr, normPerf, advResearch, mlResults] = await Promise.all([
            fetch('/data/stats/descriptive_stats.json').then(r => r.json()),
            fetch('/data/stats/correlation_matrix.json').then(r => r.json()),
            fetch('/data/stats/rolling_correlations.json').then(r => r.json()),
            fetch('/data/stats/normalized_performance.json').then(r => r.json()),
            fetch('/data/stats/advanced_research.json').then(r => r.json()),
            fetch('/data/stats/ml_results.json').then(r => r.json())
        ]);
        
        globalRollingCorrData = rollCorr;

        updateSidebarInfo(corrData.observations);
        renderDescriptiveStats(descStats);
        renderCorrelationMatrix(corrData);
        renderHistoricalChart(normPerf);
        renderRollingCorrChart(); // Uses global data
        renderRegression(advResearch.regression_analysis);
        renderRegimes(advResearch.regime_analysis);
        renderML(mlResults);
        
        setupEventListeners();
        
    } catch (err) {
        console.error("Error loading research data:", err);
        alert("Could not load research data. Please ensure the backend is running and data is generated.");
    }
}

function updateSidebarInfo(obs) {
    document.getElementById('stat-obs').textContent = obs;
    document.getElementById('stat-period').textContent = "Jan 2016 – Aug 2026";
}

function renderDescriptiveStats(data) {
    const daily = data.daily;
    const tbody = document.querySelector('#statsTable tbody');
    tbody.innerHTML = '';
    
    // Define rendering order
    const order = ['NIFTY_50', 'SP_500', 'NASDAQ_100', 'Brent_Crude', 'Gold', 'USD_INR', 'India_VIX', 'US_VIX', 'NIFTY_IT', 'NIFTY_Bank'];
    
    order.forEach(asset => {
        if (!daily[asset]) return;
        const stats = daily[asset];
        
        const annRet = (stats.annualized_return * 100).toFixed(1) + '%';
        const annVol = (stats.annualized_volatility * 100).toFixed(1) + '%';
        const skew = stats.skewness.toFixed(2);
        const kurt = stats.kurtosis.toFixed(2);
        const p5 = (stats.percentiles.p5 * 100).toFixed(2) + '%';
        const p95 = (stats.percentiles.p95 * 100).toFixed(2) + '%';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${FRIENDLY_NAMES[asset] || asset}</strong></td>
            <td class="${stats.annualized_return > 0 ? 'positive' : 'negative'}">${annRet}</td>
            <td>${annVol}</td>
            <td>${skew}</td>
            <td>${kurt}</td>
            <td class="negative">${p5}</td>
            <td class="positive">${p95}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderCorrelationMatrix(data) {
    const table = document.getElementById('corrMatrixTable');
    table.innerHTML = '';
    
    const assets = ['NIFTY_50', 'SP_500', 'NASDAQ_100', 'Brent_Crude', 'Gold', 'USD_INR', 'India_VIX'];
    
    // Header
    let thead = '<thead><tr><th>Asset</th>';
    assets.forEach(a => thead += `<th>${FRIENDLY_NAMES[a]}</th>`);
    thead += '</tr></thead>';
    table.innerHTML += thead;
    
    // Body
    let tbody = '<tbody>';
    assets.forEach(rowAsset => {
        tbody += `<tr><td>${FRIENDLY_NAMES[rowAsset]}</td>`;
        assets.forEach(colAsset => {
            if (rowAsset === colAsset) {
                tbody += `<td class="neutral">1.00</td>`;
            } else {
                const corr = data.correlation[rowAsset][colAsset];
                const pval = data.p_values[rowAsset][colAsset];
                
                let valClass = '';
                if (Math.abs(corr) > 0.5) valClass = corr > 0 ? 'positive' : 'negative';
                else valClass = 'neutral';
                
                let sigMarker = '';
                if (pval < 0.01) sigMarker = '*';
                
                tbody += `<td class="${valClass}" title="p-value: ${pval.toExponential(2)}">${corr.toFixed(2)}${sigMarker}</td>`;
            }
        });
        tbody += `</tr>`;
    });
    tbody += '</tbody>';
    table.innerHTML += tbody;
}

function renderHistoricalChart(data) {
    const ctx = document.getElementById('historicalPerformanceChart').getContext('2d');
    
    // Use NIFTY dates as the common x-axis
    const labels = data['NIFTY_50'].map(d => d.date);
    
    const assetsToPlot = ['NIFTY_50', 'SP_500', 'NASDAQ_100', 'Brent_Crude', 'Gold', 'USD_INR', 'India_VIX'];
    
    const datasets = assetsToPlot.map(asset => ({
        label: FRIENDLY_NAMES[asset] || asset,
        data: data[asset].map(d => d.val),
        borderColor: ASSET_COLORS[asset],
        borderWidth: asset === 'NIFTY_50' ? 2.5 : 1.5, // Emphasize NIFTY
        tension: 0.1,
        fill: false,
        hidden: asset !== 'NIFTY_50' && asset !== 'SP_500' // Hide others by default to prevent clutter
    }));
    
    new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: { title: { display: true, text: 'Normalized (Base 100)' } }
            }
        }
    });
}

function setupEventListeners() {
    const checkboxes = document.querySelectorAll('#corrVariableCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            renderRollingCorrChart();
        });
    });
}

function renderRollingCorrChart() {
    if (!globalRollingCorrData) return;
    const data = globalRollingCorrData;
    const ctx = document.getElementById('rollingCorrChart').getContext('2d');
    
    // Destroy previous instance if it exists
    if (rollingCorrChartInstance) {
        rollingCorrChartInstance.destroy();
    }

    // Determine which datasets are selected
    const selectedAssets = Array.from(document.querySelectorAll('#corrVariableCheckboxes input[type="checkbox"]:checked'))
                                .map(cb => cb.value);

    // If nothing selected, just clear chart
    if (selectedAssets.length === 0) {
        rollingCorrChartInstance = new Chart(ctx, { type: 'line', data: { labels: [], datasets: [] } });
        return;
    }

    // Use SP_500 (or the first selected asset) dates as x-axis
    const firstAsset = selectedAssets[0];
    const labels = data[firstAsset]['60d'].map(d => d.date);
    
    const datasets = selectedAssets.map(asset => ({
        label: `${FRIENDLY_NAMES[asset]} vs NIFTY 50`,
        data: data[asset]['60d'].map(d => d.val),
        borderColor: ASSET_COLORS[asset],
        borderWidth: 2,
        tension: 0.1
    }));
    
    rollingCorrChartInstance = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: -1, max: 1, title: { display: true, text: '60-Day Pearson Correlation' } }
            }
        }
    });
}

function renderRegression(regData) {
    const tbody = document.querySelector('#regressionTable tbody');
    tbody.innerHTML = '';
    
    const vars = regData.variables;
    
    for (const [varName, stats] of Object.entries(vars)) {
        if (varName === 'const') continue;
        
        let sigClass = 'sig-none';
        let sigText = 'Not Sig.';
        if (stats.p_value < 0.01) { sigClass = 'sig-high'; sigText = 'High Sig.'; }
        else if (stats.p_value < 0.05) { sigClass = 'sig-low'; sigText = 'Significant'; }
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${FRIENDLY_NAMES[varName] || varName}</strong></td>
            <td>${stats.coefficient.toFixed(4)}</td>
            <td>${stats.t_stat.toFixed(2)}</td>
            <td>${stats.p_value.toExponential(2)}</td>
            <td><span class="${sigClass}">${sigText}</span></td>
        `;
        tbody.appendChild(tr);
    }
}

function renderRegimes(regimeData) {
    const container = document.getElementById('regimeCardsContainer');
    container.innerHTML = '';
    
    const ordered = ['Low Volatility (Bottom 25%)', 'Normal Volatility (Middle 50%)', 'High Volatility (Top 25%)'];
    const cssClasses = ['low', 'normal', 'high'];
    
    ordered.forEach((name, i) => {
        const stats = regimeData[name];
        
        const ret = (stats.avg_nifty_return_annualized * 100).toFixed(1) + '%';
        const vol = (stats.nifty_volatility_annualized * 100).toFixed(1) + '%';
        const corrSp = stats.correlations.SP_500.toFixed(3);
        
        const card = document.createElement('div');
        card.className = `regime-card ${cssClasses[i]}`;
        card.innerHTML = `
            <h4>${name}</h4>
            <div class="regime-stat">
                <span>Annualized Return</span>
                <span class="${stats.avg_nifty_return_annualized > 0 ? 'positive' : 'negative'}">${ret}</span>
            </div>
            <div class="regime-stat">
                <span>Annualized Volatility</span>
                <span>${vol}</span>
            </div>
            <div class="regime-stat">
                <span>NIFTY / S&P 500 Corr</span>
                <span>${corrSp}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderML(mlData) {
    // 1. Render Performance List
    const list = document.getElementById('mlPerformanceList');
    list.innerHTML = '';
    
    const models = mlData.models;
    for (const [name, metrics] of Object.entries(models)) {
        const acc = (metrics.accuracy * 100).toFixed(1) + '%';
        const auc = metrics.roc_auc.toFixed(3);
        
        const li = document.createElement('li');
        li.innerHTML = `
            <span class="ml-model-name">${name.replace('_', ' ')}</span>
            <div class="ml-metrics">
                <div>
                    <div class="ml-metric-label">Accuracy</div>
                    <div class="ml-metric-val">${acc}</div>
                </div>
                <div>
                    <div class="ml-metric-label">AUC</div>
                    <div class="ml-metric-val">${auc}</div>
                </div>
            </div>
        `;
        list.appendChild(li);
    }
    
    // 2. Render Feature Importance Chart
    const ctx = document.getElementById('featureImportanceChart').getContext('2d');
    
    const importances = mlData.feature_importance;
    // Sort descending
    const sorted = Object.entries(importances).sort((a, b) => b[1] - a[1]);
    
    const labels = sorted.map(i => FRIENDLY_NAMES[i[0]] || i[0]);
    const data = sorted.map(i => i[1] * 100);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Importance (%)',
                data: data,
                backgroundColor: ASSET_COLORS['SP_500'],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: { title: { display: true, text: 'Importance %' } }
            }
        }
    });
}

// Boot
document.addEventListener('DOMContentLoaded', fetchData);
