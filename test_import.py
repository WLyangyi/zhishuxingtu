import requests
import json
import time
import os
import sys

sys.path.insert(0, r"C:\Users\流离\AppData\Roaming\Python\Python313\Lib\site-packages")

base_url = 'http://localhost:8000/api'

try:
    r = requests.post(f'{base_url}/auth/register', json={'username': 'testuser_import', 'password': 'test123456'})
    print('Register:', r.status_code)
except Exception as e:
    print('Register error:', e)

r = requests.post(f'{base_url}/auth/login', data={'username': 'testuser_import', 'password': 'test123456'})
print('Login:', r.status_code)
if r.status_code != 200:
    print('Login failed:', r.text)
    sys.exit(1)

token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

r = requests.get(f'{base_url}/import/history/list', headers=headers)
print('History:', r.status_code, r.json())

pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_sample.pdf')
try:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), 'Test PDF for Smart Import Feature', fontsize=14)
    page.insert_text(fitz.Point(72, 100), 'This is a test document for the knowledge management system.', fontsize=11)
    page.insert_text(fitz.Point(72, 120), 'It contains information about machine learning and artificial intelligence.', fontsize=11)
    page.insert_text(fitz.Point(72, 140), 'Key topics: deep learning, neural networks, NLP, computer vision.', fontsize=11)
    doc.save(pdf_path)
    doc.close()
    print(f'Test PDF created at {pdf_path}')
except ImportError:
    pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \n0000000360 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n441\n%%EOF'
    with open(pdf_path, 'wb') as f:
        f.write(pdf_content)
    print(f'Minimal test PDF created at {pdf_path}')

with open(pdf_path, 'rb') as f:
    r = requests.post(f'{base_url}/import/pdf', headers=headers, files={'file': ('test_paper.pdf', f, 'application/pdf')})
    print('Upload PDF:', r.status_code, r.json())

task_id = r.json()['data']['task_id']
print(f'Task ID: {task_id}')

task = None
for i in range(30):
    time.sleep(2)
    r = requests.get(f'{base_url}/import/{task_id}', headers=headers)
    task = r.json()['data']
    status = task['status']
    progress = task['progress']
    message = task['progress_message']
    print(f'  Poll {i+1}: status={status}, progress={progress}%, message={message}')
    if status in ('completed', 'failed'):
        break

if task and task['status'] == 'completed':
    result = task['result']
    print('\nResult:')
    print(f'  Title: {result["title"]}')
    print(f'  Summary: {result["summary"]}')
    print(f'  Key Points: {result["key_points"]}')
    print(f'  Tags: {result["tags"]}')

    r = requests.post(f'{base_url}/import/save', headers=headers, json={
        'task_id': task_id,
        'title': result['title'],
        'summary': result['summary'],
        'key_points': result['key_points'],
        'tags': result['tags']
    })
    print(f'\nSave as note: {r.status_code}', r.json())
elif task:
    error = task.get('error', 'unknown error')
    print(f'\nTask failed: {error}')

try:
    os.remove(pdf_path)
except:
    pass
