import os
import time
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
    for abstract in read_abstract(args):
        start_prompt = read_prompt(
            'start_2',
            {
                'passage':abstract
            }
        ) 
        for itr in range(3):
            print('\ntry %d\n' % (itr + 1))
            t1 = time.time()            
            response = gpt.chat_complete(start_prompt)
            t2 = time.time()
            print(response)
            print('t2-t1=', t2 - t1)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abstract_file', type=str, default='./data/abstract_examples.txt')
    parser.add_argument('--out_dir', type=str, default='output')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()


