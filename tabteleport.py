import sublime
import sublime_plugin
import os.path
import ntpath
import xml.sax.saxutils

from collections import namedtuple

package_name = 'TabTeleport'


class TabteleportCtrlTabCommand(sublime_plugin.WindowCommand):
    """Handler which manages Ctrl+Tab command"""

    def run(self):
        active_view = self.window.active_view()

        if active_view and active_view.name() == package_name:
            # Ctrl+Tab was pressed a second time on an open tabteleport view
            self._close_tabteleport_view()
        else:
            self._open_tabteleport_view()

    def _close_tabteleport_view(self):
        tabteleport_view = self.window.active_view()
        view_settings = tabteleport_view.settings()
        previous_view_id = view_settings.get('previous_view_id')

        for v in self.window.views():
            if v.id() == previous_view_id:
                previous_view = v
                break

        self.window.focus_view(previous_view)
        tabteleport_view.close()

    def _open_tabteleport_view(self):
        """Creates a new view, remembers which view was active and
        runs command to construct list of all open tabs in the view.
        """
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

        self._construct_list(edit)
        self._set_selection_on_first_line()
        self.view.window().focus_view(self.view)

        #settings = self.view.settings()
        #if 'Vintage' not in settings.get('ignored_packages'):
            #self.view.run_command('exit_insert_mode')

    def _construct_list(self, edit):
        # Holds information about tab in the constructed list.
        # We use it when user navigates around list and switches to
        # selected tab
        #   `line` - the line number identifies tab name position in
        #            constructed list.
        #   `order` - the order in the list
        #   `file_name` - tab name
        #   `view_id` - the unique identifier of the tab view
        # tabs = {'line': ('file_name', order, view_id), ...}
        tabs = {}

        # We use it to move up and down the list. Which tab name needs to
        # be highlighted when user navigates by the list
        order_list = []

        if sublime.platform() == 'windows':
            basename = ntpath.basename
        else:
            basename = os.path.basename

        order = 0
        list_data = '\n'
        line = 1
        temporal_views = []

        tab_data = namedtuple(
            'TabData',
            ['file_name', 'order', 'view_id', 'contents', 'file_type'])

        for tab_view in self.view.window().views():
            if tab_view.file_name() is not None:
                file_name = basename(tab_view.file_name())
                list_data += file_name + '\n'

                tabs[str(line)] = tab_data(
                    file_name=file_name, order=order, view_id=tab_view.id(),
                    contents='', file_type='regular')
                order_list.append((file_name, line))
                line += 1
                order += 1

                file_path = tab_view.file_name()
                list_data += file_path + '\n\n'
                line += 2

            elif tab_view.name() != package_name:
                temporal_views.append(tab_view)

        if temporal_views:
            title = ' Temporary Files '
            data = title.ljust(
                ((79 - len(title))//2) + len(title), '#').rjust(79, '#')
            list_data += data + '\n'
            line += 1

            title = ' use left or right arrow to see contents '
            data = title.ljust(
                ((79 - len(title))//2) + len(title), '#').rjust(79, '#')
            list_data +=  data + '\n\n'
            line += 2

            for ind, tab_view in enumerate(temporal_views, start=1):
                    view_contents = tab_view.substr(
                        sublime.Region(0, tab_view.size()))

                    if not view_contents.strip():
                        view_contents = 'Empty file'
                        file_name = 'temporary file %s' % ind
                        list_data += file_name + ': empty file' + '\n\n'
                    else:
                        file_name = 'temporary file %s' % ind
                        data = tab_view.substr(
                            sublime.Region(0, 79 - len(file_name) - 6))
                        data = data.replace('\n', ' ').rstrip()
                        list_data += file_name + ': ' + data + ' ...' + '\n\n'

                    tabs[str(line)] = tab_data(
                        file_name=file_name, order=order, view_id=tab_view.id(),
                        contents=(view_contents, 'closed'),
                        file_type='temporal')

                    order_list.append((file_name, line))
                    line += 2
                    order += 1

        self.view.insert(edit, 0, list_data)
        self.view.settings().set('tabs', tabs)
        self.view.settings().set('order_list', order_list)

    def _set_selection_on_first_line(self):
        point = self.view.text_point(1, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point)


class SwitchToTabCommand(sublime_plugin.TextCommand):
    """Handler which opens selected tab """

    def run(self, edit, **kwargs):
        for view in self.view.window().views():
            if view.id() == kwargs['view_id']:
                self.view.window().focus_view(view)
                break


class ShowFileContentsCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):
        selection_region = self.view.sel()[0]
        selected_row = self.view.rowcol(selection_region.a)[0]
        tabs = self.view.settings().get('tabs')

        if tabs[str(selected_row)][-1] == 'temporal':

            if tabs[str(selected_row)][-2][1] == 'closed':
                contents = tabs[str(selected_row)][-2][0]
                contents = xml.sax.saxutils.escape(contents)
                contents = contents.replace('\n', '<br>')
                self.view.show_popup(contents, max_width=800)
                tabs[str(selected_row)][-2][1] = 'open'
                self.view.settings().set('tabs', tabs)

            else:
                self.view.hide_popup()
                tabs[str(selected_row)][-2][1] = 'closed'
                self.view.settings().set('tabs', tabs)


class ExtinguishExecutionCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):
        pass


class TabTeleportKeyBindingListener(sublime_plugin.EventListener):

    def on_text_command(self, view, command_name, args):
        if view.name() == package_name:
            tab_list_nav = TabListNavigaton(view)

            if command_name == 'move' and args['by'] == 'lines':
                return tab_list_nav.move(forward=args['forward'])

            elif command_name == 'move' and args['by'] == 'characters':
                return ('show_file_contents', {})

            elif command_name == 'set_motion':
                if args.get('linewise'):
                    if args['motion_args'].get('by') == 'lines':
                        return tab_list_nav.move(
                            forward=args['motion_args']['forward'])
                    else:
                        return ('extinguish_execution', {})
                else:
                    return tab_list_nav.switch_to_tab()

            elif command_name == 'insert':
                return tab_list_nav.switch_to_tab()

            elif command_name in ['switch_to_tab', 'exit_insert_mode',
                                  'show_file_contents']:
                return None

            else:
                return ('extinguish_execution', {})

    def on_deactivated(self, view):
        if view.name() == package_name:
            # GotoTab view has lost input focus
            view.close()


class TabListNavigaton:

    def __init__(self, view):
        self.view = view

    def switch_to_tab(self):
        line_num = self._get_line_number_under_sel()
        tabs = self.view.settings().get('tabs')
        return ('switch_to_tab', {'view_id': tabs[str(line_num)][2]})

    def move(self, forward):
        tabs = self.view.settings().get('tabs')
        order_list = self.view.settings().get('order_list')

        line_num = self._get_line_number_under_sel()
        order = tabs[str(line_num)][1]

        last_item = False
        if forward:
            if (order + 1) > (len(order_list) - 1):
                point = self.view.text_point(0, 0)
            else:
                next_line_num = order_list[order+1][1]
                point = self.view.text_point(next_line_num-1, 0)

            if (order + 1) == (len(order_list) - 1):
                last_item = True
        else:
            if (order - 1) < 0:
                next_line_num = order_list[-1][1]
                point = self.view.text_point(next_line_num + 1, 0)
            else:
                next_line_num = order_list[order-1][1]
                point = self.view.text_point(next_line_num + 1, 0)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        self.view.show(point, show_surrounds=True)

        if last_item:
            layout_height = self.view.layout_extent()[1]
            viewport_height = self.view.viewport_extent()[1]
            if layout_height > viewport_height:
                new_pos = self.view.viewport_position()
                self.view.set_viewport_position((new_pos[0], new_pos[1] + 200))

    def _get_line_number_under_sel(self):
        selection_region = self.view.sel()[0]
        selected_row = self.view.rowcol(selection_region.a)[0]
        return selected_row

