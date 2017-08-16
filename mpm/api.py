# coding: utf-8
'''
See https://github.com/wheeler-microfluidics/microdrop/issues/216
'''
import importlib
import itertools as it
import logging
import json
import platform
import re
import sys
import types

import bz2
import conda_helpers as ch
import path_helpers as ph
import requests


logger = logging.getLogger(__name__)


MICRODROP_CONDA_ETC = ch.conda_prefix().joinpath('etc', 'microdrop')
MICRODROP_CONDA_SHARE = ch.conda_prefix().joinpath('share', 'microdrop')
MICRODROP_CONDA_ACTIONS = MICRODROP_CONDA_ETC.joinpath('actions')
MICRODROP_CONDA_PLUGINS = MICRODROP_CONDA_ETC.joinpath('plugins')

__all__ = ['available_packages', 'install', 'rollback', 'uninstall',
           'enable_plugin', 'disable_plugin', 'update', 'MICRODROP_CONDA_ETC',
           'MICRODROP_CONDA_SHARE', 'MICRODROP_CONDA_ACTIONS',
           'MICRODROP_CONDA_PLUGINS']


def _islinklike(dir_path):
    '''
    Parameters
    ----------
    dir_path : str
        Directory path.

    Returns
    -------
    bool
        ``True`` if :data:`dir_path` is a link *or* junction.
    '''
    dir_path = ph.path(dir_path)
    if platform.system() == 'Windows':
        if dir_path.isjunction():
            return True
    elif dir_path.islink():
        return True
    return False


def _channel_args(channels=None):
    '''
    Parameters
    ----------
    channels : list, optional
        List of Conda channels.

    Returns
    -------
    list
        List of arguments to pass to Conda commands to specify channels.

        For example, ``['-c', 'wheeler-plugins', '-c', 'conda-forge']``.
    '''
    channels = channels or ['microdrop-plugins']
    return list(it.chain(*[['-c', c] for c in channels]))


def _save_action(extra_context=None):
    '''
    Save list of revisions revisions for active Conda environment.

    .. versionchanged:: 0.18
        Compress action revision files using ``bz2`` to save disk space.

    Parameters
    ----------
    extra_context : dict, optional
        Extra content to store in stored action revision.

    Returns
    -------
    path_helpers.path, dict
        Path to which action was written and action object, including list of
        revisions for active Conda environment.
    '''
    # Get list of revisions to Conda environment since creation.
    revisions_js = ch.conda_exec('list', '--revisions', '--json',
                                 verbose=False)
    revisions = json.loads(revisions_js)
    # Save list of revisions to `/etc/microdrop/plugins/actions/rev<rev>.json`
    # See [wheeler-microfluidics/microdrop#200][i200].
    #
    # [i200]: https://github.com/wheeler-microfluidics/microdrop/issues/200
    action = extra_context.copy() if extra_context else {}
    action['revisions'] = revisions
    action_path = (MICRODROP_CONDA_ACTIONS
                   .joinpath('rev{}.json.bz2'.format(revisions[-1]['rev'])))
    action_path.parent.makedirs_p()
    # Compress action file using bz2 to save disk space.
    with bz2.BZ2File(action_path, mode='w') as output:
        json.dump(action, output, indent=2)
    return action_path, action


def _remove_broken_links():
    '''
    Remove broken links in `<conda prefix>/etc/microdrop/plugins/enabled/`.

    Returns
    -------
    list
        List of links removed (if any).
    '''
    enabled_dir = MICRODROP_CONDA_PLUGINS.joinpath('enabled')
    if not enabled_dir.isdir():
        return []

    broken_links = []
    for dir_i in enabled_dir.walkdirs(errors='ignore'):
        if platform.system() == 'Windows':
            if dir_i.isjunction() and not dir_i.readlink().isdir():
                # Junction/link target no longer exists.
                broken_links.append(dir_i)
        else:
            raise NotImplementedError('Unsupported platform')

    removed_links = []
    for link_i in broken_links:
        try:
            link_i.unlink()
        except:
            pass
        else:
            removed_links.append(link_i)
    return removed_links


