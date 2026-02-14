// <script src="{{ url_for('static', filename='js/review_filenode.js') }}"></script>
import { initContentTabs } from './review_filenode.js';

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
