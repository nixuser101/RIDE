#  Copyright 2008-2009 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import wx

from robotide import context
from robotide.model.settings import ResourceImport
from robotide.utils import RideEventHandler, RideHtmlWindow, ButtonWithHandler
from robotide import utils

from kweditor import KeywordEditor
from listeditor import ListEditor
from editordialogs import EditorDialog, DocumentationDialog,\
    ScalarVariableDialog, ListVariableDialog, LibraryImportDialog,\
    ResourceImportDialog, VariablesImportDialog, MetadataDialog


def Editor(plugin, editor_panel, tree):
    controller = plugin.get_selected_item()
    if not controller:
        return WelcomePage(editor_panel)
    editor_class = plugin.get_editor(controller.data.__class__)
    return editor_class(plugin, editor_panel, controller, tree)


class WelcomePage(RideHtmlWindow):
    undo = cut = copy = paste = delete = comment = uncomment = save \
        = show_content_assist = lambda self: None

    def __init__(self, parent):
        RideHtmlWindow.__init__(self, parent, text=context.ABOUT_RIDE)

    def close(self):
        self.Show(False)


class EditorPanel(wx.Panel):
    """Base class for all editor panels"""
    # TODO: Move outside default editor package, document
    name = doc = ''
    title = None
    undo = cut = copy = paste = delete = comment = uncomment = save \
        = show_content_assist = lambda self: None

    def __init__(self, plugin, parent, controller, tree):
        wx.Panel.__init__(self, parent)
        self.plugin = plugin
        self.controller = controller
        self._tree = tree


class _RobotTableEditor(EditorPanel):
    name = 'table'
    doc = 'table editor'

    def __init__(self, plugin, parent, controller, tree):
        EditorPanel.__init__(self, plugin, parent, controller, tree)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        if self.title:
            self.sizer.Add(self._create_header(self.title), 0, wx.ALL, 5)
            self.sizer.Add((0,10))
        self._populate()

    def close(self):
        self.Show(False)

    def _create_header(self, text):
        header = wx.StaticText(self, -1, text)
        header.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
        return header

    def _add_settings(self):
        for setting in self.controller.settings:
            editor = setting.editor(self, setting, self.plugin, self._tree)
            self.sizer.Add(editor, 0, wx.ALL|wx.EXPAND, 1)


class ResourceFileEditor(_RobotTableEditor):

    def _populate(self):
        datafile = self.controller.data
        self.sizer.Add(self._create_header(datafile.name), 0, wx.ALL, 5)
        self.sizer.Add(self._create_source_label(datafile.source), 0, wx.ALL, 1)
        self.sizer.Add((0, 10))
        self._add_settings()
        self._add_import_settings()
        self._add_variable_table()

    def _create_source_label(self, source):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add((5,0))
        sizer.Add(wx.StaticText(self, label='Source',
                                size=(context.SETTING_LABEL_WIDTH,
                                      context.SETTING_ROW_HEIGTH)))
        sizer.Add(wx.StaticText(self, label=source))
        return sizer

    def _add_import_settings(self):
        editor = ImportSettingListEditor(self, self._tree, self.controller.imports)
        self.sizer.Add(editor, 1, wx.EXPAND)

    def _add_variable_table(self):
        editor = VariablesListEditor(self, self._tree, self.controller.variables)
        self.sizer.Add(editor, 1, wx.EXPAND)


class TestCaseFileEditor(ResourceFileEditor):

    def _populate(self):
        ResourceFileEditor._populate(self)
        self.sizer.Add((0, 10))
        self._add_metadata()

    def _add_metadata(self):
        editor = MetadataListEditor(self, self._tree, self.controller.metadata)
        self.sizer.Add(editor, 1, wx.EXPAND)


class InitFileEditor(TestCaseFileEditor):
    pass


