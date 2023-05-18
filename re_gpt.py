import os
import time
import json
import argparse
import gpt

STOP_WORDS = ['the', 'of', 'a']

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
    for abstract in read_abstract(args):
        # Step 1, Get a start table draft with possibly complete property names
        '''
        table_draft = get_table_draft(abstract)
        show_output(table_draft)
        with open('./output/table_draft.json', 'w') as f_o:
            f_o.write(json.dumps(table_draft))
        
        '''
        with open('./output/table_draft.json') as f:
            table_draft = json.load(f)
        
        #Step 2, Get Entity by Property Name
        
        '''
        prop_entity_map = property_to_entity(abstract, table_draft)
        print_msg(prop_entity_map)
        with open('./output/prop_entity.json', 'w') as f_o:
            f_o.write(json.dumps(prop_entity_map))
        '''

        #Sep 3, Check row by Property-Entity map
        with open('./output/prop_entity.json') as f:
            prop_entity_map = json.load(f)
        
        show_table(table_draft)
        show_dict(prop_entity_map)

def show_dict(dict_data):
    print('_'*100)
    for key in dict_data:
        print(key, ' | ', '   '.join(dict_data[key]))

def property_to_entity(abstract, row_data):
    prop_dict = {}
    for idx, row_item in enumerate(row_data):
        entity = row_item[0]
        prop_name = row_item[1].strip()
        prop_value = row_item[2]
        if prop_name not in prop_dict:
            prop_key = prop_name.lower()
            question = f'The {prop_name} of what entity is given explicitly?'
            prop_dict[prop_key] = question
    question_lst = []
    prop_lst = []
    for prop in prop_dict:
        prop_lst.append(prop)
        question_lst.append(prop_dict[prop])

    batch_question_text = '\n'.join(question_lst)
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text
    }
    entity_prompt = read_prompt('entity', field_dict) 
    response = gpt.chat_complete(entity_prompt)
    answer_lst = response.split('\n')
    assert (len(prop_lst) == len(answer_lst))
    prop_entity_map = {}
    sep = '#@'
    for idx, prop_name in enumerate(prop_lst):
        answer_text = answer_lst[idx]
        assert(sep in answer_text)
        prop_entity_text = answer_text.split(sep)[0]
        prop_entity_lst = get_entity_from_answer(prop_name, prop_entity_text.lower())
        prop_entity_map[prop_name] = prop_entity_lst
    return prop_entity_map

def get_entity_from_answer(prop_name, prop_entity_text):
    prop_entity_text = prop_entity_text.replace(prop_name, '')
    for stop_word in STOP_WORDS:
        prop_entity_text = prop_entity_text.replace(stop_word, '')
    prop_entity_text = prop_entity_text.strip()
    entity_lst = prop_entity_text.split('|&')
    return entity_lst

def print_msg(msg):
    print('-'*100)
    print(msg)

def merge_row_data(row_data):
    row_dict = {}
    for item in row_data:
        key = ','.join([a.strip().lower() for a in item])
        if key not in row_dict:
            row_dict[key] = item

    out_row_data = row_dict.values()
    return out_row_data

def get_table_draft(abstract):  
    output_row_data = [] 
    ignore_prop_set = set()
    max_num_try = 2
    for itr in range(max_num_try):
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
        response = gpt.chat_complete(start_prompt)
        table_dict , prop_set = process_response(response)
        ignore_prop_set.update(prop_set)
        output_row_data.extend(table_dict['rows'])
    
    out_table_draft = merge_row_data(output_row_data)
    out_table_draft_sorted = sorted(out_table_draft, key=lambda x: x[1])
    return out_table_draft_sorted

def show_table(output_row_data):
    print('-'*100)
    for row_info in output_row_data:
        text = ' | '.join(row_info)
        print(text)


def process_response(response):
    lines = response.split('\n')
    table_dict = {'rows':[]}
    prop_set = set()
    for row_text in lines:
        item_eles = row_text.split(gpt.SEP_TOKEN)
        item_eles = [a.strip() for a in item_eles]
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


