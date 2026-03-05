"""
Dashboard HTML template — generates a static shell and JSONP data files.
"""
import json
import os
from .models import Transaction


def generate_data_js(transactions: list[Transaction], year: str, output_dir: str) -> None:
    """Generate a JSONP data file for a specific year."""
    js_data = [t.to_js_dict() for t in transactions]
    content = f"window.spendingData_{year} = {json.dumps(js_data)};"
    
    path = os.path.join(output_dir, f'data_{year}.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Generated data_{year}.js")


def generate_manifest_js(years: list[str], output_dir: str) -> None:
    """Generate the manifest file listing available years."""
    content = f"window.availableYears = {json.dumps(sorted(years))};"
    path = os.path.join(output_dir, 'manifest.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Generated manifest.js")


def generate_dashboard_shell(output_dir: str, title: str = "Spending Dashboard") -> None:
    """Generate the static HTML shell that loads data dynamically."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background-color: #f4f4f9; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .year-tabs {{ display: flex; background: #e9ecef; border-radius: 8px; padding: 4px; gap: 4px; }}
        .year-tab {{ padding: 8px 16px; cursor: pointer; border-radius: 6px; font-weight: 600; color: #555; transition: all 0.2s; user-select: none; }}
        .year-tab:hover {{ background: #dee2e6; color: #333; }}
        .year-tab.active {{ background: #007bff; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        
        .container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .full-width {{ grid-column: 1 / -1; }}
        h1, h2 {{ color: #333; margin: 0; }}
        #table-container {{ position: relative; }}
        #vt-scroll table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        #vt-scroll table td:nth-child(1) {{ width: 40px; text-align: center; }}
        #vt-scroll table td:nth-child(2) {{ width: 100px; }}
        #vt-scroll table td:nth-child(4) {{ width: 160px; }}
        #vt-scroll table td:nth-child(5) {{ width: 100px; }}
        #vt-scroll table td:nth-child(6) {{ width: 100px; }}
        #vt-scroll table td:nth-child(7) {{ width: 100px; }}
        #vt-scroll table td:nth-child(8) {{ width: 100px; }}
        #vt-scroll table tr:hover {{ background-color: #e8f0fe; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        th {{ background-color: #f8f8f8; position: sticky; top: 0; cursor: pointer; user-select: none; z-index: 1; }}
        th:hover {{ background-color: #e2e2e2; }}
        tbody tr:hover {{ background-color: #e8f0fe; }}
        th::after {{ content: ' \\2195'; color: #ccc; padding-left: 5px; }}
        th.asc::after {{ content: ' \\2191'; color: black; }}
        th.desc::after {{ content: ' \\2193'; color: black; }}
        th .col-resizer {{ position: absolute; right: 0; top: 0; width: 5px; height: 100%; cursor: col-resize; background: transparent; }}
        th .col-resizer:hover, th .col-resizer.dragging {{ background: #007bff; }}
        
        .summary-box {{ display: flex; justify-content: space-around; margin-bottom: 20px; }}
        .metric {{ text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        
        .controls {{ margin-bottom: 20px; display: flex; align-items: center; flex-wrap: wrap; gap: 10px; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        button {{ padding: 8px 16px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }}
        button:hover {{ background: #0056b3; }}
        
        .cb-dropdown {{ position: relative; display: inline-block; }}
        .cb-dropdown-toggle {{ padding: 8px 28px 8px 12px; border: 1px solid #ccc; border-radius: 4px; background: white; font-size: 14px; min-width: 130px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; position: relative; }}
        .cb-dropdown-toggle::after {{ content: '\\25BC'; position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-size: 10px; color: #666; }}
        .cb-dropdown-toggle:hover {{ border-color: #007bff; }}
        .cb-dropdown-menu {{ display: none; position: absolute; top: 100%; left: 0; background: white; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; max-height: 250px; overflow-y: auto; overflow-x: hidden; min-width: 260px; padding: 4px 0; }}
        .cb-dropdown.open .cb-dropdown-menu {{ display: block; }}
        .cb-dropdown-menu label {{ display: flex; align-items: center; padding: 6px 12px; cursor: pointer; white-space: nowrap; font-size: 13px; }}
        .cb-dropdown-menu label:hover {{ background: #f0f0f0; }}
        .cb-dropdown-menu input[type=checkbox] {{ margin-right: 8px; }}
        
        .search-box {{ margin-bottom: 10px; }}
        .search-box input {{ width: 100%; padding: 10px 14px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; box-sizing: border-box; }}
        .search-box input:focus {{ outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.2); }}
        
        .cat-select {{ width: 100%; border: none; background: transparent; font-size: 13px; cursor: pointer; padding: 2px; }}
        .cat-select:focus {{ outline: 1px solid #007bff; border-radius: 2px; }}

        #loading-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.8); justify-content: center; align-items: center; z-index: 2000; font-size: 20px; color: #555; display: none; }}

        /* Bulk edit bar */
        #bulk-bar {{ display: none; align-items: center; gap: 12px; padding: 10px 14px; background: #e8f0fe; border-radius: 8px; margin-bottom: 10px; flex-wrap: wrap; }}
        #bulk-bar.active {{ display: flex; }}
        #bulk-bar .bulk-count {{ font-weight: 600; color: #1a73e8; white-space: nowrap; }}
        #bulk-bar select, #bulk-bar button {{ padding: 6px 12px; border-radius: 4px; font-size: 13px; border: 1px solid #ccc; }}
        #bulk-bar button {{ background: #1a73e8; color: white; border: none; cursor: pointer; }}
        #bulk-bar button:hover {{ background: #1558b0; }}
        #bulk-bar button.btn-clear {{ background: #6c757d; }}
        #bulk-bar button.btn-clear:hover {{ background: #545b62; }}
        #vt-scroll table tr.selected {{ background-color: #d2e3fc; }}
        #vt-scroll table tr.selected:hover {{ background-color: #c0d6f7; }}
        th.col-sel {{ width: 40px !important; text-align: center; }}
        td.col-sel {{ text-align: center; }}

        /* Server connection status */
        #server-status {{ position: sticky; top: 0; left: 0; width: 100%; padding: 10px 20px; font-size: 14px; font-weight: 600; z-index: 3000; display: none; box-sizing: border-box; text-align: center; }}
        #server-status.disconnected {{ display: block; background: #dc3545; color: white; }}
        #server-status.saving {{ display: block; background: #ffc107; color: #333; }}
    </style>
</head>
<body>
    <div id="loading-overlay">Loading data...</div>
    <div id="server-status"></div>

    <div class="header">
        <h1>{title}</h1>
        <div style="display: flex; gap: 16px; align-items: center;">
            <div id="view-tabs" class="year-tabs">
                <div class="year-tab active" id="view-single" onclick="switchView('single')">Single Year</div>
                <div class="year-tab" id="view-compare" onclick="switchView('compare')">Compare Years</div>
            </div>
            <div id="year-tabs" class="year-tabs">
                <!-- Year tabs injected here -->
            </div>
        </div>
    </div>

    <div id="single-view">
    <div class="controls">
        <button onclick="resetFilters()">Reset Filters</button>
        <button id="btn-export" onclick="exportOverrides()" style="background:#28a745; display:none;">Export Overrides</button>
        <div class="cb-dropdown" id="dd-Month">
            <div class="cb-dropdown-toggle" onclick="toggleDropdown('Month')">All Months</div>
            <div class="cb-dropdown-menu" id="dd-menu-Month"></div>
        </div>
        <div class="cb-dropdown" id="dd-Category">
            <div class="cb-dropdown-toggle" onclick="toggleDropdown('Category')">All Categories</div>
            <div class="cb-dropdown-menu" id="dd-menu-Category"></div>
        </div>
        <div class="cb-dropdown" id="dd-Source">
            <div class="cb-dropdown-toggle" onclick="toggleDropdown('Source')">All Sources</div>
            <div class="cb-dropdown-menu" id="dd-menu-Source"></div>
        </div>
        <div class="cb-dropdown" id="dd-Exclude">
            <div class="cb-dropdown-toggle" onclick="toggleDropdown('Exclude')">Exclude: 2</div>
            <div class="cb-dropdown-menu" id="dd-menu-Exclude">
                <label><input type="checkbox" value="Reimbursable" onchange="onExcludeCheck()" checked> Reimbursable</label>
                <label><input type="checkbox" value="NotSpending" onchange="onExcludeCheck()" checked> Not Spending</label>
            </div>
        </div>
    </div>
    
    <div class="summary-box card full-width">
        <div class="metric">
            <div>Total Spending</div>
            <div id="total-spending" class="metric-value">$0</div>
        </div>
        <div class="metric">
            <div>Avg. Monthly</div>
            <div id="avg-monthly" class="metric-value">$0</div>
        </div>
        <div class="metric">
            <div>Top Category</div>
            <div id="top-category" class="metric-value">-</div>
        </div>
    </div>

    <div class="container">
        <div class="card full-width">
            <h2>Monthly Trend</h2>
            <div id="monthly-chart"></div>
        </div>
        
        <div class="card">
            <h2>Spending by Category</h2>
            <div id="category-chart"></div>
        </div>
        
        <div class="card">
            <h2>Spending by Source</h2>
            <div id="source-chart"></div>
        </div>

        <div class="card full-width">
            <div style="display:flex; justify-content:space-between; align-items:baseline;">
                <h2>Detailed Transactions</h2>
                <span id="table-stats" style="color:#666; font-size:13px;"></span>
            </div>
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Search by description, category, or source..." oninput="onSearchInput()">
            </div>
            <div id="bulk-bar">
                <span class="bulk-count"><span id="bulk-count-num">0</span> selected</span>
                <select id="bulk-cat"><option value="">Set Category...</option></select>
                <button onclick="bulkSetCategory()">Apply Category</button>
                <button onclick="bulkSetReimbursable(true)">Mark Reimb.</button>
                <button onclick="bulkSetReimbursable(false)">Unmark Reimb.</button>
                <button onclick="bulkSetNotSpending(true)">Mark Not Spending</button>
                <button onclick="bulkSetNotSpending(false)">Unmark Not Spending</button>
                <button class="btn-clear" onclick="clearSelection()">Clear Selection</button>
            </div>
            <div id="table-container">
                <table id="txn-table">
                    <thead>
                        <tr>
                            <th class="col-sel"><input type="checkbox" id="select-all" onchange="toggleSelectAll(this.checked)"></th>
                            <th onclick="sortTable('Date')" id="th-Date" style="width:100px;">Date<div class="col-resizer" data-col="0"></div></th>
                            <th onclick="sortTable('Description')" id="th-Description">Description<div class="col-resizer" data-col="1"></div></th>
                            <th onclick="sortTable('Category')" id="th-Category" style="width:160px;">Category<div class="col-resizer" data-col="2"></div></th>
                            <th onclick="sortTable('Source')" id="th-Source" style="width:100px;">Source<div class="col-resizer" data-col="3"></div></th>
                            <th onclick="sortTable('Amount')" id="th-Amount" style="width:100px;">Amount<div class="col-resizer" data-col="4"></div></th>
                            <th onclick="sortTable('IsReimbursable')" id="th-IsReimbursable" style="width:100px;">Reimb.</th>
                            <th onclick="sortTable('IsNotSpending')" id="th-IsNotSpending" style="width:100px;">Not Spending</th>
                        </tr>
                    </thead>
                </table>
                <div id="vt-scroll" style="overflow-y:auto; max-height:750px;" onscroll="renderVisibleRows()">
                    <div id="vt-spacer" style="position:relative;"></div>
                </div>
            </div>
        </div>
    </div>
    </div>

    <div id="compare-view" style="display:none;">
        <div class="controls">
            <div class="cb-dropdown" id="dd-CmpYears">
                <div class="cb-dropdown-toggle" onclick="toggleDropdown('CmpYears')">All Years</div>
                <div class="cb-dropdown-menu" id="dd-menu-CmpYears"></div>
            </div>
            <div class="cb-dropdown" id="dd-CmpCats">
                <div class="cb-dropdown-toggle" onclick="toggleDropdown('CmpCats')">All Categories</div>
                <div class="cb-dropdown-menu" id="dd-menu-CmpCats"></div>
            </div>
            <div class="cb-dropdown" id="dd-CmpExclude">
                <div class="cb-dropdown-toggle" onclick="toggleDropdown('CmpExclude')">Exclude: 2</div>
                <div class="cb-dropdown-menu" id="dd-menu-CmpExclude">
                    <label><input type="checkbox" value="Reimbursable" onchange="renderCompareChart()" checked> Reimbursable</label>
                    <label><input type="checkbox" value="NotSpending" onchange="renderCompareChart()" checked> Not Spending</label>
                </div>
            </div>
        </div>
        <div class="card full-width" style="max-width:100%;">
            <h2>Spending by Category Across Years</h2>
            <div id="compare-chart" style="min-height:500px;"></div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="manifest.js"></script>
    <script>
        // --- State ---
        let currentYear = '';
        let rawData = [];
        let currentData = [];
        
        // Filter state
        let activeFilters = {{}};
        let searchText = '';
        let excludeReimbursable = true;
        let sortStack = [{{ field: 'Date', direction: 'desc' }}];

        // Per-year state storage
        const yearState = {{}};
        
        let excludeNotSpending = true;

        // Reimbursable storage
        const STORAGE_KEY = 'spending_dashboard_reimbursable_ids_v1';
        let manualReimbursable = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');

        // NotSpending storage
        const NS_STORAGE_KEY = 'spending_dashboard_not_spending_ids_v1';
        let manualNotSpending = JSON.parse(localStorage.getItem(NS_STORAGE_KEY) || '{{}}');

        // Category storage (global across years)
        const CAT_STORAGE_KEY = 'spending_dashboard_custom_categories_v1';
        let manualCategories = JSON.parse(localStorage.getItem(CAT_STORAGE_KEY) || '{{}}');

        const isLocalServer = location.protocol === 'http:' || location.protocol === 'https:';

        // --- Initialization ---
        document.addEventListener('DOMContentLoaded', async () => {{
            if (isLocalServer) {{
                try {{
                    const resp = await fetch('/api/overrides');
                    if (resp.ok) {{
                        const data = await resp.json();
                        manualReimbursable = data.reimbursable || {{}};
                        manualNotSpending = data.notSpending || {{}};
                        manualCategories = data.categories || {{}};
                        saveLocalStorage();
                        // Flush any queued offline changes
                        if (pendingChanges.length > 0) flushPendingChanges();
                    }}
                }} catch (e) {{
                    // Fallback to localStorage (already loaded above)
                }}
            }}
            // Show export button only in file:// mode (no server)
            if (!isLocalServer) document.getElementById('btn-export').style.display = '';
            // Heartbeat: keep server alive and detect disconnection
            if (isLocalServer) {{
                const hb = () => fetch('/api/heartbeat').then(r => {{
                    if (r.ok && !serverConnected) {{
                        serverConnected = true;
                        if (pendingChanges.length > 0) {{
                            flushPendingChanges();
                        }} else {{
                            showServerStatus('', '');
                        }}
                    }} else if (r.ok) {{
                        serverConnected = true;
                    }}
                }}).catch(() => {{
                    serverConnected = false;
                    showServerStatus('disconnected', 'Server disconnected — changes saved to browser only.');
                }});
                hb(); // check immediately on load
                setInterval(hb, 10000);
                document.addEventListener('visibilitychange', () => {{ if (!document.hidden) hb(); }});
                window.addEventListener('focus', hb);
            }}
            initYearTabs();
        }});

        function initYearTabs() {{
            const container = document.getElementById('year-tabs');
            const years = window.availableYears || [];
            
            if (years.length === 0) {{
                container.innerHTML = '<div>No data available</div>';
                return;
            }}

            // Sort descending to show latest year first
            years.sort().reverse();
            
            years.forEach(year => {{
                const tab = document.createElement('div');
                tab.className = 'year-tab';
                tab.innerText = year;
                tab.onclick = () => loadYear(year);
                tab.id = 'tab-' + year;
                container.appendChild(tab);
            }});

            // Load latest year by default
            const savedYear = localStorage.getItem('spending_dashboard_last_year');
            if (savedYear && years.includes(savedYear)) {{
                loadYear(savedYear);
            }} else {{
                loadYear(years[0]);
            }}
        }}

        function saveYearState() {{
            if (!currentYear) return;
            yearState[currentYear] = {{
                activeFilters: JSON.parse(JSON.stringify(activeFilters)),
                searchText: searchText,
                excludeReimbursable: excludeReimbursable,
                excludeNotSpending: excludeNotSpending,
                sortStack: JSON.parse(JSON.stringify(sortStack)),
            }};
        }}

        function restoreYearState(year) {{
            const saved = yearState[year];
            if (saved) {{
                activeFilters = saved.activeFilters;
                searchText = saved.searchText;
                excludeReimbursable = saved.excludeReimbursable;
                excludeNotSpending = saved.excludeNotSpending !== undefined ? saved.excludeNotSpending : true;
                sortStack = saved.sortStack;
            }} else {{
                activeFilters = {{}};
                searchText = '';
                excludeReimbursable = true;
                excludeNotSpending = true;
                sortStack = [{{ field: 'Date', direction: 'desc' }}];
            }}
            document.getElementById('search-input').value = searchText;
            syncExcludeDropdown();
            updateSortIcons();
        }}

        function loadYear(year) {{
            if (currentYear === year) return;

            // Save current year's state before switching
            saveYearState();

            // Show loading
            document.getElementById('loading-overlay').style.display = 'flex';

            // Update UI tabs (scope to year-tabs only, not view-tabs)
            document.querySelectorAll('#year-tabs .year-tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + year).classList.add('active');

            currentYear = year;
            chartsInitialized = false;
            localStorage.setItem('spending_dashboard_last_year', year);

            // Check if data already loaded
            const varName = 'spendingData_' + year;
            if (window[varName]) {{
                setRawData(window[varName]);
                return;
            }}

            // Inject script
            const script = document.createElement('script');
            script.src = 'data_' + year + '.js';
            script.onload = () => {{
                if (window[varName]) {{
                    setRawData(window[varName]);
                }} else {{
                    alert('Error loading data for ' + year);
                    document.getElementById('loading-overlay').style.display = 'none';
                }}
            }};
            script.onerror = () => {{
                alert('Failed to load data file: data_' + year + '.js');
                document.getElementById('loading-overlay').style.display = 'none';
            }};
            document.body.appendChild(script);
        }}

        function setRawData(data) {{
            rawData = data;

            // Apply manual overrides from localStorage
            rawData.forEach(item => {{
                if (manualReimbursable.hasOwnProperty(item.TxnID)) {{
                    item.IsReimbursable = manualReimbursable[item.TxnID];
                }}
                if (manualNotSpending.hasOwnProperty(item.TxnID)) {{
                    item.IsNotSpending = manualNotSpending[item.TxnID];
                }}
                if (manualCategories.hasOwnProperty(item.TxnID)) {{
                    item.Category = manualCategories[item.TxnID];
                }}
            }});

            // Restore per-year filter state
            restoreYearState(currentYear);
            populateDropdowns();
            syncAllDropdowns();
            applyAllFilters();

            document.getElementById('loading-overlay').style.display = 'none';
        }}

        function updateDashboard(data) {{
            const total = data.reduce((sum, item) => sum + item.Amount, 0);
            const months = [...new Set(data.map(item => item.Month))].length;
            const avg = months ? total / months : 0;

            const cats = {{}};
            data.forEach(item => {{ cats[item.Category] = (cats[item.Category] || 0) + item.Amount; }});
            const topCat = Object.keys(cats).sort((a,b) => cats[b] - cats[a])[0] || '-';

            document.getElementById('total-spending').innerText = fmtAmt(total);
            document.getElementById('avg-monthly').innerText = fmtAmt(avg);
            document.getElementById('top-category').innerText = topCat;

            // Table stats
            const count = data.length;
            const avgTxn = count ? total / count : 0;
            document.getElementById('table-stats').innerText =
                count + ' rows | Sum: ' + fmtAmt(total) + ' | Avg: ' + fmtAmt(avgTxn);

            sortAndRenderTable(data);
            scheduleChartUpdate(data);
        }}

        // --- Charts (deferred to avoid blocking table render) ---

        let chartsInitialized = false;
        let chartRAF = 0;
        function scheduleChartUpdate(data) {{
            if (chartRAF) cancelAnimationFrame(chartRAF);
            chartRAF = requestAnimationFrame(() => renderCharts(data));
        }}

        function renderCharts(data) {{
            const monthMap = {{}};
            const catMap = {{}};
            const srcMap = {{}};
            for (let i = 0; i < data.length; i++) {{
                const d = data[i];
                monthMap[d.Month] = (monthMap[d.Month] || 0) + d.Amount;
                catMap[d.Category] = (catMap[d.Category] || 0) + d.Amount;
                srcMap[d.Source] = (srcMap[d.Source] || 0) + d.Amount;
            }}

            const sortedMonths = Object.keys(monthMap).sort();
            const trace1 = {{
                x: sortedMonths,
                y: sortedMonths.map(m => Math.round(monthMap[m])),
                type: 'bar',
                marker: {{color: '#3498db'}},
                hovertemplate: '%{{x}}: $%{{y:,.0f}}<extra></extra>'
            }};

            const labels = Object.keys(catMap).sort((a,b) => catMap[b] - catMap[a]);
            const trace2 = {{ labels: labels, values: labels.map(l => catMap[l]), type: 'pie', hole: 0.4 }};
            const trace3 = {{ labels: Object.keys(srcMap), values: Object.values(srcMap), type: 'pie' }};

            const barLayout = {{margin: {{t: 20}}, xaxis: {{type: 'category'}}, yaxis: {{tickprefix: '$', tickformat: ',.0f'}}}};
            const pieLayout = {{margin: {{t: 20, b: 20, l: 20, r: 20}}}};

            if (!chartsInitialized) {{
                Plotly.newPlot('monthly-chart', [trace1], barLayout, {{responsive: true}});
                document.getElementById('monthly-chart').on('plotly_click', data => filterData('Month', data.points[0].x));
                Plotly.newPlot('category-chart', [trace2], pieLayout, {{responsive: true}});
                document.getElementById('category-chart').on('plotly_click', data => filterData('Category', data.points[0].label));
                Plotly.newPlot('source-chart', [trace3], pieLayout, {{responsive: true}});
                document.getElementById('source-chart').on('plotly_click', data => filterData('Source', data.points[0].label));
                chartsInitialized = true;
            }} else {{
                Plotly.react('monthly-chart', [trace1], barLayout);
                Plotly.react('category-chart', [trace2], pieLayout);
                Plotly.react('source-chart', [trace3], pieLayout);
            }}
        }}

        function fmtAmt(n) {{
            const s = Math.abs(n).toFixed(2);
            const parts = s.split('.');
            parts[0] = parts[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
            return (n < 0 ? '-' : '') + '$' + parts.join('.');
        }}

        // --- Selection state ---
        const selectedIds = new Set();

        function toggleSelectAll(checked) {{
            selectedIds.clear();
            if (checked) {{
                vtSorted.forEach(t => selectedIds.add(t.TxnID));
            }}
            updateBulkBar();
            renderVisibleRows(true);
        }}

        function toggleRowSelect(id, checked) {{
            if (checked) selectedIds.add(id);
            else selectedIds.delete(id);
            document.getElementById('select-all').checked = selectedIds.size === vtSorted.length && vtSorted.length > 0;
            updateBulkBar();
        }}

        function clearSelection() {{
            selectedIds.clear();
            document.getElementById('select-all').checked = false;
            updateBulkBar();
            renderVisibleRows(true);
        }}

        function updateBulkBar() {{
            const bar = document.getElementById('bulk-bar');
            const n = selectedIds.size;
            document.getElementById('bulk-count-num').textContent = n;
            if (n > 0) bar.classList.add('active');
            else bar.classList.remove('active');
            // Populate category dropdown
            const sel = document.getElementById('bulk-cat');
            const allCats = getAllCategories();
            sel.innerHTML = '<option value="">Set Category...</option>' + allCats.map(c => `<option value="${{c}}">${{c}}</option>`).join('') + '<option value="__new__">-- New --</option>';
        }}

        function bulkSetCategory() {{
            const sel = document.getElementById('bulk-cat');
            let newCat = sel.value;
            if (!newCat) return;
            if (newCat === '__new__') {{
                const name = prompt('Enter new category name:');
                if (name && name.trim()) newCat = name.trim();
                else {{ sel.value = ''; return; }}
            }}
            const changes = [];
            selectedIds.forEach(id => {{
                manualCategories[id] = newCat;
                const item = rawData.find(d => d.TxnID === id);
                if (item) item.Category = newCat;
                changes.push({{ section: 'categories', id, value: newCat }});
            }});
            patchOverrides(changes);
            clearSelection();
            populateDropdowns();
            syncAllDropdowns();
            applyAllFilters();
        }}

        function bulkSetReimbursable(val) {{
            const changes = [];
            selectedIds.forEach(id => {{
                manualReimbursable[id] = val;
                const item = rawData.find(d => d.TxnID === id);
                if (item) item.IsReimbursable = val;
                changes.push({{ section: 'reimbursable', id, value: val }});
            }});
            patchOverrides(changes);
            clearSelection();
            applyAllFilters();
        }}

        function bulkSetNotSpending(val) {{
            const changes = [];
            selectedIds.forEach(id => {{
                manualNotSpending[id] = val;
                const item = rawData.find(d => d.TxnID === id);
                if (item) item.IsNotSpending = val;
                changes.push({{ section: 'notSpending', id, value: val }});
            }});
            patchOverrides(changes);
            clearSelection();
            applyAllFilters();
        }}

        // --- Virtual-scroll table ---
        const ROW_HEIGHT = 41;
        const BUFFER = 5;
        let vtSorted = [];    // sorted array backing the table
        let vtDirty = true;   // true = needs re-sort
        let vtCatCache = '';  // cached category <option> HTML

        function sortAndRenderTable(data) {{
            vtSorted = [...data].sort((a,b) => {{
                for (const criteria of sortStack) {{
                    const f = criteria.field;
                    const dir = criteria.direction === 'asc' ? 1 : -1;
                    const valA = a[f], valB = b[f];
                    let r = 0;
                    if (f === 'Amount') r = (valA - valB) * dir;
                    else if (f === 'Date') r = (valA < valB ? -1 : valA > valB ? 1 : 0) * dir;
                    else if (typeof valA === 'boolean') r = (valA === valB ? 0 : valA ? -1 : 1) * dir;
                    else r = valA.localeCompare(valB) * dir;
                    if (r !== 0) return r;
                }}
                return 0;
            }});
            // Rebuild category option cache
            const allCats = getAllCategories();
            vtCatCache = allCats.map(c => `<option value="${{c}}">${{c}}</option>`).join('') + `<option value="__new__">-- New --</option>`;
            setupVirtualScroll();
        }}

        let lastFirst = -1, lastLast = -1;
        function setupVirtualScroll() {{
            const scroller = document.getElementById('vt-scroll');
            const spacer = document.getElementById('vt-spacer');
            spacer.style.height = (vtSorted.length * ROW_HEIGHT) + 'px';
            spacer.innerHTML = '';
            scroller.scrollTop = 0;
            lastFirst = -1; lastLast = -1;
            renderVisibleRows();
        }}

        function renderVisibleRows(force) {{
            const scroller = document.getElementById('vt-scroll');
            const spacer = document.getElementById('vt-spacer');
            const scrollTop = scroller.scrollTop;
            const viewH = scroller.clientHeight;
            const totalRows = vtSorted.length;

            let first = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER);
            let last = Math.min(totalRows - 1, Math.ceil((scrollTop + viewH) / ROW_HEIGHT) + BUFFER);

            if (!force && first === lastFirst && last === lastLast) return;
            lastFirst = first; lastLast = last;

            const topOffset = first * ROW_HEIGHT;
            const rows = new Array(last - first + 1);
            for (let i = first; i <= last; i++) {{
                const txn = vtSorted[i];
                const sel = selectedIds.has(txn.TxnID);
                const opts = vtCatCache.replace(`value="${{txn.Category}}"`, `value="${{txn.Category}}" selected`);
                rows[i - first] = `<tr class="${{sel?'selected':''}}"><td class="col-sel"><input type="checkbox"${{sel?' checked':''}} onchange="toggleRowSelect('${{txn.TxnID}}',this.checked)"></td><td>${{txn.Date}}</td><td>${{txn.Description}}</td><td><select class="cat-select" onchange="changeTxnCategory('${{txn.TxnID}}',this)">${{opts}}</select></td><td>${{txn.Source}}</td><td>${{fmtAmt(txn.Amount)}}</td><td style="text-align:center"><input type="checkbox"${{txn.IsReimbursable?' checked':''}} onchange="toggleTxnReimbursable('${{txn.TxnID}}',this.checked)"></td><td style="text-align:center"><input type="checkbox"${{txn.IsNotSpending?' checked':''}} onchange="toggleTxnNotSpending('${{txn.TxnID}}',this.checked)"></td></tr>`;
            }}
            // Sync column widths from header table
            const ths = document.querySelectorAll('#txn-table thead th');
            const colgroup = [...ths].map(th => `<col style="width:${{th.offsetWidth}}px">`).join('');
            spacer.innerHTML = `<table style="width:100%; border-collapse:collapse; table-layout:fixed; position:absolute; top:${{topOffset}}px;"><colgroup>${{colgroup}}</colgroup><tbody>${{rows.join('')}}</tbody></table>`;
        }}

        function toggleTxnReimbursable(id, isChecked) {{
            manualReimbursable[id] = isChecked;
            patchOverride('reimbursable', id, isChecked);
            const item = rawData.find(d => d.TxnID === id);
            if (item) item.IsReimbursable = isChecked;
            applyAllFilters();
        }}

        function onExcludeCheck() {{
            const menu = document.getElementById('dd-menu-Exclude');
            const checked = [...menu.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);
            excludeReimbursable = checked.includes('Reimbursable');
            excludeNotSpending = checked.includes('NotSpending');
            updateExcludeLabel();
            applyAllFilters();
        }}

        function updateExcludeLabel() {{
            const menu = document.getElementById('dd-menu-Exclude');
            const checked = [...menu.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);
            const toggle = document.querySelector('#dd-Exclude .cb-dropdown-toggle');
            if (checked.length === 0) {{
                toggle.textContent = 'Exclude: None';
            }} else if (checked.length === 2) {{
                toggle.textContent = 'Exclude: 2';
            }} else {{
                toggle.textContent = 'Excl. ' + checked[0];
            }}
        }}

        function syncExcludeDropdown() {{
            const menu = document.getElementById('dd-menu-Exclude');
            menu.querySelectorAll('input[type=checkbox]').forEach(cb => {{
                if (cb.value === 'Reimbursable') cb.checked = excludeReimbursable;
                if (cb.value === 'NotSpending') cb.checked = excludeNotSpending;
            }});
            updateExcludeLabel();
        }}

        function toggleTxnNotSpending(id, isChecked) {{
            manualNotSpending[id] = isChecked;
            patchOverride('notSpending', id, isChecked);
            const item = rawData.find(d => d.TxnID === id);
            if (item) item.IsNotSpending = isChecked;
            applyAllFilters();
        }}

        function getAllCategories() {{
            // Union of categories from current rawData + all custom categories from localStorage
            const cats = new Set();
            rawData.forEach(d => cats.add(d.Category));
            Object.values(manualCategories).forEach(c => cats.add(c));
            return [...cats].sort();
        }}

        function changeTxnCategory(txnId, selectEl) {{
            let newCat = selectEl.value;
            if (newCat === '__new__') {{
                const name = prompt('Enter new category name:');
                if (name && name.trim()) {{
                    newCat = name.trim();
                }} else {{
                    // Revert selection
                    const item = rawData.find(d => d.TxnID === txnId);
                    if (item) selectEl.value = item.Category;
                    return;
                }}
            }}
            manualCategories[txnId] = newCat;
            patchOverride('categories', txnId, newCat);
            const item = rawData.find(d => d.TxnID === txnId);
            if (item) item.Category = newCat;
            setTimeout(() => {{
                populateDropdowns();
                syncAllDropdowns();
                applyAllFilters();
            }}, 0);
        }}

        function applyAllFilters() {{
            selectedIds.clear();
            document.getElementById('select-all').checked = false;
            updateBulkBar();
            currentData = rawData.filter(item => {{
                if (excludeReimbursable && item.IsReimbursable) return false;
                if (excludeNotSpending && item.IsNotSpending) return false;
                for (const [key, vals] of Object.entries(activeFilters)) {{
                    if (Array.isArray(vals)) {{
                        if (vals.length > 0 && !vals.includes(item[key])) return false;
                    }} else {{
                        if (item[key] !== vals) return false;
                    }}
                }}
                if (searchText) {{
                    const q = searchText.toLowerCase();
                    const inDesc = item.Description.toLowerCase().includes(q);
                    const inCat = item.Category.toLowerCase().includes(q);
                    const inSrc = item.Source.toLowerCase().includes(q);
                    if (!inDesc && !inCat && !inSrc) return false;
                }}
                return true;
            }});
            
            updateDashboard(currentData);
        }}

        function filterData(field, value) {{
            activeFilters[field] = [value];
            syncDropdown(field);
            applyAllFilters();
        }}
        
        function resetFilters(ignoreDataReload) {{
            activeFilters = {{}};
            searchText = '';
            excludeReimbursable = true;
            excludeNotSpending = true;
            document.getElementById('search-input').value = '';
            document.querySelectorAll('.cb-dropdown-menu input[type=checkbox]').forEach(cb => cb.checked = false);
            syncExcludeDropdown();

            // Re-populate dropdowns based on CURRENT rawData
            populateDropdowns();

            applyAllFilters();
        }}

        let searchTimer = 0;
        function onSearchInput() {{
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {{
                searchText = document.getElementById('search-input').value.trim();
                applyAllFilters();
            }}, 150);
        }}
        
        // --- Dropdowns & UI ---
        
        function toggleDropdown(field) {{
            const dd = document.getElementById('dd-' + field);
            const wasOpen = dd.classList.contains('open');
            document.querySelectorAll('.cb-dropdown').forEach(d => d.classList.remove('open'));
            if (!wasOpen) dd.classList.add('open');
        }}

        document.addEventListener('click', function(e) {{
            if (!e.target.closest('.cb-dropdown')) {{
                document.querySelectorAll('.cb-dropdown').forEach(d => d.classList.remove('open'));
            }}
        }});

        function onDropdownCheck(field) {{
            const menu = document.getElementById('dd-menu-' + field);
            const checked = [...menu.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);
            if (checked.length > 0) activeFilters[field] = checked;
            else delete activeFilters[field];
            updateDropdownLabel(field);
            applyAllFilters();
        }}

        function updateDropdownLabel(field) {{
            const menu = document.getElementById('dd-menu-' + field);
            const allBoxes = menu.querySelectorAll('input[type=checkbox]');
            const checked = [...allBoxes].filter(cb => cb.checked);
            const toggle = document.querySelector('#dd-' + field + ' .cb-dropdown-toggle');
            const labels = {{ 'Month': 'Months', 'Category': 'Categories', 'Source': 'Sources' }};

            if (checked.length === 0 || checked.length === allBoxes.length) {{
                toggle.textContent = 'All ' + labels[field];
            }} else if (checked.length <= 2) {{
                toggle.textContent = checked.map(cb => cb.value).join(', ');
            }} else {{
                toggle.textContent = checked.length + ' ' + labels[field];
            }}
        }}

        function syncDropdown(field) {{
            const menu = document.getElementById('dd-menu-' + field);
            const vals = activeFilters[field] || [];
            const valSet = new Set(Array.isArray(vals) ? vals : [vals]);
            menu.querySelectorAll('input[type=checkbox]').forEach(cb => {{
                cb.checked = valSet.has(cb.value);
            }});
            updateDropdownLabel(field);
        }}

        function syncAllDropdowns() {{
            ['Month', 'Category', 'Source'].forEach(f => syncDropdown(f));
        }}

        function populateDropdowns() {{
            const months = [...new Set(rawData.map(d => d.Month))].sort();
            const cats = getAllCategories();
            const srcs = [...new Set(rawData.map(d => d.Source))].sort();

            const populate = (field, items) => {{
                const menu = document.getElementById('dd-menu-' + field);
                menu.innerHTML = ''; // Clear existing
                items.forEach(v => {{
                    const lbl = document.createElement('label');
                    lbl.innerHTML = `<input type="checkbox" value="${{v}}" onchange="onDropdownCheck('${{field}}')"> ${{v}}`;
                    menu.appendChild(lbl);
                }});
                updateDropdownLabel(field);
            }};

            populate('Month', months);
            populate('Category', cats);
            populate('Source', srcs);
        }}
        
        // --- Sorting ---
        function sortTable(field) {{
            const existingIndex = sortStack.findIndex(s => s.field === field);
            let direction = 'asc';
            if (existingIndex !== -1) {{
                if (existingIndex === 0) direction = sortStack[0].direction === 'asc' ? 'desc' : 'asc';
                else direction = sortStack[existingIndex].direction;
                sortStack.splice(existingIndex, 1);
            }} else {{
                if (field === 'Date' || field === 'Amount') direction = 'desc';
            }}
            sortStack.unshift({{ field: field, direction: direction }});
            if (sortStack.length > 3) sortStack.pop();
            updateSortIcons();
            sortAndRenderTable(currentData);
        }}

        function updateSortIcons() {{
            document.querySelectorAll('th').forEach(th => th.classList.remove('asc', 'desc'));
            if (sortStack.length > 0) {{
                const primary = sortStack[0];
                const activeTh = document.getElementById('th-' + primary.field);
                if (activeTh) activeTh.classList.add(primary.direction);
            }}
        }}

        // --- Column Resizer ---
        (function() {{
            const resizers = document.querySelectorAll('.col-resizer');
            resizers.forEach(resizer => {{
                resizer.addEventListener('mousedown', function(e) {{
                    e.stopPropagation(); e.preventDefault();
                    const th = resizer.parentElement;
                    const startX = e.pageX;
                    const startW = th.offsetWidth;
                    resizer.classList.add('dragging');
                    function onMove(e) {{ th.style.width = Math.max(50, startW + e.pageX - startX) + 'px'; }}
                    function onUp() {{
                        resizer.classList.remove('dragging');
                        document.removeEventListener('mousemove', onMove);
                        document.removeEventListener('mouseup', onUp);
                    }}
                    document.addEventListener('mousemove', onMove);
                    document.addEventListener('mouseup', onUp);
                }});
            }});
        }})();

        let serverConnected = true;
        let pendingSave = false;
        const QUEUE_KEY = 'spending_dashboard_pending_changes_v1';
        let pendingChanges = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');

        function showServerStatus(state, msg) {{
            const el = document.getElementById('server-status');
            el.className = state;  // '' hides, 'disconnected' or 'saving' shows
            el.textContent = msg || '';
        }}

        function saveLocalStorage() {{
            localStorage.setItem(STORAGE_KEY, JSON.stringify(manualReimbursable));
            localStorage.setItem(NS_STORAGE_KEY, JSON.stringify(manualNotSpending));
            localStorage.setItem(CAT_STORAGE_KEY, JSON.stringify(manualCategories));
        }}

        function patchOverride(section, id, value) {{
            // Always update localStorage immediately
            saveLocalStorage();

            const change = {{ section, id, value, ts: Date.now() }};

            if (!isLocalServer) return;

            if (!serverConnected) {{
                // Queue for later
                pendingChanges.push(change);
                localStorage.setItem(QUEUE_KEY, JSON.stringify(pendingChanges));
                return;
            }}

            sendChanges([change]);
        }}

        function patchOverrides(changes) {{
            // Batch version for bulk edits
            saveLocalStorage();
            const ts = Date.now();
            changes.forEach(c => c.ts = ts);
            if (!isLocalServer) return;
            if (!serverConnected) {{
                pendingChanges.push(...changes);
                localStorage.setItem(QUEUE_KEY, JSON.stringify(pendingChanges));
                return;
            }}
            sendChanges(changes);
        }}

        function sendChanges(changes) {{
            pendingSave = true;
            fetch('/api/overrides', {{
                method: 'PATCH',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ changes }}),
            }}).then(resp => {{
                if (!resp.ok) throw new Error('Server error');
                pendingSave = false;
                if (!serverConnected) {{
                    serverConnected = true;
                    showServerStatus('', '');
                }}
            }}).catch(() => {{
                pendingSave = false;
                // Queue failed changes for retry
                pendingChanges.push(...changes);
                localStorage.setItem(QUEUE_KEY, JSON.stringify(pendingChanges));
                // If server is already back (heartbeat recovered), retry soon
                if (serverConnected) {{
                    setTimeout(flushPendingChanges, 500);
                }}
            }});
        }}

        function flushPendingChanges() {{
            if (pendingChanges.length === 0) return;
            const toSend = pendingChanges.splice(0);
            localStorage.setItem(QUEUE_KEY, JSON.stringify(pendingChanges));
            showServerStatus('saving', 'Reconnected — syncing...');
            fetch('/api/overrides', {{
                method: 'PATCH',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ changes: toSend }}),
            }}).then(resp => {{
                if (!resp.ok) throw new Error('Server error');
                localStorage.setItem(QUEUE_KEY, '[]');
                setTimeout(() => {{ if (serverConnected) showServerStatus('', ''); }}, 1500);
            }}).catch(() => {{
                // Put them back
                pendingChanges.unshift(...toSend);
                localStorage.setItem(QUEUE_KEY, JSON.stringify(pendingChanges));
            }});
        }}


        function exportOverrides() {{
            const data = {{
                reimbursable: manualReimbursable,
                notSpending: manualNotSpending,
                categories: manualCategories,
            }};
            const blob = new Blob([JSON.stringify(data, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'overrides.json';
            a.click();
        }}

        // --- Compare Years View ---

        let compareChartInit = false;
        let compareViewReady = false;

        function switchView(view) {{
            document.getElementById('view-single').classList.toggle('active', view === 'single');
            document.getElementById('view-compare').classList.toggle('active', view === 'compare');
            document.getElementById('single-view').style.display = (view === 'single') ? '' : 'none';
            document.getElementById('year-tabs').style.display = (view === 'single') ? '' : 'none';
            document.getElementById('compare-view').style.display = (view === 'compare') ? '' : 'none';
            if (view === 'compare') initCompareView();
        }}

        function ensureYearsLoaded(years, callback) {{
            const pending = [];
            years.forEach(year => {{
                const varName = 'spendingData_' + year;
                if (!window[varName]) {{
                    pending.push(new Promise((resolve, reject) => {{
                        const script = document.createElement('script');
                        script.src = 'data_' + year + '.js';
                        script.onload = () => window[varName] ? resolve() : reject('No data for ' + year);
                        script.onerror = () => reject('Failed to load data_' + year + '.js');
                        document.body.appendChild(script);
                    }}));
                }}
            }});
            if (pending.length === 0) {{ callback(); return; }}
            document.getElementById('loading-overlay').style.display = 'flex';
            Promise.all(pending)
                .then(() => callback())
                .catch(err => alert(err))
                .finally(() => {{ document.getElementById('loading-overlay').style.display = 'none'; }});
        }}

        function initCompareView() {{
            const years = (window.availableYears || []).slice().sort();
            if (!compareViewReady) {{
                // Populate year checkboxes
                const ym = document.getElementById('dd-menu-CmpYears');
                ym.innerHTML = '';
                years.forEach(y => {{
                    const lbl = document.createElement('label');
                    lbl.innerHTML = `<input type="checkbox" value="${{y}}" onchange="onCmpYearCheck()" checked> ${{y}}`;
                    ym.appendChild(lbl);
                }});
                updateCmpLabel('CmpYears', 'Years');

                // Load all years then populate categories
                ensureYearsLoaded(years, () => {{
                    populateCmpCategories(years);
                    compareViewReady = true;
                    renderCompareChart();
                }});
            }} else {{
                renderCompareChart();
            }}
        }}

        function populateCmpCategories(years) {{
            const allCats = new Set();
            (years || window.availableYears || []).forEach(year => {{
                const data = window['spendingData_' + year];
                if (!data) return;
                data.forEach(item => {{
                    const cat = manualCategories.hasOwnProperty(item.TxnID) ? manualCategories[item.TxnID] : item.Category;
                    allCats.add(cat);
                }});
            }});
            Object.values(manualCategories).forEach(c => allCats.add(c));
            const sorted = [...allCats].sort();
            const menu = document.getElementById('dd-menu-CmpCats');
            // Add select-all toggle
            menu.innerHTML = '<label style="font-weight:600; border-bottom:1px solid #eee; padding-bottom:4px;"><input type="checkbox" checked onchange="toggleAllCmpCats(this.checked)"> Select All</label>';
            sorted.forEach(cat => {{
                const lbl = document.createElement('label');
                lbl.innerHTML = `<input type="checkbox" value="${{cat}}" onchange="onCmpCatCheck()" checked> ${{cat}}`;
                menu.appendChild(lbl);
            }});
            updateCmpLabel('CmpCats', 'Categories');
        }}

        function toggleAllCmpCats(checked) {{
            const menu = document.getElementById('dd-menu-CmpCats');
            menu.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = checked);
            updateCmpLabel('CmpCats', 'Categories');
            renderCompareChart();
        }}

        function onCmpYearCheck() {{
            updateCmpLabel('CmpYears', 'Years');
            const menu = document.getElementById('dd-menu-CmpYears');
            const sel = [...menu.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);
            ensureYearsLoaded(sel, () => renderCompareChart());
        }}

        function onCmpCatCheck() {{
            // Update select-all checkbox state
            const menu = document.getElementById('dd-menu-CmpCats');
            const catBoxes = [...menu.querySelectorAll('input[type=checkbox]')].slice(1); // skip select-all
            const allChecked = catBoxes.every(cb => cb.checked);
            menu.querySelector('input[type=checkbox]').checked = allChecked;
            updateCmpLabel('CmpCats', 'Categories');
            renderCompareChart();
        }}

        function updateCmpLabel(field, noun) {{
            const menu = document.getElementById('dd-menu-' + field);
            let boxes = [...menu.querySelectorAll('input[type=checkbox]')];
            // Skip select-all checkbox for CmpCats
            if (field === 'CmpCats') boxes = boxes.slice(1);
            const checked = boxes.filter(cb => cb.checked);
            const toggle = document.querySelector('#dd-' + field + ' .cb-dropdown-toggle');
            if (checked.length === 0 || checked.length === boxes.length) {{
                toggle.textContent = 'All ' + noun;
            }} else if (checked.length <= 2) {{
                toggle.textContent = checked.map(cb => cb.value).join(', ');
            }} else {{
                toggle.textContent = checked.length + ' ' + noun;
            }}
        }}

        function getComparisonData(selectedYears, selectedCats, excludeR, excludeN) {{
            const result = {{}};
            selectedYears.forEach(year => {{
                const data = window['spendingData_' + year];
                if (!data) return;
                result[year] = {{}};
                data.forEach(item => {{
                    const cat = manualCategories.hasOwnProperty(item.TxnID) ? manualCategories[item.TxnID] : item.Category;
                    const isR = manualReimbursable.hasOwnProperty(item.TxnID) ? manualReimbursable[item.TxnID] : item.IsReimbursable;
                    const isN = manualNotSpending.hasOwnProperty(item.TxnID) ? manualNotSpending[item.TxnID] : item.IsNotSpending;
                    if (excludeR && isR) return;
                    if (excludeN && isN) return;
                    if (selectedCats.length > 0 && !selectedCats.includes(cat)) return;
                    result[year][cat] = (result[year][cat] || 0) + item.Amount;
                }});
            }});
            return result;
        }}

        function renderCompareChart() {{
            if (!compareViewReady) return;
            const ym = document.getElementById('dd-menu-CmpYears');
            const selectedYears = [...ym.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);

            const cm = document.getElementById('dd-menu-CmpCats');
            let catBoxes = [...cm.querySelectorAll('input[type=checkbox]')].slice(1); // skip select-all
            const checkedCats = catBoxes.filter(cb => cb.checked).map(cb => cb.value);
            const catFilter = (checkedCats.length === 0 || checkedCats.length === catBoxes.length) ? [] : checkedCats;

            const em = document.getElementById('dd-menu-CmpExclude');
            const exChecked = [...em.querySelectorAll('input[type=checkbox]:checked')].map(cb => cb.value);
            const excludeR = exChecked.includes('Reimbursable');
            const excludeN = exChecked.includes('NotSpending');

            if (selectedYears.length === 0) {{
                Plotly.purge('compare-chart');
                compareChartInit = false;
                return;
            }}

            ensureYearsLoaded(selectedYears, () => {{
                const data = getComparisonData(selectedYears, catFilter, excludeR, excludeN);

                // Collect all categories present across selected years
                const allCats = new Set();
                Object.values(data).forEach(yd => Object.keys(yd).forEach(c => allCats.add(c)));
                // Sort by total spending descending
                const catTotals = {{}};
                allCats.forEach(c => {{
                    catTotals[c] = Object.values(data).reduce((s, yd) => s + (yd[c] || 0), 0);
                }});
                const sortedCats = [...allCats].filter(c => catTotals[c] > 0).sort((a, b) => catTotals[b] - catTotals[a]);

                const yearColors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'];
                const traces = selectedYears.sort().map((year, idx) => ({{
                    x: sortedCats,
                    y: sortedCats.map(c => Math.round(data[year]?.[c] || 0)),
                    name: year,
                    type: 'bar',
                    marker: {{ color: yearColors[idx % yearColors.length] }},
                    hovertemplate: '%{{x}}: $%{{y:,.0f}}<extra>' + year + '</extra>'
                }}));

                const layout = {{
                    barmode: 'group',
                    margin: {{ t: 30, b: 140 }},
                    xaxis: {{ type: 'category', tickangle: -45, automargin: true }},
                    yaxis: {{ tickprefix: '$', tickformat: ',.0f' }},
                    legend: {{ orientation: 'h', y: 1.08 }},
                }};

                if (!compareChartInit) {{
                    Plotly.newPlot('compare-chart', traces, layout, {{ responsive: true }});
                    compareChartInit = true;
                }} else {{
                    Plotly.react('compare-chart', traces, layout);
                }}
            }});
        }}

    </script>
</body>
</html>
    """

    path = os.path.join(output_dir, 'spending_dashboard.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Dashboard shell saved to: {path}")
