import openai
from django.conf import settings

def generate_reply(prompt, context, temperature=0.8):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=300,
    )
    return response['choices'][0]['message']['content']
