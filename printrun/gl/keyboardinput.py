# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx

# for type hints
from typing import Callable, TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from .panel import wxGLPanel


KEYS = {'zoom_in': (wx.WXK_PAGEDOWN, wx.WXK_RIGHT, ord('+'), ord('='), 388),
        'zoom_out': (wx.WXK_PAGEUP, wx.WXK_LEFT, ord('-'), 390),
        'fit': (ord('F'), ),
        'reset': (ord('R'), ),
        'layerup': (ord('U'), ord('E'), wx.WXK_UP),
        'layerdown': (ord('D'), wx.WXK_DOWN),
        'currentlayer': (ord('C'), ),
       }

class KeyboardInput():
    def __init__(self, canvas: 'wxGLPanel', zoom_fn: Callable,
                 fit_fn: Callable, reset_fn: Callable) -> None:

        self.canvas = canvas
        self.canvas.Bind(wx.EVT_KEY_DOWN, self.keypress)

        # Standart features
        self.zoom = zoom_fn
        self.fit = fit_fn
        self.resetview = reset_fn

        # Optional featuress
        self.layer_up = self.dummy_fn
        self.layer_down = self.dummy_fn
        self.current_layer = self.dummy_fn

    def dummy_fn(self) -> None:
        '''Empty placeholder method'''
        return

    def keypress(self, event: wx.KeyEvent) -> None:
        """gets keypress events and moves/rotates active shape"""
        mods = event.GetModifiers()
        if mods == wx.MOD_ALT:
            # Let alt + c bubble up
            event.Skip()
            return

        if mods in (wx.MOD_CONTROL, wx.MOD_SHIFT):
            zoom_step = 1.05
        else:
            zoom_step = 1.1

        keycode = event.GetUnicodeKey()
        if keycode == wx.WXK_NONE:
            keycode = event.GetKeyCode()

        if keycode in KEYS['zoom_in']:
            self.zoom(zoom_step)

        elif keycode in KEYS['zoom_out']:
            self.zoom(1 / zoom_step)

        elif keycode in KEYS['fit']:
            self.fit()

        elif keycode in KEYS['reset']:
            self.resetview()

        elif keycode in KEYS['layerup']:
            self.layer_up()

        elif keycode in KEYS['layerdown']:
            self.layer_down()

        elif keycode in KEYS['currentlayer']:
            self.current_layer()

        event.Skip()
        wx.CallAfter(self.canvas.Refresh)

    def register(self, layerup: Optional[Callable] = None,
                 layerdown: Optional[Callable] = None,
                 currentlayer: Optional[Callable] = None) -> None:

        if layerup:
            self.layer_up = layerup

        if layerdown:
            self.layer_down = layerdown

        if currentlayer:
            self.current_layer = currentlayer


if __name__ == '__main__':
    pass

