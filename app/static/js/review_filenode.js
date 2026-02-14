/* eslint-disable no-unused-vars */
// document.addEventListener('DOMContentLoaded', function() {
const formDirtyStates = new Map();

export function initContentTabs() {
    document.addEventListener('click', function(e) {
        // Click in the right pane?
        if (!document.getElementById('right-content').contains(e.target)) return;
        // Click in a tab or sub tab?
        const isTab = e.target.classList.contains('tab-btn')
        const isSubTab = e.target.classList.contains('sub-tab-btn')
        const tab = e.target.dataset.tab;
        const record = e.target.dataset.record;
        // console.log("Sanity Check Tabs",isTab, isSubTab, tab, record)
        if (!isTab && !isSubTab) return; 
        if (isTab && tab) {
            const container = document.getElementById('right-content');
            
            container.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active');
            });
            e.target.classList.add("active");
            container.querySelectorAll('.tab-pane').forEach(c => c.style.display = 'none');
            container.querySelector(`#${tab}-pane`).style.display = 'block';
        }
        if (isSubTab && record) { // ie subtab
            const subContainer = document.getElementById('update-pane')
            subContainer.querySelectorAll('.sub-tab-btn').forEach(b => {
                b.classList.remove('active');
            });
            e.target.classList.add("active");
            subContainer.querySelectorAll('.sub-tab-content').forEach(c => c.style.display = 'none');
            subContainer.querySelector(`#${record}`).style.display = 'block';
        }
    });

    // Update form changes
    const updatePane = document.getElementById('update-pane')
    updatePane.addEventListener('change', (e) => {
        const form = e.target.closest('form')
        if (form) {
            formDirtyStates.set(form, true)
            const saveBtn = form.querySelector('.btn-primary')
            saveBtn.disabled = false
        }
    })

    function hasUnsavedChanges() {
        return Array.from(formDirtyStates.values()).some(dirty => dirty)
    }

    
    // Find which forms are dirty
    function getDirtyForms() {
        const dirtyForms = [];
        for (const [form, isDirty] of formDirtyStates.entries()) {
            if (isDirty) {
                dirtyForms.push(form);
            }
        }
        return dirtyForms;
    }

    // Before switching tabs or closing
    if (hasUnsavedChanges()) {
        if (!confirm('You have unsaved changes. Continue?')) {
            // Cancel navigation.
        }
    }

    // Query Form submission
    document.getElementById('filenodeForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        // console.log("submit via POST")
        const response = await fetch('/buscard/submit/review_filenode', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        const rootpath = document.querySelector('#filenodeForm input[name="node_path"]')?.value || '';
        updateReviewForm(data, rootpath)
        updateUpdateForms(data, rootpath)
    });

    // List view check box select all in table header 
    document.getElementById('select-all').addEventListener('change', (e) => {
        const recordCheckboxes = document.querySelectorAll('.record-checkbox')
        recordCheckboxes.forEach(cb => {
            cb.checked = e.target.checked;
        });
        updateBulkActions();
    });

    // List view bulk action selector for commit or delete etc
    document.getElementById('bulk-action-select').addEventListener('change', () => {
        updateBulkActions();
    });

    document.getElementById('delete-selected').addEventListener('click', () => {
        const selected = getSelectedRecordIds();
        
        // Simulate deletion
        if (confirm(`Delete ${selected.length} record(s)?`)) {
            selected.forEach(id => {
                const row = document.querySelector(`tr[data-id="${id}"]`);
                row.style.opacity = '0.3';
                setTimeout(() => {
                    row.remove();
                    dirtyRecords.delete(id);
                }, 300);
            });
            
            // Uncheck select-all
            document.getElementById('select-all').checked = false;
            updateBulkActions();
        }
    });

    document.getElementById('execute-action').addEventListener('click', () => {
        const actionSelect = document.getElementById('bulk-action-select')
        const action = actionSelect.value;
        const selected = getSelectedRecordIds();
        const recordCheckboxes = document.querySelectorAll('.record-checkbox')        // Only commit dirty records
        const dirtySelected = selected.filter(id => dirtyRecords.has(id));
        
        switch(action) {
            case 'commit':
                dirtySelected.forEach(id => {
                    const row = document.querySelector(`tr[data-id="${id}"]`);
                    row.classList.remove('dirty');
                    row.classList.add('pristine');
                    row.querySelector('td:last-child').textContent = 'Pristine';
                    dirtyRecords.delete(id);
                });
                break;
                
            case 'move':
                alert(`Would open file move dialog for ${selected.length} records`);
                break;
                
            case 'export':
                alert(`Would export ${selected.length} records to CSV`);
                break;
        }
        
        // Reset action select and uncheck boxes
        actionSelect.value = '';
        recordCheckboxes.forEach(cb => cb.checked = false);
        document.getElementById('select-all').checked = false;
        updateBulkActions();
    });
    document.querySelector('[data-tab="query"]').click()
};

