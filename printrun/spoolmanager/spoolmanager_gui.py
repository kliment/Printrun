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
from . import spoolmanager
from printrun.gui.widgets import getSpace

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

        self.statusbar = self.CreateStatusBar()

        self.SetIcon(parent.GetIcon())

        # Initiate the back-end
        self.spool_manager = spool_manager
        self.spool_manager.refresh()

        # Generate the dialogs showing the current spools
        self.current_spools_dialog = CurrentSpoolDialog(self,
            self.spool_manager)

        # Generate the list of recorded spools
        self.spool_list = SpoolListView(self, self.spool_manager)

        # Generate the buttons
        self.new_button = wx.Button(self, wx.ID_ADD)
        self.new_button.SetToolTip(_("Add a new spool"))
        self.edit_button = wx.Button(self, wx.ID_EDIT)
        self.edit_button.SetToolTip(_("Edit the selected spool"))
        self.delete_button = wx.Button(self, wx.ID_DELETE)
        self.delete_button.SetToolTip(_("Delete the selected spool"))
        
        self.close_button = wx.Button(self, wx.ID_CLOSE)

        # "Program" the buttons
        self.new_button.Bind(wx.EVT_BUTTON, self.onClickAdd)
        self.edit_button.Bind(wx.EVT_BUTTON, self.onClickEdit)
        self.delete_button.Bind(wx.EVT_BUTTON, self.onClickDelete)
        
        self.close_button.Bind(wx.EVT_BUTTON, self.onClickClose)

        # Layout
        ## Group the buttons
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer.Add(self.new_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT | wx.BOTTOM, getSpace('minor'))
        self.button_sizer.Add(self.edit_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT | wx.BOTTOM, getSpace('minor'))
        self.button_sizer.Add(self.delete_button, 0,
            wx.FIXED_MINSIZE | wx.EXPAND | wx.LEFT, getSpace('minor'))

        ## Group the buttons with the spool list
        self.list_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, label = "Spool List")
        self.list_sizer.Add(self.spool_list, 1, wx.EXPAND)
        self.list_sizer.Add(self.button_sizer, 0, wx.ALIGN_TOP)

        ## Layout the whole thing
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.current_spools_dialog, 0, wx.EXPAND)
        self.topsizer.Add(self.list_sizer, 1, wx.ALL | wx.EXPAND, getSpace('minor'))
        self.topsizer.Add(self.close_button, 0, 
                          wx.FIXED_MINSIZE | wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, getSpace('minor'))

        self.SetSizerAndFit(self.topsizer)
        self.CentreOnParent()

    def onClickAdd(self, event):
        """Open the window for customizing the new spool."""
        SpoolManagerAddWindow(self).Show(True)

    def onClickLoad(self, event, extruder):
        """Load the selected spool to the correspondent extruder."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1 :
            self.statusbar.SetStatusText(
                _("Could not load the spool. No spool selected."))
            return 0
        else:
            spool_name = self.spool_list.GetItemText(spool_index)
            self.statusbar.SetStatusText("")

        # If selected spool is already loaded, do nothing
        spool_extruder = self.spool_manager.isLoaded(spool_name)
        if spool_extruder > -1:
            self.statusbar.SetStatusText(
                _("Spool '%s' is already loaded for Extruder %d.") % 
                (spool_name, spool_extruder))
            return 0

        # Load the selected spool and refresh the current spools dialog
        self.spool_manager.load(spool_name, extruder)
        self.current_spools_dialog.refreshDialog(self.spool_manager)
        self.statusbar.SetStatusText(
            _("Loaded spool '%s' for Extruder %d.") % (spool_name, extruder))

    def onClickUnload(self, event, extruder):
        """Unload the spool from the correspondent extruder."""

        spool_name = self.spool_manager.getSpoolName(extruder)
        if spool_name != None:
            self.spool_manager.unload(extruder)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetStatusText(
                _("Unloaded spool from Extruder %d.") % extruder)
        else:
            self.statusbar.SetStatusText(
                _("There is no spool loaded for Extruder %d.") % extruder)

    def onClickEdit(self, event):
        """Open the window for editing the data of the selected spool."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1 :
            self.statusbar.SetStatusText(
                _("Could not edit the spool. No spool selected."))
            return 0

        # Open the edit window
        spool_name = self.spool_list.GetItemText(spool_index)
        spool_length = self.spool_list.GetItemText(spool_index, 1)
        SpoolManagerEditWindow(self, spool_name, spool_length).Show(True)
        self.statusbar.SetStatusText("")

    def onClickDelete(self, event):
        """Delete the selected spool."""

        # Get the selected spool
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1 :
            self.statusbar.SetStatusText(
                _("Could not delete the spool. No spool selected."))
            return 0
        else:
            spool_name = self.spool_list.GetItemText(spool_index)
            self.statusbar.SetStatusText("")

        # Ask confirmation for deleting
        delete_dialog = wx.MessageDialog(self,
            message = _("Are you sure you want to delete the '%s' spool") %
                spool_name,
            caption = _("Delete Spool"),
            style = wx.YES_NO | wx.ICON_EXCLAMATION)

        if delete_dialog.ShowModal() == wx.ID_YES:
            # Remove spool
            self.spool_manager.remove(spool_name)
            self.spool_list.refreshList(self.spool_manager)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetStatusText(
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

    def populateList(self, spool_manager):
        """Get the list of recorded spools from the Spool Manager."""
        spool_list = spool_manager.getSpoolList()
        for i in range(len(spool_list)):
            self.Append(spool_list[i])

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


class CurrentSpoolDialog(wx.Panel):
    """
    Custom wxStaticText object to display the currently loaded spools and
    their remaining filament.
    """

    def __init__(self, parent, spool_manager):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.extruders = spool_manager.getExtruderCount()

        topsizer = wx.BoxSizer(wx.VERTICAL)

        # Calculate the minimum size needed to properly display the
        # extruder information
        min_size = self.GetTextExtent(_("Default Very Long Spool Name"))

        # Generate a dialog for every extruder
        self.extruder_dialog = []
        load_button = []
        unload_button = []
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
            unload_button.append(wx.Button(self, label = _("Unload")))
            unload_button[i].SetToolTip(
                _("Unload the spool for Extruder %d") % i)

            # "Program" the buttons
            load_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.onClickLoad(event, extruder))
            unload_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.onClickUnload(event, extruder))

            # Layout
            button_sizer.append(wx.BoxSizer(wx.VERTICAL))
            button_sizer[i].Add(load_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.BOTTOM, getSpace('minor'))
            button_sizer[i].Add(unload_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER)

            dialog_sizer.append(wx.StaticBoxSizer(wx.HORIZONTAL, self, label = _("Spool for Extruder %d:") % i))
            dialog_sizer[i].Add(textlabel, 0, wx.ALIGN_TOP)
            dialog_sizer[i].AddSpacer(getSpace('major'))
            dialog_sizer[i].Add(self.extruder_dialog[i], 1, wx.ALIGN_TOP)
            dialog_sizer[i].AddSpacer(getSpace('major'))
            dialog_sizer[i].Add(button_sizer[i], 0, wx.EXPAND)

            topsizer.Add(dialog_sizer[i], 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, getSpace('major'))

        self.refreshDialog(spool_manager)

        self.SetSizerAndFit(topsizer)

    def refreshDialog(self, spool_manager):
        """Retrieve the current spools from the Spool Manager."""

        for i in range(self.extruders):
            spool_name = spool_manager.getSpoolName(i)
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

    if overwrite_dialog.ShowModal() == wx.ID_YES:
        return True
    else:
        return False

