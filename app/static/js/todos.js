(function () {
    let currentTodoId = null;
    let currentOwner   = null;
    // eslint-disable-next-line no-unused-vars
    let currentScore   = null;
    let panelMode      = null;  // 'edit' | 'create'
    let todosData = [];
    // eslint-disable-next-line no-unused-vars
    let editDirty = false;

    const statusFilter   = document.getElementById('todo-status-filter');
    const priorityFilter = document.getElementById('todo-priority-filter');
    const loadBtn        = document.getElementById('todo-load-btn');
    const tableWrap      = document.getElementById('todo-table-wrap');
    const tableBody      = document.getElementById('todo-table-body');
    const countEl        = document.getElementById('todo-count');
    const editPanel      = document.getElementById('todo-edit-panel');
    const editTitle      = document.getElementById('todo-edit-title');
    const editDesc       = document.getElementById('todo-edit-description');
    const editStatus     = document.getElementById('todo-edit-status');
    const editPriority   = document.getElementById('todo-edit-priority');
    const editFriction   = document.getElementById('todo-edit-friction');
    const editDue        = document.getElementById('todo-edit-due');
    const editNotes      = document.getElementById('todo-edit-notes');
    const ownerFilter    = document.getElementById('todo-owner-filter');
    const editOwner      = document.getElementById('todo-edit-owner');
    const saveBtn        = document.getElementById('todo-save-btn');
    const cancelBtn      = document.getElementById('todo-cancel-btn');
    const saveMsg        = document.getElementById('todo-save-msg');
    const newBtn         = document.getElementById('todo-new-btn');
    const subCheckWrap   = document.getElementById('todo-sub-check-wrap');
    const subCheck       = document.getElementById('todo-sub-check');
    const subPanel       = document.getElementById('todo-sub-panel');
    const subParentLabel = document.getElementById('todo-sub-parent-label');
    const subDesc        = document.getElementById('todo-sub-description');
    const subPriority    = document.getElementById('todo-sub-priority');
    const subFriction    = document.getElementById('todo-sub-friction');
    const subOwner       = document.getElementById('todo-sub-owner');
    const subDue         = document.getElementById('todo-sub-due');
    const subNotes       = document.getElementById('todo-sub-notes');
    const sortSelect     = document.getElementById('todo-sort-select');

    const PRIORITY_ORDER = { high: 1, medium: 2, low: 3 };
    const STATUS_ORDER   = { in_progress: 1, pending: 2, open: 3, completed: 4, deferred: 5, closed: 6 };
    const FRICTION_ORDER = { procrastination: 1, avoidance: 1, 'phone-call': 2, interviews: 3, 'waiting-on-other': 4, uncertain: 5, difficult: 6, boring: 7 };

    function sortedTodos(todos) {
        const mode = sortSelect.value;
        const copy = [...todos];
        if (mode === 'alpha') {
            return copy.sort((a, b) => (a.description || '').localeCompare(b.description || ''));
        }
        if (mode === 'due') {
            return copy.sort((a, b) => {
                if (!a.due && !b.due) return 0;
                if (!a.due) return 1;
                if (!b.due) return -1;
                return a.due.localeCompare(b.due);
            });
        }
        // Any policy_id sort mode - sort by score DESC
        if (mode.startsWith('policy:')) {
            return copy.sort((a, b) => (b.score || 0) - (a.score || 0));
        }
        // smart: priority → status → friction → owner
        return copy.sort((a, b) => {
            const p = (PRIORITY_ORDER[a.priority] || 9) - (PRIORITY_ORDER[b.priority] || 9);
            if (p !== 0) return p;
            const s = (STATUS_ORDER[a.status] || 9) - (STATUS_ORDER[b.status] || 9);
            if (s !== 0) return s;
            const f = (FRICTION_ORDER[a.friction] || 8) - (FRICTION_ORDER[b.friction] || 8);
            if (f !== 0) return f;
            return (a.owner || '').localeCompare(b.owner || '');
        });
    }

    const PRIORITY_COLORS = { high: '#e53935', medium: '#e67e22', low: '#888' };
    const STATUS_COLORS   = {
        open: '#3498db', pending: '#8e44ad', in_progress: '#27ae60',
        deferred: '#95a5a6', completed: '#43a047', closed: '#bbb'
    };

    function priorityBadge(p) {
        const color = PRIORITY_COLORS[p] || '#888';
        return `<span style="color:${color}; font-weight:600; font-size:12px; text-transform:uppercase;">${p || '-'}</span>`;
    }

    function statusBadge(s) {
        const color = STATUS_COLORS[s] || '#888';
        return `<span style="background:${color}; color:white; padding:2px 7px; border-radius:10px; font-size:11px;">${s || '-'}</span>`;
    }

    function truncate(str, max) {
        return str && str.length > max ? str.substring(0, max) + '...' : (str || '');
    }

    function scoreDisplay(score, nudge) {
        if (score === null || score === undefined) return '-';
        const color = nudge ? '#e53935' : '#888';
        const flag  = nudge ? ' ⚠' : '';
        return `<span style="font-size:12px; color:${color}; font-weight:${nudge ? 600 : 400};">${score}${flag}</span>`;
    }

    function renderTable(todos) {
        tableBody.innerHTML = '';
        sortedTodos(todos).forEach(todo => {
            const tr = document.createElement('tr');
            tr.dataset.id = todo.id;
            const friction = todo.friction
                ? `<span style="color:#c0392b; font-size:12px;">⚡ ${todo.friction}</span>`
                : '';
            const due = todo.due ? todo.due.substring(0, 10) : '';
            tr.innerHTML = `
                <td class="select-col"><input type="checkbox" class="record-checkbox"></td>
                <td class="description" title="${todo.description || ''}">${truncate(todo.description || '', 130)}</td>
                <td style="font-size:12px; color:#555;">${todo.owner || '-'}</td>
                <td>${priorityBadge(todo.priority)}</td>
                <td>${statusBadge(todo.status)}</td>
                <td>${friction}</td>
                <td style="font-size:12px; color:#666;">${due}</td>
                <td style="text-align:right;">${scoreDisplay(todo.score, todo.nudge)}</td>
            `;
            tr.addEventListener('click', (e) => {
                if (e.target.type === 'checkbox') return;
                openEditPanel(todo);
            });
            tableBody.appendChild(tr);
        });
        countEl.textContent = `${todos.length} item${todos.length !== 1 ? 's' : ''}`;
        tableWrap.style.display = 'block';
    }

    function openEditPanel(todo) {
        panelMode     = 'edit';
        currentTodoId = todo.id;
        currentOwner  = todo.owner || 'user';
        currentScore  = todo.score;
        const scoreStr = (todo.score !== null && todo.score !== undefined)
            ? `  |  score: ${todo.score}${todo.nudge ? ' ⚠' : ''}`
            : '';
        editTitle.textContent = `${todo.id}${scoreStr}`;
        saveBtn.textContent   = 'Save Changes';
        subCheckWrap.style.display = 'inline-flex';
        subCheck.checked           = false;
        subPanel.style.display     = 'none';
        subDesc.value = ''; subPriority.value = 'medium';
        subFriction.value = ''; subOwner.value = 'user';
        subDue.value = ''; subNotes.value = '';
        editDesc.value     = todo.description || '';
        editStatus.value   = todo.status || 'open';
        editPriority.value = (todo.priority || 'medium').toLowerCase();
        editFriction.value = todo.friction || '';
        editDue.value      = todo.due ? todo.due.substring(0, 10) : '';
        editNotes.value    = todo.notes || '';
        editOwner.value    = todo.owner || 'user';
        saveBtn.disabled   = true;
        saveMsg.textContent = '';
        editDirty = false;
        editPanel.style.display = 'block';
        editPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        document.querySelectorAll('#todo-table-body tr').forEach(r => r.classList.remove('row-edited'));
        const row = document.querySelector(`#todo-table-body tr[data-id="${todo.id}"]`);
        if (row) row.classList.add('row-edited');
    }

    function openCreatePanel() {
        panelMode     = 'create';
        currentTodoId = null;
        currentOwner  = 'user';
        currentScore  = null;
        editTitle.textContent = 'New Todo';
        saveBtn.textContent   = 'Create Todo';
        subCheckWrap.style.display = 'none';
        subPanel.style.display     = 'none';
        subCheck.checked           = false;
        editDesc.value     = '';
        editStatus.value   = 'open';
        editPriority.value = 'medium';
        editFriction.value = '';
        editDue.value      = '';
        editNotes.value    = '';
        editOwner.value    = 'user';
        saveBtn.disabled   = false;
        saveMsg.textContent = '';
        editDirty = false;
        editPanel.style.display = 'block';
        editPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        document.querySelectorAll('#todo-table-body tr').forEach(r => r.classList.remove('row-edited'));
        editDesc.focus();
    }

    function markDirty() {
        editDirty = true;
        saveBtn.disabled = false;
        saveMsg.textContent = '';
    }

    [editDesc, editStatus, editPriority, editFriction, editOwner, editDue, editNotes].forEach(el => {
        el.addEventListener('input', markDirty);
        el.addEventListener('change', markDirty);
    });

    function populateOwnerFilter(owners) {
        ownerFilter.innerHTML = owners.map(o =>
            `<option value="${o}"${o === 'user' ? ' selected' : ''}>${o === 'user' ? 'User' : o}</option>`
        ).join('');
    }

    async function initOwnerFilter() {
        try {
            const resp = await fetch('/todos/owners');
            const owners = await resp.json();
            populateOwnerFilter(['all', ...owners]);
            const ownerOptions = owners.map(o =>
                `<option value="${o}">${o === 'user' ? 'User' : o}</option>`
            ).join('');
            editOwner.innerHTML = ownerOptions;
            subOwner.innerHTML  = ownerOptions;
        } catch (err) {
            console.error('Failed to load owners:', err);
        }
    }

    async function initScorePolicies() {
        try {
            const resp = await fetch('/todos/score-policies');
            const policies = await resp.json();
            policies.forEach(p => {
                const opt = document.createElement('option');
                opt.value = `policy:${p.policy_id}`;
                opt.textContent = p.policy_id;
                opt.title = p.description || '';
                sortSelect.appendChild(opt);
            });
        } catch (err) {
            console.error('Failed to load score policies:', err);
        }
    }

    async function loadTodos() {
        loadBtn.disabled = true;
        loadBtn.textContent = 'Loading...';
        editPanel.style.display = 'none';
        try {
            const owner = ownerFilter.value;
            const payload = {
                status: statusFilter.value,
                owner: owner === 'all' ? undefined : owner
            };
            if (priorityFilter.value) payload.priority = priorityFilter.value;
            const resp = await fetch('/todos/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            todosData = await resp.json();
            renderTable(todosData);
        } catch (err) {
            console.error('Failed to load todos:', err);
            countEl.textContent = 'Error loading todos';
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = 'Load';
        }
    }

    // ── Bot helpers ───────────────────────────────────────────────────────────

    async function botExecute(botId, params) {
        const resp = await fetch('/bots/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bot_id: botId, params })
        });
        return resp.json();
    }

    function resolveOwnerNode(owner) {
        if (owner === 'user') return { label: 'User',    match: { handle: 'owner' } };
        return              { label: 'Persona', match: { name: owner } };
    }

    async function reassignOwner(todoId, oldOwner, newOwner) {
        const inspection = await botExecute('graph.rel.inspect', {
            node_label: 'Todo',
            node_match: { 'todo-id': todoId },
            rel_type:   'ASSIGNED',
            direction:  'incoming',
            reason:     'ui-todos-reassign',
        });
        if (inspection.error) return { error: `Inspect failed: ${inspection.error}` };

        const assigned = inspection.relationships.filter(r => r.rel_type === 'ASSIGNED');
        if (assigned.length === 0) return { error: 'No ASSIGNED relationship found on this todo' };
        if (assigned.length > 1)  return { error: `Expected 1 ASSIGNED, found ${assigned.length}` };

        const src         = assigned[0].other_properties;
        const expectedKey = oldOwner === 'user' ? 'handle' : 'name';
        const expectedVal = oldOwner === 'user' ? 'owner'  : oldOwner;
        if (src[expectedKey] !== expectedVal) {
            return { error: `ASSIGNED source mismatch - expected ${expectedKey}=${expectedVal}, found ${JSON.stringify(src)}` };
        }

        const oldNode = resolveOwnerNode(oldOwner);
        const newNode = resolveOwnerNode(newOwner);
        const reroute = await botExecute('graph.rel.reroute', {
            fixed_label: 'Todo',       fixed_match: { 'todo-id': todoId },
            old_label:   oldNode.label, old_match:   oldNode.match,
            new_label:   newNode.label, new_match:   newNode.match,
            rel_type:    'ASSIGNED',
            direction:   'incoming',
            reason:      'ui-todos-reassign',
        });
        if (reroute.error) return { error: `Reroute failed: ${reroute.error}` };

        return { status: 'ok' };
    }

    // ── Event listeners ───────────────────────────────────────────────────────

    subCheck.addEventListener('change', () => {
        if (subCheck.checked) {
            subParentLabel.textContent = currentTodoId;
            subPanel.style.display = 'block';
            subPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            subDesc.focus();
            saveBtn.disabled = false;
        } else {
            subPanel.style.display = 'none';
        }
    });

    newBtn.addEventListener('click', openCreatePanel);
    ownerFilter.addEventListener('change', loadTodos);
    loadBtn.addEventListener('click', loadTodos);
    sortSelect.addEventListener('change', () => renderTable(todosData));

    initOwnerFilter();
    initScorePolicies();

    saveBtn.addEventListener('click', async () => {
        if (panelMode === 'create') {
            if (!editDesc.value.trim()) {
                saveMsg.textContent = 'Description is required';
                saveMsg.style.color = '#e53935';
                return;
            }
            saveBtn.disabled = true;
            saveMsg.textContent = 'Creating...';
            saveMsg.style.color = '#888';
            try {
                const result = await botExecute('vera.todos.create', {
                    description: editDesc.value.trim(),
                    status:      editStatus.value,
                    priority:    editPriority.value,
                    friction:    editFriction.value || null,
                    due:         editDue.value || null,
                    notes:       editNotes.value || null,
                    owner:       editOwner.value || 'user',
                    made_by:     'user',
                    reason:      'ui-todos-create',
                });
                if (result.error) {
                    saveMsg.textContent = `Error: ${result.error}`;
                    saveMsg.style.color = '#e53935';
                    saveBtn.disabled = false;
                } else {
                    saveMsg.textContent = `Created: ${result['todo-id']}`;
                    saveMsg.style.color = '#43a047';
                    const newTodo = {
                        id:          result['todo-id'],
                        description: result.description,
                        status:      result.status,
                        priority:    result.priority,
                        friction:    result.friction || null,
                        due:         result.due || null,
                        notes:       result.notes || null,
                        owner:       result.owner,
                        created:     result.created,
                        score:       null,
                        nudge:       false,
                    };
                    todosData.unshift(newTodo);
                    renderTable(todosData);
                    panelMode = null;
                    editPanel.style.display = 'none';
                }
            } catch (err) {
                saveMsg.textContent = `Error: ${err.message}`;
                saveMsg.style.color = '#e53935';
                saveBtn.disabled = false;
            }
            return;
        }

        // ── Edit mode ─────────────────────────────────────────────────────────
        if (!currentTodoId) return;
        saveBtn.disabled = true;
        saveMsg.textContent = 'Saving...';
        saveMsg.style.color = '#888';

        const newOwner     = editOwner.value || 'user';
        const ownerChanged = newOwner !== currentOwner;
        if (ownerChanged) {
            saveMsg.textContent = 'Rewiring assignment...';
            const reassign = await reassignOwner(currentTodoId, currentOwner, newOwner);
            if (reassign.error) {
                saveMsg.textContent = `Reassign failed: ${reassign.error}`;
                saveMsg.style.color = '#e53935';
                saveBtn.disabled = false;
                return;
            }
        }

        const updates = {
            description: editDesc.value,
            status:      editStatus.value,
            priority:    editPriority.value,
            friction:    editFriction.value || null,
            due:         editDue.value || null,
            notes:       editNotes.value || null,
            owner:       editOwner.value || 'user',
        };

        try {
            const resp = await fetch('/todos/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ todo_id: currentTodoId, updates })
            });
            const result = await resp.json();
            if (result.error) {
                saveMsg.textContent = `Error: ${result.error}`;
                saveMsg.style.color = '#e53935';
                saveBtn.disabled = false;
            } else {
                saveMsg.textContent = 'Saved';
                saveMsg.style.color = '#43a047';
                editDirty = false;
                const idx = todosData.findIndex(t => t.id === currentTodoId);
                if (idx >= 0) todosData[idx] = { ...todosData[idx], ...result };
                renderTable(todosData);
                const row = document.querySelector(`#todo-table-body tr[data-id="${currentTodoId}"]`);
                if (row) { row.classList.remove('row-edited'); row.classList.add('row-saved'); }

                if (subCheck.checked) {
                    if (!subDesc.value.trim()) {
                        saveMsg.textContent = 'Saved (sub-todo skipped: description required)';
                        saveMsg.style.color = '#e67e22';
                        return;
                    }
                    saveMsg.textContent = 'Creating sub-todo...';
                    saveMsg.style.color = '#888';
                    const subResult = await botExecute('vera.todos.create', {
                        description:  subDesc.value.trim(),
                        status:       'open',
                        priority:     subPriority.value,
                        friction:     subFriction.value || null,
                        due:          subDue.value || null,
                        notes:        subNotes.value || null,
                        owner:        subOwner.value || 'user',
                        made_by:      'user',
                        follows_from: currentTodoId,
                        reason:       'ui-todos-sub-create',
                    });
                    if (subResult.error) {
                        saveMsg.textContent = `Saved, but sub-todo failed: ${subResult.error}`;
                        saveMsg.style.color = '#e53935';
                    } else {
                        saveMsg.textContent = `Saved + sub-todo created: ${subResult['todo-id']}`;
                        saveMsg.style.color = '#43a047';
                        const newTodo = {
                            id:          subResult['todo-id'],
                            description: subResult.description,
                            status:      subResult.status,
                            priority:    subResult.priority,
                            friction:    subResult.friction || null,
                            due:         subResult.due || null,
                            notes:       subResult.notes || null,
                            owner:       subResult.owner,
                            created:     subResult.created,
                            score:       null,
                            nudge:       false,
                        };
                        todosData.unshift(newTodo);
                        renderTable(todosData);
                        subCheck.checked       = false;
                        subPanel.style.display = 'none';
                    }
                }
            }
        } catch (err) {
            saveMsg.textContent = `Error: ${err.message}`;
            saveMsg.style.color = '#e53935';
            saveBtn.disabled = false;
        }
    });

    cancelBtn.addEventListener('click', () => {
        editPanel.style.display  = 'none';
        subPanel.style.display   = 'none';
        subCheck.checked         = false;
        subCheckWrap.style.display = 'none';
        currentTodoId = null;
        panelMode     = null;
        document.querySelectorAll('#todo-table-body tr').forEach(r => r.classList.remove('row-edited'));
    });

})();
