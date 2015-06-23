"""
Implementation of various MRT Types supported. Right now following types
are supportd.
"""

from collections import namedtuple
import struct
from socket import inet_ntoa

class MRTType(object):
    pass

MRTPeerIndexHeader = namedtuple('MRTPeerIndexHeader',
                            ['collector_ip', 'view_name_len', 'count'])

MRTPeerIndexEntry = namedtuple('MRTPeerIndexEntry',
                                ['type', 'bgp_id', 'ip_addr', 'as_id'])

class PeerIndexTable(MRTType):

    _PEER_IDX_TBL_HDRSTR = '>4sHH'
    _PEER_IDX_TBL_ENTRYSTR = 'B>III'

    def __init__(self, m, e):
        self._length = m.length
        self._entries = []
        self._collector_ip = None
        self._hdr_sz = struct.calcsize(self._PEER_IDX_TBL_HDRSTR)
        ##xx = e[0:self._hdr_sz])
        self._hdr = MRTPeerIndexHeader(*struct.unpack(self._PEER_IDX_TBL_HDRSTR,
                                                        e[0:self._hdr_sz]))
        print inet_ntoa(self._hdr.collector_ip)


def read_mrt_entry(m, e):
    if m.type == 13 and m.subtype == 1:
        print m
        peeridxtbl = PeerIndexTable(m, e)
        return peeridxtbl
    else:
        return None
