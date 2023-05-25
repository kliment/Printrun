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
#
# Copyright 2017 Rock Storm <rockstorm@gmx.com>

import wx
from printrun.gui.widgets import get_space
from printrun.utils import install_locale
install_locale('pronterface')
# Set up Internationalization using gettext

class SpoolManagerMainWindow(wx.Frame):
    """
    Front-end for the Spool Manager.

    Main window which displays the currently loaded spools and the list of
    recorded ones with buttons to add, load, edit or delete them.
    """

    def __init__(self, parent, spool_manager):
        wx.Frame.__init__(self, parent,
                          title = _("Spool Manager"),
                          style = wx.DEFAULT_FRAME_STYLE)

        # An empty wx.Frame has a darker background on win, but filled with a panel it looks native
        self.panel = wx.Panel(self, -1)

        self.SetIcon(parent.GetIcon())

        # Initiate the back-end
        self.spool_manager = spool_manager
        self.spool_manager.refresh()

        # Generate the dialogs showing the current spools
        self.current_spools_dialog = CurrentSpoolDialog(self.panel,
                                                        self.spool_manager)

        # Check if any spools are loaded on non-exisiting extruders
        for spool in self.spool_manager.getSpoolList():
            if self.spool_manager.isLoaded(spool[0]) > (spool_manager.getExtruderCount() - 1):
                spool_manager.unload(self.spool_manager.isLoaded(spool[0]))

        # Generate the list of recorded spools
        self.spool_list = SpoolListView(self.panel, self.spool_manager)

        # Generate the buttons
        self.panel.new_button = wx.Button(self.panel, wx.ID_ADD)
        self.panel.new_button.SetToolTip(_("Add a new spool"))
        self.panel.edit_button = wx.Button(self.panel, wx.ID_EDIT)
        self.panel.edit_button.SetToolTip(_("Edit the selected spool"))
        self.panel.edit_button.Disable()
        self.panel.delete_button = wx.Button(self.panel, wx.ID_DELETE)
        self.panel.delete_button.SetToolTip(_("Delete the selected spool"))
        self.panel.delete_button.Disable()

        # Instead of a real statusbar, a virtual statusbar is combined with the close button
        self.statusbar = wx.StaticText(self.panel, -1, "", style = wx.ST_ELLIPSIZE_END)
        statusfont = wx.Font(self.statusbar.GetFont())
        statusfont.MakeSmaller()
        self.statusbar.SetFont(statusfont)

        self.close_button = wx.Button(self.panel, wx.ID_CLOSE)
        self.bottom_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bottom_button_sizer.Add(self.statusbar, 1, wx.ALIGN_CENTER_VERTICAL)
        self.bottom_button_sizer.Add(self.close_button, 0, wx.ALIGN_CENTER_VERTICAL)

        # "Program" the buttons
        self.panel.new_button.Bind(wx.EVT_BUTTON, self.onClickAdd)
        self.panel.edit_button.Bind(wx.EVT_BUTTON, self.onClickEdit)
        self.panel.delete_button.Bind(wx.EVT_BUTTON, self.onClickDelete)

        self.close_button.Bind(wx.EVT_BUTTON, self.onClickClose)

        # Layout
        ## Group the buttons
        self.list_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_button_sizer.Add(self.panel.new_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT | wx.BOTTOM, get_space('minor'))
        self.list_button_sizer.Add(self.panel.edit_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT | wx.BOTTOM, get_space('minor'))
        self.list_button_sizer.Add(self.panel.delete_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT, get_space('minor'))

        ## Group the buttons with the spool list
        self.list_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel, label = _("Spool List"))
        self.list_sizer.Add(self.spool_list, 1,
                            wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, get_space('staticbox'))
        self.list_sizer.Add(self.list_button_sizer, 0,
                            wx.ALIGN_TOP | wx.TOP | wx.RIGHT, get_space('staticbox'))

        ## Layout the whole thing
        widgetsizer = wx.BoxSizer(wx.VERTICAL)
        widgetsizer.Add(self.list_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, get_space('minor'))
        widgetsizer.Add(self.current_spools_dialog, 0,
                        wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, get_space('minor'))
        widgetsizer.Add(wx.StaticLine(self.panel, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        widgetsizer.Add(self.bottom_button_sizer, 0, wx.EXPAND | wx.ALL, get_space('stddlg-frame'))

        ## Make sure the frame has the right size when it opens, but can still be resized
        self.panel.SetSizer(widgetsizer)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(self.panel, -1, wx.EXPAND)
        self.SetSizer(topsizer)
        self.SetMinClientSize(self.panel.GetEffectiveMinSize())
        self.Fit()
        self.CentreOnParent()

    def onClickAdd(self, event):
        """Open the window for customizing the new spool."""
        SpoolManagerAddWindow(self).ShowModal()

    def onClickLoad(self, event, extruder):
        """Load the selected spool to the correspondent extruder."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1:
            self.statusbar.SetLabel(
                _("Could not load the spool. No spool selected."))
            return
        spool_name = self.spool_list.GetItemText(spool_index)
        self.statusbar.SetLabel("")

        # If selected spool is already loaded, do nothing
        spool_extruder = self.spool_manager.isLoaded(spool_name)
        if spool_extruder > -1:
            self.statusbar.SetLabel(
                _("Spool '%s' is already loaded for Extruder %d.") %
                (spool_name, spool_extruder))
            self.Layout()  # Layout() is needed to ellipsize possible overlength status
            return

        # Load the selected spool and refresh the current spools dialog
        self.spool_manager.load(spool_name, extruder)
        self.current_spools_dialog.refreshDialog(self.spool_manager)
        self.current_spools_dialog.unload_button[extruder].Enable()
        self.statusbar.SetLabel(
            _("Loaded spool '%s' for Extruder %d.") % (spool_name, extruder))
        self.Layout()  # Layout() is needed to ellipsize possible overlength status

    def onClickUnload(self, event, extruder):
        """Unload the spool from the correspondent extruder."""

        spool_name = self.spool_manager.getSpoolName(extruder)
        if spool_name is not None:
            self.spool_manager.unload(extruder)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetLabel(
                _("Unloaded spool from Extruder %d.") % extruder)
            self.current_spools_dialog.unload_button[extruder].Disable()
        else:
            self.statusbar.SetLabel(
                _("There is no spool loaded for Extruder %d.") % extruder)

    def onClickEdit(self, event):
        """Open the window for editing the data of the selected spool."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1:
            self.statusbar.SetLabel(
                _("Could not edit the spool. No spool selected."))
            return

        # Open the edit window
        spool_name = self.spool_list.GetItemText(spool_index)
        spool_length = self.spool_list.GetItemText(spool_index, 1)
        SpoolManagerEditWindow(self, spool_name, spool_length).ShowModal()
        self.statusbar.SetLabel("")

    def onClickDelete(self, event):
        """Delete the selected spool."""

        # Get the selected spool
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1:
            self.statusbar.SetLabel(
                _("Could not delete the spool. No spool selected."))
            return
        spool_name = self.spool_list.GetItemText(spool_index)
        self.statusbar.SetLabel("")

        # Ask confirmation for deleting
        delete_dialog = wx.MessageDialog(self,
                                         message = _("Are you sure you want to delete the '%s' spool?") %
                                         spool_name, caption = _("Delete Spool"),
                                         style = wx.YES_NO | wx.ICON_EXCLAMATION)

        if delete_dialog.ShowModal() == wx.ID_YES:
            # Remove spool
            self.spool_manager.remove(spool_name)
            self.spool_list.refreshList(self.spool_manager)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetLabel(
                _("Deleted spool '%s'.") % spool_name)

    def onClickClose(self, event):
        self.Destroy()

class SpoolListView(wx.ListView):
    """
    Custom wxListView object which visualizes the list of available spools.
    """

    def __init__(self, parent, spool_manager):
        wx.ListView.__init__(self, parent,
                             style = wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.InsertColumn(0, _("Spool"), width = wx.LIST_AUTOSIZE_USEHEADER)
        self.InsertColumn(1, _("Filament"), width = wx.LIST_AUTOSIZE_USEHEADER)
        self.populateList(spool_manager)

        # "Program" the layout
        self.Bind(wx.EVT_SIZE, self.onResizeList)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onItemSelect)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onItemDeselect)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self.onItemDeselect)
        self.Bind(wx.EVT_LIST_INSERT_ITEM, self.onItemDeselect)

    def populateList(self, spool_manager):
        """Get the list of recorded spools from the Spool Manager."""
        spool_list = spool_manager.getSpoolList()
        for spool in spool_list:
            spool[1] = str(spool[1]) + " mm"
            self.Append(spool)

    def refreshList(self, spool_manager):
        """Refresh the list by re-reading the Spool Manager list."""
        self.DeleteAllItems()
        self.populateList(spool_manager)

    def onResizeList(self, event):
        list_size = self.GetSize()
        self.SetColumnWidth(1, -2)
        filament_column_width = self.GetColumnWidth(1)
        self.SetColumnWidth(col = 0,
                            width = list_size.width - filament_column_width)
        event.Skip()

    def onItemSelect(self, event):
        self.Parent.edit_button.Enable()
        self.Parent.delete_button.Enable()

    def onItemDeselect(self, event):
        self.Parent.edit_button.Disable()
        self.Parent.delete_button.Disable()

