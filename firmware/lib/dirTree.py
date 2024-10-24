import os
# import depending on the platform
if 'ESP32' in os.uname().sysname:
    import adafruit_hashlib as hashlib
else:
    import hashlib


# read files in chunks to be ram efficient
CHUNK_SIZE = 1024

def join_path(path: str, *paths):
    '''
    same as os.path.join
    '''
    for p in paths:
        if path == "":
            path = p
        elif path.endswith('/'):
            path += p
        else:
            path += '/' + p
    return path

def basename(path):
    '''
    same as os.path.basename 
    '''
    # Remove any trailing slashes from the path
    path = path.rstrip('/')

    # Split the path by the directory separator and return the last component
    parts = path.split('/')
    return parts[-1] if parts else ''

def calculate_md5(file_path):
    '''
    calculates the md5 hash of a file
    return: md5 hash of: basename(file_path) + file_content
    '''
    md5_hash = hashlib.md5()
    md5_hash.update(basename(file_path).encode())
    with open(file_path, "rb") as firmware_file:
        while chunk := firmware_file.read(CHUNK_SIZE):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

class Entry:
    '''
    abstract class for Folders and Files
    '''
    def __init__(self, path: str, md5_checksum) -> None:
        self.path: str = path
        self.md5_checksum: str = md5_checksum

    def to_dict(self):
        pass

    def move(self, target_path):
        pass

    @staticmethod
    def from_dict(d):
        if 'childs' in d:
            return FolderEntry.from_dict(d)
        else:
            return FileEntry.from_dict(d)

class FileEntry(Entry):
    '''
    stores path and md5 hash of file
    '''
    def __init__(self, path: str, md5_checksum=None) -> None:
        if not md5_checksum:
            md5_checksum = calculate_md5(path)
        super().__init__(path, md5_checksum)

    def to_dict(self):
        return {
            'path': self.path,
            'md5_checksum': self.md5_checksum
        }
    
    def move(self, target_path):
        target_path = join_path(target_path, basename(self.path))
        with open(self.path, 'rb') as srcf:
            with open(target_path, 'wb') as dstf:
                while (chunk := srcf.read(CHUNK_SIZE)):
                    dstf.write(chunk)
        os.remove(self.path)
        self.path = target_path

    def __str__(self) -> str:
        return f"File: {self.path}, md5_checksum: {self.md5_checksum}"

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def from_dict(d):
        return FileEntry(d['path'], d['md5_checksum'])

class FolderEntry(Entry):
    '''
    stores path, childs[Entry], md5 hash of: basename(path) + (md5_checksum of all childs)
    '''
    def __init__(self, path: str, md5_checksum=None, childs=None, ignore=None) -> None:
        self.childs: list[Entry] = childs if childs else []
        super().__init__(path, md5_checksum)

        if childs is None:
            self.childs = []
            for name in os.listdir(path):
                entry_path = join_path(path, name)
                if ignore is not None and entry_path in ignore:
                    continue
                if os.stat(entry_path)[0] & 0x4000:  # Check if the item is a directory
                    self.childs.append(FolderEntry(entry_path))
                else:
                    self.childs.append(FileEntry(entry_path))
            self.calc_md5_checksum()
        else:
            self.childs = childs
            if md5_checksum is None:
                self.calc_md5_checksum()
            else:
                self.md5_checksum = md5_checksum
        
    def to_dict(self):
        return {
            'path': self.path,
            'childs': [child.to_dict() for child in self.childs],
            'md5_checksum': self.md5_checksum
        }
    
    def calc_md5_checksum(self):
        md5_builder = hashlib.md5()
        md5_builder.update(basename(self.path).encode())
        for child in self.childs:
            md5_builder.update(child.md5_checksum.encode()) 
        self.md5_checksum = md5_builder.hexdigest()
    
    def drop(self, ignore: set[str]):
        '''
        drop all paths that are in ignore
        '''
        self.childs = [child for child in self.childs if child.path not in ignore]
        for child in self.childs:
            if isinstance(child, FolderEntry):
                child.drop(ignore=ignore)
        self.calc_md5_checksum()

    def move(self, target_path: str, move_self = True):
        target_path = join_path(target_path, basename(self.path)) if move_self else target_path
        try:
            os.mkdir(target_path)
        except OSError:
            pass
            
        for child in self.childs:
            child.move(target_path)
        os.rmdir(self.path)

        self.path = target_path
        self.calc_md5_checksum()
    
    def move_diff(self, o, target_path: str, move_self = True):
        '''
        move_self: when False only moves the content not the folder itself
        moves the difference of self - o to the target path
        '''
        target_path = join_path(target_path, basename(self.path)) if move_self else target_path
        try:
            os.mkdir(target_path)
        except OSError:
            pass

        childs = []
        can_be_removed = True
        for entry in self.childs:
            if type(entry) == FileEntry:
                if not (entry.md5_checksum in (e.md5_checksum for e in o.childs)):
                    entry.move(target_path)
                    childs.append(entry)
                else:
                    can_be_removed = False
            elif type(entry) == FolderEntry:
                oe = [e for e in o.childs if e.path == entry.path]
                # same path, but not same hash: search recursive
                if oe and oe[0].md5_checksum != entry.md5_checksum:
                    can_be_removed = False
                    entry.move_diff(oe, target_path)
                    childs.append(entry)
                # no same path: insert completely
                elif not oe:
                    entry.move(target_path)
                    childs.append(entry)
                # same path same hash: nothing
                else:
                    can_be_removed = False

        if can_be_removed:
            os.rmdir(self.path)

        self.childs = childs
        self.path = target_path
        self.calc_md5_checksum()

    def __str__(self) -> str:
        return f"Folder: {self.path}, md5_checksum: {self.md5_checksum}" + '\n'.join([''] + [f"{child}"for child in self.childs]) + '\n'

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, o: Entry):
        return self.md5_checksum == o.md5_checksum

    def __iter__(self):
        return iter(self.childs)

    def __sub__(self, o):
        childs = []
        for entry in self.childs:
            if type(entry) == FileEntry:
                if not (entry.md5_checksum in (e.md5_checksum for e in o.childs)):
                    childs.append(entry)
            elif type(entry) == FolderEntry:
                oe = [e for e in o.childs if e.path == entry.path]
                # same path, but not same hash: search recursive
                if oe and oe[0].md5_checksum != entry.md5_checksum:
                    childs.append(entry - oe)
                # no same path: insert completely
                elif not oe:
                    childs.append(entry)
                # same path same hash: nothing
        return FolderEntry(self.path, childs=childs)

    @staticmethod
    def from_dict(d):
        return FolderEntry(d['path'], d['md5_checksum'],[Entry.from_dict(dd) for dd in d['childs']]) 

def walk(folder: FolderEntry):
    q = [folder]
    while q:
        entry = q[0]
        q = q[1:]
        yield entry

        if type(entry) == FolderEntry:
            for child in entry:
                q.append(child)
