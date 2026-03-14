/* eslint-disable no-unused-vars */
const formDirtyStates = new Map();
// Map fnode properties to td classes
// Build fieldMapping from MFN
let mfn = null;
let fieldMapping = null;
let tableMapping = null;

// #### initialization for after DOM is loaded ####
export function initContentTabs() {
    // Switch tab or sub tab on click in button
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
            // event click in tab so switch content shown
            const container = document.getElementById('right-content');
            
            container.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active');
            });
            e.target.classList.add("active");
            container.querySelectorAll('.tab-pane').forEach(c => c.style.display = 'none');
            container.querySelector(`#${tab}-pane`).style.display = 'block';
        }
        if (isSubTab && record) { // ie click in subtab
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
    // input value changes for forms
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

    document.getElementById('renameTable').addEventListener('click', (e) => {
        const tr = e.target.closest('tr');
        if (!tr) return;
        const i = parseInt(tr.dataset.index);
        if (e.target.classList.contains('reset-btn')) resetRenameRow(i);
        if (e.target.classList.contains('accept-btn')) acceptRenameSuggestion(i);
        if (e.target.classList.contains('cancel-btn')) resetRenameRow(i);
    });

    document.getElementById('renameTable').addEventListener('input', (e) => {
        if (e.target.classList.contains('editable')) {
            const i = parseInt(e.target.closest('tr').dataset.index);
            onRenameEdit(e.target, i);
        }
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

document.getElementById('edit-selected').addEventListener('click', () => {
    let checked = document.querySelectorAll('.record-checkbox:checked');
    let targetRow;

    if (checked.length === 0) {
        const firstRow = document.querySelector('tr[id]');
        if (!firstRow) return;
        const nodeId = firstRow.id;
        if (!confirm(`No selection. Edit first record: ${nodeId}?`)) return;
        targetRow = firstRow;
    } else {
        targetRow = checked[0].closest('tr');
    }

    const nodeId = targetRow.id;

    // switch to Review tab
    document.querySelector('.tab-btn[data-tab="update"]').click();

    // find matching sub-tab by row index
    const rows = Array.from(document.querySelectorAll('tr[id]'));
    const rowIndex = rows.indexOf(targetRow);
    const subTabs = document.querySelectorAll('.sub-tab-btn');
    if (subTabs[rowIndex]) {
        subTabs[rowIndex].click();
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
                    const form = getFormByNodeId(update.nodeId);
                    if (form) {
                        // Update baselines so reset reverts to saved values not pre-save values
                        form.querySelectorAll('input[type="text"]').forEach(i => i.defaultValue = i.value);
                        form.querySelectorAll('textarea').forEach(t => t.defaultValue = t.value);
                        formDirtyStates.delete(form);
                        form.querySelector('.btn-primary').disabled = true;
                        form.querySelector('.btn-secondary').disabled = true;
                    }
                    const row = document.getElementById(update.nodeId);
                    row.classList.remove('row-edited');
                    row.classList.add('row-saved');
                } else {
                    console.error('Update failed for', update.nodeId, result);
                }
            }
            break;
        }
        case 'move': {
            const renameNodes = selected.map(id => {
                const form = getFormByNodeId(id);
                const fields = getFormFields(form);
                const filepath = fields.filepath || '';
                const lastSlash = filepath.lastIndexOf('\\');
                return {
                    id: id,
                    contact: fields.contact_name || null,
                    path: lastSlash >= 0 ? filepath.substring(0, lastSlash) : '',
                    file: lastSlash >= 0 ? filepath.substring(lastSlash + 1) : filepath
                };
            });

            buildRenameTable(renameNodes);
            document.querySelector('[data-tab="rename"]').classList.remove('hidden');
            // switch to rename tab
            document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
            document.querySelector('#rename-pane').style.display = 'block';
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('[data-tab="rename"]').classList.add('active');
            break;
        }
        case 'export':
            alert(`Would export ${selected.length} records to CSV`);
            break;
    }

    actionSelect.value = '';
    recordCheckboxes.forEach(cb => cb.checked = false);
    document.getElementById('select-all').checked = false;
    updateBulkActions();

});

