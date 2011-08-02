"""
Text vertexes.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = TextDerivation(xmlElement)
	if derivation.textString == '':
		print('Warning, textString is empty in getGeometryOutput in text for:')
		print(xmlElement)
		return []
	geometryOutput = []
	for textComplexLoop in svg_reader.getTextComplexLoops(derivation.fontFamily, derivation.fontSize, derivation.textString):
		textComplexLoop.reverse()
		vector3Path = euclidean.getVector3Path(textComplexLoop)
		sideLoop = lineation.SideLoop(vector3Path, None, None)
		sideLoop.rotate(xmlElement)
		geometryOutput += lineation.getGeometryOutputByManipulation(sideLoop, xmlElement)
	return geometryOutput

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	evaluate.setAttributeDictionaryByArguments(['text', 'fontSize', 'fontFamily'], arguments, xmlElement)
	return getGeometryOutput(None, xmlElement)

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return TextDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class TextDerivation:
	"""Class to hold text variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.fontFamily = evaluate.getEvaluatedString('Gentium Basic Regular', 'font-family', xmlElement)
		self.fontFamily = evaluate.getEvaluatedString(self.fontFamily, 'fontFamily', xmlElement)
		self.fontSize = evaluate.getEvaluatedFloat(12.0, 'font-size', xmlElement)
		self.fontSize = evaluate.getEvaluatedFloat(self.fontSize, 'fontSize', xmlElement)
		self.textString = xmlElement.text
		self.textString = evaluate.getEvaluatedString(self.textString, 'text', xmlElement)

	def __repr__(self):
		"""Get the string representation of this TextDerivation."""
		return str(self.__dict__)
