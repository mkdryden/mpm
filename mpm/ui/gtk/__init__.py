import threading

import gtk
import gobject
import logging_helpers as lh

from ...update import _update_plugin


# The `update_plugin_dialog` class uses threads.  Need to initialize GTK to use
# threads. See [here][1] for more information.
#
# [1]: http://faq.pygtk.org/index.py?req=show&file=faq20.001.htp
gtk.gdk.threads_init()


def update_plugin_dialog(package_name):
    '''
    Launch dialog to track status of update of specified plugin package.

    .. versionadded:: 0.19

    Parameters
    ----------
    package_name : str, optional
        Conda MicroDrop plugin package name, e.g., `microdrop.mr-box-plugin`.

    Notes
    -----
    This function launches two threads; one to pulse the progress bar
    periodically, and one to run the actual update attempt.
    '''
    thread_context = {}
    def _update(update_complete, package_name):
        '''
        Attempt to update plugin.  Display status message when complete.
        '''
        try:
            with lh.logging_restore(clear_handlers=True):
                update_response = _update_plugin(package_name)
                thread_context['update_response'] = update_response
            # Display prompt indicating update status.
            if 'new_versions' in update_response:
                #  1. Success (with previous version and new version).
                def _status():
                    old_packages = update_response.get('old_versions', [])
                    new_packages = update_response.get('new_versions', [])

                    success_message = ('The <b>`{}`</b> plugin was updated '
                                       'successfully.'.format(package_name))
                    deps_only_message = ('Dependencies of the <b>`{}`</b> '
                                         'plugin were updated successfully.'
                                         .format(package_name))
                    if any(package_name in package_i
                           for package_i in new_packages):
                        # Plugin package was updated.
                        dialog.props.text = success_message
                    else:
                        # Only dependencies were updated.
                        dialog.props.text = deps_only_message

                    def _version_lines(versions):
                        return (['<tt>'] + list(' - {}'.format(package_i)
                                                for package_i in versions) +
                                ['</tt>'])
                    def _version_message(versions):
                        return ('<tt>{}</tt>'
                                .format('\n'.join(' - {}'.format(package_i)
                                                  for package_i in
                                                  versions)))
                    detailed_message_lines = []
                    if old_packages:
                        detailed_message_lines.append('From:')
                        detailed_message_lines.extend(_version_lines(old_packages))
                    if new_packages:
                        detailed_message_lines.append('To:')
                        detailed_message_lines.extend(_version_lines(new_packages))

                    if old_packages or new_packages:
                        dialog.props.secondary_text = \
                            '\n'.join(detailed_message_lines)
                    dialog.props.use_markup = True
                    dialog.props.secondary_use_markup = True
            else:
                #  2. No update available.
                def _status():
                    #  1. Success (with previous version and new version).
                    dialog.props.text = ('The latest version of the <tt><b>'
                                         '`{}` (v{})</b></tt> plugin is '
                                         'already installed.'
                                         .format(package_name,
                                                 update_response['version']))
                    dialog.props.use_markup = True
            gobject.idle_add(_status)
        except Exception, exception:
            # Failure updating plugin.
            def _error():
                dialog.props.text = ('Error updating plugin <tt>{}</tt>:'
                                     .format(package_name))
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
        gobject.idle_add(progress_bar.set_fraction, 1.)
        gobject.idle_add(progress_bar.hide)

    dialog = gtk.MessageDialog(buttons=gtk.BUTTONS_OK)
    dialog.set_position(gtk.WIN_POS_MOUSE)
    dialog.props.resizable = True
    progress_bar = gtk.ProgressBar()
    content_area = dialog.get_content_area()
    content_area.pack_start(progress_bar, True, True, 5)
    content_area.show_all()
    dialog.props.title = 'Update plugin'
    dialog.props.text = ('Searching for update for <tt>{}</tt>...'
                         .format(package_name))
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
    return thread_context['update_response']
