# Ugm Upgrade Manager

A tool to upgrade CircuitPython firmware from a FastAPI update server.

## ✨ Features

- 🔍 **Version Check**: Automatically checks the update server for new firmware versions.
- 💾 **Pre-Upgrade Backup**: Backs up files that are modified or deleted in the new version.
- 📥 **Selective Download**: Only downloads and replaces files that are new or changed, optimizing the upgrade process.
- 🔄 **Automatic Rollback**: Detects failed upgrades and restores all previous files from the backup.

## ⚠️ Critical Files and Dependencies

Modifying any of the following files or packages may compromise upgrade stability:

### 📂 Files
- `code.py`
- All files in the `ugm` folder

### 📦 Packages
- `cptoml`
- `adafruit_requests`
- `socketpool`
- `wifi`
- `dirTree`

## 🚫 .ignore

Specifies files and directories to ignore during the upgrade process (similar to `.gitignore`).

### Default Example
```
ugm
json_queue
settings.toml
code.py
```

# dirTree

This module provides tools for efficient file and folder management, including hashing, copying, moving, and comparing directory structures. It is designed for platforms that support either CircuitPython’s `adafruit_hashlib` or Python’s native `hashlib`.

## ✨ Features

- 🔍 **MD5 Hash Calculation**: Computes the MD5 hash for individual files or entire folder structures.
- 📂 **File and Folder Management**: 
  - **Join Paths**: Combines paths similar to `os.path.join`.
  - **Basename Extraction**: Retrieves the base name of a file path.
  - **Move and Copy Files/Folders**: Supports safe moving or copying, including recursive operations on folders.
- 🧩 **Directory Difference Calculation**: Detects and moves the differences between directory structures.
- 🚫 **Selective Exclusion**: Allows specifying files or folders to ignore during operations.

## 📁 Class and Method Overview

### Functions
- `join_path`: Combines paths, handling relative paths.
- `basename`: Extracts the last part of a path.
- `calculate_md5`: Computes the MD5 hash of a file based on the filename and its content.

### Classes
- **`Entry`**: Abstract base class for handling both files and folders.
- **`FileEntry`**: Manages individual files, including their paths and MD5 checksums.
  - Supports `move`, `copy`, and dictionary serialization.
- **`FolderEntry`**: Manages folders, including contents and a cumulative MD5 checksum.
  - Supports recursive operations like `move`, `copy`, `drop` (for ignored paths), and `move_diff` (to move only differences).

## ⚙️ Key Usage

### Calculate MD5 for a File
```python
md5_hash = calculate_md5("path/to/file.txt")
```

### Move a Folder
```python
folder = FolderEntry("path/to/folder")
folder.move("path/to/destination")
```

### Compare Two Folders and Move Differences
```python
folder_a = FolderEntry("path/to/folderA")
folder_b = FolderEntry("path/to/folderB")
folder_a.move_diff(folder_b, "path/to/target")
```

## ⚠️ Platform-Specific Imports
This module automatically imports `adafruit_hashlib` on ESP32 platforms, and `hashlib` on others.