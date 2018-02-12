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
from .stltool import stl, genfacet, emitstl
a = wx.App()

def genscape(data = [[0, 1, 0, 0], [1, 0, 2, 0], [1, 0, 0, 0], [0, 1, 0, 1]],
             pscale = 1.0, bheight = 1.0, zscale = 1.0):
    o = stl(None)
    datal = len(data)
    datah = len(data[0])
    # create bottom:
    bmidpoint = (pscale * (datal - 1) / 2.0, pscale * (datah - 1) / 2.0)
    # print range(datal), bmidpoint
    for i in list(zip(range(datal + 1)[:-1], range(datal + 1)[1:]))[:-1]:
        # print (pscale*i[0], pscale*i[1])
        o.facets += [[[0, 0, -1], [[0.0, pscale * i[0], 0.0], [0.0, pscale * i[1], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [[[0, 0, -1], [[2.0 * bmidpoint[1], pscale * i[1], 0.0], [2.0 * bmidpoint[1], pscale * i[0], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [genfacet([[0.0, pscale * i[0], data[i[0]][0] * zscale + bheight], [0.0, pscale * i[1], data[i[1]][0] * zscale + bheight], [0.0, pscale * i[1], 0.0]])]
        o.facets += [genfacet([[2.0 * bmidpoint[1], pscale * i[1], data[i[1]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[0], data[i[0]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[1], 0.0]])]
        o.facets += [genfacet([[0.0, pscale * i[0], data[i[0]][0] * zscale + bheight], [0.0, pscale * i[1], 0.0], [0.0, pscale * i[0], 0.0]])]
        o.facets += [genfacet([[2.0 * bmidpoint[1], pscale * i[1], 0.0], [2.0 * bmidpoint[1], pscale * i[0], data[i[0]][datah - 1] * zscale + bheight], [2.0 * bmidpoint[1], pscale * i[0], 0.0]])]
    for i in list(zip(range(datah + 1)[: - 1], range(datah + 1)[1:]))[: - 1]:
        # print (pscale * i[0], pscale * i[1])
        o.facets += [[[0, 0, -1], [[pscale * i[1], 0.0, 0.0], [pscale * i[0], 0.0, 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [[[0, 0, -1], [[pscale * i[0], 2.0 * bmidpoint[0], 0.0], [pscale * i[1], 2.0 * bmidpoint[0], 0.0], [bmidpoint[0], bmidpoint[1], 0.0]]]]
        o.facets += [genfacet([[pscale * i[1], 0.0, data[0][i[1]] * zscale + bheight], [pscale * i[0], 0.0, data[0][i[0]] * zscale + bheight], [pscale * i[1], 0.0, 0.0]])]
        o.facets += [genfacet([[pscale * i[0], 2.0 * bmidpoint[0], data[datal - 1][i[0]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], data[datal - 1][i[1]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], 0.0]])]
        o.facets += [genfacet([[pscale * i[1], 0.0, 0.0], [pscale * i[0], 0.0, data[0][i[0]] * zscale + bheight], [pscale * i[0], 0.0, 0.0]])]
        o.facets += [genfacet([[pscale * i[0], 2.0 * bmidpoint[0], data[datal - 1][i[0]] * zscale + bheight], [pscale * i[1], 2.0 * bmidpoint[0], 0.0], [pscale * i[0], 2.0 * bmidpoint[0], 0.0]])]
    for i in range(datah - 1):
        for j in range(datal - 1):
            o.facets += [genfacet([[pscale * i, pscale * j, data[j][i] * zscale + bheight], [pscale * (i + 1), pscale * (j), data[j][i + 1] * zscale + bheight], [pscale * (i + 1), pscale * (j + 1), data[j + 1][i + 1] * zscale + bheight]])]
            o.facets += [genfacet([[pscale * (i), pscale * (j + 1), data[j + 1][i] * zscale + bheight], [pscale * i, pscale * j, data[j][i] * zscale + bheight], [pscale * (i + 1), pscale * (j + 1), data[j + 1][i + 1] * zscale + bheight]])]
            # print o.facets[-1]
    return o
def zimage(name, out):
    i = wx.Image(name)
    s = i.GetSize()
    b = list(map(ord, i.GetData()[::3]))
    print(b)
    data = []
    for i in range(s[0]):
        data += [b[i * s[1]:(i + 1) * s[1]]]
    # data = [i[::5] for i in data[::5]]
    emitstl(out, genscape(data, zscale = 0.1).facets, name)

"""
class scapewin(wx.Frame):
    def __init__(self, size = (400, 530)):
        wx.Frame.__init__(self, None,
                          title = "Right-click to load an image", size = size)
        self.SetIcon(wx.Icon("plater.png", wx.BITMAP_TYPE_PNG))
        self.SetClientSize(size)
        self.panel = wx.Panel(self, size = size)


"""
if __name__ == '__main__':
    """
    app = wx.App(False)
    main = scapewin()
    main.Show()
    app.MainLoop()
"""
    zimage("catposthtmap2.jpg", "testobj.stl")
del a
