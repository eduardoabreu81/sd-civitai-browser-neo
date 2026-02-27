import subprocess
import threading
import hashlib
import requests
import platform
import random
import stat
import json
import time
import re
import os
import gradio as gr
from pathlib import Path

# === WebUI imports ===
from modules.shared import opts, cmd_opts

# === Extension imports ===
import scripts.civitai_file_manage as _file
import scripts.civitai_global as gl
import scripts.civitai_api as _api
import scripts.download_log as _dl_log
from scripts.civitai_api import is_early_access, is_model_nsfw
from scripts.civitai_global import print, debug_print

try:
    from zip_unicode import ZipHandler
except ImportError:
    print('Python module "ZipUnicode" has not been imported correctly, please try to restart or install it manually.')


total_count = 0
current_count = 0
dl_manager_count = 0

# threading.Event: SET = not downloading (safe to cancel/cleanup), CLEARED = download in progress
_not_downloading = threading.Event()
_not_downloading.set()

def random_number(prev=None):
    number = str(random.randint(10000, 99999))
    while number == prev:
        number = str(random.randint(10000, 99999))

    return number


gl.init()


rpc_secret = "R7T5P2Q9K6"
try:
    queue = not cmd_opts.no_gradio_queue
except AttributeError:
    queue = not cmd_opts.disable_queue
except:
    queue = True


## === ANXETY EDITs ===

