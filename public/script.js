document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selection ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const uploadCard = document.getElementById('upload-card');
    const processingCard = document.getElementById('processing-card');
    const resultsCard = document.getElementById('results-card');
    const logPanel = document.getElementById('log-panel');
    const progressBar = document.getElementById('progress-bar');
    const finalOutput = document.getElementById('final-text-output');
    const copyButton = document.getElementById('copy-button');
    const downloadButton = document.getElementById('download-button');
    const startOverButton = document.getElementById('start-over-button');

    let currentJobId = null;
    let eventSource = null;

    // --- Core Upload Logic ---
    const uploadFile = (file) => {
        if (!file || !file.name.endsWith('.zip')) {
            uploadStatus.textContent = 'Error: Please select a .zip file.';
            uploadStatus.style.color = 'var(--error-color)';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Update UI to processing state
        uploadStatus.textContent = `Uploading ${file.name}...`;
        uploadCard.style.display = 'none';
        processingCard.style.display = 'block';
        logPanel.innerHTML = ''; // Clear previous logs
        updateProgressBar(0);

        fetch('/upload.php', {
            method: 'POST',
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            currentJobId = data.job_id;
            console.log(`Job started with ID: ${currentJobId}`);
            // Start listening for Server-Sent Events
            startEventSource(currentJobId);
        })
        .catch(error => {
            console.error('Upload error:', error);
            addLogEntry({
                severity: 'ERROR',
                message: `Upload failed: ${error.message}`
            });
            resetUI();
        });
    };

    // --- Drag and Drop Event Handlers ---
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        uploadFile(file);
    });

    // --- File Input Handler ---
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        uploadFile(file);
    });

    // --- Server-Sent Events (SSE) Logic ---
    const startEventSource = (jobId) => {
        eventSource = new EventSource(`/events.php?job_id=${jobId}`);

        eventSource.onmessage = (event) => {
            // The server will send JSON data
            const log = JSON.parse(event.data);
            addLogEntry(log);
            updateProgressBarByEvent(log.event);

            if (log.event === 'JOB_COMPLETED') {
                finalOutput.value = log.data.final_text;
                processingCard.style.display = 'none';
                resultsCard.style.display = 'block';
                eventSource.close(); // We're done, so close the connection
            }
            if (log.event === 'JOB_FAILED' || log.event === 'JOB_WARNING') {
                resultsCard.style.display = 'block';
                finalOutput.value = `Job ended with status: ${log.severity}\n\n${log.message}`;
                eventSource.close(); // We're done, so close the connection
            }
        };

        eventSource.onerror = (err) => {
            console.error('EventSource failed:', err);
            addLogEntry({
                severity: 'ERROR',
                message: 'Connection to server lost. Please try again.'
            });
            eventSource.close();
        };
    };

    const addLogEntry = (log) => {
        const entry = document.createElement('span');
        // Materialize colors for severities
        const severityColors = {
            'INFO': 'white-text',
            'SUCCESS': 'green-text text-lighten-2',
            'WARNING': 'yellow-text text-lighten-2',
            'ERROR': 'red-text text-lighten-2',
        };
        const severityClass = severityColors[log.severity] || 'white-text';

        const timestamp = log.timestamp ? new Date(log.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();

        entry.innerHTML = `<span class="grey-text">[${timestamp}]</span> <span class="strong ${severityClass}" style="font-weight:bold;">${log.severity}</span>: ${log.message}`;
        logPanel.appendChild(entry);
        logPanel.appendChild(document.createElement('br'));
        logPanel.scrollTop = logPanel.scrollHeight; // Auto-scroll
    };

    // --- UI Update Functions ---
    const updateProgressBar = (percentage) => {
        const p = Math.max(0, Math.min(100, percentage));
        progressBar.style.width = `${p}%`;
    };

    const updateProgressBarByEvent = (event) => {
        const eventProgress = {
            'JOB_STARTED': 5,
            'VALIDATION': 10,
            'EXTRACTION': 20,
            'IMAGE_SCAN': 40,
            'OCR_PIPELINE': 60,
            'AGGREGATION': 95,
            'JOB_COMPLETED': 100,
            'JOB_FAILED': 100,
        };
        if (event in eventProgress) {
            updateProgressBar(eventProgress[event]);
        }
    };

    const resetUI = () => {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        uploadCard.style.display = 'block';
        processingCard.style.display = 'none';
        resultsCard.style.display = 'none';
        uploadStatus.textContent = '';
        fileInput.value = '';
        logPanel.innerHTML = '';
        updateProgressBar(0);
        currentJobId = null;
    };

    // --- Action Button Handlers ---
    copyButton.addEventListener('click', () => {
        finalOutput.select();
        navigator.clipboard.writeText(finalOutput.value).then(() => {
            M.toast({html: 'Copied to clipboard!'})
        });
    });

    downloadButton.addEventListener('click', () => {
        const blob = new Blob([finalOutput.value], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr_results_${currentJobId || 'export'}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    startOverButton.addEventListener('click', resetUI);
});
