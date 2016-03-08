import sublime
import sublime_plugin
import os.path
import ntpath

package_name = 'TabTeleport'


class TabteleportCtrlTabCommand(sublime_plugin.WindowCommand):
    """Handler which manages Ctrl+Tab command
    if tabteleport view is open:
        Closes tabteleport view. Ctrl+Tab was pressed second time
    else:
        Creates a new view and runs command to construct list of all open tabs
        in the view.
    """

    def run(self):
        active_view = self.window.active_view()
        if active_view and active_view.name() == package_name:
            tabteleport_view = self.window.active_view()
            previous_view_id = tabteleport_view.settings().get(
                'previous_view_id')
            previous_view = [v for v in self.window.views()
                               if v.id() == previous_view_id][0]
            self.window.focus_view(previous_view)
            tabteleport_view.close()
        else:
            new_view = self.window.new_file()
            new_view.settings().set(
                'previous_view_id', self.window.active_view().id())
            new_view.run_command('construct_tabs_list')


class ConstructTabsListCommand(sublime_plugin.TextCommand):
    """Constructs list of all open tabs in the view"""

    def run(self, edit):
        self.view.set_scratch(True)
        self.view.set_name(package_name)
        self.view.set_syntax_file(
            'Packages/TabTeleport/tabteleport.tmLanguage')

        tab_list = self._construct_list()

        self.view.insert(edit, 0, ''.join(tab_list + ['\n']))
        self._set_selection_on_first_line()

        settings = self.view.settings()
        settings.set('number_of_tabs', len(tab_list))

        self.view.window().focus_view(self.view)

        if 'Vintage' not in settings.get('ignored_packages'):
            self.view.run_command('exit_insert_mode')

    def _construct_list(self):
        tab_list = []

        if sublime.platform() == 'windows':
            basename = ntpath.basename
        else:
            basename = os.path.basename

        for tab_view in self.view.window().views():
            if tab_view.file_name() is not None:
                tab_list.append(
                    "{}\n{}\n\n".format(basename(tab_view.file_name()),
                                        tab_view.file_name()))

        return tab_list

    def _set_selection_on_first_line(self):
        point = self.view.text_point(0, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point)


class SwitchToTabCommand(sublime_plugin.TextCommand):
    """Handler which opens selected tab """

    def run(self, edit, **kwargs):
        self.view.window().open_file(kwargs['file_path'])


class BlowOutCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):
        pass


class TabTeleportKeyBindingListener(sublime_plugin.EventListener):

    def on_text_command(self, view, command_name, args):
        if view.name() == package_name:
            tab_list_nav = TabListNavigaton(view)

            if command_name == 'move' and args['by'] == 'lines':
                return tab_list_nav.move(forward=args['forward'])

            elif command_name == 'set_motion':
                if args.get('linewise'):
                    if args['motion_args']['by'] == 'lines':
                        return tab_list_nav.move(
                            forward=args['motion_args']['forward'])
                else:
                    return tab_list_nav.switch_to_tab()

            elif command_name == 'insert':
                return tab_list_nav.switch_to_tab()

            elif command_name in ['switch_to_tab', 'exit_insert_mode']:
                return None

            else:
                return ('blow_out_command', {})

    def on_deactivated(self, view):
        if view.name() == package_name:
            # GotoTab view has lost input focus
            view.close()


class TabListNavigaton:

    def __init__(self, view):
        self.view = view

    def switch_to_tab(self):
        selection_region = self.view.sel()[0]
        selected_row = self.view.rowcol(selection_region.a)[0]
        next_row_point = self.view.text_point(selected_row+1, 0)
        region_line = self.view.full_line(next_row_point)
        file_path = self.view.substr(region_line).strip().split(": ")[-1]
        return ('switch_to_tab', {'file_path': file_path})

    def move(self, forward):
        number_of_tabs = self.view.settings().get('number_of_tabs')
        selection_region = list(self.view.sel())[0]
        row = self.view.rowcol(selection_region.a)[0]

        if row == (number_of_tabs * 3 - 3) and forward:
            return ('blow_out_command', {})
        else:
            point = self.view.text_point(row + 2 if forward else row - 2, 0)
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(point))
