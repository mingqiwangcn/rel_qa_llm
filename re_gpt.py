import os
import time
import json
import argparse
import gpt

def read_abstract(args):
    with open(args.abstract_file) as f:
        for line in f:
            abstract = line.strip()
            yield abstract

def read_prompt(name, field_dict):
    prompt_file = './prompt/%s.pmt' % name
    with open(prompt_file) as f:
        template = f.read()
    prompt = template
    for key in field_dict:
        place_holder = '{{' + key + '}}'
        if place_holder not in prompt:
            raise ValueError(place_holder + ' not found in prompt (' + name + ')')
        prompt = prompt.replace(place_holder, field_dict[key])
    return prompt 

def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key is None:
        print('OPENAI_API_KEY is not set')
        return
    gpt.set_key(api_key)
    args = get_args()
    #table_draft = get_table_draft(args)
    #with open('./output/table_draft.json', 'w') as f_o:
    #    f_o.write(json.dumps(table_draft))
    with open('./output/table_draft.json') as f:
        table_draft = json.load(f)
    
    out_table_draft = merge_row_data(table_draft)
    out_table_draft = sorted(out_table_draft, key=lambda x: x[1])
    show_output(out_table_draft)


def merge_row_data(row_data):
    row_dict = {}
    for item in row_data:
        key = ','.join([a.strip().lower() for a in item])
        if key not in row_dict:
            row_dict[key] = item

    out_row_data = row_dict.values()
    return out_row_data

def get_table_draft(args):  
    output_row_data = [] 
    ignore_prop_set = set()
    for abstract in read_abstract(args):
        for itr in range(2):
            try_no = itr + 1
            if try_no <= 1:
                field_dict = {
                    'passage':abstract
                }
            else:
                ignore_prop_lst = list(ignore_prop_set)
                ignore_prop_lst = ['"' + a + '"' for a in ignore_prop_lst]
                ignore_prop_str = ' , '.join(ignore_prop_lst)
                field_dict = {
                    'ignore_props':ignore_prop_str,
                    'passage':abstract
                }
            start_prompt = read_prompt('start_%d' % try_no, field_dict) 
            t1 = time.time()            
            response = gpt.chat_complete(start_prompt)
            t2 = time.time()
            table_dict , prop_set = process_response(response)
            ignore_prop_set.update(prop_set)

            output_row_data.extend(table_dict['rows'])
    return output_row_data

def show_output(output_row_data):
    for row_info in output_row_data:
        text = ' | '.join(row_info)
        print(text)


def process_response(response):
    lines = response.split('\n')
    table_dict = {'rows':[]}
    prop_set = set()
    for row_text in lines:
        item_eles = row_text.split(gpt.SEP_TOKEN)
        if len(item_eles) < 3:
            continue
        table_dict['rows'].append(item_eles)
        prop = item_eles[1].strip()
        prop_set.add(prop)
    return table_dict, prop_set
        

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abstract_file', type=str, default='./data/abstract_examples.txt')
    parser.add_argument('--out_dir', type=str, default='output')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()