class SettingEditor(wx.Panel, RideEventHandler):

    def __init__(self, parent, controller, plugin, tree):
        wx.Panel.__init__(self, parent)
        self._controller = controller
        self._plugin = plugin
        self._datafile = controller.datafile
        self._create_controls()
        self._dialog = EditorDialog(controller)
        self._tree = tree
        self._editing = False

    def _create_controls(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add((5,0))
        sizer.Add(wx.StaticText(self, label=self._controller.label,
                                size=(context.SETTING_LABEL_WIDTH,
                                      context.SETTING_ROW_HEIGTH)))
        self._value_display = self._get_value_display()
        self._update_value()
        sizer.Add(self._value_display, 1, wx.EXPAND)
        sizer.Add(ButtonWithHandler(self, 'Edit'), flag=wx.LEFT|wx.RIGHT, border=5)
        sizer.Add(ButtonWithHandler(self, 'Clear'))
        sizer.Layout()
        self.SetSizer(sizer)

    def _get_value_display(self):
        display = wx.TextCtrl(self, size=(-1, context.SETTING_ROW_HEIGTH))
        display.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        display.SetEditable(False)
        return display

    def refresh_datafile(self, item, event):
        self._tree.refresh_datafile(item, event)

    def OnEdit(self, event=None):
        self._editing = True
        dlg = self._dialog(self.GetGrandParent(), self._datafile, self._plugin,
                           self._controller)
        if dlg.ShowModal() == wx.ID_OK:
            self._controller.set_value(dlg.get_value())
            self._update_and_notify()
        dlg.Destroy()
        self._editing = False

    def OnLeftUp(self, event):
        selection = self._value_display.GetSelection()
        if selection[0] == selection[1] and not self._editing:
            wx.CallAfter(self.OnEdit, event)
        event.Skip()

    def _update_and_notify(self):
        self._update_value()
        self._tree.mark_dirty(self._controller)

    def OnClear(self, event):
        self._controller.clear()
        self._update_and_notify()

    def _update_value(self):
        if self._controller.is_set:
            self._value_display.SetBackgroundColour('white')
            self._value_display.SetValue(self._controller.value)
        else:
            self._value_display.Clear()
            self._value_display.SetBackgroundColour('light grey')

    def get_selected_datafile(self):
        return self._datafile


class DocumentationEditor(SettingEditor):

    def __init__(self, parent, controller, plugin, tree):
        wx.Panel.__init__(self, parent)
        self._controller = controller
        self._plugin = plugin
        self._datafile = controller.datafile
        self._tree = tree
        self._create_controls()

    def _get_value_display(self):
        display = RideHtmlWindow(self, (-1, 60))
        display.Bind(wx.EVT_LEFT_DOWN, self.OnEdit)
        return display

    def _update_value(self):
        value = self._controller.value
        self._value_display.SetPage(utils.html_escape(value, formatting=True))

    def OnEdit(self, event):
        editor = DocumentationDialog(self.GetGrandParent(), self._datafile,
                                     self._plugin, self._controller.value)
        if editor.ShowModal() == wx.ID_OK:
            self._controller.set_value(editor.get_value())
            self._update_and_notify()
        editor.Destroy()

    def OnClear(self, event):
        self._item.clear()
        self._update_and_notify()


class TestCaseEditor(_RobotTableEditor):

    def _populate(self):
        self.header = self._create_header(self.controller.name)
        self.sizer.Add(self.header, 0, wx.ALL, 5)
        self._add_settings()
        self.sizer.Add((0,10))
        self._create_kweditor()

    def _create_add_buttons(self, kweditor):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(ButtonWithHandler(self, 'Add Row', kweditor.OnInsertRows),
                                    0, wx.ALL, 2)
        sizer.Add(ButtonWithHandler(self, 'Add Column', kweditor.OnInsertCol),
                                    0, wx.ALL, 2)
        self.sizer.Add(sizer)

    def _create_kweditor(self):
        self.kweditor = KeywordEditor(self, self.controller, self._tree)
        self._create_add_buttons(self.kweditor)
        self.sizer.Add(self.kweditor, 1, wx.EXPAND|wx.ALL, 2)

    def Show(self, show):
        if hasattr(self, 'kweditor') and not show:
            self.kweditor.hide_popup()
        wx.Panel.Show(self, show)

    def close(self):
        _RobotTableEditor.close(self)
        self.kweditor.save()

    def save(self):
        self.kweditor.save()

    def undo(self):
        self.kweditor.OnUndo()

    def cut(self):
        self.kweditor.OnCut()

    def copy(self):
        self.kweditor.OnCopy()

    def paste(self):
        self.kweditor.OnPaste()

    def delete(self):
        self.kweditor.OnDelete()

    def comment(self):
        self.kweditor.comment()

    def uncomment(self):
        self.kweditor.uncomment()

    def show_content_assist(self):
        self.kweditor.show_content_assist()

    def view(self):
        _RobotTableEditor.view(self)
        self.kweditor.SetFocus()


class UserKeywordEditor(TestCaseEditor): pass


class _AbstractListEditor(ListEditor, RideEventHandler):

    def __init__(self, parent, tree, data):
        ListEditor.__init__(self, parent, self._titles, data)
        self._datafile = data.datafile
        self._tree = tree

    def get_selected_datafile(self):
        return self._datafile

    def refresh_datafile(self, item, event):
        self._tree.refresh_datafile(item, event)

    def update_data(self):
        ListEditor.update_data(self)
        self._tree.mark_dirty(self._datafile)


class VariablesListEditor(_AbstractListEditor):
    _titles = ['Variable', 'Value']
    _buttons = ['Add Scalar', 'Add List']

    def get_column_values(self, item):
        return [item.name, item.value if isinstance(item.value, basestring)
                            else ' | '.join(item.value)]

    def OnAddScalar(self, event):
        dlg = ScalarVariableDialog(self.GetGrandParent(), self._data.datafile)
        if dlg.ShowModal() == wx.ID_OK:
            self._data.new_scalar_var(*dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def OnAddList(self, event):
        dlg = ListVariableDialog(self.GetGrandParent(), self._data.datafile)
        if dlg.ShowModal() == wx.ID_OK:
            self._data.new_list_var(*dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def OnEdit(self, event):
        item = self._data.get_name_and_value(self._selection)
        if item[0].startswith('${'):
            dlg = ScalarVariableDialog(self.GetGrandParent(),
                                       self._data.datafile, item=item)
        else:
            dlg = ListVariableDialog(self.GetGrandParent(),
                                     self._data.datafile, item=item)
        if dlg.ShowModal() == wx.ID_OK:
            self._data.set_name_and_value(self._selection, *dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def update_data(self):
        self._list.DeleteAllItems()
        self._list.insert_data([(var.name, var.value) for var in self._data])
        self._tree.mark_dirty(self._datafile)


class ImportSettingListEditor(_AbstractListEditor):
    _titles = ['Import', 'Name / Path', 'Arguments']
    _buttons = ['Add Library', 'Add Resource', 'Add Variables']

    def OnEdit(self, event):
        setting = self._get_setting()
        dlg = EditorDialog(setting)(self.GetGrandParent(), self._data.datafile,
                                    item=setting)
        if dlg.ShowModal() == wx.ID_OK:
            setting.set_str_value(dlg.get_value())
            self.update_data()
            if self._resource_import_modified():
                self._data.resource_updated(self._selection)
        dlg.Destroy()

    def OnAddLibrary(self, event):
        self._show_import_editor_dialog(LibraryImportDialog,
                                        self._data.new_library)

    def OnAddResource(self, event):
        self._show_import_editor_dialog(ResourceImportDialog,
                                        self._data.new_resource)

    def OnAddVariables(self, event):
        self._show_import_editor_dialog(VariablesImportDialog,
                                        self._data.new_variables)

    def _show_import_editor_dialog(self, dialog, creator):
        dlg = dialog(self.GetGrandParent(), self._data.datafile)
        if dlg.ShowModal() == wx.ID_OK:
            creator(dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def get_column_values(self, item):
        return [item.type, item.name, utils.join_value(item.args)]

    def _resource_import_modified(self):
        return self._get_setting().__class__ == ResourceImport

    def _get_setting(self):
        return self._data[self._selection]


class MetadataListEditor(_AbstractListEditor):
    _titles = ['Metadata', 'Value']
    _buttons = ['Add Metadata']
    _sortable = False

    def OnEdit(self, event):
        meta = self._data[self._selection]
        dlg = MetadataDialog(self.GetGrandParent(), self._data.datafile,
                             item=meta)
        if dlg.ShowModal() == wx.ID_OK:
            meta.set_name_and_value(*dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def OnAddMetadata(self, event):
        dlg = MetadataDialog(self.GetGrandParent(), self._data.datafile)
        if dlg.ShowModal() == wx.ID_OK:
            self._data.new_metadata(*dlg.get_value())
            self.update_data()
        dlg.Destroy()

    def get_column_values(self, item):
        return [item.name, utils.html_escape(item.value)]
