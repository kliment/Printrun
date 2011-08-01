"""
Boolean geometry dictionary object.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_writer
import cStringIO


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getAllPaths(paths, xmlObject):
	"""Get all paths."""
	for archivableObject in xmlObject.archivableObjects:
		paths += archivableObject.getPaths()
	return paths

def getAllTransformedPaths(transformedPaths, xmlObject):
	"""Get all transformed paths."""
	for archivableObject in xmlObject.archivableObjects:
		transformedPaths += archivableObject.getTransformedPaths()
	return transformedPaths

def getAllTransformedVertexes(transformedVertexes, xmlObject):
	"""Get all transformed vertexes."""
	for archivableObject in xmlObject.archivableObjects:
		transformedVertexes += archivableObject.getTransformedVertexes()
	return transformedVertexes

def getAllVertexes(vertexes, xmlObject):
	"""Get all vertexes."""
	for archivableObject in xmlObject.archivableObjects:
		vertexes += archivableObject.getVertexes()
	return vertexes

def processXMLElement(xmlElement):
	"""Process the xml element."""
	evaluate.processArchivable( Dictionary, xmlElement)


class Dictionary:
	"""A dictionary object."""
	def __init__(self):
		"""Add empty lists."""
		self.archivableObjects = []
		self.xmlElement = None

	def __repr__(self):
		"""Get the string representation of this object info."""
		output = xml_simple_writer.getBeginGeometryXMLOutput(self.xmlElement)
		self.addXML( 1, output )
		return xml_simple_writer.getEndGeometryXMLString(output)

	def addXML(self, depth, output):
		"""Add xml for this object."""
		attributeCopy = {}
		if self.xmlElement is not None:
			attributeCopy = evaluate.getEvaluatedDictionaryByCopyKeys(['paths', 'target', 'vertexes'], self.xmlElement)
		euclidean.removeElementsFromDictionary(attributeCopy, matrix.getKeysM())
		euclidean.removeTrueFromDictionary(attributeCopy, 'visible')
		innerOutput = cStringIO.StringIO()
		self.addXMLInnerSection(depth + 1, innerOutput)
		self.addXMLArchivableObjects(depth + 1, innerOutput)
		xml_simple_writer.addBeginEndInnerXMLTag(attributeCopy, self.getXMLClassName(), depth, innerOutput.getvalue(), output)

	def addXMLArchivableObjects(self, depth, output):
		"""Add xml for this object."""
		xml_simple_writer.addXMLFromObjects( depth, self.archivableObjects, output )

	def addXMLInnerSection(self, depth, output):
		"""Add xml section for this object."""
		pass

	def createShape(self):
		"""Create the shape."""
		pass

	def getAttributeDictionary(self):
		"""Get attribute table."""
		if self.xmlElement is None:
			return {}
		return self.xmlElement.attributeDictionary

	def getComplexTransformedPathLists(self):
		"""Get complex transformed path lists."""
		complexTransformedPathLists = []
		for archivableObject in self.archivableObjects:
			complexTransformedPathLists.append(euclidean.getComplexPaths(archivableObject.getTransformedPaths()))
		return complexTransformedPathLists

	def getFabricationExtension(self):
		"""Get fabrication extension."""
		return 'xml'

	def getFabricationText(self, addLayerTemplate):
		"""Get fabrication text."""
		return self.__repr__()

	def getGeometryOutput(self):
		"""Get geometry output dictionary."""
		visibleObjects = evaluate.getVisibleObjects(self.archivableObjects)
		shapeOutput = []
		for visibleObject in visibleObjects:
			visibleObjectOutput = visibleObject.getGeometryOutput()
			if visibleObjectOutput is not None:
				shapeOutput.append(visibleObjectOutput)
		if len(shapeOutput) < 1:
			return None
		return {self.getXMLClassName() : {'shapes' : shapeOutput}}

	def getMatrix4X4(self):
		"""Get the matrix4X4."""
		return None

	def getMatrixChainTetragrid(self):
		"""Get the matrix chain tetragrid."""
		return self.xmlElement.parent.xmlObject.getMatrixChainTetragrid()

	def getMinimumZ(self):
		"""Get the minimum z."""
		return None

	def getPaths(self):
		"""Get all paths."""
		return getAllPaths([], self)

	def getTransformedPaths(self):
		"""Get all transformed paths."""
		return getAllTransformedPaths([], self)

	def getTransformedVertexes(self):
		"""Get all transformed vertexes."""
		return getAllTransformedVertexes([], self)

	def getTriangleMeshes(self):
		"""Get all triangleMeshes."""
		triangleMeshes = []
		for archivableObject in self.archivableObjects:
			triangleMeshes += archivableObject.getTriangleMeshes()
		return triangleMeshes

	def getType(self):
		"""Get type."""
		return self.__class__.__name__

	def getVertexes(self):
		"""Get all vertexes."""
		return getAllVertexes([], self)

	def getVisible(self):
		"""Get visible."""
		return False

	def getXMLClassName(self):
		"""Get xml class name."""
		return self.__class__.__name__.lower()

	def setToXMLElement(self, xmlElement):
		"""Set the shape of this carvable object info."""
		self.xmlElement = xmlElement
		xmlElement.parent.xmlObject.archivableObjects.append(self)
