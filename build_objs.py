#! /usr/bin/env/python

import lxml.etree as ET
import dumppdf
import re
from PDFUtils import unescapeHTMLEntities
def create_tree (fname ):
    xml = dumppdf.main(fname)
    #xml = unescapeHTMLEntities(xml)
    xml = re.sub("<.?xml", "xml_sub", xml, flags=re.M)
    #print xml
    return tree_from_xml(xml)

def tree_from_xml(xml):
    try:
        tree = ET.fromstring(xml)
        return tree
    except Exception as e:
        #print e.message
        if e.message.find("xmlParseCharRef") > -1:
            char = re.findall("value\s(\d*?),", e.message)
            xml = re.sub("&#" + char[0] + ";", "", xml)
            return tree_from_xml(xml)
        elif e.message.find("tag mismatch") > -1:
            lines = re.findall("\sline\s(\d*?)[\s,]", e.message)
            tag = re.findall(":\s(.*?)\s", e.message)
            if tag[0] == "pdf":
                return tree
            #print lines
            i = 0
            new_xml = ""
            for item in xml.split("\n"):
                i += 1
                if str(i) == lines[0]:
                   match = re.findall(tag[0] + "(.*?)>", item)
                   item = re.sub(tag[0] + match[0] + ">", tag[0] + match[0] + "/>", item)
                   new_xml += item + "\n"
                else:
                    new_xml += item + "\n"
            return tree_from_xml(new_xml)
        elif e.message.find("name") > -1:
            lines = re.findall("\sline\s(\d*?)[\s,]", e.message)
            i = 0
            new_xml = ""
            for item in xml.split("\n"):
                i += 1
                if str(i) == lines[0]:
                   new_xml += "<!--" + item + "-->\n"
                else:
                    new_xml += item + "\n"
            return tree_from_xml(new_xml)
        elif e.message.find("EntityRef: expecting ';'") > -1:
            lines = re.findall("\sline\s(\d*?)[\s,]", e.message)
            i = 0
            new_xml = ""
            for item in xml.split("\n"):
                i += 1
                if str(i) == lines[0]:
                   import cgi
                   new_xml += cgi.escape(item)
                else:
                    new_xml += item + "\n"
            return tree_from_xml(new_xml)
        else:
            return tree


def get_fields(root):
    ret = {}
    for key in root.iterfind("field"):
        print key.get("name")
        for elem in root.iterfind(key.get("name")):
            if elem.text != None:
                ret[key.get("name")] = unescapeHTMLEntities(elem.text)
    return ret

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
                          new[childs[2*i].text] = unescapeHTMLEntities(childs[2*i+1][0].text)
                      elif childs[2*i+1][0].tag == "ref":
                          for ob in root.iterfind(".//object"):
                              if ob.get("id") == childs[2*i+1][0].get("id"):
                                  for child in ob.iterdescendants(tag="data"):
                                     new[childs[2*i].text] = unescapeHTMLEntities(child.text)
                      else:
                           new[childs[2*i].text] = "Unknown tag: " + childs[2*i+1][0].tag
                  new["subject"] = new.pop("Subj")
                  app['doc']['annots'].append(new)
                  

def create_event_obj(tree):
    #
    #print xml
    #tree = create_tree(xml)
    event_attrs = ["author", "calculate", "creator", "creationDate", "delay", "dirty", "external", "filesize", "keywords", "modDate", "numFields", "numPages", "numTemplates", "path", "pageNum", "producer", "subject", "title", "zoom", "zoomType"]
    event = {}
    event["target"] ={}
    for item in event_attrs:
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        if elem != None:
            parent = elem.getparent()
            sibling = parent[parent.index(elem)+1][0]
            if sibling.tag == "string" and sibling.text != None:
                event["target"][item] = unescapeHTMLEntities(sibling.text)
            elif sibling.tag == "ref":
                for ob in tree.iterfind(".//object"):
                    if ob.get("id") == sibling.get("id"):
                        for child in ob.iterdescendants(tag="data"):
                            if child.text != None:
                                event["target"][item] = unescapeHTMLEntities(child.text)
            else:
                event["target"][item] = "Unknown tag: " + sibling.tag
    #print event
    return event

def create_app_obj(tree):
    app= {}
    app_attrs = ["calculate", "formsVersion", "fullscreen", "language", "numPlugins", "openInPlace", "platform", "toolbar", "toolbarHorizontal", "toolbarVertical"]
    doc = {}
    for item in app_attrs:
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        if elem != None:
            parent = elem.getparent()
            doc[item] = unescapeHTMLEntities(parent[parent.index(elem)+1][0].text)
    app['doc'] = doc;
    app['doc']['annots'] = []
    app['doc']['viewerType'] = 'Reader'
    app['viewerType'] = 'Reader'
    app['viewerVersion'] = 5.0
    app['plugIns'] = [{ 'version': 6.0}, {'version': 7.5}, {'version': 8.7},{'version': 9.1}]
    if not 'language' in app.keys():
        app['language'] = "ENU"
    if not 'platform' in app.keys():
        app['platform'] = "WIN"
    get_annots(app, tree)
    return app

def create_info_obj(tree):
    info_attrs = ["author", "creator", "creationDate", "Date", "keywords", "modDate", "producer", "subject", "title", "trapped"]
    this = {}
    this["info"] ={}
    for item in info_attrs:
        elem = search_tree(tree, ".//key", item[0].upper() + item[1:])
        if elem != None:
            parent = elem.getparent()
            sibling = parent[parent.index(elem)+1][0]
            if sibling.tag == "string" and sibling.text != None:
                this["info"][item] = unescapeHTMLEntities(sibling.text)
            elif sibling.tag == "ref":
                for ob in tree.iterfind(".//object"):
                    if ob.get("id") == sibling.get("id"):
                        for child in ob.iterdescendants(tag="data"):
                            this["info"][item] = unescapeHTMLEntities(child.text)
            else:
                this["info"][item] = "Unknown tag: " + sibling.tag
    #print this
    return this

