import urllib.request
import urllib.error
import requests
import hashlib
import base64
import errno
import json
import time
import re
import os
import io
import shutil
import gradio as gr
from urllib.parse import urlparse
from pathlib import Path
from PIL import Image

# === WebUI imports ===
from modules.shared import cmd_opts, opts

# === Extension imports ===
import scripts.civitai_download as _download
import scripts.civitai_file_manage as _file
import scripts.civitai_global as gl
import scripts.civitai_api as _api
from scripts.civitai_global import print, debug_print


IS_KAGGLE = 'KAGGLE_URL_BASE' in os.environ


try:
    from send2trash import send2trash
except ImportError:
    print('Python module "send2trash" has not been imported correctly, please try to restart or install it manually.')
try:
    from bs4 import BeautifulSoup
except ImportError:
    print('Python module "BeautifulSoup" has not been imported correctly, please try to restart or install it manually.')

gl.init()

css_path = Path(__file__).resolve().parents[1] / 'style_html.css'
no_update = False
from_tag = False
from_ver = False
from_installed = False
try:
    queue = not cmd_opts.no_gradio_queue
except AttributeError:
    queue = not cmd_opts.disable_queue
except:
    queue = True

def delete_model(delete_finish=None, model_filename=None, model_string=None, list_versions=None, sha256=None, selected_list=None, model_ver=None, model_json=None):
    deleted = False
    model_id = None

    if model_string:
        _, model_id = _api.extract_model_info(model_string)

    if not model_ver:
        model_versions = _api.update_model_versions(model_id)
    else:
        model_versions = model_ver

    (model_name, ver_value, ver_choices) = _file.card_update(model_versions, model_string, list_versions, False)
    if not model_json:
        if model_id != None:
            selected_content_type = None
            for item in gl.json_data['items']:
                if int(item['id']) == int(model_id):
                    selected_content_type = item['type']
                    desc = item['description']
                    break

            if selected_content_type == None:
                print('Model ID not found in json_data. (delete_model)')
                return
    else:
        for item in model_json['items']:
            selected_content_type = item['type']
            desc = item['description']

    model_folder = os.path.join(_api.contenttype_folder(selected_content_type, desc))

    # Delete based on provided SHA-256 hash
    if sha256:
        sha256_upper = sha256.upper()
        for root, _, files in os.walk(model_folder, followlinks=True):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    data = _api.safe_json_load(file_path)
                    if data:
                        file_sha256 = data.get('sha256', '').upper()
                    else:
                        file_sha256 = '0'

                    if file_sha256 == sha256_upper:
                        unpack_list = data.get('unpackList', [])
                        for unpacked_file in unpack_list:
                            unpacked_file_path = os.path.join(root, unpacked_file)
                            if os.path.isfile(unpacked_file_path):
                                try:
                                    send2trash(unpacked_file_path)
                                    print(f"File moved to trash based on unpackList: {unpacked_file_path}")
                                except:
                                    os.remove(unpacked_file_path)
                                    print(f"File deleted based on unpackList: {unpacked_file_path}")

                        base_name, _ = os.path.splitext(file)
                        if os.path.isfile(file_path):
                            try:
                                send2trash(file_path)
                                print(f"Model moved to trash based on SHA-256: {file_path}")
                            except:
                                os.remove(file_path)
                                print(f"Model deleted based on SHA-256: {file_path}")
                            delete_associated_files(root, base_name)
                            deleted = True

    # Fallback to delete based on filename if not deleted based on SHA-256
    filename_to_delete = os.path.splitext(model_filename)[0]
    aria2_file = model_filename + '.aria2'
    if not deleted:
        for root, dirs, files in os.walk(model_folder, followlinks=True):
            for file in files:
                current_file_name = os.path.splitext(file)[0]
                if filename_to_delete == current_file_name or aria2_file == file:
                    path_file = os.path.join(root, file)
                    if os.path.isfile(path_file):
                        try:
                            send2trash(path_file)
                            print(f"Model moved to trash based on filename: {path_file}")
                        except:
                            os.remove(path_file)
                            print(f"Model deleted based on filename: {path_file}")
                        delete_associated_files(root, current_file_name)

    number = _download.random_number(delete_finish)

    btnDwn = not selected_list or selected_list == '[]'

    return (
        gr.update(interactive=btnDwn, visible=btnDwn),  # Download Button
        gr.update(interactive=False, visible=False),  # Cancel Button
        gr.update(interactive=False, visible=False),  # Delete Button
        gr.update(value=number),  # Delete Finish Trigger
        gr.update(value=model_name),  # Current Model
        gr.update(value=ver_value, choices=ver_choices)  # Version List
    )

def delete_installed_by_sha256(sha256, delete_finish=None):
    """
    Simplified delete function for installed models using only SHA256.
    Searches all model folders for a match and deletes the model.
    """
    if not sha256:
        print("No SHA256 provided for deletion")
        return gr.update(value=_download.random_number(delete_finish))
    
    sha256_upper = sha256.upper()
    
    # Get all content types to search
    content_types = ['Checkpoint', 'LORA', 'LoCon', 'DoRA', 'VAE', 'Controlnet', 'Poses', 
                     'TextualInversion', 'Upscaler', 'MotionModule', 'Workflows', 'Detection', 'Other', 'Wildcards']
    
    folders_to_check = []
    for content_type in content_types:
        if content_type == 'Upscaler':
            for desc in ['SWINIR', 'REALESRGAN', 'GFPGAN', 'BSRGAN', 'ESRGAN']:
                folder = _api.contenttype_folder('Upscaler', desc)
                if folder and folder not in folders_to_check:
                    folders_to_check.append(folder)
        else:
            folder = _api.contenttype_folder(content_type)
            if folder and folder not in folders_to_check:
                folders_to_check.append(folder)
    
    deleted = False
    for model_folder in folders_to_check:
        if deleted:
            break
        for root, _, files in os.walk(model_folder, followlinks=True):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    data = _api.safe_json_load(file_path)
                    if not data:
                        continue
                    
                    file_sha256 = data.get('sha256', '').upper()
                    if file_sha256 == sha256_upper:
                        # Found matching model!
                        model_name = data.get('model', {}).get('name', 'Unknown Model')
                        print(f"Found model to delete: {model_name} (SHA256: {sha256_upper})")
                        
                        # Get base filename (without extension)
                        model_filename = data.get('file', {}).get('name', '')
                        if not model_filename:
                            # Try to find associated model file
                            json_base = os.path.splitext(file)[0]
                            model_extensions = ['.safetensors', '.ckpt', '.pt', '.pth', '.bin']
                            for ext in model_extensions:
                                potential_model = json_base + ext
                                if os.path.exists(potential_model):
                                    model_filename = os.path.basename(potential_model)
                                    break
                        
                        if model_filename:
                            # Delete model file
                            model_file_path = os.path.join(root, model_filename)
                            if os.path.exists(model_file_path):
                                try:
                                    send2trash(model_file_path)
                                    print(f"Model moved to trash: {model_file_path}")
                                except:
                                    os.remove(model_file_path)
                                    print(f"Model deleted: {model_file_path}")
                                
                                # Delete associated files
                                base_filename = os.path.splitext(model_filename)[0]
                                delete_associated_files(root, base_filename)
                                
                                deleted = True
                                break
                        else:
                            print(f"Could not find model file for JSON: {file_path}")
            
            if deleted:
                break
    
    if deleted:
        print(f"Successfully deleted model with SHA256: {sha256_upper}")
    else:
        print(f"Could not find model with SHA256: {sha256_upper}")
    
    return gr.update(value=_download.random_number(delete_finish))

## === ANXETY EDITs ===
def delete_associated_files(directory, base_name):
    """Deletes related model files in the save directory"""
    # Patterns for associated files
    associated_suffixes = ['', '.preview', '.api_info', '.html']
    image_exts = {'.png', '.jpg', '.jpeg'}

    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        name, ext = os.path.splitext(file)

        # Delete associated files by suffix
        if name in [f'{base_name}{sfx}' for sfx in associated_suffixes]:
            try:
                send2trash(file_path)
                print(f"Associated file moved to trash: {file_path}")
            except Exception:
                os.remove(file_path)
                print(f"Associated file deleted: {file_path}")
            continue

        # Delete images matching pattern: <base_name>_<number>.<ext>
        if name.startswith(f'{base_name}_') and ext.lower() in image_exts:
            suffix = name[len(f'{base_name}_'):]
            if suffix.isdigit():
                try:
                    send2trash(file_path)
                    print(f"Image moved to trash: {file_path}")
                except Exception:
                    os.remove(file_path)
                    print(f"Image deleted: {file_path}")


def _resize_image_bytes(image_bytes, target_size=512):
    """Resize image bytes to target_size on the longer side, keeping aspect ratio"""
    image = Image.open(io.BytesIO(image_bytes))
    width, height = image.size

    if width > height:
        new_size = (target_size, int(height * target_size / width))
    else:
        new_size = (int(width * target_size / height), target_size)

    resized_image = image.resize(new_size, Image.LANCZOS)

    output = io.BytesIO()
    resized_image.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()  # Return bytes, not BytesIO object

def save_preview(file_path, api_response, overwrite_toggle=False, sha256=None):
    proxies, ssl = _api.get_proxies()
    file_path = Path(file_path)
    install_path = file_path.parent
    name = file_path.stem
    json_file = file_path.with_suffix('.json')
    image_path = install_path / f"{name}.preview.png"

    if not overwrite_toggle and image_path.exists():
        return

    if not sha256 and json_file.exists():
        data = json.loads(json_file.read_text(encoding='utf-8'))
        if 'sha256' in data and data['sha256']:
            sha256 = data['sha256'].upper()
    elif sha256:
        sha256 = sha256.upper()

    for item in api_response['items']:
        for version in item['modelVersions']:
            for file_entry in version['files']:
                if file_entry['hashes'].get('SHA256') == sha256:
                    for image in version['images']:
                        if image['type'] == 'image':
                            url_with_width = re.sub(r'/width=\d+', f"/width={image['width']}", image['url'])
                            response = requests.get(url_with_width, proxies=proxies, verify=ssl)

                            if response.status_code == 200:
                                # Check if resize is enabled for saved previews
                                resize_saved = getattr(opts, 'resize_preview_on_save', True)
                                if resize_saved:
                                    resize_size = getattr(opts, 'resize_preview_size', 512)
                                    image_data = _resize_image_bytes(response.content, resize_size)
                                else:
                                    # Save original size
                                    image_data = response.content

                                if IS_KAGGLE:
                                    import sd_image_encryption  # Import Module for Encrypt Image
                                    img = Image.open(io.BytesIO(image_data))
                                    imginfo = img.info or {}
                                    if not all(key in imginfo for key in ['Encrypt', 'EncryptPwdSha']):
                                        sd_image_encryption.EncryptedImage.from_image(img).save(image_path)
                                else:
                                    image_path.write_bytes(image_data)

                                print(f"Preview saved at: {image_path}")
                            else:
                                print(f"Failed to save preview. Status code: {response.status_code}")
                            return

                    print(f"No preview images found for '{name}'")
                    return

def get_image_path(install_path, api_response, sub_folder):
    image_location = getattr(opts, 'image_location', '')
    sub_image_location = getattr(opts, 'sub_image_location', True)
    image_path = install_path
    if api_response:
        json_info = api_response['items'][0]
    else:
        json_info = gl.json_info

    if image_location:
        if sub_image_location:
            desc = json_info['description']
            content_type = json_info['type']
            image_path = os.path.join(_api.contenttype_folder(content_type, desc, custom_folder=image_location))

            if sub_folder and sub_folder != 'None' and sub_folder != 'Only available if the selected files are of the same model type':
                image_path = os.path.join(image_path, sub_folder.lstrip('/').lstrip('\\'))
        else:
            image_path = Path(image_location)
    make_dir(image_path)
    return image_path

