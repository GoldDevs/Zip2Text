<?php

namespace Zip2Text;

// This will require all the other pipeline components.
require_once __DIR__ . '/EventLogger.php';
require_once __DIR__ . '/ZipHandler.php';
require_once __DIR__ . '/ImageProcessor.php';
require_once __DIR__ . '/VisionClient.php';
require_once __DIR__ . '/TextAggregator.php';

class JobManager
{
    private array $job_data;
    private EventLogger $logger;
    private ?VisionClient $vision_client_override;

    public function __construct(array $job_data, ?VisionClient $vision_client_override = null)
    {
        $this->job_data = $job_data;
        $this->logger = new EventLogger($job_data['job_id']);
        $this->vision_client_override = $vision_client_override;
    }

    public function run(): void
    {
        $job_id = $this->job_data['job_id'];
        $zip_file_path = $this->job_data['zip_file_path'];
        $extracted_dir = null;

        try {
            $this->logger->emit('JOB_STARTED', 'INFO', 'Processing new job for file: ' . $this->job_data['original_filename']);

            // 1. Handle Zip File
            $zip_handler = new ZipHandler($job_id, $this->logger);
            $extracted_dir = $zip_handler->handle($zip_file_path);

            // 2. Scan for Images
            $image_processor = new ImageProcessor($job_id, $this->logger);
            $image_paths = $image_processor->scan($extracted_dir);

            if (empty($image_paths)) {
                $this->logger->emit('JOB_WARNING', 'WARNING', 'Process complete. No supported image files (.jpg, .png, .webp) were found.');
                // If no images, the job is done but not a failure.
                $this->cleanup($extracted_dir);
                return;
            }

            // 3. Perform OCR
            // Use the override if it exists, otherwise create a new client.
            $vision_client = $this->vision_client_override ?? new VisionClient($job_id, $this->logger);
            $ocr_results = $vision_client->performOcr($image_paths);

            // 4. Aggregate Text
            $text_aggregator = new TextAggregator($job_id, $this->logger);
            $final_text = $text_aggregator->aggregate($ocr_results);

            // 5. Job Completed
            $this->logger->emit('JOB_COMPLETED', 'SUCCESS', 'Successfully processed all images.', [
                'final_text' => $final_text
            ]);

        } catch (\Exception $e) {
            $this->logger->emit('JOB_FAILED', 'ERROR', 'An unexpected error occurred: ' . $e->getMessage());

        } finally {
            // 6. Cleanup
            $this->cleanup($extracted_dir);
        }
    }

    private function cleanup(?string $extracted_dir): void
    {
        // Clean up the temporary extracted directory
        if ($extracted_dir && is_dir($extracted_dir)) {
            // A recursive delete function is needed here.
            $this->rmdir_recursive($extracted_dir);
        }
    }

    /**
     * Recursively deletes a directory and its contents.
     */
    private function rmdir_recursive(string $dir): void
    {
        if (!is_dir($dir)) {
            return;
        }

        $items = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($dir, \RecursiveDirectoryIterator::SKIP_DOTS),
            \RecursiveIteratorIterator::CHILD_FIRST
        );

        foreach ($items as $item) {
            if ($item->isDir()) {
                rmdir($item->getRealPath());
            } else {
                unlink($item->getRealPath());
            }
        }

        rmdir($dir);
    }
}
