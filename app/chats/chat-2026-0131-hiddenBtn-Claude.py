### panel for table of results - mockup
"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .search-path {
            background-color: #f9f9f9;
            padding: 10px;
            margin-bottom: 10px;
            border-left: 3px solid #4CAF50;
            font-family: monospace;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        tr:hover {
            background-color: #f5f5f5;
            cursor: pointer;
        }
        
        .description {
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .location {
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .node-col {
            max-width: 150px;
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        
        .select-col {
            width: 50px;
            text-align: center;
        }
    </style>
</head>
<body>
    <h2>Search Results</h2>
    
    <div class="search-path">
        <strong>Search Path:</strong> C:\Users\termi\Dropbox\Saves\
    </div>
    
    <table>
        <thead>
            <tr>
                <th class="select-col">Select</th>
                <th>Node</th>
                <th>Category</th>
                <th>Contact</th>
                <th>Phone</th>
                <th>Cell</th>
                <th>Description</th>
                <th>Location</th>
            </tr>
        </thead>
        <tbody>
            <!-- Sample rows for prototyping -->
            <tr>
                <td class="select-col"><input type="checkbox"></td>
                <td class="node-col" title="busCard_wills_powerattorney_20240606">busCard_wills_powerattorney_20240606</td>
                <td>Legal</td>
                <td>John Doe</td>
                <td title="780-555-1234">780-555-1234</td>
                <td title="780-555-5678">780-555-5678</td>
                <td class="description" title="This is a long description that will get truncated at some point when it exceeds the maximum width allowed in the table">This is a long description that will get truncated at...</td>
                <td class="location" title="legal\wills_powerattorney.pdf">legal\wills_powerattorney.pdf</td>
            </tr>
            <tr>
                <td class="select-col"><input type="checkbox"></td>
                <td class="node-col" title="busCard_gateway_resale_20231204">busCard_gateway_resale_20231204</td>
                <td>Business</td>
                <td>Gateway Toyota</td>
                <td title="780-675-1234">780-675-1234</td>
                <td title=""></td>
                <td class="description" title="Contact information for Gateway Toyota dealership resale department">Contact information for Gateway Toyota dealership res...</td>
                <td class="location" title="busCard-gatewayResale.pdf">busCard-gatewayResale.pdf</td>
            </tr>
            <tr>
                <td class="select-col"><input type="checkbox"></td>
                <td class="node-col" title="busCard_lions_club_20240115">busCard_lions_club_20240115</td>
                <td>Organization</td>
                <td>Lions Club Edmonton</td>
                <td title="780-675-8888">780-675-8888</td>
                <td title="780-555-9999">780-555-9999</td>
                <td class="description" title="Local Lions Club chapter meeting schedule and volunteer coordinator contact info for community events">Local Lions Club chapter meeting schedule and volunte...</td>
                <td class="location" title="organizations\lions_club.pdf">organizations\lions_club.pdf</td>
            </tr>
            <tr>
                <td class="select-col"><input type="checkbox"></td>
                <td class="node-col" title="busCard_plumber_emergency_20231015">busCard_plumber_emergency_20231015</td>
                <td>Services</td>
                <td>Bob's Plumbing</td>
                <td title="780-555-0000">780-555-0000</td>
                <td title="780-555-0001">780-555-0001</td>
                <td class="description" title="24/7 emergency plumbing service available year round">24/7 emergency plumbing service available year round</td>
                <td class="location" title="home\services\plumber.pdf">home\services\plumber.pdf</td>
            </tr>
        </tbody>
    </table>
    
    <div style="margin-top: 20px;">
        <button style="padding: 8px 16px;">Edit Selected</button>
        <button style="padding: 8px 16px; margin-left: 10px;">Delete Selected</button>
    </div>
</body>
</html>
"""

### And the panel for editing a single page with tabs if there are more than one.

"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        h2 {
            margin-bottom: 20px;
        }
        
        /* Sub-tab navigation */
        .sub-tabs {
            display: flex;
            border-bottom: 2px solid #ddd;
            margin-bottom: 20px;
        }
        
        .sub-tab-btn {
            padding: 10px 20px;
            border: none;
            background: none;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-size: 14px;
            color: #666;
        }
        
        .sub-tab-btn:hover {
            background-color: #f5f5f5;
        }
        
        .sub-tab-btn.active {
            border-bottom: 3px solid #4CAF50;
            color: #333;
            font-weight: bold;
        }
        
        /* Tab content */
        .sub-tab-content {
            display: none;
        }
        
        .sub-tab-content.active {
            display: block;
        }
        
        /* Form styling */
        .record-form {
            border: 2px solid #ddd;
            padding: 20px;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        
        .record-form h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
            color: #555;
        }
        
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 3px;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
        }
        
        .form-group input[readonly] {
            background-color: #e9e9e9;
            color: #666;
        }
        
        .form-group textarea {
            min-height: 80px;
            resize: vertical;
        }
        
        .form-actions {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .btn-primary {
            background-color: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #45a049;
        }
        
        .btn-secondary {
            background-color: #999;
            color: white;
            margin-left: 10px;
        }
        
        .btn-secondary:hover {
            background-color: #777;
        }
    </style>
</head>
<body>
    <h2>Update Records</h2>
    
    <!-- Sub-tabs for each record -->
    <div class="sub-tabs">
        <button class="sub-tab-btn active" data-record="record1">Record 1</button>
        <button class="sub-tab-btn" data-record="record2">Record 2</button>
    </div>
    
    <!-- Record 1 Content -->
    <div id="record1" class="sub-tab-content active">
        <div class="record-form">
            <h3>busCard_wills_powerattorney_20240606</h3>
            
            <div class="form-group">
                <label for="node1">Node ID (read-only):</label>
                <input type="text" id="node1" name="node1" value="busCard_wills_powerattorney_20240606" readonly>
            </div>
            
            <div class="form-group">
                <label for="category1">Category:</label>
                <input type="text" id="category1" name="category1" value="Legal">
            </div>
            
            <div class="form-group">
                <label for="contact1">Contact Name:</label>
                <input type="text" id="contact1" name="contact1" value="John Doe">
            </div>
            
            <div class="form-group">
                <label for="phone1">Phone:</label>
                <input type="text" id="phone1" name="phone1" value="780-555-1234">
            </div>
            
            <div class="form-group">
                <label for="cell1">Cell:</label>
                <input type="text" id="cell1" name="cell1" value="780-555-5678">
            </div>
            
            <div class="form-group">
                <label for="description1">Description:</label>
                <textarea id="description1" name="description1">This is a long description that will get truncated at some point when it exceeds the maximum width allowed in the table</textarea>
            </div>
            
            <div class="form-group">
                <label for="location1">Location (read-only):</label>
                <input type="text" id="location1" name="location1" value="legal\wills_powerattorney.pdf" readonly>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-primary">Save Changes</button>
                <button class="btn btn-secondary">Cancel</button>
            </div>
        </div>
    </div>
    
    <!-- Record 2 Content -->
    <div id="record2" class="sub-tab-content">
        <div class="record-form">
            <h3>busCard_lions_club_20240115</h3>
            
            <div class="form-group">
                <label for="node2">Node ID (read-only):</label>
                <input type="text" id="node2" name="node2" value="busCard_lions_club_20240115" readonly>
            </div>
            
            <div class="form-group">
                <label for="category2">Category:</label>
                <input type="text" id="category2" name="category2" value="Organization">
            </div>
            
            <div class="form-group">
                <label for="contact2">Contact Name:</label>
                <input type="text" id="contact2" name="contact2" value="Lions Club Edmonton">
            </div>
            
            <div class="form-group">
                <label for="phone2">Phone:</label>
                <input type="text" id="phone2" name="phone2" value="780-675-8888">
            </div>
            
            <div class="form-group">
                <label for="cell2">Cell:</label>
                <input type="text" id="cell2" name="cell2" value="780-555-9999">
            </div>
            
            <div class="form-group">
                <label for="description2">Description:</label>
                <textarea id="description2" name="description2">Local Lions Club chapter meeting schedule and volunteer coordinator contact info for community events</textarea>
            </div>
            
            <div class="form-group">
                <label for="location2">Location (read-only):</label>
                <input type="text" id="location2" name="location2" value="organizations\lions_club.pdf" readonly>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-primary">Save Changes</button>
                <button class="btn btn-secondary">Cancel</button>
            </div>
        </div>
    </div>
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #ddd;">
        <button class="btn btn-secondary">Back to List</button>
    </div>
    
    <script>
        // Sub-tab switching logic
        document.querySelectorAll('.sub-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active class from all buttons and content
                document.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked button and corresponding content
                btn.classList.add('active');
                const recordId = btn.getAttribute('data-record');
                document.getElementById(recordId).classList.add('active');
            });
        });
    </script>
</body>
</html>
"""

### And some hints on how to update the fields in javascript

"""
// Get the tbody
const tbody = document.getElementById('search-path-rows');

// Clear any existing content
tbody.innerHTML = '';

// Add new rows
data.forEach(record => {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td class="select-col"><input type="checkbox" data-node-id="${record.nodeId}"></td>
        <td class="node-col" title="${record.nodeId}">${record.nodeId}</td>
        <td>${record.category}</td>
        <td>${record.contact}</td>
        <td title="${record.phone}">${record.phone}</td>
        <td title="${record.cell}">${record.cell}</td>
        <td class="description" title="${record.description}">${record.description.substring(0, 60)}...</td>
        <td class="location" title="${record.location}">${record.location.substring(0, 60)}</td>
    `;
    tbody.appendChild(row);
});
"""