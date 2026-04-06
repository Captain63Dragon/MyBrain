// <script src="{{ url_for('static', filename='js/review_filenode.js') }}"></script>
import { initContentTabs } from './review_filenode.js';
let mfnListLoaded = false;

// Moved from inline script in app/templates/base.html
document.addEventListener('DOMContentLoaded', function() {
    initContentTabs();
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            const serviceKey = this.dataset.service;

            // Update active state
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            this.classList.add('active');

            // Panels in the page
            const panels = ['content-banner', 'content-review', 'content-search'];
            panels.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });

            // Show the requested panel (default to banner)
            if (serviceKey === 'review_filenode') {
                const el = document.getElementById('content-review');
                if (el) el.style.display = 'block';
                if (!mfnListLoaded) {
                    loadMfnList();
                    mfnListLoaded = true;
                }
                // initialize tabs for the included fragment
            } else if (serviceKey === 'search_database') {
                const el = document.getElementById('content-search');
                if (el) el.style.display = 'block';
            } else {
                const el = document.getElementById('content-banner');
                if (el) el.style.display = 'block';
            }
        });
    });
});

async function loadMfnList() {
    const select = document.getElementById('mfnSelect');
    if (!select) return;

    try {
        const response = await fetch('/mfn/list');
        const mfns = await response.json();

        select.innerHTML = '';
        mfns.forEach(mfn => {
            const option = document.createElement('option');
            option.value = mfn.id;
            option.textContent = mfn.name;
            select.appendChild(option);
        });

        // Restore last selection from localStorage
        const lastMfnId = localStorage.getItem('lastMfnId');
        if (lastMfnId) {
            select.value = lastMfnId;
        }

        // Populate Node Path from localStorage
        const defaultSearchPath = localStorage.getItem('defaultSearchPath');
        const nodePathInput = document.getElementById('nodePathInput');
        if (nodePathInput && defaultSearchPath) {
            nodePathInput.value = defaultSearchPath;
        }

    } catch (err) {
        console.error('Failed to load MFN list:', err);
        select.innerHTML = '<option value="">Error loading MFNs</option>';
    }
}