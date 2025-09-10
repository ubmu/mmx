#: src/common.py

from typing import Literal

#: TODO: Sort this file properly.

#: General types
Endian = Literal["little", "big"]

#: General constants
MMX_BE = "big"
MMX_LE = "little"

FOURCC_ENCODING = "ascii"

#: Encodings
LATIN = "latin-1"

#: IFF-based constants
IFF_ALIGNMENT = 2
IFF_IDENTIFIER_LENGTH = 4
IFF_SIZE_LENGTH = 4

W64_ALIGNMENT = 8
W64_OVERHEAD = 24
W64_IDENTIFIER_LENGTH = 16
W64_SIZE_LENGTH = 8
