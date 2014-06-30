#! /usr/bin/env/python

import lxml.etree as ET
import dumppdf
import re
from PDFUtils import unescapeHTMLEntities
def create_tree ( xml ):
    try:
        tree = ET.fromstring(xml)
    except Exception as e:
        if e.message.find("xmlParseCharRef") > -1:
            char = re.findall("value\s(\d*?),", e.message)
            xml = re.sub("&#" + char[0] + ";", "", xml)
            return create_tree(xml)
    #tree = ET.fromstring(xml)
    return tree

#search tree for specified tag with specified value
def search_tree (root, tag, value ):
    for key in root.iterfind(tag):
        #print key.tag
        if key.text == value:
           return key
    else: 
        return None

def get_annots(app, root):
  for annot in root.iterfind(".//key"):
    if annot.text == "Annots":
        objs = []
        parent = annot.getparent()
        ref_list = parent[parent.index(annot)+1][0]
        for ref in ref_list:
          id = ref.get("id")
          for obj in root.iterfind(".//object"):
              if obj.get("id") == id:
                  size = obj[0].get("size")
                  size = re.sub("%", "", size)
                  new = {}
                  childs =  obj[0].getchildren()
                  for i in range(int(size)):
                      if childs[2*i+1][0].tag == "literal":
	                  new[childs[2*i].text] = childs[2*i+1][0].text
                      elif childs[2*i+1][0].tag == "ref":
		          for ob in root.iterfind(".//object"):
                              if ob.get("id") == childs[2*i+1][0].get("id"):
                                  for child in ob.iterdescendants(tag="data"):
                                     new[childs[2*i].text] = child.text
                      else:
                           new[childs[2*i].text] = "Unknown tag: " + childs[2*i+1][0].tag
                  new["subject"] = new.pop("Subj")
                  app['doc']['annots'].append(new)
                  

def create_event_obj(fname):
    xml = dumppdf.main(fname)
    #print xml
    tree = create_tree(xml)
    event_attrs = ["author", "calculate", "creator", "creationDate", "delay", "dirty", "external", "filesize", "keywords", "modDate", "numFields", "numPages", "numTemplates", "path", "pageNum", "producer", "subject", "title", "zoom", "zoomType"]
    event = {}
    event["target"] ={}
    for item in event_attrs:
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        if elem != None:
            parent = elem.getparent()
            sibling = parent[parent.index(elem)+1][0]
            if sibling.tag == "string":
                event["target"][item] = sibling.text
            elif sibling.tag == "ref":
                for ob in tree.iterfind(".//object"):
                    if ob.get("id") == sibling.get("id"):
                        for child in ob.iterdescendants(tag="data"):
                            event["target"][item] = child.text
            else:
                event["target"][item] = "Unknown tag: " + sibling.tag
    #print event
    return event

def create_app_obj(fname):
    xml = dumppdf.main(fname)
    import sys;
    reload(sys);
    sys.setdefaultencoding("utf8")
    #xml = unescapeHTMLEntities(xml)
    xml = re.sub("<.?xml", "xml_sub", xml, flags=re.M)
    #xml = "<xml>" + xml + "</xml>"
    #print xml
    tree = create_tree(xml)
    app= {}
    app_attrs = ["calculate", "formsVersion", "fullscreen", "language", "numPlugins", "openInPlace", "platform", "toolbar", "toolbarHorizontal", "toolbarVertical"]
    doc = {}
    for item in app_attrs:
        #print item[0].upper() + item[1:]
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        #print elem
        if elem != None:
            parent = elem.getparent()
            doc[item] = unescapeHTMLEntities(parent[parent.index(elem)+1][0].text)
    app['doc'] = doc;
    #app['doc']['syncAnnotScan'] = function () { };
    app['doc']['annots'] = []
    app['doc']['viewerType'] = 'Reader'
    #app['viewerVersion'] = 6.0
    app['plugIns'] = [{ 'version': 6.0}, {'version': 7.5}, {'version': 8.7},{'version': 9.1}]
    get_annots(app, tree)
    
    #print app
    return app

def create_info_obj(fname):
    xml = dumppdf.main(fname)
    #print xml
    tree = create_tree(xml)
    info_attrs = ["author", "creator", "creationDate", "keywords", "modDate", "producer", "subject", "title", "trapped"]
    this = {}
    this["info"] ={}
    for item in info_attrs:
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        if elem != None:
            parent = elem.getparent()
            #this["info"][item] = parent[parent.index(elem)+1][0].text
            sibling = parent[parent.index(elem)+1][0]
            if sibling.tag == "string":
                this["info"][item] = sibling.text
            elif sibling.tag == "ref":
                for ob in tree.iterfind(".//object"):
                    if ob.get("id") == sibling.get("id"):
                        for child in ob.iterdescendants(tag="data"):
                            this["info"][item] = child.text
            else:
                this["info"][item] = "Unknown tag: " + sibling.tag
    #print this
    return this

