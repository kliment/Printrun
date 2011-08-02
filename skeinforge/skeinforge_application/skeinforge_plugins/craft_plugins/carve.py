"""
This page is in the table of contents.
Carve is a script to carve a shape into svg slice layers.

The carve manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Carve

On the Arcol Blog a method of deriving the layer thickness is posted.  That article "Machine Calibrating" is at:
http://blog.arcol.hu/?p=157

==Settings==
===Add Layer Template to SVG===
Default is on.

When selected, the layer template will be added to the svg output, which adds javascript control boxes.  So 'Add Layer Template to SVG' should be selected when the svg will be viewed in a browser.

When off, no controls will be added, the svg output will only include the fabrication paths.  So 'Add Layer Template to SVG' should be deselected when the svg will be used by other software, like Inkscape.

===Extra Decimal Places===
Default is two.

Defines the number of extra decimal places export will output compared to the number of decimal places in the layer thickness.  The higher the 'Extra Decimal Places', the more significant figures the output numbers will have.

===Import Coarseness===
Default is one.

When a triangle mesh has holes in it, the triangle mesh slicer switches over to a slow algorithm that spans gaps in the mesh.  The higher the 'Import Coarseness' setting, the wider the gaps in the mesh it will span.  An import coarseness of one means it will span gaps of the perimeter width.

===Infill in Direction of Bridge===
Default is on.

When selected, the infill will be in the direction of any bridge across a gap, so that the fill will be able to span a bridge easier.

===Layer Thickness===
Default is 0.4 mm.

Defines the thickness of the extrusion layer at default extruder speed, this is the most important carve setting.

===Layers===
Carve slices from bottom to top.  To get a single layer, set the "Layers From" to zero and the "Layers To" to one.  The 'Layers From' until 'Layers To' range is a python slice.

====Layers From====
Default is zero.

Defines the index of the bottom layer that will be carved.  If the 'Layers From' is the default zero, the carving will start from the lowest layer.  If the 'Layers From' index is negative, then the carving will start from the 'Layers From' index below the top layer.

====Layers To====
Default is a huge number, which will be limited to the highest index layer.

Defines the index of the top layer that will be carved.  If the 'Layers To' index is a huge number like the default, the carving will go to the top of the model.  If the 'Layers To' index is negative, then the carving will go to the 'Layers To' index below the top layer.

===Mesh Type===
Default is 'Correct Mesh'.

====Correct Mesh====
When selected, the mesh will be accurately carved, and if a hole is found, carve will switch over to the algorithm that spans gaps.

====Unproven Mesh====
When selected, carve will use the gap spanning algorithm from the start.  The problem with the gap spanning algothm is that it will span gaps, even if there is not actually a gap in the model.

===Perimeter Width over Thickness===
Default is 1.8.

Defines the ratio of the extrusion perimeter width to the layer thickness.  The higher the value the more the perimeter will be inset, the default is 1.8.  A ratio of one means the extrusion is a circle, a typical ratio of 1.8 means the extrusion is a wide oval.  These values should be measured from a test extrusion line.

===SVG Viewer===
Default is webbrowser.

If the 'SVG Viewer' is set to the default 'webbrowser', the scalable vector graphics file will be sent to the default browser to be opened.  If the 'SVG Viewer' is set to a program name, the scalable vector graphics file will be sent to that program to be opened.

==Examples==
The following examples carve the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and carve.py.

> python carve.py
This brings up the carve dialog.

> python carve.py Screw Holder Bottom.stl
The carve tool is parsing the file:
Screw Holder Bottom.stl
..
The carve tool has created the file:
.. Screw Holder Bottom_carve.svg

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from fabmetheus_utilities import svg_writer
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftedText( fileName, gcodeText = '', repository=None):
	"""Get carved text."""
	if fileName.endswith('.svg'):
		gcodeText = archive.getTextIfEmpty(fileName, gcodeText)
		if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'carve'):
			return gcodeText
	carving = svg_writer.getCarving(fileName)
	if carving is None:
		return ''
	if repository is None:
		repository = CarveRepository()
		settings.getReadRepository(repository)
	return CarveSkein().getCarvedSVG( carving, fileName, repository )

def getNewRepository():
	"""Get new repository."""
	return CarveRepository()

def writeOutput(fileName, shouldAnalyze=True):
	"""Carve a GNU Triangulated Surface file."""
	startTime = time.time()
	print("File %s is being carved." % (archive.getSummarizedFileName(fileName)))
	repository = CarveRepository()
	settings.getReadRepository(repository)
	carveGcode = getCraftedText(fileName, '', repository)
	if carveGcode == '':
		return
	suffixFileName = archive.getFilePathWithUnderscoredBasename(fileName, '_carve.svg')
	archive.writeFileText(suffixFileName, carveGcode)
	print('The carved file is saved as ' + archive.getSummarizedFileName(suffixFileName))
	print('It took %s to carve the file.' % euclidean.getDurationString(time.time() - startTime))
	if shouldAnalyze:
		settings.openSVGPage(suffixFileName, repository.svgViewer.value)


class CarveRepository:
	"""A class to handle the carve settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.carve.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getTranslatorFileTypeTuples(), 'Open File for Carve', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Carve')
		settings.LabelDisplay().getFromName('- MAIN SETTINGS for Extrusion  -', self )
		settings.LabelSeparator().getFromRepository(self)
		self.layerThickness = settings.FloatSpin().getFromValue( 0.1, 'Layer Height = Extrusion Thickness (mm):', self, 1.0, 0.4 )
		self.perimeterWidth = settings.FloatSpin().getFromValue( 0.2, 'Extrusion Width (mm):', self, 1.0, 0.6 )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Layers to print -', self )
		self.layersFrom = settings.IntSpin().getFromValue( 0, 'Print from Layer No::', self, 3333, 0 )
		self.layersTo = settings.IntSpin().getSingleIncrementFromValue( 0, 'Print up to Layer No:', self, 912345678, 912345678 )
		settings.LabelSeparator().getFromRepository(self)		
		settings.LabelDisplay().getFromName('- Checked for technical parts, unchecked for organic pieces -', self )		
		self.infillInDirectionOfBridge = settings.BooleanSetting().getFromValue('Infill in Direction of Bridge', self, True )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Do not touch those below -', self )
		settings.LabelSeparator().getFromRepository(self)
		self.meshTypeLabel = settings.LabelDisplay().getFromName('Mesh Type: ', self )
		importLatentStringVar = settings.LatentStringVar()
		self.correctMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Correct Mesh', self, True )
		self.unprovenMesh = settings.Radio().getFromRadio( importLatentStringVar, 'Unproven Mesh', self, False )
		self.svgViewer = settings.StringSetting().getFromValue('SVG Viewer:', self, 'webbrowser')
		self.addLayerTemplateToSVG = settings.BooleanSetting().getFromValue('Add Layer Template to SVG', self, True)
		self.extraDecimalPlaces = settings.FloatSpin().getFromValue(0.0, 'Extra Decimal Places (float):', self, 3.0, 2.0)
		self.importCoarseness = settings.FloatSpin().getFromValue( 0.5, 'Import Coarseness (ratio):', self, 2.0, 1.0 )
		
		settings.LabelSeparator().getFromRepository(self)
		self.executeTitle = 'Carve'

	def execute(self):
		"""Carve button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypes(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class CarveSkein:
	"""A class to carve a carving."""
	def getCarvedSVG(self, carving, fileName, repository):
		"""Parse gnu triangulated surface text and store the carved gcode."""
		layerThickness = repository.layerThickness.value
		perimeterWidth = repository.perimeterWidth.value
		carving.setCarveInfillInDirectionOfBridge(repository.infillInDirectionOfBridge.value)
		carving.setCarveLayerThickness(layerThickness)
		importRadius = 0.5 * repository.importCoarseness.value * abs(perimeterWidth)
		carving.setCarveImportRadius(max(importRadius, 0.01 * layerThickness))
		carving.setCarveIsCorrectMesh(repository.correctMesh.value)
		rotatedLoopLayers = carving.getCarveRotatedBoundaryLayers()
		if len(rotatedLoopLayers) < 1:
			print('Warning, there are no slices for the model, this could be because the model is too small for the Layer Thickness.')
			return ''
		layerThickness = carving.getCarveLayerThickness()
		decimalPlacesCarried = euclidean.getDecimalPlacesCarried(repository.extraDecimalPlaces.value, layerThickness)
		perimeterWidth = repository.perimeterWidth.value
		svgWriter = svg_writer.SVGWriter(
			repository.addLayerTemplateToSVG.value,
			carving.getCarveCornerMaximum(),
			carving.getCarveCornerMinimum(),
			decimalPlacesCarried,
			carving.getCarveLayerThickness(),
			perimeterWidth)
		truncatedRotatedBoundaryLayers = svg_writer.getTruncatedRotatedBoundaryLayers(repository, rotatedLoopLayers)
		return svgWriter.getReplacedSVGTemplate(
			fileName, 'carve', truncatedRotatedBoundaryLayers, carving.getFabmetheusXML())


def main():
	"""Display the carve dialog."""
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == "__main__":
	main()
