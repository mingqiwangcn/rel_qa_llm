import os
import gpt
import argparse
from re_gpt import read_abstract, read_prompt, set_gpt_logger

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
        f_log = set_gpt_logger(data_dir)
        response = get_table(abstract)
        f_log.close()
        

def get_table(abstract):
    field_dict_number = {
        'passage':abstract
    }
    prompt = read_prompt('baseline', field_dict_number)
    print(prompt)
    response = gpt.chat_complete(prompt)
    print(response)
    return response

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--abstract_file', type=str, default='./data/abstract_examples.txt')
    parser.add_argument('--out_dir', type=str, default='output')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    main()
