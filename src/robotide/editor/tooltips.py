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

from popupwindow import Tooltip


class GridToolTips(object):

    def __init__(self, grid):
        self._tooltip = Tooltip(grid, (250, 80), False, True)
        self._information_popup = Tooltip(grid, (450, 300))
        self._grid = grid
        self._tooltip_timer = wx.Timer(grid.GetGridWindow())
        grid.GetGridWindow().Bind(wx.EVT_MOTION, self.OnMouseMotion)
        grid.GetGridWindow().Bind(wx.EVT_TIMER, self.OnShowToolTip)

    def OnMouseMotion(self, event):
        self._hide_tooltip()
        self._tooltip_timer.Start(500, True)
        event.Skip()

    def OnShowToolTip(self, event):
        self._hide_tooltip()
        if not self._grid.has_focus():
            return
        content = self._grid.get_tooltip_content()
        if content:
            self._show_tooltip_at(content, self._calculate_tooltip_position())
            self._grid.SetFocus()

    def _show_tooltip_at(self, content, position):
        if not self._information_popup.IsShown():
            self._tooltip.set_content(content)
            self._tooltip.show_at(position)

    def _calculate_tooltip_position(self):
        x, y = wx.GetMousePosition()
        return x+5, y+5

    def _hide_tooltip(self):
        self._tooltip.hide()

    def hide_information(self):
        self._information_popup.hide()

    def hide(self):
        self._hide_tooltip()
        self.hide_information()

    def show_info_at(self, info, title, position):
        self._tooltip.hide()
        self._information_popup.set_content(info, title)
        self._information_popup.show_at(position)