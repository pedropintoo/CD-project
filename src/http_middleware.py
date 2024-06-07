# src/middleware.py

import json
from xml.etree.ElementTree import fromstring
from src.utils.serializer_xml import dict_to_xml, parse_xml

class Middleware:
    @staticmethod
    def parse_request(headers, data):
        content_type = headers.get('Content-Type', 'application/json')
        if 'application/xml' in content_type:
            # Try to parse the XML data
            return parse_xml(data)['sudoku']
        else:
            # Try to parse the JSON data
            return json.loads(data)['sudoku']
        
    @staticmethod
    def format_response(headers, data):
        content_type = headers.get('Content-Type', 'application/json')    
        if 'application/xml' in content_type:
            return 'application/xml', dict_to_xml(data)
        else:
            return 'application/json', json.dumps(data, indent=4) + "\n"