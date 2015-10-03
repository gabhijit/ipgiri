#
# Refer to LICENSE file and README file for licensing information.
#
"""
An implementation of IPv4 Routing table that does longest prefix match.

This implementation is based on ideas from the following sources (though it is
not an actual implementation of any of these ideas).
Click Modular Router - RadixIPLookup Element
(http://www.read.cs.ucla.edu/click/elements/radixiplookup)


Broad scheme is as follows -

There are 4 levels of buckets.

First level is a list of 64K entries for first 16 bits
Second level is a list of 256 entries for each of the 'third' octet
Third level is a list of 16 entries for the higher nibble of the last octet
Final level is a list of 16 entries for the lower nibble of the last octet.

Each Entry looks like following
 - final (there's a routing prefix corresponding to this entry)
 - children (empty or a table of entries)
 - prefix len (Length of the prefix that filled this entry - see below. why
   this may be needed).

Lookup
 - First we match 'upper 16 bits with an entry'. If that has got 'final' bit
   set, we 'remember' match.
 - If it's got 'children' we index into the child corresponding to third byte
   If it's got a 'final' flag set we 'update' the match. If no children
   the current match is the best match. If has children continue looking into
   next level remembering match

Update
 Update is a bit tricky. Let's say we've a 12.0.0.0/8 prefix. Now we've to
mark entries in the first list from 12.0 - 12.255. with this. What if we now
encounter a 12.1.0.0/16 route? Update the 12.1 entry with the latest info
leaving others untouched so the table would look like

12.0 -> A (final)
12.1 -> B (final)
12.3 -> A (final)
...
...
12.255 -> A (final)

We'd overwrite 12.1 -> A with B, because when we are updating 12.1, we'c check
the current prefix length (8 for 12.0.0.0/8) with new prefix length
(16 for 12.1.0.0/16) and update the higher prefix length.

What if the order of prefixes learnt was reversed? ie. We learn about
12.1.0.0/16 first and later about 12.0.0.0/8

12.1 can be populated as

12.1 -> B (final)

Now when we want to populate 12.0 (a lesser prefix), when we encounter
12.1 -> B, we'd check for prefix length. Prefix length of the entry is longer
we'd not overwrite the entry
"""

from socket import inet_aton
import struct
import numpy as np

RouteEntryNP = np.dtype([('final', 'u1'), ('prefix_len', 'u1'),
                            ('output_idx', '>u4'), ('children', 'O')])

class RouteEntry:
    def __init__(self, pre_len, final, output_idx):
        """Prefix Length of this Entry. Whether this entry is final or not and
        output index for this entry (only valid if this entry is final)."""
        self.prefix_len = pre_len
        self.final = final
        self.output_idx = output_idx
        self.children = None
        #self.table_idx = -1
        #self.table_level = -1

    #def add_childrens(self, entry_table):
    #    """ Adds children to a given entry."""
    #    self.children = entry_table

    def __repr__(self):

        if self.children is None and self.output_idx == -1:
            return ''

        s = '%stable_idx:%d,final:%r,output_idx:%s\n' % \
                ("\t"*self.table_level, self.table_idx,
                        self.final, self.output_idx)
        s = 'final:%r, output_idx:%s' % (self.final, self.output_idx)
        if self.children is None:
            return s
        for child in self.children:
            s += repr(child)
        return s