def start_aria2_rpc():
    start_file = os.path.join(aria2path, '_')
    running_file = os.path.join(aria2path, 'running')
    null = open(os.devnull, 'w')

    if os.path.exists(running_file):
        try:
            if os_type == 'Linux':
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:' + env['PATH']
                subprocess.Popen('pkill aria2', shell=True, env=env)
            else:
                subprocess.Popen(stop_rpc, stdout=null, stderr=null)
            time.sleep(1)
        except Exception as e:
            print(f"Failed to stop Aria2 RPC : {e}")
    else:
        if os.path.exists(start_file):
            os.rename(start_file, running_file)
            return
        else:
            with open(start_file, 'w', encoding='utf-8'):
                pass

    try:
        show_log = getattr(opts, 'show_log', False)
        aria2_flags = getattr(opts, 'aria2_flags', '')
        cmd = f'"{aria2}" --enable-rpc --rpc-listen-all --rpc-listen-port=24000 --rpc-secret {rpc_secret} --check-certificate=false --ca-certificate=" " --file-allocation=none {aria2_flags}'
        subprocess_args = {'shell': True}
        if not show_log:
            subprocess_args.update({'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL})

        subprocess.Popen(cmd, **subprocess_args)
        if os.path.exists(running_file):
            print('Aria2 RPC restarted')
        else:
            print('Aria2 RPC started')
    except Exception as e:
        print(f"Failed to start Aria2 RPC server: {e}")

aria2path = Path(__file__).resolve().parents[1] / 'aria2'
os_type = platform.system()

if os_type == 'Windows':
    aria2 = os.path.join(aria2path, 'win', 'aria2.exe')
    stop_rpc = 'taskkill /im aria2.exe /f'
    start_aria2_rpc()
elif os_type == 'Linux':
    aria2 = os.path.join(aria2path, 'lin', 'aria2')
    st = os.stat(aria2)
    os.chmod(aria2, st.st_mode | stat.S_IEXEC)
    stop_rpc = 'pkill aria2'
    start_aria2_rpc()

class TimeOutFunction(Exception):
    pass

def create_model_item(dl_url, model_filename, install_path, model_name, version_name, model_sha256, model_id, create_json, from_batch=False):
    global dl_manager_count
    if model_id:
        model_id = int(model_id)
    if model_sha256:
        model_sha256 = model_sha256.upper()
    if model_sha256 == 'UNKNOWN':
        model_sha256 = None

    filtered_items = []

    for item in gl.json_data['items']:
        if int(item['id']) == int(model_id):
            filtered_items.append(item)
            content_type = item['type']
            desc = item['description']
            main_folder = _api.contenttype_folder(content_type, desc)
            break

    sub_folder = os.path.normpath(os.path.relpath(install_path, main_folder))

    model_json = {'items': filtered_items}

    # Duplicate guard
    for item in gl.download_queue:
        if item['dl_url'] == dl_url:
            return None

    dl_manager_count += 1

    item = {
        'dl_id': dl_manager_count,
        'dl_url': dl_url,
        'model_filename': model_filename,
        'install_path': install_path,
        'model_name': model_name,
        'version_name': version_name,
        'model_sha256': model_sha256,
        'model_id': model_id,
        'create_json': create_json,
        'model_json': model_json,
        'model_versions': None,        # fetched lazily in download_create_thread
        'preview_html': '',            # fetched lazily in download_create_thread
        'existing_path': install_path, # fetched lazily in download_create_thread
        'from_batch': from_batch,
        'sub_folder': sub_folder,
        '_api_ready': False,
    }

    _dl_log.log_queued(item)
    return item


def _resolve_versions_to_download(versions_list, model_folder):
    """Return the list of model versions to download for a batch update.

    For models with multiple installed families (e.g. Pony V1 AND Illustrious V1
    on the same page), returns the latest available version for each installed
    family so every family is updated in one batch action.

    Falls back to [versions_list[0]] (original behaviour) when:
    - The model folder cannot be scanned, or
    - No family-tagged installed versions are detected.
    """
    if not versions_list:
        return []

    # Collect SHA256 hashes from local JSON files in the model folder
    installed_hashes = set()
    if model_folder and os.path.isdir(str(model_folder)):
        for root, _, files in os.walk(str(model_folder), followlinks=True):
            for fname in files:
                if fname.endswith('.json'):
                    try:
                        data = _api.safe_json_load(os.path.join(root, fname))
                        if data:
                            sha = data.get('sha256', '')
                            if sha:
                                installed_hashes.add(sha.upper())
                    except Exception:
                        pass

    if not installed_hashes:
        return [versions_list[0]]

    # Map: family -> latest available version (index 0 in API response = most recent)
    latest_by_family = {}
    installed_families = set()

    for ver in versions_list:
        ver_name = ver.get('name', '')
        family, _ = _file.extract_version_from_ver_name(ver_name)
        if family and family not in latest_by_family:
            latest_by_family[family] = ver

        for file_entry in ver.get('files', []):
            sha = file_entry.get('hashes', {}).get('SHA256', '').upper()
            if sha and sha in installed_hashes:
                if family:
                    installed_families.add(family)
                break

    if not installed_families:
        # No recognised family found as installed — fresh download or non-family model
        return [versions_list[0]]

    # One latest version per installed family (de-duplicated by version id)
    seen_ids = set()
    result = []
    for fam in installed_families:
        ver = latest_by_family.get(fam)
        if ver:
            vid = ver.get('id')
            if vid not in seen_ids:
                result.append(ver)
                seen_ids.add(vid)

    return result if result else [versions_list[0]]


def selected_to_queue(model_list, subfolder, download_start, create_json, current_html):
    global total_count, current_count
    if gl.download_queue:
        number = download_start
    else:
        number = random_number(download_start)
        total_count = 0
        current_count = 0

    model_list = json.loads(model_list)
    skipped_names = []

    ## === ANXETY EDITs ===
    for model_string in model_list:
        model_name, model_id = _api.extract_model_info(model_string)
        item_found = None
        for item in gl.json_data['items']:
            if int(item['id']) == int(model_id):
                item_found = item
                break

        if not item_found:
            skipped_names.append(model_name)
            debug_print(f"Skipped model {model_name} ({model_id}) — not found in json_data")
            continue

        desc = item_found['description']
        content_type = item_found['type']
        is_nsfw = is_model_nsfw(item_found)
        creator = item_found.get('creator', {})
        model_uploader = creator.get('username', 'Unknown')
        versions_list = item_found.get('modelVersions', [])

        if not versions_list:
            skipped_names.append(model_name)
            continue

        model_folder = _api.contenttype_folder(content_type, desc)

        # Resolve which versions to download (one per installed family for multi-family models)
        versions_to_download = _resolve_versions_to_download(versions_list, model_folder)

        for version in versions_to_download:
            version_name = version.get('name')
            version_id = version.get('id')
            output_basemodel = version.get('baseModel')
            files = version.get('files', [])
            primary_file = next((f for f in files if f.get('primary', False)), None)

            if primary_file:
                model_filename = _api.cleaned_name(primary_file.get('name'))
                model_sha256 = primary_file.get('hashes', {}).get('SHA256')
                dl_url = primary_file.get('downloadUrl')
            elif files:
                model_filename = _api.cleaned_name(files[0].get('name'))
                model_sha256 = files[0].get('hashes', {}).get('SHA256')
                dl_url = files[0].get('downloadUrl')
            else:
                skipped_names.append(f"{model_name} ({version_name})")
                continue

            # Check if auto-organization is enabled
            auto_organize = getattr(opts, 'civitai_neo_auto_organize', False)
            from_batch = True  # default: treat as batch (no manual subfolder)

            if auto_organize and output_basemodel:
                # Use auto-organization: determine folder from baseModel
                from scripts.civitai_file_manage import normalize_base_model
                base_folder = normalize_base_model(output_basemodel)
                if base_folder:
                    if not base_folder.startswith(os.sep):
                        base_folder = os.sep + base_folder
                    install_path = str(model_folder) + base_folder
                else:
                    install_path = str(model_folder)
            else:
                # Original behavior: use custom subfolders or default
                default_subfolder = _api.sub_folder_value(content_type, desc)
                if default_subfolder != 'None':
                    default_subfolder = _file.convertCustomFolder(default_subfolder, output_basemodel, is_nsfw, model_uploader, model_name, model_id, version_name, version_id)

                if subfolder and subfolder != 'None' and subfolder != 'Only available if the selected files are of the same model type':
                    from_batch = False
                    if platform.system() == 'Windows':
                        subfolder = re.sub(r'[/:*?"<>|]', '', subfolder)
                    if not subfolder.startswith(os.sep):
                        subfolder = os.sep + subfolder
                    install_path = str(model_folder) + subfolder
                else:
                    from_batch = True
                    if default_subfolder != 'None':
                        install_path = str(model_folder) + default_subfolder
                    else:
                        install_path = str(model_folder)

            model_item = create_model_item(dl_url, model_filename, install_path, model_name, version_name, model_sha256, model_id, create_json, from_batch)
            if model_item:
                gl.download_queue.append(model_item)
                total_count += 1
            else:
                skipped_names.append(f"{model_name} ({version_name})")
                debug_print(f"Skipped model {model_name} ({model_id}){f' version {version_name}' if version_name else ''} due to processing error")

    html = download_manager_html(current_html)
    if skipped_names:
        names_str = ', '.join(skipped_names[:5]) + ('…' if len(skipped_names) > 5 else '')
        html = html.rsplit('</div>', 1)[0] + (
            f'<div style="background:#3a1a1a;border:1px solid #8b3030;border-radius:6px;'
            f'padding:8px 12px;margin:4px 0;color:#ff9999;font-size:13px;">'
            f'⚠️ Skipped {len(skipped_names)} model(s) — could not load info: {names_str}'
            f'</div>'
        ) + '</div>'

    return (
        gr.update(interactive=False, visible=False),  # Download Button
        gr.update(interactive=True, visible=True),  # Cancel Button
        gr.update(interactive=True if len(gl.download_queue) > 1 else False, visible=True),  # Cancel All Button
        gr.update(value=number),  # Download Start Trigger
        gr.update(value='<div style="min-height: 100px;"></div>'),  # Download Progress
        gr.update(value=html)  # Download Manager HTML
    )


def gr_progress_threadable():
    """
    Gradio progress bars can no longer be updated from a separate thread,
    so we need to use this to update them from the main thread.
    """

    # Gradio 3 does not need a wrapper
    if not hasattr(gr, '__version__') or int(gr.__version__.split('.')[0]) <= 3:
        return gr.Progress()

    gr_progress = gr.Progress()
    value = [0, None, False]  # progress, desc, has_update

    def progress(p, desc=None):
        value[0] = p
        value[1] = desc
        value[2] = True

    def _update_progress():
        if value[2]:
            gr_progress(value[0], desc=value[1])
            value[2] = False

    def join(thread):
        _update_progress()
        while thread.is_alive():
            thread.join(timeout=0.1)
            _update_progress()

    progress.join = join

    return progress


def download_start(download_start, dl_url, model_filename, install_path, model_string, version_name, model_sha256, model_id, create_json, current_html):
    global total_count, current_count
    if model_string:
        model_name, _ = _api.extract_model_info(model_string)
    model_item = create_model_item(dl_url, model_filename, install_path, model_name, version_name, model_sha256, model_id, create_json)

    if model_item:
        gl.download_queue.append(model_item)
    else:
        return (
            gr.update(interactive=True, visible=True),  # Download Button
            gr.update(interactive=False, visible=False),  # Cancel Button
            gr.update(interactive=False, visible=False),  # Cancel All Button
            gr.update(value=download_start),  # Download Start Trigger
            gr.update(value='<div style="min-height: 100px;"></div>'),  # Download Progress
            gr.update(value=current_html)  # Download Manager HTML
        )

    if len(gl.download_queue) > 1:
        number = download_start
        total_count += 1
    else:
        number = random_number(download_start)
        total_count = 1
        current_count = 0

    html = download_manager_html(current_html)

    return (
        gr.update(interactive=False, visible=True),  # Download Button
        gr.update(interactive=True, visible=True),  # Cancel Button
        gr.update(interactive=True if len(gl.download_queue) > 1 else False, visible=True),  # Cancel All Button
        gr.update(value=number),  # Download Start Trigger
        gr.update(value='<div style="min-height: 100px;"></div>'),  # Download Progress
        gr.update(value=html)  # Download Manager HTML
    )

def download_finish(model_filename, version, model_id):
    if model_id:
        model_id = int(model_id)
        model_versions = _api.update_model_versions(model_id)
    else:
        model_versions = None
    if model_versions:
        version_choices = model_versions.get('choices', [])
    else:
        version_choices = []
    prev_version = gl.last_version + " [Installed]"

    if prev_version in version_choices:
        version = prev_version
        Del = True
        Down = False
    else:
        Del = False
        Down = True

    if gl.cancel_status:
        Del = False
        Down = True

    gl.download_fail = False
    gl.cancel_status = False

    return (
        gr.update(interactive=model_filename, visible=Down, value="Download model"),  # Download Button
        gr.update(interactive=False, visible=False),  # Cancel Button
        gr.update(interactive=False, visible=False),  # Cancel All Button
        gr.update(interactive=Del, visible=Del),  # Delete Button
        gr.update(value='<div style="min-height: 0px;"></div>'),  # Download Progress
        gr.update(value=version, choices=version_choices)  # Version Dropdown
    )

def download_cancel():
    gl.cancel_status = True
    gl.download_fail = True
    if gl.download_queue:
        item = gl.download_queue[0]
    else:
        item = None

    _not_downloading.wait(timeout=60)
    if item:
        model_string = f"{item['model_name']} ({item['model_id']})"
        _file.delete_model(0, item['model_filename'], model_string, item['version_name'], False, model_ver=item['model_versions'], model_json=item['model_json'])
    return

def download_cancel_all():
    gl.cancel_status = True
    gl.download_fail = True

    if gl.download_queue:
        item = gl.download_queue[0]
    else:
        item = None

    _not_downloading.wait(timeout=60)
    if item:
        model_string = f"{item['model_name']} ({item['model_id']})"
        _file.delete_model(0, item['model_filename'], model_string, item['version_name'], False, model_ver=item['model_versions'], model_json=item['model_json'])
    _dl_log.log_all_cancelled()
    gl.download_queue = []
    return

def convert_size(size):
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} GB"

def get_download_link(url, model_id):
    headers = _api.get_headers(model_id)
    proxies, ssl = _api.get_proxies()

    response = requests.get(url, headers=headers, allow_redirects=False, proxies=proxies, verify=ssl)

    if 300 <= response.status_code <= 308:
        if 'login?returnUrl' in response.text and 'reason=download-auth' in response.text:
            return 'NO_API'

        download_link = response.headers['Location']
        return download_link
    else:
        return None

def download_file(url, file_path, install_path, model_id, progress=gr.Progress() if queue else None):
    try:
        disable_dns = getattr(opts, 'disable_dns', False)
        split_aria2 = getattr(opts, 'split_aria2', 64)
        max_retries = 5
        gl.download_fail = False
        aria2_rpc_url = "http://localhost:24000/jsonrpc"

        file_name = os.path.basename(file_path)

        ## === ANXETY EDITs ===
        # Find the model item in the download queue (by model_id and file_name)
        early_access = False
        for item in gl.download_queue:
            if int(item.get('model_id', -1)) == int(model_id):
                model_json = item.get('model_json', {})
                items = model_json.get('items', [])
                if items and 'modelVersions' in items[0]:
                    version = items[0]['modelVersions'][0]
                    if is_early_access(version):
                        early_access = True
                break

        if early_access:
            msg = f"File: '{file_name}' is marked as Early Access on CivitAI. You need to purchase this model to download it."
            print(msg)
            gl.download_fail = 'EARLY_ACCESS'
            if progress is not None:
                progress(0, desc=msg)
                time.sleep(5)
            return

        download_link = get_download_link(url, model_id)
        if not download_link:
            msg = f"File: '{file_name}' not found on CivitAI servers, it looks like the file is not available for download."
            print(msg)
            gl.download_fail = True
            return

        elif download_link == 'NO_API':
            msg = f"File: '{file_name}' requires a personal CivitAI API to be downloaded, you can set your own API key in the CivitAI Browser+ settings in the SD-WebUI settings tab"
            print(msg)
            gl.download_fail = 'NO_API'
            if progress is not None:
                progress(0, desc=msg)
                time.sleep(5)
            return

        if os.path.exists(file_path):
            _file.handle_existing_model_file(file_path)

        if disable_dns:
            dns = 'false'
        else:
            dns = 'true'

        options = {
            'dir': install_path,
            'max-connection-per-server': str(f"{split_aria2}"),
            'split': str(f"{split_aria2}"),
            'async-dns': dns,
            'out': file_name
        }

        payload = json.dumps({
            'jsonrpc': '2.0',
            'id': '1',
            'method': 'aria2.addUri',
            'params': ['token:' + rpc_secret, [download_link], options]
        })

        try:
            response = requests.post(aria2_rpc_url, data=payload)
            data = json.loads(response.text)
            if 'result' not in data:
                raise ValueError(f"Failed to start download: {data}")
            gid = data['result']
        except Exception as e:
            print(f"Failed to start download: {e}")
            gl.download_fail = True
            return

        while True:
            if gl.cancel_status:
                payload = json.dumps({
                    'jsonrpc': '2.0',
                    'id': '1',
                    'method': 'aria2.remove',
                    'params': ['token:' + rpc_secret, gid]
                })
                requests.post(aria2_rpc_url, data=payload)
                if progress != None:
                    progress(0, desc="Download cancelled.")
                return

            try:
                payload = json.dumps({
                    'jsonrpc': '2.0',
                    'id': '1',
                    'method': 'aria2.tellStatus',
                    'params': ['token:' + rpc_secret, gid]
                })

                response = requests.post(aria2_rpc_url, data=payload)
                status_info = json.loads(response.text)['result']

                total_length = int(status_info['totalLength'])
                completed_length = int(status_info['completedLength'])
                download_speed = int(status_info['downloadSpeed'])

                progress_percent = (completed_length / total_length) * 100 if total_length else 0

                remaining_size = total_length - completed_length
                if download_speed > 0:
                    eta_seconds = remaining_size / download_speed
                    eta_formatted = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
                else:
                    eta_formatted = "XX:XX:XX"
                if progress != None:
                    progress(progress_percent / 100, desc=f"Downloading: {file_name} - {convert_size(completed_length)}/{convert_size(total_length)} - Speed: {convert_size(download_speed)}/s - ETA: {eta_formatted} - Queue: {current_count}/{total_count}")

                if status_info['status'] == 'complete':
                    msg = f"Model saved to: {file_path}"
                    print(msg)
                    if progress != None:
                        progress(1, desc=msg)
                    gl.download_fail = False
                    return

                if status_info['status'] == 'error':
                    if progress != None:
                        progress(0, desc=f"Encountered an error during download of: '{file_name}' Please try again.")
                    gl.download_fail = True
                    return

                time.sleep(0.25)

            except Exception as e:
                print(f"Error occurred during Aria2 status update: {e}")
                max_retries -= 1
                if max_retries == 0:
                    if progress != None:
                        progress(0, desc=f"Encountered an error during download of: '{file_name}' Please try again.")
                    gl.download_fail = True
                    return
                # #5 Aria2 RPC unreachable — restart and re-add the download
                print("Aria2 RPC unreachable, attempting to reconnect...")
                start_aria2_rpc()
                time.sleep(3)
                try:
                    _reconnect_resp = requests.post(aria2_rpc_url, timeout=5, data=json.dumps({
                        'jsonrpc': '2.0', 'id': '1', 'method': 'aria2.addUri',
                        'params': ['token:' + rpc_secret, [download_link], options]
                    }))
                    _reconnect_data = json.loads(_reconnect_resp.text)
                    if 'result' in _reconnect_data:
                        gid = _reconnect_data['result']
                        print(f"Aria2 reconnected, resumed download of '{file_name}'.")
                except Exception:
                    pass
                time.sleep(2)
    except:
        if progress != None:
            progress(0, desc=f"Encountered an error during download of: '{file_name}' Please try again.")
        gl.download_fail = True
        if os.path.exists(file_path):
            os.remove(file_path)
        time.sleep(5)

def info_to_json(install_path, model_id, model_sha256, unpackList=None):
    json_file = os.path.splitext(install_path)[0] + '.json'
    data = _api.safe_json_load(json_file) or {}
    data.update({
        'modelId': model_id,
        'sha256': model_sha256
    })
    if unpackList:
        data['unpackList'] = unpackList

    _api.safe_json_save(json_file, data)

def download_file_old(url, file_path, model_id, progress=gr.Progress() if queue else None):
    try:
        gl.download_fail = False
        max_retries = 5
        if os.path.exists(file_path):
            os.remove(file_path)

        downloaded_size = 0
        tokens = re.split(re.escape(os.sep), file_path)
        file_name_display = tokens[-1]
        start_time = time.time()
        last_update_time = 0
        update_interval = 0.25

        download_link = get_download_link(url, model_id)
        if not download_link:
            msg = f"File: '{file_name_display}' not found on CivitAI servers, it looks like the file is not available for download."
            print(msg)
            if progress != None:
                progress(0, desc=msg)
                time.sleep(5)
            gl.download_fail = True
            return

        elif download_link == 'NO_API':
            msg = f"File: '{file_name_display}' requires a personal CivitAI API key to be downloaded, you can set your own API key in the CivitAI Browser+ settings in the SD-WebUI settings tab"
            print(msg)
            gl.download_fail = 'NO_API'
            if progress != None:
                progress(0, desc=msg)
                time.sleep(5)
            return

        headers = _api.get_headers(model_id, True)
        proxies, ssl = _api.get_proxies()

        while True:
            if gl.cancel_status:
                if progress != None:
                    progress(0, desc='Download cancelled.')
                return
            if os.path.exists(file_path):
                downloaded_size = os.path.getsize(file_path)
                headers['Range'] = f"bytes={downloaded_size}-"

            with open(file_path, 'ab') as f:
                while gl.isDownloading:
                    try:
                        if gl.cancel_status:
                            if progress != None:
                                progress(0, desc='Download cancelled.')
                            return
                        try:
                            if gl.cancel_status:
                                if progress != None:
                                    progress(0, desc='Download cancelled.')
                                return
                            response = requests.get(download_link, headers=headers, stream=True, timeout=10, proxies=proxies, verify=ssl)
                            if response.status_code == 404:
                                if progress != None:
                                    progress(0, desc=f"Encountered an error during download of: {file_name_display}, file is not found on CivitAI servers.")
                                gl.download_fail = True
                                return
                            total_size = int(response.headers.get('Content-Length', 0))
                        except:
                            raise TimeOutFunction('Timed Out')

                        if total_size == 0:
                            total_size = downloaded_size

                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                if gl.cancel_status:
                                    if progress != None:
                                        progress(0, desc='Download cancelled.')
                                    return
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                elapsed_time = time.time() - start_time
                                download_speed = downloaded_size / elapsed_time
                                remaining_size = total_size - downloaded_size
                                if download_speed > 0:
                                    eta_seconds = remaining_size / download_speed
                                    eta_formatted = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))
                                else:
                                    eta_formatted = 'XX:XX:XX'
                                current_time = time.time()
                                if current_time - last_update_time >= update_interval:
                                    if progress != None:
                                        progress(downloaded_size / total_size, desc=f"Downloading: {file_name_display} {convert_size(downloaded_size)} / {convert_size(total_size)} - Speed: {convert_size(int(download_speed))}/s - ETA: {eta_formatted} - Queue: {current_count}/{total_count}")
                                    last_update_time = current_time
                                if gl.isDownloading == False:
                                    response.close
                                    break
                        downloaded_size = os.path.getsize(file_path)
                        break

                    except TimeOutFunction:
                        if progress != None:
                            progress(0, desc='CivitAI API did not respond, retrying...')
                        max_retries -= 1
                        if max_retries == 0:
                            if progress != None:
                                progress(0, desc=f"Encountered an error during download of: {file_name_display}, please try again.")
                            gl.download_fail = True
                            return
                        time.sleep(5)

            if (gl.isDownloading == False):
                break

            gl.isDownloading = False
            downloaded_size = os.path.getsize(file_path)
            if downloaded_size >= total_size:
                if not gl.cancel_status:
                    msg = f"Model saved to: {file_path}"
                    print(msg)
                    if progress != None:
                        progress(1, desc=msg)
                    gl.download_fail = False
                    return

            else:
                if progress != None:
                    progress(0, desc=f"Encountered an error during download of: {file_name_display}, please try again.")
                print(f"File download failed: {file_name_display}")
                gl.download_fail = True
                if os.path.exists(file_path):
                    os.remove(file_path)
    except:
        if progress != None:
            progress(0, desc=f"Encountered an error during download of: {file_name_display}, please try again.")
        gl.download_fail = True
        if os.path.exists(file_path):
            os.remove(file_path)
        time.sleep(5)

