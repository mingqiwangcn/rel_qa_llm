from tqdm import tqdm
from multiprocessing import Pool as ProcessPool
import json
import os
import argparse
import glob

def write_buffer(args, out_buffer, out_file):
    with open(out_file, 'w') as f_o:
        for source in out_buffer:
            out_info = out_buffer[source]
            f_o.write(json.dumps(out_info) + '\n')

def get_source(url):
    start_str_1 = 'https://'
    start_str_2 = 'http://'
    if url.startswith(start_str_1):
        start_str = start_str_1
    elif url.startswith(start_str_2):
        start_str = start_str_2
    else:
        raise ValueError(url) 
    pos = url.index('/', len(start_str)) 
    source = url[len(start_str):pos]
    return source

def read_paper_file(paper_file):
    out_data = {}
    with open(paper_file) as f:
        for line in f:
            item = json.loads(line)
            url = item['url']
            if url is not None:
                source = get_source(url)
                if source not in out_data:
                    out_data[source] = {
                        'source':source,
                        'tag':item['tag'],
                        'url':url,
                        'count':1,
                    }
                else:
                    out_data[source]['count'] += 1
    return out_data

def main(args):
    out_file = './paper_source.txt'
    if os.path.isfile(out_file):
        print('%s already exists' % out_file)
        return
    
    file_pattern = os.path.join(args.paper_dir, '**', '*.jsonl')
    file_lst = glob.glob(file_pattern)
    if len(file_lst) == 0:
        print('No paper file found at %s', args.paper_dir)
        return

    cpu_count = os.cpu_count()
    num_workers = min(cpu_count, len(file_lst))
    work_pool = ProcessPool(num_workers)
    out_buffer = {}
    for out_info in tqdm(work_pool.imap_unordered(read_paper_file, file_lst), total=len(file_lst)):
        for source in out_info:
            if source not in out_buffer:
                out_buffer[source] = out_info[source]
            else:
                out_buffer[source]['count'] += out_info[source]['count']

    write_buffer(args, out_buffer, out_file) 

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper_dir', type=str, required=True)
    args = parser.parse_args()
    return args 

if __name__ == '__main__':
    args = get_args()

    main(args)