document.getElementById('rename-apply-all').addEventListener('click', validateAndDispatch);
document.getElementById('rename-reset-all').addEventListener('click', resetAllRename);

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
    // console.log ("Selected Rows", recordCheckboxes)
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
    const cnt = form.dataset.cnt
    // console.log('fieldMapping:', fieldMapping);
    // console.log('cnt:', cnt);
    // Object.entries(fieldMapping).forEach(([formKey, nodeKey]) => {
    //     if (formKey === 'node') return;
    //     const el = form.querySelector(`[name="${formKey}${cnt}"]`);
    //     console.log(`${formKey}${cnt} ->`, el ? el.type : 'NOT FOUND', el ? el.value : '');
    // });
    const fields = {};
    Object.entries(fieldMapping).forEach(([formKey, nodeKey]) => {
        if (formKey === 'node') return;
        const el = form.querySelector(`[name="${formKey}${cnt}"]`);
        if (!el) return;
        // Skip hidden optional fields
        const group = el.closest('.form-group');
        if (el.type !== 'checkbox' && (!group || group.style.display === 'none')) return;
        if (el.type === 'checkbox') {
            fields[nodeKey] = el.checked;
        } else if (el.value === '' && el.defaultValue !== '') {
            // Intentional clear — explicitly null so caller can decide
            fields[nodeKey] = null;
        } else if (el.value !== '') {
            fields[nodeKey] = el.value;
        }
        // empty and was empty — skip entirely
    });
    return fields;
}

function createAddFieldPicker(optionalGroups, mfn) {
    const container = document.createElement('div');
    container.className = 'add-field-picker';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-add-field';
    btn.textContent = '▸ Add Field';

    const dropdown = document.createElement('div');
    dropdown.className = 'add-field-dropdown';
    dropdown.style.display = 'none';

    function getHidden() {
        return Object.entries(optionalGroups)
            .filter(([, grp]) => grp.style.display === 'none');
    }

    function updateVisibility() {
        container.style.display = getHidden().length === 0 ? 'none' : '';
    }

    function buildDropdown() {
        dropdown.innerHTML = '';
        const hidden = getHidden();
        const checkedKeys = new Set();

        hidden.forEach(([prop]) => {
            const meta = mfn.optional_properties[prop];
            const itemLabel = meta.label ? meta.label : prop.replace(/-/g, ' ').replace(/_/g, ' ')
                .replace(/\b\w/g, c => c.toUpperCase());

            const item = document.createElement('div');
            item.className = 'add-field-item';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = prop;
            cb.id = `picker-${prop}`;
            cb.addEventListener('change', () => {
                cb.checked ? checkedKeys.add(prop) : checkedKeys.delete(prop);
                addBtn.disabled = checkedKeys.size === 0;
                addBtn.textContent = checkedKeys.size > 0
                    ? `Add ${checkedKeys.size} Field${checkedKeys.size > 1 ? 's' : ''}`
                    : 'Add Fields';
            });

            const lbl = document.createElement('label');
            lbl.htmlFor = `picker-${prop}`;
            lbl.textContent = itemLabel;

            item.appendChild(cb);
            item.appendChild(lbl);
            dropdown.appendChild(item);
        });

        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn-add-field-confirm';
        addBtn.textContent = 'Add Fields';
        addBtn.disabled = true;

        addBtn.addEventListener('click', () => {
            checkedKeys.forEach(prop => {
                optionalGroups[prop].style.display = '';
            });
            dropdown.style.display = 'none';
            btn.textContent = '▸ Add Field';
            updateVisibility();
        });

        dropdown.appendChild(addBtn);
    }

    btn.addEventListener('click', () => {
        if (dropdown.style.display === 'none') {
            buildDropdown();
            dropdown.style.display = '';
            btn.textContent = '▾ Add Field';
        } else {
            dropdown.style.display = 'none';
            btn.textContent = '▸ Add Field';
        }
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            dropdown.style.display = 'none';
            btn.textContent = '▸ Add Field';
        }
    });

    container.update = updateVisibility;
    container.appendChild(btn);
    container.appendChild(dropdown);
    updateVisibility();
    return container;
}

