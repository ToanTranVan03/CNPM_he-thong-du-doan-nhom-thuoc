import sys
import json
from app import app

client = app.test_client()

def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)

# 1) Login admin
r = client.post('/api/login', json={'email':'admin@gmail.com','password':'123456'})
if r.status_code != 200:
    fail(f'login failed: {r.status_code} {r.data}')

token = r.get_json().get('token')
if not token:
    fail('no token returned')
headers = {'Authorization': f'Bearer {token}'}

# 2) Create symptom
import time
ma_val = f"TEST_{int(time.time()*1000)}"
payload = {'ten':'Test Symptom XYZ','ma':ma_val,'ten_en':'test symptom','synonyms':['test','xyz'],'mo_ta':'mota'}
r = client.post('/api/symptoms', json=payload, headers=headers)
if r.status_code != 201:
    fail(f'create failed: {r.status_code} {r.data}')
item = r.get_json()
item_id = item.get('id')
print('Created id=', item_id)

# 3) List symptoms (no filter)
r = client.get('/api/admin/symptoms')
print('LIST STATUS', r.status_code, 'BODY', r.get_data(as_text=True))
if r.status_code != 200:
    fail('list failed')
data = r.get_json()
if data.get('total',0) < 1:
    fail(f"list returned empty, body={r.get_data(as_text=True)}")
# optional: check q filter works (non-fatal)
r = client.get('/api/symptoms?q=Test')
print('Q-LIST STATUS', r.status_code, 'BODY', r.get_data(as_text=True))
if r.status_code == 200:
    dq = r.get_json()
    print('q-filter returned', dq.get('total',0), 'hits')

# 4) Get detail
r = client.get(f'/api/symptoms/{item_id}')
if r.status_code != 200:
    fail('get detail failed')

# 5) Update
r = client.put(f'/api/symptoms/{item_id}', json={'ten':'Test Symptom XYZ Updated'}, headers=headers)
if r.status_code != 200:
    fail('update failed')
new = r.get_json()
if new.get('ten') != 'Test Symptom XYZ Updated':
    fail('update did not change ten')

# 6) Delete
r = client.delete(f'/api/symptoms/{item_id}', headers=headers)
if r.status_code != 200:
    fail('delete failed')

# 7) Confirm deleted
r = client.get(f'/api/symptoms/{item_id}')
if r.status_code != 404:
    fail('item still present after delete')

print('SMOKE TESTS PASSED')
sys.exit(0)
