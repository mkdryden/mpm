# coding: utf-8
'''
Inspired by `pip`.

    mpm install <plugin-name>[(==|>|>=|<=)version] [<plugin-name>[(==|>|>=|<=)version]...]
    mpm install -r plugin_requirements.txt
    mpm remove <plugin-name>
'''
from collections import OrderedDict
import cStringIO as StringIO
import os

from path_helpers import path
from pip_helpers import CRE_PACKAGE
import configobj
import pip_helpers
import progressbar
import requests
import tarfile
import warnings
import yaml


DEFAULT_INDEX_HOST = r'http://microfluidics.utoronto.ca/update'
SERVER_URL_TEMPLATE = r'%s/plugins/{}/json/'
DEFAULT_SERVER_URL = SERVER_URL_TEMPLATE % DEFAULT_INDEX_HOST


def home_dir():
    '''
    Returns
    -------

        (str) : Path to home directory (or `Documents` directory on Windows).
    '''
    if os.name == 'nt':
        from win32com.shell import shell, shellcon

        return shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
    else:
        return os.path.expanduser('~')


def get_plugins_directory(config_path=None, microdrop_user_root=None):
    '''
    Args
    ----

        config_path (str) : Configuration file path (i.e., path to `microdrop.ini`).
            If `None`, `<home directory>/Microdrop/microdrop.ini` is used.
        microdrop_user_root (str) : Path to Microdrop user data directory.
            If `None`, `<home directory>/Microdrop` is used.

    Returns
    -------

        (path) : Absolute path to plugins directory.  If plugins directory
            setting cannot be resolved from a configuration file, the default
            plugins directory will be used:
            `<home directory>/Microdrop/plugins`.
    '''
    # # Find plugins directory path #
    if microdrop_user_root is None:
        microdrop_user_root = path(home_dir()).joinpath('Microdrop')
    else:
        microdrop_user_root = path(microdrop_user_root).expand()

    if config_path is None:
        config_path = microdrop_user_root.joinpath('microdrop.ini')
    else:
        config_path = path(config_path).expand()

    try:
        plugins_directory = path(configobj.ConfigObj(config_path)
                                 ['plugins']['directory'])
        if not plugins_directory.isabs():
            plugins_directory = config_path.parent.joinpath(plugins_directory)
    except Exception, why:
        plugins_directory = microdrop_user_root.joinpath('plugins')
        warnings.warn('%s.  Using default plugins directory: %s' %
                      (why, plugins_directory))
    return plugins_directory


def plugin_request(plugin_str):
    match = CRE_PACKAGE.match(plugin_str)
    if not match:
        raise ValueError('Invalid plugin descriptor. Must be like "foo", '
                         '"foo==1.0", "foo>=1.0", etc.')
    return match.groupdict()


