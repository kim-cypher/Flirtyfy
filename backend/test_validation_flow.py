import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()
user = User.objects.get(username='fresh_user_223f2340')
token, _ = Token.objects.get_or_create(user=user)

# Test 1: Text too short
print('TEST 1: Text too short (8 chars)')
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
response = client.post('/api/novelty/upload/', {'original_text': 'Hi there'}, format='json')
print(f'Status: {response.status_code}')
resp_json = response.json()
print(f'Error: {resp_json}')

# Test 2: Text just right (10 chars)
print('\nTEST 2: Text valid (10 chars)')
response = client.post('/api/novelty/upload/', {'original_text': 'Hi there ok'}, format='json')
print(f'Status: {response.status_code}')
resp_json = response.json()
if response.status_code == 201:
    upload_id = resp_json.get('id')
    print(f'Success: Upload ID {upload_id}')
else:
    print(f'Error: {resp_json}')

# Test 3: Real conversation
print('\nTEST 3: Real conversation')
real_text = 'I really love spending time with you. What kind of future do you imagine for us together?'
response = client.post('/api/novelty/upload/', {'original_text': real_text}, format='json')
print(f'Status: {response.status_code}')
resp_json = response.json()
if response.status_code == 201:
    upload_id = resp_json.get('id')
    print(f'Success: Upload ID {upload_id}')
else:
    print(f'Error: {resp_json}')
