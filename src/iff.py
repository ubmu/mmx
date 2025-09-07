#: src/iff.py -- functions for reading chunks from iff/riff-based formats.

import uuid

from dataclasses import dataclass, field
from typing import Dict, Tuple

from .common import Endian, LATIN, IFF_ALIGNMENT, IFF_IDENTIFIER_LENGTH, IFF_SIZE_LENGTH, W64_IDENTIFIER_LENGTH, W64_SIZE_LENGTH, W64_OVERHEAD
from .source import ReadableSource

#: Match containers to their endianness.
CONTAINER_ENDIANNESS = {
    "FORM": ("big", "IFF"), "RIFX": ("big", "RIFF"), "FFIR": ("big", "RIFF"),
    "RF64": ("little", "RF64"), "riff": ("little", "W64"), "RIFF": ("little", "RIFF"),
}

class EOSError(Exception): ...

class InvalidContainerError(Exception): ...

@dataclass
class Chunk:
    """A generic chunk."""
    identifier: str
    size: int
    payload: bytes
    start: int
    end: int

@dataclass
class ContainerMetadata:
    master: str
    endian: Endian
    container_type: str
    form_type: str
    size: int

@dataclass
class ContainerLayout:
    endian: Endian
    encoding: str = LATIN
    identifier_length: int = IFF_IDENTIFIER_LENGTH
    payload_size_length: int = IFF_SIZE_LENGTH
    alignment: int = IFF_ALIGNMENT
    overhead: int = 0
    chunk_size_storage: Dict[str, int] = field(default_factory=dict)

@dataclass
class ContainerInfo:
    metadata: ContainerMetadata
    layout: ContainerLayout

#: Helper functions for 'derive_container_info()'
def _parse_w64_header(source: ReadableSource, endian: Endian, container_type: str, start: int) -> ContainerInfo:
    source.reset()
    master_bytes = source.read(W64_IDENTIFIER_LENGTH)
    master = str(uuid.UUID(bytes_le=master_bytes)).upper() #: Uppercase for GUID consistency.
    size_bytes = source.read(W64_SIZE_LENGTH)
    size = int.from_bytes(size_bytes, byteorder=endian) - W64_OVERHEAD
    form_bytes = source.read(W64_IDENTIFIER_LENGTH)
    form_type = form_bytes.decode(LATIN)

    return ContainerInfo(ContainerMetadata(master, endian, container_type, form_type, size),  ContainerLayout(endian, "", W64_IDENTIFIER_LENGTH, W64_SIZE_LENGTH, IFF_ALIGNMENT, W64_OVERHEAD))

def _parse_rf64_header(source: ReadableSource, endian: Endian, container_type: str, start: int) -> ContainerInfo:
    return ContainerInfo()

#: Header metadata & layout parsing.
def derive_container_info(source: ReadableSource, start: int = 0) -> ContainerInfo:
    """
    Inspect an IFF/RIFF-based header and extract container metadata and layout.

    'start' can be used if you suspect that your source starts later than the 0th byte.
    """
    source.seek(start) #: Reset to the start before probing.
    master_bytes = source.read(4)  #: Probe first four bytes.
    master = master_bytes.decode(LATIN)
    endian, container_type = CONTAINER_ENDIANNESS.get(master, (None, None))
    if endian is None:
        raise InvalidContainerError(f"Master identifier {master} indicates the source is not IFF-base or malformed.")

    if master == "riff":
        return _parse_w64_header(source, endian, container_type, start)

    elif master == "RF64":
        return _parse_rf64_header(source, endian, container_type, start) #: 'ds64' chunk info will not be returned since it is only useful for reading.

    size_bytes = source.read(IFF_SIZE_LENGTH)
    size = int.from_bytes(size_bytes, byteorder=endian)
    form_bytes = source.read(IFF_IDENTIFIER_LENGTH)
    form_type = form_bytes.decode(LATIN)

    return ContainerInfo(ContainerMetadata(master, endian, container_type, form_type, size), ContainerLayout(endian))

#: Chunk reading functions.
def read_chunk(source: ReadableSource, layout: ContainerLayout) -> Chunk:
    """Read a single chunk from an IFF-based container at the current offset."""
    offset = source.tell()
    if (offset + layout.identifier_length + layout.payload_size_length) > len(source):
        raise EOSError("Not enough data to read segment identifier and size fields.")

    identifier_bytes = source.read(layout.identifier_length)
    if layout.encoding == "":
        identifier = str(uuid.UUID(bytes_le=identifier_bytes)).upper()
    else:
        identifier = identifier_bytes.decode(LATIN)

    payload_size_bytes = source.read(layout.payload_size_length)
    payload_size = int.from_bytes(payload_size_bytes, byteorder=layout.endian) #: TODO: Some formats assign special meaning to certain size values. Account for this later.
    if (offset + layout.identifier_length + layout.payload_size_length) + payload_size - layout.overhead > len(source):
       raise EOSError(f"Segment payload at offset {offset} of size {payload_size} exceeds source length {len(source)}.")

    payload = source.read(payload_size - layout.overhead)
    if layout.alignment:
        padding = (layout.alignment - (payload_size % layout.alignment)) % layout.alignment
        if padding:
            source.seek(padding, 1)

    return Chunk(identifier, payload_size, payload, offset, source.tell())

def yield_chunks(source: ReadableSource, layout: ContainerLayout):
    """Yield each chunk from an IFF/RIFF-based format."""
    eos = len(source)

    while (layout.identifier_length + layout.payload_size_length + source.tell() < eos):
        try:
            yield read_chunk(source, layout)
        except EOSError:
            raise
