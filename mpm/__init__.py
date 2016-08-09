# coding: utf-8
from collections import OrderedDict


def pformat_dict(data, separator='  '):
    column_widths = OrderedDict([(k, max([len(k)] +
                                         map(lambda v: len(str(v)), v)))
                                for k, v in data.iteritems()])

    header = separator.join([('{:>%ds}' % (column_width)).format(value)
                             for value, column_width in
                             zip(data.keys(), column_widths.values())])
    hbar = separator.join(['-' * column_width
                           for value, column_width in
                           zip(data.keys(), column_widths.values())])
    rows = [separator.join([('{:>%ds}' % (column_width)).format(value)
                            for value, column_width in
                            zip(row, column_widths.values())])
            for row in zip(*data.values())]

    return '\n'.join([header, hbar] + rows)