function updateReviewForm(data, rootpath) {
    const [debugQuery, ...fnodes] = data;
    if (!debugQuery) {
        console.log("Debug Query invalid:", debugQuery)
    }
    if (!fnodes || fnodes.length === 0) {
        console.log(`Full results node data not found ${data}`, data)
        return
    }
    const container = document.querySelector('.list')
    container.querySelector('.root-path').textContent = rootpath
    const tableBody = container.querySelector('#search-path-rows')
    tableBody.innerHTML = ''
    fnodes.forEach(fnode => {
        tableBody.appendChild(createRow(fnode['fnode'], rootpath));
    });

    // Unhide list and update tabs and show list tab
    document.querySelector('[data-tab="update"]').classList.remove('hidden');
    const tab2 = document.querySelector('[data-tab="list"]')
    tab2.classList.remove('hidden');
    tab2.click();
    // console.log(data)
    document.getElementById('results').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// Map fnode properties to td classes
const fieldMapping = {
  'node-col': 'FILE-NODE-id',
  'category': 'category',
  'name': 'contact_name',
  'phone': 'phone',
  'cell': 'cell',
  'description': 'description',
  'location': 'filepath'
};
    //   fn = data['fnode'] 
    //     'node-col'
    // }
    // tr.id = `node-${fnode.nodeId}`;
    // if fn['FILE-NODE-id']
    // "FILE-NODE-id": "busCard-employment-serv_20250916",
    // if fn['category']
    // "category": "employment services",
    // if fn['contact_name']
    // "contact_name": "Nadine Byers",
    // if fn['phone']
    // "phone": "780-609-0660",
    // if fn['cell']
    // if fn['description']
    // "description": "Employment agency that helps Athabascans get work.",
    // if fn['filepath']
    // "filepath": "C:\\Users\\termi\\Dropbox\\2025_0916-busCard-EmploymentServ.pdf",
    // if fn['context_note']
    // "context_note": "She helped me get employed at the Seniors Centre. See phone contact list for full contact info. Not an actual card.",
    // if fn['email']
    // "email": "nadine@abwes.com",
    // if fn['timestamp']
    // "timestamp": "2025-09-16 3:08 PM"
    // if fn['size']
    //   "size": "113 KB",
    // },
    // })

function truncate(str, maxLength) {
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

function createRow(fnode, rootpath) {
    const tr = document.createElement('tr');
    tr.id = fnode['FILE-NODE-id'];

    // Checkbox column
    const checkboxTd = document.createElement('td');
    checkboxTd.className = 'select-col';
    checkboxTd.innerHTML = '<input type="checkbox" class="record-checkbox">';
    const cb = checkboxTd.querySelector('.record-checkbox');
    cb.addEventListener('change', updateBulkActions);
    tr.appendChild(checkboxTd);

    // Data columns
    for (const [className, propName] of Object.entries(fieldMapping)) {
    const td = document.createElement('td');
    var newValue = fnode[propName]
    if (className == 'location') {
        // remove the root path
        const filepath = newValue
        // console.log("My rootpath is", rootpath, fnode['filepath'])
        const subpath = filepath.toLowerCase().startsWith(rootpath.toLowerCase()) 
            ? filepath.slice(rootpath.length) 
            : filepath;
        newValue = subpath
    }
    td.className = className;
    const value = newValue || '';

    td.title = value;
    td.textContent = className === 'description' ? truncate(value, 47) : value;
    td.textContent = className === 'location' ? truncate(value, 87) : value;
    tr.appendChild(td);
    }
    return tr;
}

const dirtyRecords = new Set(['record-2', 'record-4']);

function updateUpdateForms(data, rootpath) {
    // console.log("In updateUpdateForms",data, rootpath)
    const [debugQuery, ...fnodes] = data;
    if (!debugQuery) { // I dont think this fails; just for linter. 
        console.log('Debug query is invalid:', debugQuery);
}
    if (!fnodes || fnodes.length === 0) {
        console.log(`Full results node data not found ${data}`, data)
        return
    }
    // find sub tab div and hide all current buttons. 
    const tabContainer = document.getElementById('update-pane');
    tabContainer.innerHTML = '' // start fresh
    const recordTabs = document.createElement('div')
    recordTabs.className = 'sub-tabs'
    //   for each record tab button content
    fnodes.forEach((fnode, i) => {
        recordTabs.appendChild(createSubTab(fnode['fnode'], i+1));
    });
    tabContainer.appendChild(recordTabs)
    
    fnodes.forEach((fnode, i )=> {
        tabContainer.appendChild(createRecordPanel(fnode['fnode'], rootpath, i+1))
    });
} 

function createSubTab (record, cnt) {
    const btn = document.createElement('button')
    btn.className = 'sub-tab-btn'
    if (cnt === 1) btn.classList.add('active');
    btn.textContent = record['contact_name'] || `Record ${cnt}`
    btn.dataset.record = `record${cnt}`;
    return btn
}

function createRecordPanel(record, rootpath, cnt) {
    const stc = document.createElement('div')
    stc.id = `record${cnt}`
    stc.className = 'sub-tab-content'
    if (cnt === 1) stc.classList.add('active')
    const recordForm = document.createElement('form')
    recordForm.className = 'record-form'
    // Helper function to create form groups
    function createFormGroup(label, id, name, value, readonly = false, isTextarea = false) {
        const group = document.createElement('div');
        group.className = 'form-group';
        
        const labelEl = document.createElement('label');
        labelEl.setAttribute('for', id);
        labelEl.textContent = label;
        
        let input;
        if (isTextarea) {
            input = document.createElement('textarea');
            input.textContent = value || '';
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = value || '';
        }
        
        input.id = id;
        input.name = name;
        if (readonly) input.readOnly = true;
        
        group.appendChild(labelEl);
        group.appendChild(input);
        return group;
    }

        // Create recordForm fields
    recordForm.appendChild(createFormGroup('Node ID:', `node${cnt}`, `node${cnt}`, record['FILE-NODE-id'], true));
    recordForm.appendChild(createFormGroup('Category:', `category${cnt}`, `category${cnt}`, record['category']));
    recordForm.appendChild(createFormGroup('Company:', `company${cnt}`, `company${cnt}`, record['company']));
    recordForm.appendChild(createFormGroup('Contact Name:', `contact${cnt}`, `contact${cnt}`, record['contact_name']));
    recordForm.appendChild(createFormGroup('Phone:', `phone${cnt}`, `phone${cnt}`, record['phone']));
    recordForm.appendChild(createFormGroup('Email:', `email${cnt}`, `email${cnt}`, record['email']));
    recordForm.appendChild(createFormGroup('Description:', `description${cnt}`, `description${cnt}`, record['description'], false, true));
    recordForm.appendChild(createFormGroup('Context Note:', `context${cnt}`, `context${cnt}`, record['context_note'], false, true));
    recordForm.appendChild(createFormGroup('Location:', `location${cnt}`, `location${cnt}`, record['filepath'], true));
    // Create form actions
    const actions = document.createElement('div');
    actions.className = 'form-actions';
    
    const saveBtn = document.createElement('button');
    saveBtn.type = 'submit';
    saveBtn.className = 'btn btn-primary';
    saveBtn.textContent = 'Save Changes';
    
    const resetBtn = document.createElement('button');
    resetBtn.type = 'reset';
    resetBtn.className = 'btn btn-secondary';
    resetBtn.textContent = 'Reset';

    const reviewedCB = document.createElement('input');
    reviewedCB.type = 'checkbox';
    reviewedCB.id = `reviewed${cnt}`; 
    reviewedCB.name = `reviewed${cnt}`;
    reviewedCB.checked = record.reviewed ?? false;
    reviewedCB.className = 'my-checkbox-class';
    const label = document.createElement('label');
    label.htmlFor = `reviewed${cnt}`;
    label.textContent = 'Reviewed';

    actions.appendChild(saveBtn);
    actions.appendChild(resetBtn);
    actions.appendChild(reviewedCB);
    actions.appendChild(label);
    recordForm.appendChild(actions);



    
    // Add form submit handler
    recordForm.addEventListener('submit', (e) => {
        e.preventDefault();
        // Handle save logic here
        console.log('Form submitted for record', cnt);
    });
    
    stc.appendChild(recordForm);
    return stc;
}

// Update bulk action controls based on selection
function updateBulkActions() {
    const checkedCount = getCheckedCount();
    const dirtyCheckedCount = getCheckedDirtyCount();
    const selectionCount = document.getElementById('selection-count')
    
    // Update selection count
    if (checkedCount === 0) {
        selectionCount.textContent = '0 selected';
    } else {
        selectionCount.textContent = `${checkedCount} selected${dirtyCheckedCount > 0 ? ` (${dirtyCheckedCount} edited)` : ''}`;
    }
    
    // Enable/disable buttons
    document.getElementById('delete-selected').disabled = checkedCount === 0;
    const actionSelect = document.getElementById('bulk-action-select')
    const executeBtn = document.getElementById('execute-action')
    executeBtn.disabled = !actionSelect.value || checkedCount === 0;
}

// Get count of checked checkboxes
function getCheckedCount() {
    const recordCheckboxes = document.querySelectorAll('.record-checkbox')
    return Array.from(recordCheckboxes).filter(cb => cb.checked).length;
}

// Get count of checked dirty records
function getCheckedDirtyCount() {
    const recordCheckboxes = document.querySelectorAll('.record-checkbox')
    let count = 0;
    recordCheckboxes.forEach(cb => {
        if (cb.checked) {
            const row = cb.closest('tr');
            const recordId = row.dataset.id;
            if (dirtyRecords.has(recordId)) {
                count++;
            }
        }
    });
    return count;
}

// Get selected record IDs
function getSelectedRecordIds() {
    const recordCheckboxes = document.querySelectorAll('.record-checkbox')
    const selected = [];
    recordCheckboxes.forEach(cb => {
        if (cb.checked) {
            const row = cb.closest('tr');
            selected.push(row.dataset.id);
        }
    });
    return selected;
}


