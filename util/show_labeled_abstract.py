import os
import json
import html
import argparse

DEFAULT_TOKEN = 'O'

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_name', type=str, required=True)
    args = parser.parse_args()
    return args

def main():
    args = get_args()
    out_html = '<html> \
                    <head> \
                        <style> \
                             .POLYMER { font-weight: bold; color: green } \n \
                             .POLYMER_FAMILY { font-weight: bold; color: tan } \n \
                             .ORGANIC { font-weight: bold; color:purple } \n \
                             .MONOMER { font-weight: bold; color:red} \n \
                             .INORGANIC { font-weight: bold; color: darkgray } \n \
                             .MATERIAL_AMOUNT { font-weight: bold; color:orange } \n \
                             .PROP_NAME { font-weight: bold; color: cornflowerblue } \n \
                             .PROP_VALUE { font-weight: bold; color:blue } \n \
                             td { \n \
                                    padding-top: 12px; \n \
                                    padding-bottom: 6px; \n \
                             } \n \
                             th.sticky-header { \n \
                                  position: sticky; \n \
                                  top: 0; \n \
                                  z-index: 10; \n \
                                  background-color: white; \n \
                             } \n \
                        </style> \
                    </head> \
                    <body> \
                        <table> \
                            <tr> \
                                <th class="sticky-header" >No.</th> \
                                <th class="sticky-header" >Abtract( \
                                    <span class="POLYMER")> POLYMER &nbsp &nbsp &nbsp </span> \
                                    <span class="POLYMER_FAMILY")> POLYMER_FAMILY &nbsp &nbsp &nbsp </span> \
                                    <span class="ORGANIC")> ORGANIC &nbsp &nbsp &nbsp </span> \
                                    <span class="MONOMER")> MONOMER &nbsp &nbsp &nbsp </span> \
                                    <span class="INORGANIC")> INORGANIC &nbsp &nbsp &nbsp </span> \
                                    <span class="MATERIAL_AMOUNT")> MATERIAL_AMOUNT &nbsp &nbsp &nbsp </span> \
                                    <span class="PROP_NAME")> PROP_NAME &nbsp &nbsp &nbsp </span> \
                                    <span class="PROP_VALUE")> PROP_VALUE </span> ) \
                                </th> \
                            </tr> \
               \n'
    with open(args.file_name) as f:
        row = 0
        for line in f:
            out_span_lst = []
            row += 1
            item = json.loads(line)
            raw_words = item['words']
            words = [html.escape(a) for a in raw_words]
            labels = item['ner']
            assert(len(words) == len(labels))
            N = len(labels)
            offset = 0
            while offset < N:
                tag = labels[offset]
                if tag != DEFAULT_TOKEN:
                    pos = offset + 1
                    while pos < N:
                        if labels[pos] == tag:
                            pos += 1
                        else:
                            break
                    entity = ' '.join(words[offset:pos])
                    entity_span = "<span class='%s'> %s </span>" % (tag, entity) 
                    out_span_lst.append(entity_span)
                    offset = pos
                else:
                    out_span_lst.append(words[offset])
                    offset += 1
            abstract_span = ' '.join(out_span_lst)
            
            out_html += '<tr><td>%d</td><td>%s</td>\n' % (row, abstract_span) 

    out_html += '</table>\n</body>\n</html>'
    base_name = os.path.basename(args.file_name) 
    out_file = './%s.html' % base_name
    with open(out_file, 'w') as f_o:
        f_o.write(out_html)
    

if __name__ == '__main__':
    main()

