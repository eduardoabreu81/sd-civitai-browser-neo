#!/usr/bin/env python3
"""
Test script to debug dashboard folder detection on RunPod
Run this in the Forge Neo terminal on RunPod
"""
import os

# RunPod paths
FORGE_PATH = "/workspace/stable-diffusion-webui-forge-neo"
MODELS_PATH = os.path.join(FORGE_PATH, "models")

MODEL_EXTENSIONS = ('.safetensors', '.ckpt', '.pt', '.pth', '.vae', '.zip', '.th')

def format_size(size_bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def test_checkpoint_folder():
    """Test what the dashboard sees for Checkpoint folder"""
    
    # Try common checkpoint folder locations
    possible_paths = [
        os.path.join(MODELS_PATH, "Stable-diffusion"),
        os.path.join(MODELS_PATH, "checkpoints"),
        os.path.join(FORGE_PATH, "Stable-diffusion"),
    ]
    
    folder_str = None
    for path in possible_paths:
        if os.path.isdir(path):
            folder_str = path
            break
    
    if not folder_str:
        print("ERROR: Could not find Checkpoint folder")
        print("Checked:")
        for p in possible_paths:
            print(f"  - {p}")
        return
    
    print(f"\n{'='*70}")
    print(f"Checkpoint Folder: {folder_str}")
    print(f"{'='*70}")
    
    # List all items in folder
    print(f"\nScanning folder contents...")
    subfolders = []
    root_files = []
    
    try:
        items = os.listdir(folder_str)
        print(f"Total items in folder: {len(items)}")
        print()
        
        for item in items:
            item_path = os.path.join(folder_str, item)
            if os.path.isdir(item_path):
                subfolders.append(item)
                print(f"  [DIR]  {item}/")
            elif item.endswith(MODEL_EXTENSIONS):
                size = os.path.getsize(item_path)
                root_files.append((item_path, size))
                print(f"  [FILE] {item} ({format_size(size)})")
    except Exception as e:
        print(f"ERROR listing folder: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n{'-'*70}")
    print(f"Summary:")
    print(f"  Subfolders: {len(subfolders)}")
    print(f"  Files in root: {len(root_files)}")
    print(f"{'-'*70}\n")
    
    # Scan each subfolder
    all_stats = []
    
    for subfolder in sorted(subfolders):
        subfolder_path = os.path.join(folder_str, subfolder)
        file_count = 0
        total_size = 0
        files_list = []
        
        try:
            for root, dirs, files in os.walk(subfolder_path):
                for file in files:
                    if file.endswith(MODEL_EXTENSIONS):
                        file_path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(file_path)
                            file_count += 1
                            total_size += size
                            files_list.append((file, size))
                        except Exception as e:
                            print(f"     ERROR reading {file}: {e}")
            
            all_stats.append((subfolder, file_count, total_size))
            
            print(f"📁 {subfolder}/")
            print(f"   Files: {file_count}")
            print(f"   Size:  {format_size(total_size)}")
            print(f"   % of total: {(total_size / (1024**3) / 987.9 * 100):.1f}%")
            
            # Show first 3 files as sample
            if files_list and file_count > 0:
                print(f"   Sample files:")
                for fname, fsize in sorted(files_list, key=lambda x: x[1], reverse=True)[:3]:
                    print(f"     - {fname} ({format_size(fsize)})")
            print()
            
        except Exception as e:
            print(f"📁 {subfolder}/")
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    if root_files:
        total_size = sum(size for _, size in root_files)
        print(f"📄 Files in root (Não classificado)")
        print(f"   Files: {len(root_files)}")
        print(f"   Size:  {format_size(total_size)}")
        print(f"   % of total: {(total_size / (1024**3) / 987.9 * 100):.1f}%")
        for fpath, fsize in root_files[:3]:
            print(f"     - {os.path.basename(fpath)} ({format_size(fsize)})")
        print()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"FINAL SUMMARY (sorted by size):")
    print(f"{'='*70}")
    for subfolder, count, size in sorted(all_stats, key=lambda x: x[2], reverse=True):
        pct = (size / (1024**3) / 987.9 * 100)
        print(f"  {subfolder:20s} {count:4d} files  {format_size(size):>12s}  {pct:5.1f}%")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    test_checkpoint_folder()
