#!/usr/bin/env python3

import sys

import openai

import eywa.key as key


class GPT4:
    def __init__(self):
        # openai.api_type = ''
        # openai.api_base = ''
        # openai.api_version = ''
        openai.api_key = key.get_key()
        # self.engine_ = ''

    def query_openai_endpoint(self, user_prompt: str, temperature: float = 0.0, system_prompt: str = None) -> str:
        '''
        Query the OpenAI endpoint and return the response.

        Args:
            user_prompt (str): The prompt to use.
            system_prompt (str): The system prompt to use.
        '''

        messages = [{'role': 'user', 'content': user_prompt}]
        if system_prompt is not None and system_prompt != "":
            messages.append({'role': 'system', 'content': system_prompt})

        response = openai.chat.completions.create(
            # engine=self.engine_,
            model='gpt-4',
            messages=messages,
            temperature=temperature,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None)

        top_choice = response.choices[0]
        if top_choice.finish_reason != 'stop':
            sys.exit(
                f'Model did not finish properly: {top_choice.finish_reason}')

        response_text = top_choice.message.content
        return response_text