def install(plugin_package, plugins_directory, server_url=DEFAULT_SERVER_URL):
    '''
    Args
    ----

        plugin_package (str) : Name of plugin package hosted on Microdrop
            plugin index. Version constraints are also supported (e.g., `"foo",
            "foo==1.0", "foo>=1.0"`, etc.)  See [version specifiers][1]
            reference for more details.
        plugins_directory (str) : Path to Microdrop user plugins directory.
        server_url (str) : URL of JSON request for Microdrop plugins package
            index.  See `DEFAULT_SERVER_URL` for default.

    Returns
    -------

        (path, dict) : Path to directory of installed plugin and plugin package
            metadata dictionary.

    [1]: https://www.python.org/dev/peps/pep-0440/#version-specifiers
    '''
    # Look up latest release matching specifiers.
    try:
        name, releases = pip_helpers.get_releases(plugin_package,
                                                  server_url=server_url)
        version, release = releases.items()[-1]
    except KeyError:
        raise

    # Check existing version (if any).
    plugin_path = plugins_directory.joinpath(name)

    if not plugin_path.isdir():
        existing_version = None
    else:
        plugin_metadata = yaml.load(plugin_path.joinpath('properties.yml')
                                    .bytes())
        existing_version = plugin_metadata['version']

    if version == existing_version:
        # Package already installed.
        raise ValueError('`{}=={}` is already installed.'.format(name,
                                                                 version))

    if existing_version is not None:
        # Uninstall existing package.
        uninstall(name, plugins_directory)

    # Install latest release
    # ======================
    print 'Installing `{}=={}`.'.format(name, version)

    # Download plugin release archive.
    download = requests.get(release['url'], stream=True)

    plugin_archive_bytes = StringIO.StringIO()
    total_bytes = int(download.headers['Content-length'])
    bytes_read = 0

    with progressbar.ProgressBar(max_value=total_bytes) as bar:
        while bytes_read < total_bytes:
            chunk_i = download.raw.read(1 << 8)
            bytes_read += len(chunk_i)
            plugin_archive_bytes.write(chunk_i)
            bar.update(bytes_read)

    # Extract downloaded plugin to install path.
    plugin_archive_bytes.seek(0)
    tar = tarfile.open(mode="r:gz", fileobj=plugin_archive_bytes)

    try:
        tar.extractall(plugin_path)

        plugin_metadata = yaml.load(plugin_path.joinpath('properties.yml').bytes())
        # Ensure installed package and version does not match requested version.
        assert(all([plugin_metadata['package_name'] == name,
                    plugin_metadata['version'] == version]))
    except:
        # Error occured, so delete extracted plugin.
        plugin_path.rmtree()
        raise
    print '  \--> done'

    # TODO Handle `requirements.txt`.
    return plugin_path, plugin_metadata


def uninstall(plugin_package, plugins_directory):
    '''
    Args
    ----

        plugin_package (str) : Name of plugin package hosted on Microdrop plugin index.
        plugins_directory (str) : Path to Microdrop user plugins directory.

    Returns
    -------

        None
    '''
    # Check existing version (if any).
    plugin_path = plugins_directory.joinpath(plugin_package)

    if not plugin_path.isdir():
        raise IOError('Plugin `%s` is not installed in `%s`' %
                      (plugin_package, plugins_directory))
    else:
        try:
            plugin_metadata = yaml.load(plugin_path.joinpath('properties.yml').bytes())
            existing_version = plugin_metadata['version']
        except:
            existing_version = None

    if existing_version is not None:
        # Uninstall existing package.
        print 'Uninstalling `{}=={}`.'.format(plugin_package, existing_version)
    else:
        print 'Uninstalling `{}`.'.format(plugin_package)

    # Uninstall latest release
    # ======================
    plugin_path.rmtree()
    print '  \--> done'


def freeze(plugins_directory):
    '''
    Args
    ----

        plugins_directory (str) : Path to Microdrop user plugins directory.

    Returns
    -------

        (list) : List of package strings corresponding to installed plugin versions.
    '''
    # Check existing version (if any).
    package_versions = []
    for plugin_path_i in plugins_directory.dirs():
        try:
            plugin_metadata = yaml.load(plugin_path_i
                                        .joinpath('properties.yml').bytes())
            if plugin_path_i.name != plugin_metadata['package_name']:
                continue
            package_versions.append((plugin_metadata['package_name'],
                                     plugin_metadata['version']))
        except:
            continue
    return ['%s==%s' % v for v in package_versions]


def search(plugin_package, server_url=DEFAULT_SERVER_URL):
    '''
    Args
    ----

        plugin_package (str) : Name of plugin package hosted on Microdrop
            plugin index. Version constraints are also supported (e.g., `"foo",
            "foo==1.0", "foo>=1.0"`, etc.)  See [version specifiers][1]
            reference for more details.
        server_url (str) : URL of JSON request for Microdrop plugins package
            index.  See `DEFAULT_SERVER_URL` for default.

    Returns
    -------

        (str, OrderedDict) : Name of found plugin and mapping of version
            strings to plugin package metadata dictionaries.

    [1]: https://www.python.org/dev/peps/pep-0440/#version-specifiers
    '''
    # Look up latest release matching specifiers.
    return pip_helpers.get_releases(plugin_package, server_url=server_url)
