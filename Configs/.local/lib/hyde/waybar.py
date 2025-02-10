#!/usr/bin/env python3

import json
import os
import glob
import logging
import subprocess
import re
import argparse
import shutil
import time
import signal
import sys
import hashlib

#TODO: Add utils

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

def get_file_hash(filepath):
    """Calculate the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as file:
        while chunk := file.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_current_layout_from_config():
    """Get the current layout by comparing the hash of the files in the layouts directory with the current config.jsonc."""
    config_filepath = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/config.jsonc')
    config_hash = get_file_hash(config_filepath)
    layout_dir = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/layouts')
    layouts = sorted(glob.glob(os.path.join(layout_dir, '*.jsonc')))
    for layout in layouts:
        if get_file_hash(layout) == config_hash:
            return layout
    return None

def ensure_state_file():
    """Ensure the state file has the necessary entries."""
    state_file = os.path.expanduser(os.getenv('HYDE_STATE_HOME', '~/.local/state') + '/staterc')
    if not os.path.exists(state_file) or os.path.getsize(state_file) == 0:
        current_layout = get_current_layout_from_config()
        if current_layout:
            with open(state_file, 'w') as file:
                file.write(f'WAYBAR_LAYOUT_PATH={current_layout}\n')
                style_path = resolve_style_path(current_layout)
                file.write(f'WAYBAR_STYLE_PATH={style_path}\n')
    else:
        with open(state_file, 'r') as file:
            lines = file.readlines()
        layout_path_exists = any(line.startswith('WAYBAR_LAYOUT_PATH=') for line in lines)
        style_path_exists = any(line.startswith('WAYBAR_STYLE_PATH=') for line in lines)
        if not layout_path_exists or not style_path_exists:
            current_layout = get_current_layout_from_config()
            if current_layout:
                with open(state_file, 'a') as file:
                    if not layout_path_exists:
                        file.write(f'WAYBAR_LAYOUT_PATH={current_layout}\n')
                    if not style_path_exists:
                        style_path = resolve_style_path(current_layout)
                        file.write(f'WAYBAR_STYLE_PATH={style_path}\n')

def resolve_style_path(layout_path):
    """Resolve the style path based on the layout path."""
    basename = os.path.basename(layout_path).replace('.jsonc', '')
    style_dir = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/styles')
    
    # First check for a match with the basename#tag format
    style_path = glob.glob(os.path.join(style_dir, f'{basename}*.css'))
    if not style_path:
        # If not found, try without the '#'
        basename = basename.split('#')[0]
        style_path = glob.glob(os.path.join(style_dir, f'{basename}*.css'))
    
    if not style_path:
        return os.path.join(style_dir, 'defaults.css')
    return style_path[0]

def set_layout(layout_path):
    """Set the layout and corresponding style."""
    style_path = resolve_style_path(layout_path)

    state_file = os.path.expanduser(os.getenv('HYDE_STATE_HOME', '~/.local/state') + '/staterc')
    with open(state_file, 'r') as file:
        lines = file.readlines()
    with open(state_file, 'w') as file:
        for line in lines:
            if line.startswith('WAYBAR_LAYOUT_PATH='):
                file.write(f'WAYBAR_LAYOUT_PATH={layout_path}\n')
            elif line.startswith('WAYBAR_STYLE_PATH='):
                file.write(f'WAYBAR_STYLE_PATH={style_path}\n')
            else:
                file.write(line)

    config_filepath = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/config.jsonc')
    style_filepath = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/style.css')
    shutil.copyfile(layout_path, config_filepath)
    write_style_file(style_filepath, style_path)
    subprocess.run(['pkill', '-SIGUSR2', 'waybar'])

def handle_layout_navigation(option):
    """Handle --next, --prev, and --set options."""
    layout_dir = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/layouts')
    layouts = sorted(glob.glob(os.path.join(layout_dir, '*.jsonc')))
    state_file = os.path.expanduser(os.getenv('HYDE_STATE_HOME', '~/.local/state') + '/staterc')
    current_layout = None
    with open(state_file, 'r') as file:
        for line in file:
            if line.startswith('WAYBAR_LAYOUT_PATH='):
                current_layout = line.split('=')[1].strip()
                break

    if not current_layout:
        logger.error('Current layout not found in state file.')
        return

    current_index = layouts.index(current_layout)
    if option == '--next':
        next_index = (current_index + 1) % len(layouts)
        set_layout(layouts[next_index])
    elif option == '--prev':
        prev_index = (current_index - 1 + len(layouts)) % len(layouts)
        set_layout(layouts[prev_index])
    elif option == '--set':
        if len(sys.argv) < 3:
            logger.error('Usage: --set <layout>')
            return
        layout_path = sys.argv[2]
        if not os.path.exists(layout_path):
            logger.error(f"Layout {layout_path} not found")
            sys.exit(1)
        set_layout(layout_path)

def list_layouts_json():
    """List all layouts in JSON format with their matching styles."""
    layout_dir = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/layouts')
    layouts = sorted(glob.glob(os.path.join(layout_dir, '*.jsonc')))
    layout_style_pairs = []
    for layout in layouts:
        basename = os.path.basename(layout).replace('.jsonc', '')
        style_path = resolve_style_path(layout)
        layout_style_pairs.append({'layout': layout, 'basename': basename, 'style': style_path})
    layouts_json = json.dumps(layout_style_pairs, indent=4)
    print(layouts_json)
    sys.exit(0)

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

def write_style_file(style_filepath, source_filepath):
    """Override the style file with the given source style."""
    wallbash_gtk_css_file = os.path.expanduser(os.getenv('XDG_CACHE_HOME', '~/.cache') + '/hyde/wallbash/gtk.css')
    wallbash_gtk_css_file_str = f'@import "{wallbash_gtk_css_file}";' if os.path.exists(wallbash_gtk_css_file) else '/*  wallbash gtk.css not found   */'
    style_css = f"""
    /*!  DO NOT EDIT THIS FILE */
    /*
    *     ░▒▒▒░░░▓▓           ___________
    *   ░░▒▒▒░░░░░▓▓        //___________/
    *  ░░▒▒▒░░░░░▓▓     _   _ _    _ _____
    *  ░░▒▒░░░░░▓▓▓▓▓ | | | | |  | |  __/
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
    with open(style_filepath, 'w') as file:
        file.write(style_css)
    logger.info(f"Successfully wrote style to '{style_filepath}'")

def run_waybar_command(command):
    """Run a Waybar command and redirect its output to the Waybar log file."""
    log_dir = os.path.expanduser(os.getenv('XDG_RUNTIME_DIR', '~/.runtime') + '/hyde')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'waybar.log')
    with open(log_file, 'a') as file:
        file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Running command: {command}\n")
        subprocess.run(command, shell=True, stdout=file, stderr=file)

def main():
    parser = argparse.ArgumentParser(description="Waybar configuration script")
    parser.add_argument('--set', type=str, help="Set a specific layout")
    parser.add_argument('-n', '--next', action='store_true', help="Switch to the next layout")
    parser.add_argument('-p', '--prev', action='store_true', help="Switch to the previous layout")
    parser.add_argument('-u','--update', action='store_true', help="Update all (icon size, border radius, includes, config, style)")
    parser.add_argument('-i', '--update-icon-size', action='store_true', help="Update icon size in JSON files")
    parser.add_argument('-b', '--update-border-radius', action='store_true', help="Update border radius in CSS file")
    parser.add_argument('-g', '--generate-includes', action='store_true', help="Generate includes.json file")
    parser.add_argument('-c', '--config', type=str, help="Path to the source config.jsonc file")
    parser.add_argument('-s', '--style', type=str, help="Path to the source style.css file")
    parser.add_argument('-w', '--watch', action='store_true', help="Watch and restart Waybar if it dies")
    parser.add_argument('--json', '-j', action='store_true', help="List all layouts in JSON format")
    args = parser.parse_args()

    # Ensure the state file has the necessary entries
    ensure_state_file()

    source_env_file(os.path.expanduser(os.getenv('XDG_RUNTIME_DIR', '~/.runtime') + '/hyde/environment'))
    source_env_file(os.path.expanduser(os.getenv('XDG_STATE_HOME', '~/.local/state') + '/hyde/config'))

    if args.update:
        update_icon_size()
        update_border_radius()
        generate_includes()
    if args.update_icon_size:
        update_icon_size()
    if args.update_border_radius:
        update_border_radius()
    if args.generate_includes:
        generate_includes()
    if args.config:
        update_config(args.config)
    if args.style:
        update_style(args.style)
    if args.next or args.prev or args.set:
        handle_layout_navigation('--next' if args.next else '--prev' if args.prev else '--set')
    if args.json:
        list_layouts_json()
    if args.watch:
        watch_waybar()
    else:
        run_waybar_command('killall waybar; waybar & disown')

    # Exit if no valid flag is provided
    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(1)

def update_icon_size():
    widgets_directory = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules')
    icon_size = int(os.getenv('WAYBAR_ICON_SIZE', int(os.getenv('WAYBAR_FONT_SIZE', int(os.getenv('FONT_SIZE', 10))) + 6)))
    for json_file in glob.glob(os.path.join(widgets_directory, '*.json')):
        data = parse_json_file(json_file)
        data = modify_json_key(data, 'icon-size', icon_size)
        data = modify_json_key(data, 'tooltip-icon-size', icon_size)
        with open(json_file, 'w') as file:
            json.dump(data, file, indent=4)
    privacy_file = os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules/privacy.json')
    data = parse_json_file(privacy_file)
    data = modify_json_key(data, 'icon-size', icon_size - 6)
    with open(privacy_file, 'w') as file:
        json.dump(data, file, indent=4)

def update_border_radius():
    css_filepath = os.path.expanduser('~/.config/waybar/styles/dynamic/border-radius.css')
    border_radius = os.getenv('WAYBAR_BORDER_RADIUS')
    if not border_radius:
        result = subprocess.run(['hyprctl', 'getoption', 'decoration:rounding', '-j'], capture_output=True, text=True)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                border_radius = data.get('int', 3)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output: {e}")
                border_radius = 3
        else:
            logger.error(f"Failed to run hyprctl command: {result.stderr}")
            border_radius = 2
    if border_radius is None or border_radius < 2:
        border_radius = 2
    with open(css_filepath, 'r') as file:
        content = file.read()
    updated_content = re.sub(r'\d+pt', f'{border_radius}pt', content)
    with open(css_filepath, 'w') as file:
        file.write(updated_content)

def generate_includes():
    directories = [
        os.path.expanduser(os.getenv('XDG_CONFIG_HOME', '~/.config') + '/waybar/modules/'),
        os.path.expanduser(os.getenv('XDG_DATA_HOME', '~/.local/share') + '/hyde/waybar/modules/')
    ]
    includes = []
    for directory in directories:
        if not os.path.isdir(directory):
            logger.error(f"Directory '{directory}' does not exist.")
            continue
        includes.extend(glob.glob(os.path.join(directory, '*.json')))
        includes.extend(glob.glob(os.path.join(directory, '*.jsonc')))
    includes_data = {'include': includes}
    output_filepath = os.path.join(os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), 'waybar', 'includes.json')
    with open(output_filepath, 'w') as file:
        json.dump(includes_data, file, indent=4)
    logger.info(f"Successfully generated '{output_filepath}' with {len(includes)} entries.")

def update_config(config_path):
    xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    config_filepath = os.path.join(xdg_config_home, 'waybar', 'config.jsonc')
    shutil.copyfile(config_path, config_filepath)
    logger.info(f"Successfully copied config from '{config_path}' to '{config_filepath}'")

def update_style(style_path):
    xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    style_filepath = os.path.join(xdg_config_home, 'waybar', 'style.css')
    write_style_file(style_filepath, style_path)

def watch_waybar():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    while True:
        try:
            result = subprocess.run(['pgrep', 'waybar'], capture_output=True)
            if result.returncode != 0:
                subprocess.Popen(['waybar'])
                logger.info('Waybar restarted')
        except Exception as e:
            logger.error(f"Error monitoring Waybar: {e}")
        time.sleep(2)

if __name__ == '__main__':
    main()