# The class below is deprecated, but still is here for reference which depicts
# basic structre. Numpy 'dtype' RouteEntryNP does exactly the same
class RouteTable:
    def __init__(self, filename=None):
        self.table_sizes = [ 1 << 16, 1 << 8, 1 << 4, 1 << 4]
        self.levels = [16, 24, 28, 32]
        if filename is None:
            self.level0_table = np.zeros(self.table_sizes[0], RouteEntryNP)
            self.rtentries_alloced = 0
            self.rtentries_alloced += self.table_sizes[0]
        else:
            self._load_table(filename)
            # FIXME : Get this right
            self.rtentries_alloced = 0

        #for i in range(self.table_sizes[0]):
            #self.level0_table.append(RouteEntry(0,0,0))

    def lookup(self, ip_address):
        """ Looks up an IP address and returns an output Index"""
        ip_arr = [ord(x) for x in inet_aton(ip_address)]
        match = None
        tbl = self.level0_table
        for i, level in enumerate(self.levels):
            idx, _ = self._idx_from_tuple(ip_arr, 32, i)
            entry = tbl[idx]
            if entry['final'] == 1:
                match = entry['output_idx']
            if entry['children'] != 0:
                tbl = entry['children']
            else:
                break
        return match

    def add(self, prefix, length, dest_idx):
        """ Adds a prefix to routing table."""

        prefix_arr = [ord(x) for x in inet_aton(prefix)]
        level = 0
        tbl = self.level0_table
        while level < len(self.levels):
            idx_base, span = self._idx_from_tuple(prefix_arr,
                                                    length, level)

            lvl_prelen = self.levels[level]
            tblsz = self.table_sizes[level]
            nxtsz = self.table_sizes[level+1] if level < 3 else 0
            i = 0
            while i < span:
                assert tbl is not None
                entry = tbl[idx_base+i]
                #entry.table_idx = idx_base + i
                #entry.table_level = level
                if length <= lvl_prelen:
                    #entry.entry = struct.pack('>BBI', True, length, dest_idx)
                    entry['final'] = 1
                    entry['prefix_len'] = length
                    entry['output_idx'] = dest_idx
                else:
                    if entry['children'] != 0:
                        break
                    tbl = np.zeros(nxtsz, RouteEntryNP)
                    self.rtentries_alloced += nxtsz
                    entry['children'] = tbl
                i += 1
            if lvl_prelen >= length: # Break from outer loop
                break
            level += 1
            tbl = entry['children']

    def delete(self, prefix, length):
        "Deletes an entry in the routing table."
        prefix_arr = [ord(x) for x in inet_aton(prefix)]
        level = 0
        tbl = self.level0_table
        while level < len(self.levels):
            idx_base, span = self._idx_from_tuple(prefix_arr,
                                                    length, level)

            lvl_prelen = self.levels[level]
            tblsz = self.table_sizes[level]
            nxtsz = self.table_sizes[level+1] if level < 3 else 0
            i = 0
            while i < span:
                entry = tbl[idx_base+i]
                if length <= lvl_prelen:
                    #entry.entry = struct.pack('>BBI', False, 0, 0)
                    entry['final'] = 0
                    entry['prefix_len'] = 0
                    entry['output_idx'] = 0
                else:
                    tbl = entry['children']
                # FIXME : Add code to delete the entry.children
                # if occupation of table is zero
                i += 1
            level += 1

    def _idx_from_tuple(self, prefix_arr, prelen, level):
        _levels = [16, 24, 28, 32]
        _level_edges = [(0,2),(2,3), (3,4), (3,4)]
        begin, end = _level_edges[level]
        leveloff = _levels[level]

        if prelen > leveloff:
            span = 1
        else:
            span = 1 << (leveloff - prelen)
        prefix_arr = prefix_arr[begin:end][::-1]
        idx = reduce(lambda x,y: x+ ((1 << (8*y[0])) * y[1]),
                        enumerate(prefix_arr), 0)
        if level == 2:
            idx = idx >> 4
        if level == 3:
            idx = idx & 0x0F
        return idx, span

    def print_entry(self, entry, tblidx, level):
        if entry['output_idx'] != 0 or entry['children'] != 0:
            print "%sidx:%d,final:%d,output:%d" % \
                    ('\t'*level, tblidx, entry['final'], entry['output_idx'])
            if entry['children'] != 0:
                for i, entry2 in enumerate(entry['children']):
                    self.print_entry(entry2, i, level+1)

    def print_table(self):
        for i, entry in enumerate(self.level0_table):
            self.print_entry(entry, i, 0)

    def save_table(self, filename):
        allocced = np.zeros(1, '>u4')
        allocced[0] = self.rtentries_alloced
        with open(filename, 'wb+') as f:
            np.savez(f, allocced=allocced, tbl0=self.level0_table)

    def _load_table(self, filename):
        x = np.load(filename)
        self.level0_table = x['tbl0']
        self.rtentries_alloced = x['allocced'][0]

if __name__ == '__main__':
    r = RouteTable()

    #r.add('12.0.0.0', 8, 2000)
    #r.add('12.0.1.0', 24, 2001)
    #r.add('12.0.2.16', 28, 2004)
    #r.add('12.0.2.0', 24, 2005)
    #r.add('12.1.128.0', 23, 2003)
    #r.add('12.0.0.0', 16, 2002)

    #r.add('212.85.129.0', 24, '134.222.85.45')
    #r.add('210.51.225.0', 24, '193.251.245.6')
    #r.add('209.136.89.0', 24, '12.0.1.63')
    #r.add('209.34.243.0', 24, '12.0.1.63')

    r.add('202.209.199.0', 24, 230)
    r.add('202.209.199.0', 28, 231)
    r.add('202.209.199.8', 29, 232)
    r.add('202.209.199.48',29, 233)
    r.print_table()
    print r.lookup('202.209.199.49')
    print r.lookup('202.209.199.8')
    print r.lookup('202.209.199.9')
    print r.lookup('202.209.199.7')

    r.delete('202.209.199.0', 28)
    r.delete('202.209.199.8', 29)
    r.print_table()

    r.add('202.209.199.8', 29, 232)
    r.add('202.209.199.0', 28, 231)
    r.print_table()

    r.save_table('rttable.now')

    print "****************************"
    r2 = RouteTable('rttable.now')
    r2.print_table()
