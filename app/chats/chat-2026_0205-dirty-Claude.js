// ******** Using a Map object to relate a Form to a boolean representing dirty status. ******

// At the top level of your script, outside any functions
const formDirtyStates = new Map();  // so I think in review_filenode.js

// Now all your event handlers can access it
container.addEventListener('change', (e) => {
    const form = e.target.closest('form');
    if (form) {
        formDirtyStates.set(form, true);
        const saveBtn = form.querySelector('.btn-primary');
        saveBtn.disabled = false;
    }
});

// Check dirty forms from anywhere
function hasUnsavedChanges() {
    return Array.from(formDirtyStates.values()).some(dirty => dirty);
}

// Find which forms are dirty
function getDirtyForms() {
    return Array.from(formDirtyStates.entries())
        .filter(([form, isDirty]) => isDirty)
        .map(([form, isDirty]) => form);
}

// Before switching tabs or closing
if (hasUnsavedChanges()) {
    if (!confirm('You have unsaved changes. Continue?')) {
        // Cancel navigation
    }
}