import os
import sys
from PIL import Image
import logging
import unittest
from unittest.mock import patch
import io
import argparse
import time

def convert_webp_to_png(source, target_dir, batch_mode=False):
    # Set up logging
    logging.basicConfig(filename='conversion_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Initialize counters
    successful_conversions = 0
    failed_conversions = 0
    skipped_files = 0

    # Sets the PNG compression level to 6, balancing compression efficiency with file save time. 
    # This level provides a good compromise between reducing file size and not excessively prolonging the compression process.
    # Higher levels (max 9) increase compression at the cost of longer processing times, while lower levels speed up saving but may result in larger files.
    # Level 6 is recommended as a default for general use.
    compress_level = 1

    def process_file(source_file, target_dir):
        nonlocal successful_conversions, failed_conversions, skipped_files
        filename = os.path.basename(source_file)
        if filename.endswith('.webp'):
            try:
                target_filename = filename.replace('.webp', '.png')
                target_file = os.path.join(target_dir, target_filename)
                # Check if target file already exists
                if os.path.exists(target_file):
                    user_input = input(f"The file {target_filename} already exists in the target directory. Replace or skip? (r/s): ").strip().lower()
                    if user_input != 'r':
                        logging.info(f"Skipped conversion of {filename}.")
                        skipped_files += 1
                        return
                
                with Image.open(source_file) as img:
                    img.save(target_file, 'PNG', compress_level=compress_level)
                    logging.info(f"Successfully converted {filename} to .png.")
                    successful_conversions += 1
            except Exception as e:
                logging.error(f"Failed to convert {filename}. Error: {e}")
                failed_conversions += 1

    if batch_mode and os.path.isdir(source):
        # Batch process all .webp files in the directory
        for filename in os.listdir(source):
            process_file(os.path.join(source, filename), target_dir)
    else:
        # Process a single file
        if os.path.isfile(source) and source.endswith('.webp'):
            process_file(source, target_dir)
        else:
            logging.error(f"The source {source} is not a valid .webp file or does not exist.")
            print(f"Error: The source {source} is not a valid .webp file or does not exist.")
    
    logging.info(f"Conversion completed. {successful_conversions} successful, {failed_conversions} failed, {skipped_files} skipped.")

def create_parser():
    parser = argparse.ArgumentParser(description="Convert .webp images to .png format.")
    parser.add_argument('source', nargs='?', type=str, help="The source .webp file or directory containing .webp files.", default=None)
    parser.add_argument('target_dir', nargs='?', type=str, help="The directory where converted .png files will be saved.", default=None)
    parser.add_argument('--batch', action='store_true', help="Enable batch mode to process all .webp files in the specified directory.")
    parser.add_argument('--test', action='store_true', help="Run the script's test suite.")
    return parser

class TestConversion(unittest.TestCase):
    def setUp(self):
        # Setup for tests; create a temporary directory with test images
        self.test_dir = 'test_originals'
        self.output_dir = 'test_images'
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        # Create a sample .webp image for testing
        self.sample_image_path = os.path.join(self.test_dir, 'test_image.webp')
        img = Image.new('RGB', (100, 100), color = 'red')
        img.save(self.sample_image_path, 'WEBP')

    def tearDown(self):
        # Cleanup after tests; remove test directories and files
        for folder in [self.test_dir, self.output_dir]:
            for file in os.listdir(folder):
                os.remove(os.path.join(folder, file))
            os.rmdir(folder)

    def test_single_file_conversion(self):
        # Test conversion of a single .webp file to .png
        convert_webp_to_png(self.sample_image_path, self.output_dir)
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'test_image.png')))

    def test_batch_file_conversion(self):
        # Test batch conversion of .webp files to .png
        # Assuming setUp has created one sample .webp image, we can directly test batch processing
        convert_webp_to_png(self.test_dir, self.output_dir, batch_mode=True)
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, 'test_image.png')))
    
    def test_existing_file_skip(self):
        # Test the skip functionality when a .png file already exists
        # First, create an existing .png file
        existing_image_path = os.path.join(self.output_dir, 'test_image.png')
        img = Image.new('RGB', (100, 100), color = 'blue')
        img.save(existing_image_path, 'PNG')
        
        with patch('builtins.input', return_value='s'):
            convert_webp_to_png(self.sample_image_path, self.output_dir)
            with Image.open(existing_image_path) as img:
                self.assertEqual(img.getpixel((0,0)), (0, 0, 255))  # Checking if the image was skipped by color
    
    def test_existing_file_replace(self):
        # Ensure the existing PNG file is created before the test
        existing_image_path = os.path.join(self.output_dir, 'test_image.png')
        self.sample_image_path = os.path.join(self.test_dir, 'test_image.webp')
        img = Image.new('RGB', (100, 100), color='red')
        img.save(existing_image_path, 'PNG')

        # Record the modification time of the existing file
        original_mod_time = os.path.getmtime(existing_image_path)

        # Wait a moment to ensure the file system's timestamp resolution captures the change
        time.sleep(2)

        # Attempt to replace the file
        with patch('builtins.input', return_value='r'):
            convert_webp_to_png(self.sample_image_path, self.output_dir)

        # Check the modification time after the replacement attempt
        replaced_mod_time = os.path.getmtime(existing_image_path)

        # Verify the file was replaced by comparing modification times
        self.assertTrue(replaced_mod_time > original_mod_time, "The file was not replaced as expected.")

        # Optionally, if checking the color is still required:
        # with Image.open(existing_image_path) as img:
        #     self.assertEqual(img.getpixel((0,0)), (255, 0, 0), "The image color does not match the expected value.")

    def test_nonexistent_source_file(self):
        # Capture the output
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            convert_webp_to_png('nonexistent.webp', self.output_dir)
            self.assertIn("Error: The source nonexistent.webp is not a valid .webp file or does not exist.", mock_stdout.getvalue())

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    if args.test:
        # Adjust argv for unittest to avoid conflicts with argparse
        sys.argv = [sys.argv[0]]  # Necessary to only pass the script name to unittest
        unittest.main()
    else:
        if args.source and args.target_dir:
            # Proceed with image conversion based on provided arguments
            convert_webp_to_png(args.source, args.target_dir, batch_mode=args.batch)
        else:
            print("Error: Please provide a source and target directory for conversion.")
