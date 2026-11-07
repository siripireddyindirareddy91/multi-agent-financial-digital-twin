import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
c=TestClient(app)
def login():
    r=c.post('/api/auth/login',json={'email':'demo@finstress.ai','password':'FinstressDemo!2026'});assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['token']}
def test_auth_required():assert c.get('/api/digital-twins').status_code in [401,403]
def test_end_to_end():
    h=login();t=c.get('/api/digital-twins',headers=h).json()[0];s=c.get('/api/scenarios',headers=h).json()[2]
    r=c.post('/api/simulations/run',headers=h,json={'twin_id':t['id'],'scenario_id':s['id']});assert r.status_code==200
    run=c.get('/api/simulations/'+r.json()['id'],headers=h).json();assert run['status']=='completed';assert len(run['executions'])==10
    mc=c.post('/api/simulations/'+run['id']+'/monte-carlo',headers=h,json={'runs':100});assert mc.status_code==200
    ap=next(a for a in c.get('/api/approvals',headers=h).json() if a['run_id']==run['id'])
    decision=c.post('/api/approvals/'+ap['id']+'/approve',headers=h,json={'comment':'Reviewed synthetic evidence'});assert decision.status_code==200
    assert c.post('/api/approvals/'+ap['id']+'/reject',headers=h,json={'comment':'second decision'}).status_code==409
    report=c.post('/api/reports/generate',headers=h,json={'run_id':run['id']});assert report.status_code==200
    pdf=c.get('/api/reports/'+report.json()['id']+'/download',headers=h);assert pdf.content.startswith(b'%PDF')
    csv=c.get('/api/reports/'+report.json()['id']+'/download?format=csv',headers=h);assert 'synthetic model estimate' in csv.text
def test_tenant_isolation_and_roles():
    email=f'test-{uuid.uuid4()}@example.com';payload={'email':email,'password':'TestSecure!2026'}
    assert c.post('/api/auth/register',json=payload).status_code==200
    token=c.post('/api/auth/login',json=payload).json()['token'];h={'Authorization':'Bearer '+token}
    other=login();t=c.get('/api/digital-twins',headers=other).json()[0]
    assert c.get('/api/digital-twins/'+t['id'],headers=h).status_code==404
    ap=c.get('/api/approvals',headers=other).json()
    if ap:assert c.post('/api/approvals/'+ap[0]['id']+'/approve',headers=h,json={'comment':'No manager access'}).status_code==403
def test_validation():
    h=login();assert c.post('/api/digital-twins',headers=h,json={'name':'Invalid','deposits':999999}).status_code==422
