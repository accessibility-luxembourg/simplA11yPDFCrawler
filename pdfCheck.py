from pikepdf import Pdf, String, _qpdf
import pikepdf
from pikepdf.models.metadata import decode_pdf_date
from datetime import datetime
from langcodes import Language, tag_parser
import xml.etree.ElementTree as ET
import re, json, csv, os, pytz, typer, dateparser
from bitstring import BitArray

app = typer.Typer()

deadlineDateStr = '2018-09-23T00:00:00+02:00'
outputFields = [ 'Site', 'File', 'Accessible', 'TotallyInaccessible', 'BrokenFile', 'TaggedTest', 'EmptyTextTest', 'ProtectedTest', 'TitleTest', 'LanguageTest', 'BookmarksTest', 'Exempt', 'Date', 'hasTitle', 'hasDisplayDocTitle',  'hasLang', 'InvalidLang', 'Form',  'xfa', 'hasBookmarks', 'hasXmp', 'PDFVersion', 'Creator', 'Producer', 'Pages', '_log', 'fonts', 'numTxtObjects']
debug = False

def extract_date(s: str) -> datetime:
    if (s is None):
        return None
    if isinstance(s, String):
        s = str(s)
    try:
        return dateparser.parse(s, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
    except ValueError:
        return None


def extract_pdf_date(s: str) -> datetime:
    if (s is None):
        return None
    if isinstance(s, String):
        s = str(s)
    s = s.strip()
    if (len(s) == 0):
        return None
    if (s.startswith('CPY Document')):
        return None

    # manage malformed timezones (ex: +01, +1'0', +01'00', + 1' 0')
    m = re.search(r'\+([\d\':\s]+)$', s)
    if (m is not None):
        tz = m.group(0)
        inittz = tz
        if (len(tz) == 3):
            tz = tz + '00'
        if ('\'' in tz):
            n = re.search(r'\+\s?(\d+)\'\s?(\d+)\'?', tz)
            if (n is not None):
                tz = "+%02d%02d" % (int(n.group(1)), int(n.group(2)))
            else:
                tz = "+0000"
        s = s.replace(inittz, tz)
    try:
        pdf_date = decode_pdf_date(s) 
        # we add a timezone when it is missing
        # it can of course be inaccurate, but we don't really need a precision < 1 day
        if (not(pdf_date.tzinfo is not None and pdf_date.tzinfo.utcoffset(pdf_date) is not None)):
            pdf_date = pdf_date.replace(tzinfo=pytz.utc)
        return pdf_date
    except ValueError:
        return extract_date(s)

def initAnalysis():
    res = {}
    res['numTxt'] = 0
    res['fontNames'] = set()
    return res    

def mergeAnalyses(a, b):
    res = {}
    for i in a.keys():
        if (i == 'fontNames'):
            res[i] = set.union(a[i], b[i])
        else:
            res[i] = a[i] + b[i]
    return res

def analyseContent(content, isXObject:bool = False):
    res = initAnalysis()
    if (content.get('/Resources') is not None):
        xobject = content.Resources.get('/XObject')
        if (xobject is not None):
            for i in xobject:
                if (str(xobject[i].get('/Subtype')) == '/Form' and xobject[i].get('/Ref') == None):
                    res = mergeAnalyses(res, analyseContent(xobject[i], True))

        if (content.Resources.get('/Font') is not None):        
            # get all font names 
            for i in content.Resources.Font:
                font = content.Resources.Font[i]
                fontName = None
                if (font.get('/FontDescriptor') is not None):
                    fontName = str(content.Resources.Font[i].FontDescriptor.FontName)
                else:
                    fontName = str(content.Resources.Font[i].get('/BaseFont'))
                res['fontNames'].add(fontName)

            # count the number of text objects
            for operands, operator in pikepdf.parse_content_stream(content, "Tf"):
                res['numTxt'] += 1
                
    return res

def checkFile(fileName: str, site: str = None, debug: bool = False):
    result = {}

    for f in outputFields:
        result[f] = None
    result['Site'] = site
    result['File'] = os.path.basename(fileName)
    result['_log'] = ''
    result['Accessible'] = True # presumption of conformity :)
    result['Exempt'] = False
    result['TotallyInaccessible'] = False

    try:
        pdf = Pdf.open(fileName)
        result['PDFVersion'] = pdf.pdf_version
        result['Pages'] = len(pdf.pages)

        # check if is exempted? (based on which date?)
        meta = pdf.open_metadata()
        if (meta is None):
            result['hasXmp'] = False
            result['Accessible'] = False # Matterhorn 06-001 # FIXME is it really an accessibility issue?
            result['_log'] += 'xmp '
        else:
            result['hasXmp'] = True
            result['Creator'] = meta.get('xmp:CreatorTool')
            result['Producer'] = meta.get('pdf:Producer')

            xmpModifyDate = extract_date(meta.get('xmp:ModifyDate'))
            dcModifiedDate = extract_date(meta.get('dc:Modified'))
            modDate = extract_pdf_date(pdf.docinfo.get('/ModDate'))
            createDate = extract_date(meta.get('xmp:CreateDate'))
            creationDate = extract_pdf_date(pdf.docinfo.get('/CreationDate'))

            date = xmpModifyDate or dcModifiedDate or modDate or createDate or creationDate

            if (date is not None):
                deadlineDate = datetime.strptime(deadlineDateStr, '%Y-%m-%dT%H:%M:%S%z')
                result['Date'] = str(date)
                if (date < deadlineDate):
                    result['Exempt'] = True
            else:
                result['_log'] += 'no date found, ' 

            # check if has Title
            result['TitleTest'] = 'Pass'
            title = meta.get('dc:title') or pdf.docinfo.get('/Title') # here we go further than Matterhorn 06-003 to avoid false positives
            viewerPrefs = pdf.Root.get('/ViewerPreferences')
            if (title is not None and len(str(title)) != 0):
                result['hasTitle'] = True
                if (viewerPrefs is not None):
                    dispDocTitle = viewerPrefs.get('/DisplayDocTitle')
                    if (dispDocTitle is not None):
                        if (dispDocTitle == False): # Matterhorn 07-002
                            result['TitleTest'] = 'Fail'
                            result['hasDisplayDocTitle'] = False
                            result['Accessible'] = False
                            result['_log'] += 'title, '
                        else:
                            result['TitleTest'] = 'Pass'
                            result['hasDisplayDocTitle'] = True
                    else:
                        result['TitleTest'] = 'Fail' # Matterhorn 07-001
                        result['hasDisplayDocTitle'] = False
                        result['Accessible'] = False
                        result['_log'] += 'title, '
                else:
                    result['TitleTest'] = 'Fail'
                    result['hasDisplayDocTitle'] = False
                    result['Accessible'] = False
                    result['_log'] += 'title, '
            else:
                result['TitleTest'] = 'Fail'
                result['hasTitle'] = False
                result['Accessible'] = False
                result['_log'] += 'title, ' 

        # check if Tagged
        # TODO: extend checks here by verifying that all objects in the document are tagged (cf Matterhorn Checkpoint 01)
        structTreeRoot = pdf.Root.get('/StructTreeRoot')
        if (structTreeRoot is not None):
            markInfo = pdf.Root.get('/MarkInfo')
            if (markInfo is not None):
                marked = markInfo.get('/Marked')
                if (marked is not None):
                    if (marked == False):
                        result['TaggedTest'] = 'Fail'
                        result['Accessible'] = False
                        result['_log'] += 'tagged, '
                    else:
                        result['TaggedTest'] = 'Pass'
                else:
                    result['TaggedTest'] = 'Fail'
                    result['Accessible'] = False
                    result['_log'] += 'tagged, '
            else:
                result['TaggedTest'] = 'Fail'
                result['Accessible'] = False
                result['_log'] += 'tagged, '
        else:
            result['TaggedTest'] = 'Fail'
            result['Accessible'] = False
            result['_log'] += 'tagged, '

        # check if not protected
        result['ProtectedTest'] = 'Pass'
        if (pdf.is_encrypted): # Matterhorn 26-001
            if (pdf.encryption.P is None):
                result['Accessible'] = False 
                result['ProtectedTest'] = 'Fail'  

            if (pdf.allow is None):
                result['_log'] += 'permissions not found, should not happen'
            else:
                # according to the Matterhorn test 26-002 we should only test the 10th bit of P
                # but according to our tests, in Acrobat, the 5th bit and the R field are also used to give permissions to screen readers.
                # The algorithm behind pdf.allow.accessibility is here https://github.com/qpdf/qpdf/blob/8971443e4680fc1c0babe56da58cc9070a9dae2e/libqpdf/QPDF_encryption.cc#L1486
                # This algorithm works in most cases, except when the 10th bit is not set and the 5th bit is set. In this case Acrobat is considering that the 5th bit overrides the 10th bit and gives access.
                # I was able to test this only with a file where R=3. To be tested with R<3, but this case seems to be rare.
                bits = BitArray(intbe=pdf.encryption.P, length=16)
                bit10 = bits[16-10]
                bit5 = bits[16-5]
                #print(bits[16-3],bits[16-4],bits[16-5],bits[16-6],bits[16-9],bits[16-10],bits[16-11],bits[16-12])
                #print(pdf.allow)
                if ((not bit10) and bit5):
                    result['ProtectedTest'] = 'Pass'
                    result['_log'] += 'P[10]='+str(bit10)+ ' P[5]='+str(bit5)+' R='+str(pdf.encryption.R)+', '                      
                else:
                    result['ProtectedTest'] = 'Pass' if pdf.allow.accessibility else 'Fail'

                if (result['ProtectedTest'] == 'Fail'):
                    result['Accessible'] = False

        # check if has default language? is the default language valid?
        # "x-default" and "x-unknown" are not considered valid languages, as they are managed by screen readers as if no language was specified
        lang = pdf.Root.get('/Lang')
        if (lang is not None and len(str(lang)) != 0):
            result['hasLang'] = True
            try:
                if (not Language.get(str(lang)).is_valid()):
                    result['InvalidLang'] = True
                    result['LanguageTest'] = 'Fail'
                    result['_log'] += 'Default language is not valid: '+str(lang)+ ', '
                    result['Accessible'] = False
                else:
                    result['LanguageTest'] = 'Pass'
            except tag_parser.LanguageTagError:
                result['InvalidLang'] = True
                result['LanguageTest'] = 'Fail'
                result['_log'] += 'Default language is not valid: '+str(lang)+ ', '
                result['Accessible'] = False            
        else:
            result['LanguageTest'] = 'Fail'
            result['hasLang'] = False
            result['Accessible'] = False
            result['_log'] += 'lang, '

        acro = pdf.Root.get('/AcroForm')
        if (acro is not None):
            try:
                # warn users about Dynamic XFA
                # Dynamic XFA is not compliant with PDF/UA but seems that WCAG has nothing against it
                # cf https://technica11y.org/pdf-accessibility
                xfa = acro.get('/XFA') # Matterhorn 25-001
                configPos = -1
                found = False
                if (xfa is not None):
                    try:
                        for n in range(0, len(xfa)-1):
                            if (xfa[n] == 'config'):
                                configPos = n+1
                                found = True
                                break
                        if (found and xfa[configPos] is not None):
                            xmlStr = xfa[configPos].read_bytes().decode()
                            document = ET.fromstring(xmlStr)
                            for d in document.iter():
                                if (re.match(r'.*dynamicRender', d.tag)): # because of namespaces...
                                    if (d.text == 'required'):
                                        result['xfa'] = True
                                        result['_log'] += 'xfa, '
                    except TypeError:
                        result['_log'] += 'malformed xfa, '
            except ValueError:
                result['_log'] += 'malformed xfa, '

            try:    
                fields = acro.get('/Fields')
                if (fields is not None and len(fields) != 0):
                    result['Form'] = True
                    result['Exempt'] = False
            except ValueError:
                result['_log'] += 'malformed Form fields, '

        outline = pdf.open_outline()
        result['hasBookmarks'] = True
        result['BookmarksTest'] = 'Pass'
        if (len(outline.root) == 0):
            result['hasBookmarks'] = False
            if (len(pdf.pages) > 20):
                result['BookmarksTest'] = 'Fail'
                result['Accessible'] = False
                result['_log'] += 'no bookmarks and more than 20 pages, ' 
                # rule from Acrobat Pro accessibility checker 
                # https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html#Bookmarks

        # try to detect if this PDF contains no text (ex: scanned document)
        # - if the document is not tagged and has no text, it will be inaccessible
        # - if the document is tagged and has no text, it can be accessible

        res = initAnalysis()
        for p in pdf.pages:
            res = mergeAnalyses(res, analyseContent(p))

        result['fonts'] = len(res['fontNames'])
        if (result['fonts'] != 0):
            result['_log'] += "fonts:" + ", ".join(res['fontNames'])
        result['numTxtObjects'] = res['numTxt']

        result['EmptyTextTest'] = 'Fail' if (len(res['fontNames']) == 0 or res['numTxt'] == 0) else 'Pass'

    except _qpdf.PdfError as err:
        result['BrokenFile'] = True
        result['Accessible'] = None
        result['_log'] += 'PdfError: {0}'.format(err)
    except _qpdf.PasswordError as err:
        result['BrokenFile'] = True
        result['Accessible'] = None
        result['_log'] += 'Password protected file: {0}'.format(err)
    except ValueError as err:
        result['BrokenFile'] = True
        result['Accessible'] = None
        result['_log'] += 'ValueError: {0}'.format(err)

    if (result['TaggedTest'] == 'Fail' and result['EmptyTextTest'] == 'Fail'):
        result['TotallyInaccessible'] = True

    if (result['ProtectedTest'] == 'Fail'): 
        result['TotallyInaccessible'] = True

    return result


@app.command()
def toCSV(site: str, inputfile: str, outputfile: str = './out/pdfCheck.csv', debug: bool = False):    
    # analyse file
    results = []
    result = checkFile(inputfile, site, debug)
    outFields = outputFields

    if (not debug):
        del result['_log']
        del result['fonts']
        del result['numTxtObjects']
        outFields = outputFields[0:len(outputFields)-3]
    results.append(result)

    # export data as CSV
    csvExists = os.path.exists(outputfile)
    with open(outputfile, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=outFields)
        if (not csvExists):
            writer.writeheader()
        writer.writerows(results)

@app.command()
def toJSON(inputfile: str, debug: bool = False, pretty: bool = False):
    # analyse file
    result = checkFile(inputfile)
    if (not debug):
        del result['_log']
        del result['fonts']
        del result['numTxtObjects']
    if (pretty):
        print(json.dumps(result, indent=4))
    else:
        print(json.dumps(result))
        
if __name__ == "__main__":
    app()