class CurrentSpoolDialog(wx.Panel):
    """
    Custom wxStaticText object to display the currently loaded spools and
    their remaining filament.
    """

    def __init__(self, parent, spool_manager):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.extruders = spool_manager.getExtruderCount()
        # If the settings file has no entry, at least 1 extruder will be set
        if not self.extruders:
            self.extruders = 1

        csd_sizer = wx.BoxSizer(wx.VERTICAL)

        # Calculate the minimum size needed to properly display the
        # extruder information
        min_size = self.GetTextExtent("Default Very Long Spool Name")

        # Generate a dialog for every extruder
        self.extruder_dialog = []
        load_button = []
        self.unload_button = []
        button_sizer = []
        dialog_sizer = []
        for i in range(self.extruders):
            # Generate the dialog with the spool information
            textlabel = wx.StaticText(self, label = _("Name:\nRemaining filament:"),
                                      style = wx.ALIGN_RIGHT)
            self.extruder_dialog.append(
                wx.StaticText(self, style = wx.ST_ELLIPSIZE_END))
            self.extruder_dialog[i].SetMinSize(wx.Size(min_size.width, -1))

            # Generate the "load" and "unload" buttons
            load_button.append(wx.Button(self, label = _("Load")))
            load_button[i].SetToolTip(
                _("Load selected spool for Extruder %d") % i)
            self.unload_button.append(wx.Button(self, label = _("Unload")))
            self.unload_button[i].Disable()
            self.unload_button[i].SetToolTip(
                _("Unload the spool for Extruder %d") % i)

            # "Program" the buttons
            load_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.Parent.onClickLoad(event, extruder))
            self.unload_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.Parent.onClickUnload(event, extruder))

            # Layout
            button_sizer.append(wx.BoxSizer(wx.HORIZONTAL))
            button_sizer[i].Add(load_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, get_space('minor'))
            button_sizer[i].Add(self.unload_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER)

            dialog_sizer.append(wx.StaticBoxSizer(wx.HORIZONTAL,
                                                  self, label = _("Spool for Extruder %d:") % i))
            dialog_sizer[i].Add(textlabel, 0, wx.ALIGN_TOP | wx.ALL, get_space('staticbox'))
            dialog_sizer[i].AddSpacer(get_space('minor'))
            dialog_sizer[i].Add(self.extruder_dialog[i], 1, wx.ALIGN_TOP | wx.TOP, get_space('staticbox'))
            dialog_sizer[i].AddSpacer(get_space('major'))
            dialog_sizer[i].Add(button_sizer[i], 0, wx.EXPAND | wx.RIGHT, get_space('staticbox'))

            csd_sizer.Add(dialog_sizer[i], 0, wx.EXPAND | wx.TOP, get_space('minor'))

        self.refreshDialog(spool_manager)

        self.SetSizerAndFit(csd_sizer)

    def refreshDialog(self, spool_manager):
        """Retrieve the current spools from the Spool Manager."""

        for i in range(self.extruders):
            spool_name = spool_manager.getSpoolName(i)
            if spool_name is not None:
                self.unload_button[i].Enable()
            else:
                self.unload_button[i].Disable()
            spool_filament = spool_manager.getRemainingFilament(i)
            label = ("%s\n" % spool_name +
                     "%.2f mm" % spool_filament)
            self.extruder_dialog[i].SetLabelText(label)