def save_images(preview_html, model_filename, install_path, sub_folder, api_response=None):
    image_path = get_image_path(install_path, api_response, sub_folder)
    img_urls = re.findall(r'data-sampleimg="true" src=[\'"]?([^\'" >]+)', preview_html)

    if not img_urls:
        print('No images found to download.')
        return

    # Limit number of images to download
    img_count = getattr(opts, 'save_img_count', 16)
    img_count = max(4, min(64, img_count))
    img_urls = img_urls[:img_count]

    name = os.path.splitext(model_filename)[0]

    # Setup download
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    # Download images
    downloaded_count = 0
    for i, img_url in enumerate(img_urls):
        filename = f"{name}_{i}.png"
        img_url = urllib.parse.quote(img_url, safe=':/=')
        try:
            with urllib.request.urlopen(img_url) as url:
                image_data = url.read()

                # Check if resize is enabled for saved images
                resize_saved = getattr(opts, 'resize_preview_on_save', True)
                if resize_saved:
                    resize_size = getattr(opts, 'resize_preview_size', 512)
                    image_data = _resize_image_bytes(image_data, resize_size)

                img = Image.open(io.BytesIO(image_data))

                if img.mode in ('RGBA', 'LA', 'P'):
                    pass  # Keep transparency
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                save_path = os.path.join(image_path, filename)

                if IS_KAGGLE:
                    import sd_image_encryption
                    imginfo = img.info or {}
                    if not all(key in imginfo for key in ['Encrypt', 'EncryptPwdSha']):
                        sd_image_encryption.EncryptedImage.from_image(img).save(save_path)
                    else:
                        img.save(save_path, 'PNG')
                else:
                    img.save(save_path, 'PNG')

                print(f"Downloaded image: {filename}")
                downloaded_count += 1

        except urllib.error.URLError as e:
            print(f"Error downloading {filename}: {e.reason}")
        except Exception as e:
            print(f"Error processing image {filename}: {e}")

    if downloaded_count > 0:
        print(f"Successfully downloaded {downloaded_count} images to: {image_path}")
    else:
        print('No images were downloaded.')

def card_update(gr_components, model_name, list_versions, is_install):
    if gr_components:
        version_choices = gr_components['choices']
    else:
        print("Couldn't retrieve version, defaulting to installed")
        model_name += '.New'
        return model_name, None, None

    if is_install and not gl.download_fail and not gl.cancel_status:
        version_value_clean = list_versions + ' [Installed]'
        version_choices_clean = [
            version if version + ' [Installed]' != version_value_clean else version_value_clean
            for version in version_choices
        ]
    else:
        version_value_clean = list_versions.replace(' [Installed]', '')
        version_choices_clean = [
            version if version.replace(' [Installed]', '') != version_value_clean else version_value_clean
            for version in version_choices
        ]

    first_version_installed = '[Installed]' in version_choices_clean[0]
    any_later_version_installed = any('[Installed]' in version for version in version_choices_clean[1:])

    if first_version_installed:
        model_name += '.New'
    elif any_later_version_installed:
        model_name += '.Old'
    else:
        model_name += '.None'

    return model_name, version_value_clean, version_choices_clean

def list_files(folders):
    model_files = []
    extensions = ['.pt', '.ckpt', '.pth', '.safetensors', '.th', '.zip', '.vae']

    for folder in folders:
        if folder and os.path.exists(folder):
            for root, _, files in os.walk(folder, followlinks=True):
                for file in files:
                    _, file_extension = os.path.splitext(file)
                    if file_extension.lower() in extensions:
                        model_files.append(os.path.join(root, file))

    model_files = sorted(list(set(model_files)))
    return model_files

def gen_sha256(file_path):
    json_file = os.path.splitext(file_path)[0] + '.json'

    if os.path.exists(json_file):
        data = _api.safe_json_load(json_file)
        if data and 'sha256' in data and data['sha256']:
            return data['sha256']

    def read_chunks(file, size=io.DEFAULT_BUFFER_SIZE):
        while True:
            chunk = file.read(size)
            if not chunk:
                break
            yield chunk

    blocksize = 1 << 20
    h = hashlib.sha256()
    length = 0
    with open(os.path.realpath(file_path), 'rb') as f:
        for block in read_chunks(f, size=blocksize):
            length += len(block)
            h.update(block)

    hash_value = h.hexdigest()

    if os.path.exists(json_file):
        data = _api.safe_json_load(json_file)
        if data:
            data['sha256'] = hash_value
        else:
            data = {'sha256': hash_value}
    else:
        data = {'sha256': hash_value}

    _api.safe_json_save(json_file, data)

    return hash_value

def convert_local_images(html):
    soup = BeautifulSoup(html)
    for simg in soup.find_all('img', attrs={'data-sampleimg': 'true'}):
        url = urlparse(simg['src'])
        path = url.path
        if not os.path.exists(path):
            print(f"URL path does not exist: {url.path}")
            # Try the raw url, files can be saved in windows as "C:\..." and
            # that confuses urlparse because people only really test on Linux.
            if os.path.exists(simg['src']):
                path = simg['src']
            else:
                continue
        with open(path, 'rb') as f:
            imgdata = f.read()
        b64img = base64.b64encode(imgdata).decode('utf-8')
        imgtype = Image.open(io.BytesIO(imgdata)).format
        if not imgtype:
            imgtype = 'PNG'
        simg['src'] = f"data:image/{imgtype};base64,{b64img}"
    return str(soup)

def model_from_sent(model_name, content_type):
    modelID_failed = False
    output_html = None
    model_file = None
    use_local_html = getattr(opts, 'use_local_html', False)
    local_path_in_html = getattr(opts, 'local_path_in_html', False)

    model_name = re.sub(r'\.\d{3}$', '', model_name)
    content_type = re.sub(r'\.\d{3}$', '', content_type).lower()
    if 'inversion' in content_type:
        content_type = ['TextualInversion']
    elif 'checkpoint' in content_type:
        content_type = ['Checkpoint']
    elif 'lora' in content_type:
        content_type = ['LORA']
    elif 'detection' in content_type:
        content_type = ['Detection']

    extensions = ['.pt', '.ckpt', '.pth', '.safetensors', '.th', '.zip', '.vae']

    for content_type_item in content_type:
        folder = _api.contenttype_folder(content_type_item)
        for folder_path, _, files in os.walk(folder, followlinks=True):
            for file in files:
                if file.startswith(model_name) and file.endswith(tuple(extensions)):
                    model_file = os.path.join(folder_path, file)

    if not model_file:
        output_html = _api.api_error_msg('path_not_found')
        print(f"Error: Could not find model path for model: '{model_name}'")
        print(f"Content type: '{content_type}'")
        print(f"Main folder path: '{folder}'")
        use_local_html = False

    if use_local_html:
        html_file = os.path.splitext(model_file)[0] + '.html'
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as html:
                output_html = html.read()
                index = output_html.find('</head>')
                if index != -1:
                    output_html = output_html[index + len('</head>'):]
                if local_path_in_html:
                    output_html = convert_local_images(output_html)

    if not output_html:
        api_response = None
        modelID = get_models(model_file, True)
        if not modelID or modelID == 'Model not found':
            output_html = _api.api_error_msg('not_found')
            modelID_failed = True
        if modelID == 'offline':
            output_html = _api.api_error_msg('offline')
            modelID_failed = True
        if not modelID_failed:
            api_response = _api.request_civit_api(f"https://civitai.com/api/v1/models?ids={modelID}&nsfw=true")
        if modelID_failed or api_response in ['timeout', 'error', 'offline']:
            return gr.update(value='<p>ERROR</p>', placeholder=_download.random_number()),  # Preview HTML

        # Get SHA256 hash for the file to find the specific version
        file_sha256 = None
        json_file = os.path.splitext(model_file)[0] + '.json'
        if os.path.exists(json_file):
            data = _api.safe_json_load(json_file)
            file_sha256 = data.get('sha256') if data else None
        # Find the specific model version based on SHA256 or filename
        if file_sha256:
            model_version, item = find_model_version_by_sha256(api_response, file_sha256)
        else:
            model_version, item = find_model_version_by_filename(api_response, model_file)
        if model_version and item:
            # Use the specific model version name for HTML generation
            output_html = _api.update_model_info(None, model_version.get('name'), True, modelID, api_response, True)
        else:
            # Fallback to first version if specific version not found
            model_versions = _api.update_model_versions(modelID, api_response)
            output_html = _api.update_model_info(None, model_versions.get('value'), True, modelID, api_response, True)

    css_path = Path(__file__).resolve().parents[1] / 'style_html.css'
    with open(css_path, 'r', encoding='utf-8') as css_file:
        css = css_file.read()

    style_tag = f'<style>{css}</style>'
    head_section = f'<head>{style_tag}</head>'
    output_html = str(head_section + output_html)

    # debug_print(output_html)
    return gr.update(value=output_html, placeholder=_download.random_number()),  # Preview HTML

def send_to_browser(model_name, content_type, click_first_item):
    modelID_failed = False
    output_html = None
    model_file = None
    number = click_first_item

    model_name = re.sub(r'\.\d{3}$', '', model_name)
    content_type = re.sub(r'\.\d{3}$', '', content_type).lower()
    if 'inversion' in content_type:
        content_type = ['TextualInversion']
    elif 'checkpoint' in content_type:
        content_type = ['Checkpoint']
    elif 'lora' in content_type:
        content_type = ['LORA']
    extensions = ['.pt', '.ckpt', '.pth', '.safetensors', '.th', '.zip', '.vae']

    for content_type_item in content_type:
        folder = _api.contenttype_folder(content_type_item)
        for folder_path, _, files in os.walk(folder, followlinks=True):
            for file in files:
                if file.startswith(model_name) and file.endswith(tuple(extensions)):
                    model_file = os.path.join(folder_path, file)

    if not model_file:
        output_html = _api.api_error_msg('path_not_found')
        print(f"Error: Could not find model path for model: '{model_name}'")
        print(f"Content type: '{content_type}'")
        print(f"Main folder path: '{folder}'")
    if not output_html:
        modelID = get_models(model_file, True)
        if not modelID or modelID == 'Model not found':
            output_html = _api.api_error_msg('not_found')
            modelID_failed = True
        if modelID == 'offline':
            output_html = _api.api_error_msg('offline')
            modelID_failed = True

        if not modelID_failed:
            gl.json_data = _api.request_civit_api(f"https://civitai.com/api/v1/models?ids={modelID}&nsfw=true")
            output_html = _api.model_list_html(gl.json_data)
            number = _download.random_number(click_first_item)

    return (
        gr.update(value=output_html),  # Card HTML
        gr.update(interactive=False),   # Prev Button
        gr.update(interactive=False),   # Next Button
        gr.update(value=1, maximum=1),  # Page Slider
        gr.update(value=number)        # Click first card trigger
    )

def convertCustomFolder(folderValue, basemodel, nsfw, author, modelName, modelId, versionName, versionId):
    replacements = {
        'BASEMODEL': _api.cleaned_name(str(basemodel)),
        'AUTHOR': _api.cleaned_name(str(author)),
        'MODELNAME': _api.cleaned_name(str(modelName)),
        'MODELID': _api.cleaned_name(str(modelId)),
        'VERSIONNAME': _api.cleaned_name(str(versionName)),
        'VERSIONID': _api.cleaned_name(str(versionId))
    }

    if not nsfw:
        segments = folderValue.split(os.sep)
        segments = [seg for seg in segments if "{NSFW}" not in seg]
        folderValue = os.sep.join(segments)
    else:
        replacements['NSFW'] = 'nsfw'

    formatted_value = folderValue.format(**replacements)

    converted_folder = formatted_value.replace('/', os.sep).replace('\\', os.sep)
    converted_folder = os.sep.join(part for part in converted_folder.split(os.sep) if part)

    if not converted_folder.startswith(os.sep):
        converted_folder = os.sep + converted_folder

    return converted_folder

