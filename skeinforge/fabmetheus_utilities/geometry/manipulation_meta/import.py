"""
Boolean geometry group of solids.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.solids import group
from fabmetheus_utilities import xml_simple_reader
from fabmetheus_utilities import xml_simple_writer
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
import cStringIO
import os


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Art of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewDerivation(xmlElement):
	"""Get new derivation."""
	return ImportDerivation(xmlElement)

def getXMLFromCarvingFileName(fileName):
	"""Get xml text from xml text."""
	carving = fabmetheus_interpret.getCarving(fileName)
	if carving is None:
		return ''
	output = xml_simple_writer.getBeginGeometryXMLOutput()
	carving.addXML(0, output)
	return xml_simple_writer.getEndGeometryXMLString(output)

def processXMLElement(xmlElement):
	"""Process the xml element."""
	processXMLElementByDerivation(None, xmlElement)

def processXMLElementByDerivation(derivation, xmlElement):
	"""Process the xml element by derivation."""
	if derivation is None:
		derivation = ImportDerivation(xmlElement)
	if derivation.fileName is None:
		return
	parserFileName = xmlElement.getParser().fileName
	absoluteFileName = archive.getAbsoluteFolderPath(parserFileName, derivation.fileName)
	if 'models/' not in absoluteFileName:
		print('Warning, models/ was not in the absolute file path, so for security nothing will be done for:')
		print(xmlElement)
		print('For which the absolute file path is:')
		print(absoluteFileName)
		print('The import tool can only read a file which has models/ in the file path.')
		print('To import the file, move the file into a folder called model/ or a subfolder which is inside the model folder tree.')
		return
	xmlText = ''
	if derivation.fileName.endswith('.xml'):
		xmlText = archive.getFileText(absoluteFileName)
	else:
		xmlText = getXMLFromCarvingFileName(absoluteFileName)
	print('The import tool is opening the file:')
	print(absoluteFileName)
	if xmlText == '':
		print('The file %s could not be found by processXMLElement in import.' % derivation.fileName)
		return
	if derivation.importName is None:
		xmlElement.importName = archive.getUntilDot(derivation.fileName)
		if derivation.basename:
			xmlElement.importName = os.path.basename(xmlElement.importName)
		xmlElement.attributeDictionary['_importName'] = xmlElement.importName
	else:
		xmlElement.importName = derivation.importName
	importXMLElement = xml_simple_reader.XMLElement()
	xml_simple_reader.XMLSimpleReader(parserFileName, importXMLElement, xmlText)
	for child in importXMLElement.children:
		child.copyXMLChildren('', xmlElement)
		evaluate.removeIdentifiersFromDictionary(child.attributeDictionary)
		xmlElement.attributeDictionary.update(child.attributeDictionary)
		if derivation.overwriteRoot:
			xmlElement.getRoot().attributeDictionary.update(child.attributeDictionary)
	xmlElement.className = 'group'
	evaluate.processArchivable(group.Group, xmlElement)


class ImportDerivation:
	"""Class to hold import variables."""
	def __init__(self, xmlElement):
		"""Set defaults."""
		self.basename = evaluate.getEvaluatedBoolean(True, 'basename', xmlElement)
		self.fileName = evaluate.getEvaluatedString('', 'file', xmlElement)
		self.importName = evaluate.getEvaluatedString(None, '_importName', xmlElement)
		self.overwriteRoot = evaluate.getEvaluatedBoolean(False, 'overwriteRoot', xmlElement)
		self.xmlElement = xmlElement

	def __repr__(self):
		"""Get the string representation of this ImportDerivation."""
		return str(self.__dict__)
