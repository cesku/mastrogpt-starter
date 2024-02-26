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


def alert_on_slack(text):
    requests.get(f'https://nuvolaris.dev/api/v1/web/utils/demo/slack?text={urllib.parse.quote_plus(text)}')


def check_for_email(text):
    pattern = r'[\w\.-]+@[\w\.-]+'
    match = re.search(pattern, text)
    if match:
        return match.group()


def is_valid_email(email):
    response = requests.get(
        f'https://api.usebouncer.com/v1.1/email/verify?email={email}',
        auth=('', 'ZnPBfGaYU27DsDyrb5BtZ5VQ5126l02daQhQjWJY'),
    )
    if response.ok:
        data = response.json()
        if data.get('status', '') == 'deliverable':
            return True
    return False

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
            if is_valid_email(email_in_input):
                alert_on_slack(f'received email of {email_in_input}')
                result["output"] = "Thank you for providing your email"
                result["message"] = "Just sent an alert on slack with the email"                
            else:
                alert_on_slack(f'received FAKE email of {email_in_input}')
                result["output"] = "You're trying to trick me, this email is FAKE"
                result["message"] = "Just sent an alert on slack with the FAKE email"   

        elif domain_in_input:
            alert_on_slack(f'getting info for domain {domain_in_input}')
            ip_address = domain_to_ip(domain_in_input)
            input = f"Assuming  {domain_in_input} has IP address {ip_address}, answer to this question: {input}"
            result["message"] = f"Just resolved a domain IP ({ip_address})"
    
        if not result['output']:
            result['output'] = ask(input)

    return {"body": result }
