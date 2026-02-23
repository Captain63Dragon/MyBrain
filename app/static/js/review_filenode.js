/* eslint-disable no-unused-vars */
const formDirtyStates = new Map();
// Map fnode properties to td classes
export const fieldMapping = {
    'node': 'FILE-NODE-id',
    'category': 'category',
    'company': 'company',
    'contact': 'contact_name',
    'phone': 'phone',
    'cell': 'cell',
    'email': 'email',
    'description': 'description',
    'context': 'context_note',
    'filepath': 'filepath',
    'reviewed': 'reviewed'
};

const tableColumns = ['node', 'category', 'contact', 'phone', 'cell', 'description', 'filepath'];
const tableMapping = Object.fromEntries(
    Object.entries(fieldMapping).filter(([key]) => tableColumns.includes(key))
);


// #### initialization for after DOM is loaded ####
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
    // updatePane.addEventListener('change', (e) => {
    updatePane.addEventListener('input', (e) => {
        // filter out updates to reviewed checkbox
        if (e.target.name?.startsWith('reviewed')) return 
        const form = e.target.closest('form')
        if (form) {
            formDirtyStates.set(form, true)
            const saveBtn = form.querySelector('.btn-primary')
            const resetBtn = form.querySelector('.btn-secondary')
            const cnt = form.dataset.cnt;
            const nodeId = form.querySelector(`#node${cnt}`).value;
            const row = document.getElementById(nodeId);
            row.classList.add('row-edited');
            saveBtn.disabled = false
            resetBtn.disabled = false
            updateBulkActions()
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
        const response = await fetch('/buscard/query/review_filenode', {
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
    document.querySelector('[data-tab="query"]').click()
};

document.getElementById('delete-selected').addEventListener('click', async () => {
    const selected = getSelectedRecordIds();
    // console.log("Selected is ", selected)
    if (confirm(`Delete ${selected.length} record(s)?`)) {
        const response = await fetch('/buscard/node/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodeIds: selected })
        });

        const result = await response.json();

        if (result.status === 'ok') {
            // your existing UI cleanup code
            selected.forEach(id => {
                const row = document.getElementById(id)
                const form = getFormByNodeId(id)
                row.style.opacity = '0.3'
                setTimeout(() => {
                    row.remove()
                    if (form) {
                        formDirtyStates.delete(form)
                        const panelId = `record${form.dataset.cnt}`
                        form.closest('.sub-tab-content')?.remove()
                        document.querySelector(`[data-record="${panelId}"]`)?.remove()
                    }
                }, 300)
            })

            document.getElementById('select-all').checked = false;
            updateBulkActions();
        } else {
            console.error('Delete failed:', result);
        }
    }
});

document.getElementById('execute-action').addEventListener('click', async () => {
    const actionSelect = document.getElementById('bulk-action-select');
    const action = actionSelect.value;
    const selected = getSelectedRecordIds();
    const recordCheckboxes = document.querySelectorAll('.record-checkbox');

    const dirtySelected = selected.filter(id => {
        const form = getFormByNodeId(id);
        return form && formDirtyStates.get(form);
    });

    switch(action) {
        case 'commit': {
            const updates = dirtySelected.map(id => {
                const form = getFormByNodeId(id);
                return {
                    nodeId: id,
                    fields: getFormFields(form)
                };
            });

            for (const update of updates) {
                const response = await fetch('/buscard/node/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(update)
                });
                const result = await response.json();

                if (result.status === 'ok') {
                    const row = document.getElementById(update.nodeId);
                    row.classList.remove('row-edited');
                    row.classList.add('row-saved');
                    const form = getFormByNodeId(update.nodeId);
                    if (form) {
                        formDirtyStates.delete(form);
                        form.querySelector('.save-btn').disabled = true;
                        form.querySelector('.reset-btn').disabled = true;
                    }
                } else {
                    console.error('Update failed for', update.nodeId, result);
                }
            }
            break;
        }
        case 'move':
            alert(`Would open file move dialog for ${selected.length} records`);
            break;

        case 'export':
            alert(`Would export ${selected.length} records to CSV`);
            break;
    }

    actionSelect.value = '';
    recordCheckboxes.forEach(cb => cb.checked = false);
    document.getElementById('select-all').checked = false;
    updateBulkActions();

});

// #### Table and Row updates ####
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
    for (const [className, propName] of Object.entries(tableMapping)) {
        const td = document.createElement('td');
        let newValue = fnode[propName];

        if (className === 'filepath') {
            const filepath = newValue || '';
            const subpath = filepath.toLowerCase().startsWith(rootpath.toLowerCase())
                ? filepath.slice(rootpath.length)
                : filepath;
            newValue = subpath;
        }

        td.className = className;
        const value = newValue || '';
        td.title = value;

        if (className === 'description') {
            td.textContent = truncate(value, 47);
        } else if (className === 'filepath') {
            td.textContent = truncate(value, 87);
        } else {
            td.textContent = value;
        }

        tr.appendChild(td);
    }
    return tr;
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
            const form = getFormByNodeId(row.id)
            if (form && formDirtyStates.get(form)) {
                count++
            }
        }
    });
    return count;
}

// Get selected record IDs
function getSelectedRecordIds() {
    const recordCheckboxes = document.querySelectorAll('.record-checkbox')
    console.log ("Selected Rows", recordCheckboxes)
    const selected = [];
    recordCheckboxes.forEach(cb => {
        if (cb.checked) {
            const row = cb.closest('tr');
            selected.push(row.id);
        }
    });
    // console.log("Checked boxes", selected)
    return selected;
}

