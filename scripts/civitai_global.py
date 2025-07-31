## === ANXETY EDITs ===
import warnings, os, json
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime

# ===  WebUI imports ===
from modules.shared import opts


class Colors:
    """ANSI color codes for terminal output"""
    BLACK   = '\033[30m'
    RED     = '\033[31m'
    GREEN   = '\033[32m'
    YELLOW  = '\033[33m'
    BLUE    = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN    = '\033[36m'
    BRIGHT_BLACK   = '\033[90m'
    BRIGHT_RED     = '\033[91m'
    BRIGHT_GREEN   = '\033[92m'
    BRIGHT_YELLOW  = '\033[93m'
    BRIGHT_BLUE    = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN    = '\033[96m'
    RESET = '\033[0m'


do_debug_print = getattr(opts, "civitai_debug_prints", False)
def init():
    warnings.simplefilter('ignore', InsecureRequestWarning)

    config_folder = os.path.join(os.getcwd(), "config_states")
    if not os.path.exists(config_folder):
        os.mkdir(config_folder)

    global download_queue, last_version, cancel_status, recent_model, last_url, json_data, json_info, main_folder, previous_inputs, download_fail, sortNewest, isDownloading, old_download, scan_files, from_update_tab, url_list, print, subfolder_json

    cancel_status = None
    recent_model = None
    json_data = None
    json_info = None
    main_folder = None
    previous_inputs = None
    last_version = None
    url_list = {}
    download_queue = []

    subfolder_json = os.path.join(config_folder, "civitai_subfolders.json")
    if not os.path.exists(subfolder_json):
        with open(subfolder_json, 'w') as json_file:
            #json.dump({}, json_file)
            json.dump({"created_at": datetime.now().timestamp()}, json_file)

    from_update_tab = False
    scan_files = False
    download_fail = False
    sortNewest = False
    isDownloading = False
    old_download = False

_print = print
def print(print_message):
    _print(f'{Colors.BLUE}[CivitAI-Browser+]{Colors.RESET} - {print_message}')

def debug_print(print_message):
    if do_debug_print:
        _print(f'{Colors.MAGENTA}[DEBUG] {Colors.BLUE}[CivitAI-Browser+]{Colors.RESET} - {print_message}')