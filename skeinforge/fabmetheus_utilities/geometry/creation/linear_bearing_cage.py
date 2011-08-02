"""
Linear bearing cage.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import extrude
from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.creation import peg
from fabmetheus_utilities.geometry.creation import solid
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.manipulation_matrix import translate
from fabmetheus_utilities.geometry.solids import cylinder
from fabmetheus_utilities.geometry.solids import sphere
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addAssemblyCage(derivation, negatives, positives):
	"""Add assembly linear bearing cage."""
	addCageGroove(derivation, negatives, positives)
	for pegCenterX in derivation.pegCenterXs:
		addPositivePeg(derivation, positives, pegCenterX, -derivation.pegY)
		addPositivePeg(derivation, positives, pegCenterX, derivation.pegY)
	translate.translateNegativesPositives(negatives, positives, Vector3(0.0, -derivation.halfSeparationWidth))
	femaleNegatives = []
	femalePositives = []
	addCageGroove(derivation, femaleNegatives, femalePositives)
	for pegCenterX in derivation.pegCenterXs:
		addNegativePeg(derivation, femaleNegatives, pegCenterX, -derivation.pegY)
		addNegativePeg(derivation, femaleNegatives, pegCenterX, derivation.pegY)
	translate.translateNegativesPositives(femaleNegatives, femalePositives, Vector3(0.0, derivation.halfSeparationWidth))
	negatives += femaleNegatives
	positives += femalePositives

def addCage(derivation, height, negatives, positives):
	"""Add linear bearing cage."""
	copyShallow = derivation.xmlElement.getCopyShallow()
	copyShallow.attributeDictionary['path'] = [Vector3(), Vector3(0.0, 0.0, height)]
	extrudeDerivation = extrude.ExtrudeDerivation(copyShallow)
	roundedExtendedRectangle = getRoundedExtendedRectangle(derivation.demiwidth, derivation.rectangleCenterX, 14)
	outsidePath = euclidean.getVector3Path(roundedExtendedRectangle)
	extrude.addPositives(extrudeDerivation, [outsidePath], positives)
	for bearingCenterX in derivation.bearingCenterXs:
		addNegativeSphere(derivation, negatives, bearingCenterX)

def addCageGroove(derivation, negatives, positives):
	"""Add cage and groove."""
	addCage(derivation, derivation.demiheight, negatives, positives)
	addGroove(derivation, negatives)

def addGroove(derivation, negatives):
	"""Add groove on each side of cage."""
	bottom = derivation.demiheight - 0.5 * derivation.grooveWidth
	outside = 1.0001 * derivation.demiwidth
	top = derivation.demiheight
	leftGroove = [
		complex(-outside, top),
		complex(-derivation.innerDemiwidth, derivation.demiheight),
		complex(-outside, bottom)]
	rightGroove = [
		complex(outside, bottom),
		complex(derivation.innerDemiwidth, derivation.demiheight),
		complex(outside, top)]
	extrude.addSymmetricXPaths(negatives, [leftGroove, rightGroove], derivation.demilength)

def addNegativePeg(derivation, negatives, x, y):
	"""Add negative cylinder at x and y."""
	negativePegRadius = derivation.pegRadius + derivation.halfPegClearance
	inradius = complex(negativePegRadius, negativePegRadius)
	copyShallow = derivation.xmlElement.getCopyShallow()
	start = Vector3(x, y, derivation.height)
	sides = evaluate.getSidesMinimumThreeBasedOnPrecision(negativePegRadius, copyShallow )
	cylinder.addCylinderOutputByEndStart(0.0, inradius, negatives, sides, start, derivation.topOverBottom)

def addNegativeSphere(derivation, negatives, x):
	"""Add negative sphere at x."""
	radius = Vector3(derivation.radiusPlusClearance, derivation.radiusPlusClearance, derivation.radiusPlusClearance)
	sphereOutput = sphere.getGeometryOutput(radius, derivation.xmlElement.getCopyShallow())
	euclidean.translateVector3Path(matrix.getVertexes(sphereOutput), Vector3(x, 0.0, derivation.demiheight))
	negatives.append(sphereOutput)

def addPositivePeg(derivation, positives, x, y):
	"""Add positive cylinder at x and y."""
	positivePegRadius = derivation.pegRadius - derivation.halfPegClearance
	radius = complex(positivePegRadius, positivePegRadius)
	copyShallow = derivation.xmlElement.getCopyShallow()
	start = Vector3(x, y, derivation.demiheight)
	endZ = derivation.height
	peg.addPegOutput(derivation.pegBevel, endZ, positives, radius, start, derivation.topOverBottom, copyShallow)

def getBearingCenterXs(bearingCenterX, numberOfSteps, stepX):
	"""Get the bearing center x list."""
	bearingCenterXs = []
	for stepIndex in xrange(numberOfSteps + 1):
		bearingCenterXs.append(bearingCenterX)
		bearingCenterX += stepX
	return bearingCenterXs

def getGeometryOutput(xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	derivation = LinearBearingCageDerivation(xmlElement)
	negatives = []
	positives = []
	if derivation.typeStringFirstCharacter == 'a':
		addAssemblyCage(derivation, negatives, positives)
	else:
		addCage(derivation, derivation.height, negatives, positives)
	return extrude.getGeometryOutputByNegativesPositives(negatives, positives, xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['length', 'radius'], arguments, xmlElement)
	return getGeometryOutput(xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return LinearBearingCageDerivation(xmlElement)

def getPegCenterXs(numberOfSteps, pegCenterX, stepX):
	"""Get the peg center x list."""
	pegCenterXs = []
	for stepIndex in xrange(numberOfSteps):
		pegCenterXs.append(pegCenterX)
		pegCenterX += stepX
	return pegCenterXs

def getRoundedExtendedRectangle(radius, rectangleCenterX, sides):
	"""Get the rounded extended rectangle."""
	roundedExtendedRectangle = []
	halfSides = int(sides / 2)
	halfSidesPlusOne = abs(halfSides + 1)
	sideAngle = math.pi / float(halfSides)
	extensionMultiplier = 1.0 / math.cos(0.5 * sideAngle)
	center = complex(rectangleCenterX, 0.0)
	startAngle = 0.5 * math.pi
	for halfSide in xrange(halfSidesPlusOne):
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		unitPolarExtended = complex(unitPolar.real * extensionMultiplier, unitPolar.imag)
		roundedExtendedRectangle.append(unitPolarExtended * radius + center)
		startAngle += sideAngle
	center = complex(-rectangleCenterX, 0.0)
	startAngle = -0.5 * math.pi
	for halfSide in xrange(halfSidesPlusOne):
		unitPolar = euclidean.getWiddershinsUnitPolar(startAngle)
		unitPolarExtended = complex(unitPolar.real * extensionMultiplier, unitPolar.imag)
		roundedExtendedRectangle.append(unitPolarExtended * radius + center)
		startAngle += sideAngle
	return roundedExtendedRectangle

def processXMLElement(xmlElement):
	"""Process the xml element."""
	solid.processXMLElementByGeometry(getGeometryOutput(xmlElement), xmlElement)


class LinearBearingCageDerivation:
	"""Class to hold linear bearing cage variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.length = evaluate.getEvaluatedFloat(50.0, 'length', xmlElement)
		self.demilength = 0.5 * self.length
		self.radius = lineation.getFloatByPrefixBeginEnd('radius', 'diameter', 5.0, xmlElement)
		self.cageClearanceOverRadius = evaluate.getEvaluatedFloat(0.05, 'cageClearanceOverRadius', xmlElement)
		self.cageClearance = self.cageClearanceOverRadius * self.radius
		self.cageClearance = evaluate.getEvaluatedFloat(self.cageClearance, 'cageClearance', xmlElement)
		self.racewayClearanceOverRadius = evaluate.getEvaluatedFloat(0.1, 'racewayClearanceOverRadius', xmlElement)
		self.racewayClearance = self.racewayClearanceOverRadius * self.radius
		self.racewayClearance = evaluate.getEvaluatedFloat(self.racewayClearance, 'racewayClearance', xmlElement)
		self.typeMenuRadioStrings = 'assembly integral'.split()
		self.typeString = evaluate.getEvaluatedString('assembly', 'type', xmlElement)
		self.typeStringFirstCharacter = self.typeString[: 1 ].lower()
		self.wallThicknessOverRadius = evaluate.getEvaluatedFloat(0.5, 'wallThicknessOverRadius', xmlElement)
		self.wallThickness = self.wallThicknessOverRadius * self.radius
		self.wallThickness = evaluate.getEvaluatedFloat(self.wallThickness, 'wallThickness', xmlElement)
		self.zenithAngle = evaluate.getEvaluatedFloat(45.0, 'zenithAngle', xmlElement)
		self.zenithRadian = math.radians(self.zenithAngle)
		self.demiheight = self.radius * math.cos(self.zenithRadian) - self.racewayClearance
		self.height = self.demiheight + self.demiheight
		self.radiusPlusClearance = self.radius + self.cageClearance
		self.cageRadius = self.radiusPlusClearance + self.wallThickness
		self.demiwidth = self.cageRadius
		self.bearingCenterX = self.cageRadius - self.demilength
		separation = self.cageRadius + self.radiusPlusClearance
		bearingLength = -self.bearingCenterX - self.bearingCenterX
		self.numberOfSteps = int(math.floor(bearingLength / separation))
		self.stepX = bearingLength / float(self.numberOfSteps)
		self.bearingCenterXs = getBearingCenterXs(self.bearingCenterX, self.numberOfSteps, self.stepX)
		self.xmlElement = xmlElement
		if self.typeStringFirstCharacter == 'a':
			self.setAssemblyCage()
		self.rectangleCenterX = self.demiwidth - self.demilength

	def __repr__(self):
		"""Get the string representation of this LinearBearingCageDerivation."""
		return str(self.__dict__)

	def setAssemblyCage(self):
		"""Set two piece assembly parameters."""
		self.grooveDepthOverRadius = evaluate.getEvaluatedFloat(0.15, 'grooveDepthOverRadius', self.xmlElement)
		self.grooveDepth = self.grooveDepthOverRadius * self.radius
		self.grooveDepth = evaluate.getEvaluatedFloat(self.grooveDepth, 'grooveDepth', self.xmlElement)
		self.grooveWidthOverRadius = evaluate.getEvaluatedFloat(0.6, 'grooveWidthOverRadius', self.xmlElement)
		self.grooveWidth = self.grooveWidthOverRadius * self.radius
		self.grooveWidth = evaluate.getEvaluatedFloat(self.grooveWidth, 'grooveWidth', self.xmlElement)
		self.pegClearanceOverRadius = evaluate.getEvaluatedFloat(0.0, 'pegClearanceOverRadius', self.xmlElement)
		self.pegClearance = self.pegClearanceOverRadius * self.radius
		self.pegClearance = evaluate.getEvaluatedFloat(self.pegClearance, 'pegClearance', self.xmlElement)
		self.halfPegClearance = 0.5 * self.pegClearance
		self.pegRadiusOverRadius = evaluate.getEvaluatedFloat(0.5, 'pegRadiusOverRadius', self.xmlElement)
		self.pegRadius = self.pegRadiusOverRadius * self.radius
		self.pegRadius = evaluate.getEvaluatedFloat(self.pegRadius, 'pegRadius', self.xmlElement)
		self.pegBevelOverPegRadius = evaluate.getEvaluatedFloat(0.25, 'pegBevelOverPegRadius', self.xmlElement)
		self.pegBevel = self.pegBevelOverPegRadius * self.pegRadius
		self.pegBevel = evaluate.getEvaluatedFloat(self.pegBevel, 'pegBevel', self.xmlElement)
		self.pegMaximumRadius = self.pegRadius + abs(self.halfPegClearance)
		self.separationOverRadius = evaluate.getEvaluatedFloat(0.5, 'separationOverRadius', self.xmlElement)
		self.separation = self.separationOverRadius * self.radius
		self.separation = evaluate.getEvaluatedFloat(self.separation, 'separation', self.xmlElement)
		self.topOverBottom = evaluate.getEvaluatedFloat(0.8, 'topOverBottom', self.xmlElement)
		self.quarterHeight = 0.5 * self.demiheight
		self.pegY = 0.5 * self.wallThickness + self.pegMaximumRadius
		cagePegRadius = self.cageRadius + self.pegMaximumRadius
		halfStepX = 0.5 * self.stepX
		pegHypotenuse = math.sqrt(self.pegY * self.pegY + halfStepX * halfStepX)
		if cagePegRadius > pegHypotenuse:
			self.pegY = math.sqrt(cagePegRadius * cagePegRadius - halfStepX * halfStepX)
		self.demiwidth = max(self.pegY + self.pegMaximumRadius + self.wallThickness, self.demiwidth)
		self.innerDemiwidth = self.demiwidth
		self.demiwidth += self.grooveDepth
		self.halfSeparationWidth = self.demiwidth + 0.5 * self.separation
		if self.pegRadius <= 0.0:
			self.pegCenterXs = []
		else:
			self.pegCenterXs = getPegCenterXs(self.numberOfSteps, self.bearingCenterX + halfStepX, self.stepX)
