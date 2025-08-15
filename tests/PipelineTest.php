<?php

namespace Zip2Text\Tests;

use PHPUnit\Framework\TestCase;
use Zip2Text\JobManager;
use Zip2Text\EventLogger;
use Zip2Text\VisionClient;
use ZipArchive;

// Mock the EventLogger to capture events instead of writing them to a file.
class MockEventLogger extends EventLogger
{
    public array $events = [];

    public function __construct(string $job_id)
    {
        // Don't call parent constructor, we don't want to deal with files.
    }

    public function emit(string $event_name, string $severity, string $message, ?array $data = null): void
    {
        $this->events[] = [
            'event' => $event_name,
            'severity' => $severity,
            'message' => $message,
            'data' => $data,
        ];
    }
}

// Mock the VisionClient to avoid making real API calls.
class MockVisionClient extends VisionClient
{
    public function performOcr(array $image_paths): array
    {
        $results = [];
        foreach ($image_paths as $path) {
            $filename = basename($path);
            $results[$path] = "Mocked text for {$filename}";
        }
        return $results;
    }
}

class PipelineTest extends TestCase
{
    private string $test_dir;
    private string $uploads_dir;

    protected function setUp(): void
    {
        // Create a temporary directory for test artifacts.
        $this->test_dir = sys_get_temp_dir() . '/zip2text_test_' . uniqid();
        mkdir($this->test_dir, 0777, true);
        $this->uploads_dir = $this->test_dir . '/uploads';
        mkdir($this->uploads_dir, 0777, true);
    }

    protected function tearDown(): void
    {
        // Clean up the temporary directory.
        $this->rmdir_recursive($this->test_dir);
    }

    private function createDummyZip(string $zip_name, array $files_to_add): string
    {
        $zip_path = $this->uploads_dir . '/' . $zip_name;
        $zip = new ZipArchive();
        $zip->open($zip_path, ZipArchive::CREATE);

        foreach ($files_to_add as $filename) {
            $file_path = $this->test_dir . '/' . $filename;
            file_put_contents($file_path, "dummy content");
            $zip->addFile($file_path, $filename);
        }

        $zip->close();
        return $zip_path;
    }

    public function testFullJobRun()
    {
        // 1. Setup
        $job_id = 'test-job-123';
        $zip_file_path = $this->createDummyZip($job_id . '.zip', ['image1.png', 'image2.jpg', 'document.txt']);

        $job_data = [
            'job_id' => $job_id,
            'original_filename' => 'test.zip',
            'zip_file_path' => $zip_file_path,
        ];

        // Instantiate our mock logger and vision client
        $mock_logger = new MockEventLogger($job_id);
        $mock_vision_client = new MockVisionClient($job_id, $mock_logger);

        // We need to inject the mock logger into the real JobManager.
        // The easiest way is to modify the JobManager to allow a logger instance in its constructor.
        // For now, let's just replace the logger property after construction using reflection.
        $job_manager = new JobManager($job_data, $mock_vision_client);

        $reflector = new \ReflectionObject($job_manager);
        $logger_prop = $reflector->getProperty('logger');
        $logger_prop->setAccessible(true);
        $logger_prop->setValue($job_manager, $mock_logger);

        // 2. Execution
        $job_manager->run();

        // 3. Assertions
        $events = $mock_logger->events;

        // Check that the job started and completed successfully.
        $this->assertSame('JOB_STARTED', $events[0]['event']);
        $this->assertSame('JOB_COMPLETED', end($events)['event']);
        $this->assertSame('SUCCESS', end($events)['severity']);

        // Check that the OCR results were aggregated in the final text.
        $final_text = end($events)['data']['final_text'];
        $this->assertStringContainsString('Mocked text for image1.png', $final_text);
        $this->assertStringContainsString('Mocked text for image2.jpg', $final_text);
        $this->assertStringNotContainsString('document.txt', $final_text);
    }

    private function rmdir_recursive(string $dir): void
    {
        if (!is_dir($dir)) return;
        $items = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($dir, \RecursiveDirectoryIterator::SKIP_DOTS),
            \RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($items as $item) {
            if ($item->isDir()) rmdir($item->getRealPath());
            else unlink($item->getRealPath());
        }
        rmdir($dir);
    }
}
