"""
The xml_simple_reader.py script is an xml parser that can parse a line separated xml text.

This xml parser will read a line seperated xml text and produce a tree of the xml with a root element.  Each element can have an attribute table, children, a class name, parent, text and a link to the root element.

This example gets an xml tree for the xml file boolean.xml.  This example is run in a terminal in the folder which contains boolean.xml and xml_simple_reader.py.


> python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> fileName = 'boolean.xml'
>>> file = open(fileName, 'r')
>>> xmlText = file.read()
>>> file.close()
>>> from xml_simple_reader import XMLSimpleReader
>>> xmlParser = XMLSimpleReader(fileName, None, xmlText)
>>> print( xmlParser )
  ?xml, {'version': '1.0'}
  ArtOfIllusion, {'xmlns:bf': '//babelfiche/codec', 'version': '2.0', 'fileversion': '3'}
  Scene, {'bf:id': 'theScene'}
  materials, {'bf:elem-type': 'java.lang.Object', 'bf:list': 'collection', 'bf:id': '1', 'bf:type': 'java.util.Vector'}
..
many more lines of the xml tree
..

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.geometry.geometry_utilities import evaluate
from fabmetheus_utilities.geometry.geometry_utilities import matrix
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import xml_simple_writer
import cStringIO


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addXMLLine(line, xmlLines):
	"""Get the all the xml lines of a text."""
	strippedLine = line.strip()
	if strippedLine[ : len('<!--') ] == '<!--':
		endIndex = line.find('-->')
		if endIndex != - 1:
			endIndex += len('-->')
			commentLine = line[: endIndex]
			remainderLine = line[endIndex :].strip()
			if len(remainderLine) > 0:
				xmlLines.append(commentLine)
				xmlLines.append(remainderLine)
				return
	xmlLines.append(line)

def getXMLLines(text):
	"""Get the all the xml lines of a text."""
	accumulatedOutput = None
	textLines = archive.getTextLines(text)
	combinedLines = []
	lastWord = '>'
	for textLine in textLines:
		strippedLine = textLine.strip()
		firstCharacter = None
		lastCharacter = None
		if len( strippedLine ) > 1:
			firstCharacter = strippedLine[0]
			lastCharacter = strippedLine[-1]
		if firstCharacter == '<' and lastCharacter != '>' and accumulatedOutput is None:
			accumulatedOutput = cStringIO.StringIO()
			accumulatedOutput.write( textLine )
			if strippedLine[ : len('<!--') ] == '<!--':
				lastWord = '-->'
		else:
			if accumulatedOutput is None:
				addXMLLine( textLine, combinedLines )
			else:
				accumulatedOutput.write('\n' + textLine )
				if strippedLine[ - len( lastWord ) : ] == lastWord:
					addXMLLine( accumulatedOutput.getvalue(), combinedLines )
					accumulatedOutput = None
					lastWord = '>'
	xmlLines = []
	for combinedLine in combinedLines:
		xmlLines += getXMLTagSplitLines(combinedLine)
	return xmlLines

def getXMLTagSplitLines(combinedLine):
	"""Get the xml lines split at a tag."""
	characterIndex = 0
	lastWord = None
	splitIndexes = []
	tagEnd = False
	while characterIndex < len(combinedLine):
		character = combinedLine[characterIndex]
		if character == '"' or character == "'":
			lastWord = character
		elif combinedLine[characterIndex : characterIndex + len('<!--')] == '<!--':
			lastWord = '-->'
		elif combinedLine[characterIndex : characterIndex + len('<![CDATA[')] == '<![CDATA[':
			lastWord = ']]>'
		if lastWord is not None:
			characterIndex = combinedLine.find(lastWord, characterIndex + 1)
			if characterIndex == -1:
				return [combinedLine]
			character = None
			lastWord = None
		if character == '>':
			tagEnd = True
		elif character == '<':
			if tagEnd:
				if combinedLine[characterIndex : characterIndex + 2] != '</':
					splitIndexes.append(characterIndex)
		characterIndex += 1
	if len(splitIndexes) < 1:
		return [combinedLine]
	xmlTagSplitLines = []
	lastSplitIndex = 0
	for splitIndex in splitIndexes:
		xmlTagSplitLines.append(combinedLine[lastSplitIndex : splitIndex])
		lastSplitIndex = splitIndex
	xmlTagSplitLines.append(combinedLine[lastSplitIndex :])
	return xmlTagSplitLines


class XMLElement:
	"""An xml element."""
	def __init__(self):
		"""Add empty lists."""
		self.attributeDictionary = {}
		self.children = []
		self.className = ''
		self.idDictionary = {}
		self.importName = ''
		self.nameDictionary = {}
		self.parent = None
		self.tagDictionary = {}
		self.text=''
		self.xmlObject = None

	def __repr__(self):
		"""Get the string representation of this XML element."""
		return '%s\n%s\n%s' % ( self.className, self.attributeDictionary, self.text )

	def _getAccessibleAttribute(self, attributeName):
		"""Get the accessible attribute."""
		global globalGetAccessibleAttributeSet
		if attributeName in globalGetAccessibleAttributeSet:
			return getattr(self, attributeName, None)
		return None

	def addAttribute( self, beforeQuote, withinQuote ):
		"""Add the attribute to the dictionary."""
		beforeQuote = beforeQuote.strip()
		lastEqualIndex = beforeQuote.rfind('=')
		if lastEqualIndex < 0:
			return
		key = beforeQuote[ : lastEqualIndex ].strip()
		self.attributeDictionary[key] = withinQuote

	def addSuffixToID(self, idSuffix):
		"""Add the suffix to the id."""
		if 'id' in self.attributeDictionary:
			self.attributeDictionary['id'] += idSuffix

	def addToIdentifierDictionaryIFIdentifierExists(self):
		"""Add to the id dictionary if the id key exists in the attribute dictionary."""
		if 'id' in self.attributeDictionary:
			idKey = self.getImportNameWithDot() + self.attributeDictionary['id']
			self.getRoot().idDictionary[idKey] = self
		if 'name' in self.attributeDictionary:
			nameKey = self.getImportNameWithDot() + self.attributeDictionary['name']
			euclidean.addElementToListDictionaryIfNotThere(self, nameKey, self.getRoot().nameDictionary)
		for tagKey in self.getTagKeys():
			euclidean.addElementToListDictionaryIfNotThere(self, tagKey, self.getRoot().tagDictionary)

	def addXML(self, depth, output):
		"""Add xml for this xmlElement."""
		if self.className == 'comment':
			output.write( self.text )
			return
		innerOutput = cStringIO.StringIO()
		xml_simple_writer.addXMLFromObjects(depth + 1, self.children, innerOutput)
		innerText = innerOutput.getvalue()
		xml_simple_writer.addBeginEndInnerXMLTag(self.attributeDictionary, self.className, depth, innerText, output, self.text)

	def copyXMLChildren( self, idSuffix, parent ):
		"""Copy the xml children."""
		for child in self.children:
			child.getCopy( idSuffix, parent )

	def getCascadeFloat(self, defaultFloat, key):
		"""Get the cascade float."""
		if key in self.attributeDictionary:
			value = evaluate.getEvaluatedFloat(None, key, self)
			if value is not None:
				return value
		if self.parent is None:
			return defaultFloat
		return self.parent.getCascadeFloat(defaultFloat, key)

	def getChildrenWithClassName(self, className):
		"""Get the children which have the given class name."""
		childrenWithClassName = []
		for child in self.children:
			if className == child.className:
				childrenWithClassName.append(child)
		return childrenWithClassName

	def getChildrenWithClassNameRecursively(self, className):
		"""Get the children which have the given class name recursively."""
		childrenWithClassName = self.getChildrenWithClassName(className)
		for child in self.children:
			childrenWithClassName += child.getChildrenWithClassNameRecursively(className)
		return childrenWithClassName

	def getCopy(self, idSuffix, parent):
		"""Copy the xml element, set its dictionary and add it to the parent."""
		matrix4X4 = matrix.getBranchMatrixSetXMLElement(self)
		attributeDictionaryCopy = self.attributeDictionary.copy()
		attributeDictionaryCopy.update(matrix4X4.getAttributeDictionary('matrix.'))
		copy = self.getCopyShallow(attributeDictionaryCopy)
		copy.setParentAddToChildren(parent)
		copy.addSuffixToID(idSuffix)
		copy.text = self.text
		copy.addToIdentifierDictionaryIFIdentifierExists()
		self.copyXMLChildren(idSuffix, copy)
		return copy

	def getCopyShallow(self, attributeDictionary=None):
		"""Copy the xml element and set its dictionary and parent."""
		if attributeDictionary is None: # to evade default initialization bug where a dictionary is initialized to the last dictionary
			attributeDictionary = {}
		copyShallow = XMLElement()
		copyShallow.attributeDictionary = attributeDictionary
		copyShallow.className = self.className
		copyShallow.importName = self.importName
		copyShallow.parent = self.parent
		return copyShallow

	def getFirstChildWithClassName(self, className):
		"""Get the first child which has the given class name."""
		for child in self.children:
			if className == child.className:
				return child
		return None

	def getIDSuffix(self, elementIndex=None):
		"""Get the id suffix from the dictionary."""
		suffix = self.className
		if 'id' in self.attributeDictionary:
			suffix = self.attributeDictionary['id']
		if elementIndex is None:
			return '_%s' % suffix
		return '_%s_%s' % (suffix, elementIndex)

	def getImportNameWithDot(self):
		"""Get import name with dot."""
		if self.importName == '':
			return ''
		return self.importName + '.'

	def getParentParseReplacedLine(self, line, lineStripped, parent):
		"""Parse replaced line and return the parent."""
		if lineStripped[: len('<!--')] == '<!--':
			self.className = 'comment'
			self.text = line + '\n'
			self.setParentAddToChildren(parent)
			return parent
		if lineStripped[: len('</')] == '</':
			if parent is None:
				return parent
			return parent.parent
		self.setParentAddToChildren(parent)
		cdataBeginIndex = lineStripped.find('<![CDATA[')
		if cdataBeginIndex != - 1:
			cdataEndIndex = lineStripped.rfind(']]>')
			if cdataEndIndex != - 1:
				cdataEndIndex += len(']]>')
				self.text = lineStripped[cdataBeginIndex : cdataEndIndex]
				lineStripped = lineStripped[: cdataBeginIndex] + lineStripped[cdataEndIndex :]
		self.className = lineStripped[1 : lineStripped.replace('/>', ' ').replace('>', ' ').replace('\n', ' ').find(' ')]
		lastWord = lineStripped[-2 :]
		lineAfterClassName = lineStripped[2 + len(self.className) : -1]
		beforeQuote = ''
		lastQuoteCharacter = None
		withinQuote = ''
		for characterIndex in xrange(len(lineAfterClassName)):
			character = lineAfterClassName[characterIndex]
			if lastQuoteCharacter is None:
				if character == '"' or character == "'":
					lastQuoteCharacter = character
					character = ''
			if character == lastQuoteCharacter:
				self.addAttribute(beforeQuote, withinQuote)
				beforeQuote = ''
				lastQuoteCharacter = None
				withinQuote = ''
				character = ''
			if lastQuoteCharacter is None:
				beforeQuote += character
			else:
				withinQuote += character
		self.addToIdentifierDictionaryIFIdentifierExists()
		if lastWord == '/>':
			return parent
		tagEnd = '</%s>' % self.className
		if lineStripped[-len(tagEnd) :] == tagEnd:
			untilTagEnd = lineStripped[: -len(tagEnd)]
			lastGreaterThanIndex = untilTagEnd.rfind('>')
			self.text += untilTagEnd[ lastGreaterThanIndex + 1 : ]
			return parent
		return self

	def getParser(self):
		"""Get the parser."""
		return self.getRoot().parser

	def getPaths(self):
		"""Get all paths."""
		if self.xmlObject is None:
			return []
		return self.xmlObject.getPaths()

	def getPreviousVertex(self, defaultVector3=None):
		"""Get previous vertex if it exists."""
		if self.parent is None:
			return defaultVector3
		if self.parent.xmlObject is None:
			return defaultVector3
		if len(self.parent.xmlObject.vertexes) < 1:
			return defaultVector3
		return self.parent.xmlObject.vertexes[-1]

	def getPreviousXMLElement(self):
		"""Get previous XMLElement if it exists."""
		if self.parent is None:
			return None
		previousXMLElementIndex = self.parent.children.index(self) - 1
		if previousXMLElementIndex < 0:
			return None
		return self.parent.children[previousXMLElementIndex]

	def getRoot(self):
		"""Get the root element."""
		if self.parent is None:
			return self
		return self.parent.getRoot()

	def getSubChildWithID( self, idReference ):
		"""Get the child which has the idReference."""
		for child in self.children:
			if 'bf:id' in child.attributeDictionary:
				if child.attributeDictionary['bf:id'] == idReference:
					return child
			subChildWithID = child.getSubChildWithID( idReference )
			if subChildWithID is not None:
				return subChildWithID
		return None

	def getTagKeys(self):
		"""Get stripped tag keys."""
		if 'tags' not in self.attributeDictionary:
			return []
		tagKeys = []
		tagString = self.attributeDictionary['tags']
		if tagString.startswith('='):
			tagString = tagString[1 :]
		if tagString.startswith('['):
			tagString = tagString[1 :]
		if tagString.endswith(']'):
			tagString = tagString[: -1]
		for tagWord in tagString.split(','):
			tagKey = tagWord.strip()
			if tagKey != '':
				tagKeys.append(tagKey)
		return tagKeys

	def getValueByKey( self, key ):
		"""Get value by the key."""
		if key in evaluate.globalElementValueDictionary:
			return evaluate.globalElementValueDictionary[key](self)
		if key in self.attributeDictionary:
			return evaluate.getEvaluatedLinkValue( self.attributeDictionary[key], self )
		return None

	def getVertexes(self):
		"""Get the vertexes."""
		if self.xmlObject is None:
			return []
		return self.xmlObject.getVertexes()

	def getXMLElementByID(self, idKey):
		"""Get the xml element by id."""
		idDictionary = self.getRoot().idDictionary
		if idKey in idDictionary:
			return idDictionary[idKey]
		return None

	def getXMLElementByImportID(self, idKey):
		"""Get the xml element by import file name and id."""
		return self.getXMLElementByID( self.getImportNameWithDot() + idKey )

	def getXMLElementsByImportName(self, name):
		"""Get the xml element by import file name and name."""
		return self.getXMLElementsByName( self.getImportNameWithDot() + name )

	def getXMLElementsByName(self, name):
		"""Get the xml elements by name."""
		nameDictionary = self.getRoot().nameDictionary
		if name in nameDictionary:
			return nameDictionary[name]
		return None

	def getXMLElementsByTag(self, tag):
		"""Get the xml elements by tag."""
		tagDictionary = self.getRoot().tagDictionary
		if tag in tagDictionary:
			return tagDictionary[tag]
		return None

	def getXMLProcessor(self):
		"""Get the xmlProcessor."""
		return self.getRoot().xmlProcessor

	def linkObject(self, xmlObject):
		"""Link self to xmlObject and add xmlObject to archivableObjects."""
		self.xmlObject = xmlObject
		self.xmlObject.xmlElement = self
		self.parent.xmlObject.archivableObjects.append(self.xmlObject)

	def printAllVariables(self):
		"""Print all variables."""
		print('attributeDictionary')
		print(self.attributeDictionary)
		print('children')
		print(self.children)
		print('className')
		print(self.className)
		print('idDictionary')
		print(self.idDictionary)
		print('importName')
		print(self.importName)
		print('nameDictionary')
		print(self.nameDictionary)
		print('parent')
		print(self.parent)
		print('tagDictionary')
		print(self.tagDictionary)
		print('text')
		print(self.text)
		print('xmlObject')
		print(self.xmlObject)
		print('')

	def printAllVariablesRoot(self):
		"""Print all variables and the root variables."""
		self.printAllVariables()
		root = self.getRoot()
		if root is not None and root != self:
			print('')
			print('Root variables:')
			root.printAllVariables()

	def removeChildrenFromIDNameParent(self):
		"""Remove the children from the id and name dictionaries and the children list."""
		childrenCopy = self.children[:]
		for child in childrenCopy:
			child.removeFromIDNameParent()

	def removeFromIDNameParent(self):
		"""Remove this from the id and name dictionaries and the children of the parent."""
		self.removeChildrenFromIDNameParent()
		if 'id' in self.attributeDictionary:
			idDictionary = self.getRoot().idDictionary
			idKey = self.getImportNameWithDot() + self.attributeDictionary['id']
			if idKey in idDictionary:
				del idDictionary[idKey]
		if 'name' in self.attributeDictionary:
			nameDictionary = self.getRoot().nameDictionary
			nameKey = self.getImportNameWithDot() + self.attributeDictionary['name']
			euclidean.removeElementFromListTable(self, nameKey, nameDictionary)
		for tagKey in self.getTagKeys():
			euclidean.removeElementFromListTable(self, tagKey, self.getRoot().tagDictionary)
		if self.parent is not None:
			self.parent.children.remove(self)

	def setParentAddToChildren(self, parent):
		"""Set the parent and add this to its children."""
		self.parent = parent
		if self.parent is not None:
			self.parent.children.append(self)


class XMLSimpleReader:
	"""A simple xml parser."""
	def __init__(self, fileName, parent, xmlText):
		"""Add empty lists."""
		self.beforeRoot = ''
		self.fileName = fileName
		self.isXML = False
		self.numberOfWarnings = 0
		self.parent = parent
		self.root = None
		if parent is not None:
			self.root = parent.getRoot()
		self.lines = getXMLLines(xmlText)
		for self.lineIndex, line in enumerate(self.lines):
			self.parseLine(line)
		self.xmlText = xmlText
	
	def __repr__(self):
		"""Get the string representation of this parser."""
		return str( self.root )

	def getOriginalRoot(self):
		"""Get the original reparsed root element."""
		if evaluate.getEvaluatedBoolean(True, 'getOriginalRoot', self.root):
			return XMLSimpleReader(self.fileName, self.parent, self.xmlText).root
		return None

	def getRoot(self):
		"""Get the root element."""
		return self.root

	def parseLine(self, line):
		"""Parse an xml line and add it to the xml tree."""
		lineStripped = line.strip()
		if len( lineStripped ) < 1:
			return
		if lineStripped.startswith('<?xml'):
			self.isXML = True
			return
		if not self.isXML:
			if self.numberOfWarnings < 1:
				print('Warning, xml file should start with <?xml.')
				print('Until it does, parseLine in XMLSimpleReader will do nothing for:')
				print(self.fileName)
				self.numberOfWarnings += 1
			return
		xmlElement = XMLElement()
		self.parent = xmlElement.getParentParseReplacedLine( line, lineStripped, self.parent )
		if self.root is not None:
			return
		lowerClassName = xmlElement.className.lower()
		if lowerClassName == 'comment' or lowerClassName == '!doctype':
			return
		self.root = xmlElement
		self.root.parser = self
		for line in self.lines[ : self.lineIndex ]:
			self.beforeRoot += line + '\n'


globalGetAccessibleAttributeSet = set('getPaths getPreviousVertex getPreviousXMLElement getVertexes parent'.split())
