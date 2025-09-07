#: src/common.py

from typing import Literal

#: General types
Endian = Literal["little", "big"]

#: Encodings
LATIN = "latin-1"

#: IFF-based constants
IFF_ALIGNMENT = 2               #: might be 4?
IFF_IDENTIFIER_LENGTH = 4
IFF_SIZE_LENGTH = 4

#W64_ALIGNMENT = 8
W64_OVERHEAD = 24               #: Accounts for 16 byte (guid) identifier & 8 byte size field
W64_IDENTIFIER_LENGTH = 16
W64_SIZE_LENGTH = 8
