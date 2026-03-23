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

from pathlib import Path

import wx

from printrun.utils import imagefile


def make_button(parent, label, callback, tooltip, container = None, size = wx.DefaultSize, style = 0):
    button = wx.Button(parent, -1, label, style = style, size = size)
    button.Bind(wx.EVT_BUTTON, callback)
    button.SetToolTip(wx.ToolTip(tooltip))
    if container:
        container.Add(button)
    return button

def make_autosize_button(*args):
    return make_button(*args, size = (-1, -1), style = wx.BU_EXACTFIT)

def make_custom_button(root, parentpanel, i, style = 0):
    btn = make_button(parentpanel, i.label, root.process_button,
                      i.tooltip, style = style)
    btn.SetBackgroundColour(i.background)
    btn.SetForegroundColour("black")
    btn.properties = i
    root.btndict[i.command] = btn
    root.printerControls.append(btn)
    return btn


def get_scaled_icon(iconname: str, width: int, window: wx.Window,
                    iconbundle=None) -> wx.Icon:
    """
    Find the specified icon and scale it correctly without making it blurry.
    """
    sc = window.GetContentScaleFactor()
    final_w = int(width * sc)

    if not iconbundle:
        iconbundle = get_iconbundle(iconname)

    raw_icn = iconbundle.GetIcon((final_w, final_w),
                                 wx.IconBundle.FALLBACK_NEAREST_LARGER)

    ic_bmp = wx.Bitmap()
    ic_bmp.CopyFromIcon(raw_icn)
    if raw_icn.GetWidth() != final_w:
        ic_img = ic_bmp.ConvertToImage()
        ic_img.Rescale(final_w, final_w, wx.IMAGE_QUALITY_HIGH)
        ic_bmp = ic_img.ConvertToBitmap()
    ic_bmp.SetScaleFactor(sc)

    return wx.Icon(ic_bmp)


def get_iconbundle(iconname: str) -> wx.IconBundle:
    """
    Get a IconBundle of an application-icon with the specified name.
    If the icon cannot be found, an empty IconBundle is returned.
    """

    icons = wx.IconBundle()
    rel_path = Path("printrun", "assets", "icons", iconname)

    base_filename = iconname + "_32x32.png"
    png_file = imagefile(base_filename, rel_path)

    if not png_file.is_file():
        return icons

    pngs = png_file.parent.iterdir()
    for file in pngs:
        if file.suffix == ".png":
            icons.AddIcon(str(file), wx.BITMAP_TYPE_PNG)

    return icons


def toolbaricon(iconname: str) -> wx.BitmapBundle:
    """
    Get a BitmapBundle of a toolbar-icon with the specified name.
    If the icon cannot be found, an empty BitmapBundle is returned.
    """

    icons = wx.BitmapBundle()
    rel_path = Path("printrun", "assets", "toolbar")

    # On windows the application is light grey, even in 'dark mode',
    # therefore on windows we always use the dark icons on bright background.
    os_name = wx.PlatformInformation().Get().GetOperatingSystemFamilyName()
    if wx.SystemSettings.GetAppearance().IsDark() and os_name != "Windows":
        base_filename = iconname + "_w.svg"
    else:
        base_filename = iconname + ".svg"

    svg_path = imagefile(base_filename, rel_path)

    if not svg_path.is_file():
        return icons

    return icons.FromSVGFile(str(svg_path), (24, 24))
