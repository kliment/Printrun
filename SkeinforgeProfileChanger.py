#!/usr/bin/env python

from skeinforge.fabmetheus_utilities import archive
from skeinforge.fabmetheus_utilities import settings
from skeinforge.skeinforge_application.skeinforge_plugins.profile_plugins import extrusion
from skeinforge.skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import fileinput
import sys

class SkeinforgeProfileChanger():
    '''Provides a list of profiles and can change the active profile in skeinforge.'''
    def __init__(self, *args):
        None
        
    def getProfileNames(self):
        return settings.getFolders(archive.getProfilesPath('extrusion'))
    
    def getActiveProfileName(self):
        return skeinforge_profile.getProfileName('extrusion')
    
    def setActiveProfileName(self, newProfileName):
        ap = self.getActiveProfileName()

        extrusionRepository = extrusion.getNewRepository()
        extrusionSettingsFilename = os.path.join(archive.getProfilesPath() , settings.getProfileBaseName(extrusionRepository))
        for line in fileinput.FileInput(extrusionSettingsFilename, inplace=1):
            if "Profile Selection:\t"+ap in line:
                line = line.replace(ap, newProfileName)
            sys.stdout.write(line)
        print "Skeinforge Profile is " + newProfileName