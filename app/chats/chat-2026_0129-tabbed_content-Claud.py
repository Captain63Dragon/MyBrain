
# Javascript: tabs_widget.js
/**
 * Tabbed Widget Module
 * Manages Query and Results tabs with swappable content
 */

class TabbedWidget {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }
        
        this.activeTab = 'query'; // Default active tab
        this.init();
    }

    /**
     * Initialize the tabbed widget
     */
    init() {
        this.render();
        this.attachEventListeners();
    }

    /**
     * Render the HTML structure
     */
    render() {
        this.container.innerHTML = `
            <div class="tabbed-widget">
                <!-- Tab Headers -->
                <div class="tab-headers">
                    <button class="tab-button active" data-tab="query">Query</button>
                    <button class="tab-button" data-tab="results">Results</button>
                </div>

                <!-- Tab Content -->
                <div class="tab-content">
                    <!-- Query Tab -->
                    <div class="tab-pane active" id="query-pane">
                        <div class="query-form">
                            <h3>Enter Your Query</h3>
                            <textarea 
                                id="query-input" 
                                class="query-textarea" 
                                placeholder="Enter your Cypher query here..."
                                rows="10"
                            ></textarea>
                            <div class="query-actions">
                                <button id="execute-query-btn" class="btn-primary">Execute Query</button>
                                <button id="clear-query-btn" class="btn-secondary">Clear</button>
                            </div>
                        </div>
                    </div>

                    <!-- Results Tab -->
                    <div class="tab-pane" id="results-pane">
                        <div class="results-container">
                            <div class="results-placeholder">
                                <p>No results yet. Execute a query to see results here.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners to tab buttons
     */
    attachEventListeners() {
        const tabButtons = this.container.querySelectorAll('.tab-button');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });

        // Optional: Add query execution handler
        const executeBtn = this.container.querySelector('#execute-query-btn');
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.handleQueryExecution());
        }

        // Optional: Add clear button handler
        const clearBtn = this.container.querySelector('#clear-query-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearQuery());
        }
    }

    /**
     * Switch between tabs
     * @param {string} tabName - Name of the tab to switch to
     */
    switchTab(tabName) {
        // Update active tab
        this.activeTab = tabName;

        // Update tab buttons
        const tabButtons = this.container.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            if (button.getAttribute('data-tab') === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });

        // Update tab panes
        const tabPanes = this.container.querySelectorAll('.tab-pane');
        tabPanes.forEach(pane => {
            if (pane.id === `${tabName}-pane`) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });
    }

    /**
     * Handle query execution (to be implemented/overridden)
     */
    handleQueryExecution() {
        const queryInput = this.container.querySelector('#query-input');
        const query = queryInput.value.trim();

        if (!query) {
            alert('Please enter a query');
            return;
        }

        // Placeholder for query execution
        console.log('Executing query:', query);
        
        // Switch to results tab
        this.switchTab('results');

        // This is where you'd call your backend
        // Example: this.executeQuery(query);
    }

    /**
     * Clear the query input
     */
    clearQuery() {
        const queryInput = this.container.querySelector('#query-input');
        if (queryInput) {
            queryInput.value = '';
        }
    }

    /**
     * Update results content
     * @param {string} html - HTML content to display in results
     */
    updateResults(html) {
        const resultsContainer = this.container.querySelector('.results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = html;
        }
    }

    /**
     * Get current query text
     * @returns {string} Current query text
     */
    getQuery() {
        const queryInput = this.container.querySelector('#query-input');
        return queryInput ? queryInput.value.trim() : '';
    }
}

# style sheet: tabs_widget.css
/* Tabbed Widget Styles */

.tabbed-widget {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Tab Headers */
.tab-headers {
    display: flex;
    border-bottom: 2px solid #e0e0e0;
    background: #f5f5f5;
}

.tab-button {
    padding: 12px 24px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    transition: all 0.3s ease;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}

.tab-button:hover {
    background: #ececec;
    color: #333;
}

.tab-button.active {
    color: #007bff;
    border-bottom: 2px solid #007bff;
    background: #fff;
}

/* Tab Content */
.tab-content {
    flex: 1;
    overflow: auto;
    position: relative;
}

.tab-pane {
    display: none;
    padding: 20px;
    height: 100%;
    box-sizing: border-box;
}

.tab-pane.active {
    display: block;
}

/* Query Form */
.query-form h3 {
    margin-top: 0;
    margin-bottom: 16px;
    color: #333;
    font-size: 18px;
}

.query-textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    resize: vertical;
    box-sizing: border-box;
}

.query-textarea:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
}

.query-actions {
    margin-top: 16px;
    display: flex;
    gap: 12px;
}

.btn-primary,
.btn-secondary {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.btn-primary {
    background: #007bff;
    color: white;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary {
    background: #6c757d;
    color: white;
}

.btn-secondary:hover {
    background: #545b62;
}

/* Results Container */
.results-container {
    height: 100%;
}

.results-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #999;
    font-style: italic;
}

.results-placeholder p {
    margin: 0;
}

# HTML example usage of tabbed content page -  example_usage.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tabbed Widget Example</title>
    <!-- For Flask, use: <link rel="stylesheet" href="{{ url_for('static', filename='css/tabs_widget.css') }}"> -->
    <link rel="stylesheet" href="tabs_widget.css">
    <style>
        /* Minimal mock container for the tabbed content window */
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #ecf0f1;
        }

        #widget-container {
            max-width: 1200px;
            height: 600px;
            margin: 0 auto;
        }
    </style>
</head>
<body>
    <!-- Just the tabbed content window -->
    <div id="widget-container"></div>

    <!-- For Flask, use: <script src="{{ url_for('static', filename='js/tabs_widget.js') }}"></script> -->
    <script src="tabs_widget.js"></script>
    <script>
        // Initialize the widget when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            const widget = new TabbedWidget('widget-container');

            // Optional: You can extend the widget's functionality
            // For example, override the query execution to call your backend
            const originalHandleQueryExecution = widget.handleQueryExecution.bind(widget);
            widget.handleQueryExecution = function() {
                const query = this.getQuery();
                
                if (!query) {
                    alert('Please enter a query');
                    return;
                }

                // Call your Flask backend
                fetch('/api/execute-query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                })
                .then(response => response.json())
                .then(data => {
                    // Update results
                    this.updateResults(formatResults(data));
                    // Switch to results tab
                    this.switchTab('results');
                })
                .catch(error => {
                    console.error('Error executing query:', error);
                    this.updateResults('<div class="error">Error executing query</div>');
                    this.switchTab('results');
                });
            };

            // Helper function to format results (customize as needed)
            function formatResults(data) {
                if (!data || !data.results || data.results.length === 0) {
                    return '<div class="results-placeholder"><p>No results found</p></div>';
                }

                // Example: Display results as a table
                let html = '<table class="results-table">';
                html += '<thead><tr>';
                
                // Add headers
                const headers = Object.keys(data.results[0]);
                headers.forEach(header => {
                    html += `<th>${header}</th>`;
                });
                html += '</tr></thead><tbody>';

                // Add rows
                data.results.forEach(row => {
                    html += '<tr>';
                    headers.forEach(header => {
                        html += `<td>${row[header]}</td>`;
                    });
                    html += '</tr>';
                });

                html += '</tbody></table>';
                return html;
            }
        });
    </script>
</body>
</html>