def getSubfolders(model_folder, basemodel=None, nsfw=None, author=None, modelName=None, modelId=None, versionName=None, versionId=None):
    try:
        dot_subfolders = getattr(opts, 'dot_subfolders', True)
        sub_folders = ['None']
        for root, dirs, _ in os.walk(model_folder, followlinks=True):
            if dot_subfolders:
                dirs = [d for d in dirs if not d.startswith('.')]
                dirs = [d for d in dirs if not any(part.startswith('.') for part in os.path.join(root, d).split(os.sep))]
            for d in dirs:
                sub_folder = os.path.relpath(os.path.join(root, d), model_folder)
                if sub_folder:
                    if not sub_folder.startswith(os.sep):
                        sub_folder = os.sep + sub_folder
                    sub_folders.append(sub_folder)

        config_data = _api.safe_json_load(gl.subfolder_json) or {}

        for key, value in config_data.items():
            # Skip timestamp field and non-string values
            if key == 'created_at' or not isinstance(value, str):
                continue

            if basemodel:
                try:
                    converted_value = convertCustomFolder(value, basemodel, nsfw, author, modelName, modelId, versionName, versionId)
                    sub_folders.append(converted_value)
                except Exception as e:
                    print(f"Error: Failed to process custom subfolder: {e}")
            else:
                display_value = value
                if not display_value.startswith(os.sep):
                    display_value = os.sep + display_value
                sub_folders.append(display_value)

        sub_folders.remove('None')
        sub_folders = sorted(sub_folders, key=lambda x: (x.lower(), x))
        sub_folders.insert(0, 'None')

    except Exception as e:
        print(e)
        sub_folders = ['None']

    list = set()
    sub_folders = [x for x in sub_folders if not (x in list or list.add(x))]

    return sub_folders

def updateSubfolder(subfolderInput):
    data = _api.safe_json_load(gl.subfolder_json) or {}
    index, action, value = subfolderInput.split('.', 2)
    index = str(index)

    if action == 'delete':
        data.pop(index, None)
    elif action == 'add':
        data[index] = value

    _api.safe_json_save(gl.subfolder_json, data)

def is_image_url(url):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    parsed = urlparse(url)
    return any(parsed.path.endswith(ext) for ext in image_extensions)