# ---------------------------------------------------------------------------
def checkOverwrite(parent, spool_name):
    """Ask the user whether or not to overwrite the existing spool."""

    overwrite_dialog = wx.MessageDialog(parent,
        message = _("A spool with the name '%s'' already exists.") %
            spool_name +
            _("Do you wish to overwrite it?"),
            caption = _("Overwrite"),
            style = wx.YES_NO | wx.ICON_EXCLAMATION)

    return overwrite_dialog.ShowModal() == wx.ID_YES


def getFloat(parent, number):
    """
    Check whether the input number is a float. Either return the number or
    return False.
    """
    if ',' in number:
        parent.parent.statusbar.SetLabel(_("Value contains a comma, please use a point for decimal values: %s") % number)
        parent.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
        return False

    try:
        return float(number)
    except ValueError:
        parent.parent.statusbar.SetLabel(_("Unrecognized number: %s") % number)
        parent.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
        return False

# ---------------------------------------------------------------------------
class SpoolManagerAddWindow(wx.Dialog):
    """Window for adding spools."""

    def __init__(self, parent):

        wx.Dialog.__init__(self, parent,
                           title = _("Add Spool"),
                           style = wx.DEFAULT_DIALOG_STYLE)

        self.parent = parent

        self.SetIcon(parent.GetIcon())

        # Generate the dialogs
        # The wx.TextCtrl variabels need to be declared before the loop, empty
        self.name_dialog = wx.TextCtrl(self, -1)
        self.diameter_dialog = wx.TextCtrl(self, -1)
        self.weight_dialog = wx.TextCtrl(self, -1)
        self.density_dialog = wx.TextCtrl(self, -1)
        self.length_dialog = wx.TextCtrl(self, -1)

        # The list contains field-description, textctrl value, default value, unit, tooltip;
        name_dlg = [_("Name:"), self.name_dialog, _("Default Spool"), "", ""]
        diameter_dlg = [_("Diameter:"), self.diameter_dialog, "1.75", "mm",
                        _("Typically, either 1.75 mm or 2.85 mm")]
        weight_dlg = [_("Weight:"), self.weight_dialog, "1.0", "kg", ""]
        density_dlg = [_("Density:"), self.density_dialog, "1.25", "g/cm^3",
                       _("Typical densities are 1.25 g/cm^3 for PLA,\n1.27 g/cm^3 for PETG or 1.08 g/cm^3 for ABS")]
        length_dlg = [_("Length:"), self.length_dialog, "332601.35", "mm", ""]
        dialog_list = [name_dlg, diameter_dlg, weight_dlg, density_dlg, length_dlg]

        minwidth = self.GetTextExtent('Default Long Spool Name').width
        grid = wx.FlexGridSizer(rows = 0, cols = 3, hgap = get_space('minor'), vgap = get_space('minor'))

        for dialog in dialog_list:
            # Add a field-description label
            grid.Add(wx.StaticText(self, -1, dialog[0], size = (-1, -1)), 0,
                     wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
            # Give the TextCtrl the right value
            dialog[1].ChangeValue(dialog[2])
            dialog[1].SetMinSize((minwidth, -1))
            # Add a tooltip
            if dialog[4] != "":
                dialog[1].SetToolTip(dialog[4])
            grid.Add(dialog[1])
            # Add a label for the unit
            if dialog[3] == "":
                grid.Add((0, 0))
            else:
                grid.Add(wx.StaticText(self, -1, dialog[3], size = (-1, -1)), 0, wx.ALIGN_CENTER_VERTICAL)

        # "Program" the dialogs
        self.diameter_dialog.Bind(wx.EVT_TEXT, self.calculateLength)
        self.weight_dialog.Bind(wx.EVT_TEXT, self.calculateLength)
        self.density_dialog.Bind(wx.EVT_TEXT, self.calculateLength)
        self.length_dialog.Bind(wx.EVT_TEXT, self.calculateWeight)

        # Generate the bottom buttons
        self.add_button = wx.Button(self, wx.ID_ADD)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        # "Program" the bottom buttons
        self.add_button.Bind(wx.EVT_BUTTON, self.onClickAdd)
        self.add_button.SetDefault()
        self.SetAffirmativeId(wx.ID_ADD)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)

        # Layout
        ## Setup the bottom buttons
        self.bottom_buttons_sizer = wx.StdDialogButtonSizer()
        self.bottom_buttons_sizer.SetAffirmativeButton(self.add_button)
        self.bottom_buttons_sizer.AddButton(self.cancel_button)

        self.bottom_buttons_sizer.Realize()

        ## Group the whole window
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(grid, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, get_space('major'))
        self.topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0,
                          wx.EXPAND | wx.TOP, get_space('minor'))
        self.topsizer.Add(self.bottom_buttons_sizer, 0,
                          wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))

        self.SetSizerAndFit(self.topsizer)
        self.CentreOnParent()
        self.name_dialog.SetFocus()

    def onClickAdd(self, ev):
        """Add the new spool and close the window."""

        spool_name = self.name_dialog.GetValue()
        spool_length = getFloat(self, self.length_dialog.GetValue())

        # Check whether the length is actually a number
        if not spool_length:
            self.parent.statusbar.SetLabel(_("ERROR: Unrecognized length: %s.") %
                                           self.length_dialog.GetValue())
            self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
            return

        # The remaining filament should always be a positive number
        if not spool_length > 0:
            self.parent.statusbar.SetLabel(_("ERROR: Length is zero or negative: %.2f.") %
                                           spool_length)
            self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
            return

        # Check whether the name is already used. If it is used, prompt the
        # user before overwriting it
        if self.parent.spool_manager.isListed(spool_name):
            if checkOverwrite(self, spool_name):
                # Remove the "will be overwritten" spool
                self.parent.spool_manager.remove(spool_name)
            else:
                return

        # Add the new spool
        self.parent.spool_manager.add(spool_name, spool_length)
        self.parent.spool_list.refreshList(self.parent.spool_manager)
        self.parent.current_spools_dialog.refreshDialog(
                self.parent.spool_manager)
        self.parent.statusbar.SetLabel(
            _("Added new spool '%s'") % spool_name +
            _(" with %.2f mm of remaining filament.") % spool_length)
        self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status

        self.EndModal(True)
        self.Destroy()

    def onClickCancel(self, event):
        """Do nothing and close the window."""
        self.parent.statusbar.SetLabel("")
        self.EndModal(True)
        self.Destroy()

    def calculateLength(self, event):
        """
        Calculate the length of the filament given the mass, diameter and
        density of the filament. Set the 'Length' field to this quantity.
        """

        mass = getFloat(self, self.weight_dialog.GetValue())
        diameter = getFloat(self, self.diameter_dialog.GetValue())
        density = getFloat(self, self.density_dialog.GetValue())
        if mass and diameter and density:
            pi = 3.14159265359
            length = 4e6 * mass / pi / diameter**2 / density
            self.parent.statusbar.SetLabel("")
            self.length_dialog.ChangeValue("%.2f" % length)
        else:
            self.length_dialog.ChangeValue("---")

    def calculateWeight(self, event):
        """
        Calculate the weight of the filament given the length, diameter and
        density of the filament. Set the 'Weight' field to this value.
        """

        length = getFloat(self, self.length_dialog.GetValue())
        diameter = getFloat(self, self.diameter_dialog.GetValue())
        density = getFloat(self, self.density_dialog.GetValue())
        if length and diameter and density:
            pi = 3.14159265359
            mass = length * pi * diameter**2 * density / 4e6
            self.parent.statusbar.SetLabel("")
            self.weight_dialog.ChangeValue("%.2f" % mass)
        else:
            self.weight_dialog.ChangeValue("---")

