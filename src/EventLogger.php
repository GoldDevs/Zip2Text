<?php

namespace Zip2Text;

class EventLogger
{
    private string $log_file_path;
    private string $job_id;

    public function __construct(string $job_id)
    {
        $this->job_id = $job_id;
        $this->log_file_path = realpath(__DIR__ . '/../logs') . '/' . $job_id . '.log';
    }

    /**
     * Emits a structured log event to the job's log file.
     *
     * @param string $event_name A machine-readable event name (e.g., 'JOB_STARTED').
     * @param string $severity 'INFO', 'SUCCESS', 'WARNING', 'ERROR'.
     * @param string $message A human-readable message.
     * @param array|null $data Optional additional data to include in the log.
     */
    public function emit(string $event_name, string $severity, string $message, ?array $data = null): void
    {
        $log_entry = [
            'job_id' => $this->job_id,
            'event' => $event_name,
            'severity' => strtoupper($severity),
            'message' => $message,
            'timestamp' => time(),
            'data' => $data,
        ];

        // JSON_UNESCAPED_SLASHES is good practice for file paths.
        $json_string = json_encode($log_entry, JSON_UNESCAPED_SLASHES);

        // Append the log entry as a new line in the log file.
        // The FILE_APPEND flag is crucial to avoid overwriting the file.
        // The LOCK_EX flag prevents other processes from writing to the file at the same time.
        file_put_contents($this->log_file_path, $json_string . PHP_EOL, FILE_APPEND | LOCK_EX);
    }
}
