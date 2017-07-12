import argparse
import logging
import os
import subprocess as sp
import sys
import zipfile

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
        # Extract module name from Conda package name.
        #
        # For example, the module name for a package named
        # `microdrop.droplet_planning_plugin` would be
        # `droplet_planning_plugin`.
        module_name = os.environ['PKG_NAME'].split('.')[-1]
        parsed_args.target_dir = prefix_dir.joinpath('share', 'microdrop',
                                                     'plugins', 'available',
                                                     module_name)

    return parsed_args


def build(source_dir, target_dir):
    '''
    Create a release of a MicroDrop plugin source directory in the target
    directory path.

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
    target_dir.makedirs_p()
    source_archive = source_dir.joinpath(source_dir.name + '.zip')

    # Export git archive, which substitutes version expressions in
    # `_version.py` to reflect the state (i.e., revision and tag info) of the
    # git repository.
    sp.check_call(['git', 'archive', '-o', source_archive, 'HEAD'], shell=True)

    # Extract exported git archive to Conda MicroDrop plugins directory.
    with zipfile.ZipFile(source_archive, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    # Delete Conda build recipe from installed package.
    target_dir.joinpath('.conda-recipe').rmtree()
    # Delete Conda build recipe from installed package.
    for p in target_dir.files('.git*'):
        p.remove()

    # Write package information to (legacy) `properties.yml` file.
    original_dir = ph.path(os.getcwd())
    try:
        os.chdir(source_dir)
        import _version as v
    finally:
        os.chdir(original_dir)

    # Create properties dictionary object (cast types, e.g., `ph.path`, to
    # strings for cleaner YAML dump).
    properties = {'package_name': str(target_dir.name),
                  'plugin_name': str(target_dir.name),
                  'version': v.get_versions()['version'],
                  'versioneer': v.get_versions()}
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
