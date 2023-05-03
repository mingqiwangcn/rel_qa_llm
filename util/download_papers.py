from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from multiprocessing import Pool as ProcessPool
import json
import os

def init_browser():
    global browser
    option = webdriver.FirefoxOptions()
    browser = webdriver.Firefox(options=option)

def get_tag_lst():
    tag_lst = []
    with open('./training_DOI.txt') as f:
        for line in tqdm(f):    
            tag_lst.append(line.strip())
    return tag_lst

def get_paper_url(tag):
    browser.get('https://doi.org/' + tag)
    url = browser.current_url
    out_info = {
        'tag':tag,
        'url':url,
    }
    return out_info

def write_buffer(out_buffer, out_file_no):
    out_file = './outputs/html_%d.jsonl' % out_file_no
    with open(out_file, 'w') as f_o:
        for item in out_buffer:
            f_o.write(json.dumps(item) + '\n')
    
def main():
    tag_lst = get_tag_lst()
    cpu_count = os.cpu_count()
    work_pool = ProcessPool(cpu_count, initializer=init_browser)
    arg_info_lst = []
    out_file_no = 1
    out_buffer = []
    init_browser()
    for out_info in tqdm(work_pool.imap_unordered(get_paper_url, tag_lst), total=len(tag_lst)):
        out_buffer.append(out_info)
        if len(out_buffer) >= 20000:
            write_buffer(out_buffer, out_file_no) 
            out_buffer = []
            out_file_no += 1
    if len(out_buffer) > 0: 
        write_buffer(out_buffer, out_file_no) 
        out_buffer = []
        out_file_no += 1
        
if __name__ == '__main__':
    main()
