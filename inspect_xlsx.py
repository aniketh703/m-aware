import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

path = Path('c:/Users/Ani/OneDrive/Desktop/knowledge graph/NewSample.xlsx')
ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

with zipfile.ZipFile(path) as z:
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    sheets = wb.find('a:sheets', ns)
    print('SHEETS:', [s.attrib['name'] for s in sheets])

    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid_to_target = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
    first = list(sheets)[0]
    target = rid_to_target[first.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
    sheet_path = 'xl/' + target if not target.startswith('xl/') else target
    sheet = ET.fromstring(z.read(sheet_path))

    rows = sheet.find('a:sheetData', ns).findall('a:row', ns)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        sst = ET.fromstring(z.read('xl/sharedStrings.xml'))
        shared = [''.join(t.text or '' for t in si.iterfind('.//a:t', ns)) for si in sst.findall('a:si', ns)]

    headers = []
    for c in rows[0].findall('a:c', ns):
        v = c.find('a:v', ns)
        val = '' if v is None else v.text or ''
        headers.append(shared[int(val)] if c.attrib.get('t') == 's' else val)

    print('HEADERS:', headers)
    print('ROWS:', len(rows))