## === ANXETY EDITs ===
def clean_description(desc):
    """This function cleans up HTML descriptions for better readability"""
    try:
        # Flatten to single-line string
        cleaned_lines = [line.strip() for line in desc.splitlines() if line.strip()]
        cleaned_text = ''.join(cleaned_lines)
        cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
        # Begin html processing
        soup = BeautifulSoup(cleaned_text, 'html.parser')
        for a in soup.find_all('a', href=True):
            hyperlink_url = a['href']
            if not is_image_url(hyperlink_url):
                # Add the URL to the text if they are different
                a.replace_with(a.text + (f' ({hyperlink_url})' if a.text != hyperlink_url else ''))
        # Apply markdown-like formatting and newlines for various blocks
        for e in soup.find_all(['br']):
            e.replace_with('\n')
        for e in soup.find_all(['hr']):
            e.replace_with('\n\n')
        for e in soup.find_all(['li']):
            if e.text.strip():
                e.insert_before('- ')
                e.insert_after('\n')
                e.unwrap()
            else:
                e.replace_with('\n')
        for e in soup.find_all(['s']):
            if e.text.strip():
                e.insert_before('~~')
                e.insert_after('~~')
                e.unwrap()
            else:
                e.replace_with('')
        for e in soup.find_all(['p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if e.text.strip():
                e.insert_after('\n\n')
                e.unwrap()
            else:
                e.replace_with('\n\n')
        # Convert back to plaintext
        cleaned_text = soup.get_text()
        # Clean extra characters
        cleaned_text = re.sub(r'~{3,}', '', cleaned_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    except ImportError:
        print('Python module "BeautifulSoup" was not imported correctly, cannot clean description. Please try to restart or install it manually.')
        cleaned_text = desc

    return cleaned_text.strip()

def make_dir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EACCES:
            try:
                os.makedirs(path, mode=0o777)
            except OSError as e2:
                if e2.errno == errno.EACCES:
                    print('Permission denied even with elevated permissions.')
                else:
                    print(f"Error creating directory: {e2}")
        else:
            print(f"Error creating directory: {e}")
    except Exception as e:
        print(f"Error creating directory: {e}")

## === ANXETY EDITs ===
def save_model_info(install_path, file_name, sub_folder, sha256=None, preview_html=None, overwrite_toggle=False, api_response=None):
    save_path, filename = get_save_path_and_name(install_path, file_name, api_response, sub_folder)
    image_path = get_image_path(install_path, api_response, sub_folder)
    json_file = os.path.join(install_path, f'{filename}.json')
    make_dir(install_path)

    save_api_info = getattr(opts, 'save_api_info', False)
    use_local = getattr(opts, 'local_path_in_html', False)
    save_html_on_save = getattr(opts, 'save_html_on_save', False)

    if not api_response:
        api_response = gl.json_data

    # Try to find SHA256 from existing JSON file if not provided
    if not sha256:
        existing_json_file = os.path.splitext(os.path.join(install_path, file_name))[0] + '.json'
        if os.path.exists(existing_json_file):
            data = _api.safe_json_load(existing_json_file)
            sha256 = data.get('sha256') if data else None

    result = find_and_save(api_response, sha256, file_name, json_file, False, overwrite_toggle)
    if result != 'found':
        result = find_and_save(api_response, sha256, file_name, json_file, True, overwrite_toggle)

    if preview_html and save_html_on_save:
        if use_local:
            img_urls = re.findall(r"data-sampleimg='true' src=[\'\"]?([^\'\" >]+)", preview_html)
            for i, img_url in enumerate(img_urls):
                debug_print(img_url)
                img_name = f'{filename}_{i}.png'
                preview_html = preview_html.replace(img_url, f"{os.path.join(image_path, img_name)}")

        match = re.search(r'(\s*)<div class="main-container">', preview_html)
        if match:
            indentation = match.group(1)
        else:
            indentation = ''
        css_link = f'<link rel="stylesheet" type="text/css" href="{css_path}">'
        utf8_meta_tag = f'{indentation}<meta charset="UTF-8">'
        head_section = f'{indentation}<head>{indentation}    {utf8_meta_tag}{indentation}    {css_link}{indentation}</head>'
        HTML = head_section + preview_html
        path_to_new_file = os.path.join(save_path, f'{filename}.html')
        with open(path_to_new_file, 'wb') as f:
            f.write(HTML.encode('utf8'))
        print(f"HTML saved at: {path_to_new_file}")

    if save_api_info:
        path_to_new_file = os.path.join(save_path, f'{filename}.api_info.json')
        if not os.path.exists(path_to_new_file) or overwrite_toggle:
            _api.safe_json_save(path_to_new_file, gl.json_info)

def find_model_version_by_sha256(api_response, sha256):
    """Find the specific model version that matches the given SHA256 hash"""
    for item in api_response.get('items', []):
        for model_version in item.get('modelVersions', []):
            for file in model_version.get('files', []):
                file_sha256 = file.get('hashes', {}).get('SHA256', '')
                if _api.normalize_sha256(file_sha256) == _api.normalize_sha256(sha256):
                    return model_version, item
    return None, None

def find_model_version_by_filename(api_response, file_name):
    """Find the specific model version that matches the given filename"""
    for item in api_response.get('items', []):
        for model_version in item.get('modelVersions', []):
            for file in model_version.get('files', []):
                file_name_api = file.get('name', '')
                if file_name == file_name_api:
                    return model_version, item
    return None, None

## === ANXETY EDITs ===
def find_and_save(api_response, sha256=None, file_name=None, json_file=None, no_hash=None, overwrite_toggle=None):
    save_desc = getattr(opts, 'model_desc_to_json', True)

    # Find the specific model version based on SHA256 or filename
    if no_hash:
        model_version, item = find_model_version_by_filename(api_response, file_name)
    else:
        model_version, item = find_model_version_by_sha256(api_response, sha256)

    if model_version and item:
        gl.json_info = item
        trained_words = model_version.get('trainedWords', [])

        if save_desc:
            description = item.get('description', '')
            if description is not None and description.strip():
                ver_description = model_version.get('description', '')
                # Include "About This Version" if available
                if ver_description is not None and ver_description.strip():
                    description += '\n<p>About this version:</p>\n' + ver_description
                description = clean_description(description)

        base_model = model_version.get('baseModel', '')
        
        # Normalize base model using the same function as organization
        normalized_base_model = normalize_base_model(base_model)
        if normalized_base_model:
            base_model = normalized_base_model
        else:
            # If normalize returns None (leave in root), keep original or set to 'Other'
            base_model = base_model if base_model else 'Other'

        if isinstance(trained_words, list):
            trained_tags = ','.join(trained_words)
            trained_tags = re.sub(r'<[^>]*:[^>]*>', '', trained_tags)
            trained_tags = re.sub(r', ?', ', ', trained_tags)
            trained_tags = trained_tags.strip(', ')
        else:
            trained_tags = trained_words

        content = _api.safe_json_load(json_file) or {}
        changed = False
        if overwrite_toggle == False:
            if 'activation text' not in content:
                content['activation text'] = trained_tags
                changed = True
            if save_desc and ('description' not in content):
                content['description'] = description
                changed = True
            if 'sd version' not in content:
                content['sd version'] = base_model
                changed = True
            # Add new fields for model and version information
            if 'modelId' not in content:
                content['modelId'] = item.get('id')
                changed = True
            if 'modelVersionId' not in content:
                content['modelVersionId'] = model_version.get('id')
                changed = True
            if 'modelPageURL' not in content:
                content['modelPageURL'] = f"https://civitai.com/models/{item.get('id')}?modelVersionId={model_version.get('id')}"
                changed = True
        else:
            content['activation text'] = trained_tags
            if save_desc:
                content['description'] = description
            content['sd version'] = base_model
            # Always update these fields when overwrite is enabled
            content['modelId'] = item.get('id')
            content['modelVersionId'] = model_version.get('id')
            content['modelPageURL'] = f"https://civitai.com/models/{item.get('id')}?modelVersionId={model_version.get('id')}"
            changed = True

        _api.safe_json_save(json_file, content)

        if changed:
            print(f"Model info saved to: {json_file}")
        return 'found'

    return 'not found'

def get_models(file_path, gen_hash=None):
    modelId = None
    modelVersionId = None
    sha256 = None
    json_file = os.path.splitext(file_path)[0] + '.json'
    if os.path.exists(json_file):
        data = _api.safe_json_load(json_file)
        if data:
            modelId = data.get('modelId')
            modelVersionId = data.get('modelVersionId')
            sha256 = data.get('sha256')

    if not modelId or not modelVersionId or not sha256:
        if not sha256 and gen_hash:
            sha256 = gen_sha256(file_path)

        if sha256:
            by_hash = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256}"
        else:
            return modelId if modelId else None

    proxies, ssl = _api.get_proxies()
    try:
        if not modelId or not modelVersionId:
            response = requests.get(by_hash, timeout=(60, 30), proxies=proxies, verify=ssl)
            if response.status_code == 200:
                api_response = response.json()
                if 'error' in api_response:
                    print(f"{file_path}: {api_response['error']}")
                    return None
                else:
                    modelId = api_response.get('modelId', '')
                    modelVersionId = api_response.get('id', '')
            elif response.status_code == 503:
                return 'offline'
            elif response.status_code == 404:
                modelId = 'Model not found'
                modelVersionId = 'Model not found'

            if os.path.exists(json_file):
                data = _api.safe_json_load(json_file)
                if not data:
                    data = {}
            else:
                data = {}

            data.update({
                'modelId': modelId,
                'modelVersionId': modelVersionId,
                'modelPageURL': f"https://civitai.com/models/{modelId}?modelVersionId={modelVersionId}",
                'sha256': sha256.upper()
            })
            _api.safe_json_save(json_file, data)

        return modelId
    except requests.exceptions.Timeout:
        print(f"Request timed out for {file_path}. Skipping...")
        return 'offline'
    except requests.exceptions.ConnectionError:
        print('Failed to connect to the API. The CivitAI servers might be offline.')
        return 'offline'
    except Exception as e:
        print(f"An error occurred for {file_path}: {str(e)}")
        return None

## === ANXETY EDITs ===
def extract_version_from_ver_name(filename):
    """
    Extracts the model family name and version from the model name string.
    Returns: (family_name or None, version_parts: list[int])
    """
    version_patterns = [
        r'[_\-]?v(\d+\.\d+)$',  # 1.0, _v2.1, -v3.2
        r'[_\-]?v(\d+)$',       # v1, _v2, -v3
        # r'[_\-]?(\d+\.\d+)$',   # 1.0, _2.1, -3.2
        # r'[_\-]?(\d+)$',        # 1, _2, -3
    ]
    for pattern in version_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            version_str = match.group(1)
            parts = [int(p) for p in version_str.split('.') if p.isdigit()]
            # Remove the matched part from the end of the string to get the family name
            family = filename[:match.start()].strip("_- .")
            # If family looks like a pure version (for example, 'v3'), treat it as None
            if not family or re.fullmatch(r'v?\d+(\.\d+)?', family, re.IGNORECASE):
                family = None

            return family, parts
    return None, []

def compare_version_parts(a_parts, b_parts):
    """
    Compare two version parts lists.
    Returns:
      -1 if a < b,
      0 if a == b,
      1 if a > b
    """
    max_len = max(len(a_parts), len(b_parts))
    a = a_parts + [0] * (max_len - len(a_parts))
    b = b_parts + [0] * (max_len - len(b_parts))
    return (a > b) - (a < b)

def version_match(file_paths, api_response, log=False):
    """
    Checking model updates by version.
    - If opts.precise_version_check = False:
        Compares only versions (without families).
    - If True:
        Compares versions by family, if family exists.
        If family=None — switches to comparison without family.
    """
    precise_check = getattr(opts, 'precise_version_check', True)
    updated_models = []
    outdated_models = []

    # === 1. Collecting installed SHA256 ===
    installed_hashes = set()
    for path in file_paths:
        json_path = f"{os.path.splitext(path)[0]}.json"
        data = _api.safe_json_load(json_path)
        if data:
            sha = data.get('sha256', '')
            if sha:
                installed_hashes.add(sha.upper())

    if log:
        print(f"[LOG] {len(installed_hashes)} installed model hashes found")

    # === 2. Determine installed versions and families ===
    installed_map = {}  # family -> list of versions
    installed_all = []  # all versions regardless of family

    for model in api_response.get('items', []):
        for ver in model.get('modelVersions', []):
            ver_name = ver.get('name', '')
            family, ver_parts = extract_version_from_ver_name(ver_name)

            for file_entry in ver.get('files', []):
                sha = file_entry.get('hashes', {}).get('SHA256', '').upper()
                if sha in installed_hashes:
                    if precise_check and family:
                        installed_map.setdefault(family, []).append(ver_parts)
                        if log:
                            print(f"[LOG] Family '{family}' version {ver_parts} is installed")
                    else:
                        installed_all.append(ver_parts)
                        if log:
                            print(f"[LOG] Version {ver_parts} is installed (without family)")
                    break

    # === 3. Compare with available versions ===
    for model in api_response.get('items', []):
        model_id = model.get('id')
        model_name = model.get('name')
        model_versions = model.get('modelVersions', [])

        if not model_versions:
            continue

        available_map = {}  # dictionary: { family_name: [list of versions] } — all versions grouped by family
        available_all = []  # list of all versions without grouping by family (used if precise_check=False)

        for ver in model_versions:
            ver_name = ver.get('name', '')
            family, ver_parts = extract_version_from_ver_name(ver_name)

            if precise_check and family:
                available_map.setdefault(family, []).append(ver_parts)
            else:
                available_all.append(ver_parts)

        has_outdated = False

        if precise_check and available_map:
            # Сomparison by families
            for fam_key, avail_versions in available_map.items():
                installed_versions = installed_map.get(fam_key, [])
                if not installed_versions:
                    continue

                max_inst = max(installed_versions, key=lambda x: x or [0])
                max_avail = max(avail_versions, key=lambda x: x or [0])
                cmp = compare_version_parts(max_inst, max_avail)

                if cmp < 0:
                    has_outdated = True
                    if log:
                        print(f"[LOG] '{model_name}' family '{fam_key}': outdated ({max_inst} < {max_avail})")
                elif log:
                    print(f"[LOG] '{model_name}' family '{fam_key}': up-to-date ({max_inst} >= {max_avail})")

        else:
            # Сomparison without families
            if not installed_all:
                continue
            max_inst = max(installed_all, key=lambda x: x or [0])
            max_avail = max(available_all, key=lambda x: x or [0])
            cmp = compare_version_parts(max_inst, max_avail)

            if cmp < 0:
                has_outdated = True
                if log:
                    print(f"[LOG] '{model_name}': outdated ({max_inst} < {max_avail})")
            elif log:
                print(f"[LOG] '{model_name}': up-to-date ({max_inst} >= {max_avail})")

        if has_outdated:
            outdated_models.append((f"&ids={model_id}", model_name))
        else:
            updated_models.append((f"&ids={model_id}", model_name))

    return updated_models, outdated_models

def get_content_choices(scan_choices=False):
    content_list = [
        'Checkpoint', 'TextualInversion', 'LORA', 'Poses', 'Controlnet', 'Detection',
        'VAE', 'Upscaler', 'Wildcards', 'AestheticGradient', 'MotionModule', 'Workflows', 'Other'
    ]
    if scan_choices:
        content_list.insert(0, 'All')
        return content_list
    return content_list

def get_save_path_and_name(install_path, file_name, api_response, sub_folder=None):
    save_to_custom = getattr(opts, 'save_to_custom', False)

    name = os.path.splitext(file_name)[0]
    if not sub_folder:
        sub_folder = os.path.normpath(os.path.relpath(install_path, gl.main_folder))
    image_path = _file.get_image_path(install_path, api_response, sub_folder)

    if save_to_custom:
        save_path = image_path
    else:
        save_path = install_path

    return save_path, name

## === ANXETY EDITs ===
def file_scan(folders, tag_finish, ver_finish, installed_finish, preview_finish, organize_finish, overwrite_toggle, tile_count, gen_hash, create_html, progress=gr.Progress() if queue else None):
    global no_update
    proxies, ssl = _api.get_proxies()
    gl.scan_files = True
    no_update = False

    if from_tag:
        number = _download.random_number(tag_finish)
    elif from_ver:
        number = _download.random_number(ver_finish)
    elif from_installed:
        number = _download.random_number(installed_finish)
    elif from_preview:
        number = _download.random_number(preview_finish)
    elif from_organize:
        number = _download.random_number(organize_finish)

    if not folders:
        if progress != None:
            progress(0, desc='No model type selected.')
        no_update = True
        gl.scan_files = False
        time.sleep(2)
        return (
            gr.update(value='<div style="min-height: 0px;"></div>'),
            gr.update(value=number)
        )

    folders_to_check = []
    if 'All' in folders:
        folders = _file.get_content_choices()

    for item in folders:
        if item == 'LORA':
            folder = _api.contenttype_folder('LORA')
            if folder:
                folders_to_check.append(folder)
        elif item == 'Upscaler':
            folder = _api.contenttype_folder(item, 'SwinIR')
            if folder:
                folders_to_check.append(folder)
            folder = _api.contenttype_folder(item, 'RealESRGAN')
            if folder:
                folders_to_check.append(folder)
            folder = _api.contenttype_folder(item, 'GFPGAN')
            if folder:
                folders_to_check.append(folder)
            folder = _api.contenttype_folder(item, 'BSRGAN')
            if folder:
                folders_to_check.append(folder)
            folder = _api.contenttype_folder(item, 'ESRGAN')
            if folder:
                folders_to_check.append(folder)
        else:
            folder = _api.contenttype_folder(item)
            if folder:
                folders_to_check.append(folder)

    total_files = 0
    files_done = 0

    files = list_files(folders_to_check)
    total_files += len(files)

    if total_files == 0:
        if progress != None:
            progress(1, desc='No files in selected folder.')
        no_update = True
        gl.scan_files = False
        time.sleep(2)
        return (
            gr.update(value='<div style="min-height: 0px;"></div>'),
            gr.update(value=number)
        )

    all_model_ids = []
    file_paths = []
    all_ids = []

    for file_path in files:
        if gl.cancel_status:
            if progress != None:
                progress(files_done / total_files, desc='Processing files cancelled.')
            no_update = True
            gl.scan_files = False
            time.sleep(2)
            return (
                gr.update(value='<div style="min-height: 0px;"></div>'),
                gr.update(value=number)
            )
        file_name = os.path.basename(file_path)
        if progress != None:
            progress(files_done / total_files, desc=f"Processing file: {file_name}")

        model_id = get_models(file_path, gen_hash)
        if model_id == 'offline':
            print('The CivitAI servers did not respond, unable to retrieve Model ID')
        elif model_id == 'Model not found':
            debug_print(f"model: '{file_name}' not found on CivitAI servers.")
        elif model_id != None:
            all_model_ids.append(f"&ids={model_id}")
            all_ids.append(model_id)
            file_paths.append(file_path)
        elif not model_id:
            print(f"model ID not found for: '{file_name}'")
        files_done += 1

    all_items = []

    all_model_ids = list(set(all_model_ids))

    if not all_model_ids:
        progress(1, desc='No model IDs could be retrieved.')
        print("Could not retrieve any Model IDs, please make sure to turn on the 'One-Time Hash Generation for externally downloaded models.' option if you haven't already.")
        no_update = True
        gl.scan_files = False
        time.sleep(2)
        return (
            gr.update(value='<div style="min-height: 0px;"></div>'),
            gr.update(value=number)
        )

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    if not from_installed:
        model_chunks = list(chunks(all_model_ids, 500))

        base_url = "https://civitai.com/api/v1/models?limit=100&nsfw=true"
        url_list = [f"{base_url}{''.join(chunk)}" for chunk in model_chunks]

        url_count = len(all_model_ids) // 100
        if len(all_model_ids) % 100 != 0:
            url_count += 1
        url_done = 0
        api_response = {}
        for url in url_list:
            while url:
                try:
                    if progress != None:
                        progress(url_done / url_count, desc=f"Sending API request... {url_done}/{url_count}")
                    response = requests.get(url, timeout=(60, 30), proxies=proxies, verify=ssl)
                    if response.status_code == 200:
                        api_response_json = response.json()
                        all_items.extend(api_response_json['items'])
                        metadata = api_response_json.get('metadata', {})
                        url = metadata.get('nextPage', None)
                    elif response.status_code == 503:
                        print(f"Error: Received status code: {response.status_code} with URL: {url}")
                        print(response.text)
                        return (
                            gr.update(value=_api.api_error_msg('error')),
                            gr.update(value=number)
                        )
                    else:
                        print(f"Error: Received status code {response.status_code} with URL: {url}")
                        url = None
                    url_done += 1
                except requests.exceptions.Timeout:
                    print(f"Request timed out for {url}. Skipping...")
                    url = None
                except requests.exceptions.ConnectionError:
                    print('Failed to connect to the API. The servers might be offline.')
                    url = None
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                    url = None

        api_response['items'] = all_items
        if api_response['items'] == []:
            return (
                gr.update(value=_api.api_error_msg('no_items')),
                gr.update(value=number)
            )

    if progress != None:
        progress(1, desc='Processing final results...')

    if from_ver:
        updated_models, outdated_models = version_match(file_paths, api_response)

        updated_set = set(updated_models)
        outdated_set = set(outdated_models)
        outdated_set = {model for model in outdated_set if model[0] not in {updated_model[0] for updated_model in updated_set}}

        all_model_ids = [model[0] for model in outdated_set]
        all_model_names = [model[1] for model in outdated_set]

        for model_name in all_model_names:
            print(f'"{model_name}" is currently outdated.')

        if len(all_model_ids) == 0:
            no_update = True
            gl.scan_files = False
            return (
                gr.update(value='<div style="font-size: 24px; text-align: center; margin: 50px !important;">No updates found for selected models.</div>'),
                gr.update(value=number)
            )

    model_chunks = list(chunks(all_model_ids, tile_count))

    base_url = "https://civitai.com/api/v1/models?limit=100&nsfw=true"
    gl.url_list = {i + 1: f"{base_url}{''.join(chunk)}" for i, chunk in enumerate(model_chunks)}

    ## === ANXETY EDITs ===
    if from_ver:
        gl.scan_files = False
        return (
            gr.update(value='<div style="font-size: 24px; text-align: center; margin: 50px !important;">Outdated models have been found.<br>Please press the button above to load the models into the browser tab</div>'),
            gr.update(value=number)
        )

    elif from_installed:
        gl.scan_files = False
        return (
            gr.update(value='<div style="font-size: 24px; text-align: center; margin: 50px !important;">Installed models have been loaded.<br>Please press the button above to load the models into the browser tab</div>'),
            gr.update(value=number)
        )

    elif from_tag:
        completed_tags = 0
        tag_count = len(file_paths)

        for file_path, id_value in zip(file_paths, all_ids):
            install_path, file_name = os.path.split(file_path)

            try:
                save_path, name = get_save_path_and_name(install_path, file_name, api_response)

                # Get SHA256 hash for the file to find the specific version
                file_sha256 = None
                json_file = os.path.splitext(file_path)[0] + '.json'
                if os.path.exists(json_file):
                    data = _api.safe_json_load(json_file)
                    file_sha256 = data.get('sha256') if data else None

                # Find the specific model version based on SHA256 or filename
                if file_sha256:
                    model_version, item = find_model_version_by_sha256(api_response, file_sha256)
                else:
                    model_version, item = find_model_version_by_filename(api_response, file_name)

                html_path = os.path.join(save_path, f'{name}.html')

                if create_html and not os.path.exists(html_path) or create_html and overwrite_toggle:
                    if model_version and item:
                        # Use the specific model version name for HTML generation
                        preview_html = _api.update_model_info(None, model_version.get('name'), True, id_value, api_response, True)
                    else:
                        # Fallback to first version if specific version not found
                        model_versions = _api.update_model_versions(id_value, api_response)
                        preview_html = _api.update_model_info(None, model_versions.get('value'), True, id_value, api_response, True)
                else:
                    preview_html = None

                completed_tags += 1
                if progress != None:
                    progress(
                        completed_tags / tag_count,
                        desc=f"Saving tags{' & HTML' if preview_html else ''}... {completed_tags}/{tag_count} | {name}"
                    )
                sub_folder = os.path.normpath(os.path.relpath(install_path, gl.main_folder))
                save_model_info(install_path, file_name, sub_folder, sha256=file_sha256, preview_html=preview_html, api_response=api_response, overwrite_toggle=overwrite_toggle)

            except Exception as e:
                print(f"Error processing model {file_name}: {e}")
                completed_tags += 1
                if progress != None:
                    progress(
                        completed_tags / tag_count,
                        desc=f"Skipped {name} due to error... {completed_tags}/{tag_count}"
                    )
                continue  # Skip this model and continue with the next

        if progress != None:
            progress(1, desc='All tags succesfully saved!')
        gl.scan_files = False
        time.sleep(2)
        return (
            gr.update(value='<div style="min-height: 0px;"></div>'),
            gr.update(value=number)
        )

    elif from_preview:
        completed_preview = 0
        preview_count = len(file_paths)
        for file in file_paths:
            _, file_name = os.path.split(file)
            name = os.path.splitext(file_name)[0]
            completed_preview += 1
            if progress != None:
                progress(
                    completed_preview / preview_count,
                    desc=f"Saving preview images... {completed_preview}/{preview_count} | {name}"
                )
            save_preview(file, api_response, overwrite_toggle)
        gl.scan_files = False
        return (
            gr.update(value='<div style="min-height: 0px;"></div>'),
            gr.update(value=number)
        )
    
    elif from_organize:
        # Step 1: Analyze organization needs
        if progress != None:
            progress(0, desc='Analyzing models for organization...')
        
        organization_plan = analyze_organization_plan(folders, progress)
        
        # Always show preview first with statistics
        preview_html = generate_organization_preview_html(organization_plan)
        
        if not organization_plan['moves']:
            # No files need organization
            gl.scan_files = False
            return (
                gr.update(value=preview_html),
                gr.update(value=number)
            )
        
        # Files need organization - show preview with detailed stats
        _debug_log(f"Organization plan created: {len(organization_plan['moves'])} files to move")
        for category, info in organization_plan['summary'].items():
            _debug_log(f"  {category}: {info['count']} files ({format_size(info['size'])})")
        
        # Step 2: Save backup before making changes
        if progress != None:
            progress(0.9, desc='Creating backup...')
        
        backup_id = save_organization_backup(organization_plan)
        if not backup_id:
            gl.scan_files = False
            error_html = '''
            <div style="padding: 20px; border: 1px solid var(--error-border-color); border-radius: 8px;">
                <h3 style="color: var(--error-text-color);">⚠️ Backup Failed</h3>
                <p>Unable to create backup. Organization cancelled for safety.</p>
                <p>Please check file permissions and try again.</p>
            </div>
            '''
            return (
                gr.update(value=error_html),
                gr.update(value=number)
            )
        
        # Step 3: Execute organization
        total_moves = len(organization_plan['moves'])
        print(f"[CivitAI Browser Neo] Starting organization of {total_moves} files...")
        print(f"[CivitAI Browser Neo] 💾 Backup ID: {backup_id}")
        
        result = execute_organization(organization_plan, progress)
        
        # Step 4: Generate result message with detailed statistics
        if result['success']:
            # Calculate total size moved
            total_size = sum(info['size'] for info in organization_plan['summary'].values())
            folder_list = ', '.join(sorted(organization_plan['summary'].keys()))
            
            result_html = f'''
            <div style="padding: 20px; text-align: center; color: var(--color-accent);">
                <h2 style="margin: 0 0 15px 0;">✅ Organization Complete!</h2>
                <div style="font-size: 18px; margin-bottom: 20px;">
                    <strong>{result['completed']} files</strong> ({format_size(total_size)}) organized into <strong>{len(organization_plan['summary'])} folders</strong>
                </div>
                <div style="background: var(--background-fill-secondary); padding: 10px; border-radius: 5px; font-size: 14px;">
                    📂 {folder_list}
                </div>
                <div style="margin-top: 15px; padding: 10px; background: var(--color-accent-soft); border-radius: 5px; font-size: 13px;">
                    💾 Backup: {backup_id} | Use "↶ Undo" button to rollback
                </div>
            </div>
            '''
        else:
            error_list = '<br>'.join(result['errors'][:10])
            if len(result['errors']) > 10:
                error_list += f'<br><em>... and {len(result["errors"]) - 10} more errors</em>'
            
            result_html = f'''
            <div style="padding: 20px; border: 1px solid var(--error-border-color); border-radius: 8px;">
                <h3 style="color: var(--error-text-color);">⚠️ Organization Completed with Errors</h3>
                <p>Completed: {result['completed']}/{result['total']} files</p>
                <p>💾 Backup saved: {backup_id}</p>
                <details>
                    <summary style="cursor: pointer;">View errors</summary>
                    <div style="margin-top: 10px; padding: 10px; background: var(--block-background-fill); border-radius: 5px;">
                        {error_list}
                    </div>
                </details>
                <div style="margin-top: 10px;">
                    Use the "Undo Organization" button to rollback changes.
                </div>
            </div>
            '''
        
        print(f"[CivitAI Browser Neo] {result['message']}")
        gl.scan_files = False
        return (
            gr.update(value=result_html),
            gr.update(value=number)
        )

def finish_returns():
    return (
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),  # Organize models button
        gr.update(interactive=False, visible=False)
    )

def start_returns(number):
    return (
        gr.update(value=number),
        gr.update(interactive=False, visible=False),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=False, visible=True),
        gr.update(interactive=False, visible=True),
        gr.update(interactive=False, visible=True),
        gr.update(interactive=False, visible=True),  # Organize models button (keep visible but disabled during scan)
        gr.update(value='<div style="min-height: 100px;"></div>')
    )

