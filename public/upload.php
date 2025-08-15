<?php

// Include the Composer autoloader to get access to vendor libraries.
require __DIR__ . '/../vendor/autoload.php';

use Ramsey\Uuid\Uuid;

// Define paths for our data directories. Using realpath to get canonicalized absolute paths.
define('UPLOADS_DIR', realpath(__DIR__ . '/../uploads'));
define('JOBS_DIR', realpath(__DIR__ . '/../jobs'));

// --- Helper function to send a JSON error response and exit ---
function send_json_error(string $message, int $statusCode = 400): void
{
    header('Content-Type: application/json');
    http_response_code($statusCode);
    echo json_encode(['error' => $message]);
    exit;
}

// --- Main Request Handling Logic ---

// 1. Basic Security Checks
// Only allow POST requests.
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json_error('Invalid request method.', 405);
}

// Check if a file was uploaded.
if (!isset($_FILES['file'])) {
    send_json_error('No file part in the request.');
}

$file = $_FILES['file'];

// Check for upload errors.
if ($file['error'] !== UPLOAD_ERR_OK) {
    send_json_error('File upload error: ' . $file['error']);
}

// Check if a file was actually selected.
if (empty($file['name'])) {
    send_json_error('No file selected.');
}

// 2. File Validation
$fileExtension = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
if ($fileExtension !== 'zip') {
    send_json_error('Invalid file type. Please upload a .zip file.');
}

// It's also a good practice to check the MIME type.
$finfo = new finfo(FILEINFO_MIME_TYPE);
$mimeType = $finfo->file($file['tmp_name']);
if ($mimeType !== 'application/zip') {
    send_json_error('Invalid MIME type. Please upload a valid .zip file.');
}

// 3. Process the Upload
try {
    // Generate a unique ID for the job.
    $job_id = Uuid::uuid4()->toString();

    // Create a secure filename and the full path to save the file.
    // The uploaded file will be named after the job ID to avoid conflicts and keep it simple.
    $save_path = UPLOADS_DIR . '/' . $job_id . '.zip';

    // Move the uploaded file from its temporary location to our uploads directory.
    if (!move_uploaded_file($file['tmp_name'], $save_path)) {
        throw new RuntimeException('Failed to move uploaded file.');
    }

    // 4. Create the Job File
    // The job file will contain the necessary info for the worker to process the job.
    $job_data = [
        'job_id' => $job_id,
        'original_filename' => basename($file['name']), // Use basename for security
        'zip_file_path' => $save_path,
        'status' => 'pending',
        'submitted_at' => time(),
    ];

    // Create the job file in the 'jobs' directory.
    $job_file_path = JOBS_DIR . '/' . $job_id . '.json';
    if (file_put_contents($job_file_path, json_encode($job_data, JSON_PRETTY_PRINT)) === false) {
        // If we can't create the job file, we should clean up the uploaded file.
        unlink($save_path);
        throw new RuntimeException('Failed to create job file.');
    }

    // 5. Send Success Response
    // If everything is successful, return the job_id to the client.
    header('Content-Type: application/json');
    echo json_encode(['job_id' => $job_id]);

} catch (Exception $e) {
    // Catch any exception during the process and return a server error.
    // In a real application, you would want to log this error.
    send_json_error('An internal server error occurred: ' . $e->getMessage(), 500);
}
