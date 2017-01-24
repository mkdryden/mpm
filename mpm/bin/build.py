import argparse
import logging
import os
import sys

import path_helpers as ph

logger = logging.getLogger(__name__)


def parse_args(args=None):
    '''Parses arguments, returns ``(options, args)``.'''
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(description='MicroDrop plugin '
                                     'Conda recipe builder')
    parser.add_argument('-s', '--source-dir', type=ph.path, nargs='?')
    parser.add_argument('-t', '--target-dir', type=ph.path, nargs='?')

    parsed_args = parser.parse_args()
    if not parsed_args.source_dir:
        parsed_args.source_dir = ph.path(os.environ['SRC_DIR'])
    if not parsed_args.target_dir:
        prefix_dir = ph.path(os.environ['PREFIX'])
        pkg_name = os.environ['PKG_NAME']
        parsed_args.target_dir = prefix_dir.joinpath('share', 'microdrop',
                                                     'plugins', 'available',
                                                     pkg_name)

    return parsed_args


def build(source_dir, target_dir):
    '''
    Copy MicroDrop plugin source directory to target directory path.

    Skip the following patterns:

     - ``bld.bat``
     - ``.conda-recipe/*``
     - ``.git/*``

    Parameters
    ----------
    source_dir : str
        Source directory.
    target_dir : str
        Target directory.
    '''
    source_dir = ph.path(source_dir).realpath()
    target_dir = ph.path(target_dir).realpath()
    target_dir.parent.makedirs_p()

    def ignore(src, names):
        return [name_i for name_i in names
                if name_i in ['bld.bat', '.conda-recipe', '.git']]
    source_dir.copytree(target_dir, ignore=ignore)


def main(args=None):
    if args is None:
        args = parse_args()
    logger.debug('Arguments: %s', args)
    build(args.source_dir, args.target_dir)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main()
