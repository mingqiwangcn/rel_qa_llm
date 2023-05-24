import openai

SEP_TOKEN = ' | '

def set_key(key):
    openai.api_key = key

def chat_complete(prompt, temperature=0):
    MODEL = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature, # to get determinstic output so that it is easy to control by prompt.
    )
    out_msg = response['choices'][0]['message']['content']
    return out_msg

def get_group_answer(response):
    line_lst = response.split('\n')
    answer_group_dict = {}
    for line in line_lst:
        line_text = line.strip()
        if line_text.lower() == 'n/a':
            short_answer = 'n/a'
        else:
            pos = line_text.index(',')
            number_parts = line_text[:pos].split('.')
            if line_text[pos-3:pos].lower() == 'yes':
                short_answer = 'yes'
            elif line_text[pos-2:pos].lower() == 'no':
                short_answer = 'no'
            else:
                raise ValueError(f'unexpected line ( {line_text} )')
            #12.1.a. Yes,
            #12.1.b. No,
            q_id = '.'.join(number_parts[:-1])
            group_id = '.'.join(number_parts[:-2])
            if group_id not in answer_group_dict:
                answer_group_dict[group_id] = []
            answer_info = {
                'q_id':q_id,
                'short_answer':short_answer,
                'text':line_text
            }
            answer_group_dict[group_id].append(answer_info)
    return answer_group_dict

def check_consistaency(question_lst):
    
    batch_question_text = '\n'.join([a['text'] for a in question_lst])
    field_dict = {
        'passage':abstract,
        'questions':batch_question_text,
    }
    prompt = read_prompt('check_1_hop_entity_from_prop', field_dict)
    print_msg(prompt)
    response = gpt.chat_complete(prompt)
    print_msg(response)
    
    import pdb; pdb.set_trace()
    group_answer_dict = gpt.get_group_answer(response)

    answer_lst = response.split('\n')
    for offset, answer_text in enumerate(answer_lst):
        row_idx = question_lst[offset]['row_idx']
        table_row = table_draft[row_idx]
        pos = answer_text.index(',')
        number_parts = answer_text[:pos].split('.')
        assert len(number_parts) > 1

        if answer_text[pos-3:pos].lower() == 'yes':
            if table_row['entity_matched'] != '':
                table_row['entity_matched'] += ' , '
            table_row['entity_matched'] += 'Y(rel IN)'
            if len(number_parts) == 2:
                table_row['refer_hop_1_entity'] = table_row['1_hop_entity_from_prop']
            else:
                hop_1_entity_offset = int(number_parts[1]) - 1
                hop_1_entity = table_row['1_hop_entity_from_prop'][hop_1_entity_offset]
                table_row['refer_hop_1_entity'].append(hop_1_entity)

        elif answer_text[pos-2:pos].lower() == 'no':
            if table_row['entity_matched'] != '':
                table_row['entity_matched'] += ' , '
            table_row['entity_matched'] += 'N'

        elif answer_text[pos-3:pos].lower() == 'n/a':
            if table_row['entity_matched'] != '':
                table_row['entity_matched'] += ' , '
            table_row['entity_matched'] += 'N/A'
            for hop_1_ent in table_row['1_hop_entity_from_prop']:
                if table_row['entity'].lower() in hop_1_ent:
                    table_row['refer_hop_1_entity'].append(hop_1_ent)
        else:
            raise ValueError(f'Unexpected answer f{answer_text}')