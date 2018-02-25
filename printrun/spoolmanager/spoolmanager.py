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

# This module indirectly depends of pronsole and settings but it does not
# import them

class SpoolManager():
    """
    Back-end for the Spool Manager.

    It is expected to be called from an object which has the contents of
    settings.py and pronsole.py. This way the class is able to '_add' and
    'set' settings.

    This class basically handles a single variable called '_spool_list'. It is
    a list of spool_items. A spool_item is in turn a list three elements: a
    string, a float and an integer. Namely: the name of the spool, the
    remaining length of filament and the extruder it is loaded to. E.g.:

       spool_item = [string name, float length, int extruder]

       _spool_list = [spool_item spool_1, ... , spool_item spool_n ]

    '_spool_list' is somehow a Nx3 matrix where N is the number of recorded
    spools. The first column contains the names of the spools, the second the
    lengths of remaining filament and the third column contains which extruder
    is the spool loaded for.

    The variable '_spool_list' is saved in the configuration file using a
    setting with the same name: 'spool_list'. It is saved as a single string.
    It concatenates every item from the list and separates them by a comma and
    a space. For instance, if the variable '_spool_list' was:

           _spool_list = [["spool_1", 100.0, 0], ["spool_2", 200.0, -1]]

       The 'spool_list' setting will look like:

           "spool_1, 100.0, 0, spool_2, 200.0, -1"
    """

    def __init__(self, parent):
        self.parent = parent
        self.refresh()

    def refresh(self):
        """
        Read the configuration file and populate the list of recorded spools.
        """
        self._spool_list = self._readSetting(self.parent.settings.spool_list)

    def add(self, spool_name, spool_length):
        """Add the given spool to the list of recorded spools."""
        self._spool_list.append([spool_name, spool_length, -1])
        self._save()

    def load(self, spool_name, extruder):
        """Set the extruder field of the given spool item."""

        # If there was a spool already loaded for this extruder unload it
        previous_spool = self._findByColumn(extruder, 2)
        if previous_spool != -1:
            self.unload(extruder)

        # Load the given spool
        new_spool = self._findByColumn(spool_name, 0)
        self.remove(spool_name)
        self._spool_list.append([new_spool[0], new_spool[1], extruder])
        self._save()

    def remove(self, spool_name):
        """Remove the given spool item from the list of recorded spools."""
        spool_item = self._findByColumn(spool_name, 0)
        self._spool_list.remove(spool_item)
        self._save()

    def unload(self, extruder):
        """Set to -1 the extruder field of the spool item currently on."""

        spool_item = self._findByColumn(extruder, 2)
        if spool_item != -1:
            self.remove(spool_item[0])
            self._spool_list.append([spool_item[0], spool_item[1], -1])
            self._save()

    def isLoaded(self, spool_name):
        """
        int isLoaded( string name )

        Return the extruder that the given spool is loaded to. -1 if it is
        not loaded for any extruder or None if the given name does not match
        any known spool.
        """

        spool_item = self._findByColumn(spool_name, 0)
        if spool_item != -1:
            return spool_item[2]
        else:
            return None

    def isListed(self, spool_name):
        """Return 'True' if the given spool is on the list."""

        spool_item = self._findByColumn(spool_name, 0)
        if not spool_item == -1:
            return True
        else:
            return False

    def getSpoolName(self, extruder):
        """
        string getSpoolName( int extruder )

        Return the name of the spool loaded for the given extruder.
        """

        spool_item = self._findByColumn(extruder, 2)
        if spool_item != -1:
            return spool_item[0]
        else:
            return None

    def getRemainingFilament(self, extruder):
        """
        float getRemainingFilament( int extruder )

        Return the name of the spool loaded for the given extruder.
        """

        spool_item = self._findByColumn(extruder, 2)
        if spool_item != -1:
            return spool_item[1]
        else:
            return float("NaN")

    def editLength(self, increment, spool_name = None, extruder = -1):
        """
        int editLength ( float increment, string spool_name, int extruder )

        Add the given 'increment' amount to the length of filament of the
        given spool. Spool can be specified either by name or by the extruder
        it is loaded to.
        """

        if spool_name != None:
            spool_item = self._findByColumn(spool_name, 0)
        elif extruder != -1:
            spool_item = self._findByColumn(extruder, 2)
        else:
            return -1   # Not enough arguments

        if spool_item == -1:
            return -2   # No spool found for the given name or extruder

        length = spool_item[1] + increment
        self.remove(spool_item[0])
        self.add(spool_item[0], length)
        if spool_item[2] > -1:
            self.load(spool_item[0], spool_item[2])
        self._save()

        return 0

    def getExtruderCount(self):
        """int getExtruderCount()"""
        return self.parent.settings.extruders

    def getSpoolCount(self):
        """
        int getSpoolCount()

        Return the number of currently recorded spools.
        """
        return len(self._spool_list)

    def getSpoolList(self):
        """
        [N][2] getSpoolList ()

        Returns a list of the recorded spools. Returns a Nx2 matrix where N is
        the number of recorded spools. The first column contains the names of
        the spools and the second the lengths of remaining filament.
        """

        slist = []
        for i in range(self.getSpoolCount()):
            item = [self._spool_list[i][0], self._spool_list[i][1]]
            slist.append(item)
        return slist

    def _findByColumn(self, data, col = 0):
        """
        Find which spool_item from the list contains certain data.

        The 'col' argument specifies in which field from the spool_item to
        look for. For instance, with the following list:

            _spool_list = [["spool_1",   100.0, 1],
                           ["spool_2",   200.0, 0],
                           .
                           .
                           .
                           ["spool_10", 1000.0, 0]]

        A call like: _findByColumn("spool_2", 0)

        Will produce: ["spool_2", 200.0, 0]

        col = 0, would look into the "name's column"
        col = 1, would look into the "length's column"
        col = 2, would look into the "extruder's column"
        """

        for spool_item in self._spool_list:
            if data == spool_item[col]:
                return spool_item

        return -1

    def _save(self):
        """Update the list of recorded spools in the configuration file."""
        self._setSetting(self._spool_list, "spool_list")

    def _setSetting(self, variable, setting):
        """
        Write the given variable to the given setting of the configuration
        file.
        """
        n = 3 # number of fields in spool_item
        string_list = []
        for i in range(len(variable)):
            for j in range(n):
                string_list.append(str(variable[i][j]))
        separator = ", "
        self.parent.set(setting, separator.join(string_list))

    def _readSetting(self, setting):
        """
        Return the variable read.
        """
        n = 3 # number of fields in spool_item
        string_list = setting.split(", ")
        variable = []
        for i in range(len(string_list)//n):
            variable.append(
                [string_list[n*i],
                 float(string_list[n*i+1]),
                 int(string_list[n*i+2])])
        return variable
