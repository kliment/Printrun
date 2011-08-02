"""
Path.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import dictionary
from fabmetheus_utilities.geometry.geometry_tools import vertex
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import svg_writer
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities import xml_simple_writer


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def convertXMLElementByPath(geometryOutput, xmlElement):
	"""Convert the xml element to a path xml element."""
	createLinkPath(xmlElement)
	xmlElement.xmlObject.vertexes = geometryOutput
	vertex.addGeometryList(geometryOutput, xmlElement)

def convertXMLElement(geometryOutput, xmlElement):
	"""Convert the xml element by geometryOutput."""
	if geometryOutput is None:
		return
	if len(geometryOutput) < 1:
		return
	if len(geometryOutput) == 1:
		firstLoop = geometryOutput[0]
		if firstLoop.__class__ == list:
			geometryOutput = firstLoop
	firstElement = geometryOutput[0]
	if firstElement.__class__ == list:
		if len(firstElement) > 1:
			convertXMLElementRenameByPaths(geometryOutput, xmlElement)
		else:
			convertXMLElementByPath(firstElement, xmlElement)
	else:
		convertXMLElementByPath(geometryOutput, xmlElement)

def convertXMLElementRenameByPaths(geometryOutput, xmlElement):
	"""Convert the xml element to a path xml element and add paths."""
	createLinkPath(xmlElement)
	for geometryOutputChild in geometryOutput:
		pathElement = xml_simple_reader.XMLElement()
		pathElement.setParentAddToChildren(xmlElement)
		convertXMLElementByPath(geometryOutputChild, pathElement)

def createLinkPath(xmlElement):
	"""Create and link a path object."""
	xmlElement.className = 'path'
	xmlElement.linkObject(Path())

def processXMLElement(xmlElement):
	"""Process the xml element."""
	evaluate.processArchivable(Path, xmlElement)


class Path(dictionary.Dictionary):
	"""A path."""
	def __init__(self):
		"""Add empty lists."""
		dictionary.Dictionary.__init__(self)
		self.matrix4X4 = matrix.Matrix()
		self.oldChainTetragrid = None
		self.transformedPath = None
		self.vertexes = []

	def addXMLInnerSection(self, depth, output):
		"""Add the xml section for this object."""
		if self.matrix4X4 is not None:
			self.matrix4X4.addXML(depth, output)
		xml_simple_writer.addXMLFromVertexes(depth, output, self.vertexes)

	def getFabricationExtension(self):
		"""Get fabrication extension."""
		return 'svg'

	def getFabricationText(self, addLayerTemplate):
		"""Get fabrication text."""
		carving = SVGFabricationCarving(addLayerTemplate, self.xmlElement)
		carving.setCarveLayerThickness(setting.getSheetThickness(self.xmlElement))
		carving.processSVGElement(self.xmlElement.getRoot().parser.fileName)
		return str(carving)

	def getMatrix4X4(self):
		"""Get the matrix4X4."""
		return self.matrix4X4

	def getMatrixChainTetragrid(self):
		"""Get the matrix chain tetragrid."""
		return matrix.getTetragridTimesOther(self.xmlElement.parent.xmlObject.getMatrixChainTetragrid(), self.matrix4X4.tetragrid)

	def getPaths(self):
		"""Get all paths."""
		self.transformedPath = None
		if len(self.vertexes) > 0:
			return dictionary.getAllPaths([self.vertexes], self)
		return dictionary.getAllPaths([], self)

	def getTransformedPaths(self):
		"""Get all transformed paths."""
		if self.xmlElement is None:
			return dictionary.getAllPaths([self.vertexes], self)
		chainTetragrid = self.getMatrixChainTetragrid()
		if self.oldChainTetragrid != chainTetragrid:
			self.oldChainTetragrid = chainTetragrid
			self.transformedPath = None
		if self.transformedPath is None:
			self.transformedPath = matrix.getTransformedVector3s(chainTetragrid, self.vertexes)
		if len(self.transformedPath) > 0:
			return dictionary.getAllTransformedPaths([self.transformedPath], self)
		return dictionary.getAllTransformedPaths([], self)


class SVGFabricationCarving:
	"""An svg carving."""
	def __init__(self, addLayerTemplate, xmlElement):
		"""Add empty lists."""
		self.addLayerTemplate = addLayerTemplate
		self.layerThickness = 1.0
		self.rotatedLoopLayers = []
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this carving."""
		return self.getCarvedSVG()

	def addXML(self, depth, output):
		"""Add xml for this object."""
		xml_simple_writer.addXMLFromObjects(depth, self.rotatedLoopLayers, output)

	def getCarveCornerMaximum(self):
		"""Get the corner maximum of the vertexes."""
		return self.cornerMaximum

	def getCarveCornerMinimum(self):
		"""Get the corner minimum of the vertexes."""
		return self.cornerMinimum

	def getCarvedSVG(self):
		"""Get the carved svg text."""
		return svg_writer.getSVGByLoopLayers(self.addLayerTemplate, self, self.rotatedLoopLayers)

	def getCarveLayerThickness(self):
		"""Get the layer thickness."""
		return self.layerThickness

	def getCarveRotatedBoundaryLayers(self):
		"""Get the rotated boundary layers."""
		return self.rotatedLoopLayers

	def getFabmetheusXML(self):
		"""Return the fabmetheus XML."""
		return self.xmlElement.getParser().getOriginalRoot()

	def getInterpretationSuffix(self):
		"""Return the suffix for a carving."""
		return 'svg'

	def processSVGElement(self, fileName):
		"""Parse SVG element and store the layers."""
		self.fileName = fileName
		paths = self.xmlElement.xmlObject.getPaths()
		oldZ = None
		self.rotatedLoopLayers = []
		rotatedLoopLayer = None
		for path in paths:
			if len(path) > 0:
				z = path[0].z
				if z != oldZ:
					rotatedLoopLayer = euclidean.RotatedLoopLayer(z)
					self.rotatedLoopLayers.append(rotatedLoopLayer)
					oldZ = z
				rotatedLoopLayer.loops.append(euclidean.getComplexPath(path))
		if len(self.rotatedLoopLayers) < 1:
			return
		self.cornerMaximum = Vector3(-987654321.0, -987654321.0, -987654321.0)
		self.cornerMinimum = Vector3(987654321.0, 987654321.0, 987654321.0)
		svg_writer.setSVGCarvingCorners(self.cornerMaximum, self.cornerMinimum, self.layerThickness, self.rotatedLoopLayers)

	def setCarveInfillInDirectionOfBridge( self, infillInDirectionOfBridge ):
		"""Set the infill in direction of bridge."""
		pass

	def setCarveLayerThickness( self, layerThickness ):
		"""Set the layer thickness."""
		self.layerThickness = layerThickness

	def setCarveImportRadius( self, importRadius ):
		"""Set the import radius."""
		pass

	def setCarveIsCorrectMesh( self, isCorrectMesh ):
		"""Set the is correct mesh flag."""
		pass
