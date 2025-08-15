<?php

namespace Zip2Text;

class ImageProcessor
{
    private string $job_id;
    private EventLogger $logger;

    // Define the list of supported image extensions.
    private const SUPPORTED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp'];

    public function __construct(string $job_id, EventLogger $logger)
    {
        $this->job_id = $job_id;
        $this->logger = $logger;
    }

    /**
     * Scans a directory for supported image files.
     *
     * @param string $directory The path to the directory to scan.
     * @return array A list of full paths to the found image files.
     */
    public function scan(string $directory): array
    {
        $this->logger->emit('IMAGE_SCAN', 'INFO', 'Scanning for supported image files...');

        $image_paths = [];
        $iterator = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($directory, \RecursiveDirectoryIterator::SKIP_DOTS)
        );

        foreach ($iterator as $file) {
            if ($file->isFile()) {
                $extension = strtolower($file->getExtension());
                if (in_array($extension, self::SUPPORTED_EXTENSIONS)) {
                    $image_paths[] = $file->getRealPath();
                }
            }
        }

        $image_count = count($image_paths);
        $this->logger->emit('IMAGE_SCAN', 'SUCCESS', "Found {$image_count} supported images.");

        return $image_paths;
    }
}