function createRecordPanel(record, rootpath, cnt, mfn) {

    const stc = document.createElement('div');
    stc.id = `record${cnt}`;
    stc.className = 'sub-tab-content';
    if (cnt === 1) stc.classList.add('active');
    const recordForm = document.createElement('form');
    recordForm.className = 'record-form';

    function createFormGroup(label, id, name, value, readonly = false, isTextarea = false, placeholder = '') {
        const group = document.createElement('div');
        group.className = 'form-group';

        const labelEl = document.createElement('label');
        labelEl.setAttribute('for', id);
        labelEl.textContent = label;

        let input;
        if (isTextarea) {
            input = document.createElement('textarea');
            input.textContent = value || '';
            input.defaultValue = value || '';
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = value || '';
            input.defaultValue = value || '';
        }

        input.id = id;
        input.name = name;
        if (readonly) input.readOnly = true;
        if (placeholder) input.placeholder = placeholder;

        group.appendChild(labelEl);
        group.appendChild(input);
        return group;
    }

    function toLabel(prop) {
        return prop.replace(/-/g, ' ').replace(/_/g, ' ')
                   .replace(/\b\w/g, c => c.toUpperCase()) + ':';
    }

    function addPropertyField(prop, meta, hidden = false) {
        const label = meta.label ? meta.label + ':' : toLabel(prop);
        const id = `${prop}${cnt}`;
        const value = record[prop];
        const isTextarea = meta.textarea === true;
        const placeholder = meta.description || '';
        const group = createFormGroup(label, id, id, value, false, isTextarea, placeholder);
        if (hidden) {
            group.style.display = 'none';
            group.dataset.originallyEmpty = 'true';
        }
        recordForm.appendChild(group);
        return group;
    }

    // --- System field: Node ID (readonly, always first) ---
    const nodeGroup = createFormGroup('Node ID:', `node${cnt}`, `node${cnt}`, record['FILE-NODE-id'], true);
    const nodeId = nodeGroup.querySelector('input[name^="node"]').value;
    recordForm.dataset.nodeId = nodeId;
    recordForm.dataset.cnt = cnt;
    recordForm.appendChild(nodeGroup);

    // --- Core properties: always render ---
    for (const [prop, meta] of Object.entries(mfn.core_properties)) {
        addPropertyField(prop, meta, false);
    }

    // --- Optional properties: render all, hide if unpopulated ---
    const optionalGroups = {};
    for (const [prop, meta] of Object.entries(mfn.optional_properties)) {
        const val = record[prop];
        const isEmpty = val === undefined || val === null || val === '';
        optionalGroups[prop] = addPropertyField(prop, meta, isEmpty);
    }

    // --- Add field picker ---
    const picker = createAddFieldPicker(optionalGroups, mfn);
    recordForm.appendChild(picker);

    // --- System field: filepath (readonly, always last) ---
    recordForm.appendChild(createFormGroup('File Path:', `filepath${cnt}`, `filepath${cnt}`, record['filepath'], true));

    // --- Form actions ---
    const actions = document.createElement('div');
    actions.className = 'form-actions';

    const saveBtn = document.createElement('button');
    saveBtn.type = 'submit';
    saveBtn.className = 'btn btn-primary save-btn';
    saveBtn.textContent = 'Save Changes';
    saveBtn.disabled = true;

    const resetBtn = document.createElement('button');
    resetBtn.type = 'reset';
    resetBtn.className = 'btn btn-secondary reset-btn';
    resetBtn.textContent = 'Reset';
    resetBtn.disabled = true;

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

    // --- Listeners ---
    resetBtn.addEventListener('click', () => {
        recordForm.reset();
    });

    recordForm.addEventListener('reset', () => {
        // Re-hide optional fields that were originally empty
        for (const [, group] of Object.entries(optionalGroups)) {
            if (group.dataset.originallyEmpty === 'true') {
                group.style.display = 'none';
            }
        }
        picker.update();
        formDirtyStates.set(recordForm, false);
        saveBtn.disabled = true;
        resetBtn.disabled = true;
        const row = document.getElementById(nodeId);
        row.classList.remove('row-edited');
        updateBulkActions();
    });

    reviewedCB.addEventListener('change', (e) => {
        const row = document.getElementById(nodeId);
        if (e.target.checked) {
            row.classList.add('row-reviewed');
        } else {
            row.classList.remove('row-reviewed');
        }
    });

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

    formDirtyStates.set(recordForm, false);
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
    let debugQuery = null;
    const fnodes = [];

    for (const item of data) {
        if (item.debug_query) { debugQuery = item; continue; }
        if (item.meta_file_node) continue;  // already handled in updateReviewForm
        fnodes.push(item);
    }

    if (!debugQuery) console.log('Debug query is invalid:', debugQuery);
    if (!fnodes || fnodes.length === 0) {
        console.log(`Full results node data not found`, data);
        return;
    }

    const tabContainer = document.getElementById('update-pane');
    tabContainer.innerHTML = '';
    const recordTabs = document.createElement('div');
    recordTabs.className = 'sub-tabs';

    fnodes.forEach((fnode, i) => {
        recordTabs.appendChild(createSubTab(fnode['fnode'], i+1));
    });
    tabContainer.appendChild(recordTabs);

    fnodes.forEach((fnode, i) => {
        tabContainer.appendChild(createRecordPanel(fnode['fnode'], rootpath, i+1, mfn));
    });
}

