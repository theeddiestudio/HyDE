#!/usr/bin/env python3

import json
import os
import glob
import logging
import subprocess
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for DEBUG environment variable
if os.getenv('DEBUG'):
    logger.setLevel(logging.DEBUG)

def source_env_file(filepath):
    """Source environment variables from a file."""
    if os.path.exists(filepath):
        with open(filepath) as file:
            for line in file:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip("'")

# Source environment variables


source_env_file(os.path.expanduser(os.getenv('XDG_RUNTIME_DIR', '~/.runtime') + '/hyde/environment'))
source_env_file(os.path.expanduser(os.getenv('XDG_STATE_HOME', '~/.local/state') + '/hyde/config'))


def update_border_radius_css(filepath, new_value):
    """Update all occurrences of {number}pt in the CSS file with the new value."""
    if not os.path.exists(filepath):
        logger.error(f"File '{filepath}' does not exist.")
        return
    
    try:
        with open(filepath, 'r') as file:
            content = file.read()
        
        updated_content = re.sub(r'\d+pt', f'{new_value}pt', content)
        
        with open(filepath, 'w') as file:
            file.write(updated_content)
        
        logger.info(f"Successfully updated border-radius values to '{new_value}pt' in '{filepath}'")
    except Exception as e:
        logger.error(f"Failed to update border-radius values in '{filepath}': {e}")


def get_waybar_icon_size():
    """Determine the WAYBAR_ICON_SIZE based on environment variables."""
    waybar_icon_size = os.getenv('WAYBAR_ICON_SIZE')
    if waybar_icon_size:
        return int(waybar_icon_size)
    
    waybar_font_size = os.getenv('WAYBAR_FONT_SIZE')
    if waybar_font_size:
        return int(waybar_font_size) + 16
    
    font_size = os.getenv('FONT_SIZE')
    if font_size:
        return int(font_size) + 6
    
    return 16  # Default value if none of the environment variables are set

def parse_json_file(filepath):
    """Parse a JSON file and return the data."""
    with open(filepath, 'r') as file:
        data = json.load(file)
    return data

def modify_json_key(data, key, value):
    """Recursively modify the specified key with the given value in the JSON data."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k == key:
                data[k] = value
            elif isinstance(v, dict):
                modify_json_key(v, key, value)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        modify_json_key(item, key, value)
    return data

def update_json_file(filepath, key, value):
    """Update the specified key with the given value in a single JSON file."""
    data = parse_json_file(filepath)
    logger.debug(f"Original data in '{filepath}': {data}")
    
    modified_data = modify_json_key(data, key, value)
    logger.debug(f"Modified data in '{filepath}': {modified_data}")
    
    try:
        with open(filepath, 'w') as file:
            json.dump(modified_data, file, indent=4)
        logger.info(f"Successfully updated '{key}' to '{value}' in '{filepath}'")
    except Exception as e:
        logger.error(f"Failed to update '{key}' in '{filepath}': {e}")

def update_all_json_files(directory, key, value):
    """Update the specified key with the given value in all JSON files in the directory."""
    if not os.path.isdir(directory):
        logger.error(f"Directory '{directory}' does not exist.")
        return
    json_files = glob.glob(os.path.join(directory, '*.json'))
    
    for json_file in json_files:
        update_json_file(json_file, key, value)



# Update the icon size in all JSON files in the Waybar widgets directory
widgets_directory = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules')
update_all_json_files(widgets_directory, 'icon-size', get_waybar_icon_size())
update_all_json_files(widgets_directory, 'tooltip-icon-size', get_waybar_icon_size())
update_json_file(os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules/privacy.json'), 'icon-size', get_waybar_icon_size() - 6  )

# Update the border-radius in the Waybar CSS file
css_filepath = os.path.expanduser('~/.config/waybar/styles/dynamic/border-radius.css')
border_radius = os.getenv('WAYBAR_BORDER_RADIUS')
if not border_radius:
    result = subprocess.run(['hyprctl', 'getoption', 'decoration:rounding', '-j'], capture_output=True, text=True)
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            border_radius = data.get('int', 3)  # Default to 3 if 'int' is not found
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON output: {e}")
            border_radius = 3
    else:
        logger.error(f"Failed to run hyprctl command: {result.stderr}")
        border_radius = 2

if border_radius is None or border_radius < 2:
            border_radius = 2

update_border_radius_css(css_filepath, border_radius)


subprocess.run(['sh', '-c', 'killall waybar; waybar & disown'])