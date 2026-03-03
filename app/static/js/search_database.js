document.addEventListener('DOMContentLoaded', function() {

    // document.getElementById('searchForm').addEventListener('submit', async (e) => {
    //     e.preventDefault();
    //     const formData = new FormData(e.target);
    //     const response = await fetch('/submit/search_database', {
    //         method: 'POST',
    //         body: formData
    //     });
    //     const data = await response.json();
    //     const msg = document.getElementById('message');
    //     msg.textContent = JSON.stringify(data, null, 2);
    //     msg.style.display = 'block';
    //     msg.style.background = '#d4edda';
    //     msg.style.color = '#155724';
    // });

    document.getElementById('btn-discovery-scan').addEventListener('click', async (e) => {
        e.preventDefault();
        
        const actionType = document.querySelector('[name="action_type"]').value;
        
        if (actionType === 'discovery_scan') {
            const r1 = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:   'discovery',
                    source:   'C:\\Users\\termi\\MyBrain-test\\',
                    mfn_id:   'BusinessCard_20260121',
                    patterns: ['busCard', 'BusCard', 'Buscard', 'busCardish'],
                })
            });
            const r2 = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:   'discovery',
                    source:   'C:\\Users\\termi\\MyBrain-test-backup\\',
                    mfn_id:   'BusinessCard_20260121',
                    patterns: ['busCard', 'BusCard', 'Buscard', 'busCardish'],
                })
            });
            console.log("scan 1:", await r1.json());
            console.log("scan 2:", await r2.json());

        } else if (actionType === 'discovery_process') {
            const response = await fetch('/buscard/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'discovery' })
            });
            const result = await response.json();
            console.log("discovery process", result);

        } else if (actionType === 'insitu_copy') {
            const response = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:  'insitu_copy',
                    source:  'C:\\Users\\termi\\MyBrain-test\\2026_0101-busCard-test-beta.pdf',
                    target:  'C:\\Users\\termi\\MyBrain-test-archive\\2026_0101-busCard-test-beta.pdf',
                    node_id: 'buscard-test-beta_20260101',
                    mfn_id:  'BusinessCard_20260121',
                })
            });
            const result = await response.json();
            console.log("insitu_copy queued", result);

        } else if (actionType === 'insitu_process') {
            const response = await fetch('/buscard/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'copy' })
            });
            const result = await response.json();
            console.log("insitu process", result);

        } else if (actionType === 'copy_master_source') {
            const response = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:  'copy_master_source',
                    source:  'C:\\Users\\termi\\MyBrain-test\\2026_0101-busCard-test-epsilon.pdf',
                    target:  'C:\\Users\\termi\\MyBrain-test-archive\\2026_0101-busCard-test-epsilon.pdf',
                    node_id: 'buscard-test-epsilon_20260101',
                    mfn_id:  'BusinessCard_20260121',
                })
            });
            const result = await response.json();
            console.log("copy master source queued", result);
            const response2 = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:  'copy_master_source',
                    source:  'C:\\Users\\termi\\MyBrain-test\\2026_0101-busCard-test-epsilon.pdf',
                    target:  'C:\\Users\\termi\\MyBrain-test-backup\\2026_0101-busCard-test-epsilon.pdf',
                    node_id: 'buscard-test-epsilon_20260101',
                    mfn_id:  'BusinessCard_20260121',
                })
            });
            console.log("copy master source 2 queued", await response2.json());

        } else if (actionType === 'copy_master_target') {
            const response = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:  'copy_master_target',
                    source:  'C:\\Users\\termi\\MyBrain-test-backup\\2026_0101-busCard-test-zeta.pdf',
                    target:  'C:\\Users\\termi\\MyBrain-test-archive\\2026_0101-busCard-test-zeta.pdf',
                    node_id: 'buscard-test-zeta_20260101',
                    mfn_id:  'BusinessCard_20260121',
                })
            });
            const result = await response.json();
            console.log("copy master target queued", result);

        } else if (actionType === 'process_copy') {
            const response = await fetch('/buscard/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'copy' })
            });
            const result = await response.json();
            console.log("copy process", result);

        } else if (actionType === 'move') {
            const response = await fetch('/buscard/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action:  'move',
                    source:  'C:\\Users\\termi\\MyBrain-test\\2026_0101-busCard-test-gamma.pdf',
                    target:  'C:\\Users\\termi\\MyBrain-test-backup\\2026_0101-busCard-test-gamma.pdf',
                    node_id: 'buscard-test-gamma_20260101',
                    mfn_id:  'BusinessCard_20260121',
                })
            });
            const result = await response.json();
            console.log("move queued", result);

        } else if (actionType === 'process_move') {
            const response = await fetch('/buscard/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'move' })
            });
            const result = await response.json();
            console.log("move processed", result);

        } else {
            console.log("no action type selected");
        }
    });   
});