def download_create_thread(download_finish, queue_trigger, progress=gr_progress_threadable() if queue else None):
    global current_count
    current_count += 1

    if not gl.download_queue:
        return (
            gr.update(),  # Download Progress HTML
            gr.update(value=None),  # Current Model
            gr.update(value=random_number(download_finish)),  # Download Finish Trigger
            gr.update(value=queue_trigger),  # Queue Trigger
            gr.update(interactive=False)  # Cancel All Button
        )

    item = gl.download_queue[0]
    gl.cancel_status = False
    use_aria2 = getattr(opts, 'use_aria2', True)
    unpack_zip = getattr(opts, 'unpack_zip', False)
    save_all_images = getattr(opts, 'auto_save_all_img', False)
    gl.recent_model = item['model_name']
    gl.last_version = item['version_name']

    # #2 Lazy API fetch: deferred from enqueue time for batch performance
    if not item.get('_api_ready'):
        _lazy_versions = _api.update_model_versions(item['model_id'])
        if _lazy_versions:
            item['model_versions'] = _lazy_versions
        try:
            _lazy_result = _api.update_model_info(None, (item['model_versions'] or {}).get('value'), False, item['model_id'])
            item['preview_html'] = _lazy_result[0].get('value', '') if isinstance(_lazy_result[0], dict) else ''
            item['existing_path'] = _lazy_result[11].get('value', item['install_path']) if isinstance(_lazy_result[11], dict) else item['install_path']
        except Exception as _e:
            debug_print(f"[Lazy fetch] Could not load API data for {item['model_name']}: {_e}")
        item['_api_ready'] = True

    # Fix #3: do not mutate item dict — use a local effective path
    effective_install_path = item['existing_path'] if item['from_batch'] else item['install_path']

    gl.isDownloading = True
    _not_downloading.clear()  # signal: download in progress
    _dl_log.log_downloading(item['dl_id'])
    _file.make_dir(effective_install_path)

    path_to_new_file = os.path.join(effective_install_path, item['model_filename'])

    if use_aria2 and os_type != 'Darwin':
        thread = threading.Thread(target=download_file, args=(item['dl_url'], path_to_new_file, effective_install_path, item['model_id'], progress))
    else:
        thread = threading.Thread(target=download_file_old, args=(item['dl_url'], path_to_new_file, item['model_id'], progress))
    thread.start()
    if progress != None and hasattr(progress, 'join'):
        progress.join(thread)
    else:
        thread.join()

    # Fix #1: SHA256 integrity check after download
    if not gl.cancel_status and not gl.download_fail and item.get('model_sha256') and os.path.exists(path_to_new_file):
        if progress is not None:
            progress(0.99, desc=f"Verifying integrity: {item['model_filename']}...")
        sha256_hash = hashlib.sha256()
        with open(path_to_new_file, 'rb') as _f:
            for _chunk in iter(lambda: _f.read(1024 * 1024), b''):
                sha256_hash.update(_chunk)
        actual_sha256 = sha256_hash.hexdigest().upper()
        if actual_sha256 != item['model_sha256'].upper():
            print(f"SHA256 mismatch for '{item['model_filename']}': expected {item['model_sha256'][:12]}…, got {actual_sha256[:12]}…")
            gl.download_fail = True
            if progress is not None:
                progress(0, desc=f"Integrity check failed for '{item['model_filename']}' — file may be corrupted.")
        else:
            # Pre-populate Forge's SHA256 cache so the model loads instantly without recalculation
            try:
                from modules import hashes as _hashes
                _h = _hashes.cache("hashes")
                _h[path_to_new_file] = {
                    "mtime": os.path.getmtime(path_to_new_file),
                    "sha256": actual_sha256.lower()
                }
                _hashes.dump_cache()
                debug_print(f"[SHA256 cache] Pre-cached for '{item['model_filename']}' — Forge will skip hash calculation on first load.")
            except Exception as _e:
                debug_print(f"[SHA256 cache] Could not pre-populate Forge hash cache: {_e}")

    if not gl.cancel_status or gl.download_fail:
        if os.path.exists(path_to_new_file):
            unpackList = []
            if unpack_zip:
                try:
                    if path_to_new_file.endswith('.zip'):
                        directory = Path(os.path.dirname(path_to_new_file))
                        zip_handler = ZipHandler(path_to_new_file)

                        for _, decoded_name in zip_handler.name_map.items():
                            unpackList.append(decoded_name)

                        zip_handler.extract_all(directory)
                        zip_handler.zip_ref.close()

                        print(f"Successfully extracted {item['model_filename']} to {directory}")
                        os.remove(path_to_new_file)
                except ImportError:
                    print('Python module "ZipUnicode" has not been imported correctly, cannot extract zip file. Please try to restart or install it manually.')
                except Exception as e:
                    print(f"Failed to extract {item['model_filename']} with error: {e}")
            if not gl.cancel_status:
                if item['create_json']:
                    _file.save_model_info(effective_install_path, item['model_filename'], item['sub_folder'], item['model_sha256'], item['preview_html'], api_response=item['model_json'])
                info_to_json(path_to_new_file, item['model_id'], item['model_sha256'], unpackList)
                _file.save_preview(path_to_new_file, item['model_json'], True, item['model_sha256'])
                if save_all_images:
                    _file.save_images(item['preview_html'], item['model_filename'], effective_install_path, item['sub_folder'], api_response=item['model_json'])

    base_name = os.path.splitext(item['model_filename'])[0]
    base_name_preview = base_name + '.preview'

    if gl.download_fail:
        for root, dirs, files in os.walk(effective_install_path, followlinks=True):
            for file in files:
                file_base_name = os.path.splitext(file)[0]
                if file_base_name == base_name or file_base_name == base_name_preview:
                    path_file = os.path.join(root, file)
                    os.remove(path_file)

        if gl.cancel_status:
            print(f"Cancelled download of '{item['model_filename']}'")
        else:
            if gl.download_fail != 'NO_API':
                print(f"Error occured during download of '{item['model_filename']}'")

    if gl.cancel_status:
        card_name = None
    else:
        model_string = f"{item['model_name']} ({item['model_id']})"
        (card_name, _, _) = _file.card_update(item['model_versions'], model_string, item['version_name'], True)

    # Log final download status before removing from queue
    if gl.cancel_status:
        _dl_log.log_cancelled(item['dl_id'])
    elif gl.download_fail:
        _dl_log.log_failed(item['dl_id'])
    else:
        _dl_log.log_completed(item['dl_id'])

    if len(gl.download_queue) != 0:
        gl.download_queue.pop(0)
    gl.isDownloading = False
    _not_downloading.set()  # signal: download finished, safe to cancel/cleanup
    time.sleep(2)

    if len(gl.download_queue) == 0:
        finish_nr = random_number(download_finish)
        queue_nr = queue_trigger
    else:
        finish_nr = download_finish
        queue_nr = random_number(queue_trigger)

    return (
        gr.update(),  # Download Progress HTML
        gr.update(value=card_name),  # Current Model
        gr.update(value=finish_nr),  # Download Finish Trigger
        gr.update(value=queue_nr),  # Queue Trigger
        gr.update(interactive=True if len(gl.download_queue) != 1 else False)  # Cancel All Button
    )

