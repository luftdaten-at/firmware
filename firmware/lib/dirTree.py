import os

# Import hashlib depending on the platform
if 'ESP32' in os.uname().sysname:
    import adafruit_hashlib as hashlib
else:
    import hashlib

# Read files in chunks to be RAM efficient
CHUNK_SIZE = 1024

def join_path(path: str, *paths: str) -> str:
    """
    Joins one or more path components intelligently.
    
    Args:
        path (str): The initial path.
        *paths (str): Additional paths to join.

    Returns:
        str: The joined path.
    """
    for p in paths:
        if path == "":
            path = p
        elif path.endswith('/'):
            path += p
        else:
            path += '/' + p
    return path

def basename(path: str) -> str:
    """
    Returns the base name of the path, removing any leading directory components.
    
    Args:
        path (str): The path to process.

    Returns:
        str: The base name of the path.
    """
    # Remove any trailing slashes from the path
    path = path.rstrip('/')

    # Split the path by the directory separator and return the last component
    parts = path.split('/')
    return parts[-1] if parts else ''

def calculate_md5(file_path: str) -> str:
    """
    Calculates the MD5 hash of a file.
    
    The hash is computed from the file's content and the base name of the file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The MD5 hash of the file's content.
    """
    md5_hash = hashlib.md5()
    md5_hash.update(basename(file_path).encode())
    with open(file_path, "rb") as firmware_file:
        while chunk := firmware_file.read(CHUNK_SIZE):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

