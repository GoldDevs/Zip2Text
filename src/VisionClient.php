<?php

namespace Zip2Text;

use Google\Cloud\Vision\V1\ImageAnnotatorClient;
use Google\ApiCore\ApiException;

class VisionClient
{
    private string $job_id;
    private EventLogger $logger;
    private ?ImageAnnotatorClient $client = null;

    public function __construct(string $job_id, EventLogger $logger)
    {
        $this->job_id = $job_id;
        $this->logger = $logger;
    }

    /**
     * Initializes the Vision API client using credentials from an environment variable.
     * @throws \RuntimeException if credentials are not set or are invalid.
     */
    private function initializeClient(): void
    {
        if ($this->client) {
            return;
        }

        $credentialsJson = getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON');
        if (empty($credentialsJson)) {
            throw new \RuntimeException('GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.');
        }

        try {
            $credentials = json_decode($credentialsJson, true);
            if (json_last_error() !== JSON_ERROR_NONE) {
                throw new \RuntimeException('Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON.');
            }

            $this->client = new ImageAnnotatorClient([
                'credentials' => $credentials
            ]);

        } catch (\Exception $e) {
            throw new \RuntimeException('Failed to initialize Google Vision client: ' . $e->getMessage());
        }
    }

    /**
     * Performs OCR on a list of images.
     *
     * @param array $image_paths List of full paths to image files.
     * @return array A dictionary mapping image path to its extracted text.
     */
    public function performOcr(array $image_paths): array
    {
        $total_images = count($image_paths);
        $this->logger->emit('OCR_PIPELINE', 'INFO', "Starting OCR process for {$total_images} images...");

        try {
            $this->initializeClient();
        } catch (\RuntimeException $e) {
            // This is a critical failure. Log it and re-throw to stop the job.
            $this->logger->emit('OCR_PIPELINE', 'ERROR', 'Configuration error: Could not initialize Vision API. Please check server credentials.');
            throw $e;
        }

        $ocr_results = [];
        foreach ($image_paths as $index => $image_path) {
            $filename = basename($image_path);
            $current_num = $index + 1;
            $this->logger->emit('OCR_STARTED', 'INFO', "({$current_num}/{$total_images}) Processing: {$filename}");

            try {
                $image_content = file_get_contents($image_path);
                if ($image_content === false) {
                    throw new \Exception("Could not read image file content.");
                }

                $response = $this->client->documentTextDetection($image_content);
                $annotation = $response->getFullTextAnnotation();

                if ($annotation) {
                    $ocr_results[$image_path] = $annotation->getText();
                    $this->logger->emit('OCR_SUCCESS', 'SUCCESS', "({$current_num}/{$total_images}) Successfully processed: {$filename}");
                } else {
                    // This can happen if the image has no text.
                    $ocr_results[$image_path] = '';
                    $this->logger->emit('OCR_SUCCESS', 'INFO', "({$current_num}/{$total_images}) Processed (no text found): {$filename}");
                }

            } catch (ApiException $e) {
                $error_message = "API Error processing image {$filename}: " . $e->getMessage();
                $this->logger->emit('OCR_FAILED', 'ERROR', $error_message);
                $ocr_results[$image_path] = "[Error: " . $e->getBasicMessage() . "]";
            } catch (\Exception $e) {
                $error_message = "General Error processing image {$filename}: " . $e->getMessage();
                $this->logger->emit('OCR_FAILED', 'ERROR', $error_message);
                $ocr_results[$image_path] = "[Error: " . $e->getMessage() . "]";
            }
        }

        $this->logger->emit('OCR_PIPELINE', 'SUCCESS', 'Finished processing all images.');
        return $ocr_results;
    }

    public function __destruct()
    {
        if ($this->client) {
            $this->client->close();
        }
    }
}
