#!/usr/bin/env python

from skeinforge.fabmetheus_utilities import archive
from skeinforge.fabmetheus_utilities import settings
from skeinforge.skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge.skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import wx

class SkeinforgeQuickEditDialog(wx.Dialog):
    '''Shows a consise list of important settings from the active Skeinforge profile.'''
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.RESIZE_BORDER
        wx.Dialog.__init__(self, *args, **kwds)
        self.okButton = wx.Button(self, wx.ID_OK, "Save")
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "")
        self.Bind(wx.EVT_BUTTON, self.OnExit, self.cancelButton)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.okButton)
        
        """
            The following list determines which settings are shown.
            The dictionary key is the plugin name and the value is a list of setting names as found in the corresponding .csv file for that plugin.
            
            NOTE:  Skeinforge is tightly integrated with Tkinter and there appears to be a dependency which stops radio-button values from being saved.
                   Perhaps this can be solved, but at the moment this dialog cannot modify radio button values.  One will have to use the main Skeinforge application.  
        """
        self.moduleSettingsMap = {
                                'dimension':['Filament Diameter (mm):','Retraction Distance (millimeters):', 'Retraction Distance (millimeters):','Extruder Retraction Speed (mm/s):'],
                                'carve':['Layer Height = Extrusion Thickness (mm):', 'Extrusion Width (mm):'],
                                'chamber':['Heated PrintBed Temperature (Celcius):', 'Turn print Bed Heater Off at Shut Down', 'Turn Extruder Heater Off at Shut Down'],
                                'cool':['Activate Cool.. but use with a fan!', 'Use Cool if layer takes shorter than(seconds):'],
                                'fill':['Activate Fill:', 'Infill Solidity (ratio):', 'Fully filled Layers (each top and bottom):', 'Extra Shells on Sparse Layer (layers):', 'Extra Shells on Alternating Solid Layer (layers):'],
                                'multiply':['Number of Columns (integer):', 'Number of Rows (integer):'],
                                'raft':['First Layer Main Feedrate (mm/s):','First Layer Perimeter Feedrate (mm/s):','First Layer Flow Rate Infill(scaler):','First Layer Flow Rate Perimeter(scaler):',],
                                'speed':['Main Feed Rate (mm/s):','Main Flow Rate  (scaler):','Perimeter Feed Rate (mm/s):','Perimeter Flow Rate (scaler):','Travel Feed Rate (mm/s):']
                               }
        
        self.scrollbarPanel = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        self.settingsSizer = self.getProfileSettings()
        self.scrollbarPanel.SetSizer(self.settingsSizer)

        self.__set_properties()   
        self.__do_layout()        
        self.Show()
        
    def __set_properties(self):
        self.profileName = skeinforge_profile.getProfileName(skeinforge_profile.getCraftTypeName())
        self.SetTitle("Skeinforge Quick Edit Profile: " + self.profileName)
        
        # For some reason the dialog size is not consistent between Windows and Linux - this is a hack to get it working 
        if (os.name == 'nt'):
            self.SetMinSize(wx.DLG_SZE(self, (465, 370)))
        else:
            self.SetSize(wx.DLG_SZE(self, (465, 325)))
            
        self.SetPosition((0, 0))
        self.scrollbarPanel.SetScrollRate(10, 10)
        
    def __do_layout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        actionsSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(self.scrollbarPanel, 1, wx.EXPAND | wx.ALL, 5)
        actionsSizer.Add(self.okButton, 0, 0, 0)
        actionsSizer.Add(self.cancelButton, 0, wx.LEFT, 10)
        mainSizer.Add(actionsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(mainSizer)
        self.Layout()
                
    def getProfileSettings(self):
        settingsSizer = wx.GridBagSizer(hgap=2, vgap=1)
        settingsRow = 0
        
        for craftName in sorted(self.moduleSettingsMap.keys()):
            
            craftStaticBox = wx.StaticBox(self.scrollbarPanel, -1, craftName.capitalize())
            craftStaticBoxSizer = wx.StaticBoxSizer(craftStaticBox, wx.VERTICAL)
            
            # For some reason the dialog size is not consistent between Windows and Linux - this is a hack to get it working
            if (os.name == 'nt'):
                craftStaticBoxSizer.SetMinSize((320, -1))
            else: 
                craftStaticBoxSizer.SetMinSize((450, -1))
            pluginModule = archive.getModuleWithPath(os.path.join(skeinforge_craft.getPluginsDirectoryPath(), craftName))
            repo = pluginModule.getNewRepository()
            
            for setting in settings.getReadRepository(repo).preferences:
                if setting.name in self.moduleSettingsMap[craftName]:
            
                    settingSizer = wx.GridBagSizer(hgap=2, vgap=2)
                    settingSizer.AddGrowableCol(0)
                    settingRow = 0
                    settingLabel = wx.StaticText(self.scrollbarPanel, -1, setting.name)
                    settingLabel.Wrap(400)
                    settingSizer.Add(settingLabel, pos=(settingRow, 0))
                    
                    if (isinstance(setting.value, bool)):
                        checkbox = wx.CheckBox(self.scrollbarPanel)
                        checkbox.SetName(craftName + '.' + setting.name)
                        checkbox.SetValue(setting.value)
                        settingSizer.Add(checkbox, pos=(settingRow, 1))
                        settingSizer.AddSpacer((25, -1), pos=(settingRow, 2))
                    else:
                        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=str(setting.value), size=(50, -1))
                        textCtrl.SetName(craftName + '.' + setting.name)
                        settingSizer.Add(textCtrl, pos=(settingRow, 1))
                        
                    craftStaticBoxSizer.Add(settingSizer, 1, wx.EXPAND, 0)
                    settingRow += 1
            col = settingsRow % 2
            settingsSizer.Add(craftStaticBoxSizer, pos=(settingsRow - col, col))
            settingsRow += 1

        return settingsSizer

    def OnExit(self, e):
        self.Destroy()
        
    def OnSave(self, e):
        for x in self.scrollbarPanel.GetChildren():
            if (isinstance(x, (wx.CheckBox, wx.TextCtrl))):
                name = x.GetName().partition('.')
                craftName = name[0]
                settingName = name[2]
                pluginModule = archive.getModuleWithPath(os.path.join(skeinforge_craft.getPluginsDirectoryPath(), craftName))
                repo = pluginModule.getNewRepository()
                isDirty = False
                for setting in settings.getReadRepository(repo).preferences:
                    if setting.name == settingName:
                        if setting.value == None or str(x.GetValue()) != str(setting.value):
                            print('Saving ... ' + settingName + ' = ' + str(x.GetValue()))
                            setting.value = x.GetValue()
                            isDirty = True
                if isDirty:
                    settings.saveRepository(repo)
        print("Skeinforge settings have been saved.")
        self.Destroy()

class SkeinforgeQuickEditApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        SkeinforgeQuickEditDialog(None, -1, "")
        return 1

if __name__ == "__main__":
    skeinforgeQuickEditApp = SkeinforgeQuickEditApp(0)
    skeinforgeQuickEditApp.MainLoop()