# ## Supporting legacy MicroDrop plugins ##
#
# Legacy MicroDrop plugins **MAY** be made **available** by linking according
# to **(2)** above.
#
# # TODO #
#
#  - [ ] Create Python API for MicroDrop plugins to:
#      * [x] Query available plugin packages based on specified Conda channels
def available_packages(*args, **kwargs):
    '''
    Query available plugin packages based on specified Conda channels.

    Parameters
    ----------
    *args
        Extra arguments to pass to Conda ``search`` command.
    channels : list, optional
        .. warning::
            Support for ``--override-channels`` flag in ``conda search`` is
            broken.

            See https://github.com/conda/conda/issues/5158 for details.
        .. versionchanged:: 0.14
            Explicitly only look for plugins on the ``microdrop-plugins`` channel.

            This is a temporary workaround for the ``conda search`` issue (see
            https://github.com/conda/conda/issues/5158)
    override_channels : bool, optional
        .. warning::
            Support for ``--override-channels`` flag in ``conda search`` is
            broken.

            See https://github.com/conda/conda/issues/5158 for details.

    Returns
    -------
    dict
        .. versionchanged:: 0.14
            All available packages from the ``microdrop-plugins`` channel.

        .. warning::
            The :data:`channels` argument is currently ignored until the issue
            with ``conda search`` is resolved (see
            https://github.com/conda/conda/issues/5158).

        Each *key* corresponds to a package name.

        Each *value* corresponds to a ``list`` of dictionaries, each
        corresponding to an available version of the respective package.
    '''
    # Fetch `microdrop-plugins` repository package list.
    response = requests.get('https://conda.anaconda.org/microdrop-plugins/win-32/repodata.json')
    repo_info = json.loads(response.text)
    key_func = lambda v: v['name']

    # Group available `*.bz2` packages by package name.
    plugin_infos = dict([(k, list(v)) for k, v in
                         it.groupby(sorted(repo_info['packages'].values(),
                                           key=key_func), key_func)])
    return plugin_infos


#      * [x] Install plugin package(s) from selected Conda channels
def install(plugin_name, *args, **kwargs):
    '''
    Install plugin packages based on specified Conda channels.

    .. versionchanged:: 0.19.1
        Do not save rollback info on dry-run.

    Parameters
    ----------
    plugin_name : str or list
        Plugin package(s) to install.

        Version specifiers are also supported, e.g., ``package >=1.0.5``.
    *args
        Extra arguments to pass to Conda ``install`` command.
    channels : list, optional
        List of Conda channels to search.

        Local channels can be specified using the ``'file://'`` prefix.

        For example, on Windows, use something similar to:

            'file:///C:/Users/chris/local-repo'

        ..notes::
            A local directory containing packages may be converted to a local
            channel by running ``conda index`` within the directory.

            Each local file channel must point to a directory with the name of
            a Conda platform (e.g., ``win-32``) or to a parent directory
            containing multiple directories, where each directory has the name
            of a Conda platform.

    Returns
    -------
    dict
        Conda installation log object (from JSON Conda install output).
    '''
    channel_args = _channel_args(channels=kwargs.pop('channels', None))
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]

    # Perform installation
    conda_args = (['install', '-y', '--json'] + channel_args + list(args) +
                  plugin_name)
    install_log_js = ch.conda_exec(*conda_args, verbose=False)
    install_log = json.loads(install_log_js.split('\x00')[-1])
    if 'actions' in install_log and not install_log.get('dry_run'):
        # Install command modified Conda environment.
        _save_action({'conda_args': conda_args, 'install_log': install_log})
        logger.debug('Installed plugin(s): ```%s```', install_log['actions'])
    return install_log


#      * [x] **Rollback** (i.e., load last revision number from latest
#        `<conda prefix>/etc/microdrop/plugins/restore_points/r<revision>.json`
#        and run `conda install --revision <revision number>`), see #200
def rollback(*args, **kwargs):
    '''
    Restore previous revision of Conda environment according to most recent
    action in :attr:`MICRODROP_CONDA_ACTIONS`.

    .. versionchanged:: 0.18
        Add support for action revision files compressed using ``bz2``.

    Parameters
    ----------
    *args
        Extra arguments to pass to Conda ``install`` roll-back command.
    channels : list, optional
        List of Conda channels to search.

        Local channels can be specified using the ``'file://'`` prefix.

        For example, on Windows, use something similar to:

            'file:///C:/Users/chris/local-repo'

        ..notes::
            A local directory containing packages may be converted to a local
            channel by running ``conda index`` within the directory.

            Each local file channel must point to a directory with the name of
            a Conda platform (e.g., ``win-32``) or to a parent directory
            containing multiple directories, where each directory has the name
            of a Conda platform.

    Returns
    -------
    int, dict
        Revision after roll back and Conda installation log object (from JSON
        Conda install output).

    See also
    --------

    `wheeler-microfluidics/microdrop#200 <https://github.com/wheeler-microfluidics/microdrop/issues/200>`
    '''
    channel_args = _channel_args(channels=kwargs.pop('channels', None))
    action_files = MICRODROP_CONDA_ACTIONS.files()
    if not action_files:
        # No action files, return current revision.
        logger.debug('No rollback actions have been recorded.')
        revisions_js = ch.conda_exec('list', '--revisions', '--json',
                                     verbose=False)
        revisions = json.loads(revisions_js)
        return revisions[-1]['rev']
    # Get file associated with most recent action.
    cre_rev = re.compile(r'rev(?P<rev>\d+)')
    action_file = sorted([(int(cre_rev.match(file_i.namebase).group('rev')),
                           file_i) for file_i in
                          action_files if cre_rev.match(file_i.namebase)],
                         reverse=True)[0]
    # Do rollback (i.e., install state of previous revision).
    if action_file.ext.lower() == '.bz2':
        # Assume file is compressed using bz2.
        with bz2.BZ2File(action_file, mode='r') as input_:
            action = json.load(input_)
    else:
        # Assume it is raw JSON.
        with action_file.open('r') as input_:
            action = json.load(input_)
    rollback_revision = action['revisions'][-2]
    conda_args = (['install', '--json'] + channel_args + list(args) +
                  ['--revision', str(rollback_revision)])
    install_log_js = ch.conda_exec(*conda_args, verbose=False)
    install_log = json.loads(install_log_js.split('\x00')[-1])
    logger.debug('Rolled back to revision %s', rollback_revision)
    return rollback_revision, install_log


