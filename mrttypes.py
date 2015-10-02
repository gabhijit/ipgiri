"""
Implementation of various MRT Types supported. Right now following types
are supportd.
"""

from collections import namedtuple
import struct
from socket import inet_ntoa
import gc

#BGP Path ATypes
BGP_ATYPE_ORIGIN = 1
BGP_ATYPE_ASPATH = 2
BGP_ATYPE_NEXTHOP = 3

BGP_ORIGIN_TYPES = ['IGP', 'EGP', 'UNDEFINED']

def bytes_to_hexstr(bytestr):
    return ' '.join(['%02X' % ord(x) for x in bytestr])

def parse_bgp_attr(atype, aval_buf):
    """Given a type and value buffer, parses a BGP attribute and returns the value
    parsed"""
    if atype == BGP_ATYPE_ORIGIN:
        attr = 'ORIGIN'
        if len(aval_buf) != 1:
            return None, None, -1
        aval = struct.unpack('B', aval_buf)[0]
        aval = BGP_ORIGIN_TYPES[aval]
        return attr, aval, 1
    elif atype == BGP_ATYPE_ASPATH:
        attr = 'ASPATH'
        segtype, seglen = struct.unpack('BB', aval_buf[:2])
        ases = []
        segproc = 2
        for i in range(seglen):
            as_,  = struct.unpack('>I', aval_buf[segproc:segproc+4])
            segproc += 4
            ases.append(as_)
        return attr, ases, len(aval_buf)
    elif atype == BGP_ATYPE_NEXTHOP:
        attr = 'NEXTHOP'
        aval = inet_ntoa(aval_buf)
        return attr, aval, 4
    else:
        return None, None, len(aval_buf)


def parse_bgp_attrs(attr_buf):
    """Parses BGP attributes in the buffers, returns a dictionary of attributes
        key: Attribute, val:Attribute_value of respective type
    """
    attrlen = len(attr_buf)
    if not attrlen:
        return {}

    proc = 0
    attr_dict = {}
    while proc < attrlen:
        f, t =  struct.unpack('BB', attr_buf[proc:proc+2])
        optional = (f & 0x80) == 0
        transitive = not optional or (f & 0x40) == 0
        partial = f & 0x20
        extlen = f & 0x10
        proc += 2

        if extlen:
            alen = struct.unpack('>H', attr_buf[proc:proc+2])
            proc += 2
        else:
            alen = struct.unpack('B', attr_buf[proc:proc+1])
            proc += 1

        alen = alen[0]
        aval = attr_buf[proc:proc+alen]
        attr, attr_val, p = parse_bgp_attr(t, aval)
        if p <  0:
            break
        if attr is not None:
            attr_dict[attr] = attr_val
        proc += p
    return attr_dict

class MRTType(object):
    pass

MRTPeerIndexHeader = namedtuple('MRTPeerIndexHeader',
                            ['collector_ip', 'view_name_len'])

MRTPeerIndexEntry = namedtuple('MRTPeerIndexEntry',
                                ['entry_type', 'peer_bgp_id', 'peer_ip', 'peer_asid'])

class PeerIndexTable(MRTType):

    _PEER_IDX_TBL_HDRSTR = '>4sH'
    _PEER_IDX_TBL_ENTRYSTRS = ['>BI4sH', '>BI16sH', '>BI4sI', '>BI16sI']

    def __init__(self, m, e, o):
        self._length = m.length
        self._entries = []
        self._collector_ip = None
        self._view_name = ''
        self._nentries = 0
        self.owner = o
        self._hdr_sz = struct.calcsize(self._PEER_IDX_TBL_HDRSTR)
        ##xx = e[0:self._hdr_sz])
        self._hdr = MRTPeerIndexHeader(*struct.unpack(self._PEER_IDX_TBL_HDRSTR,
                                                        e[0:self._hdr_sz]))
        o = self._hdr_sz

        #print inet_ntoa(self._hdr.collector_ip)
        if self._hdr.view_name_len:
            self._view_name = e[o+1:o+self._hdr.view_name_len]

        o += self._hdr.view_name_len
        self._nentries = struct.unpack('>H', e[o:o+2])[0]
        o += 2

        # o is now @ the beginning of first entry
        for i in range(self._nentries):
            ebyte = struct.unpack('B', e[o])[0]
            estr = self._PEER_IDX_TBL_ENTRYSTRS[ebyte]
            estrlen = struct.calcsize(estr)
            entry = MRTPeerIndexEntry(*struct.unpack(estr, e[o:o+estrlen]))
            o += estrlen
            self._entries.append(entry)
            self._entry_print(entry)

    def _entry_print(self, entry):
        print 'TYPE:%d,Peer_BGP_ID:%d,Peer_IP:%s,Peer_AS:AS%d' % \
                (entry.entry_type, entry.peer_bgp_id,
                    inet_ntoa(entry.peer_ip), entry.peer_asid)

    def get_peer_at_idx(self, idx):
        """Returns the peer @ given idx."""
        return self._entries[idx]

