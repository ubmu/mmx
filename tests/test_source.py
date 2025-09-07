#: tests/test_source.py -- test source normalization and operations

import os
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

from src.source import (
    source_normalize,
    ByteSource,
    BinarySource,
    FileSource,
    MmapSource,
)

TEST_DATA = b"RIFFWAVE"

@pytest.fixture(params=[
    ("bytes", TEST_DATA),
    ("binary", BytesIO(TEST_DATA)),
    ("binary2", TEST_DATA),
    ("file", TEST_DATA),
    ("mmap", TEST_DATA),
])
def source(request):
    stype, val = request.param
    if stype == "bytes":
        src = source_normalize(val)
        expected_type = ByteSource
    elif stype == "binary":
        src = source_normalize(val)
        expected_type = BinarySource

    elif stype == "binary2":
        fd, temp_path = tempfile.mkstemp()
        os.write(fd, val)
        os.close(fd)
        bstream = Path(temp_path).open("rb")
        src = source_normalize(bstream)
        expected_type = BinarySource
    elif stype == "file":
        fd, temp_path = tempfile.mkstemp()
        os.write(fd, val)
        os.close(fd)
        src = source_normalize(temp_path)
        expected_type = FileSource
    elif stype == "mmap":
        fd, temp_path = tempfile.mkstemp()
        os.write(fd, val)
        os.close(fd)
        src = source_normalize(temp_path, use_mmap=True)
        expected_type = MmapSource
    else:
        raise ValueError("Unknown type")

    assert isinstance(src, expected_type)
    return src

def test_source_has_operations(source):
    assert hasattr(source, "read")
    assert hasattr(source, "seek")
    assert hasattr(source, "tell")
    assert hasattr(source, "reset")
    assert hasattr(source, "read_at_offset")
    assert hasattr(source, "__len__")

def test__len__operation(source):
    assert len(source) == len(TEST_DATA)

def test_tell_operation(source):
    assert source.tell() == 0
    source.seek(4)
    assert source.tell() == 4

def test_reset_operation(source):
    assert source.tell() == 0
    source.seek(4)
    source.reset()
    assert source.tell() == 0

def test_seek_operation(source):
    assert source.tell() == 0
    source.seek(4)              #: from start
    assert source.tell() == 4
    source.seek()               #: defaults to zero
    assert source.tell() == 0
    source.seek(4, 0)           #: absolute seek
    assert source.tell() == 4
    source.seek(4, 1)           #: relative seek
    assert source.tell() == 8
    source.seek(-2, 2)          #: seek from end
    assert source.tell() == 6

def test_read_operation(source):
    assert source.read(4) == TEST_DATA[:4]
    assert source.tell() == 4
    source.seek(4)
    assert source.read(4) == TEST_DATA[4:]
    source.seek()
    assert source.read() == TEST_DATA
    assert source.read(0) == b""
    source.reset()
    assert source.read(999) == TEST_DATA

def test_read_at_offset_operation(source):
    #: Perhaps it's better to call this seek_read
    #: read_at_offset might imply that absolute seek is used
    assert source.read_at_offset(0, 4) == TEST_DATA[:4]
    assert source.read_at_offset(4, 4) == TEST_DATA[4:]
