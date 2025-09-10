#: container.py: Utility for reading different container formats.
import uuid

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .common import Endian, MMX_BE, MMX_LE, FOURCC_ENCODING, IFF_ALIGNMENT, IFF_IDENTIFIER_LENGTH, IFF_SIZE_LENGTH, W64_ALIGNMENT, W64_OVERHEAD, W64_IDENTIFIER_LENGTH, W64_SIZE_LENGTH
from .source import ReadableSource

#:
#: Utility for reading IFF, RIFF, RIFX, RF64, W64, BWF, AIFF,
#:

@dataclass
class ContainerStructure:
    """The layout and characteristics needed to read a container."""
    format: str
    endian: Endian = MMX_LE
    identifier_length: int = IFF_IDENTIFIER_LENGTH
    payload_size_length: int = IFF_SIZE_LENGTH
    alignment: int = IFF_ALIGNMENT
    overhead: int = 0
    chunk_size_storage: Optional[Dict[str, int]] = None

#: Generic structure with big-endian identifiers.
IFF_STRUCTURE  = ContainerStructure("IFF", endian=MMX_BE)
#: Generic structure with little-endian identifiers.
RIFF_STRUCTURE = ContainerStructure("RIFF")
#: Follows RIFF structure with big-endian identifiers.
RIFX_STRUCTURE = ContainerStructure("RIFX", endian=MMX_BE)
#: Follows RIFF structure but file-size (EOF) and certain chunk-sizes are stored in `ds64`, requiring extra reading.
RF64_STRUCTURE = ContainerStructure("RF64", chunk_size_storage={})
#: Utilizes 16-byte GUIDs as identifiers and 8 byte size fields. Size field includes 16 byte identifier and 8 byte size, resulting in a 24 byte overhead to account for.
W64_STRUCTURE  = ContainerStructure("W64", identifier_length=W64_IDENTIFIER_LENGTH, payload_size_length=W64_SIZE_LENGTH, alignment=W64_ALIGNMENT, overhead=W64_OVERHEAD)

@dataclass
class Chunk:
    """A generic chunk within a container."""
    identifier: str
    size: int
    payload: bytes = field(repr=False) #: Don't print unparsed payload.
    start: int

@dataclass
class ContainerInfo:
    """Stores header information and chunks from parsed container."""
    master: str
    eos: int
    form: str
    chunks: List[Chunk]
    structure: ContainerStructure

class EOSError(Exception):
    """Raised when source does not contain enough bytes for reading."""

class GenericContainer():
    """Generic parser for generic container formats."""
    def __init__(self, source: ReadableSource, structure: ContainerStructure, start: int = 0):
        self._source = source
        self._structure = structure
        self._start = start

        self._source.reset()

        if self._structure.format == "W64":
            self.read_identifier = self.read_guid
        else:
            self.read_identifier = self.read_generic_identifier

        if self._structure.format == "RF64":
            self.read_header = self.read_rf_header
        else:
            self.read_header = self.read_generic_header

        self._chunks = []

    def align_source(self, payload_size: int):
        """Seeks forward to align the source for next read."""
        padding = (self._structure.alignment - (payload_size % self._structure.alignment)) % self._structure.alignment
        if padding:
            self._source.seek(padding, 1)

    def read_generic_identifier(self) -> str:
        """Reads an identifier from source."""
        return self._source.read(self._structure.identifier_length).decode(FOURCC_ENCODING)

    def read_guid(self) -> str:
        """Reads a GUID identifier from source."""
        guid_bytes = self._source.read(self._structure.identifier_length)
        return str(uuid.UUID(bytes_le=guid_bytes)).upper() #: Uppercase for GUID consistency.

    def read_size(self) -> int:
        """Reads a header or chunk size from source and accounts for overhead."""
        size_bytes = self._source.read(self._structure.payload_size_length)
        return int.from_bytes(size_bytes, byteorder=self._structure.endian) - self._structure.overhead #: Account for w64

    def read_payload(self, payload_size: int) -> bytes:
        """Reads the payload data of a chunk."""
        return self._source.read(payload_size)

    def read_generic_header(self) -> Tuple[str, int, str]:
        """Reads the container header."""
        master = self.read_identifier(); size = self.read_size();form = self.read_identifier()
        return master, size, form

    def read_rf_header(self) -> Tuple[str, int, str]:
        """Reads the RF64 container header and the following [ds64] chunk."""
        #: TODO: Read header and `ds64`
        return ()

    def ensure_fields_room(self, offset: int):
        """Ensure enough bytes remain to read identifier and size fields."""
        required_field_size = self._structure.identifier_length + self._structure.payload_size_length
        if offset + required_field_size > len(self._source):
            raise EOSError(f"Not enough bytes to read identifier and/or size fields at {offset}. Remaining bytes in source: {len(self._source) - offset}")

    def ensure_payload_room(self, payload_size: int, offset: int):
        """Ensures enough bytes remain to read payload."""
        if offset + payload_size > len(self._source):
            raise EOSError(f"Not enough bytes to read payload of size {payload_size} at {offset}. Remaining bytes in source: {len(self._source) - offset}")

    def read_chunk(self) -> Chunk:
        """Reads the chunk at the current offset."""
        start_offset = self._source.tell()
        self.ensure_fields_room(start_offset)
        identifier = self.read_identifier(); payload_size = self.read_size(); post_field_offset = self._source.tell()
        self.ensure_payload_room(payload_size, post_field_offset)
        payload = self.read_payload(payload_size)
        self.align_source(payload_size) #: Align for next chunk read. Otherwise, we are at or beyond EOS.
        return Chunk(identifier, payload_size, payload, start_offset)

    def read_all(self) -> ContainerInfo:
        """Reads header and all chunks from the container."""
        master, eos, form = self.read_header()
        while (self._source.tell() < eos): #: Opt for header eos rather than len(self._source)
            try:
                chunk = self.read_chunk()
            except EOSError:
                break

            self._chunks.append(chunk)

        return ContainerInfo(master, eos, form, self._chunks, self._structure)