class PeerIndexEntry(MRTType):
    pass

### RIB Entries
RIB_ENTRY_IPV4_UCAST = 0
RIB_ENTRY_IPV4_MCAST = 1
RIB_ENTRY_IPV6_UCAST = 2
RIB_ENTRY_IPV6_MCAST = 3

class RIBEntry(MRTType):

    _SEQNO_PREFIX_STR = '>IB'
    _RIBENTRY_PREFIX_STR = '>HIH'
    _ENTRY_LENGTHS = [4, 4, 16, 16]
    _ENTRY_TYPES = [ RIB_ENTRY_IPV4_UCAST, RIB_ENTRY_IPV4_MCAST,
                    RIB_ENTRY_IPV6_UCAST, RIB_ENTRY_IPV6_MCAST]

    def __init__(self, m, e, o, etype):
        #print bytes_to_hexxtr(e)
        s, p = struct.unpack(self._SEQNO_PREFIX_STR, e[0:5])
        self._seqno = s
        self._prefixlen = p
        self._prefix = None
        self._entry_type = etype
        self._entries = []
        self.owner = o
        pb = 0
        if p % 8:
            pb = 1
        pb += (p/8)
        if pb:
            pestr = self._SEQNO_PREFIX_STR + '%dsH' % pb
            pestrl = struct.calcsize(pestr)
            #print bytes_to_hexstr(e[0:pestrl])
            s, pl, pr, en = struct.unpack(pestr, e[0:pestrl])
            self._prefix = pr + ('\x00' * (self._ENTRY_LENGTHS[etype] - pb))
        else:
            pestr = self._SEQNO_PREFIX_STR + 'H'
            pestrl = struct.calcsize(pestr)
            #print bytes_to_hexstr(e[0:pestrl])
            self._prefix = '\x00' * self._ENTRY_LENGTHS[etype]
            s, pl, en = struct.unpack(pestr, e[0:pestrl])
        self._entry_count = en
        self._prefixstr = '.'.join([str(ord(x)) for x in self._prefix])

        used = pestrl
        for i in range(self._entry_count):
            # disassemble each entry
            ehdr_len = struct.calcsize(self._RIBENTRY_PREFIX_STR)
            peeridx, ts, attrlen = struct.unpack(self._RIBENTRY_PREFIX_STR,
                                                    e[used:used+ehdr_len])
            # parse remaining attributes
            begin = used+ehdr_len
            end = begin + attrlen
            attrs = parse_bgp_attrs(e[begin:end])
            used += ehdr_len
            used += attrlen
            peer = self.owner.get_peer_by_idx(peeridx)
            attrs['PEER_IP'] = inet_ntoa(peer.peer_ip)
            attrs['PEER_AS'] = peer.peer_asid
            attrs['PREFIX'] = '%s/%d' % \
                                (inet_ntoa(self._prefix), self._prefixlen)
            self._entries.append(attrs)

    def get_prefix_length_dest_as(self):
        dest_aspath = self._entries[0]['ASPATH']
        dest_as = dest_aspath[-1]
        return self._prefixstr, self._prefixlen, dest_as

    def __repr__(self):
        return '\n'.join([str(x) for x in self._entries])


def read_mrt_entry(m, e, o):
    """ Given an MRT Entry header and buffer, returns an Object
    of respective MRTType. If the type and/or subtype is not supported
    returns None"""

    # FIXME : Remove Hardcoding
    if m.type == 13 and m.subtype == 1:
        peeridxtbl = PeerIndexTable(m, e, o)
        return peeridxtbl
    if m.type == 13 and m.subtype == 2:
        rib_entry = RIBEntry(m, e, o, RIB_ENTRY_IPV4_UCAST)
        #print rib_entry.get_prefix_length_dest_as()
        # Not sure why explicit gc.collect() below is required
        gc.collect()
        return rib_entry
