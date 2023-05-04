from tqdm import tqdm
from multiprocessing import Pool as ProcessPool
import json
import os
import argparse
import glob

def write_buffer(args, out_buffer, out_file):
    with open(out_file, 'w') as f_o:
        for paper_tag in out_buffer:
            f_o.write(paper_tag + '\n')

def read_paper_file(paper_file):
    out_data = []
    with open(paper_file) as f:
        for line in f:
            item = json.loads(line)
            if item['url'] is None:
                out_data.append(item['tag'])
    return out_data

def main(args):
    out_file = './paper_not_downloaded_%s.txt' % args.out_tag
    if os.path.isfile(out_file):
        print('%s already exists' % out_file)
        return
    
    file_pattern = os.path.join(args.paper_dir, '*.jsonl')
    file_lst = glob.glob(file_pattern)
    if len(file_lst) == 0:
        print('No paper file found at %s', args.paper_dir)
        return

    cpu_count = os.cpu_count()
    num_workers = min(cpu_count, len(file_lst))
    work_pool = ProcessPool(num_workers)
    out_buffer = []
    for out_info in tqdm(work_pool.imap_unordered(read_paper_file, file_lst), total=len(file_lst)):
        out_buffer.extend(out_info)

    write_buffer(args, out_buffer, out_file) 

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper_dir', type=str, required=True)
    parser.add_argument('--out_tag', type=str, required=True)
    args = parser.parse_args()
    return args 

if __name__ == '__main__':
    args = get_args()

    main(args)




