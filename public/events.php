<?php

// Set a higher time limit to keep the connection open for a while.
set_time_limit(120); // 2 minutes

// Define paths
define('LOGS_DIR', realpath(__DIR__ . '/../logs'));

// --- Helper function to send an SSE-formatted message ---
function send_sse_message(string $data): void
{
    // The SSE format is "data: {json_string}\n\n"
    echo "data: " . $data . "\n\n";
    // Flush the output buffer to make sure the message is sent immediately.
    ob_flush();
    flush();
}

// --- Main Request Handling Logic ---

// 1. Set SSE Headers
header('Content-Type: text/event-stream');
header('Cache-Control: no-cache');
header('Connection: keep-alive');

// 2. Get and Validate job_id
if (!isset($_GET['job_id'])) {
    // We can't send a normal error response here as the client expects an event stream.
    // We can send an error event and then close.
    send_sse_message(json_encode([
        'event' => 'JOB_FAILED',
        'severity' => 'ERROR',
        'message' => 'No job_id provided.',
        'timestamp' => time()
    ]));
    exit;
}

$job_id = $_GET['job_id'];

// Security: Validate the job_id format to prevent directory traversal.
// A simple regex check for a UUID format is a good measure.
if (!preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/', $job_id)) {
    send_sse_message(json_encode([
        'event' => 'JOB_FAILED',
        'severity' => 'ERROR',
        'message' => 'Invalid job_id format.',
        'timestamp' => time()
    ]));
    exit;
}

// 3. Locate and Poll the Log File
$log_file_path = LOGS_DIR . '/' . $job_id . '.log';
$file_handle = null;
$current_position = 0;
$job_is_done = false;
$start_time = time();

// Keep the script running until the job is done or we time out.
while (!$job_is_done && (time() - $start_time) < 115) { // 115s timeout, less than set_time_limit
    // Clear file status cache to get the latest size.
    clearstatcache(true, $log_file_path);

    // Check if the log file exists. It might not be created immediately by the worker.
    if (file_exists($log_file_path)) {
        if ($file_handle === null) {
            $file_handle = fopen($log_file_path, 'r');
            if ($file_handle === false) {
                // If we can't open the file, send an error and exit.
                send_sse_message(json_encode([
                    'event' => 'JOB_FAILED',
                    'severity' => 'ERROR',
                    'message' => 'Could not open log file for reading.',
                    'timestamp' => time()
                ]));
                exit;
            }
        }

        fseek($file_handle, $current_position);

        // Read new lines from the file.
        while (($line = fgets($file_handle)) !== false) {
            $line = trim($line);
            if (!empty($line)) {
                send_sse_message($line);
                // Check if the line indicates the job is finished.
                $log_data = json_decode($line, true);
                if (isset($log_data['event']) && in_array($log_data['event'], ['JOB_COMPLETED', 'JOB_FAILED', 'JOB_WARNING'])) {
                    $job_is_done = true;
                }
            }
        }

        // Update our position in the file.
        $current_position = ftell($file_handle);
    }

    // If the job is done, we can break the loop.
    if ($job_is_done) {
        break;
    }

    // Wait for a short period before polling again to avoid excessive CPU usage.
    sleep(1);
}

if ($file_handle) {
    fclose($file_handle);
}

// If the loop timed out, send a final error message.
if (!$job_is_done) {
    send_sse_message(json_encode([
        'event' => 'JOB_FAILED',
        'severity' => 'ERROR',
        'message' => 'Connection timed out waiting for job to complete.',
        'timestamp' => time()
    ]));
}
