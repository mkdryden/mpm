from argparse import ArgumentParser
from pip_helpers import CRE_PACKAGE
import os
import sys


def home_dir():
    if os.name == 'nt':
        from win32com.shell import shell, shellcon

        return shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
    else:
        return os.path.expanduser('~')


def plugin_request(plugin_str):
    match = CRE_PACKAGE.match(plugin_str)
    if not match:
        raise ValueError('Invalid plugin descriptor. Must be like "foo", '
                         '"foo==1.0", "foo>=1.0", etc.')
    return match.groupdict()


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Microdrop plugin manager')

    plugins_parser = ArgumentParser(add_help=False)
    plugins_parser.add_argument('plugin', nargs='+')

    subparsers = parser.add_subparsers(help='help for subcommand',
                                       dest='command')

    parser_install = subparsers.add_parser('install', help='Install plugins.',
                                           parents=[plugins_parser])

    parser_uninstall = subparsers.add_parser('uninstall',
                                             help='Uninstall plugins.',
                                             parents=[plugins_parser])

    parser_freeze = subparsers.add_parser('freeze', help='Output installed '
                                          'packages in requirements format.')

    args = parser.parse_args()
    if hasattr(args, 'plugin'):
        args.plugin = map(plugin_request, args.plugin)
    return args


def main():
    args = parse_args()
    print args
