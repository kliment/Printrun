"""
This page is in the table of contents.
Some filaments contract too much and to prevent this you have to print the object in a temperature regulated chamber or on a temperature regulated bed. The chamber tool allows you to control the bed and chamber temperature and the holding pressure.  The gcodes are also described at:
http://reprap.org/wiki/Mendel_User_Manual:_RepRapGCodes

The chamber manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Chamber

==Operation==
The default 'Activate Chamber' checkbox is on.  When it is on, the functions described below will work, when it is off, the functions will not be called.

==Settings==
===Bed Temperature===
Default is 60C.

Defines the print_bed temperature in Celcius by adding an M140 command.

===Chamber Temperature===
Default is 30C.

Defines the chamber temperature in Celcius by adding an M141 command.

===Holding Force===
Default is zero.

Defines the holding pressure of a mechanism, like a vacuum table or electromagnet, to hold the bed surface or object, by adding an M142 command.  The holding pressure is in bar. For hardware which only has on/off holding, when the holding pressure is zero, turn off holding, when the holding pressure is greater than zero, turn on holding. 

==Heated Beds==
===Bothacker===
A resistor heated aluminum plate by Bothacker:
http://bothacker.com

with an article at:
http://bothacker.com/2009/12/18/heated-build-platform/

===Domingo===
A heated copper build plate by Domingo:
http://casainho-emcrepstrap.blogspot.com/

with articles at:
http://casainho-emcrepstrap.blogspot.com/2010/01/first-time-with-pla-testing-it-also-on.html
http://casainho-emcrepstrap.blogspot.com/2010/01/call-for-helpideas-to-develop-heated.html
http://casainho-emcrepstrap.blogspot.com/2010/01/new-heated-build-platform.html
http://casainho-emcrepstrap.blogspot.com/2010/01/no-acrylic-and-instead-kapton-tape-on.html
http://casainho-emcrepstrap.blogspot.com/2010/01/problems-with-heated-build-platform-and.html
http://casainho-emcrepstrap.blogspot.com/2010/01/perfect-build-platform.html
http://casainho-emcrepstrap.blogspot.com/2009/12/almost-no-warp.html
http://casainho-emcrepstrap.blogspot.com/2009/12/heated-base-plate.html

===Jmil===
A heated build stage by jmil, over at:
http://www.hive76.org

with articles at:
http://www.hive76.org/handling-hot-build-surfaces
http://www.hive76.org/heated-build-stage-success

===Kulitorum===
Kulitorum has made a heated bed.  It is a 5mm Alu sheet with a pattern laid out in kapton tape.  The wire is a 0.6mm2 Konstantin wire and it's held in place by small pieces of kapton tape.  The description and picture is at:
http://gallery.kulitorum.com/main.php?g2_itemId=283

===Metalab===
A heated base by the Metalab folks:
http://reprap.soup.io

with information at:
http://reprap.soup.io/?search=heated%20base

===Nophead===
A resistor heated aluminum bed by Nophead:
http://hydraraptor.blogspot.com

with articles at:
http://hydraraptor.blogspot.com/2010/01/will-it-stick.html
http://hydraraptor.blogspot.com/2010/01/hot-metal-and-serendipity.html
http://hydraraptor.blogspot.com/2010/01/new-year-new-plastic.html
http://hydraraptor.blogspot.com/2010/01/hot-bed.html

===Prusajr===
A resistive wire heated plexiglass plate by prusajr:
http://prusadjs.cz/

with articles at:
http://prusadjs.cz/2010/01/heated-reprap-print-bed-mk2/
http://prusadjs.cz/2009/11/look-ma-no-warping-heated-reprap-print-bed/

===Pumpernickel2===
A resistor heated aluminum plate by Pumpernickel2:
http://dev.forums.reprap.org/profile.php?14,844

with a picture at:
http://dev.forums.reprap.org/file.php?14,file=1228,filename=heatedplate.jpg

===Zaggo===
A resistor heated aluminum plate by Zaggo at Pleasant Software:
http://pleasantsoftware.com/developer/3d/

with articles at:
ttp://pleasantsoftware.com/developer/3d/2009/12/05/raftless/
http://pleasantsoftware.com/developer/3d/2009/11/15/living-in-times-of-warp-free-printing/
http://pleasantsoftware.com/developer/3d/2009/11/12/canned-heat/

==Examples==
The following examples chamber the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and chamber.py.

> python chamber.py
This brings up the chamber dialog.

> python chamber.py Screw Holder Bottom.stl
The chamber tool is parsing the file:
Screw Holder Bottom.stl
..
The chamber tool has created the file:
Screw Holder Bottom_chamber.gcode

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText(fileName, text='', repository=None):
	"""Chamber the file or text."""
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	"""Chamber a gcode linear move text."""
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'chamber'):
		return gcodeText
	if repository is None:
		repository = settings.getReadRepository(ChamberRepository())
	if not repository.activateChamber.value:
		return gcodeText
	return ChamberSkein().getCraftedGcode(gcodeText, repository)

def getNewRepository():
	"""Get new repository."""
	return ChamberRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"""Chamber a gcode linear move file."""
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'chamber', shouldAnalyze)


class ChamberRepository:
	"""A class to handle the chamber settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.chamber.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Chamber', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Chamber')
		self.activateChamber = settings.BooleanSetting().getFromValue('Activate Chamber..if you want below functions to work', self, False )
		settings.LabelSeparator().getFromRepository(self)
		self.bedTemperature = settings.FloatSpin().getFromValue( 20.0, 'Heated PrintBed Temperature (Celcius):', self, 130.0, 60.0 )
		settings.LabelSeparator().getFromRepository(self)
		self.turnBedHeaterOffAtShutDown = settings.BooleanSetting().getFromValue('Turn print Bed Heater Off at Shut Down', self, True )
		self.turnExtruderHeaterOffAtShutDown = settings.BooleanSetting().getFromValue('Turn Extruder Heater Off at Shut Down', self, True )
		self.executeTitle = 'Chamber'

	def execute(self):
		""""Chamber button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)



class ChamberSkein:
	"""A class to chamber a skein of extrusions."""
	def __init__(self):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lineIndex = 0
		self.lines = None

	def getCraftedGcode(self, gcodeText, repository):
		"""Parse gcode text and store the chamber gcode."""
		self.repository = repository
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		"""Parse gcode initialization and store the parameters."""
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addLine('(<procedureName> chamber </procedureName>)')
				return
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		"""Parse a gcode line and add it to the chamber skein."""
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == '(<crafting>)':
			self.distanceFeedRate.addLine(line)
			self.distanceFeedRate.addParameter('M140', self.repository.bedTemperature.value ) # Set bed temperature.

		elif firstWord == '(</crafting>)':
				self.distanceFeedRate.addLine(line)
				if self.repository.turnExtruderHeaterOffAtShutDown.value:
					self.distanceFeedRate.addLine('M104 S0') # Turn extruder heater off.
				if self.repository.turnBedHeaterOffAtShutDown.value:
					self.distanceFeedRate.addLine('M140 S0') # Turn bed heater off.
				return
		self.distanceFeedRate.addLine(line)


def main():
	"""Display the chamber dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == "__main__":
	main()
