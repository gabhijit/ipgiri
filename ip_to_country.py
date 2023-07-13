#
# Refer to LICENSE file and README file for licensing information.
#
import gc

from mrtdump import MRTDumper
from asinformation import ASInformation
from ipv4_routing_table import RouteTable
from mrttypes import PeerIndexTable, RIBEntry

a = ASInformation('20150701.as-org2info.txt')
r = RouteTable()
dumper = MRTDumper('rib.20230626.0400.bz2')

count = 0
for dump in dumper:
    if type(dump) == PeerIndexTable:
        dumper._peeridx_tbl = dump
    if type(dump) == RIBEntry:
        prefix, length, asid =  dump.get_prefix_length_dest_as()
        r.add(prefix, length, asid)
        #r.print_table()
        #dumper._rib_entries.append(dump)
    count += 1
    if count % 1000 == 0:
        print(count, prefix, length, asid, r.rtentries_alloced)
        gc.collect()

r.save_table('585kentries.table')
print(r.lookup('123.252.240.140'))
