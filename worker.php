<?php

// The worker should be run from the command line, not a web browser.
if (php_sapi_name() !== 'cli') {
    die("This script can only be run from the command line.");
}

// Set a long execution time, or unlimited. 0 means no time limit.
set_time_limit(0);

// Include Composer's autoloader
require __DIR__ . '/vendor/autoload.php';

// Define paths
define('JOBS_DIR', realpath(__DIR__ . '/jobs'));
define('UPLOADS_DIR', realpath(__DIR__ . '/uploads'));

echo "Starting Zip2Text worker...\n";
echo "Monitoring directory: " . JOBS_DIR . "\n";

// --- Main Worker Loop ---
// This loop will run indefinitely. In a real production environment,
// you would use a process manager like Supervisor or systemd to ensure
// this script is always running.
while (true) {
    // Scan the jobs directory for new job files.
    $job_files = glob(JOBS_DIR . '/*.json');

    if (empty($job_files)) {
        // If there are no jobs, wait for a bit before checking again.
        sleep(5);
        continue;
    }

    foreach ($job_files as $job_file) {
        $processing_file = $job_file . '.processing';

        // --- Claim the Job ---
        // We rename the file to "claim" it. This is a simple locking mechanism
        // to prevent multiple workers from processing the same job.
        if (rename($job_file, $processing_file)) {
            echo "Processing job: " . basename($job_file) . "\n";

            // Read the job data.
            $job_data_json = file_get_contents($processing_file);
            $job_data = json_decode($job_data_json, true);

            if (json_last_error() !== JSON_ERROR_NONE || !isset($job_data['job_id'])) {
                echo "Error: Invalid job data in " . basename($job_file) . ". Skipping.\n";
                // Optionally, move to a 'failed' directory instead of deleting.
                unlink($processing_file);
                continue;
            }

            $original_zip_path = UPLOADS_DIR . '/' . $job_data['job_id'] . '.zip';

            try {
                // --- Run the Job ---
                // Instantiate the JobManager and run the pipeline.
                $job_manager = new Zip2Text\JobManager($job_data);
                $job_manager->run();
                echo "Finished job: " . $job_data['job_id'] . "\n";

            } catch (Exception $e) {
                // This would catch any fatal error not handled within the JobManager.
                echo "FATAL ERROR processing job " . $job_data['job_id'] . ": " . $e->getMessage() . "\n";
                // We should still try to clean up.
            } finally {
                // --- Clean Up ---
                // Delete the .processing file.
                if (file_exists($processing_file)) {
                    unlink($processing_file);
                }
                // Delete the original uploaded zip file.
                if (file_exists($original_zip_path)) {
                    unlink($original_zip_path);
                }
                echo "Cleaned up for job: " . $job_data['job_id'] . "\n";
            }
        }
    }

    // A short sleep at the end of the loop to prevent 100% CPU usage if
    // there's a continuous stream of jobs.
    sleep(2);
}
