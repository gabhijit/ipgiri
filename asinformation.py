#
# Refer to LICENSE file and README file for licensing information.
#
"""
A utility that parses AS information file and populates following information
 - AS Id
 - Country where the AS is registered
 - Org to which AS belongs

Also keeps other data handy
  - A country wide list of All ASes registered in the country
  So one can ask questions like 'which country has maximum ASes etc
"""

import os
from collections import namedtuple

asinfo = namedtuple('asinfo', ['id', 'name', 'org', 'country'])

class ASInformation:
    def __init__(self, filename):
        self._ases = {} # dictionary of AS informations key:asid, val:info
        self._countries = {} #dictionary of Countries: key:Countrycode val:asid
        self._file_handler = self._get_file_handler(filename)
        self._orgs = {} # Org to country mapping

    def _do_get_file_handle(self, cls, filename):
        return cls(filename, 'rb')

    def _get_file_handler(self, filename):
        if not os.path.exists(filename):
            raise IOError

        if os.path.splitext(filename)[1].lower() == '.gz':
            return self._do_get_file_handle(GzipFile, filename)
        elif os.path.splitext(filename)[1].lower() == '.bz2':
            return self._do_get_file_handle(BZ2File, filename)
        else:
            return self._do_get_file_handle(open, filename)

    def parse(self):
        f = self._file_handler
        if not f or f.closed:
            raise IOError

        _format1_found = False
        _format2_found = False
        for line in f:
            if line.startswith("# format:org_id"):
                _format1_found = True
                _format2_found = False
                continue
            if line.startswith("# format:aut"):
                _format2_found = True
                _format1_found = False
                continue
            if _format1_found:
                self._do_parse_format1(line)
            elif _format2_found:
                self._do_parse_format2(line)

    def _do_parse_format1(self, line):
        """parse format 1 lines and update orgs dict"""
        toks = line.strip().split('|')
        if len(toks) != 5:
            print (f"invalid line: {line}")
            return

        org, _, _, country, _ = toks

        self._orgs[org] = country
        return

    def _do_parse_format2(self, line):
        """parse format 2 lines and update ases and countries dicts"""
        toks = line.strip().split('|')
        if len(toks) != 5:
            print (f"invalid line: {line}")
            return

        asid, _,asname, org, _ = toks
        country = self._orgs[org]
        info = asinfo(*[int(asid), asname, org, country])
        self._ases[int(asid)] = info
        if country not in self._countries.keys():
            self._countries[country] = [int(asid)]
        else:
            self._countries[country].append(int(asid))

    def close(self):
        try:
            if self._file_handler:
                self._file_handler.close()
        except:
            pass

    def get_countries(self):
        return self._countries

    def get_ases_for_country(self, country):
        return self._countries.get(country)

    def country_from_asid(self, asid):
        return self._ases.get(asid).country if self._ases.has_key(asid) \
                else None

    def get_as_info(self, asid):
        return self._ases.get(asid) if self._ases.has_key(asid) else None

if __name__ == '__main__':

    from collections import OrderedDict
    a = ASInformation('20150701.as-org2info.txt')
    a.parse()

    cdict = a.get_countries()
    countries_by_num_ases = OrderedDict(sorted(cdict.items(),
                                                key=lambda x: len(x[1]), reverse=True))
    for country in countries_by_num_ases:
        print(country, (a.get_ases_for_country(country)))

    print(a.country_from_asid(37614))
    for as_ in a.get_ases_for_country('IN'):
        pass #print a.get_as_info(as_)
