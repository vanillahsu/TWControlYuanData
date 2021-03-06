"""
The MIT License

Copyright (c) 2013 g0v

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
# encoding: utf-8
import os
import re
import getopt
import sys
import urllib
import json
import codecs
try:
    import lxml
    from bs4 import BeautifulSoup
except Exception, e:
    print "Please install package BeautifulSoup and lxml."
    exit()

default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

DEBUG = False
IS_DUMP_FILE = False
CAHCE_FILE = "./dump.log"
FETCH_URL = 'http://www.cy.gov.tw/sp.asp?xdUrl=.%2FDI%2Fedoc%2Fdb2.asp&ctNode=911&edoc_no=2&doQuery=1&intYear=&mm=&input_edoc_no=&case_pty=&input_edoc_unit=&keyword=&submit=%E6%9F%A5%E8%A9%A2'
DOWNLOAD_FOLDER = '../data/'
DOCUMENT_FOLDER = '../data/doc'
CONTROL_YUAN_URL = "http://www.cy.gov.tw/sp.asp?xdURL=./di/edoc/db2.asp&ctNode={0:d}&doQuery=1&cPage={1:d}&edoc_no={2:d}&intYear={3:s}"
EDOC_MAPPING = {910: 1, 911: 2, 912: 3, 913: 4}

def getDomain(url):
    reObj = re.match(r'(http://.+/)', url)
    return reObj.group()

def fetchPage(url):
    if DEBUG and os.path.exists(CAHCE_FILE):
        content = fetchPageFromFile(CAHCE_FILE)
    else:
        content = fetchPageFromURL(url)
    if IS_DUMP_FILE:
        fd = open(CAHCE_FILE, 'w')
        fd.write(content)
        fd.close
    return content

def fetchFileByList(table, caseType, year):
    for i in table:
        if i['docx'] != '':
            fetchFileFromUrl(i['docx'], caseType, year)

        if i['pdf'] != '':
            fetchFileFromUrl(i['pdf'], caseType, year)

def fetchFileFromUrl(url, caseType, year):
    tmp = urllib.unquote(url).split('/')
    path = os.path.join(DOCUMENT_FOLDER, str(caseType), year)
    if not os.access(path, os.F_OK):
        os.makedirs(path)
    filename = os.path.join(path, tmp[-1])
    urllib.urlretrieve(url, filename)

def fetchPageFromURL(url):
    return urllib.urlopen(url).read()

def fetchPageFromFile(file):
    fd = open(file, 'r')
    return fd.read()

def contentDownloader(caseType, year = '', page = 1):
    edoc = EDOC_MAPPING[caseType]
    url = CONTROL_YUAN_URL.format(caseType, page, edoc, year)
    content = fetchPage(url)
    return content

def createParser(content):
    return BeautifulSoup(content)

def caseParser(parser, content):
    talbe = parseCaseTable(parser)
    return talbe

def pageParser(parser, content):
    pageNum = parsePageNumber(parser)
    return pageNum

def yearParser(parser, content):
    return parseYearNumber(parser)

def page():
    pass

def normalizeContent(content):
    content = content.encode('utf-8')
    content = content.replace('\\', '/')
    content = content.replace(' ', '')
    content = content.replace('\t', '')
    content = content.replace('\n', '')
    content = content.replace('\r', '')
    return content

def insertCase(caseTable, content, index):
    item = index % 6
    caseNo = index / 6
    if item == 0:
        caseTable[caseNo] = {"date": content.text}
        pass
    elif item == 1:
        caseTable[caseNo]['id'] = normalizeContent(content.text)
        pass
    elif item == 2: 
        caseTable[caseNo]['describe'] = normalizeContent(content.text)
        pass
    elif item == 3:
        try:
            caseTable[caseNo]['docx'] = FETCH_DOMAIN + normalizeContent(content.a['href'])
        except:
            caseTable[caseNo]['docx'] = ''
    elif item == 4:
        try:
            caseTable[caseNo]['pdf'] = FETCH_DOMAIN + normalizeContent(content.a['href'])
        except:
            caseTable[caseNo]['pdf'] = ''
    elif item == 5:
        try:
            caseTable[caseNo]['reportLink'] = FETCH_DOMAIN + normalizeContent(content.a['href'])
        except Exception, e:
            caseTable[caseNo]['reportLink'] = ''
    pass

def parseYearNumber(parser):
    items = parser.find_all('form', attrs={'action': 'sp.asp'})[1].find_all(
            'select', attrs={'name': 'intYear'})[0].find_all('option')
    years = []
    for item in items:
        reObj = re.match(r'.*value="(\d+)".*', str(item))
        if reObj == None:
            continue
        years.append(reObj.group(1))
    return years

def parsePageNumber(parser):
    try:
        lastPage = parser.find('div', attrs={'class':'page'}).find_all('a')[-1]['href']
        reObj = re.match(r'.*cPage=(\d+).*', lastPage)
        return int(reObj.group(1))
    except Exception, e:
        return 0

def parseCaseTable(parser):
    cases = parser.find('div', attrs={'class': 'lpTb'}).find_all('td')
    caseNum = len(cases) / 6
    if caseNum == 0:
        return []

    caseTable = [None]*caseNum
    idx = 0
    for case in cases:
        insertCase(caseTable, case, idx)
        idx += 1
    return caseTable

def dumpToJson(table, caseType, year, page):
    fileName = "data_{0:d}_{1:s}_{2:d}.json".format(caseType, year, page)
    fd = codecs.open(os.path.join(DOWNLOAD_FOLDER, fileName), 'w', encoding="utf-8")
    json.dump(table, fd, indent=2, ensure_ascii=False)
    fd.close()
    pass

def crawlerByYear(caseType, year, download=False):
    print "Download case: {0:d}, year: {1:s}, page: {2:d}".format(caseType, year, 1)
    content = contentDownloader(caseType, year)
    parser = createParser(content)
    pageNum = pageParser(parser, content)
    table = caseParser(parser, content)
    if len(table) > 0:
        if download:
            fetchFileByList(table, caseType, year)
        dumpToJson(table, caseType, year, 1)

    for idx in xrange(2, pageNum + 1):
        print "Download case: {0:d}, year: {1:s}, page: {2:d}".format(caseType, year, idx)
        content = contentDownloader(caseType, year, idx)
        parser = createParser(content)
        table = caseParser(parser, content)
        if len(table) > 0:
            if download:
                fetchFileByList(table, caseType, year)
            dumpToJson(table, caseType, year, idx)

    pass

def crawlerByType(caseType, download=False):
    content = contentDownloader(caseType)
    parser = createParser(content)
    years = yearParser(parser, content)

    for year in years:
        crawlerByYear(caseType, year, download)

    pass

def main(argv):
    try:
        download = False
        opts, args = getopt.getopt(argv[1:], 'd')
        for opt, arg in opts:
            if opt in '-d':
                download = True

        crawlerByType(910, download)
        crawlerByType(911, download)
        crawlerByType(912, download)
        crawlerByType(913, download)

    except getopt.GetoptError:
        print "getopt error"
        sys.exit(1)

if __name__ == '__main__':
    FETCH_DOMAIN = getDomain(FETCH_URL)
    main(sys.argv)
