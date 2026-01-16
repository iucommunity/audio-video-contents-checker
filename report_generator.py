"""Generate HTML reports from check results."""

import os
import json
import webbrowser
from datetime import datetime
from typing import List, Dict
import config


class ReportGenerator:
    """Generate HTML reports with charts and tables."""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or config.REPORTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))
    
    def generate_html(self, results: List[Dict], summary: Dict, auto_open: bool = True) -> str:
        """Generate HTML report with charts and tables."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"content_check_report_{timestamp}.html")
        
        # Prepare data for charts
        working_count = summary.get('working', 0)
        broken_count = summary.get('broken', 0)
        total_count = summary.get('total', 0)
        
        # Data for type breakdown chart
        type_labels = []
        type_working = []
        type_broken = []
        if summary.get('by_type'):
            for type_name, type_stats in summary['by_type'].items():
                type_labels.append(type_name.capitalize())
                type_working.append(type_stats.get('working', 0))
                type_broken.append(type_stats.get('broken', 0))
        
        # Group results by type for tables
        results_by_type = {}
        for result in results:
            result_type = result.get('type', 'unknown')
            if result_type not in results_by_type:
                results_by_type[result_type] = []
            results_by_type[result_type].append(result)
        
        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Check Report - {timestamp}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .card-title {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .card-value {{
            font-size: 2.5em;
            font-weight: 700;
            color: #333;
        }}
        
        .card.working .card-value {{
            color: #27ae60;
        }}
        
        .card.broken .card-value {{
            color: #e74c3c;
        }}
        
        .card.total .card-value {{
            color: #3498db;
        }}
        
        .charts-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            padding: 30px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .chart-container h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.5em;
        }}
        
        .tables-section {{
            padding: 30px;
        }}
        
        .table-container {{
            margin-bottom: 40px;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .table-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 25px;
            font-size: 1.3em;
            font-weight: 600;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead {{
            background: #f8f9fa;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
            position: sticky;
            top: 0;
            background: #f8f9fa;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6;
        }}
        
        tbody tr {{
            transition: background-color 0.2s;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-working {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-broken {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .url-cell {{
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .url-link {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .url-link:hover {{
            text-decoration: underline;
        }}
        
        .error-cell {{
            max-width: 300px;
            font-size: 0.9em;
            color: #666;
        }}
        
        .filter-controls {{
            padding: 15px 25px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .filter-controls label {{
            font-weight: 600;
            color: #333;
        }}
        
        .filter-controls select, .filter-controls input {{
            padding: 8px 12px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .charts-section {{
                grid-template-columns: 1fr;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
            
            .table-wrapper {{
                overflow-x: scroll;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Content Check Report</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <div class="summary-cards">
            <div class="card total">
                <div class="card-title">Total Items</div>
                <div class="card-value">{total_count}</div>
            </div>
            <div class="card working">
                <div class="card-title">Working</div>
                <div class="card-value">{working_count}</div>
            </div>
            <div class="card broken">
                <div class="card-title">Broken</div>
                <div class="card-value">{broken_count}</div>
            </div>
            <div class="card">
                <div class="card-title">Success Rate</div>
                <div class="card-value">{round((working_count / total_count * 100) if total_count > 0 else 0, 1)}%</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-container">
                <h2>Status Overview</h2>
                <canvas id="statusChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>Status by Type</h2>
                <canvas id="typeChart"></canvas>
            </div>
        </div>
        
        <div class="tables-section">
            <div class="table-container">
                <div class="table-header">All Results</div>
                <div class="filter-controls">
                    <label>Filter by Type:</label>
                    <select id="typeFilter" onchange="filterTable()">
                        <option value="">All Types</option>
                        {''.join([f'<option value="{t}">{t.capitalize()}</option>' for t in results_by_type.keys()])}
                    </select>
                    <label>Filter by Status:</label>
                    <select id="statusFilter" onchange="filterTable()">
                        <option value="">All Statuses</option>
                        <option value="working">Working</option>
                        <option value="broken">Broken</option>
                    </select>
                    <label>Search:</label>
                    <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Search by name or URL...">
                </div>
                <div class="table-wrapper">
                    <table id="resultsTable">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>URL</th>
                                <th>Error Message</th>
                                <th>Check Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {self._generate_table_rows(results)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Status Overview Chart (Pie Chart)
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Working', 'Broken'],
                datasets: [{{
                    data: [{working_count}, {broken_count}],
                    backgroundColor: ['#27ae60', '#e74c3c'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            font: {{
                                size: 14
                            }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = {total_count};
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${{label}}: ${{value}} (${{percentage}}%)`;
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Status by Type Chart (Bar Chart)
        const typeCtx = document.getElementById('typeChart').getContext('2d');
        new Chart(typeCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(type_labels) if type_labels else '[]'},
                datasets: [
                    {{
                        label: 'Working',
                        data: {json.dumps(type_working) if type_working else '[]'},
                        backgroundColor: '#27ae60',
                        borderRadius: 5
                    }},
                    {{
                        label: 'Broken',
                        data: {json.dumps(type_broken) if type_broken else '[]'},
                        backgroundColor: '#e74c3c',
                        borderRadius: 5
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        position: 'top',
                        labels: {{
                            padding: 15,
                            font: {{
                                size: 14
                            }}
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    x: {{
                        stacked: false,
                        grid: {{
                            display: false
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
        
        // Table filtering function
        function filterTable() {{
            const typeFilter = document.getElementById('typeFilter').value.toLowerCase();
            const statusFilter = document.getElementById('statusFilter').value.toLowerCase();
            const searchInput = document.getElementById('searchInput').value.toLowerCase();
            const table = document.getElementById('resultsTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let i = 0; i < rows.length; i++) {{
                const row = rows[i];
                const type = row.getAttribute('data-type') || '';
                const status = row.getAttribute('data-status') || '';
                const text = row.textContent || '';
                
                const typeMatch = !typeFilter || type.toLowerCase() === typeFilter;
                const statusMatch = !statusFilter || status.toLowerCase() === statusFilter;
                const searchMatch = !searchInput || text.toLowerCase().includes(searchInput);
                
                if (typeMatch && statusMatch && searchMatch) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }}
        }}
    </script>
</body>
</html>"""
        
        # Write HTML file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML report saved: {filename}")
        
        # Auto-open in browser
        if auto_open:
            try:
                webbrowser.open(f'file://{os.path.abspath(filename)}')
                print("Report opened in default browser.")
            except Exception as e:
                print(f"Could not auto-open report: {e}")
                print(f"Please open manually: {filename}")
        
        return filename
    
    def _generate_table_rows(self, results: List[Dict]) -> str:
        """Generate HTML table rows from results."""
        rows = []
        for result in results:
            name = self._escape_html(result.get('name', 'Unknown'))
            result_type = self._escape_html(result.get('type', 'unknown'))
            status = result.get('status', 'unknown')
            url = self._escape_html(result.get('url', ''))
            error_msg = self._escape_html(result.get('error_message', ''))
            check_time = self._escape_html(result.get('check_time', ''))
            
            status_class = 'status-working' if status == 'working' else 'status-broken'
            status_text = 'Working' if status == 'working' else 'Broken'
            
            row = f"""
            <tr data-type="{result_type}" data-status="{status}">
                <td><strong>{name}</strong></td>
                <td>{result_type.capitalize()}</td>
                <td><span class="status-badge {status_class}">{status_text}</span></td>
                <td class="url-cell">
                    <a href="{url}" target="_blank" class="url-link" title="{url}">
                        {url[:60] + ('...' if len(url) > 60 else '')}
                    </a>
                </td>
                <td class="error-cell">{error_msg if error_msg else '-'}</td>
                <td>{check_time[:19] if check_time else '-'}</td>
            </tr>"""
            rows.append(row)
        
        return ''.join(rows)
    
    def generate_reports(self, results: List[Dict], summary: Dict, output_format: str = "html", auto_open: bool = True):
        """
        Generate reports in specified format.
        
        Args:
            results: List of check results
            summary: Summary statistics
            output_format: 'html' (default)
            auto_open: Whether to automatically open the HTML report in browser
        """
        generated_files = []
        
        if output_format in ['html', 'both']:
            html_file = self.generate_html(results, summary, auto_open=auto_open)
            generated_files.append(html_file)
        
        return generated_files
