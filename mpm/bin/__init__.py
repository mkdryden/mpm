# coding: utf-8
from argparse import ArgumentParser
from path_helpers import path
import logging
import sys

from ..commands import (DEFAULT_INDEX_HOST, freeze, get_plugins_directory,
                        install, SERVER_URL_TEMPLATE, uninstall)

logger = logging.getLogger(__name__)

default_plugins_directory = get_plugins_directory()
default_config_path = (default_plugins_directory.parent
                       .joinpath('microdrop.ini'))

# Parsers that may be reused by other modules.
LOG_PARSER = ArgumentParser(add_help=False)
LOG_PARSER.add_argument('-l', '--log-level', default='error',
                        choices=['error', 'debug', 'info'])
CONFIG_PARSER_ARGS = (('-c', '--config-file'),
                      dict(type=path, help='Microdrop config file '
                           '(default="{default}").'
                           .format(default=default_config_path)))
CONFIG_PARSER = ArgumentParser(add_help=False)
CONFIG_PARSER.add_argument(*CONFIG_PARSER_ARGS[0], **CONFIG_PARSER_ARGS[1])

SERVER_PARSER = ArgumentParser(add_help=False)
SERVER_PARSER.add_argument('-s', '--server-url',
                            default=DEFAULT_INDEX_HOST, help='Microdrop '
                            'plugin index URL (default="%(default)s")')
PLUGINS_PARSER = ArgumentParser(add_help=False)
PLUGINS_PARSER.add_argument('plugin', nargs='+')

MPM_PARSER = ArgumentParser(add_help=False, parents=[LOG_PARSER])
mutex_path = MPM_PARSER.add_mutually_exclusive_group()
mutex_path.add_argument(*CONFIG_PARSER_ARGS[0], **CONFIG_PARSER_ARGS[1])
mutex_path.add_argument('-d', '--plugins-directory', type=path,
                        help='Microdrop plugins directory '
                        '(default="{default}").'
                        .format(default=default_plugins_directory))
subparsers = MPM_PARSER.add_subparsers(help='help for subcommand',
                                       dest='command')
subparsers.add_parser('install', help='Install plugins.',
                      parents=[PLUGINS_PARSER, SERVER_PARSER])
subparsers.add_parser('uninstall', help='Uninstall plugins.',
                      parents=[PLUGINS_PARSER])
subparsers.add_parser('freeze', help='Output installed packages in '
                      'requirements format.')


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''
    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Microdrop plugin manager',
                            parents=[MPM_PARSER])

    return parser.parse_args()


def validate_args(args):
    '''
    Apply custom validation and actions based on parsed arguments.

    Args
    ----

        args (Namespace) : Result from `parse_args` method of
            `argparse.ArgumentParser` instance.

    Returns
    -------

        (Namespace) : Reference to input `args`, which have been
            validated/updated.
    '''
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


def main(args=None):
    if args is None:
        args = parse_args()
    args = validate_args(args)
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
