import openai
import time

SEP_TOKEN = ' | '

def set_key(key):
    openai.api_key = key

def chat_complete(prompt, temperature=0):
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