def remove_from_queue(dl_id):
    global total_count
    for item in gl.download_queue:
        if int(dl_id) == int(item['dl_id']):
            gl.download_queue.remove(item)
            total_count -= 1
            _dl_log.log_cancelled(int(dl_id))
            return

def arrange_queue(input):
    id_and_index = input.split('.')
    dl_id = int(id_and_index[0])
    index = int(id_and_index[1]) + 1
    for item in gl.download_queue:
        if int(item['dl_id']) == dl_id:
            current_item = gl.download_queue.pop(gl.download_queue.index(item))
            gl.download_queue.insert(index, current_item)
            break

def get_style(size, left_border):
    return f"flex-grow: {size};" + ("border-left: 1px solid var(--border-color-primary);" if left_border else '') + "padding: 5px 10px 5px 10px;width: 0;align-self: center;"

def download_manager_html(current_html):
    html = current_html.rsplit('</div>', 1)[0]
    pattern = r'dl_id="(\d+)"'
    matches = re.findall(pattern, html)
    existing_item_ids = [int(match) for match in matches]

    for item in gl.download_queue:
        if item['dl_id'] not in existing_item_ids:
            download_item = (
                f'<div class="civitai_dl_item" dl_id="{item["dl_id"]}" style="display: flex; font-size: var(--section-header-text-size);">'
                f'<div class="dl_name" style="{get_style(1, False)}"><span title="{item["model_name"]}">{item["model_name"]}</span></div>'
                f'<div class="dl_ver" style="{get_style(0.75, True)}"><span title="{item["version_name"]}">{item["version_name"]}</span></div>'
                f'<div class="dl_path" style="{get_style(1.5, True)}"><span title="{item["install_path"]}">{item["install_path"]}</span></div>'
                f'<div class="dl_stat" style="{get_style(1.5, True)}"><div class="dl_progress_bar" style="width:0%">In queue...</div></div>'
                f'<div class="dl_action_btn" style="{get_style(0.3, True)}text-align: center;"><span onclick="removeDlItem({item["dl_id"]}, this)" class="civitai-btn-text" style="font-size: larger;">Remove</span></div>'
                '</div>'
            )
            html += download_item
    html += '</div>'

    return html