// #### Forms and Panel routines ####
function getFormByNodeId(nodeId) {
    for (const [form] of formDirtyStates.entries()) {
        if (form.dataset.nodeId === nodeId) {
            return form
        }
    }
    return null
}

function getFormFields(form) {
    const cnt = form.dataset.cnt;
    const fields = {};
    Object.entries(fieldMapping).forEach(([formKey, nodeKey]) => {
        if (formKey === 'node') return;
        const el = form.querySelector(`[name="${formKey}${cnt}"]`);
        if (!el) return;
        fields[nodeKey] = el.type === 'checkbox' ? el.checked : el.value;
    });
    return fields;
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
            input.defaultValue = value || '';
        }
        
        input.id = id;
        input.name = name;
        if (readonly) input.readOnly = true;
        
        group.appendChild(labelEl);
        group.appendChild(input);
        return group;
    }

        // Create recordForm fields
    const nodeGroup = createFormGroup('Node ID:', `node${cnt}`, `node${cnt}`, record['FILE-NODE-id'], true);
    // nodeId captured here for closure scope in listeners. Also accessible via the dataset nodeId.
    const nodeId = nodeGroup.querySelector('input[name^="node"]').value;
    recordForm.dataset.nodeId = nodeId;
    recordForm.dataset.cnt = cnt;
    recordForm.appendChild(nodeGroup);
    recordForm.appendChild(createFormGroup('Category:', `category${cnt}`, `category${cnt}`, record['category']));
    recordForm.appendChild(createFormGroup('Company:', `company${cnt}`, `company${cnt}`, record['company']));
    recordForm.appendChild(createFormGroup('Contact Name:', `contact${cnt}`, `contact${cnt}`, record['contact_name']));
    recordForm.appendChild(createFormGroup('Phone:', `phone${cnt}`, `phone${cnt}`, record['phone']));
    recordForm.appendChild(createFormGroup('Email:', `email${cnt}`, `email${cnt}`, record['email']));
    recordForm.appendChild(createFormGroup('Description:', `description${cnt}`, `description${cnt}`, record['description'], false, true));
    recordForm.appendChild(createFormGroup('Context Note:', `context${cnt}`, `context${cnt}`, record['context_note'], false, true));
    recordForm.appendChild(createFormGroup('File Path:', `filepath${cnt}`, `filepath${cnt}`, record['filepath'], true));
    // Create form actions
    const actions = document.createElement('div');
    actions.className = 'form-actions';
    
    const saveBtn = document.createElement('button');
    saveBtn.type = 'submit';
    saveBtn.className = 'btn btn-primary';
    saveBtn.textContent = 'Save Changes';
    saveBtn.disabled = true;  // TODO: could this be set to the actual value here?
    
    const resetBtn = document.createElement('button');
    resetBtn.type = 'reset';
    resetBtn.className = 'btn btn-secondary';
    resetBtn.textContent = 'Reset';
    resetBtn.disabled = true; // TODO: could this be set to the actual value here?

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

    resetBtn.addEventListener('click', () => {
        recordForm.reset();
        // console.log("Reset Btn")
    });

    recordForm.addEventListener('reset', () => {
        formDirtyStates.set(recordForm, false);
        saveBtn.disabled = true;
        resetBtn.disabled = true;
        const row = document.getElementById(nodeId);
        row.classList.remove('row-edited');
        // console.log("Reset form", recordForm)
        updateBulkActions()
    });

    reviewedCB.addEventListener('change', (e) => {
        const row = document.getElementById(nodeId);
        if (e.target.checked) {
            row.classList.add('row-reviewed');
        } else {
            row.classList.remove('row-reviewed');
        }
    })

    recordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nodeId = recordForm.dataset.nodeId;
        const fields = getFormFields(recordForm);

        const response = await fetch('/buscard/node/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nodeId, fields })
        });

        const result = await response.json();

        if (result.status === 'ok') {
            // Baseline defaults to saved values for revert
            recordForm.querySelectorAll('input[type="text"]').forEach(input => {
                input.defaultValue = input.value;
            });
            recordForm.querySelectorAll('textarea').forEach(textarea => {
                textarea.defaultValue = textarea.value;
            });

            const row = document.getElementById(nodeId);
            formDirtyStates.set(recordForm, false);
            row.classList.remove('row-edited');
            row.classList.add('row-saved');
            saveBtn.disabled = true;
            resetBtn.disabled = true;
            updateBulkActions();
        } else {
            console.error('Save failed for', nodeId, result);
        }
    });
    
    formDirtyStates.set(recordForm, false)
    stc.appendChild(recordForm);
    return stc;
}

function deleteRecordPanel(form) {
    const dirtyCount = Array.from(formDirtyStates.values()).filter(dirty => dirty).length;
    if (dirtyCount > 0) {
        if (!confirm(`${dirtyCount} record(s) have unsaved changes. Confirm?`)) {
            return;
        }
    }
    formDirtyStates.delete(form);
    form.remove();
}

function createSubTab (record, cnt) {
    const btn = document.createElement('button')
    btn.className = 'sub-tab-btn'
    if (cnt === 1) btn.classList.add('active');
    btn.textContent = record['contact_name'] || `Record ${cnt}`
    btn.dataset.record = `record${cnt}`;
    return btn
}

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
// #### Utilities ####
function truncate(str, maxLength) {
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}
