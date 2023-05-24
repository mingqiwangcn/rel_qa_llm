import os
import time
import json
import argparse
import gpt
import pandas as pd

STOP_WORDS = ['the', 'of', 'a', ","]

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
        with open('./output/table_draft.json', 'w') as f_o:
            f_o.write(json.dumps(table_draft))
        '''
        with open('./output/table_draft.json') as f:
            table_draft = json.load(f)
        show_table(table_draft)

        #Step 2, Get 1-hop Entity by Property Name
        
        '''
        prop_entity_map = get_1_hop_entity_from_prop(abstract, table_draft)
        with open('./output/1_hop_entity_from_prop.json', 'w') as f_o:
            f_o.write(json.dumps(prop_entity_map))
        '''

        with open('./output/1_hop_entity_from_prop.json') as f:
            prop_entity_map = json.load(f)
        show_dict(prop_entity_map)

        #Sep 3, Check row by Property-Entity map
        
        check_1_hop_entity_from_prop(abstract, table_draft, prop_entity_map)
        show_table(table_draft)
        
        hop_1_table = get_1_hop_val_from_prop(abstract, table_draft)
        show_table(hop_1_table)

        out_table = join_table(table_draft, hop_1_table)
        show_table(out_table)
        

def join_table(table_draft, hop_1_table):
    hop_1_dict = {}
    for hop_1_row in hop_1_table:
        key = f"{hop_1_row['entity'].strip()}-{hop_1_row['prop_name'].strip()}"
        key_normed = key.lower()
        hop_1_dict[key_normed] = hop_1_row
    
    output_table = []
    filed_names = ['prop_value', 'min', 'max', 'unit', 'category']
    for table_row in table_draft:
        refer_hop_1_entity_lst = table_row['refer_hop_1_entity']
        if len(refer_hop_1_entity_lst) == 0:
            continue
        for refer_ent in refer_hop_1_entity_lst:
            if refer_ent is None:
                continue
            key = f"{refer_ent.strip()}-{table_row['prop'].strip()}"
            key_normed = key.lower()
            matched_hop_1_row = hop_1_dict[key_normed]
            out_row = {
                'entity':table_row['entity'],
                'prop_name':table_row['prop'],
                'hop_1_entity':refer_ent,
            }
            for field in filed_names:
                out_row[field] = matched_hop_1_row[field]
            output_table.append(out_row)
    return output_table

def get_1_hop_val_from_prop(abstract, table_draft):
    prop_dict = {}
    for idx, row_item in enumerate(table_draft):
        prop_name = row_item['prop']
        if prop_name not in prop_dict:
            prop_key = prop_name.lower()
            entity_text = row_item['1_hop_entity_from_prop']
            question = f'what are the values for {prop_name} of the entity {entity_text} ?'
            prop_dict[prop_key] = question
    question_lst = []
    prop_lst = []
    for prop in prop_dict:
        prop_lst.append(prop)
        question_lst.append(prop_dict[prop])

    batch_question_text = get_numbered_text(question_lst)
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text
    }
    prompt = read_prompt('get_1_hop_val_from_prop', field_dict)
    response = gpt.chat_complete(prompt)
    
    number_passages = response.split('\n')
    field_dict_number = {
        'passage':'\n'.join(number_passages)
    }
    prompt_number = read_prompt('extract_number', field_dict_number)
    response_number = gpt.chat_complete(prompt_number)
    output_table = []
    item_lst = response_number.split('\n')
    for idx in range(1, len(item_lst)):
        row_item = item_lst[idx].split(' | ')
        prop_idx = int(row_item[0].strip()) -1
        out_row = {
            'entity':row_item[1].strip(),
            'prop_name':row_item[2].strip(),
            'prop_value':row_item[3].strip(),
            'min':row_item[4].strip(),
            'max':row_item[5].strip(),
            'unit':row_item[6].strip(),
            'category':row_item[7].strip()
        }
        output_table.append(out_row)
    return output_table

def get_entity_set(table_draft):
    entity_set = set()
    for table_row in table_draft:
        row_entity = table_row['entity'].strip().lower()
        entity_set.add(row_entity)
    return entity_set

def check_1_hop_entity_from_prop(abstract, table_draft, prop_entity_map):
    entity_set = get_entity_set(table_draft)
    question_lst = []
    q_id = 0
    for idx, table_row in enumerate(table_draft):
        prop = table_row['prop']
        prop_entity_lst = prop_entity_map[prop.lower()]
        assert len(prop_entity_lst) > 0
        table_row['1_hop_entity_from_prop'] = prop_entity_lst
        table_row['entity_matched'] = []
        table_row['refer_hop_1_entity'] = []
        row_entity = table_row['entity']
        
        for offset, prop_entity in enumerate(prop_entity_lst):
            prop_entity_normed = prop_entity.strip().lower()
            if exact_match(row_entity, prop_entity):
                match_type = 'EM'
                refer_entity = prop_entity
                table_row['entity_matched'].append(match_type)
                table_row['refer_hop_1_entity'].append(refer_entity)
            elif prop_entity_normed in entity_set:
                match_type = None
                refer_entity = None
                table_row['entity_matched'].append(match_type)
                table_row['refer_hop_1_entity'].append(refer_entity)
            else:
                q_id += 1
                q_info = get_corefer_question(idx, str(q_id), row_entity, prop_entity, prop)
                question_lst.append(q_info)

    if len(question_lst) > 0:
        resolve_entity_refer(table_draft, abstract, question_lst)    
            
def exact_match(text_1, text_2):
    return text_1.strip().lower() == text_2.strip().lower()

def get_corefer_question(idx, q_id, row_entity, prop_entity, prop):
    question_part_1 = f'{q_id}. Which one of the following claims is true ?'
    claim_a = f'    A. {row_entity} is another name of {prop_entity} .'
    claim_b = f'    B. {row_entity} is a {prop_entity}  .'
    claim_c = f'    C. {row_entity} is an ingredient of {prop_entity}.'
    claim_d = f'    D. All the 3 choices above are false.'
    question = '\n'.join([question_part_1, claim_a, claim_b, claim_c, claim_d])
    question_info = {
        'q_id':q_id,
        'row_idx':idx,
        'row_entity':row_entity,
        'prop_entity':prop_entity,
        'prop':prop,
        'text':question
    }
    return question_info

def resolve_entity_refer(table_draft, passage, question_lst):
    batch_size = 1
    max_row_idx = len(table_draft) - 1
    for idx in range(0, len(question_lst), batch_size):
        batch_questions = question_lst[idx:(idx+batch_size)]
        
        msg_lst = []
        for q_info in batch_questions:
            msg = f"{q_info['row_idx']}/{max_row_idx} matching {q_info['row_entity']} and {q_info['prop_entity']} on {q_info['prop']}"
            msg_lst.append(msg)
        batch_msg = '\n'.join(msg_lst)
        print(batch_msg)

        batch_question_text = '\n\n'.join([a['text'] for a in batch_questions])
        field_dict = {
            'passage':passage,
            'questions':batch_question_text
        }
        prompt = read_prompt('check_consistency', field_dict)
        print_msg(prompt)
        response = gpt.chat_complete(prompt, temperature=0)
        print_msg(response)
        input('\ncontinue ')
        choice_dict = get_answer_choice(response)
        
        for q_info in batch_questions:
            q_id = q_info['q_id']
            table_row = table_draft[q_info['row_idx']]
            choice = choice_dict[q_id]['choice']
            match_type = 'corefer' if choice in ['A', 'B', 'C'] else None
            refer_entity = q_info['prop_entity'] if match_type is not None else None
            table_row['entity_matched'].append(match_type)
            table_row['refer_hop_1_entity'].append(refer_entity)

        
def get_answer_choice(response):
    answer_dict = {}
    tag = 'So, the answer choice for question'
    res_lines = response.split('\n')
    for line in res_lines:
        idx = line.find(tag)
        if idx == -1:
            continue
        pos_1 = idx + len(tag)
        pos_2 = line.index(' is ', pos_1)
        q_id = line[pos_1:pos_2].strip()
        pos_3 = line.index('.', pos_2)
        choice = line[(pos_3-1):pos_3].strip()
        assert choice in ['A', 'B', 'C', 'D']
        choice_info = {
            'q_id':q_id,
            'choice':choice
        }
        answer_dict[q_id] = choice_info
    return answer_dict

def complete_answer(passage, question, part_answer):
    field_dict = {
        'passage':passage,
        'questions':question,
        'answers':part_answer
    }
    prompt = read_prompt('answer_complete', field_dict)
    print_msg('complete answer')
    print_msg(prompt)
    response = gpt.chat_complete(prompt, temperature=0)
    print_msg(response)
    choice_dict = get_answer_choice(response, False)
    return choice_dict

def show_dict(dict_data):
    print('_'*100)
    
    for key in dict_data:
        print(key, ' | ', '  #@  '.join(dict_data[key]))

def get_1_hop_entity_from_prop(abstract, row_data):
    prop_dict = {}
    for idx, row_item in enumerate(row_data):
        entity = row_item['entity']
        prop_name = row_item['prop'].strip()
        if prop_name not in prop_dict:
            prop_key = prop_name.lower()
            question = f'The {prop_name} of what is given explicitly?'
            prop_dict[prop_key] = question
    question_lst = []
    prop_lst = []
    for prop in prop_dict:
        prop_lst.append(prop)
        question_lst.append(prop_dict[prop])

    question_lst = [str(offset+1) + '. ' + a for offset, a in enumerate(question_lst)]
    batch_question_text = '\n'.join(question_lst)
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text
    }
    entity_prompt = read_prompt('get_1_hop_entity_from_prop', field_dict) 
    response = gpt.chat_complete(entity_prompt)
    answer_lst = response.split('\n')
    assert (len(prop_lst) == len(answer_lst))
    sep = ' | '
    answer_info_lst = []
    for idx, answe_text in enumerate(answer_lst):
        parts = answe_text.split(sep)
        prop_entity_text = parts[0]
        evidence_text = parts[1]
        answer_info = {
            'prop':prop_lst[idx],
            'prop_entity':prop_entity_text,
            'evidence':evidence_text
        }
        answer_info_lst.append(answer_info)
    prop_entity_passage = '\n'.join([a['prop_entity'] for a in answer_info_lst])
    prop_1_hop_entities = extract_1_hop_entity(prop_entity_passage)
    assert len(prop_1_hop_entities) == len(answer_info_lst)
    
    prop_hop_1_ent_map = {}
    for idx, answer_info in enumerate(answer_info_lst):
        prop = answer_info['prop']
        prop_hop_1_ent_map[prop] = prop_1_hop_entities[idx]
    return prop_hop_1_ent_map

def get_numbered_text(text_lst):
    return '\n'.join([str(idx+1) + '. ' + text for idx, text in enumerate(text_lst)])

def extract_1_hop_entity(prop_entity_passage):
    field_dict = {
        'passage':prop_entity_passage,
    }
    prompt = read_prompt('extract_1_hop_entity', field_dict)
    print_msg(prompt)
    response = gpt.chat_complete(prompt)
    print_msg(response)
    res_line_lst = response.split('\n')
    SEP = ' | '
    prop_1_hop_entities = []
    for res_line in res_line_lst:
        parts = res_line.split(SEP)
        if parts[0].strip().lower() == 'no.': # header row
            continue
        entity_lst = parts[2].split(' @ ')
        entity_lst = [a.strip() for a in entity_lst]
        prop_1_hop_entities.append(entity_lst)
    return prop_1_hop_entities

def print_msg(msg):
    print('-'*60 + 'SEP' + '-'*60)
    print(msg)
    print('-'*60 + 'SEP' + '-'*60)

def merge_entity_prop_pairs(row_data):
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
        prompt_name = ('start_1' if try_no == 1 else 'start_2')
        
        start_prompt = read_prompt(prompt_name, field_dict) 
        response = gpt.chat_complete(start_prompt, temperature=0.7)
        table_dict , prop_set = get_entity_prop_pairs(response)
        ignore_prop_set.update(prop_set)
        output_row_data.extend(table_dict['rows'])
    
    out_table_draft = merge_entity_prop_pairs(output_row_data)
    out_table_draft_sorted = sorted(out_table_draft, key=lambda x: x[1])

    table_data = []
    for row_item in out_table_draft_sorted:
        table_row = {
            'entity':row_item[0],
            'prop':row_item[1]
        }
        table_data.append(table_row)
    return table_data

def show_table(table_data):
    df = pd.DataFrame(table_data)
    print('-'*100)
    print(df)

def get_entity_prop_pairs(response):
    lines = response.split('\n')
    table_dict = {'rows':[]}
    prop_set = set()
    for row_text in lines:
        item_eles = row_text.split(gpt.SEP_TOKEN)
        if len(item_eles) < 3:
            continue

        ent_prop_pair = [item_eles[0].strip(), item_eles[1].strip()]
        table_dict['rows'].append(ent_prop_pair)
        prop = ent_prop_pair[1]
        prop_normed = prop.lower() 
        prop_set.add(prop_normed)
    return table_dict, prop_set

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abstract_file', type=str, default='./data/abstract_examples.txt')
    parser.add_argument('--out_dir', type=str, default='output')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()