#      * [x] Uninstall plugin package(s) from selected Conda channels
#          - Remove broken links in `<conda prefix>/etc/microdrop/plugins/enabled/`
def uninstall(plugin_name, *args):
    '''
    Uninstall plugin packages.

    Plugin packages must have a directory with the same name as the package in
    the following directory:

        <conda prefix>/share/microdrop/plugins/available/

    Parameters
    ----------
    plugin_name : str or list
        Plugin package(s) to uninstall.
    *args
        Extra arguments to pass to Conda ``uninstall`` command.

    Returns
    -------
    dict
        Conda uninstallation log object (from JSON Conda uninstall output).
    '''
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]

    available_path = MICRODROP_CONDA_SHARE.joinpath('plugins', 'available')
    for name_i in plugin_name:
        plugin_module_i = name_i.split('.')[-1].replace('-', '_')
        plugin_path_i = available_path.joinpath(plugin_module_i)
        if not _islinklike(plugin_path_i) and not plugin_path_i.isdir():
            raise IOError('Plugin `{}` not found in `{}`'
                          .format(name_i, available_path))
        else:
            logging.debug('[uninstall] Found plugin `%s`', plugin_path_i)

    # Perform uninstall operation.
    conda_args = ['uninstall', '--json', '-y'] + list(args) + plugin_name
    uninstall_log_js = ch.conda_exec(*conda_args, verbose=False)
    # Remove broken links in `<conda prefix>/etc/microdrop/plugins/enabled/`,
    # since uninstall may have made one or more packages unavailable.
    _remove_broken_links()
    logger.debug('Uninstalled plugins: ```%s```', plugin_name)
    return json.loads(uninstall_log_js.split('\x00')[-1])


#      * [x] Enable/disable installed plugin package(s)
def enable_plugin(plugin_name):
    '''
    Enable installed plugin package(s).

    Each plugin package must have a directory with the same name as the package
    in the following directory:

        <conda prefix>/share/microdrop/plugins/available/

    Parameters
    ----------
    plugin_name : str or list
        Plugin package(s) to enable.

    Returns
    -------
    dict
        Dictionary containing a flag for each plugin name:

         - ``False`` iff the plugin was already enabled.
         - ``True`` iff it was just enabled now.

    Raises
    ------
    IOError
        If plugin is not installed to ``<conda prefix>/share/microdrop/plugins/available/``.
    '''
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]
        singleton = True
    else:
        singleton = False

    # Conda-managed plugins
    shared_available_path = MICRODROP_CONDA_SHARE.joinpath('plugins',
                                                           'available')
    # User-managed plugins
    etc_available_path = MICRODROP_CONDA_ETC.joinpath('plugins', 'available')

    available_paths = (etc_available_path, shared_available_path)
    plugin_paths = []
    for name_i in plugin_name:
        for available_path_j in available_paths:
            plugin_path_ij = available_path_j.joinpath(name_i)
            if not _islinklike(plugin_path_ij) and plugin_path_ij.isdir():
                logger.debug('Found plugin directory: `%s`', plugin_path_ij)
                break
        else:
            raise IOError('Plugin `{}` not found in `{}` or `{}`'
                          .format(name_i, *available_paths))
        plugin_paths.append(plugin_path_ij)

    # All specified plugins are available.

    # Link all specified plugins in
    # `<conda prefix>/etc/microdrop/plugins/enabled/` (if not already linked).
    enabled_path = MICRODROP_CONDA_PLUGINS.joinpath('enabled')
    enabled_path.makedirs_p()

    # Set flag for each plugin: `False` iff the plugin was already enabled,
    # `True` iff it was just enabled now.
    enabled_now = {}
    for plugin_path_i in plugin_paths:
        plugin_link_path_i = enabled_path.joinpath(plugin_path_i.name)
        if not plugin_link_path_i.exists():
            if platform.system() == 'Windows':
                plugin_path_i.junction(plugin_link_path_i)
            else:
                plugin_path_i.symlink(plugin_link_path_i)
            logger.debug('Enabled plugin directory: `%s` -> `%s`',
                         plugin_path_i, plugin_link_path_i)
            enabled_now[plugin_path_i.name] = True
        else:
            logger.debug('Plugin already enabled: `%s` -> `%s`', plugin_path_i,
                         plugin_link_path_i)
            enabled_now[plugin_path_i.name] = False
    return enabled_now if not singleton else enabled_now.values()[0]


