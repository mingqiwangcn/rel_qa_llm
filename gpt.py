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

 
