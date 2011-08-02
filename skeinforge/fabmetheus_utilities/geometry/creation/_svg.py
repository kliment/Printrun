"""
Svg reader.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.creation import lineation
from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_reader


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getGeometryOutput(derivation, xmlElement):
	"""Get vector3 vertexes from attribute dictionary."""
	if derivation is None:
		derivation = SVGDerivation(xmlElement)
	return getGeometryOutputBySVGReader(derivation.svgReader, xmlElement)

def getGeometryOutputByArguments(arguments, xmlElement):
	"""Get vector3 vertexes from attribute dictionary by arguments."""
	derivation = SVGDerivation()
	derivation.svgReader.parseSVG('', arguments[0])
	return getGeometryOutput(derivation, xmlElement)

def getGeometryOutputBySVGReader(svgReader, xmlElement):
	"""Get vector3 vertexes from svgReader."""
	geometryOutput = []
	for rotatedLoopLayer in svgReader.rotatedLoopLayers:
		for loop in rotatedLoopLayer.loops:
			vector3Path = euclidean.getVector3Path(loop, rotatedLoopLayer.z)
			sideLoop = lineation.SideLoop(vector3Path, None, None)
			sideLoop.rotate(xmlElement)
			geometryOutput += lineation.getGeometryOutputByManipulation(sideLoop, xmlElement)
	return geometryOutput

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return SVGDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	path.convertXMLElement(getGeometryOutput(None, xmlElement), xmlElement)


class SVGDerivation:
	"""Class to hold svg variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.svgReader = svg_reader.SVGReader()
		self.svgReader.parseSVGByXMLElement(xmlElement)

	def __repr__(self):
		"""Get the string representation of this SVGDerivation."""
		return str(self.__dict__)
