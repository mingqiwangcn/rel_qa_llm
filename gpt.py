import openai
import time

SEP_TOKEN = ' | '
f_log = None
prompt_no = 0

def set_key(key):
    openai.api_key = key

def set_logger(logger):
    global f_log
    f_log = logger

def write_log(log_msg, commit=False):
    f_log.write(log_msg + '\n')
    if commit:
        f_log.flush()

def chat_complete(prompt, temperature=0):
    global prompt_no
    prompt_no += 1
    write_log(f'prompt {prompt_no}')
    write_log('-'*100)
    write_log(prompt)
    retry_cnt = 0
    response = None
    wait_seconds = 3
    while response is None:
        try:
            response = call_gpt(prompt, temperature)
        except openai.error.RateLimitError as err:
            response = None
            retry_cnt += 1
            print('Error from GPT')
            print('\n')
            print(err)
            print('\n')
            print(f'Retry {retry_cnt} to call GPT in {wait_seconds} seconds\n')
            time.sleep(wait_seconds)
    
    write_log('\n' + '*'*30 + '\n')
    write_log(response)
    write_log('-'*100, commit=True)
    return response

def call_gpt(prompt, temperature):
    MODEL = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    out_msg = response['choices'][0]['message']['content']
    return out_msg
