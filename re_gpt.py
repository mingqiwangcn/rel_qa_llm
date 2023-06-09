import os
import time
import datetime
import json
import argparse
import gpt
import pandas as pd

def read_abstract(args):
    with open(args.abstract_file) as f:
        for line in f:
            abstract = line.strip()
            if abstract.startswith('### '):
                abstract = None
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

def print_lst(data):
    print('-'*100)
    
    msg = '\n'.join(data)
    print(msg)
    
    print('-'*100)

def write_log(log_dir, data, file_name):
    data_file = os.path.join(log_dir, file_name)
    with open(data_file, 'w') as f_o:
        json.dump(data, f_o)

def read_log(log_dir, file_name):
    data_file = os.path.join(log_dir, file_name)
    with open(data_file) as f:
        data = json.load(f)
        return data

def set_gpt_logger(log_dir):
    cur_time = datetime.datetime.now()
    time_str = cur_time.strftime("%Y_%m_%d_%H_%M_%S")
    log_file = f'{log_dir}/gtp_log_{time_str}.txt'
    f_log = open(log_file, 'w')
    gpt.set_logger(f_log)
    return f_log  

def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key is None:
        print('OPENAI_API_KEY is not set')
        return
    gpt.set_key(api_key)
    args = get_args()

    for idx, abstract in enumerate(read_abstract(args)):
        if abstract is None:
            continue
        data_dir = f'{args.out_dir}/passage_{idx+1}'
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir)

        f_gpt_log = set_gpt_logger(data_dir)
        t1 = time.time()
        print(f'Passage {idx+1}. Step 1, Get all polymers')
        polymer_lst = get_all_polymers(abstract)
        write_log(data_dir, polymer_lst, 'polymer.json')
        polymer_lst = read_log(data_dir, 'polymer.json')
        show_table(polymer_lst)
        if len(polymer_lst) == 0:
            print(f'There is no polymers for passage {idx+1}')
            return
        
        print(f'Passage {idx+1}. Step 2, Get property names')
        prop_lst = get_all_numeric_props(abstract)
        write_log(data_dir, prop_lst, 'prop.json')
        prop_lst = read_log(data_dir, 'prop.json')
        print_lst(prop_lst)
        
        print(f'Passage {idx+1}. Step 3, Get 1-hop entity by property name')
        prop_entity_map = get_1_hop_entity(abstract, prop_lst)
        write_log(data_dir, prop_entity_map, '1_hop_entity.json')
        prop_entity_map = read_log(data_dir, '1_hop_entity.json')
        show_dict(prop_entity_map)
        
        print(f'Passage {idx+1}. Step 4, Connect poymer to 1-hop entity of property')
        polymer_table = connect_polymer_to_1_hop_entity(abstract, polymer_lst, prop_entity_map)
        write_log(data_dir, polymer_table, 'polymer_table.json')
        polymer_table = read_log(data_dir, 'polymer_table.json')
        show_table(polymer_table)
        
        print(f'Passage {idx+1}. Setp 5, Get 1-hop property and numbers')
        hop_1_table = get_1_hop_val_from_prop(abstract, polymer_table)
        
        write_log(data_dir, hop_1_table, '1_hop_table.json')
        hop_1_table = read_log(data_dir, '1_hop_table.json')
        show_table(hop_1_table)

        print(f'Passage {idx+1}. Setp 6, Join table')
        out_table = join_table(polymer_table, hop_1_table)
        write_log(data_dir, out_table, 'output_table.json')
        out_table = read_log(data_dir, 'output_table.json')
        show_table(out_table)
        t2 = time.time()
        print('time spent (seconds) : %d' %(t2-t1))

        f_gpt_log.close()
        

def get_all_polymers(passage):
    field_dict_number = {
        'passage':passage
    }
    prompt = read_prompt('get_polymer', field_dict_number)
    #print(prompt)
    response = gpt.chat_complete(prompt)
    res_lines = response.split('\n')
    polymer_data = []
    for line in res_lines:
        items = line.split(' | ')
        if len(items) < 2:
            continue
        if line.startswith('full name | short name'):
            continue
        name_text = normalize_text(items[1])
        full_name = normalize_text(items[0])
        assert name_text != 'n/a'
        name_lst = name_text.split('#@')
        for name in name_lst:
            polymer_info = {
                'entity':normalize_text(name),
                'full_name':full_name
            }
            polymer_data.append(polymer_info)
    return polymer_data

