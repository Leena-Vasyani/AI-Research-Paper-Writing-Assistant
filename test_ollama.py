import requests, os
from dotenv import load_dotenv

load_dotenv()

url = 'https://ollama.com/api/chat'
token_str = 'This is a long test to see if ollama cuts off or does something weird when the context is maxed out. ' * 600
payload = {
    'model': 'qwen3.5:397b-cloud', 
    'messages': [{'role':'user','content': 'Summarize this: ' + token_str}], 
    'stream': False
}
api_key = os.environ.get("OLLAMA_API_KEY", "")
headers = {
    'Content-Type': 'application/json', 
    'Authorization': f'Bearer {api_key}'
}

try:
    resp = requests.post(url, json=payload, headers=headers)
    print('Status:', resp.status_code)
    data = resp.json()
    print('JSON response:', data)
    print('Message Content:', data.get("message", {}).get("content"))
except Exception as e:
    print('Error:', e)
