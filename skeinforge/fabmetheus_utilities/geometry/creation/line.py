"""
Square path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
import math


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = LineDerivation(xmlElement)
	endMinusStart = derivation.end - derivation.start
	endMinusStartLength = abs(endMinusStart)
	if endMinusStartLength <= 0.0:
		print('Warning, end is the same as start in getGeometryOutput in line for:')
		print(derivation.start)
		print(derivation.end)
		print(xmlElement)
		return None
	typeStringTwoCharacters = derivation.typeString.lower()[: 2]
	xmlElement.attributeDictionary['closed'] = str(derivation.closed)
	if derivation.step is None and derivation.steps is None:
		return lineation.getGeometryOutputByLoop(lineation.SideLoop([derivation.start, derivation.end]), xmlElement)
	loop = [derivation.start]
	if derivation.step is not None and derivation.steps is not None:
		stepVector = derivation.step / endMinusStartLength * endMinusStart
		derivation.end = derivation.start + stepVector * derivation.steps
		return getGeometryOutputByStep(derivation.end, loop, derivation.steps, stepVector, xmlElement)
	if derivation.step is None:
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(derivation.end, loop, derivation.steps, stepVector, xmlElement)
	endMinusStartLengthOverStep = endMinusStartLength / derivation.step
	if typeStringTwoCharacters == 'av':
		derivation.steps = max(1.0, round(endMinusStartLengthOverStep))
		stepVector = derivation.step / endMinusStartLength * endMinusStart
		derivation.end = derivation.start + stepVector * derivation.steps
		return getGeometryOutputByStep(derivation.end, loop, derivation.steps, stepVector, xmlElement)
	if typeStringTwoCharacters == 'ma':
		derivation.steps = math.ceil(endMinusStartLengthOverStep)
		if derivation.steps < 1.0:
			return lineation.getGeometryOutputByLoop(lineation.SideLoop([derivation.start, derivation.end]), xmlElement)
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(derivation.end, loop, derivation.steps, stepVector, xmlElement)
	if typeStringTwoCharacters == 'mi':
		derivation.steps = math.floor(endMinusStartLengthOverStep)
		if derivation.steps < 1.0:
			return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop), xmlElement)
		stepVector = endMinusStart / derivation.steps
		return getGeometryOutputByStep(derivation.end, loop, derivation.steps, stepVector, xmlElement)
	print('Warning, the step type was not one of (average, maximum or minimum) in getGeometryOutput in line for:')
	print(derivation.typeString)
	print(xmlElement)
	loop.append(derivation.end)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop), xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['start', 'end', 'step'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getGeometryOutputByStep(end, loop, steps, stepVector, xmlElement):
	"""Get line geometry output by the end, loop, steps and stepVector."""
	stepsFloor = int(math.floor(abs(steps)))
	for stepIndex in xrange(1, stepsFloor):
		loop.append(loop[stepIndex - 1] + stepVector)
	loop.append(end)
	return lineation.getGeometryOutputByLoop(lineation.SideLoop(loop), xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return LineDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class LineDerivation:
	"""Class to hold line variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.closed = evaluate.getEvaluatedBoolean(False, 'closed', xmlElement)
		self.end = evaluate.getVector3ByPrefix(Vector3(), 'end', xmlElement)
		self.start = evaluate.getVector3ByPrefix(Vector3(), 'start', xmlElement)
		self.step = evaluate.getEvaluatedFloat(None, 'step', xmlElement)
		self.steps = evaluate.getEvaluatedFloat(None, 'steps', xmlElement)
		self.typeMenuRadioStrings = 'average maximum minimum'.split()
		self.typeString = evaluate.getEvaluatedString('minimum', 'type', xmlElement)

	def __repr__(self):
		"""Get the string representation of this LineDerivation."""
		return str(self.__dict__)
