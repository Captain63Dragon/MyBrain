document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('searchForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const response = await fetch('/submit/search_database', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        const msg = document.getElementById('message');
        msg.textContent = JSON.stringify(data, null, 2);
        msg.style.display = 'block';
        msg.style.background = '#d4edda';
        msg.style.color = '#155724';
    });
});