# ---------------------------------------------------------------------------
class SpoolManagerEditWindow(wx.Dialog):
    """Window for editing the name or the length of a spool."""

    def __init__(self, parent, spool_name, spool_length):

        wx.Dialog.__init__(self, parent,
            title = _("Edit Spool"),
            style = wx.DEFAULT_DIALOG_STYLE)

        self.parent = parent

        self.SetIcon(parent.GetIcon())

        self.old_spool_name = spool_name
        self.old_spool_length = getFloat(self, spool_length.replace(" mm", ""))

        # Set how many millimeters will the buttons add or subtract
        self.quantities = [-100.0, -50.0, -10.0, 10.0, 50.0, 100.0]

        # Generate the name field
        self.name_title = wx.StaticText(self, -1, _("Name:"))
        minwidth = self.GetTextExtent('Default Very Long Spool Name').width
        self.name_field = wx.TextCtrl(self, -1, self.old_spool_name, style = wx.TE_RIGHT)
        self.name_field.SetMinSize((minwidth, -1))

        # Generate the length field
        self.length_title = wx.StaticText(self, label = _("Remaining filament:"),
                                          style = wx.ALIGN_RIGHT)
        self.length_field = wx.TextCtrl(self, -1, value = str(self.old_spool_length),
                                        style = wx.TE_RIGHT)
        self.length_field.SetMinSize((minwidth, -1))

        # Generate the buttons
        button_min_width = self.GetTextExtent('  +000.0  ').width
        self.minus3_button = wx.Button(self,
            label = str(self.quantities[0]))
        self.minus2_button = wx.Button(self,
            label = str(self.quantities[1]))
        self.minus1_button = wx.Button(self,
            label = str(self.quantities[2]))

        self.plus1_button = wx.Button(self,
            label = "+" + str(self.quantities[3]))
        self.plus2_button = wx.Button(self,
            label = "+" + str(self.quantities[4]))
        self.plus3_button = wx.Button(self,
            label = "+" + str(self.quantities[5]))

        self.minus3_button.SetSize((button_min_width, -1))
        self.minus2_button.SetSize((button_min_width, -1))
        self.minus1_button.SetSize((button_min_width, -1))
        self.plus1_button.SetSize((button_min_width, -1))
        self.plus2_button.SetSize((button_min_width, -1))
        self.plus3_button.SetSize((button_min_width, -1))

        # "Program" the length buttons
        self.minus3_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.minus2_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.minus1_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus1_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus2_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus3_button.Bind(wx.EVT_BUTTON, self.changeLength)

        # Generate the bottom buttons
        self.save_button = wx.Button(self, wx.ID_SAVE)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        # "Program" the bottom buttons
        self.save_button.Bind(wx.EVT_BUTTON, self.onClickSave)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)
        self.save_button.SetDefault()
        self.SetAffirmativeId(wx.ID_SAVE)

        # Layout
        ## Group the length field and its correspondent buttons
        self.btn_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self)
        self.btn_sizer.Add(self.minus3_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT | wx.TOP | wx.BOTTOM,
                           get_space('staticbox'))
        self.btn_sizer.Add(self.minus2_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, get_space('mini'))
        self.btn_sizer.Add(self.minus1_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, get_space('mini'))
        self.btn_sizer.AddSpacer(get_space('major'))
        self.btn_sizer.Add(self.plus1_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT, get_space('mini'))
        self.btn_sizer.Add(self.plus2_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, get_space('mini'))
        self.btn_sizer.Add(self.plus3_button, 0,
                           wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, get_space('staticbox'))

        ## Group the bottom buttons
        self.bottom_buttons_sizer = wx.StdDialogButtonSizer()
        self.bottom_buttons_sizer.AddButton(self.save_button)
        self.bottom_buttons_sizer.AddButton(self.cancel_button)
        self.bottom_buttons_sizer.Realize()

        ## Lay out the whole window
        grid = wx.GridBagSizer(hgap = get_space('minor'), vgap = get_space('minor'))

        # Gridbagsizer: pos = (row, col), span = (rowspan, colspan)
        grid.Add(self.name_title, pos = (0, 0), span = (1, 1), border = 0,
                 flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.name_field, pos = (0, 1), span = (1, 1), border = 0,
                 flag = wx.ALIGN_LEFT)
        grid.Add(self.length_title, pos = (1, 0), span = (1, 1), border = 0,
                 flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.length_field, pos = (1, 1), span = (1, 1), border = 0,
                 flag = wx.ALIGN_LEFT)
        grid.Add(self.btn_sizer, pos = (2, 0), span = (1, 2), border = 0,
                 flag = wx.ALIGN_CENTER | wx.EXPAND)

        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(grid, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, get_space('major'))
        topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0,
                     wx.EXPAND | wx.TOP, get_space('minor'))
        topsizer.Add(self.bottom_buttons_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, get_space('stddlg'))

        self.SetSizer(topsizer)
        self.Fit()
        self.CentreOnParent()
        self.name_field.SetFocus()

    def changeLength(self, event):
        new_length = getFloat(self, self.length_field.GetValue())
        if new_length:
            new_length = new_length + float(event.GetEventObject().GetLabel())
            self.length_field.ChangeValue("%.2f" % new_length)
            self.parent.statusbar.SetLabel("")

    def onClickSave(self, event):

        new_spool_name = self.name_field.GetValue()
        new_spool_length = getFloat(self, self.length_field.GetValue())

        # Check whether the length is actually a number
        if not new_spool_length:
            self.parent.statusbar.SetLabel(
                _("ERROR: Unrecognized length: %s.") %
                self.length_field.GetValue())
            self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
            return

        if not new_spool_length > 0:
            self.parent.statusbar.SetLabel(
                _("ERROR: Length is zero or negative: %.2f.") % new_spool_length)
            self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
            return

        # Check whether the "old" spool was loaded
        new_spool_extruder = self.parent.spool_manager.isLoaded(
            self.old_spool_name)

        # Check whether the name has changed
        if new_spool_name == self.old_spool_name:
            # Remove only the "old" spool
            self.parent.spool_manager.remove(self.old_spool_name)
        else:
            # Check whether the new name is already used
            if self.parent.spool_manager.isListed(new_spool_name):
                if checkOverwrite(self, new_spool_name):
                    # Remove the "old" and the "will be overwritten" spools
                    self.parent.spool_manager.remove(self.old_spool_name)
                    self.parent.spool_manager.remove(new_spool_name)
                else:
                    return
            else:
                # Remove only the "old" spool
                self.parent.spool_manager.remove(self.old_spool_name)

        # Add "new" or edited spool
        self.parent.spool_manager.add(new_spool_name, new_spool_length)
        self.parent.spool_manager.load(new_spool_name, new_spool_extruder)
        self.parent.spool_list.refreshList(self.parent.spool_manager)
        self.parent.current_spools_dialog.refreshDialog(
            self.parent.spool_manager)
        self.parent.statusbar.SetLabel(
            _("Edited spool '%s'") % new_spool_name +
            _(" with %.2f mm of remaining filament.") % new_spool_length)
        self.parent.Layout()  # Layout() is needed to ellipsize possible overlength status
        self.EndModal(True)
        self.Destroy()

    def onClickCancel(self, event):
        self.parent.statusbar.SetLabel("")
        self.EndModal(True)
        self.Destroy()