def normalize_text(text):
    return text.strip().lower()

def get_all_numeric_props(passage):
    output_table = []
    field_dict_number = {
        'passage':passage
    }
    prompt = read_prompt('get_prop', field_dict_number)
    #print(prompt)
    response = gpt.chat_complete(prompt)
    #print(response)
    res_lines = response.split('\n')
    prop_set = set()
    for line in res_lines:
        items = line.split(' | ')
        prop_val = normalize_text(items[3])
        prop_unit = normalize_text(items[4])
        if prop_val == 'n/a' or prop_unit == 'n/a':
            continue
        prop_name = normalize_text(items[2])
        prop_set.add(prop_name)
    prop_list = list(prop_set)
    return prop_list

def join_table(table_draft, hop_1_table):
    hop_1_dict = {}
    for hop_1_row in hop_1_table:
        key = f"{hop_1_row['hop_1_entity']}-{hop_1_row['prop_name']}"
        hop_1_dict[key] = hop_1_row
    
    output_table = []
    filed_names = ['prop_value', 'min', 'max', 'unit', 'category']
    for table_row in table_draft:
        refer_hop_1_entity_lst = table_row['refer_hop_1_entity']
        if len(refer_hop_1_entity_lst) == 0:
            continue
        for refer_ent in refer_hop_1_entity_lst:
            if refer_ent is None:
                continue
            refer_ent_normed = normalize_text(refer_ent)
            key = f"{refer_ent_normed}-{table_row['prop']}"
            if key not in hop_1_dict:
                continue
            matched_hop_1_row = hop_1_dict[key]
            out_row = {
                'entity':table_row['entity'],
                'prop_name':table_row['prop'],
                'hop_1_entity':refer_ent,
            }
            for field in filed_names:
                out_row[field] = matched_hop_1_row[field]
            output_table.append(out_row)
    return output_table

def get_numeric_detail(passage, question_lst):
    output_table = []
    field_dict_number = {
        'passage':passage
    }
    #To use this propmt, a passage must be generated in the template of few-shot examples in the prompt.
    prompt_number = read_prompt('extract_number', field_dict_number)
    response_number = gpt.chat_complete(prompt_number)
    item_lst = response_number.split('\n')
    for idx in range(1, len(item_lst)):
        row_item = item_lst[idx].split(' | ')
        q_idx = int(row_item[0].strip()) -1
        question_info = question_lst[q_idx]
        #if question_info['prop'] != row_item[2].strip().lower():
        #    continue
        out_row = {
            'hop_1_entity':question_info['refer_entity'],
            'prop_name':question_info['prop'],
            'prop_value':row_item[3].strip(),
            'min':row_item[4].strip(),
            'max':row_item[5].strip(),
            'unit':row_item[6].strip(),
            'category':row_item[7].strip()
        }
        for field_name in ['prop_value', 'min', 'max']:
            if out_row[field_name] == 'n/a':
                out_row[field_name] = ''
        output_table.append(out_row)
    return output_table

def get_1_hop_val_from_prop(abstract, polymer_table):
    prop_refer_entity_dict = {}
    question_lst = []
    for idx, row_item in enumerate(polymer_table):
        prop_name = row_item['prop']
        refer_entity_lst = row_item['refer_hop_1_entity']
        query_entity_lst = [a for a in refer_entity_lst if a is not None]
        for query_entity in query_entity_lst:
            query_entity_normalized = normalize_text(query_entity)
            key = f'{prop_name}-{query_entity_normalized}'
            if key not in prop_refer_entity_dict:
                question = f'what is the value for {prop_name} of the entity {query_entity_normalized} ?'
                question_info = {
                    'prop':prop_name,
                    'refer_entity':query_entity_normalized,
                    'question':question
                }
                question_lst.append(question_info)
                prop_refer_entity_dict[key] = question_info

    if len(question_lst) == 0:
        return []
    question_text_lst = [a['question'] for a in question_lst]
    batch_question_text = get_numbered_text(question_text_lst)
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text
    }
    prompt = read_prompt('get_1_hop_val_from_prop', field_dict)
    response = gpt.chat_complete(prompt)
    
    number_passages = response.split('\n')
    passage_text = '\n'.join(number_passages)

    numeric_detail_table = get_numeric_detail(passage_text, question_lst)
    return numeric_detail_table

