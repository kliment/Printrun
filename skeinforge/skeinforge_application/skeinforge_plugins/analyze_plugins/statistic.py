"""
This page is in the table of contents.
Statistic is a script to generate statistics a gcode file.

The statistic manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Statistic

==Operation==
The default 'Activate Statistic' checkbox is on.  When it is on, the functions described below will work when called from the skeinforge toolchain, when it is off, the functions will not be called from the toolchain.  The functions will still be called, whether or not the 'Activate Statistic' checkbox is on, when statistic is run directly.

==Settings==
===Extrusion Diameter over Thickness===
Default is 1.25.

The 'Extrusion Diameter over Thickness is the ratio of the extrusion diameter over the layer thickness, the default is 1.25.  The extrusion fill density ratio that is printed to the console, ( it is derived quantity not a parameter ) is the area of the extrusion diameter over the extrusion width over the layer thickness.  Assuming the extrusion diameter is correct, a high value means the filament will be packed tightly, and the object will be almost as dense as the filament.  If the fill density ratio is too high, there could be too little room for the filament, and the extruder will end up plowing through the extra filament.  A low fill density ratio means the filaments will be far away from each other, the object will be leaky and light.  The fill density ratio with the default extrusion settings is around 0.68.

===Print Statistics===
Default is on.

When the 'Print Statistics' checkbox is on, the statistics will be printed to the console.

===Save Statistics===
Default is off.

When the 'Save Statistics' checkbox is on, the statistics will be saved as a .txt file.

==Gcodes==
An explanation of the gcodes is at:
http://reprap.org/bin/view/Main/Arduino_GCode_Interpreter

and at:
http://reprap.org/bin/view/Main/MCodeReference

A gode example is at:
http://forums.reprap.org/file.php?12,file=565

==Examples==
Below are examples of statistic being used.  These examples are run in a terminal in the folder which contains Screw Holder_penultimate.gcode and statistic.py.  The 'Save Statistics' checkbox is selected.

> python statistic.py
This brings up the statistic dialog.

> python statistic.py Screw Holder_penultimate.gcode
The statistic file is saved as Screw_Holder_penultimate_statistic.txt

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import cStringIO
import math
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	"""Get new repository."""
	return StatisticRepository()

def getWindowAnalyzeFile(fileName):
	"""Write statistics for a gcode file."""
	return getWindowAnalyzeFileGivenText( fileName, archive.getFileText(fileName) )

def getWindowAnalyzeFileGivenText( fileName, gcodeText, repository=None):
	"""Write statistics for a gcode file."""
	print('')
	print('')
	print('Statistics are being generated for the file ' + archive.getSummarizedFileName(fileName) )
	if repository is None:
		repository = settings.getReadRepository( StatisticRepository() )
	skein = StatisticSkein()
	statisticGcode = skein.getCraftedGcode(gcodeText, repository)
	if repository.printStatistics.value:
		print( statisticGcode )
	if repository.saveStatistics.value:
		archive.writeFileMessageEnd('.txt', fileName, statisticGcode, 'The statistics file is saved as ')

def writeOutput(fileName, fileNamePenultimate, fileNameSuffix, filePenultimateWritten, gcodeText=''):
	"""Write statistics for a skeinforge gcode file, if 'Write Statistics File for Skeinforge Chain' is selected."""
	repository = settings.getReadRepository( StatisticRepository() )
	if gcodeText == '':
		gcodeText = archive.getFileText( fileNameSuffix )
	if repository.activateStatistic.value:
		getWindowAnalyzeFileGivenText( fileNameSuffix, gcodeText, repository )


class StatisticRepository:
	"""A class to handle the statistics settings."""
	def __init__(self):
		"""Set the default settings, execute title & settings fileName."""
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.analyze_plugins.statistic.html', self)
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute('http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Statistic')
		self.activateStatistic = settings.BooleanSetting().getFromValue('Activate Statistic', self, True )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Cost -', self )
		self.machineTime = settings.FloatSpin().getFromValue( 0.0, 'Machine Time ($/hour):', self, 5.0, 1.0 )
		self.material = settings.FloatSpin().getFromValue( 0.0, 'Material ($/kg):', self, 40.0, 20.0 )
		settings.LabelSeparator().getFromRepository(self)
		self.density = settings.FloatSpin().getFromValue( 500.0, 'Density (kg/m3):', self, 2000.0, 930.0 )
		self.extrusionDiameterOverThickness = settings.FloatSpin().getFromValue( 1.0, 'Extrusion Diameter over Thickness (ratio):', self, 1.5, 1.25 )
		self.fileNameInput = settings.FileNameInput().getFromFileName( [ ('Gcode text files', '*.gcode') ], 'Open File to Generate Statistics for', self, '')
		self.printStatistics = settings.BooleanSetting().getFromValue('Print Statistics', self, True )
		self.saveStatistics = settings.BooleanSetting().getFromValue('Save Statistics', self, False )
		self.executeTitle = 'Generate Statistics'

	def execute(self):
		"""Write button has been clicked."""
		fileNames = skeinforge_polyfile.getFileOrGcodeDirectory( self.fileNameInput.value, self.fileNameInput.wasCancelled, ['_comment'] )
		for fileName in fileNames:
			getWindowAnalyzeFile(fileName)


class StatisticSkein:
	"""A class to get statistics for a gcode skein."""
	def __init__(self):
		self.extrusionDiameter = None
		self.oldLocation = None
		self.operatingFeedRatePerSecond = None
		self.output = cStringIO.StringIO()
		self.profileName = None
		self.version = None

	def addLine(self, line):
		"""Add a line of text and a newline to the output."""
		self.output.write(line + '\n')

	def addToPath(self, location):
		"""Add a point to travel and maybe extrusion."""
		if self.oldLocation is not None:
			travel = location.distance( self.oldLocation )
			if self.feedRateMinute > 0.0:
				self.totalBuildTime += 60.0 * travel / self.feedRateMinute
			self.totalDistanceTraveled += travel
			if self.extruderActive:
				self.totalDistanceExtruded += travel
				self.cornerMaximum.maximize(location)
				self.cornerMinimum.minimize(location)
		self.oldLocation = location

	def extruderSet( self, active ):
		"""Maybe increment the number of times the extruder was toggled."""
		if self.extruderActive != active:
			self.extruderToggled += 1
		self.extruderActive = active

	def getCraftedGcode(self, gcodeText, repository):
		"""Parse gcode text and store the statistics."""
		self.absolutePerimeterWidth = 0.4
		self.characters = 0
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		self.extruderActive = False
		self.extruderSpeed = None
		self.extruderToggled = 0
		self.feedRateMinute = 600.0
		self.layerThickness = 0.4
		self.numberOfLines = 0
		self.procedures = []
		self.repository = repository
		self.totalBuildTime = 0.0
		self.totalDistanceExtruded = 0.0
		self.totalDistanceTraveled = 0.0
		lines = archive.getTextLines(gcodeText)
		for line in lines:
			self.parseLine(line)
		averageFeedRate = self.totalDistanceTraveled / self.totalBuildTime
		self.characters += self.numberOfLines
		kilobytes = round( self.characters / 1024.0 )
		halfPerimeterWidth = 0.5 * self.absolutePerimeterWidth
		halfExtrusionCorner = Vector3( halfPerimeterWidth, halfPerimeterWidth, halfPerimeterWidth )
		self.cornerMaximum += halfExtrusionCorner
		self.cornerMinimum -= halfExtrusionCorner
		extent = self.cornerMaximum - self.cornerMinimum
		roundedHigh = euclidean.getRoundedPoint( self.cornerMaximum )
		roundedLow = euclidean.getRoundedPoint( self.cornerMinimum )
		roundedExtent = euclidean.getRoundedPoint( extent )
		axisString =  " axis extrusion starts at "
		crossSectionArea = 0.9 * self.absolutePerimeterWidth * self.layerThickness # 0.9 if from the typical fill density
		if self.extrusionDiameter is not None:
			crossSectionArea = math.pi / 4.0 * self.extrusionDiameter * self.extrusionDiameter
		volumeExtruded = 0.001 * crossSectionArea * self.totalDistanceExtruded
		mass = volumeExtruded / repository.density.value
		machineTimeCost = repository.machineTime.value * self.totalBuildTime / 3600.0
		materialCost = repository.material.value * mass
		self.addLine(' ')
		self.addLine('Cost')
		self.addLine( "Machine time cost is %s$." % round( machineTimeCost, 2 ) )
		self.addLine( "Material cost is %s$." % round( materialCost, 2 ) )
		self.addLine( "Total cost is %s$." % round( machineTimeCost + materialCost, 2 ) )
		self.addLine(' ')
		self.addLine('Extent')
		self.addLine( "X%s%s mm and ends at %s mm, for a width of %s mm." % ( axisString, int( roundedLow.x ), int( roundedHigh.x ), int( extent.x ) ) )
		self.addLine( "Y%s%s mm and ends at %s mm, for a depth of %s mm." % ( axisString, int( roundedLow.y ), int( roundedHigh.y ), int( extent.y ) ) )
		self.addLine( "Z%s%s mm and ends at %s mm, for a height of %s mm." % ( axisString, int( roundedLow.z ), int( roundedHigh.z ), int( extent.z ) ) )
		self.addLine(' ')
		self.addLine('Extruder')
		self.addLine( "Build time is %s." % euclidean.getDurationString( self.totalBuildTime ) )
		self.addLine( "Distance extruded is %s mm." % euclidean.getThreeSignificantFigures( self.totalDistanceExtruded ) )
		self.addLine( "Distance traveled is %s mm." % euclidean.getThreeSignificantFigures( self.totalDistanceTraveled ) )
		if self.extruderSpeed is not None:
			self.addLine( "Extruder speed is %s" % euclidean.getThreeSignificantFigures( self.extruderSpeed ) )
		self.addLine( "Extruder was extruding %s percent of the time." % euclidean.getThreeSignificantFigures( 100.0 * self.totalDistanceExtruded / self.totalDistanceTraveled ) )
		self.addLine( "Extruder was toggled %s times." % self.extruderToggled )
		if self.operatingFeedRatePerSecond is not None:
			flowRate = crossSectionArea * self.operatingFeedRatePerSecond
			self.addLine( "Operating flow rate is %s mm3/s." % euclidean.getThreeSignificantFigures( flowRate ) )
		self.addLine( "Feed rate average is %s mm/s, (%s mm/min)." % ( euclidean.getThreeSignificantFigures( averageFeedRate ), euclidean.getThreeSignificantFigures( 60.0 * averageFeedRate ) ) )
		self.addLine(' ')
		self.addLine('Filament')
		self.addLine( "Cross section area is %s mm2." % euclidean.getThreeSignificantFigures( crossSectionArea ) )
		if self.extrusionDiameter is not None:
			self.addLine( "Extrusion diameter is %s mm." % euclidean.getThreeSignificantFigures( self.extrusionDiameter ) )
		self.addLine('Extrusion fill density ratio is %s' % euclidean.getThreeSignificantFigures( crossSectionArea / self.absolutePerimeterWidth / self.layerThickness ) )
		self.addLine(' ')
		self.addLine('Material')
		self.addLine( "Mass extruded is %s grams." % euclidean.getThreeSignificantFigures( 1000.0 * mass ) )
		self.addLine( "Volume extruded is %s cc." % euclidean.getThreeSignificantFigures( volumeExtruded ) )
		self.addLine(' ')
		self.addLine('Meta')
		self.addLine( "Text has %s lines and a size of %s KB." % ( self.numberOfLines, kilobytes ) )
		if self.version is not None:
			self.addLine( "Version is "  + self.version )
		self.addLine(' ')
		self.addLine( "Procedures" )
		for procedure in self.procedures:
			self.addLine(procedure)
		if self.profileName is not None:
			self.addLine(' ')
			self.addLine( 'Profile' )
			self.addLine(self.profileName)
		self.addLine(' ')
		self.addLine('Slice')
		self.addLine( "Layer thickness is %s mm." % euclidean.getThreeSignificantFigures( self.layerThickness ) )
		self.addLine( "Perimeter width is %s mm." % euclidean.getThreeSignificantFigures( self.absolutePerimeterWidth ) )
		self.addLine(' ')
		return self.output.getvalue()

	def getLocationSetFeedRateToSplitLine( self, splitLine ):
		"""Get location ans set feed rate to the plsit line."""
		location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		indexOfF = gcodec.getIndexOfStartingWithSecond( "F", splitLine )
		if indexOfF > 0:
			self.feedRateMinute = gcodec.getDoubleAfterFirstLetter( splitLine[indexOfF] )
		return location

	def helicalMove( self, isCounterclockwise, splitLine ):
		"""Get statistics for a helical move."""
		if self.oldLocation is None:
			return
		location = self.getLocationSetFeedRateToSplitLine(splitLine)
		location += self.oldLocation
		center = self.oldLocation.copy()
		indexOfR = gcodec.getIndexOfStartingWithSecond( "R", splitLine )
		if indexOfR > 0:
			radius = gcodec.getDoubleAfterFirstLetter( splitLine[ indexOfR ] )
			halfLocationMinusOld = location - self.oldLocation
			halfLocationMinusOld *= 0.5
			halfLocationMinusOldLength = halfLocationMinusOld.magnitude()
			centerMidpointDistanceSquared = radius * radius - halfLocationMinusOldLength * halfLocationMinusOldLength
			centerMidpointDistance = math.sqrt( max( centerMidpointDistanceSquared, 0.0 ) )
			centerMinusMidpoint = euclidean.getRotatedWiddershinsQuarterAroundZAxis( halfLocationMinusOld )
			centerMinusMidpoint.normalize()
			centerMinusMidpoint *= centerMidpointDistance
			if isCounterclockwise:
				center.setToVector3( halfLocationMinusOld + centerMinusMidpoint )
			else:
				center.setToVector3( halfLocationMinusOld - centerMinusMidpoint )
		else:
			center.x = gcodec.getDoubleForLetter( "I", splitLine )
			center.y = gcodec.getDoubleForLetter( "J", splitLine )
		curveSection = 0.5
		center += self.oldLocation
		afterCenterSegment = location - center
		beforeCenterSegment = self.oldLocation - center
		afterCenterDifferenceAngle = euclidean.getAngleAroundZAxisDifference( afterCenterSegment, beforeCenterSegment )
		absoluteDifferenceAngle = abs( afterCenterDifferenceAngle )
		steps = int( round( 0.5 + max( absoluteDifferenceAngle * 2.4, absoluteDifferenceAngle * beforeCenterSegment.magnitude() / curveSection ) ) )
		stepPlaneAngle = euclidean.getWiddershinsUnitPolar( afterCenterDifferenceAngle / steps )
		zIncrement = ( afterCenterSegment.z - beforeCenterSegment.z ) / float( steps )
		for step in xrange( 1, steps ):
			beforeCenterSegment = euclidean.getRoundZAxisByPlaneAngle( stepPlaneAngle, beforeCenterSegment )
			beforeCenterSegment.z += zIncrement
			arcPoint = center + beforeCenterSegment
			self.addToPath( arcPoint )
		self.addToPath( location )

	def linearMove( self, splitLine ):
		"""Get statistics for a linear move."""
		location = self.getLocationSetFeedRateToSplitLine(splitLine)
		self.addToPath( location )

	def parseLine(self, line):
		"""Parse a gcode line and add it to the statistics."""
		self.characters += len(line)
		self.numberOfLines += 1
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			self.linearMove(splitLine)
		elif firstWord == 'G2':
			self.helicalMove( False, splitLine )
		elif firstWord == 'G3':
			self.helicalMove( True, splitLine )
		elif firstWord == 'M101':
			self.extruderSet( True )
		elif firstWord == 'M102':
			self.extruderSet( False )
		elif firstWord == 'M103':
			self.extruderSet( False )
		elif firstWord == '(<layerThickness>':
			self.layerThickness = float(splitLine[1])
			self.extrusionDiameter = self.repository.extrusionDiameterOverThickness.value * self.layerThickness
		elif firstWord == '(<operatingFeedRatePerSecond>':
			self.operatingFeedRatePerSecond = float(splitLine[1])
		elif firstWord == '(<perimeterWidth>':
			self.absolutePerimeterWidth = abs(float(splitLine[1]))
		elif firstWord == '(<procedureName>':
			self.procedures.append(splitLine[1])
		elif firstWord == '(<profileName>':
			self.profileName = line.replace('(<profileName>', '').replace('</profileName>)', '').strip()
		elif firstWord == '(<version>':
			self.version = splitLine[1]


def main():
	"""Display the statistics dialog."""
	if len(sys.argv) > 1:
		getWindowAnalyzeFile(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor( getNewRepository() )

if __name__ == "__main__":
	main()
