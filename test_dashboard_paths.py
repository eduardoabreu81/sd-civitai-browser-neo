#!/usr/bin/env python3
"""
Test script to debug dashboard folder detection
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import from scripts
try:
    from scripts import civitai_neo
    _api = civitai_neo
except:
    print("Could not import civitai_neo, trying alternative...")
    try:
        import civitai_neo as _api
    except:
        print("ERROR: Could not import civitai_neo")
        sys.exit(1)

MODEL_EXTENSIONS = ('.safetensors', '.ckpt', '.pt', '.pth', '.vae', '.zip', '.th')

def test_checkpoint_folder():
    """Test what the dashboard sees for Checkpoint folder"""
    
    # Get Checkpoint folder
    content_type = 'Checkpoint'
    folder = _api.contenttype_folder(content_type)
    
    if not folder:
        print(f"ERROR: Could not get folder for {content_type}")
        return
    
    folder_str = str(folder)
    print(f"\n{'='*70}")
    print(f"Checkpoint Folder: {folder_str}")
    print(f"{'='*70}")
    
    if not os.path.isdir(folder_str):
        print(f"ERROR: Folder does not exist: {folder_str}")
        return
    
    # List all items in folder
    print(f"\nScanning folder contents...")
    subfolders = []
    root_files = []
    
    try:
        items = os.listdir(folder_str)
        print(f"Total items in folder: {len(items)}")
        
        for item in items:
            item_path = os.path.join(folder_str, item)
            if os.path.isdir(item_path):
                subfolders.append(item)
                print(f"  [DIR]  {item}")
            elif item.endswith(MODEL_EXTENSIONS):
                root_files.append(item_path)
                print(f"  [FILE] {item}")
    except Exception as e:
        print(f"ERROR listing folder: {e}")
        return
    
    print(f"\n{'-'*70}")
    print(f"Summary:")
    print(f"  Subfolders: {len(subfolders)}")
    print(f"  Files in root: {len(root_files)}")
    print(f"{'-'*70}")
    
    # Scan each subfolder
    for subfolder in subfolders:
        subfolder_path = os.path.join(folder_str, subfolder)
        file_count = 0
        total_size = 0
        
        try:
            for root, dirs, files in os.walk(subfolder_path):
                for file in files:
                    if file.endswith(MODEL_EXTENSIONS):
                        file_path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(file_path)
                            file_count += 1
                            total_size += size
                        except:
                            pass
            
            # Format size
            size_str = f"{total_size / (1024**3):.1f} GB"
            print(f"\n  📁 {subfolder}")
            print(f"     Files: {file_count}")
            print(f"     Size:  {size_str}")
        except Exception as e:
            print(f"\n  📁 {subfolder}")
            print(f"     ERROR: {e}")
    
    if root_files:
        total_size = sum(os.path.getsize(f) for f in root_files)
        size_str = f"{total_size / (1024**3):.1f} GB"
        print(f"\n  📄 Files in root (Não classificado)")
        print(f"     Files: {len(root_files)}")
        print(f"     Size:  {size_str}")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    test_checkpoint_folder()
