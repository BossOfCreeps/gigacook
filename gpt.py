from gigachat import GigaChat


def gpt_call(payload: str):
    with GigaChat(verify_ssl_certs=False) as giga:
        response = giga.chat(payload)
        return response.choices[0].message.content
