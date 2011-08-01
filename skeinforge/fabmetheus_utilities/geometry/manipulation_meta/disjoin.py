"""
Boolean geometry disjoin.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_tools import path
from fabmetheus_utilities.geometry.geometry_utilities.evaluate_elements import setting
from fabmetheus_utilities.geometry.geometry_utilities import boolean_geometry
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities.geometry.solids import difference
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities.vector3 import Vector3


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getLinkedXMLElement(idSuffix, parent, target):
	"""Get xmlElement with identifiers, importName and parent."""
	linkedXMLElement = xml_simple_reader.XMLElement()
	linkedXMLElement.importName = parent.importName
	euclidean.overwriteDictionary(target.attributeDictionary, ['id', 'name', 'quantity'], linkedXMLElement.attributeDictionary)
	linkedXMLElement.addSuffixToID(idSuffix)
	tagKeys = target.getTagKeys()
	tagKeys.append('disjoin')
	tagKeys.sort()
	tags = ', '.join(tagKeys)
	linkedXMLElement.attributeDictionary['tags'] = tags
	linkedXMLElement.setParentAddToChildren(parent)
	linkedXMLElement.addToIdentifierDictionaryIFIdentifierExists()
	return linkedXMLElement

def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return DisjoinDerivation(xmlElement)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	processXMLElementByDerivation(None, xmlElement)

def processXMLElementByDerivation(derivation, xmlElement):
	"""Process the xml element by derivation."""
	if derivation is None:
		derivation = DisjoinDerivation(xmlElement)
	targetXMLElement = derivation.targetXMLElement
	if targetXMLElement is None:
		print('Warning, disjoin could not get target for:')
		print(xmlElement)
		return
	xmlObject = targetXMLElement.xmlObject
	if xmlObject is None:
		print('Warning, processXMLElementByDerivation in disjoin could not get xmlObject for:')
		print(targetXMLElement)
		print(derivation.xmlElement)
		return
	transformedVertexes = xmlObject.getTransformedVertexes()
	if len(transformedVertexes) < 1:
		print('Warning, transformedVertexes is zero in processXMLElementByDerivation in disjoin for:')
		print(xmlObject)
		print(targetXMLElement)
		print(derivation.xmlElement)
		return
	xmlElement.className = 'group'
	xmlElement.getXMLProcessor().processXMLElement(xmlElement)
	matrix.getBranchMatrixSetXMLElement(targetXMLElement)
	targetChainMatrix = matrix.Matrix(xmlObject.getMatrixChainTetragrid())
	minimumZ = boolean_geometry.getMinimumZ(xmlObject)
	z = minimumZ + 0.5 * derivation.sheetThickness
	zoneArrangement = triangle_mesh.ZoneArrangement(derivation.layerThickness, transformedVertexes)
	oldVisibleString = targetXMLElement.attributeDictionary['visible']
	targetXMLElement.attributeDictionary['visible'] = True
	loops = boolean_geometry.getEmptyZLoops([xmlObject], derivation.importRadius, False, z, zoneArrangement)
	targetXMLElement.attributeDictionary['visible'] = oldVisibleString
	vector3Loops = euclidean.getVector3Paths(loops, z)
	pathElement = getLinkedXMLElement('_sheet', xmlElement, targetXMLElement)
	path.convertXMLElement(vector3Loops, pathElement)
	targetOutput = xmlObject.getGeometryOutput()
	differenceElement = getLinkedXMLElement('_solid', xmlElement, targetXMLElement)
	targetElementCopy = targetXMLElement.getCopy('_positive', differenceElement)
	targetElementCopy.attributeDictionary['visible'] = True
	targetElementCopy.attributeDictionary.update(targetChainMatrix.getAttributeDictionary('matrix.'))
	complexMaximum = euclidean.getMaximumByVector3Path(transformedVertexes).dropAxis()
	complexMinimum = euclidean.getMinimumByVector3Path(transformedVertexes).dropAxis()
	centerComplex = 0.5 * (complexMaximum + complexMinimum)
	centerVector3 = Vector3(centerComplex.real, centerComplex.imag, minimumZ)
	slightlyMoreThanHalfExtent = 0.501 * (complexMaximum - complexMinimum)
	inradius = Vector3(slightlyMoreThanHalfExtent.real, slightlyMoreThanHalfExtent.imag, derivation.sheetThickness)
	cubeElement = xml_simple_reader.XMLElement()
	cubeElement.attributeDictionary['inradius'] = str(inradius)
	if not centerVector3.getIsDefault():
		cubeElement.attributeDictionary['translate.'] = str(centerVector3)
	cubeElement.className = 'cube'
	cubeElement.importName = differenceElement.importName
	cubeElement.setParentAddToChildren(differenceElement)
	difference.processXMLElement(differenceElement)


class DisjoinDerivation:
	"""Class to hold disjoin variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.importRadius = setting.getImportRadius(xmlElement)
		self.layerThickness = setting.getLayerThickness(xmlElement)
		self.sheetThickness = setting.getSheetThickness(xmlElement)
		self.targetXMLElement = evaluate.getXMLElementByKey('target', xmlElement)

	def __repr__(self):
		"""Get the string representation of this DisjoinDerivation."""
		return str(self.__dict__)
