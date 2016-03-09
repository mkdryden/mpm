from argparse import ArgumentParser
from path_helpers import path
import logging
import sys

from ..commands import (DEFAULT_INDEX_HOST, freeze, get_plugins_directory,
                        install, SERVER_URL_TEMPLATE, uninstall)

logger = logging.getLogger(__name__)


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''

    if args is None:
        args = sys.argv

    default_plugins_directory = get_plugins_directory()
    default_config_path = (default_plugins_directory.parent
                           .joinpath('microdrop.ini'))

    parser = ArgumentParser(description='Microdrop plugin manager')
    parser.add_argument('-l', '--log-level', choices=['error', 'debug',
                                                      'info'],
                        default='error')
    mutex_path = parser.add_mutually_exclusive_group()
    mutex_path.add_argument('-c', '--config-file', type=path,
                            help='Microdrop config file '
                            '(default="{default}").'
                            .format(default=default_config_path))
    mutex_path.add_argument('-d', '--plugins-directory', type=path,
                            help='Microdrop plugins directory '
                            '(default="{default}").'
                            .format(default=default_plugins_directory))

    server_parser = ArgumentParser(add_help=False)
    server_parser.add_argument('-s', '--server-url',
                               default=DEFAULT_INDEX_HOST, help='Microdrop '
                               'plugin index URL (default="%(default)s")')

    plugins_parser = ArgumentParser(add_help=False)
    plugins_parser.add_argument('plugin', nargs='+')

    subparsers = parser.add_subparsers(help='help for subcommand',
                                       dest='command')

    parser_install = subparsers.add_parser('install', help='Install plugins.',
                                           parents=[plugins_parser,
                                                    server_parser])

    parser_uninstall = subparsers.add_parser('uninstall',
                                             help='Uninstall plugins.',
                                             parents=[plugins_parser])

    parser_freeze = subparsers.add_parser('freeze', help='Output installed '
                                          'packages in requirements format.')

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    if hasattr(args, 'server_url'):
        logger.debug('Using Microdrop index server: "%s"', args.server_url)
        args.server_url = SERVER_URL_TEMPLATE % args.server_url
    if all([args.plugins_directory is None,
            args.config_file is None]):
        args.plugins_directory = default_plugins_directory
        logger.debug('Using default plugins directory: "%s"',
                     args.plugins_directory)
    elif args.plugins_directory is None:
        args.plugins_directory = get_plugins_directory(config_path=
                                                       args.config_file)
        logger.debug('Plugins directory from config file: "%s"',
                     args.plugins_directory)
    else:
        logger.debug('Using explicit plugins directory: "%s"',
                     args.plugins_directory)
    return args


def main():
    args = parse_args()
    logger.debug('Arguments: %s', args)
    if args.command == 'freeze':
        print '\n'.join(freeze(plugins_directory=args.plugins_directory))
    elif args.command == 'install':
        for plugin_i in args.plugin:
            try:
                install(plugin_package=plugin_i,
                        plugins_directory=args.plugins_directory,
                        server_url=args.server_url)
            except ValueError, exception:
                print exception.message
                continue
    elif args.command == 'uninstall':
        for plugin_i in args.plugin:
            uninstall(plugin_package=plugin_i,
                      plugins_directory=args.plugins_directory)