## === ANXETY EDITs ===
def set_globals(input_global=None):
    global from_tag, from_ver, from_installed, from_preview, from_organize
    from_tag = from_ver = from_installed = from_preview = from_organize = False
    if input_global == 'reset':
        return
    elif input_global == 'from_tag':
        from_tag = True
    elif input_global == 'from_ver':
        from_ver = True
    elif input_global == 'from_installed':
        from_installed = True
    elif input_global == 'from_preview':
        from_preview = True
    elif input_global == 'from_organize':
        from_organize = True

def save_tag_start(tag_start):
    set_globals('from_tag')
    number = _download.random_number(tag_start)
    return start_returns(number)

def save_preview_start(preview_start):
    set_globals('from_preview')
    number = _download.random_number(preview_start)
    return start_returns(number)

def ver_search_start(ver_start):
    set_globals('from_ver')
    number = _download.random_number(ver_start)
    return start_returns(number)

def installed_models_start(installed_start):
    set_globals('from_installed')
    number = _download.random_number(installed_start)
    return start_returns(number)

def get_model_categories():
    """
    Get model organization categories from settings or default
    Returns dict mapping folder names to detection patterns
    """
    # Default categories based on Forge Neo supported models
    default_categories = {
        'SD': ['SD 1', 'SD1', 'SD 2', 'SD2'],
        'SDXL': ['SDXL'],
        'Pony': ['PONY', 'PONYXL', 'PONY XL', 'PONY V6', 'PONYV6'],
        'Illustrious': ['ILLUSTRIOUS'],
        'FLUX': ['FLUX'],
        'Wan': ['WAN'],
        'Qwen': ['QWEN'],
        'Z-Image': ['Z-IMAGE', 'ZIMAGE', 'Z IMAGE'],
        'Lumina': ['LUMINA'],
        'Anima': ['ANIMA'],
        'Cascade': ['CASCADE'],
        'PixArt': ['PIXART', 'PIX ART'],
        'Playground': ['PLAYGROUND'],
        'SVD': ['SVD', 'STABLE VIDEO'],
        'Hunyuan': ['HUNYUAN'],
        'Kolors': ['KOLORS'],
        'AuraFlow': ['AURAFLOW', 'AURA FLOW'],
        'Chroma': ['CHROMA'],
    }
    
    # Try to load custom categories from settings
    try:
        custom_categories = getattr(opts, 'civitai_neo_model_categories', None)
        if custom_categories:
            # Parse JSON if stored as string
            if isinstance(custom_categories, str):
                import json
                custom_categories = json.loads(custom_categories)
            return custom_categories
    except:
        pass
    
    return default_categories

def _debug_log(message):
    """
    Print debug messages for organization system if enabled in settings
    Enable in Settings > CivitAI Browser Neo > Debug Organization Logs
    """
    if getattr(opts, 'civitai_neo_debug_organize', False):
        print(f"[DEBUG] {message}")

def normalize_base_model(base_model):
    """
    Normalize baseModel from CivitAI to folder-friendly name
    Supports all Forge Neo model types with customizable categories
    """
    _debug_log(f"normalize_base_model() received: '{base_model}'")
    
    if not base_model or base_model == 'Not Found':
        # Check if user wants to create "Other" folder
        if not getattr(opts, 'civitai_neo_create_other_folder', True):
            _debug_log("No baseModel, returning None (no 'Other' folder)")
            return None  # Leave in root
        _debug_log("No baseModel, returning 'Other'")
        return 'Other'
    
    base_model_upper = base_model.upper()
    categories = get_model_categories()
    
    _debug_log(f"Checking '{base_model_upper}' against categories...")
    
    # Check each category's patterns
    for folder_name, patterns in categories.items():
        for pattern in patterns:
            if pattern.upper() in base_model_upper:
                _debug_log(f"MATCH! '{pattern}' found in '{base_model_upper}' → Folder: '{folder_name}'")
                return folder_name
    
    # No match found
    _debug_log(f"No match found for '{base_model_upper}'")
    if not getattr(opts, 'civitai_neo_create_other_folder', True):
        _debug_log("Returning None (no 'Other' folder)")
        return None  # Leave in root
    _debug_log("Returning 'Other'")
    return 'Other'

