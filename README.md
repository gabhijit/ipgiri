An implementation of IPv4 Routing Lookup Table and MRT files parsing in python.

This is how it works -
  - MRT RIB file is parsed for type 13 subtypes (1,2) to obtain, peerIndexTable and RIBEntries
  - For each RIB Entry the 'last AS' in ASPath attribute is the 'destination AS' for that prefix
  - This information is used to populate a routing table that implements Radix Lookup.
  - The Routing table can then be searched for finding out destination AS for a given input IP Address (using Longest Prefix Match)
  - Information from asorg info (see below in caida datasets) is used to map an AS number to country.


 1. mrtdump.py - A wrapper class for an MRT file
 2. mrttypes.py - A class implementing individual MRT entries (supported right now are PeerIndexTable and RIBEntry for IPv4)
 3. asinformation.py - A class supporting various 'AS -> Country' mappings and similar
 4. ipv4_route_table.py - A simple routing table implementation that supports longest prefix match. Tested for about 585K entries from a BGP RIB dump.
 5. ip_to_country.py - Python scripts that puts all together to test

Most of the data is available from http://data.caida.org/datasets/
docs/ directory contains referred RFCs, files