function updateReviewForm(data, rootpath) {
    // Extract known metadata items first, collect real fnodes
    let debugQuery = null;
    const fnodes = [];

    for (const item of data) {
        if (item.debug_query) { debugQuery = item; continue; }
        if (item.meta_file_node) {
            mfn = item.meta_file_node;
            mfn.core_properties = JSON.parse(mfn.core_properties);
            mfn.optional_properties = JSON.parse(mfn.optional_properties);
            // Build fieldMapping and tableMapping now that mfn is available
            fieldMapping = { 'node': 'FILE-NODE-id', 'filepath': 'filepath', 'reviewed': 'reviewed' };
            for (const prop of Object.keys(mfn.core_properties)) fieldMapping[prop] = prop;
            for (const prop of Object.keys(mfn.optional_properties)) fieldMapping[prop] = prop;
            const tableColumns = ['node', 'category', 'contact_name', 'phone', 'cell', 'description', 'filepath'];
            tableMapping = Object.fromEntries(
                tableColumns
                    .filter(key => key in fieldMapping)
                    .map(key => [key, fieldMapping[key]])
            );
            continue;
        }
        fnodes.push(item);
    }

    if (!debugQuery) console.log("Debug Query invalid:", debugQuery);
    if (!fnodes.length) { console.log(`Full results node data not found`, data); return; }

    const container = document.querySelector('.list');
    container.querySelector('.root-path').textContent = rootpath;
    const tableBody = container.querySelector('#search-path-rows');
    tableBody.innerHTML = '';
    fnodes.forEach(fnode => {
        tableBody.appendChild(createRow(fnode['fnode'], rootpath));
    });

    document.querySelector('[data-tab="update"]').classList.remove('hidden');
    const tab2 = document.querySelector('[data-tab="list"]');
    tab2.classList.remove('hidden');
    tab2.click();
    document.getElementById('results').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// #### Rename and or Move table helper functions. 
function onRenameEdit(input, i) {
    const pathInp = document.getElementById(`rpath-${i}`);
    const fileInp = document.getElementById(`rfile-${i}`);
    pathInp.classList.toggle('dirty', pathInp.value !== pathInp.dataset.orig);
    fileInp.classList.toggle('dirty', fileInp.value !== fileInp.dataset.orig);
    const isDirty = pathInp.value !== pathInp.dataset.orig || fileInp.value !== fileInp.dataset.orig;
    setRenameRowState(i, isDirty ? 'dirty' : 'clean');
    updateRenameDirtyCount();
}

function setRenameRowState(i, state) {
    const tr = document.querySelector(`#renameTable tr[data-index="${i}"]`);
    const dot = document.getElementById(`rdot-${i}`);
    tr.className = '';
    dot.className = 'status-dot';
    tr.dataset.rowstate = state;
    if (state === 'dirty')      { tr.classList.add('dirty');      dot.classList.add('dirty'); }
    if (state === 'suggested')  { tr.classList.add('suggested');  dot.classList.add('suggested'); }
    if (state === 'flagged')    { tr.classList.add('flagged');    dot.classList.add('flagged'); }
    if (state === 'dispatched') { tr.classList.add('dispatched'); }
    if (state === 'success')    { tr.classList.add('success'); }
    if (state === 'error')      { tr.classList.add('error');      dot.classList.add('flagged'); }
    if (state === 'clean')      { dot.classList.add('hidden'); }
}

function setRenameFlag(i, msg, state) {
    document.getElementById(`rflag-${i}`).textContent = msg;
    setRenameRowState(i, state);
}

function setRenameActions(i, type, errMsg = '') {
    const cell = document.getElementById(`ractions-${i}`);
    if (type === 'reset') {
        cell.innerHTML = `<button class="reset-btn" title="Reset row">↺</button>`;
    } else if (type === 'accept') {
        cell.innerHTML = `
            <button class="accept-btn">Accept</button>
            <button class="cancel-btn" title="Cancel">✕</button>`;
    } else if (type === 'spinner') {
        cell.innerHTML = `<span class="spinner"></span>`;
    } else if (type === 'done') {
        cell.innerHTML = `<span style="color:#43a047; font-size:16px;">✓</span>`;
    } else if (type === 'error') {
        cell.innerHTML = `<span style="color:#e53935; font-size:16px;" title="${errMsg}">✕</span>`;
    }
}

function resetRenameRow(i) {
    const pathInp = document.getElementById(`rpath-${i}`);
    const fileInp = document.getElementById(`rfile-${i}`);
    pathInp.value = pathInp.dataset.orig;
    fileInp.value = fileInp.dataset.orig;
    pathInp.classList.remove('dirty', 'suggested');
    fileInp.classList.remove('dirty', 'suggested');
    document.getElementById(`rflag-${i}`).textContent = '';
    setRenameRowState(i, 'clean');
    setRenameActions(i, 'reset');
    updateRenameDirtyCount();
}

function resetAllRename() {
    const rows = document.querySelectorAll('#renameTable tr[data-index]');
    rows.forEach(tr => resetRenameRow(parseInt(tr.dataset.index)));
}

function updateRenameDirtyCount() {
    const count = document.querySelectorAll('#renameTable tr.dirty, #renameTable tr.suggested').length;
    document.getElementById('dirtyCount').textContent = count;
    
    // check if all rows are done
    const allRows = document.querySelectorAll('#renameTable tr[data-index]');
    const doneRows = document.querySelectorAll('#renameTable tr[style*="display: none"]');
    
    if (allRows.length > 0 && allRows.length === doneRows.length) {
        // all done — hide tab, switch to list
        document.querySelector('[data-tab="rename"]').classList.add('hidden');
        document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
        document.getElementById('list-pane').style.display = 'block';
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-tab="list"]').classList.add('active');
    }
}