def get_polymer_props(polymer_data, prop_entity_map):
    out_table = []
    for polymer_info in polymer_data:
        for prop in prop_entity_map:
            out_row = {
                'entity':polymer_info['entity'],
                'prop':prop
            }
            out_table.append(out_row)
    return out_table

def connect_polymer_to_1_hop_entity (abstract, polymer_lst, prop_entity_map):
    entity_set = set([a['entity'] for a in polymer_lst])
    question_lst = []
    q_id = 0
    polymer_table = get_polymer_props(polymer_lst, prop_entity_map)
    for idx, table_row in enumerate(polymer_table):
        prop = table_row['prop']
        prop_entity_lst = prop_entity_map[prop]
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
        resolve_entity_refer(polymer_table, abstract, question_lst)
    return polymer_table
            
def exact_match(text_1, text_2):
    return text_1.strip().lower() == text_2.strip().lower()

def get_corefer_question(idx, q_id, row_entity, prop_entity, prop):
    question_part_1 = f'{q_id}. Which one of the following claims is true ?'
    claim_a = f'    A. {row_entity} is the same as {prop_entity} .'
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
        #print('\n' + batch_msg)

        batch_question_text = '\n\n'.join([a['text'] for a in batch_questions])
        field_dict = {
            'passage':passage,
            'questions':batch_question_text
        }
        prompt = read_prompt('check_consistency', field_dict)
        response = gpt.chat_complete(prompt, temperature=0)
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
    #print_msg('complete answer')
    #print_msg(prompt)
    response = gpt.chat_complete(prompt, temperature=0)
    #print_msg(response)
    choice_dict = get_answer_choice(response, False)
    return choice_dict

def show_dict(dict_data):
    print('-'*100)
    
    for key in dict_data:
        print(key, ' | ', '  #@  '.join(dict_data[key]))

    print('-'*100)

def get_1_hop_entity(abstract, prop_lst):
    question_lst = []
    for idx, prop_name in enumerate(prop_lst):
        q_id = idx + 1
        question = f'{q_id}. The {prop_name} of what is given explicitly?'
        question_lst.append(question)
    
    batch_question_text = '\n'.join(question_lst)
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text
    }

    entity_prompt = read_prompt('get_1_hop_entity_from_prop', field_dict) 
    #print(entity_prompt)
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
    #print_msg(prompt)
    response = gpt.chat_complete(prompt)
    #print_msg(response)
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
    #print('-'*60 + 'SEP' + '-'*60)
    print(msg)
    #print('-'*60 + 'SEP' + '-'*60)

def merge_entity_prop_pairs(row_data):
    row_dict = {}
    for item in row_data:
        key = ','.join([a.strip().lower() for a in item])
        if key not in row_dict:
            row_dict[key] = item
    out_row_data = row_dict.values()
    return out_row_data

def show_table(table_data):
    pd.set_option('display.max_colwidth', 20)
    pd.set_option('display.max_columns', 100)
    df = pd.DataFrame(table_data)
    print('-'*100)
    print(df)
    print('-'*100)

def get_entity_prop_pairs(response):
    lines = response.split('\n')
    table_dict = {'rows':[]}
    prop_set = set()
    for row_text in lines:
        item_eles = row_text.split(gpt.SEP_TOKEN)
        if len(item_eles) < 5:
            continue
        unit = item_eles[-1].strip().lower()
        if unit == 'n/a':
            continue
        ent_prop_pair = [item_eles[0].strip(), item_eles[2].strip()]
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


