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

class SpoolManagerMainWindow(wx.Frame):
    """
    Front-end for the Spool Manager.

    Main window which displays the currently loaded spools and the list of
    recorded ones with buttons to add, load, edit or delete them.
    """

    def __init__(self, parent, spool_manager):
        wx.Frame.__init__(self, parent,
            title = "Spool Manager",
            style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

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
        self.new_button.SetToolTip("Add a new spool")
        self.edit_button = wx.Button(self, wx.ID_EDIT)
        self.edit_button.SetToolTip("Edit the selected spool")
        self.delete_button = wx.Button(self, wx.ID_DELETE)
        self.delete_button.SetToolTip("Delete the selected spool")

        # "Program" the buttons
        self.new_button.Bind(wx.EVT_BUTTON, self.onClickAdd)
        self.edit_button.Bind(wx.EVT_BUTTON, self.onClickEdit)
        self.delete_button.Bind(wx.EVT_BUTTON, self.onClickDelete)

        # Layout
        ## Group the buttons
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer.Add(self.new_button, 1,
            wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.button_sizer.Add(self.edit_button, 1,
            wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.button_sizer.Add(self.delete_button, 1,
            wx.FIXED_MINSIZE | wx.ALIGN_CENTER)

        ## Group the buttons with the spool list
        self.list_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.list_sizer.Add(self.spool_list, 1, wx.EXPAND)
        self.list_sizer.Add(self.button_sizer, 0, wx.ALIGN_CENTER)

        ## Layout the whole thing
        self.full_sizer = wx.BoxSizer(wx.VERTICAL)
        self.full_sizer.Add(self.current_spools_dialog, 0, wx.EXPAND)
        self.full_sizer.Add(self.list_sizer, 1, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(self.full_sizer)

    def onClickAdd(self, event):
        """Open the window for customizing the new spool."""
        SpoolManagerAddWindow(self).Show(True)

    def onClickLoad(self, event, extruder):
        """Load the selected spool to the correspondent extruder."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1 :
            self.statusbar.SetStatusText(
                "Could not load the spool. No spool selected.")
            return 0
        else:
            spool_name = self.spool_list.GetItemText(spool_index)
            self.statusbar.SetStatusText("")

        # If selected spool is already loaded, do nothing
        spool_extruder = self.spool_manager.isLoaded(spool_name)
        if spool_extruder > -1:
            self.statusbar.SetStatusText(
                "Spool '%s' is already loaded for Extruder %d." % 
                (spool_name, spool_extruder))
            return 0

        # Load the selected spool and refresh the current spools dialog
        self.spool_manager.load(spool_name, extruder)
        self.current_spools_dialog.refreshDialog(self.spool_manager)
        self.statusbar.SetStatusText(
            "Loaded spool '%s' for Extruder %d." % (spool_name, extruder))

    def onClickUnload(self, event, extruder):
        """Unload the spool from the correspondent extruder."""

        spool_name = self.spool_manager.getSpoolName(extruder)
        if spool_name != None:
            self.spool_manager.unload(extruder)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetStatusText(
                "Unloaded spool from Extruder %d." % extruder)
        else:
            self.statusbar.SetStatusText(
                "There is no spool loaded for Extruder %d." % extruder)

    def onClickEdit(self, event):
        """Open the window for editing the data of the selected spool."""

        # Check whether there is a spool selected
        spool_index = self.spool_list.GetFirstSelected()
        if spool_index == -1 :
            self.statusbar.SetStatusText(
                "Could not edit the spool. No spool selected.")
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
                "Could not delete the spool. No spool selected.")
            return 0
        else:
            spool_name = self.spool_list.GetItemText(spool_index)
            self.statusbar.SetStatusText("")

        # Ask confirmation for deleting
        delete_dialog = wx.MessageDialog(self,
            message = "Are you sure you want to delete the '%s' spool" %
                spool_name,
            caption = "Delete Spool",
            style = wx.YES_NO | wx.ICON_EXCLAMATION)

        if delete_dialog.ShowModal() == wx.ID_YES:
            # Remove spool
            self.spool_manager.remove(spool_name)
            self.spool_list.refreshList(self.spool_manager)
            self.current_spools_dialog.refreshDialog(self.spool_manager)
            self.statusbar.SetStatusText(
                "Deleted spool '%s'." % spool_name)


class SpoolListView(wx.ListView):
    """
    Custom wxListView object which visualizes the list of available spools.
    """

    def __init__(self, parent, spool_manager):
        wx.ListView.__init__(self, parent,
            style = wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.InsertColumn(0, "Spool", width = wx.LIST_AUTOSIZE_USEHEADER)
        self.InsertColumn(1, "Filament", width = wx.LIST_AUTOSIZE_USEHEADER)
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

        full_sizer = wx.BoxSizer(wx.VERTICAL)

        # Calculate the minimum size needed to properly display the
        # extruder information
        min_size = self.GetTextExtent("    Remaining filament: 0000000.00")

        # Generate a dialog for every extruder
        self.extruder_dialog = []
        load_button = []
        unload_button = []
        button_sizer = []
        dialog_sizer = []
        for i in range(self.extruders):
            # Generate the dialog with the spool information
            self.extruder_dialog.append(
                wx.StaticText(self, style = wx.ST_ELLIPSIZE_END))
            self.extruder_dialog[i].SetMinSize(wx.Size(min_size.width, -1))

            # Generate the "load" and "unload" buttons
            load_button.append(wx.Button(self, label = "Load"))
            load_button[i].SetToolTip(
                "Load selected spool for Extruder %d" % i)
            unload_button.append(wx.Button(self, label = "Unload"))
            unload_button[i].SetToolTip(
                "Unload the spool for Extruder %d" % i)

            # "Program" the buttons
            load_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.onClickLoad(event, extruder))
            unload_button[i].Bind(wx.EVT_BUTTON,
                lambda event, extruder=i: parent.onClickUnload(event, extruder))

            # Layout
            button_sizer.append(wx.BoxSizer(wx.VERTICAL))
            button_sizer[i].Add(load_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
            button_sizer[i].Add(unload_button[i], 0,
                wx.FIXED_MINSIZE | wx.ALIGN_CENTER)

            dialog_sizer.append(wx.BoxSizer(wx.HORIZONTAL))
            dialog_sizer[i].Add(self.extruder_dialog[i], 1, wx.ALIGN_CENTER)
            dialog_sizer[i].AddSpacer(10)
            dialog_sizer[i].Add(button_sizer[i], 0, wx.EXPAND)

            full_sizer.Add(dialog_sizer[i], 0, wx.ALL | wx.EXPAND, 10)

        self.refreshDialog(spool_manager)

        self.SetSizerAndFit(full_sizer)


    def refreshDialog(self, spool_manager):
        """Retrieve the current spools from the Spool Manager."""

        for i in range(self.extruders):
            spool_name = spool_manager.getSpoolName(i)
            spool_filament = spool_manager.getRemainingFilament(i)
            label = ("Spool for Extruder %d:\n" % i +
                     "    Name:               %s\n" % spool_name +
                     "    Remaining filament: %.2f" % spool_filament)
            self.extruder_dialog[i].SetLabelText(label)


# ---------------------------------------------------------------------------
def checkOverwrite(parent, spool_name):
    """Ask the user whether or not to overwrite the existing spool."""

    overwrite_dialog = wx.MessageDialog(parent,
        message = "A spool with the name '%s'' already exists." %
            spool_name +
            "Do you wish to overwrite it?",
        caption = "Overwrite",
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
    try:
        return float(number)
    except ValueError:
        parent.statusbar.SetStatusText("Unrecognized number: %s" % number)
        return False


# ---------------------------------------------------------------------------
class SpoolManagerAddWindow(wx.Frame):
    """Window for adding spools."""

    def __init__(self, parent):

        wx.Frame.__init__(self, parent,
            title = "Add Spool",
            style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        self.statusbar = self.CreateStatusBar()

        self.parent = parent

        self.SetIcon(parent.GetIcon())

        # Generate the dialogs
        self.name_dialog = LabeledTextCtrl(self,
            "Name", "Default Spool", "")
        self.diameter_dialog = LabeledTextCtrl(self,
            "Diameter", "1.75", "mm")
        self.diameter_dialog.SetToolTip(
            "Typically, either 1.75 mm or 2.85 mm (a.k.a '3')")
        self.weight_dialog = LabeledTextCtrl(self,
            "Weight", "1", "Kg")
        self.density_dialog = LabeledTextCtrl(self,
            "Density", "1.25", "g/cm^3")
        self.density_dialog.SetToolTip(
            "Typical densities are 1.25 g/cm^3 for PLA and 1.08 g/cm^3 for" +
            " ABS")
        self.length_dialog = LabeledTextCtrl(self,
            "Length", "332601.35", "mm")

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
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)

        # Layout
        ## Group the bottom buttons
        self.bottom_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bottom_buttons_sizer.Add(self.add_button, 0, wx.FIXED_MINSIZE)
        self.bottom_buttons_sizer.Add(self.cancel_button, 0, wx.FIXED_MINSIZE)

        ## Group the whole window
        self.full_sizer = wx.BoxSizer(wx.VERTICAL)
        self.full_sizer.Add(self.name_dialog, 0,
            wx.TOP | wx.BOTTOM | wx.EXPAND,  10)
        self.full_sizer.Add(self.diameter_dialog, 0, wx.EXPAND)
        self.full_sizer.Add(self.weight_dialog, 0, wx.EXPAND)
        self.full_sizer.Add(self.density_dialog, 0, wx.EXPAND)
        self.full_sizer.Add(self.length_dialog, 0, wx.EXPAND)
        self.full_sizer.Add(self.bottom_buttons_sizer, 0,
            wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        self.SetSizerAndFit(self.full_sizer)

        # Don't allow this window to be resized in height
        add_window_size = self.GetSize()
        self.SetMaxSize((-1, add_window_size.height))

    def onClickAdd(self, event):
        """Add the new spool and close the window."""

        spool_name = self.name_dialog.field.GetValue()
        spool_length = getFloat(self, self.length_dialog.field.GetValue())

        # Check whether the length is actually a number
        if not spool_length:
            self.statusbar.SetStatusText(
                "ERROR: Unrecognized length: %s." %
                    self.length_dialog.field.GetValue())
            return -1

        # The remaining filament should always be a positive number
        if not spool_length > 0:
            self.statusbar.SetStatusText(
                "ERROR: Length is zero or negative: %.2f." % spool_length)
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
            "Added new spool '%s'" % spool_name +
            " with %.2f mm of remaining filament." % spool_length)

        self.Close(True)

    def onClickCancel(self, event):
        """Do nothing and close the window."""
        self.Close(True)
        self.parent.statusbar.SetStatusText("")

    def calculateLength(self, event):
        """
        Calculate the length of the filament given the mass, diameter and
        density of the filament. Set the 'Length' field to this quantity.
        """

        mass = getFloat(self, self.weight_dialog.field.GetValue())
        diameter = getFloat(self, self.diameter_dialog.field.GetValue())
        density = getFloat(self, self.density_dialog.field.GetValue())
        if mass and diameter and density:
            pi = 3.14159265359
            length = 4e6 * mass / pi / diameter**2 / density
            self.length_dialog.field.ChangeValue("%.2f" % length)
            self.statusbar.SetStatusText("")
        else:
            self.length_dialog.field.ChangeValue("---")

    def calculateWeight(self, event):
        """
        Calculate the weight of the filament given the length, diameter and
        density of the filament. Set the 'Weight' field to this value.
        """

        length = getFloat(self, self.length_dialog.field.GetValue())
        diameter = getFloat(self, self.diameter_dialog.field.GetValue())
        density = getFloat(self, self.density_dialog.field.GetValue())
        if length and diameter and density:
            pi = 3.14159265359
            mass = length * pi * diameter**2 * density / 4e6
            self.weight_dialog.field.ChangeValue("%.2f" % mass)
            self.statusbar.SetStatusText("")
        else:
            self.weight_dialog.field.ChangeValue("---")


class LabeledTextCtrl(wx.Panel):
    """
    Group together a wxTextCtrl with a preceding and a subsequent wxStaticText.
    """

    def __init__(self, parent, preceding_text, field_value, subsequent_text):
        wx.Panel.__init__(self, parent)
        self.pretext = wx.StaticText(self, label = preceding_text,
            style = wx.ALIGN_RIGHT)
        self.field = wx.TextCtrl(self, value = field_value)
        self.subtext = wx.StaticText(self, label = subsequent_text)

        # Layout the panel
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.pretext, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 10)
        self.sizer.SetItemMinSize(self.pretext, (80, -1))
        self.sizer.Add(self.field, 1, wx.EXPAND)
        self.sizer.Add(self.subtext, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
        self.sizer.SetItemMinSize(self.subtext, (50, -1))

        self.SetSizerAndFit(self.sizer)


# ---------------------------------------------------------------------------
class SpoolManagerEditWindow(wx.Frame):
    """Window for editing the name or the length of a spool."""

    def __init__(self, parent, spool_name, spool_length):

        wx.Frame.__init__(self, parent,
            title = "Edit Spool",
            style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        self.statusbar = self.CreateStatusBar()

        self.parent = parent

        self.SetIcon(parent.GetIcon())

        self.old_spool_name = spool_name
        self.old_spool_length = getFloat(self, spool_length)

        # Set how many millimeters will the buttons add or subtract
        self.quantities = [-100.0, -50.0, -10.0, 10.0, 50.0, 100.0]

        # Generate the name field
        self.name_field = LabeledTextCtrl(self,
            "Name", self.old_spool_name, "")

        # Generate the length field and buttons
        self.length_title = wx.StaticText(self, label = "Remaining filament:")
        self.minus3_button = wx.Button(self,
            label = str(self.quantities[0]), style = wx.BU_EXACTFIT)
        self.minus2_button = wx.Button(self,
            label = str(self.quantities[1]), style = wx.BU_EXACTFIT)
        self.minus1_button = wx.Button(self,
            label = str(self.quantities[2]), style = wx.BU_EXACTFIT)
        self.length_field = wx.TextCtrl(self,
            value = str(self.old_spool_length))
        self.plus1_button = wx.Button(self,
            label = "+" + str(self.quantities[3]), style = wx.BU_EXACTFIT)
        self.plus2_button = wx.Button(self,
            label = "+" + str(self.quantities[4]), style = wx.BU_EXACTFIT)
        self.plus3_button = wx.Button(self,
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
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        # "Program" the bottom buttons
        self.save_button.Bind(wx.EVT_BUTTON, self.onClickSave)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.onClickCancel)

        # Layout
        ## Group the length field and its correspondent buttons
        self.length_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.length_sizer.Add(self.minus3_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.length_sizer.Add(self.minus2_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.length_sizer.Add(self.minus1_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.length_sizer.Add(self.length_field, 1, wx.EXPAND)
        self.length_sizer.Add(self.plus1_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.length_sizer.Add(self.plus2_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)
        self.length_sizer.Add(self.plus3_button, 0,
                              wx.FIXED_MINSIZE | wx.ALIGN_CENTER)

        ## Group the bottom buttons
        self.bottom_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bottom_buttons_sizer.Add(self.save_button, 0, wx.EXPAND)
        self.bottom_buttons_sizer.Add(self.cancel_button, 0, wx.EXPAND)

        ## Lay out the whole window
        self.full_sizer = wx.BoxSizer(wx.VERTICAL)
        self.full_sizer.Add(self.name_field, 0, wx.EXPAND)
        self.full_sizer.AddSpacer(10)
        self.full_sizer.Add(self.length_title, 0,
            wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        self.full_sizer.Add(self.length_sizer, 0,
            wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        self.full_sizer.AddSpacer(10)
        self.full_sizer.Add(self.bottom_buttons_sizer, 0, wx.ALIGN_CENTER)

        self.SetSizerAndFit(self.full_sizer)

        # Don't allow this window to be resized in height
        edit_window_size = self.GetSize()
        self.SetMaxSize((-1, edit_window_size.height))

    def changeLength(self, event):
        new_length = getFloat(self, self.length_field.GetValue())
        if new_length:
            new_length = new_length + float(event.GetEventObject().GetLabel())
            self.length_field.ChangeValue("%.2f" % new_length)
            self.statusbar.SetStatusText("")

    def onClickSave(self, event):

        new_spool_name = self.name_field.field.GetValue()
        new_spool_length = getFloat(self, self.length_field.GetValue())

        # Check whether the length is actually a number
        if not new_spool_length:
            self.statusbar.SetStatusText(
                "ERROR: Unrecognized length: %s." %
                    self.length_field.GetValue())
            return -1

        if not new_spool_length > 0:
            self.statusbar.SetStatusText(
                "ERROR: Length is zero or negative: %.2f." % new_spool_length)
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
            "Edited spool '%s'" % new_spool_name +
            " with %.2f mm of remaining filament." % new_spool_length)

        self.Close(True)

    def onClickCancel(self, event):
            self.Close(True)
            self.parent.statusbar.SetStatusText("")
