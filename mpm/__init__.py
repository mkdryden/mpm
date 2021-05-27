# coding: utf-8
from collections import OrderedDict


def pformat_dict(data, separator='  '):
    column_widths = OrderedDict([(k, max([len(k)] +
                                         [len(str(v)) for v in v]))
                                for k, v in data.items()])

    header = separator.join([('{:>%ds}' % (column_width)).format(value)
                             for value, column_width in
                             zip(list(data.keys()), list(column_widths.values()))])
    hbar = separator.join(['-' * column_width
                           for value, column_width in
                           zip(list(data.keys()), list(column_widths.values()))])
    rows = [separator.join([('{:>%ds}' % (column_width)).format(value)
                            for value, column_width in
                            zip(row, list(column_widths.values()))])
            for row in zip(*list(data.values()))]

    return '\n'.join([header, hbar] + rows)