def getFloat(parent, number):
    """
    Check whether the input number is a float. Either return the number or
    return False.
    """
    if ',' in number:
        parent.parent.statusbar.SetStatusText(_("Value contains a comma, please use a point for decimal values: %s") % number)
        return False

    try:
        return float(number)
    except ValueError:
        parent.parent.statusbar.SetStatusText(_("Unrecognized number: %s") % number)
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

        # The list contains field-description, textctrl variabel, default value, unit, tooltip;
        name_dlg = [_("Name:"), self.name_dialog, _("Default Spool"), "", ""]
        diameter_dlg = [_("Diameter:"), self.diameter_dialog, "1.75", "mm", _("Typically, either 1.75 mm or 2.85 mm")]
        weight_dlg = [_("Weight:"), self.weight_dialog, "1.0", "kg", ""]
        density_dlg = [_("Density:"), self.density_dialog, "1.25", "g/cm^3", _("Typical densities are 1.25 g/cm^3 for PLA,\n1.27 g/cm^3 for PETG or 1.08 g/cm^3 for ABS")]
        length_dlg = [_("Length"), self.length_dialog, "332601.35", "mm", ""]
        dialog_list = [name_dlg, diameter_dlg, weight_dlg, density_dlg, length_dlg]

        minwidth = self.GetTextExtent('Default Long Spool Name').width
        grid = wx.FlexGridSizer(rows = 0, cols = 3, hgap = getSpace('minor'), vgap = getSpace('minor'))

        for dialog in dialog_list:
            grid.Add(wx.StaticText(self, -1, dialog[0], size = (-1, -1), style = wx.TE_RIGHT), 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
            dialog[1].ChangeValue(dialog[2])
            dialog[1].SetMinSize((minwidth, -1))
            if dialog[4] != "":
                dialog[1].SetToolTip(dialog[4])
            grid.Add(dialog[1])
            if dialog[3] == "":
                grid.Add((0,0))
            else:
                grid.Add(wx.StaticText(self, -1, dialog[3], size = (-1, -1)), wx.ALIGN_CENTER_VERTICAL)

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
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)

        # Layout
        ## Setup the bottom buttons
        self.bottom_buttons_sizer = wx.StdDialogButtonSizer()
        self.bottom_buttons_sizer.SetAffirmativeButton(self.add_button)
        self.bottom_buttons_sizer.AddButton(self.cancel_button)

        self.bottom_buttons_sizer.Realize()

        ## Group the whole window
        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(grid, 1, wx.EXPAND | wx.ALL, getSpace('major'))
        self.topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND)
        self.topsizer.Add(self.bottom_buttons_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, getSpace('stddlg'))

        self.SetSizerAndFit(self.topsizer)
        self.CentreOnParent()
        self.name_dialog.SetFocus()

    def onClickAdd(self, ev):
        """Add the new spool and close the window."""

        spool_name = self.name_dialog.GetValue()
        spool_length = getFloat(self, self.length_dialog.GetValue())

        # Check whether the length is actually a number
        if not spool_length:
            self.parent.statusbar.SetStatusText(
                _("ERROR: Unrecognized length: %s.") %
                    self.length_dialog.GetValue())
            return -1

        # The remaining filament should always be a positive number
        if not spool_length > 0:
            self.parent.statusbar.SetStatusText(
                _("ERROR: Length is zero or negative: %.2f.") % spool_length)
            return -1

        # Check whether the name is already used. If it is used, prompt the
        # user before overwriting it
        if self.parent.spool_manager.isListed(spool_name):
            if checkOverwrite(self, spool_name):
                # Remove the "will be overwritten" spool
                self.parent.spool_manager.remove(spool_name)
            else:
                return 0

        # Add the new spool
        self.parent.spool_manager.add(spool_name, spool_length)
        self.parent.spool_list.refreshList(self.parent.spool_manager)
        self.parent.current_spools_dialog.refreshDialog(
                self.parent.spool_manager)
        self.parent.statusbar.SetStatusText(
            _("Added new spool '%s'") % spool_name +
            _(" with %.2f mm of remaining filament.") % spool_length)

        self.Destroy()

    def onClickCancel(self, event):
        """Do nothing and close the window."""
        self.Destroy()

    def calculateLength(self, event):
        """
        Calculate the length of the filament given the mass, diameter and
        density of the filament. Set the 'Length' field to this quantity.
        """
        print(self.weight_dialog.GetValue())
        print(self.diameter_dialog.GetValue())
        print(self.density_dialog.GetValue())
        mass = getFloat(self, self.weight_dialog.GetValue())
        diameter = getFloat(self, self.diameter_dialog.GetValue())
        density = getFloat(self, self.density_dialog.GetValue())
        if mass and diameter and density:
            pi = 3.14159265359
            length = 4e6 * mass / pi / diameter**2 / density
            self.parent.statusbar.SetStatusText("")
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
            self.parent.statusbar.SetStatusText("")
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
        self.old_spool_length = getFloat(self, spool_length)

        # Set how many millimeters will the buttons add or subtract
        self.quantities = [-100.0, -50.0, -10.0, 10.0, 50.0, 100.0]

        # All widgets go into a sizer which is assigned to this panel
        self.panel = wx.Panel(self)

        # Generate the name field
        self.name_title = wx.StaticText(self.panel, -1, _("Name:"))
        minwidth = self.GetTextExtent('Default Very Long Spool Name').width
        self.name_field = wx.TextCtrl(self.panel, -1, self.old_spool_name, style = wx.TE_RIGHT)
        self.name_field.SetMinSize((minwidth, -1))

        # Generate the length field and buttons
        self.length_title = wx.StaticText(self.panel, label = _("Remaining filament:"), style = wx.ALIGN_RIGHT)
        self.length_field = wx.TextCtrl(self.panel, -1,
            value = str(self.old_spool_length), style = wx.TE_RIGHT)
        self.length_field.SetMinSize((minwidth, -1))
        
        self.minus3_button = wx.Button(self.panel,
            label = str(self.quantities[0]), style = wx.BU_EXACTFIT)
        self.minus2_button = wx.Button(self.panel,
            label = str(self.quantities[1]), style = wx.BU_EXACTFIT)
        self.minus1_button = wx.Button(self.panel,
            label = str(self.quantities[2]), style = wx.BU_EXACTFIT)

        self.plus1_button = wx.Button(self.panel,
            label = "+" + str(self.quantities[3]), style = wx.BU_EXACTFIT)
        self.plus2_button = wx.Button(self.panel,
            label = "+" + str(self.quantities[4]), style = wx.BU_EXACTFIT)
        self.plus3_button = wx.Button(self.panel,
            label = "+" + str(self.quantities[5]), style = wx.BU_EXACTFIT)

        # "Program" the length buttons
        self.minus3_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.minus2_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.minus1_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus1_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus2_button.Bind(wx.EVT_BUTTON, self.changeLength)
        self.plus3_button.Bind(wx.EVT_BUTTON, self.changeLength)

        # Generate the bottom buttons        
        self.save_button = wx.Button(self, wx.ID_SAVE)
        self.save_button.SetDefault()
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        # "Program" the bottom buttons
        self.save_button.Bind(wx.EVT_BUTTON, self.onClickSave)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)

        # Layout
        ## Group the length field and its correspondent buttons             
        self.btn_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self.panel)
        self.btn_sizer.Add(self.minus3_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, getSpace('mini'))
        self.btn_sizer.Add(self.minus2_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, getSpace('mini'))
        self.btn_sizer.Add(self.minus1_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.RIGHT, getSpace('mini'))
        self.btn_sizer.AddSpacer(getSpace('major'))
        self.btn_sizer.Add(self.plus1_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT, getSpace('mini'))
        self.btn_sizer.Add(self.plus2_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT, getSpace('mini'))
        self.btn_sizer.Add(self.plus3_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER | wx.LEFT, getSpace('mini'))

        ## Group the bottom buttons
        self.bottom_buttons_sizer = wx.StdDialogButtonSizer()

        self.bottom_buttons_sizer.AddButton(self.save_button)
        self.bottom_buttons_sizer.AddButton(self.cancel_button)
        self.save_button.SetDefault()

        self.bottom_buttons_sizer.Realize()

        ## Lay out the whole window
        grid = wx.GridBagSizer(hgap = getSpace('minor'), vgap = getSpace('minor'))
        
        grid.Add((getSpace('mini'),getSpace('mini')), pos = (0, 0), span = (1, 4),
                                    border = 0, flag = 0) #pos = row, col, span = rowspan, colspan
        grid.Add(self.name_title, pos = (1, 1), span = (1, 1),
                                    border = 0, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.name_field, pos = (1, 2), span = (1, 1),
                                    border = 0, flag = wx.ALIGN_LEFT)
        grid.Add(self.length_title, pos = (2, 1), span = (1, 1),
                                    border = 0, flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        grid.Add(self.length_field, pos = (2, 2), span = (1, 1),
                                    border = 0, flag = wx.ALIGN_LEFT)
        grid.Add(self.btn_sizer, pos = (3, 1), span = (1, 2),
                                    border = 0, flag = wx.ALIGN_CENTER | wx.EXPAND)
        grid.Add((getSpace('mini'),getSpace('mini')), pos = (3, 3), span = (1, 1),
                                    border = 0, flag = 0)

        self.panel.SetSizer(grid)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(self.panel, wx.EXPAND)
        topsizer.Add(wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL), 0, wx.EXPAND | wx.TOP, getSpace('mini'))
        topsizer.Add(self.bottom_buttons_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, getSpace('stddlg'))

        self.SetSizer(topsizer)
        self.Fit()
        self.CentreOnParent()
        self.name_field.SetFocus()

    def changeLength(self, event):
        new_length = getFloat(self, self.length_field.GetValue())
        if new_length:
            new_length = new_length + float(event.GetEventObject().GetLabel())
            self.length_field.ChangeValue("%.2f" % new_length)
            #self.statusbar.SetStatusText("")

    def onClickSave(self, event):

        new_spool_name = self.name_field.GetValue()
        new_spool_length = getFloat(self, self.length_field.GetValue())

        # Check whether the length is actually a number
        if not new_spool_length:
            self.statusbar.SetStatusText(
                _("ERROR: Unrecognized length: %s.") %
                    self.length_field.GetValue())
            return -1

        if not new_spool_length > 0:
            self.statusbar.SetStatusText(
                _("ERROR: Length is zero or negative: %.2f.") % new_spool_length)
            return -1

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
                    return 0
            else:
                # Remove only the "old" spool
                self.parent.spool_manager.remove(self.old_spool_name)

        # Add "new" or edited spool
        self.parent.spool_manager.add(new_spool_name, new_spool_length)
        self.parent.spool_manager.load(new_spool_name, new_spool_extruder)
        self.parent.spool_list.refreshList(self.parent.spool_manager)
        self.parent.current_spools_dialog.refreshDialog(
            self.parent.spool_manager)
        self.parent.statusbar.SetStatusText(
            _("Edited spool '%s'") % new_spool_name +
            _(" with %.2f mm of remaining filament.") % new_spool_length)

        self.Destroy()

    def onClickCancel(self, event):
            self.Destroy()
            self.parent.statusbar.SetStatusText("")
