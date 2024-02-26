#--web true
#--param OPENAI_API_KEY $OPENAI_API_KEY
#--param OPENAI_API_HOST $OPENAI_API_HOST

from openai import AzureOpenAI
import re
import requests
import socket
import urllib.parse

ROLE = """
When requested to write code, pick Python.
When requested to show chess position, always use the FEN notation.
When showing HTML, always include what is in the body tag, 
but exclude the code surrounding the actual content. 
So exclude always BODY, HEAD and HTML .
"""

MODEL = "gpt-35-turbo"
AI = None

def req(msg):
    return [{"role": "system", "content": ROLE}, 
            {"role": "user", "content": msg}]

def ask(input):
    comp = AI.chat.completions.create(model=MODEL, messages=req(input))
    if len(comp.choices) > 0:
        content = comp.choices[0].message.content
        return content
    return "ERROR"


"""
import re
from pathlib import Path
text = Path("util/test/chess.txt").read_text()
text = Path("util/test/html.txt").read_text()
text = Path("util/test/code.txt").read_text()
"""
def extract(text):
    res = {}

    # search for a chess position
    pattern = r'(([rnbqkpRNBQKP1-8]{1,8}/){7}[rnbqkpRNBQKP1-8]{1,8} [bw] (-|K?Q?k?q?) (-|[a-h][36]) \d+ \d+)'
    m = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    #print(m)
    if len(m) > 0:
        res['chess'] = m[0][0]
        return res

    # search for code
    pattern = r"```(\w+)\n(.*?)```"
    m = re.findall(pattern, text, re.DOTALL)
    if len(m) > 0:
        if m[0][0] == "html":
            html = m[0][1]
            # extract the body if any
            pattern = r"<body.*?>(.*?)</body>"
            m = re.findall(pattern, html, re.DOTALL)
            if m:
                html = m[0]
            res['html'] = html
            return res
        res['language'] = m[0][0]
        res['code'] = m[0][1]
        return res
    
    return res

def alert_on_slack(text):
    #requests.get(f'https://nuvolaris.dev/api/v1/web/utils/demo/slack?text=ciao+da+{match.group()}')
    requests.get(f'http://reflab.com/alert?{urllib.parse.quote_plus(text)}')

def check_for_email(text):
    pattern = r'[\w\.-]+@[\w\.-]+'
    match = re.search(pattern, text)
    if match:
        return match.group()

def check_for_domain(text):
    pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(?:/[^\s]*)?'
    match = re.search(pattern, text)
    if match:
        return match.group()

def domain_to_ip(domain):
    try:
        ip_address = socket.gethostbyname(domain)
        return ip_address
    except socket.gaierror:
        return None


def main(args):
    global AI
    (key, host) = (args["OPENAI_API_KEY"], args["OPENAI_API_HOST"])
    AI = AzureOpenAI(api_version="2023-12-01-preview", api_key=key, azure_endpoint=host)

    input = args.get("input", "")
    if input == "":
        result = {
            "output": "Welcome to the OpenAI demo chat created by Francesco Merlo",
            "title": "OpenAI Chat",
            "message": "You can chat with OpenAI."
        }
    else:
        email_in_input = check_for_email(input)
        domain_in_input = check_for_domain(input)
        result = {
            "title": "OpenAI Chat",
            "message": "Chatting with OpenAI",
            "output": ""
        }

        if email_in_input:
            alert_on_slack('ricevuta email di {email_in_input}')
            result["output"] = "Thank you for providing your email"
            result["message"] = "Just sent an alert on slack with the email"                

        if domain_in_input:
            ip_address = domain_to_ip(domain_in_input)
            input = f"Assuming  {domain_in_input} has IP address {ip_address}, answer to this question: {input}"
            result["message"] = f"Just resolved a domain IP ({ip_address})"
    
        if not result['output']:
            output = ask(input)
            result['output'] = f'** {output}'

    return {"body": result }
