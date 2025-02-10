#!/usr/bin/env python3

import json
import os
import glob
import logging
import subprocess
import re
import argparse

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
        
        logger.debug(f"Successfully updated border-radius values to '{new_value}pt' in '{filepath}'")
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
        logger.debug(f"Successfully updated '{key}' to '{value}' in '{filepath}'")
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

def generate_includes_json(directories, output_filepath=None):
    """Generate an includes.json file with paths of JSON and JSONC modules from given directories."""
    includes = []

    for directory in directories:
        if not os.path.isdir(directory):
            logger.error(f"Directory '{directory}' does not exist.")
            continue
        
        json_files = glob.glob(os.path.join(directory, '*.json'))
        jsonc_files = glob.glob(os.path.join(directory, '*.jsonc'))
        includes.extend(json_files + jsonc_files)
    
    if output_filepath is None:
        xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        output_filepath = os.path.join(xdg_config_home, 'waybar', 'includes.json')
    
    includes_data = {"include": includes}
    
    try:
        with open(output_filepath, 'w') as file:
            json.dump(includes_data, file, indent=4)
        logger.info(f"Successfully generated '{output_filepath}' with {len(includes)} entries.")
    except Exception as e:
        logger.error(f"Failed to generate '{output_filepath}': {e}")

import shutil
import time
import signal
import sys

def write_config_file(filepath, source_filepath):
    """Copy the contents of the source config file to the destination config file."""
    try:
        shutil.copyfile(source_filepath, filepath)
        logger.info(f"Successfully copied config from '{source_filepath}' to '{filepath}'")
    except Exception as e:
        logger.error(f"Failed to copy config from '{source_filepath}' to '{filepath}': {e}")

def write_style_file(filepath, source_filepath):
    """Set the contents of the source style file to the destination style file."""
    
    wallbash_gtk_css_file = os.path.expanduser(os.getenv('XDG_CACHE_HOME', '~/.cache') + '/hyde/wallbash/gtk.css')
    wallbash_gtk_css_file_str = ""
    
    if os.path.exists(wallbash_gtk_css_file):
            wallbash_gtk_css_file_str = f'@import "{wallbash_gtk_css_file}";'
    else :
        wallbash_gtk_css_file_str = "/*  wallbash gtk.css not found   */"
        logger.debug(f"Wallbash GTK CSS file not found: '{wallbash_gtk_css_file}'")



    style_css = f"""
    /*!  DO NOT EDIT THIS FILE */
    /*
    *     ░▒▒▒░░░▓▓           ___________
    *   ░░▒▒▒░░░░░▓▓        //___________/
    *  ░░▒▒▒░░░░░▓▓     _   _ _    _ _____
    *  ░░▒▒░░░░░▓▓▓▓▓▓ | | | | |  | |  __/
    *   ░▒▒░░░░▓▓   ▓▓ | |_| | |_/ /| |___
    *    ░▒▒░░▓▓   ▓▓   |__  |____/ |____/
    *      ░▒▓▓   ▓▓  //____/
    */

    /* Modified by Hyde */

    /* Modify/add style in ~/.config/waybar/styles/ */
    @import "{source_filepath}";

    /* Imports wallbash colors */
    {wallbash_gtk_css_file_str}

    /* Colors and theme configuration is generated through the `theme.css` file */
    @import "theme.css";

    /* Users who want to override the current style add/edit 'user-style.css' */
    @import "user-style.css";
    """

    try:
        with open(filepath, 'w') as file:
            file.write(style_css)
        logger.info(f"Successfully wrote style to '{filepath}'")
    except Exception as e:
        logger.error(f"Failed to write style to '{filepath}': {e}")


def signal_handler(sig, frame):
    # Kill waybar and exit when script receives SIGTERM/SIGINT
    subprocess.run(['killall', 'waybar'])
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Waybar configuration script")
    parser.add_argument('-u', '--update-icon-size', action='store_true', help="Update icon size in JSON files")
    parser.add_argument('-b', '--update-border-radius', action='store_true', help="Update border radius in CSS file")
    parser.add_argument('-g', '--generate-includes', action='store_true', help="Generate includes.json file")
    parser.add_argument('-c', '--config', type=str, help="Path to the source config.jsonc file")
    parser.add_argument('-s', '--style', type=str, help="Path to the source style.css file")
    parser.add_argument('-w', '--watch', action='store_true', help="Watch and restart Waybar if it dies")
    args = parser.parse_args()

    # Source environment variables
    source_env_file(os.path.expanduser(os.getenv('XDG_RUNTIME_DIR', '~/.runtime') + '/hyde/environment'))
    source_env_file(os.path.expanduser(os.getenv('XDG_STATE_HOME', '~/.local/state') + '/hyde/config'))

    if args.update_icon_size:
        # Update the icon size in all JSON files in the Waybar widgets directory
        widgets_directory = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules')
        icon_size = get_waybar_icon_size()
        update_all_json_files(widgets_directory, 'icon-size', icon_size)
        update_all_json_files(widgets_directory, 'tooltip-icon-size', icon_size)
        update_json_file(os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules/privacy.json'), 'icon-size', icon_size - 6)

    if args.update_border_radius:
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

    if args.generate_includes:
        # Generate an includes.json file with paths of JSON/c modules from the specified directories
        directories = [
            os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules/'),
            os.path.expanduser(os.getenv('XDG_DATA_HOME', '~/.local/share') + '/hyde/waybar/modules/'),
            # Add more directories as needed
        ]
        generate_includes_json(directories)

    if args.config:
        # Copy the source config.jsonc file to the default location
        xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        config_filepath = os.path.join(xdg_config_home, 'waybar', 'config.jsonc')
        write_config_file(config_filepath, args.config)

    if args.style:
        # Copy the source style.css file to the default location
        xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        style_filepath = os.path.join(xdg_config_home, 'waybar', 'style.css')
        write_style_file(style_filepath, args.style)

    if args.watch:
        # Set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Monitor and restart Waybar if it dies
        while True:
            try:
                # Check if waybar is running
                result = subprocess.run(['pgrep', 'waybar'], capture_output=True)
                if result.returncode != 0:
                    # Waybar is not running, start it
                    subprocess.Popen(['waybar'])
                    logger.info("Waybar restarted")
            except Exception as e:
                logger.error(f"Error monitoring Waybar: {e}")

            # Wait before next check
            time.sleep(2)
    else:
        subprocess.run(['sh', '-c', 'killall waybar; waybar & disown'])



if __name__ == "__main__":
    main()