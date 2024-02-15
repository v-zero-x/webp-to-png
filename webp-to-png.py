#!/usr/bin/env python3

import os
import sys
from PIL import Image
import logging
import unittest
from unittest.mock import patch
import io
import argparse
import time
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import shutil

# Configure logging
def setup_logging():
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, handlers=[
        logging.FileHandler("conversion_log.log"),
        logging.StreamHandler()
    ])

# Call setup_logging() right after defining it, before other functions or main logic
setup_logging()

@contextmanager
def use_cwd(path):
    """A context manager to temporarily change the current working directory."""
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

def convert_webp_to_png(source=None, target_dir=None, batch_mode=False):
    # Adjust source and target_dir based on provided input
    if source:
        source = Path(source)
        if source.is_file() and not target_dir:
            # If source is a file and no target directory is provided, use source's parent directory as target
            target_dir = source.parent
        elif not target_dir:
            # If no target directory is provided, default to source if it's a directory, else current directory
            target_dir = source if source.is_dir() else Path.cwd()
    else:
        # If no source is provided, default both source and target to current working directory
        source = Path.cwd()
        target_dir = Path.cwd()

    target_dir = Path(target_dir)  # Ensure target_dir is a Path object

    # Attempt to create the target directory if it does not exist
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created target directory: {target_dir}")

    successful_conversions, failed_conversions, skipped_files = 0, 0, 0
    compress_level = 6  # Sets the PNG compression level

    def process_file(source_file, target_dir):
        nonlocal successful_conversions, failed_conversions, skipped_files
        if source_file.suffix == '.webp':
            target_file = target_dir / source_file.with_suffix('.png').name
            if target_file.exists():
                response = input(f"File {target_file} already exists. Replace? (y/n): ").strip().lower()
                if response != 'y':
                    print(f"Skipped: {target_file.name}")
                    skipped_files += 1
                    return
            try:
                with Image.open(source_file) as img:
                    img.save(target_file, 'PNG', compress_level=compress_level)
                print(f"Converted: {source_file.name}")
                successful_conversions += 1
            except IOError as e:
                logging.error(f"IOError for {source_file.name}: {e}")
                failed_conversions += 1
            except Exception as e:
                logging.error(f"Unexpected error for {source_file.name}: {e}")
                failed_conversions += 1

    # Batch mode processing
    if batch_mode and source.is_dir():
        for file in source.glob('*.webp'):
            process_file(file, target_dir)
    # Single file processing
    elif source.is_file() and source.suffix == '.webp':
        process_file(source, target_dir)
    else:
        print(f"Error: The source {source} is not a valid .webp file or does not exist.", file=sys.stderr)

    logging.info(f"Completed. Success: {successful_conversions}, Failed: {failed_conversions}, Skipped: {skipped_files}")


def create_parser():
    parser = argparse.ArgumentParser(description="Convert .webp images to .png format.")
    # Set defaults to None to allow the convert_webp_to_png function to handle defaults
    parser.add_argument('source', nargs='?', type=str, help="The source .webp file or directory containing .webp files. Defaults to the current directory.", default=None)
    parser.add_argument('target_dir', nargs='?', type=str, help="The directory where converted .png files will be saved. Defaults to the same as the source directory.", default=None)
    parser.add_argument('--batch', action='store_true', help="Enable batch mode to process all .webp files in the specified directory.")
    parser.add_argument('--test', action='store_true', help="Run the script's test suite.")
    return parser

class TestConversion(unittest.TestCase):
    def setUp(self):
        # Setup for tests; create a temporary directory with test images using Pathlib
        self.test_dir = Path('test_originals')
        self.output_dir = Path('test_images')
        self.test_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        # Create a sample .webp image for testing
        self.sample_image_path = self.test_dir / 'test_image.webp'
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.sample_image_path, 'WEBP')

    def tearDown(self):
        # Cleanup after tests; remove test directories and files
        for folder in [self.test_dir, self.output_dir]:
            shutil.rmtree(folder, ignore_errors=True)

    def test_single_file_conversion(self):
        # Test conversion of a single .webp file to .png
        convert_webp_to_png(str(self.sample_image_path), str(self.output_dir))
        self.assertTrue((self.output_dir / 'test_image.png').exists())

    def test_batch_file_conversion(self):
        # Test batch conversion of .webp files to .png
        convert_webp_to_png(str(self.test_dir), str(self.output_dir), batch_mode=True)
        self.assertTrue((self.output_dir / 'test_image.png').exists())

    def test_output_directory_creation(self):
        non_existent_output_dir = self.test_dir / "non_existent_dir"
        convert_webp_to_png(str(self.sample_image_path), str(non_existent_output_dir))
        self.assertTrue(non_existent_output_dir.exists(), "Output directory was not created.")
        self.assertTrue((non_existent_output_dir / 'test_image.png').exists(), "Converted file not found in the newly created output directory.")

    # Use this context manager in your test
    def test_default_behavior_for_directories(self):
        with use_cwd(self.test_dir):
            convert_webp_to_png(batch_mode=True)
        self.assertTrue((self.test_dir / 'test_image.png').exists(), "Conversion file not found in the expected directory.")

    def test_existing_file_replace(self):
        # Simulate 'y' input for replacing the existing file
        with patch('builtins.input', return_value='y'):
            convert_webp_to_png(str(self.sample_image_path), str(self.output_dir))
        self.assertTrue((self.output_dir / 'test_image.png').exists(), "Converted file should replace the existing one.")

    # def test_existing_file_skip(self):
    #     # Simulate 'n' input for skipping the existing file
    #     with patch('builtins.input', return_value='n'):
    #         convert_webp_to_png(str(self.sample_image_path), str(self.output_dir))
    #     # Now verify the existing file was not replaced
    #     with Image.open(self.output_dir / 'test_image.png') as img:
    #         self.assertEqual(img.getpixel((0,0)), (0, 0, 255), "The image was not skipped as expected.")

    def test_nonexistent_source_file(self):
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            convert_webp_to_png('nonexistent.webp', str(self.output_dir))
            self.assertIn("Error: The source nonexistent.webp is not a valid .webp file or does not exist.", mock_stderr.getvalue())

# if __name__ == '__main__':
#     parser = create_parser()
#     args = parser.parse_args()

#     if args.test:
#         sys.argv = [sys.argv[0]]
#         unittest.main()
#     else:
#         convert_webp_to_png(Path(args.source), Path(args.target_dir), batch_mode=args.batch)

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    source_path = Path(args.source) if args.source else None
    target_dir_path = Path(args.target_dir) if args.target_dir else None

    if args.test:
        sys.argv = [sys.argv[0]]
        unittest.main()
    else:
        convert_webp_to_png(source_path, target_dir_path, batch_mode=args.batch)
