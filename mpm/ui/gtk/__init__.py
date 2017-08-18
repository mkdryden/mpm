import logging
import threading
import types

import conda_helpers as ch
import gtk
import gobject
import logging_helpers as lh

from ...api import installed_plugins, update

logger = logging.getLogger(__name__)

# The `update_plugin_dialog` class uses threads.  Need to initialize GTK to use
# threads. See [here][1] for more information.
#
# [1]: http://faq.pygtk.org/index.py?req=show&file=faq20.001.htp
gtk.gdk.threads_init()


def update_plugin_dialog(package_name=None, update_args=None,
                         update_kwargs=None, ignore_not_installed=True):
    '''
    Launch dialog to track status of update of specified plugin package.

    .. versionadded:: 0.19

    .. versionchanged:: 0.20
        Add support for updating multiple packages (update all **installed**
        plugins by default).

        Add :data:`update_args` and :data:`update_kwargs` arguments.

    .. versionchanged:: 0.20.1
        Disable "OK" button until update has completed.

        Add "Cancel" button.

    .. versionchanged:: 0.20.3
        Fix typo in handling of attempt to update plugin packages that are not
        installed.

    .. versionchanged:: 0.23
        Add :data:`ignore_not_installed` parameter.

    Parameters
    ----------
    package_name : str or list, optional
        Conda MicroDrop plugin package name, e.g., `microdrop.mr-box-plugin`.

        Multiple plugin package names may be provided as a list.

        If no package name(s) specified, update **all installed** plugin
        packages.
    update_args : list or tuple, optional
        Extra arguments to pass to :func:`mpm.api.update` call.
    update_kwargs : dict, optional
        Extra keyword arguments to pass to :func:`mpm.api.update` call.
    ignore_not_installed : bool, optional
        If ``True`` (*default*), ignore plugin packages that are not installed
        as Conda packages.

        Otherwise, a :class:`conda_heplers.PackageNotFound` exception will be
        raised for plugins that are not installed as Conda packages.

    Returns
    -------
    dict or None
        Conda install log.

        If dialog is closed or cancelled, ``None`` is returned.

    Notes
    -----
    This function launches two threads; one to pulse the progress bar
    periodically, and one to run the actual update attempt.
    '''
    thread_context = {}

    if package_name is None:
        # No plugin package specified.  Update all plugins which are installed
        # as Conda packages.
        installed_plugins_ = installed_plugins(only_conda=True)
        installed_package_names = [plugin_i['package_name']
                                   for plugin_i in installed_plugins_]
        package_name = installed_package_names
        logger.info('Update all plugins installed as Conda packages.')
    else:
        # At least one plugin package name was explicitly specified.
        if isinstance(package_name, types.StringTypes):
            package_name = [package_name]

        # Only update plugins that are installed as Conda packages.
        try:
            conda_package_infos = ch.package_version(package_name, verbose=False)
        except ch.PackageNotFound, exception:
            # At least one specified plugin package name did not correspond to an
            # installed Conda package.
            if not ignore_not_installed:
                # Raise error indicating at least one plugin is not installed
                # as a Conda package.
                raise
            logger.warning(str(exception))
            conda_package_infos = exception.available
        # Extract name from each Conda plugin package.
        package_name = [package_i['name'] for package_i in conda_package_infos]
        logger.info('Update the following plugins: %s',
                    ', '.join('`{}`'.format(name_i)
                              for name_i in package_name))

    # Format string list of packages.
    package_name_list = ', '.join('`{}`'.format(name_i)
                                  for name_i in package_name)
    # Format multiple-lines string list of packages.
    package_name_lines = '\n'.join(' - {}'.format(name_i)
                                   for name_i in package_name)

    def _update(update_complete, package_name):
        '''
        Attempt to update plugin.  Display status message when complete.

        Parameters
        ----------
        update_complete : threading.Event
            Set when update operation has been completed.
        package_name : str, list, or None
            Conda MicroDrop plugin package name(s) (default to all installed
            plugins).
        '''
        try:
            with lh.logging_restore(clear_handlers=True):
                args = update_args or []
                kwargs = update_kwargs or {}
                kwargs['package_name'] = package_name
                # Pass extra args and kwargs to `.api.update` (if specified).
                update_response = update(*args, **kwargs)
                thread_context['update_response'] = update_response

            # Display prompt indicating update status.

            # Get list of unlinked and linked packages.
            install_info_ = ch.install_info(update_response)

            if any(install_info_):
                # At least one package was uninstalled or installed (or
                # "unlinked"/"linked" in Conda lingo).
                def _status():
                    updated_packages = []
                    for package_name_i in package_name:
                        if any(linked_i[0].startswith(package_name_i)
                               for linked_i in install_info_[1]):
                            # Plugin package was updated.
                            updated_packages.append(package_name_i)

                    def _version_lines(package_info_tuples):
                        return (['<tt>'] + list(' - {} (from {})'
                                                .format(name_i, channel_i)
                                                for name_i, channel_i in
                                                package_info_tuples) +
                                ['</tt>'])
                    detailed_message_lines = []
                    if install_info_[0]:
                        detailed_message_lines.append('<b>Uninstalled:</b>')
                        (detailed_message_lines
                         .extend(_version_lines(install_info_[0])))
                    if install_info_[1]:
                        detailed_message_lines.append('<b>Installed:</b>')
                        (detailed_message_lines
                         .extend(_version_lines(install_info_[1])))

                    dialog.props.secondary_text = \
                        '\n'.join(detailed_message_lines)
                    dialog.props.secondary_use_markup = True
                    dialog.props.use_markup = True

                    if updated_packages:
                        message = ('The following plugin(s) were updated '
                                   'successfully:\n<b><tt>{}</tt></b>'
                                   .format(package_name_lines))
                    else:
                        message = ('Plugin dependencies were updated '
                                   'successfully.')
                    dialog.props.text = message
            else:
                # No packages were unlinked **or** linked.
                def _status():
                    #  1. Success (with previous version and new version).
                    dialog.props.text = ('The latest version of the following '
                                         'plugin(s) are already installed: '
                                         '<tt><b>`{}`'
                                         .format(package_name_list))
                    dialog.props.use_markup = True
            gobject.idle_add(_status)
        except Exception, exception:
            # Failure updating plugin.
            def _error():
                dialog.props.text = ('Error updating plugin(s):\n<tt>{}</tt>'
                                     .format(package_name_lines))
                dialog.props.use_markup = True
                exception_markup = gobject.markup_escape_text(str(exception))
                exception_markup = exception_markup.replace(r'\n', '\n')

                content_area = dialog.get_content_area()
                label = gtk.Label()
                label.set_markup(exception_markup)
                error_scroll = gtk.ScrolledWindow()
                error_scroll.set_policy(gtk.POLICY_AUTOMATIC,
                                        gtk.POLICY_AUTOMATIC)
                error_scroll.add_with_viewport(label)
                error_scroll.show_all()

                content_area.pack_start(error_scroll, expand=True, fill=True)
            gobject.idle_add(_error)
            thread_context['update_response'] = None
        update_complete.set()

    def _pulse(update_complete, progress_bar):
        '''
        Show pulsing progress bar to indicate activity.
        '''
        while not update_complete.wait(1. / 16):
            gobject.idle_add(progress_bar.pulse)
        def _on_complete():
            progress_bar.set_fraction(1.)
            progress_bar.hide()
            # Enable "OK" button and focus it.
            dialog.action_area.get_children()[1].props.sensitive = True
            dialog.action_area.get_children()[1].grab_focus()
        gobject.idle_add(_on_complete)

    dialog = gtk.MessageDialog(buttons=gtk.BUTTONS_OK_CANCEL)
    dialog.set_position(gtk.WIN_POS_MOUSE)
    dialog.props.resizable = True
    progress_bar = gtk.ProgressBar()
    content_area = dialog.get_content_area()
    content_area.pack_start(progress_bar, True, True, 5)
    content_area.show_all()
    # Disable "OK" button until update has completed.
    dialog.action_area.get_children()[1].props.sensitive = False

    dialog.props.title = 'Update plugin'
    if len(package_name) > 1:
        # Multiple packages were specified.
        dialog.props.text = ('Searching for updates for:\n<tt>{}</tt>'
                             .format(package_name_lines))
    else:
        # A single package was specified.
        dialog.props.text = ('Searching for updates for <tt>{}</tt>...'
                             .format(package_name[0]))
    dialog.props.use_markup = True

    # Event to keep progress bar pulsing while waiting for update to
    # complete.
    update_complete = threading.Event()

    # Launch thread to periodically pulse progress bar.
    progress_thread = threading.Thread(target=_pulse, args=(update_complete,
                                                            progress_bar, ))
    progress_thread.daemon = True
    progress_thread.start()

    # Launch thread to attempt plugin update.
    update_thread = threading.Thread(target=_update, args=(update_complete,
                                                           package_name, ))
    update_thread.daemon = True
    update_thread.start()

    # Show dialog.
    dialog.run()
    dialog.destroy()

    # Return response from `conda_helpers.api.update` call.
    return thread_context.get('update_response')
