import hashlib
#import adafruit_hashlib as hashlib

import os

def join_path(path: str, *paths):
    for p in paths:
        if path == "":
            path = p
        elif path.endswith('/'):
            path += p
        else:
            path += '/' + p
    return path

def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as firmware_file:
        while chunk := firmware_file.read(1<<12):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

class Entry:
    def __init__(self, path: str, md5_checksum) -> None:
        self.path: str = path
        self.md5_checksum: str = md5_checksum
    def to_dict(self):
        pass
    @staticmethod
    def from_dict(d):
        if 'childs' in d:
            return FolderEntry.from_dict(d)
        else:
            return FileEntry.from_dict(d)

class FileEntry(Entry):
    def __init__(self, path: str, md5_checksum=None) -> None:
        if not md5_checksum:
            md5_checksum = calculate_md5(path)
        super().__init__(path, md5_checksum)
    def to_dict(self):
        return {
            'path': self.path,
            'md5_checksum': self.md5_checksum
        }
    def __str__(self) -> str:
        return f"File: {self.path}, md5_checksum: {self.md5_checksum}"
    def __repr__(self) -> str:
        return self.__str__()
    @staticmethod
    def from_dict(d):
        return FileEntry(d['path'], d['md5_checksum'])

class FolderEntry(Entry):
    def __init__(self, path: str, md5_checksum=None, childs=None) -> None:
        self.childs: list[Entry] = childs if childs else []
        if not md5_checksum:
            md5_builder = hashlib.md5()
            md5_builder.update(path.encode()) 
            for name in os.listdir(path):
                entry_path = join_path(path, name)
                if os.stat(entry_path)[0] & 0x4000:  # Check if the item is a directory
                    self.childs.append(FolderEntry(entry_path))
                else:
                    self.childs.append(FileEntry(entry_path))
                md5_builder.update(self.childs[-1].md5_checksum.encode())
            md5_checksum = md5_builder.hexdigest()
        super().__init__(path, md5_checksum)
    def to_dict(self):
        return {
            'path': self.path,
            'childs': [child.to_dict() for child in self.childs],
            'md5_checksum': self.md5_checksum
        }
    def __str__(self) -> str:
        return f"Folder: {self.path}, md5_checksum: {self.md5_checksum}" + '\n'.join([''] + [f"{child}"for child in self.childs]) + '\n'
    def __repr__(self) -> str:
        return self.__str__()
    def __eq__(self, o: Entry):
        return self.md5_checksum == o.md5_checksum
    def __sub__(self, o):
        childs = []
        md5_builder = hashlib.md5()
        md5_builder.update(self.path.encode()) 
        for entry in self.childs:
            if type(entry) == FileEntry:
                if not (entry.md5_checksum in (e.md5_checksum for e in o.childs)):
                    childs.append(entry)
            elif type(entry) == FolderEntry:
                oe = [e for e in o.childs if e.path == entry.path]
                # same path, but not same hash: search recursive
                if oe and oe[0].md5_checksum != entry.md5_checksum:
                    childs.append(entry - oe)
                    md5_builder.update(childs[-1].md5_checksum.encode())
                # no same path: insert completely
                elif not oe:
                    childs.append(entry)
                    md5_builder.update(childs[-1].md5_checksum.encode())
                # same path same hash: nothing
        return FolderEntry(self.path, md5_checksum=md5_builder.hexdigest(), childs=childs)
    @staticmethod
    def from_dict(d):
        return FolderEntry(d['path'], d['md5_checksum'],[Entry.from_dict(dd) for dd in d['childs']]) 
