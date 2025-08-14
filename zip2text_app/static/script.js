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

    // --- Socket.IO Connection ---
    const socket = io();

    socket.on('connect', () => {
        console.log('Connected to server via Socket.IO');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

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

        fetch('/upload', {
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
            // Join the room for this job to receive logs
            socket.emit('join', { job_id: currentJobId });
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

    // --- Real-time Log Handler ---
    socket.on('new_log', (log) => {
        addLogEntry(log);
        updateProgressBarByEvent(log.event);

        if (log.event === 'JOB_COMPLETED') {
            finalOutput.value = log.data.final_text;
            processingCard.style.display = 'none';
            resultsCard.style.display = 'block';
        }
        if (log.event === 'JOB_FAILED' || log.event === 'JOB_WARNING') {
             // Keep processing card visible to show the error, but unhide results card to allow starting over.
            resultsCard.style.display = 'block';
            finalOutput.value = `Job ended with status: ${log.severity}\n\n${log.message}`;
        }
    });

    const addLogEntry = (log) => {
        const entry = document.createElement('span');
        entry.classList.add('log-entry', `log-severity-${log.severity}`);

        const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();

        entry.innerHTML = `<span class="timestamp">[${timestamp}]</span> <span class="severity">${log.severity}</span> ${log.message}`;
        logPanel.appendChild(entry);
        logPanel.scrollTop = logPanel.scrollHeight; // Auto-scroll
    };

    // --- UI Update Functions ---
    const updateProgressBar = (percentage) => {
        const p = Math.max(0, Math.min(100, percentage));
        progressBar.style.width = `${p}%`;
        // progressBar.textContent = `${Math.round(p)}%`;
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
        uploadCard.style.display = 'block';
        processingCard.style.display = 'none';
        resultsCard.style.display = 'none';
        uploadStatus.textContent = '';
        fileInput.value = ''; // Reset file input
        logPanel.innerHTML = '';
        updateProgressBar(0);
        currentJobId = null;
    };

    // --- Action Button Handlers ---
    copyButton.addEventListener('click', () => {
        finalOutput.select();
        navigator.clipboard.writeText(finalOutput.value).then(() => {
            copyButton.textContent = 'Copied!';
            setTimeout(() => { copyButton.textContent = 'Copy Text'; }, 2000);
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
