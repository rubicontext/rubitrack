import xml.dom.minidom


def traverseTree(document, depth=0):
    tag = document.tagName
    for child in document.childNodes:
        if child.nodeType == child.TEXT_NODE:
            # if document.tagName == 'Title':
            print(depth * '    ', child.data)
        if child.nodeType == xml.dom.Node.ELEMENT_NODE:
            traverseTree(child, depth + 1)


# filename = '/track/data/collection.nml'
# dom = xml.dom.minidom.parse(filename)
# traverseTree(dom.documentElement)