def disable_plugin(plugin_name):
    '''
    Disable plugin package(s).

    Parameters
    ----------
    plugin_name : str or list
        Plugin package(s) to disable.

    Raises
    ------
    IOError
        If plugin is not enabled.
    '''
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]

    # Verify all specified plugins are currently enabled.
    enabled_path = MICRODROP_CONDA_PLUGINS.joinpath('enabled')
    for name_i in plugin_name:
        plugin_path_i = enabled_path.joinpath(name_i)
        if not _islinklike(plugin_path_i) and not plugin_path_i.isdir():
            raise IOError('Plugin `{}` not found in `{}`'
                          .format(name_i, enabled_path))

    # All specified plugins are enabled.

    # Remove all specified plugins from
    # `<conda prefix>/etc/microdrop/plugins/enabled/`.
    for name_i in plugin_name:
        plugin_link_path_i = enabled_path.joinpath(name_i)
        plugin_link_path_i.unlink()
        logger.debug('Disabled plugin `%s` (i.e., removed `%s`)',
                     plugin_path_i, plugin_link_path_i)


def update(*args, **kwargs):
    '''
    Update all installed plugin package(s).

    Each plugin package must have a directory (**NOT** a link) with the same
    name as the package in the following directory:

        <conda prefix>/share/microdrop/plugins/available/

    Parameters
    ----------
    *args
        Extra arguments to pass to Conda ``install`` command.

        See :func:`install`.
    **kwargs
        See :func:`install`.

    Returns
    -------
    dict
        Conda installation log object (from JSON ``conda install`` output).

    Notes
    -----
    Only actual plugin directories are considered when updating (i.e., **NOT**
    directory links).

    This permits, for example, linking of a plugin into the ``available``
    plugins directory during development without risking overwriting during an
    update.

    Raises
    ------
    RuntimeError
        If one or more installed plugin packages cannot be updated.

        This can happen, for example, if the plugin package is not available in
        any of the specified Conda channels.
    '''
    available_path = MICRODROP_CONDA_SHARE.joinpath('plugins', 'available')
    if not available_path.isdir():
        return {}
    installed_plugins = []
    for plugin_path_i in available_path.dirs():
        # Only process plugin directory if it is *not a link*.
        if not _islinklike(plugin_path_i):
            installed_plugins.append(plugin_path_i.name)
    if installed_plugins:
        install_log = install(installed_plugins, *args, **kwargs)
        if 'actions' in install_log:
            logger.debug('Updated plugin(s): ```%s```', install_log['actions'])
        return install_log
    else:
        return {}


def import_plugin(package_name, include_available=False):
    '''
    Import MicroDrop plugin.

    Parameters
    ----------
    package_name : str
        Name of MicroDrop plugin Conda package.
    include_available : bool, optional
        If ``True``, import from all available plugins (not just **enabled**
        ones).

        By default, only the ``<conda>/etc/microdrop/plugins/enabled``
        directory is added to the Python import paths (if necessary).

        If ``True``, also add the ``<conda>/share/microdrop/plugins/available``
        directory to the Python import paths.

    Returns
    -------
    module
        Imported plugin module.
    '''
    available_plugins_dir = MICRODROP_CONDA_SHARE.joinpath('plugins',
                                                           'available')
    enabled_plugins_dir = MICRODROP_CONDA_ETC.joinpath('plugins', 'enabled')
    search_paths = [enabled_plugins_dir]
    if include_available:
        search_paths += [available_plugins_dir]
    for dir_i in search_paths:
        if dir_i not in sys.path:
            sys.path.insert(0, dir_i)
    module_name = package_name.split('.')[-1].replace('-', '_')
    return importlib.import_module(module_name)
