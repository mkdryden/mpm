# coding: utf-8
'''
See https://github.com/wheeler-microfluidics/microdrop/issues/216
'''
import itertools as it
import json
import re
import types

import conda_helpers as ch


MICRODROP_CONDA_ETC = ch.conda_prefix().joinpath('etc', 'microdrop')
MICRODROP_CONDA_SHARE = ch.conda_prefix().joinpath('share', 'microdrop')
MICRODROP_CONDA_ACTIONS = MICRODROP_CONDA_ETC.joinpath('actions')
MICRODROP_CONDA_PLUGINS = MICRODROP_CONDA_ETC.joinpath('plugins')


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
                   .joinpath('rev{}.json'.format(revisions[-1]['rev'])))
    action_path.parent.makedirs_p()
    with action_path.open('w') as output:
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
        try:
            dir_i.listdir()
        except WindowsError:
            broken_links.append(dir_i)

    removed_links = []
    for link_i in broken_links:
        try:
            link_i.rm_rf()
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
def available_packages(channels=None):
    '''
    Query available plugin packages based on specified Conda channels.

    Parameters
    ----------
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
        All available packages from channels.

        Each *key* corresponds to a package name.

        Each *value* corresponds to a ``list`` of dictionaries, each
        corresponding to an available version of the respective package.
    '''
    channels_args = _channel_args(channels)

    # Get dictionary of available packages
    conda_args = ['search', '--override-channels', '--json'] + channels_args
    pkgs_js = ch.conda_exec(*conda_args, verbose=False)
    return json.loads(pkgs_js)


#      * [x] Install plugin package(s) from selected Conda channels
def install(plugin_name, *args, **kwargs):
    '''
    Install plugin packages based on specified Conda channels.

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
        Result from

        Each *key* corresponds to a package name.

        Each *value* corresponds to a ``list`` of dictionaries, each
        corresponding to an available version of the respective package.
    '''
    channel_args = _channel_args(channels=kwargs.pop('channels', None))
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]

    # Perform installation
    conda_args = (['install', '-y', '--json'] + channel_args + list(args) +
                  plugin_name)
    install_log_js = ch.conda_exec(*conda_args, verbose=False)
    install_log = json.loads(install_log_js.split('\x00')[-1])
    if 'actions' in install_log:
        # Install command modified Conda environment.
        _save_action({'conda_args': conda_args, 'install_log': install_log})
    return install_log


#      * [x] **Rollback** (i.e., load last revision number from latest
#        `<conda prefix>/etc/microdrop/plugins/restore_points/r<revision>.json`
#        and run `conda install --revision <revision number>`), see #200
def rollback(*args, **kwargs):
    '''
    Restore previous revision of Conda environment according to most recent
    action in :attr:`MICRODROP_CONDA_ACTIONS`.

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
    with action_file.open('r') as input_:
        action = json.load(input_)
    rollback_revision = action['revisions'][-2]
    conda_args = (['install', '--json'] + channel_args + list(args) +
                  ['--revision', str(rollback_revision)])
    install_log_js = ch.conda_exec(*conda_args, verbose=False)
    install_log = json.loads(install_log_js.split('\x00')[-1])
    return rollback_revision, install_log