function acceptRenameSuggestion(i) {
    setRenameRowState(i, 'dispatched');
    setRenameActions(i, 'spinner');
    dispatchRenameRow(i);
    updateRenameDirtyCount();
}

async function validateAndDispatch() {
    const dirtyRows = [];
    document.querySelectorAll('#renameTable tr.dirty').forEach(tr => {
        dirtyRows.push(parseInt(tr.dataset.index));
    });

    if (!dirtyRows.length) { alert('Nothing staged.'); return; }

    for (const i of dirtyRows) {
        const node = window._renameNodes[i];
        const pathInp = document.getElementById(`rpath-${i}`);
        const fileInp = document.getElementById(`rfile-${i}`);
        const intent = (node.file !== fileInp.value) ? 'rename' : 'move';

        const targetPath = pathInp.value;
        const targetFile = fileInp.value;
        const source = node.path + '\\' + node.file;
        const target = targetPath + '\\' + targetFile;
        // no change — skip
        if (source === target) {
            resetRenameRow(i);
            continue;
        }

        // dispatch immediately
        setRenameRowState(i, 'dispatched');
        setRenameActions(i, 'spinner');
        await dispatchRenameRow(i, intent);
    }
    updateRenameDirtyCount();
}

function buildRenameTable(nodes) {
    const tbody = document.getElementById('renameTable');
    tbody.innerHTML = '';
    
    nodes.forEach((node, i) => {
        const tr = document.createElement('tr');
        tr.dataset.index = i;
        tr.dataset.nodeId = node.id;
        tr.dataset.rowstate = 'clean';
        tr.innerHTML = `
            <td class="col-status"><span class="status-dot hidden" id="rdot-${i}"></span></td>
            <td class="col-id node" title="${node.id}">${node.id}</td>
            <td class="col-contact">${node.contact || '<span class="null-val">—</span>'}</td>
            <td class="col-path">
                <input class="editable" id="rpath-${i}" data-field="path" data-orig="${node.path}" value="${node.path}" />
                <span class="flag-msg" id="rflag-${i}"></span>
            </td>
            <td class="sep">\\</td>
            <td class="col-file">
                <input class="editable" id="rfile-${i}" data-field="file" data-orig="${node.file}" value="${node.file}" />
            </td>
            <td class="col-actions" id="ractions-${i}">
                <button class="reset-btn" title="Reset row">↺</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // store for later reference
    window._renameNodes = nodes;
}

function watchRenameResult(i, mfi_id) {
    const es = new EventSource(`/sse/watch?mfi_ids=${mfi_id}`);

    es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // DEBUG console.log('[watchRenameResult] onmessage received:', data);
        
        if (data.status === 'done') { es.close(); return; }
        if (data.status === 'timeout') { 
            es.close();
            setRenameRowState(i, 'flagged');
            document.getElementById(`rflag-${i}`).textContent = 'No response — check manually';
            return; 
        }
        
        es.close();

        if (data.status === 'completed') {
            setRenameRowState(i, 'success');
            setRenameActions(i, 'done');
            setTimeout(() => {
                const tr = document.querySelector(`#renameTable tr[data-index="${i}"]`);
                tr.style.transition = 'opacity 0.8s';
                tr.style.opacity = '0';
                setTimeout(() => {
                    tr.style.display = 'none';
                    updateRenameDirtyCount();
                }, 800);
            }, 1200);
        } else {
            // failed path — data.error should have the message
            const errMsg = data.error || 'Unknown error';
            setRenameRowState(i, 'error');
            setRenameActions(i, 'error', errMsg);
            document.getElementById(`rflag-${i}`).textContent = errMsg;
        }
    };

    es.onerror = () => {
        es.close();
        setRenameRowState(i, 'error');
        setRenameActions(i, 'error', 'SSE connection failed');
        document.getElementById(`rflag-${i}`).textContent = 'SSE connection failed';
    };
}

async function dispatchRenameRow(i, move_intent) {
    const node = window._renameNodes[i];
    const pathInp = document.getElementById(`rpath-${i}`);
    const fileInp = document.getElementById(`rfile-${i}`);

    const source = node.path + '\\' + node.file;
    const target = pathInp.value + '\\' + fileInp.value;

    try {
        const response = await fetch('/buscard/dispatch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action:  'move',
                source:  source,
                target:  target,
                node_id: node.id,
                intent: move_intent,
                mfn_id:  mfn['MFN-id'],
            })
        });
        const result = await response.json();
        // DEBUG console.log('rename dispatch queued', result);
        // DEBUG console.log('watching for mfi_id:', result.mfi_id);

        // watch mfi_id via SSE for result
        watchRenameResult(i, result.mfi_id);

    } catch (err) {
        setRenameRowState(i, 'error');
        setRenameActions(i, 'error', err.message);
        document.getElementById(`rflag-${i}`).textContent = err.message;
    }
}

// #### Utilities ####
function truncate(str, maxLength) {
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}
