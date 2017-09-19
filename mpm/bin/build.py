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
    '''
    Parses arguments, returns ``(options, args)``.

    .. versionchanged:: 0.24.1
        Fix handling of optional :data:`args`.
    '''
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='MicroDrop plugin '
                                     'Conda recipe builder')
    parser.add_argument('-s', '--source-dir', type=ph.path, nargs='?')
    parser.add_argument('-t', '--target-dir', type=ph.path, nargs='?')
    parser.add_argument('-p', '--package-name', nargs='?')

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
        module_name = os.environ['PKG_NAME'].split('.')[-1].replace('-', '_')
        parsed_args.target_dir = prefix_dir.joinpath('share', 'microdrop',
                                                     'plugins', 'available',
                                                     module_name)
    if not parsed_args.package_name:
        parsed_args.package_name = os.environ['PKG_NAME']

    return parsed_args


def build(source_dir, target_dir, package_name=None):
    '''
    Create a release of a MicroDrop plugin source directory in the target
    directory path.

    Skip the following patterns:

     - ``bld.bat``
     - ``.conda-recipe/*``
     - ``.git/*``

    .. versionchanged:: 0.24.1
        Remove temporary archive after extraction.

        Change directory into source directory before running ``git archive``.

    Parameters
    ----------
    source_dir : str
        Source directory.
    target_dir : str
        Target directory.
    package_name : str, optional
        Name of plugin Conda package (defaults to name of :data:`target_dir`).
    '''
    source_dir = ph.path(source_dir).realpath()
    target_dir = ph.path(target_dir).realpath()
    target_dir.makedirs_p()
    source_archive = source_dir.joinpath(source_dir.name + '.zip')
    if package_name is None:
        package_name = str(target_dir.name)
    logger.info('Source directory: %s', source_dir)
    logger.info('Source archive: %s', source_archive)
    logger.info('Target directory: %s', target_dir)
    logger.info('Package name: %s', package_name)

    # Export git archive, which substitutes version expressions in
    # `_version.py` to reflect the state (i.e., revision and tag info) of the
    # git repository.
    original_dir = ph.path(os.getcwd())
    try:
        os.chdir(source_dir)
        sp.check_call(['git', 'archive', '-o', source_archive, 'HEAD'],
                      shell=True)
    finally:
        os.chdir(original_dir)

    # Extract exported git archive to Conda MicroDrop plugins directory.
    with zipfile.ZipFile(source_archive, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    # Extraction is complete.  Remove temporary archive.
    source_archive.remove()

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
    properties = {'package_name': package_name,
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
    build(args.source_dir, args.target_dir, package_name=args.package_name)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    main()
