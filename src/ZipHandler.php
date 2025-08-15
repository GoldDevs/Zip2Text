<?php

namespace Zip2Text;

use ZipArchive;

class ZipHandler
{
    private string $job_id;
    private EventLogger $logger;

    public function __construct(string $job_id, EventLogger $logger)
    {
        $this->job_id = $job_id;
        $this->logger = $logger;
    }

    /**
     * Handles the extraction of the zip file.
     *
     * @param string $zip_file_path The path to the zip file.
     * @return string The path to the directory where files were extracted.
     * @throws \RuntimeException If the extraction fails.
     */
    public function handle(string $zip_file_path): string
    {
        $this->logger->emit('VALIDATION', 'INFO', 'Validating ZIP file...');

        $zip = new ZipArchive();
        $res = $zip->open($zip_file_path);

        if ($res !== true) {
            throw new \RuntimeException('Failed to open ZIP archive. Error code: ' . $res);
        }

        // Create a unique directory for extraction based on the job ID.
        $extraction_dir = sys_get_temp_dir() . '/zip2text_' . $this->job_id;
        if (!mkdir($extraction_dir, 0777, true) && !is_dir($extraction_dir)) {
            throw new \RuntimeException('Failed to create extraction directory.');
        }

        $this->logger->emit('EXTRACTION', 'INFO', 'Extracting files to temporary directory...');

        if (!$zip->extractTo($extraction_dir)) {
            $zip->close();
            throw new \RuntimeException('Failed to extract files from ZIP archive.');
        }

        $zip->close();

        $this->logger->emit('EXTRACTION', 'SUCCESS', 'Successfully extracted ' . $zip->numFiles . ' items.');

        return $extraction_dir;
    }
}
