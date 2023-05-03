from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from multiprocessing import Pool as ProcessPool
import json

def init_browser():
    global driver
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

def get_tag_lst():
    tag_lst = []
    with open('./training_DOI.txt') as f:
        for line in tqdm(f):    
            tag_lst.append(line.strip())
    return tag_lst

def get_paper(tag):
    driver.get('https://doi.org/' + tag)
    html = driver.page_source
    out_info = {
        'tag':tag,
        'url':driver.current_url,
        'html':driver.page_source,
    }
    return out_info

def write_buffer(out_buffer, out_file_no):
    out_file = './outputs/html_%d.jsonl' % out_file_no
    with open(out_file, 'w') as f_o:
        for item in out_buffer:
            f_o.write(json.dumps(item) + '\n')
    
def main():
    tag_lst = get_tag_lst()
    work_pool = ProcessPool(48, initializer=init_browser)
    arg_info_lst = []

    out_file_no = 1
    out_buffer = []
    for out_info in tqdm(work_pool.imap_unordered(get_paper, tag_lst), total=len(tag_lst)):
        out_buffer.append(out_info)
        if len(out_buffer) >= 100:
            write_buffer(out_buffer, out_file_no) 
            out_buffer = []
            out_file_no += 1
    
    write_buffer(out_buffer, out_file_no) 
    out_buffer = []
    out_file_no += 1
        
    '''
    soup = BeautifulSoup(html)
    item_lst = soup.findAll("meta", {"property" : "og:description"})
    if len(item_lst) > 0:
        item = item_lst[0]
        print('\n------------------Abstract----------------\n')
        print(item['content'])
    else:
        print('\n Abstract Not Found \n')

    '''
        
if __name__ == '__main__':
    main()
