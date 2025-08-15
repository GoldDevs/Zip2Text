<?php

namespace Zip2Text;

class TextAggregator
{
    private string $job_id;
    private EventLogger $logger;

    public function __construct(string $job_id, EventLogger $logger)
    {
        $this->job_id = $job_id;
        $this->logger = $logger;
    }

    /**
     * Aggregates OCR results from multiple images into a single text block.
     *
     * @param array $ocr_results A dictionary mapping image path to its extracted text.
     * @return string The final aggregated text.
     */
    public function aggregate(array $ocr_results): string
    {
        $this->logger->emit('AGGREGATION', 'INFO', 'Aggregating text results...');

        $final_text = '';
        $separator = "\n\n" . str_repeat('=', 80) . "\n\n";

        foreach ($ocr_results as $image_path => $text) {
            $filename = basename($image_path);
            $final_text .= "Source Image: " . $filename . "\n";
            $final_text .= str_repeat('-', strlen($filename) + 14) . "\n";
            $final_text .= trim($text) . "\n";
            $final_text .= $separator;
        }

        $this->logger->emit('AGGREGATION', 'SUCCESS', 'Text aggregation complete.');

        // Remove the last separator for a cleaner output.
        return rtrim($final_text, $separator);
    }
}
