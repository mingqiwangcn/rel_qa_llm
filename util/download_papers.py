from tqdm import tqdm
from multiprocessing import Pool as ProcessPool
import json
import os
import argparse
import requests
from bs4 import BeautifulSoup

def get_tag_lst(args):
    tag_lst = []
    with open(args.file_name) as f:
        for line in tqdm(f):    
            tag_lst.append(line.strip())
    return tag_lst

def get_paper_url(tag):
    req_url = 'https://doi.org/' + tag
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
    res = requests.get(req_url, headers=headers)
    source_code = res.text
    #soup = BeautifulSoup(source_code, 'html.parser')
    out_info = {
        'tag':tag,
        'url':res.url,
        'html':source_code,
    }
    return out_info

def write_buffer(args, out_buffer, out_file_no):
    base_name = os.path.basename(args.file_name)
    out_file = './outputs/%s_paper_%d.jsonl' % (base_name, out_file_no)
    with open(out_file, 'w') as f_o:
        for item in out_buffer:
            f_o.write(json.dumps(item) + '\n')
    
def main(args):
    if not os.path.isdir('./outputs'):
        os.makedirs('./outputs')
    tag_lst = get_tag_lst(args)
    cpu_count = os.cpu_count()
    work_pool = ProcessPool(cpu_count)
    arg_info_lst = []
    out_file_no = 1
    out_buffer = []
    for out_info in tqdm(work_pool.imap_unordered(get_paper_url, tag_lst), total=len(tag_lst)):
        out_buffer.append(out_info)
        if len(out_buffer) >= 10000:
            write_buffer(args, out_buffer, out_file_no) 
            out_buffer = []
            out_file_no += 1
    if len(out_buffer) > 0: 
        write_buffer(args, out_buffer, out_file_no) 
        out_buffer = []
        out_file_no += 1

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_name', type=str, required=True)
    args = parser.parse_args()
    return args 

if __name__ == '__main__':
    args = get_args()
    main(args)
