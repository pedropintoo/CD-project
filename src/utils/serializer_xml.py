# utils/dict_to_xml.py

from xml.etree.ElementTree import Element, tostring, fromstring
from xml.dom.minidom import parseString
import re

def dict_to_xml(data):
        def build_xml_element(parent, dict_data):
            for key, value in dict_data.items():
                # Replace invalid characters in XML tags with underscores
                key = re.sub(r'[^a-zA-Z0-9_]', '_', key)
                elem = Element(key)
                parent.append(elem)
                if isinstance(value, dict):
                    build_xml_element(elem, value)
                elif isinstance(value, list):
                    for sub_value in value:
                        sub_elem = Element(key[:-1] if key.endswith('s') else key)
                        elem.append(sub_elem)
                        if isinstance(sub_value, dict):
                            build_xml_element(sub_elem, sub_value)
                        else:
                            sub_elem.text = str(sub_value)
                else:
                    elem.text = str(value)

        root = Element('response')
        build_xml_element(root, data)
        raw_xml = tostring(root, encoding='unicode', method='xml')
        parsed_xml = parseString(raw_xml)
        return parsed_xml.toprettyxml(indent="    ")
    
    
def parse_xml(data):
    try:
        root = fromstring(data)
        sudoku = []
        for row in root.findall('.//row'):
            sudoku_row = [int(cell.text) for cell in row.findall('.//cell')]
            sudoku.append(sudoku_row)
        return {'sudoku': sudoku}
    except Exception as e:
        raise ValueError(f"Invalid XML format: {str(e)}")
