import argparse
import logging
import sys

from ..api import import_plugin

logger = logging.getLogger(__name__)


def parse_args(args=None):
    '''Parses arguments, returns ``(options, args)``.'''
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(description='MicroDrop plugin import '
                                     'test')
    parser.add_argument('module_name', help='Plugin module name')
    parser.add_argument('-a', '--include-available', help='Include all '
                        'available plugins (not just enabled ones).',
                        action='store_true')

    parsed_args = parser.parse_args()

    return parsed_args


def main(args=None):
    if args is None:
        args = parse_args()
    logger.debug('Arguments: %s', args)
    import_plugin(args.module_name, include_available=args.include_available)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main()