def get_model_info_for_organization(file_path):
    """
    Get model info from associated JSON file for organization purposes
    Only uses JSON metadata - does NOT auto-detect to avoid incorrect moves
    
    Returns tuple: (base_model_type, model_name)
    If no JSON found or no baseModel in JSON, returns (None, model_name)
    User must decide whether to fetch metadata via API or organize manually
    """
    model_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_path)[0]
    
    _debug_log(f"Checking metadata for: {model_name}")
    
    # Try .api_info.json FIRST (official API data), then .json (local data)
    json_files = [
        base_name + '.api_info.json',
        base_name + '.json'
    ]
    
    for json_file in json_files:
        _debug_log(f"Trying: {os.path.basename(json_file)}")
        if os.path.exists(json_file):
            _debug_log(f"File exists: {os.path.basename(json_file)}")
            try:
                data = _api.safe_json_load(json_file)
                if data:
                    # Try multiple sources for base model (in priority order)
                    base_model = None
                    
                    # 1. Check raw 'baseModel' from API (most reliable)
                    if 'baseModel' in data:
                        base_model = data.get('baseModel', '')
                        if base_model:  # Only print if non-empty
                            _debug_log(f"Found from data['baseModel']: '{base_model}'")
                    
                    # 2. Check 'sd version' (legacy storage)
                    if not base_model:
                        base_model = data.get('sd version', '')
                        if base_model:
                            _debug_log(f"Found from data['sd version']: '{base_model}'")
                    
                    # 3. Check nested in model data
                    if not base_model and 'model' in data:
                        base_model = data.get('model', {}).get('baseModel', '')
                        if base_model:
                            _debug_log(f"Found from data['model']['baseModel']: '{base_model}'")
                    
                    # 4. Check in modelVersions array (CivitAI API format)
                    if not base_model and 'modelVersions' in data:
                        versions = data.get('modelVersions', [])
                        _debug_log(f"Found modelVersions array with {len(versions)} versions")
                        if versions and len(versions) > 0:
                            # Try to find the correct version by SHA256 hash
                            file_hash = _file.get_model_hash(file_path, hash_type='SHA256')
                            matched_version = None
                            
                            if file_hash:
                                _debug_log(f"Model SHA256: {file_hash}")
                                # Search for matching version by hash
                                for version in versions:
                                    version_files = version.get('files', [])
                                    for vfile in version_files:
                                        hashes = vfile.get('hashes', {})
                                        if hashes.get('SHA256', '').upper() == file_hash.upper():
                                            matched_version = version
                                            _debug_log(f"Found matching version by SHA256: {version.get('name')} (id: {version.get('id')})")
                                            break
                                    if matched_version:
                                        break
                            
                            # Use matched version if found, otherwise use first version
                            target_version = matched_version if matched_version else versions[0]
                            base_model = target_version.get('baseModel', '')
                            
                            if base_model:
                                if matched_version:
                                    _debug_log(f"Found from MATCHED modelVersion['{target_version.get('name')}']: '{base_model}'")
                                else:
                                    _debug_log(f"Found from modelVersions[0]['baseModel']: '{base_model}' (no hash match, using first)")
                    
                    # 5. Check in version data
                    if not base_model and 'version' in data:
                        base_model = data.get('version', {}).get('baseModel', '')
                        if base_model:
                            _debug_log(f"Found from data['version']['baseModel']: '{base_model}'")
                    
                    if base_model:
                        _debug_log(f"SUCCESS! Final baseModel: '{base_model}' from {os.path.basename(json_file)}")
                        return base_model, model_name
                    else:
                        # JSON exists but no baseModel found - try next JSON file
                        _debug_log(f"No baseModel found in {os.path.basename(json_file)}, trying next file...")
                        continue  # ← FIX: Continue to next file instead of returning
            except Exception as e:
                _debug_log(f"Error reading JSON {json_file}: {e}")
                continue
    
    # No JSON file found OR no baseModel in any JSON - cannot determine base model
    _debug_log(f"⚠️ No baseModel found in any JSON file for: {model_name}")
    print(f"[CivitAI Browser Neo] ⚠️ No metadata with baseModel for: {model_name} - Use API search to fetch metadata")
    return None, model_name