# ─── Queue Restore  (called from civitai_gui.py) ─────────────────────────────

def get_interrupted_downloads_json():
    """Called by Gradio .load() on every page load.
    Returns a JSON string of interrupted items, or '' if none.
    Also purges stale completed/cancelled entries from the log file."""
    _dl_log.purge_old_entries(days=7)
    interrupted = _dl_log.get_interrupted()
    if not interrupted:
        return ''
    import json as _json
    return _json.dumps(interrupted)


def dismiss_interrupted_downloads():
    """Called when the user dismisses the restore banner without restoring."""
    _dl_log.dismiss_interrupted()
    return ''


def _restore_queue_item(data):
    """Rebuild a full queue item dict from a log entry, fetching fresh API data."""
    model_id = int(data['model_id'])

    # Duplicate guard
    for existing in gl.download_queue:
        if existing.get('dl_url') == data['dl_url']:
            return None

    model_versions = _api.update_model_versions(model_id)
    if not model_versions:
        return None

    preview_html_val = ''
    existing_path_val = data['install_path']
    model_json = {'items': []}

    try:
        result = _api.update_model_info(None, model_versions.get('value'), False, model_id)
        # update_model_info returns a 13-tuple; index 0 = preview_html, index 11 = existing_path
        preview_html_val = result[0].get('value', '') if isinstance(result[0], dict) else ''
        existing_path_val = result[11].get('value', data['install_path']) if isinstance(result[11], dict) else data['install_path']

        # Re-fetch model JSON for metadata saving
        api_url = f'https://civitai.com/api/v1/models/{model_id}'
        raw = _api.request_civit_api(api_url)
        if raw and isinstance(raw, dict):
            model_json = {'items': [raw]}
    except Exception as e:
        debug_print(f"[Restore] Could not fetch API data for model {model_id}: {e}")

    global dl_manager_count
    dl_manager_count += 1

    return {
        'dl_id':          dl_manager_count,
        'dl_url':         data['dl_url'],
        'model_filename': data['model_filename'],
        'install_path':   data['install_path'],
        'model_name':     data['model_name'],
        'version_name':   data.get('version_name', ''),
        'model_sha256':   data.get('model_sha256'),
        'model_id':       model_id,
        'create_json':    data.get('create_json', True),
        'model_json':     model_json,
        'model_versions': model_versions,
        'preview_html':   preview_html_val,
        'existing_path':  existing_path_val,
        'from_batch':     data.get('from_batch', False),
        'sub_folder':     data.get('sub_folder', ''),
        '_api_ready':     True,  # already fetched above
    }


def restore_interrupted_to_queue(current_html):
    """Re-enqueue all interrupted downloads and kick off the download chain.
    Returns the same 6-tuple as download_start / selected_to_queue so the GUI
    wires up identically."""
    global total_count, current_count

    interrupted = _dl_log.get_interrupted()
    if not interrupted:
        return (
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(),
            gr.update(value=current_html),
        )

    number = random_number()
    total_count = 0
    current_count = 0

    for data in interrupted:
        item = _restore_queue_item(data)
        if item:
            gl.download_queue.append(item)
            total_count += 1

    _dl_log.dismiss_interrupted()  # don't show banner again unless new interruptions

    if not gl.download_queue:
        return (
            gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(),
            gr.update(value=current_html),
        )

    html = download_manager_html(current_html)

    return (
        gr.update(interactive=False, visible=False),   # Download Button
        gr.update(interactive=True, visible=True),     # Cancel Button
        gr.update(interactive=len(gl.download_queue) > 1, visible=True),  # Cancel All Button
        gr.update(value=number),                       # Download Start Trigger
        gr.update(value='<div style="min-height: 100px;"></div>'),  # Download Progress
        gr.update(value=html),                         # Download Manager HTML
    )