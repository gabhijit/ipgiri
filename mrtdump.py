"""
A python implementation of MRT file reader.

Format of the MRT file is described in rfc6396
(http://tools.ietf.org/html/rfc6396)

Supports TABLE_DUMP (Type 12) and TABLE_DUMP_V2 (Type 13)
"""

import struct
from collections import namedtuple
import os

from gzip import GzipFile
from bz2 import BZ2File

from mrttypes import read_mrt_entry

MRTHeader = namedtuple('MRTHeader', ['ts', 'type', 'subtype', 'length'])
MRT_HEADER_LENGTH = 12
_MRT_HDR_PACKSTR = '>IHHI'
_KNOWN_MRT_TYPES = (11, 12, 13, 16, 17, 32, 33, 48, 49)


class MRTFileNotFoundErr(Exception):
    pass

class InvalidMRTFileErr(Exception):
    pass

class MRTDumper(object):
    def __init__(self, mrt_file):
        self._file_reader = self._get_file_handle(mrt_file)

    def _get_file_handle(self, mrt_file):
        """ Tries to determine the file type of the mrt_file, if it's a valid
        file and then opens the file for reading using appropriate reader.
            1. For normal MRT file - just returns the file handle
            2. For bz2 MRT file - returns an open bz2.BZ2File handle
            3. For gz MRT file - returns an open gzip.GZipFile handle
        Also tries to do a basic error checking, ensure that the first 12
        bytes are indeed MRT header.
        """
        if not os.path.exists(mrt_file):
            raise MRTFileNotFoundErr

        if os.path.splitext(mrt_file)[1].lower() == '.gz':
            return self._do_get_file_handle(GzipFile, mrt_file)
        elif os.path.splitext(mrt_file)[1].lower() == '.bz2':
            return self._do_get_file_handle(BZ2File, mrt_file)
        else:
            return self._do_get_file_handle(open, mrt_file)

    def __iter__(self):
        """ Iterator for the class"""
        print "__iter__ called"
        return self

    def next(self):

        if not self._file_reader:
            raise StopIteration
        f = self._file_reader
        try:
            x = f.read(MRT_HEADER_LENGTH)
            m = MRTHeader(*struct.unpack(_MRT_HDR_PACKSTR, x))
        except:
            raise StopIteration

        e = f.read(m.length)
        entry = read_mrt_entry(m, e)
        return entry

    def _do_get_file_handle(self, cls, mrt_file):
        """Lower Level file open and error checking"""
        f = cls(mrt_file, 'rb')
        x = f.read(MRT_HEADER_LENGTH)
        m = MRTHeader(*struct.unpack(_MRT_HDR_PACKSTR, x))
        if m.type not in _KNOWN_MRT_TYPES:
            f.close()
            raise InvalidMRTFileErr, mrt_file
        f.seek(0)
        return f

    def close(self):
        """Basically closes the file reader. Ignores any errors"""
        try:
            if self._file_reader and not self._file_reader.closed:
                self._file_reader.close()
        except:
            pass

if __name__ == '__main__':
    #dumper = MRTDumper('updates.20150603.1000')
    dumper = MRTDumper('rib.20150617.1600.bz2')

    print dumper
    for dump in dumper:
        if dump is not None:
            print dump
    dumper.close()
