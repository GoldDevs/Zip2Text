import unittest
import os
import tempfile
import shutil
import zipfile
from unittest.mock import MagicMock

# Add the project root to the python path to allow imports from the 'zip2text_app' package
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to be tested
from zip2text_app.pipeline.zip_handler import handle_zip_file
from zip2text_app.pipeline.image_processor import scan_for_images
from zip2text_app.pipeline.text_aggregator import aggregate_text_results
from zip2text_app.pipeline.job_manager import run_job
from unittest.mock import patch


class TestPipeline(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and mock objects before each test."""
        self.test_dir = tempfile.mkdtemp()

        # Create a mock event streamer
        self.mock_streamer = MagicMock()
        self.mock_streamer.emit_event = MagicMock()

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir)

    def _create_dummy_zip(self, zip_name, files_to_add):
        """Helper function to create a dummy zip file."""
        zip_path = os.path.join(self.test_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for file_path, file_content in files_to_add.items():
                full_path = os.path.join(self.test_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(file_content)
                zf.write(full_path, arcname=file_path)
        return zip_path

    def test_handle_zip_file_success(self):
        """Test that a valid zip file is extracted correctly."""
        files = {'image.png': 'dummy_content', 'text.txt': 'hello'}
        zip_path = self._create_dummy_zip('test.zip', files)

        extracted_dir = handle_zip_file(zip_path, 'job1', self.mock_streamer)

        self.assertIsNotNone(extracted_dir)
        self.assertTrue(os.path.isdir(extracted_dir))
        self.assertTrue(os.path.exists(os.path.join(extracted_dir, 'image.png')))
        self.assertTrue(os.path.exists(os.path.join(extracted_dir, 'text.txt')))
        shutil.rmtree(extracted_dir)

    def test_handle_zip_file_invalid(self):
        """Test that an invalid file raises a ValueError."""
        invalid_file_path = os.path.join(self.test_dir, 'invalid.txt')
        with open(invalid_file_path, 'w') as f:
            f.write('this is not a zip file')

        with self.assertRaises(ValueError):
            handle_zip_file(invalid_file_path, 'job2', self.mock_streamer)

    def test_scan_for_images(self):
        """Test that image scanning correctly identifies and sorts image files."""
        # Create a dummy directory structure
        img_dir = os.path.join(self.test_dir, 'images')
        os.makedirs(img_dir)
        # Create dummy files
        with open(os.path.join(img_dir, 'b_image.png'), 'w') as f: f.write('d')
        with open(os.path.join(img_dir, 'a_image.jpg'), 'w') as f: f.write('d')
        with open(os.path.join(img_dir, 'c_image.webp'), 'w') as f: f.write('d')
        with open(os.path.join(img_dir, 'document.txt'), 'w') as f: f.write('d')

        image_paths, count = scan_for_images(img_dir, 'job3', self.mock_streamer)

        self.assertEqual(count, 3)
        self.assertEqual(len(image_paths), 3)
        # Check for correct sorting
        self.assertTrue(image_paths[0].endswith('a_image.jpg'))
        self.assertTrue(image_paths[1].endswith('b_image.png'))
        self.assertTrue(image_paths[2].endswith('c_image.webp'))

    def test_aggregate_text_results(self):
        """Test that text aggregation works in the correct order."""
        sorted_paths = ['path/to/page1.png', 'path/to/page2.png']
        results = {
            'path/to/page2.png': 'Text from page 2.',
            'path/to/page1.png': 'Text from page 1.'
        }

        final_text = aggregate_text_results(sorted_paths, results, 'job4', self.mock_streamer)

        self.assertIn('Text from page 1.', final_text)
        self.assertIn('Text from page 2.', final_text)
        self.assertTrue(final_text.find('Text from page 1.') < final_text.find('Text from page 2.'))

    @patch('zip2text_app.pipeline.job_manager.perform_ocr_on_images')
    def test_run_job_full_success(self, mock_perform_ocr):
        """Integration test for a successful job run."""
        # A more robust mock that generates text based on input filenames
        def ocr_side_effect(image_paths, job_id, streamer):
            results = {}
            for path in image_paths:
                filename = os.path.basename(path)
                results[path] = f"Mocked text for {filename}"
            return results

        mock_perform_ocr.side_effect = ocr_side_effect

        files = {
            'test_images/page1.png': 'dummy_png',
            'test_images/page2.jpg': 'dummy_jpg',
            'docs/readme.txt': 'instructions'
        }
        zip_path = self._create_dummy_zip('full_test.zip', files)

        # Pass the mock streamer directly to the function
        final_text = run_job(zip_path, 'job5', self.mock_streamer)

        # Check that the mocked vision client was called
        mock_perform_ocr.assert_called_once()
        # Check the final aggregated text
        self.assertIn("Mocked text for page1.png", final_text)
        self.assertIn("Mocked text for page2.jpg", final_text)
        # Check that the final "JOB_COMPLETED" event was emitted
        self.mock_streamer.emit_event.assert_any_call(
            job_id='job5', event_name='JOB_COMPLETED', status='SUCCESS',
            severity=unittest.mock.ANY, message=unittest.mock.ANY, data=unittest.mock.ANY
        )

    def test_run_job_no_images(self):
        """Test a job where the zip file contains no supported images."""
        files = {'doc.txt': 'text', 'archive.dat': 'data'}
        zip_path = self._create_dummy_zip('no_images.zip', files)

        result_message = run_job(zip_path, 'job6', self.mock_streamer)

        self.assertIn("No supported image files", result_message)
        self.mock_streamer.emit_event.assert_any_call(
            job_id='job6', event_name='JOB_WARNING', status='COMPLETED',
            severity=unittest.mock.ANY, message=unittest.mock.ANY
        )


if __name__ == '__main__':
    unittest.main()