class Entry:
    """
    Abstract base class for file and folder entries.
    
    Attributes:
        path (str): The path to the entry.
        md5_checksum (str): The MD5 checksum of the entry.
    """
    def __init__(self, path: str, md5_checksum: str) -> None:
        """
        Initializes an Entry instance.

        Args:
            path (str): The path to the entry.
            md5_checksum (str): The MD5 checksum of the entry.
        """
        self.path: str = path
        self.md5_checksum: str = md5_checksum

    def to_dict(self) -> dict:
        """
        Converts the entry to a dictionary representation.
        
        Returns:
            dict: The dictionary representation of the entry.
        """
        pass

    def move(self, target_path: str) -> None:
        """
        Moves the entry to a target path.
        
        Args:
            target_path (str): The destination path.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        pass

    @staticmethod
    def from_dict(d: dict) -> 'Entry':
        """
        Creates an entry from a dictionary representation.

        Args:
            d (dict): The dictionary representation.

        Returns:
            Entry: An instance of FileEntry or FolderEntry.
        """
        if 'childs' in d:
            return FolderEntry.from_dict(d)
        else:
            return FileEntry.from_dict(d)

class FileEntry(Entry):
    """
    Represents a file entry in the file system.

    Inherits from Entry.

    Attributes:
        path (str): The path to the file.
        md5_checksum (str): The MD5 checksum of the file.
    """
    def __init__(self, path: str, md5_checksum: str = None) -> None:
        """
        Initializes a FileEntry instance.

        Args:
            path (str): The path to the file.
            md5_checksum (str, optional): The MD5 checksum of the file. If not provided, it is calculated.
        """
        if not md5_checksum:
            md5_checksum = calculate_md5(path)
        super().__init__(path, md5_checksum)

    def to_dict(self) -> dict:
        """
        Converts the file entry to a dictionary representation.

        Returns:
            dict: The dictionary representation of the file entry.
        """
        return {
            'path': self.path,
            'md5_checksum': self.md5_checksum
        }
    
    def move(self, target_path: str) -> None:
        """
        Moves the file to a target path.

        Args:
            target_path (str): The destination path.
        """
        target_path = join_path(target_path, basename(self.path))
        with open(self.path, 'rb') as srcf:
            with open(target_path, 'wb') as dstf:
                while (chunk := srcf.read(CHUNK_SIZE)):
                    dstf.write(chunk)
        os.remove(self.path)
        self.path = target_path

    def __str__(self) -> str:
        """
        Returns a string representation of the file entry.

        Returns:
            str: String representation of the file entry.
        """
        return f"File: {self.path}, md5_checksum: {self.md5_checksum}"

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def from_dict(d: dict) -> 'FileEntry':
        """
        Creates a FileEntry from a dictionary representation.

        Args:
            d (dict): The dictionary representation.

        Returns:
            FileEntry: An instance of FileEntry.
        """
        return FileEntry(d['path'], d['md5_checksum'])

class FolderEntry(Entry):
    """
    Represents a folder entry in the file system.

    Inherits from Entry.

    Attributes:
        path (str): The path to the folder.
        childs (list[Entry]): A list of child entries (files or folders).
        md5_checksum (str): The MD5 checksum of the folder.
    """
    def __init__(self, path: str, md5_checksum: str = None, childs: list = None) -> None:
        """
        Initializes a FolderEntry instance.

        Args:
            path (str): The path to the folder.
            md5_checksum (str, optional): The MD5 checksum of the folder. If not provided, it is calculated.
            childs (list, optional): A list of child entries.
        """
        self.childs: list[Entry] = childs if childs else []
        if not md5_checksum:
            md5_builder = hashlib.md5()
            md5_builder.update(basename(path).encode()) 
            for name in os.listdir(path):
                entry_path = join_path(path, name)
                if os.stat(entry_path)[0] & 0x4000:  # Check if the item is a directory
                    self.childs.append(FolderEntry(entry_path))
                else:
                    self.childs.append(FileEntry(entry_path))
                md5_builder.update(self.childs[-1].md5_checksum.encode())
            md5_checksum = md5_builder.hexdigest()
        super().__init__(path, md5_checksum)

    def to_dict(self) -> dict:
        """
        Converts the folder entry to a dictionary representation.

        Returns:
            dict: The dictionary representation of the folder entry.
        """
        return {
            'path': self.path,
            'childs': [child.to_dict() for child in self.childs],
            'md5_checksum': self.md5_checksum
        }
    
    def move(self, target_path: str) -> None:
        """
        Moves the folder and its contents to a target path.

        Args:
            target_path (str): The destination path.
        """
        target_path = join_path(target_path, basename(self.path))

        md5_builder = hashlib.md5()
        md5_builder.update(basename(target_path).encode()) 

        os.mkdir(target_path)
        for child in self.childs:
            child.move(target_path)
            md5_builder.update(child.md5_checksum.encode())
        os.rmdir(self.path)

        self.path = target_path
        self.md5_checksum = md5_builder.hexdigest()
    
    def move_diff(self, o, target_path: str) -> None:
        """
        Moves the differences between this folder and another to a target path.

        Args:
            o (FolderEntry): The other folder entry to compare against.
            target_path (str): The destination path for the moved entries.
        """
        target_path = join_path(target_path, basename(self.path))
        md5_builder = hashlib.md5()
        md5_builder.update(basename(target_path).encode()) 

        childs = []
        can_be_removed = True
        os.mkdir(target_path)
        for entry in self.childs:
            if isinstance(entry, FileEntry):
                if not (entry.md5_checksum in (e.md5_checksum for e in o.childs)):
                    entry.move(target_path)
                    md5_builder.update(entry.md5_checksum.encode())
                    childs.append(entry)
                else:
                    can_be_removed = False
            elif isinstance(entry, FolderEntry):
                oe = [e for e in o.childs if e.path == entry.path]
                # Same path, but not same hash: search recursively
                if oe and oe[0].md5_checksum != entry.md5_checksum:
                    can_be_removed = False
                    entry.move_diff(oe, target_path)
                    md5_builder.update(entry.md5_checksum.encode())
                    childs.append(entry)
                # No same path: insert completely
                elif not oe:
                    entry.move(target_path)
                    md5_builder.update(entry.md5_checksum.encode())
                    childs.append(entry)
                # Same path, same hash: nothing
                else:
                    can_be_removed = False

        if can_be_removed:
            os.rmdir(self.path)

        self.childs = childs
        self.path = target_path
        self.md5_checksum = md5_builder.hexdigest()

    def __str__(self) -> str:
        """
        Returns a string representation of the folder entry.

        Returns:
            str: String representation of the folder entry.
        """
        return f"Folder: {self.path}, md5_checksum: {self.md5_checksum}" + '\n'.join([''] + [f"{child}" for child in self.childs]) + '\n'

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, o: Entry) -> bool:
        """
        Compares this folder entry with another entry for equality.

        Args:
            o (Entry): The other entry to compare with.

        Returns:
            bool: True if they are equal, False otherwise.
        """
        return self.md5_checksum == o.md5_checksum

    def __iter__(self):
        """
        Returns an iterator over the child entries.

        Yields:
            Entry: Each child entry in the folder.
        """
        return iter(self.childs)

    def __sub__(self, o: 'FolderEntry') -> 'FolderEntry':
        """
        Computes the difference between this folder and another folder.

        Args:
            o (FolderEntry): The other folder to compare against.

        Returns:
            FolderEntry: A new FolderEntry representing the differences.
        """
        childs = []
        md5_builder = hashlib.md5()
        md5_builder.update(basename(self.path).encode()) 
        for entry in self.childs:
            if isinstance(entry, FileEntry):
                if not (entry.md5_checksum in (e.md5_checksum for e in o.childs)):
                    childs.append(entry)
            elif isinstance(entry, FolderEntry):
                oe = [e for e in o.childs if e.path == entry.path]
                # Same path, but not same hash: search recursively
                if oe and oe[0].md5_checksum != entry.md5_checksum:
                    childs.append(entry - oe)
                    md5_builder.update(childs[-1].md5_checksum.encode())
                # No same path: insert completely
                elif not oe:
                    childs.append(entry)
                    md5_builder.update(childs[-1].md5_checksum.encode())
                # Same path, same hash: nothing
        return FolderEntry(self.path, md5_checksum=md5_builder.hexdigest(), childs=childs)

    @staticmethod
    def from_dict(d: dict) -> 'FolderEntry':
        """
        Creates a FolderEntry from a dictionary representation.

        Args:
            d (dict): The dictionary representation.

        Returns:
            FolderEntry: An instance of FolderEntry.
        """
        return FolderEntry(d['path'], d['md5_checksum'], [Entry.from_dict(dd) for dd in d['childs']]) 

def walk(folder: FolderEntry):
    """
    Generator function to traverse a folder and its children.

    Args:
        folder (FolderEntry): The starting folder entry.

    Yields:
        Entry: Each entry in the folder hierarchy.
    """
    q = [folder]
    while q:
        entry = q[0]
        q = q[1:]
        yield entry

        if isinstance(entry, FolderEntry):
            for child in entry:
                q.append(child)
