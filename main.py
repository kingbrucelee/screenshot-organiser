import os
import re
from collections import defaultdict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCREENSHOTS_FOLDER = 'screenshots'
MAX_FILES_PER_FOLDER = 50
BAR_HEIGHT = 50
FONT_SIZE = 16
TEXT_PADDING = 10
DATE_TEXT_RIGHT_OFFSET = 100
PACKAGE_NAME_OFFSET = 50

class FileNameError(Exception):
    pass

def extract_info(filename):
    match = re.search(r'Screenshot_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})_(.*)\.jpg', filename)
    if match:
        timestamp, package_name = match.groups()
        package_name = package_name.split('-')[0] # Example: com.package.name-edit treated as com.package.name because it's still the same app. The character "-" is not allowed in package name so there are no collisions.
        return timestamp, package_name
    raise FileNameError(f"Filename '{filename}' does not match the expected pattern")

def modify_image(image_path, time_text, date_text, package_name, output_path):
    try:
        with Image.open(image_path) as image:
            new_width = image.width
            new_height = image.height + BAR_HEIGHT
            new_image = Image.new("RGB", (new_width, new_height), "black")
            new_image.paste(image, (0, BAR_HEIGHT))
            draw = ImageDraw.Draw(new_image)
            
            try:
                font = ImageFont.truetype("arial.ttf", FONT_SIZE)
            except IOError:
                font = ImageFont.load_default()
            
            draw.text((TEXT_PADDING, TEXT_PADDING), time_text, font=font, fill="white")
            draw.text((new_width - DATE_TEXT_RIGHT_OFFSET, TEXT_PADDING), date_text, font=font, fill="white")
            draw.text(((new_width // 2) - PACKAGE_NAME_OFFSET, TEXT_PADDING), package_name, font=font, fill="white")
            new_image.save(output_path)
        return True
    except Exception as e:
        logging.error(f"Error modifying image {image_path}: {str(e)}")
        return False

def organize_screenshots(folder):
    if not os.path.exists(folder):
        logging.critical(f"The folder {folder} does not exist.")
        return

    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    package_files = defaultdict(list)
    ignored_files = []

    for file in files:
        try:
            timestamp, package_name = extract_info(file)
            try:
                date = datetime.strptime(timestamp, '%Y-%m-%d-%H-%M-%S-%f')
                package_files[package_name].append((timestamp, file))
            except ValueError:
                raise FileNameError(f"Invalid date extracted from filename: {file}")
        except FileNameError as e:
            logging.debug(str(e))
            ignored_files.append(file)

    if ignored_files:
        logging.error(f"The following files were ignored due to invalid naming: {', '.join(ignored_files)}")

    for package_name, file_list in package_files.items():
        package_folder_name = f"{len(file_list)}_{package_name}"
        package_folder = os.path.join(folder, package_folder_name)
        os.makedirs(package_folder, exist_ok=True)

        if len(file_list) > MAX_FILES_PER_FOLDER:
            monthly_files = defaultdict(list)
            for timestamp, file in file_list:
                date = datetime.strptime(timestamp, '%Y-%m-%d-%H-%M-%S-%f')
                month_folder_name = date.strftime('%Y-%m')
                monthly_files[month_folder_name].append((timestamp, file))
            
            for month_folder_name, month_files in monthly_files.items():
                month_folder = os.path.join(package_folder, month_folder_name)
                os.makedirs(month_folder, exist_ok=True)
                process_files(folder, month_folder, month_files, package_name)
        else:
            process_files(folder, package_folder, file_list, package_name)

def process_files(source_folder, destination_folder, file_list, package_name):
    not_processed_files = []
    for timestamp, file in file_list:
        source = os.path.join(source_folder, file)
        date = datetime.strptime(timestamp, '%Y-%m-%d-%H-%M-%S-%f')
        time_text = date.strftime('%H:%M')
        date_text = date.strftime('%Y-%m-%d')
        destination = os.path.join(destination_folder, file)
        if modify_image(source, time_text, date_text, package_name, destination):
            os.remove(source)
            logging.info(f"Moved {file} to {destination_folder}")
        else:
            not_processed_files.append(file)
    if not_processed_files:
        logging.error(f"Failed to process {', '.join(not_processed_files)}")
            
if __name__ == "__main__":
    organize_screenshots(SCREENSHOTS_FOLDER)