def analyze_organization_plan(folders, progress=None):
    """
    Analyze current model files and create an organization plan
    Returns organization plan with moves grouped by base model
    """
    folders_to_check = []
    
    if 'All' in folders:
        folders = _file.get_content_choices()
    
    for item in folders:
        if item == 'LORA':
            folder = _api.contenttype_folder('LORA')
            if folder:
                folders_to_check.append(folder)
        else:
            folder = _api.contenttype_folder(item)
            if folder:
                folders_to_check.append(folder)
    
    files = list_files(folders_to_check)
    
    organization_plan = {
        'moves': [],
        'summary': {},
        'total_files': 0,
        'files_with_info': 0,
        'files_without_info': 0
    }
    
    files_processed = 0
    total_files = len(files)
    
    for file_path in files:
        files_processed += 1
        if progress is not None:
            file_name = os.path.basename(file_path)
            progress(files_processed / total_files, desc=f"Analyzing: {file_name}")
        
        base_model_raw, model_name = get_model_info_for_organization(file_path)
        
        if not base_model_raw:
            organization_plan['files_without_info'] += 1
            continue
        
        organization_plan['files_with_info'] += 1
        
        # Normalize base model to folder name
        base_model_folder = normalize_base_model(base_model_raw)
        
        # If normalize returns None, skip this file (leave in root)
        if not base_model_folder:
            continue
        
        # Get current directory
        current_dir = os.path.dirname(file_path)
        
        # Check if already in correct subfolder
        current_parent = os.path.basename(current_dir)
        if current_parent == base_model_folder:
            # Already organized
            continue
        
        # Create target path
        # Determine root folder from current file location
        # Go up levels until we find a models folder or we're at root model type folder
        root_folder = current_dir
        while os.path.basename(root_folder) not in ['Lora', 'Stable-diffusion', 'embeddings', 'VAE', 'ControlNet']:
            parent = os.path.dirname(root_folder)
            if parent == root_folder:  # We've reached filesystem root
                root_folder = current_dir
                break
            root_folder = parent
        
        target_folder = os.path.join(root_folder, base_model_folder)
        target_path = os.path.join(target_folder, os.path.basename(file_path))
        
        # Add to plan
        organization_plan['moves'].append({
            'from': file_path,
            'to': target_path,
            'base_model': base_model_folder,
            'model_name': model_name,
            'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        })
        
        # Update summary
        if base_model_folder not in organization_plan['summary']:
            organization_plan['summary'][base_model_folder] = {
                'count': 0,
                'size': 0
            }
        
        organization_plan['summary'][base_model_folder]['count'] += 1
        organization_plan['summary'][base_model_folder]['size'] += organization_plan['moves'][-1]['size']
    
    organization_plan['total_files'] = total_files
    
    return organization_plan

def format_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def generate_organization_preview_html(organization_plan):
    """Generate HTML preview of organization plan"""
    
    if not organization_plan['moves']:
        return '''
        <div style="padding: 20px; text-align: center;">
            <h3>✅ All models are already organized!</h3>
            <p>No files need to be moved.</p>
        </div>
        '''
    
    # Build compact summary table
    summary_rows = ''
    for base_model in sorted(organization_plan['summary'].keys()):
        info = organization_plan['summary'][base_model]
        summary_rows += f'''
        <tr>
            <td style="padding: 5px;">📂 {base_model}</td>
            <td style="text-align: center; padding: 5px;">{info['count']}</td>
            <td style="text-align: right; padding: 5px;">{format_size(info['size'])}</td>
        </tr>
        '''
    
    total_size = sum(info['size'] for info in organization_plan['summary'].values())
    total_moves = len(organization_plan['moves'])
    total_folders = len(organization_plan['summary'])
    files_without_info = organization_plan['files_without_info']
    
    html = f'''
    <div style="padding: 15px; border: 1px solid var(--border-color-primary); border-radius: 8px; margin: 10px 0;">
        <h3 style="margin: 0 0 15px 0;">📁 Organization Plan</h3>
        
        <div style="background: var(--background-fill-secondary); padding: 12px; border-radius: 5px; margin-bottom: 15px; font-size: 15px;">
            <strong>{total_moves} files</strong> ({format_size(total_size)}) → <strong>{total_folders} folders</strong>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background: var(--background-fill-secondary);">
                    <th style="padding: 8px; text-align: left;">Folder</th>
                    <th style="padding: 8px; text-align: center;">Files</th>
                    <th style="padding: 8px; text-align: right;">Size</th>
                </tr>
            </thead>
            <tbody>
                {summary_rows}
            </tbody>
        </table>
        
        {f'<div style="margin-top: 12px; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 13px;">⚠️ {files_without_info} of {organization_plan["total_files"]} files without metadata (will be skipped)</div>' if files_without_info > 0 else ''}
        
        <details style="margin-top: 12px;">
            <summary style="cursor: pointer; padding: 8px; background: var(--block-background-fill); border-radius: 5px; font-size: 13px;">
                📋 Show file list ({total_moves} files)
            </summary>
            <div style="max-height: 200px; overflow-y: auto; margin-top: 8px; padding: 8px; background: var(--block-background-fill); border-radius: 5px; font-size: 12px; font-family: monospace;">
                {'<br>'.join([f"• {os.path.basename(m['from'])} → {m['base_model']}/" for m in organization_plan['moves'][:50]])}
                {f'<br><em>... and {total_moves - 50} more</em>' if total_moves > 50 else ''}
            </div>
        </details>
    </div>
    '''
    
    return html

def save_organization_backup(organization_plan):
    """
    Save organization plan as backup before executing
    Returns backup ID (timestamp)
    """
    from datetime import datetime
    
    # Calculate statistics
    total_files = len(organization_plan['moves'])
    total_size = sum(info['size'] for info in organization_plan['summary'].values())
    
    backup_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        'date_readable': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'moves': organization_plan['moves'],
        'summary': organization_plan['summary'],
        'stats': {
            'total_files': total_files,
            'total_size': total_size,
            'total_folders': len(organization_plan['summary']),
            'folders': list(organization_plan['summary'].keys())
        }
    }
    
    # Load existing backup file
    backup_file_data = {'created_at': datetime.now().timestamp(), 'backups': []}
    if os.path.exists(gl.organization_backup_file):
        try:
            with open(gl.organization_backup_file, 'r', encoding='utf-8') as f:
                backup_file_data = json.load(f)
                # Handle old format (plain list) - migrate to new format
                if isinstance(backup_file_data, list):
                    backup_file_data = {'created_at': datetime.now().timestamp(), 'backups': backup_file_data}
                elif 'backups' not in backup_file_data:
                    backup_file_data['backups'] = []
        except:
            backup_file_data = {'created_at': datetime.now().timestamp(), 'backups': []}
    
    # Add new backup
    backup_file_data['backups'].append(backup_data)
    
    # Keep only last 5 backups
    if len(backup_file_data['backups']) > 5:
        backup_file_data['backups'] = backup_file_data['backups'][-5:]
    
    # Save backups
    try:
        with open(gl.organization_backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_file_data, f, indent=2, ensure_ascii=False)
        
        gl.last_organization_backup = backup_data['timestamp']
        print(f"[CivitAI Browser Neo] Backup saved: {backup_data['timestamp']}")
        return backup_data['timestamp']
    except Exception as e:
        print(f"[CivitAI Browser Neo] Failed to save backup: {e}")
        return None

def get_last_organization_backup():
    """
    Get the most recent organization backup
    Returns backup data or None
    """
    if not os.path.exists(gl.organization_backup_file):
        return None
    
    try:
        with open(gl.organization_backup_file, 'r', encoding='utf-8') as f:
            backup_file_data = json.load(f)
        
        # Handle old format (plain list)
        if isinstance(backup_file_data, list):
            backups = backup_file_data
        else:
            backups = backup_file_data.get('backups', [])
        
        if backups:
            return backups[-1]
    except Exception as e:
        debug_print(f"Error loading backup: {e}")
    
    return None

def execute_rollback(progress=None):
    """
    Rollback the last organization operation
    Moves files back to their original locations
    """
    backup = get_last_organization_backup()
    
    if not backup:
        return {
            'success': False,
            'message': 'No backup found to rollback',
            'completed': 0,
            'total': 0,
            'errors': []
        }
    
    moves = backup.get('moves', [])
    total_moves = len(moves)
    moves_completed = 0
    errors = []
    
    print(f"[CivitAI Browser Neo] Starting rollback of {total_moves} files...")
    
    for move_info in moves:
        if gl.cancel_status:
            return {
                'success': False,
                'completed': moves_completed,
                'total': total_moves,
                'errors': errors,
                'message': 'Rollback cancelled by user'
            }
        
        # Reverse: from target back to source
        source_path = move_info['to']  # Where it was moved TO
        target_path = move_info['from']  # Where it came FROM
        model_name = move_info['model_name']
        
        moves_completed += 1
        if progress is not None:
            progress(moves_completed / total_moves, 
                    desc=f"Rolling back: {model_name} ({moves_completed}/{total_moves})")
        
        try:
            # Check if source file exists (file might have been deleted/moved)
            if not os.path.exists(source_path):
                errors.append(f"File not found (may have been moved): {model_name}")
                continue
            
            # Create target directory if it doesn't exist
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            
            # Check if target already exists
            if os.path.exists(target_path):
                errors.append(f"Target already exists, skipping: {model_name}")
                continue
            
            # Move main file back
            shutil.move(source_path, target_path)
            
            # Move associated files back
            base_name_source = os.path.splitext(source_path)[0]
            base_name_target = os.path.splitext(target_path)[0]
            
            associated_extensions = ['.json', '.png', '.jpg', '.jpeg', '.txt', '.html', '.civitai.info']
            
            # Move exact matches back
            for ext in associated_extensions:
                associated_source = base_name_source + ext
                associated_target = base_name_target + ext
                
                if os.path.exists(associated_source):
                    try:
                        shutil.move(associated_source, associated_target)
                        debug_print(f"Rolled back: {os.path.basename(associated_source)}")
                    except Exception as e:
                        debug_print(f"Could not move associated file back: {e}")
            
            # Move numbered preview images back (_0.png, _1.png, etc.)
            for i in range(20):
                for ext in ['.png', '.jpg', '.jpeg']:
                    numbered_source = f"{base_name_source}_{i}{ext}"
                    if os.path.exists(numbered_source):
                        numbered_target = f"{base_name_target}_{i}{ext}"
                        try:
                            shutil.move(numbered_source, numbered_target)
                            debug_print(f"Rolled back preview: {os.path.basename(numbered_source)}")
                        except Exception as e:
                            debug_print(f"Could not rollback preview {numbered_source}: {e}")
            
            # Move suffixed files back (.preview, .api_info, .civitai)
            suffixes = ['.preview', '.api_info', '.civitai']
            for suffix in suffixes:
                for ext in associated_extensions:
                    suffixed_source = base_name_source + suffix + ext
                    if os.path.exists(suffixed_source):
                        suffixed_target = base_name_target + suffix + ext
                        try:
                            shutil.move(suffixed_source, suffixed_target)
                            debug_print(f"Rolled back {suffix}: {os.path.basename(suffixed_source)}")
                        except Exception as e:
                            debug_print(f"Could not rollback {suffixed_source}: {e}")
            
            print(f"✓ Rolled back: {model_name}")
            
        except Exception as e:
            error_msg = f"Failed to rollback {model_name}: {str(e)}"
            errors.append(error_msg)
            debug_print(error_msg)
    
    # Clean up empty folders created during organization
    try:
        for move_info in moves:
            folder = os.path.dirname(move_info['to'])
            if os.path.exists(folder) and not os.listdir(folder):
                os.rmdir(folder)
                print(f"Removed empty folder: {folder}")
    except Exception as e:
        debug_print(f"Error cleaning up folders: {e}")
    
    return {
        'success': len(errors) == 0,
        'completed': moves_completed,
        'total': total_moves,
        'errors': errors,
        'message': f"Successfully rolled back {moves_completed} files" if len(errors) == 0 else f"Completed with {len(errors)} errors"
    }

def execute_organization(organization_plan, progress=None):
    """
    Execute the organization plan by moving files
    Moves model files along with associated .json, .png, .txt files
    """
    total_moves = len(organization_plan['moves'])
    moves_completed = 0
    errors = []
    
    for move_info in organization_plan['moves']:
        if gl.cancel_status:
            return {
                'success': False,
                'completed': moves_completed,
                'total': total_moves,
                'errors': errors,
                'message': 'Organization cancelled by user'
            }
        
        source_path = move_info['from']
        target_path = move_info['to']
        model_name = move_info['model_name']
        
        moves_completed += 1
        if progress is not None:
            progress(moves_completed / total_moves, 
                    desc=f"Organizing: {model_name} ({moves_completed}/{total_moves})")
        
        try:
            # Create target directory if it doesn't exist
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            
            # Check if target file already exists
            if os.path.exists(target_path):
                debug_print(f"Target already exists, skipping: {target_path}")
                continue
            
            # Move main model file
            shutil.move(source_path, target_path)
            
            # Move associated files
            # First, handle exact matches (.json, .png, etc.)
            base_name = os.path.splitext(source_path)[0]
            target_base_name = os.path.splitext(target_path)[0]
            source_dir = os.path.dirname(source_path)
            
            # Extensions to move (both with and without .preview suffix)
            associated_extensions = ['.json', '.png', '.jpg', '.jpeg', '.txt', '.html', '.civitai.info']
            
            # Move files with exact base name
            for ext in associated_extensions:
                associated_file = base_name + ext
                if os.path.exists(associated_file):
                    target_associated = target_base_name + ext
                    try:
                        shutil.move(associated_file, target_associated)
                        debug_print(f"Moved associated file: {os.path.basename(associated_file)}")
                    except Exception as e:
                        debug_print(f"Could not move associated file {associated_file}: {e}")
            
            # Move numbered preview images (e.g., model_0.png, model_1.png, ...)
            import glob
            model_basename = os.path.basename(base_name)
            for i in range(20):  # Support up to 20 preview images
                for ext in ['.png', '.jpg', '.jpeg']:
                    numbered_file = f"{base_name}_{i}{ext}"
                    if os.path.exists(numbered_file):
                        target_numbered = f"{target_base_name}_{i}{ext}"
                        try:
                            shutil.move(numbered_file, target_numbered)
                            debug_print(f"Moved numbered preview: {os.path.basename(numbered_file)}")
                        except Exception as e:
                            debug_print(f"Could not move numbered preview {numbered_file}: {e}")
            
            # Also move files with .preview, .api_info suffixes before extension
            # e.g., model.preview.png, model.api_info.json
            suffixes = ['.preview', '.api_info', '.civitai']
            for suffix in suffixes:
                for ext in associated_extensions:
                    associated_file = base_name + suffix + ext
                    if os.path.exists(associated_file):
                        target_associated = target_base_name + suffix + ext
                        try:
                            shutil.move(associated_file, target_associated)
                            debug_print(f"Moved associated file: {os.path.basename(associated_file)}")
                        except Exception as e:
                            debug_print(f"Could not move associated file {associated_file}: {e}")
            
            print(f"✓ Organized: {model_name} → {move_info['base_model']}/")
            
        except Exception as e:
            error_msg = f"Failed to move {model_name}: {str(e)}"
            errors.append(error_msg)
            debug_print(error_msg)
    
    return {
        'success': len(errors) == 0,
        'completed': moves_completed,
        'total': total_moves,
        'errors': errors,
        'message': f"Successfully organized {moves_completed} files" if len(errors) == 0 else f"Completed with {len(errors)} errors"
    }

def organize_start(organize_start):
    set_globals('from_organize')
    number = _download.random_number(organize_start)
    return start_returns(number)

def rollback_organization(progress=gr.Progress() if queue else None):
    """
    Rollback the last organization operation
    """
    backup = get_last_organization_backup()
    
    if not backup:
        return gr.update(value='''
            <div style="padding: 20px; text-align: center;">
                <h3>ℹ️ No Backup Found</h3>
                <p>There is no recent organization to undo.</p>
                <p>Organization backups are only available for operations performed in the current session.</p>
            </div>
        ''')
    
    # Show confirmation with backup details
    total_files = len(backup.get('moves', []))
    timestamp = backup.get('timestamp', 'Unknown')
    
    if progress is not None:
        progress(0, desc=f"Starting rollback of {total_files} files...")
    
    print(f"[CivitAI Browser Neo] Starting rollback (Backup: {timestamp})...")
    
    result = execute_rollback(progress)
    
    # Get backup stats if available
    stats = backup.get('stats', {})
    total_size = stats.get('total_size', 0)
    
    # Generate compact result message
    if result['success']:
        result_html = f'''
        <div style="padding: 20px; text-align: center; color: var(--color-accent);">
            <h2 style="margin: 0 0 15px 0;">✅ Rollback Complete!</h2>
            <div style="font-size: 16px;">
                <strong>{result['completed']} files</strong> {f'({format_size(total_size)})' if total_size > 0 else ''} restored to original locations
            </div>
            <div style="margin-top: 10px; font-size: 13px; opacity: 0.8;">
                Backup: {timestamp}
            </div>
        </div>
        '''
    else:
        error_list = '<br>'.join(result['errors'][:10])
        if len(result['errors']) > 10:
            error_list += f'<br><em>... and {len(result["errors"]) - 10} more errors</em>'
        
        result_html = f'''
        <div style="padding: 20px; text-align: center; color: var(--error-text-color);">
            <h2 style="margin: 0 0 15px 0;">⚠️ Rollback Completed with Errors</h2>
            <div style="font-size: 16px; margin-bottom: 15px;">
                {result['completed']}/{result['total']} files restored | {len(result['errors'])} errors
            </div>
            <details style="text-align: left;">
                <summary style="cursor: pointer; padding: 8px; background: var(--block-background-fill); border-radius: 5px;">
                    View errors
                </summary>
                <div style="margin-top: 10px; padding: 10px; background: var(--block-background-fill); border-radius: 5px; font-size: 13px; max-height: 200px; overflow-y: auto;">
                    {error_list}
                </div>
            </details>
        </div>
        '''
    
    print(f"[CivitAI Browser Neo] {result['message']}")
    return gr.update(value=result_html)

def save_tag_finish():
    set_globals('reset')
    return finish_returns()

def save_preview_finish():
    set_globals('reset')
    return finish_returns()

def generate_dashboard_statistics(selected_types, progress=gr.Progress() if queue else None):
    """
    Generate dashboard statistics showing disk usage by model type
    Returns HTML with detailed breakdown of files and sizes per folder
    """
    import os
    import math
    from collections import defaultdict
    
    # Format sizes helper function
    def format_size(size_bytes):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    if progress is not None:
        progress(0, desc="Starting dashboard generation...")
    
    # Get content types to scan
    if not selected_types:
        return gr.update(value='<div style="padding: 20px; text-align: center;">Please select at least one content type to scan.</div>')
    
    # Dictionary to store stats: {category: {'count': int, 'size': int}}
    model_stats = defaultdict(lambda: {'count': 0, 'size': 0})
    total_files = 0
    total_size = 0
    
    # Extensions to scan
    MODEL_EXTENSIONS = ('.safetensors', '.ckpt', '.pt', '.pth', '.vae', '.zip', '.th')
    
    # Process each content type
    for content_type in selected_types:
        if progress is not None:
            progress(0.1, desc=f"Scanning {content_type}...")
        
        # Get base folder
        folder = None
        if content_type == 'Upscaler':
            # Upscalers have multiple subfolders - handle separately
            for desc in ['ESRGAN', 'RealESRGAN', 'SwinIR', 'GFPGAN', 'BSRGAN']:
                upscaler_folder = _api.contenttype_folder('Upscaler', desc)
                if upscaler_folder and os.path.isdir(str(upscaler_folder)):
                    category = f'Upscaler ({desc})'
                    # Scan all files in this upscaler folder
                    for root, dirs, files in os.walk(str(upscaler_folder)):
                        for file in files:
                            if file.endswith(MODEL_EXTENSIONS):
                                file_path = os.path.join(root, file)
                                try:
                                    file_size = os.path.getsize(file_path)
                                    model_stats[category]['count'] += 1
                                    model_stats[category]['size'] += file_size
                                    total_files += 1
                                    total_size += file_size
                                except:
                                    pass
            continue
        elif content_type == 'Wildcards':
            folder = _api.contenttype_folder('Wildcards')
            wildcard_extensions = ('.txt', '.yaml', '.yml')
        elif content_type == 'Workflows':
            folder = _api.contenttype_folder('Workflows')
            wildcard_extensions = ('.json', '.workflow')
        else:
            folder = _api.contenttype_folder(content_type)
            wildcard_extensions = MODEL_EXTENSIONS
        
        if not folder or not os.path.isdir(str(folder)):
            continue
        
        folder_str = str(folder)
        print(f"\n[Dashboard] Scanning {content_type} folder: {folder_str}")
        
        # For Checkpoint and LORA: scan subfolders and categorize
        if content_type in ['Checkpoint', 'LORA']:
            # First, check if there are subfolders
            subfolders = []
            root_files = []
            
            for item in os.listdir(folder_str):
                item_path = os.path.join(folder_str, item)
                if os.path.isdir(item_path):
                    subfolders.append(item)
                    print(f"[Dashboard]   Found subfolder: {item}")
                elif item.endswith(MODEL_EXTENSIONS):
                    root_files.append(item_path)
            
            print(f"[Dashboard]   Total subfolders: {len(subfolders)}")
            print(f"[Dashboard]   Files in root: {len(root_files)}")
            
            # Process files in root (not in subfolders)
            if root_files:
                category = f'{content_type} → Não classificado'
                for file_path in root_files:
                    try:
                        file_size = os.path.getsize(file_path)
                        model_stats[category]['count'] += 1
                        model_stats[category]['size'] += file_size
                        total_files += 1
                        total_size += file_size
                    except:
                        pass
                print(f"[Dashboard]   Category '{category}': {model_stats[category]['count']} files")
            
            # Process each subfolder
            for subfolder in subfolders:
                subfolder_path = os.path.join(folder_str, subfolder)
                # Use the actual folder name as the category
                # This shows how the user has actually organized their models
                category = f'{content_type} → {subfolder}'
                
                print(f"[Dashboard]   Scanning subfolder: {subfolder}")
                print(f"[Dashboard]   Category key: '{category}'")
                folder_file_count = 0
                folder_size_before = model_stats[category]['size']
                
                # Scan all files in subfolder (including nested subfolders)
                for root, dirs, files in os.walk(subfolder_path):
                    for file in files:
                        if file.endswith(MODEL_EXTENSIONS):
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                model_stats[category]['count'] += 1
                                model_stats[category]['size'] += file_size
                                total_files += 1
                                total_size += file_size
                                folder_file_count += 1
                                
                                # Debug first 2 files per folder
                                if folder_file_count <= 2:
                                    print(f"[Dashboard]     File: {file} → {format_size(file_size)}")
                            except Exception as e:
                                print(f"[Dashboard]     ERROR reading {file}: {e}")
                
                folder_size_after = model_stats[category]['size']
                print(f"[Dashboard]     → Found {folder_file_count} files in '{subfolder}'")
                print(f"[Dashboard]     → Total size: {format_size(folder_size_after)}")
                print(f"[Dashboard]     → Added: {format_size(folder_size_after - folder_size_before)}")
                print()
        
        else:
            # For other types: just count all files in folder
            category = content_type
            for root, dirs, files in os.walk(folder_str):
                for file in files:
                    if file.endswith(wildcard_extensions if content_type in ['Wildcards', 'Workflows'] else MODEL_EXTENSIONS):
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            model_stats[category]['count'] += 1
                            model_stats[category]['size'] += file_size
                            total_files += 1
                            total_size += file_size
                        except:
                            pass
    
    if total_files == 0:
        return gr.update(value='<div style="padding: 20px; text-align: center;">No model files found in selected directories.</div>')
    
    # Debug: Show final model_stats before sorting
    print("\n[Dashboard] === FINAL STATS BEFORE SORTING ===")
    for cat, stats in model_stats.items():
        print(f"[Dashboard]   {cat}: {stats['count']} files, {format_size(stats['size'])}")
    print("[Dashboard] ===================================\n")
    
    if progress is not None:
        progress(1.0, desc="Generating dashboard...")
    
    # Sort by size (descending)
    sorted_stats = sorted(model_stats.items(), key=lambda x: x[1]['size'], reverse=True)
    
    # Generate HTML
    html_parts = []
    
    # Header with total stats
    html_parts.append(f'''
    <div style="padding: 20px; font-family: Arial, sans-serif;">
        <h2 style="margin: 0 0 20px 0; color: var(--body-text-color); text-align: center;">
            📊 Model Collection Dashboard
        </h2>
        <div style="text-align: center; font-size: 18px; margin-bottom: 30px; padding: 15px; background: var(--block-background-fill); border-radius: 8px;">
            <strong>{total_files} files ({format_size(total_size)}) → {len(model_stats)} categories</strong>
        </div>
    ''')
    
    # Pie chart - Always show when there's data
    if sorted_stats and len(sorted_stats) > 0:
        try:
            print(f"[Dashboard] Generating pie chart for {len(sorted_stats)} categories")
            # Generate pie chart using SVG
            pie_colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#FF6B9D', '#C9CBCF', '#8DD3C7', '#FFED6F',
                '#BEBADA', '#FB8072', '#80B1D3', '#FDB462', '#B3DE69'
            ]
            
            # Prepare data for top categories (show top 8, group rest as "Others")
            top_categories = sorted_stats[:8]
            other_size = sum(stats['size'] for _, stats in sorted_stats[8:])
            other_count = sum(stats['count'] for _, stats in sorted_stats[8:])
            
            if len(sorted_stats) > 8 and other_size > 0:
                chart_data = top_categories + [('Others', {'size': other_size, 'count': other_count})]
            else:
                chart_data = sorted_stats
            
            print(f"[Dashboard] Chart will show {len(chart_data)} categories")
            
            # Calculate angles for pie slices
            total = sum(stats['size'] for _, stats in chart_data)
            angles = []
            current_angle = 0
            
            for category, stats in chart_data:
                percentage = (stats['size'] / total * 100) if total > 0 else 0
                angle = (stats['size'] / total * 360) if total > 0 else 0
                angles.append((category, percentage, current_angle, current_angle + angle, stats))
                current_angle += angle
            
            print(f"[Dashboard] Calculated {len(angles)} pie slices")
            
            # Generate SVG pie chart
            svg_parts = []
            svg_parts.append('''
            <div style="display: flex; justify-content: center; margin: 30px 0; flex-wrap: wrap; gap: 40px; align-items: center;">
                <div style="position: relative;">
                    <svg viewBox="0 0 200 200" style="width: 300px; height: 300px; transform: rotate(-90deg);">
            ''')
            
            slice_count = 0
            for i, (category, percentage, start_angle, end_angle, stats) in enumerate(angles):
                if percentage < 0.1:  # Skip very small slices
                    print(f"[Dashboard] Skipping tiny slice: {category} ({percentage:.2f}%)")
                    continue
                
                slice_count += 1
                
                # Convert angles to radians
                start_rad = start_angle * math.pi / 180
                end_rad = end_angle * math.pi / 180
                
                # Calculate arc path
                x1 = 100 + 90 * math.cos(start_rad)
                y1 = 100 + 90 * math.sin(start_rad)
                x2 = 100 + 90 * math.cos(end_rad)
                y2 = 100 + 90 * math.sin(end_rad)
                
                large_arc = 1 if (end_angle - start_angle) > 180 else 0
                
                color = pie_colors[i % len(pie_colors)]
                
                svg_parts.append(f'''
                    <path d="M 100 100 L {x1:.2f} {y1:.2f} A 90 90 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
                          fill="{color}" stroke="#ffffff" stroke-width="2"
                          style="transition: opacity 0.3s; cursor: pointer;"
                          onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">
                        <title>{category}: {format_size(stats['size'])} ({percentage:.1f}%)</title>
                    </path>
                ''')
            
            print(f"[Dashboard] Generated {slice_count} SVG slices")
            
            svg_parts.append('''
                    </svg>
                </div>
                <div style="display: flex; flex-direction: column; justify-content: center; gap: 8px; max-width: 300px;">
            ''')
            
            # Legend
            legend_count = 0
            for i, (category, percentage, _, _, stats) in enumerate(angles):
                if percentage < 0.1:
                    continue
                legend_count += 1
                color = pie_colors[i % len(pie_colors)]
                svg_parts.append(f'''
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 20px; height: 20px; background: {color}; border-radius: 3px; flex-shrink: 0;"></div>
                        <div style="color: var(--body-text-color); font-size: 13px;">
                            <strong>{category}</strong><br>
                            <span style="color: var(--body-text-color-subdued); font-size: 12px;">
                                {format_size(stats['size'])} ({percentage:.1f}%)
                            </span>
                        </div>
                    </div>
                ''')
            
            print(f"[Dashboard] Generated {legend_count} legend items")
            
            svg_parts.append('''
                </div>
            </div>
            ''')
            
            html_parts.append(''.join(svg_parts))
            print(f"[Dashboard] Pie chart HTML added ({len(''.join(svg_parts))} chars)")
        except Exception as e:
            # If pie chart fails, log error but continue with table
            error_msg = f'Pie chart generation failed: {str(e)}'
            print(f"[Dashboard ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            html_parts.append(f'<div style="color: red; padding: 10px; text-align: center;">{error_msg}</div>')
    
    # Table with breakdown
    if sorted_stats:
        html_parts.append('''
        <table style="width: 100%; border-collapse: collapse; margin: 0 auto; max-width: 900px;">
            <thead>
                <tr style="background: var(--block-title-background-fill); border-bottom: 2px solid var(--border-color-primary);">
                    <th style="padding: 12px; text-align: left; font-size: 14px;">MODEL TYPE</th>
                    <th style="padding: 12px; text-align: center; font-size: 14px;">FILES</th>
                    <th style="padding: 12px; text-align: right; font-size: 14px;">TOTAL SIZE</th>
                    <th style="padding: 12px; text-align: right; font-size: 14px;">% OF TOTAL</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        for category, stats in sorted_stats:
            percentage = (stats['size'] / total_size * 100) if total_size > 0 else 0
            
            # Create visual bar for percentage
            bar_width = int(percentage)
            bar_html = f'''
            <div style="background: linear-gradient(90deg, var(--primary-500) 0%, var(--primary-400) 100%); 
                        height: 6px; width: {bar_width}%; border-radius: 3px; margin-top: 4px;"></div>
            '''
            
            html_parts.append(f'''
                <tr style="border-bottom: 1px solid var(--border-color-primary);">
                    <td style="padding: 12px; font-weight: bold; color: var(--body-text-color);">
                        {category}
                        {bar_html}
                    </td>
                    <td style="padding: 12px; text-align: center; color: var(--body-text-color-subdued);">
                        {stats['count']}
                    </td>
                    <td style="padding: 12px; text-align: right; color: var(--body-text-color);">
                        {format_size(stats['size'])}
                    </td>
                    <td style="padding: 12px; text-align: right; color: var(--body-text-color-subdued);">
                        {percentage:.1f}%
                    </td>
                </tr>
            ''')
        
        html_parts.append('''
            </tbody>
        </table>
        ''')
    
    # Footer
    html_parts.append(f'''
        <div style="margin-top: 20px; text-align: center; font-size: 13px; color: var(--body-text-color-subdued);">
            <em>Dashboard generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em>
        </div>
    </div>
    ''')
    
    return gr.update(value=''.join(html_parts))


def scan_finish():
    set_globals('reset')
    return (
        gr.update(interactive=no_update, visible=no_update),
        gr.update(interactive=no_update, visible=no_update),
        gr.update(interactive=no_update, visible=no_update),
        gr.update(interactive=no_update, visible=no_update),
        gr.update(interactive=no_update, visible=False),
        gr.update(interactive=False, visible=False),
        gr.update(interactive=not no_update, visible=not no_update)
    )

## === ANXETY EDITs ===
def load_to_browser(content_type, sort_type, period_type, use_search_term, search_term, tile_count, base_filter, nsfw, exact_search):
    global from_ver, from_installed

    model_list_return = _api.initial_model_page(content_type, sort_type, period_type, use_search_term, search_term, 1, base_filter, False, nsfw, exact_search, tile_count, True)
    from_ver, from_installed =  False, False
    return (
        *model_list_return,
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=True, visible=True),
        gr.update(interactive=False, visible=False),
        gr.update(interactive=False, visible=False),
        gr.update(value='<div style="min-height: 0px;"></div>')
    )

def cancel_scan():
    gl.cancel_status = True

    while True:
        if not gl.scan_files:
            gl.cancel_status = False
            return
        else:
            time.sleep(0.5)
            continue