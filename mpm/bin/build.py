import argparse
import logging
import os
import subprocess as sp
import sys

import path_helpers as ph
import yaml

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
    setup_cfg = source_dir.joinpath('setup.cfg')
    if not setup_cfg.isfile():
        with setup_cfg.open('w') as f_setup_cfg:
            f_setup_cfg.write('''\
[versioneer]
VCS = git
style = pep440
versionfile_source = .
tag_prefix = v''')
    original_dir = ph.path(os.getcwd())
    try:
        os.chdir(source_dir)
        sp.call('versioneer install', shell=True, stderr=sp.PIPE,
                stdout=sp.PIPE)
        import versioneer
        version = versioneer.get_version()
    finally:
        os.chdir(original_dir)
    properties = {'package_name': target_dir.name,
                  'plugin_name': target_dir.name,
                  'version': version}
    with target_dir.joinpath('properties.yml').open('w') as properties_yml:
        # Dump properties to YAML-formatted file.
        # Setting `default_flow_style=False` writes each property on a separate
        # line (cosmetic change only).
        yaml.dump(properties, properties_yml, default_flow_style=False)


def main(args=None):
    if args is None:
        args = parse_args()
    logger.debug('Arguments: %s', args)
    build(args.source_dir, args.target_dir)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main()
