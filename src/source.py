#: source.py -- unified source input

import mmap
import os

from io import BufferedReader, BytesIO
from pathlib import Path
from typing import Protocol, Union

#: TODO: EOS checks -- if offset + size > len(source)
#: TODO: A secondary variant that still reads as much as possible?

class Source(Protocol):
    def read(self, size: int = -1) -> bytes: ...

    def seek(self, offset: int = 0, whence: int = 0) -> None: ...

    def read_at_offset(self, offset: int, size: int) -> bytes: ...

    def tell(self) -> int: ...

    def reset(self) -> None: ...

    def __len__(self) -> int: ...

class BinarySource(Source):
    def __init__(self, source: Union[BufferedReader, BytesIO]):
        self._source = source
        if isinstance(self._source, BytesIO):
            self._length = len(self._source.getbuffer())
        else:
            self._source.seek(0, os.SEEK_END)
            self._length = self._source.tell()
            self._source.seek(0)

    def read(self, size: int = -1) -> bytes:
        return self._source.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._source.seek(offset, whence)

    def read_at_offset(self, offset: int, size: int) -> bytes:
        self._source.seek(offset)
        return self._source.read(size)

    def tell(self) -> int:
        return self._source.tell()

    def reset(self) -> None:
        self._source.seek(0)

    def __len__(self) -> int:
        return self._length

class ByteSource(Source):
    def __init__(self, data: bytes):
        self._source = BytesIO(data)
        self._length = len(data)

    def read(self, size: int = -1) -> bytes:
        return self._source.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._source.seek(offset, whence)

    def read_at_offset(self, offset: int, size: int) -> bytes:
        self._source.seek(offset)
        return self._source.read(size)

    def tell(self) -> int:
        return self._source.tell()

    def reset(self) -> None:
        self._source.seek(0)

    def __len__(self) -> int:
        return self._length

class FileSource(Source):
    def __init__(self, fp: Union[Path, str]):
        self._source = open(fp, "rb")
        self._length = os.fstat(self._source.fileno()).st_size

    def read(self, size: int = -1) -> bytes:
        return self._source.read(size)

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        self._source.seek(offset, whence)

    def read_at_offset(self, offset: int, size: int) -> bytes:
        self._source.seek(offset)
        return self._source.read(size)

    def tell(self) -> int:
        return self._source.tell()

    def reset(self) -> None:
        self._source.seek(0)

    def close(self) -> None:
        self._source.close()

    def __len__(self) -> int:
        return self._length

class MmapSource(Source):
    def __init__(self, fp: Union[str, Path]):
        self._file = open(fp, "rb")
        self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._map) - self._pos
        start = self._pos
        self._pos += size
        return self._map[start:self._pos]

    def seek(self, offset: int = 0, whence: int = 0) -> None:
        if whence == 0:  # absolute
            self._pos = offset
        elif whence == 1:  # relative
            self._pos += offset
        elif whence == 2:  # from end
            self._pos = len(self._map) + offset

    def read_at_offset(self, offset: int, size: int) -> bytes:
        return self._map[offset:offset + size]

    def tell(self) -> int:
        return self._pos

    def reset(self) -> None:
        self._pos = 0

    def __len__(self) -> int:
        return len(self._map)


#: Source types
ReadableSource = Union[BinarySource, ByteSource, FileSource, MmapSource]
RawSource = Union[bytes, BytesIO, BufferedReader, Path, str, ReadableSource]

def source_normalize(raw_source: RawSource, use_mmap: bool = False) -> ReadableSource:
    if isinstance(raw_source, ReadableSource):
        return raw_source

    elif use_mmap and isinstance(raw_source, (str, Path)):
        return MmapSource(raw_source)

    elif isinstance(raw_source, (BufferedReader, BytesIO)):
        return BinarySource(raw_source)

    elif isinstance(raw_source, bytes):
        return ByteSource(raw_source)

    elif isinstance(raw_source, (str, Path)) and Path(raw_source).is_file():
        return FileSource(raw_source)

    else:
        raise ValueError(f"Invalid input type: {type(raw_source)}")
