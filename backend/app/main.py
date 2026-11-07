import os, json, secrets, hashlib, hmac, io, csv, threading, logging, uuid
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
import jwt
from .database import Base, engine, Session, User, Twin, Scenario, Run, Approval, Audit, Report, Settings, Execution, uid
from .schemas import Credentials, TwinInput, ScenarioInput, RunInput, MCInput, Decision, ReportInput
from .finance import AGENTS, calculate, balance, monte_carlo
from .agents import run_workflow

logging.basicConfig(level=logging.INFO)
log=logging.getLogger('finstress')
app=FastAPI(title='FINSTRESS AI',version='1.0.0',description='Synthetic financial digital twin research platform. Currency: INR crore.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000').split(','),allow_methods=['*'],allow_headers=['*'])
security=HTTPBearer()
SECRET=os.getenv('JWT_SECRET') or secrets.token_urlsafe(48)
DEMO_PASSWORD=os.getenv('DEMO_PASSWORD','FinstressDemo!2026')
init_lock=threading.Lock(); initialized=False
def password_hash(p,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),260000).hex()
def password_ok(p,stored): return hmac.compare_digest(password_hash(p,stored.split(':')[0]),stored)
def serialize(row): return {'id':row.id,**row.data,'created_at':row.created_at.isoformat(),'updated_at':row.updated_at.isoformat()}
def audit(db,user,action,details): db.add(Audit(owner_id=user.id,data={'actor':user.email,'action':action,'details':details}))
def seed_user(db,user):
    twin=Twin(id=str(uuid.uuid5(uuid.NAMESPACE_URL,user.email+'/aurelia')),owner_id=user.id,data=TwinInput(name='Aurelia National Bank').model_dump()); db.add(twin)
    defaults=[('Baseline','baseline',2,3,0,4,0,0,0,0),('Moderate Economic Slowdown','moderate',-2,4,100,5,10,10,5,1),('Severe Financial Crisis','severe',-5,7,200,8,20,20,10,3),('Extreme Global Economic Shock','extreme',-8,10,300,12,35,30,20,6)]
    for name,severity,gdp,inflation,interest,unemployment,equity,estate,withdrawal,defaults_n in defaults:
        db.add(Scenario(id=str(uuid.uuid5(uuid.NAMESPACE_URL,user.email+'/'+severity)),owner_id=user.id,data=ScenarioInput(name=name,severity=severity,gdp=gdp,inflation=inflation,interest=interest,unemployment=unemployment,equity_decline=equity,real_estate=estate,withdrawal=withdrawal,defaults=defaults_n,description='Synthetic research scenario.').model_dump()))
    audit(db,user,'workspace.initialized','Synthetic institution and scenarios created')
def initialize():
    global initialized
    if initialized:return
    with init_lock:
        if initialized:return
        Base.metadata.create_all(engine)
        with Session() as db:
            if os.getenv('ENABLE_DEMO','true').lower()=='true' and not db.scalar(select(User).where(User.email=='demo@finstress.ai')):
                u=User(id=str(uuid.uuid5(uuid.NAMESPACE_URL,'demo@finstress.ai')),email='demo@finstress.ai',password=password_hash(DEMO_PASSWORD),role='manager'); db.add(u); db.flush(); seed_user(db,u); db.commit()
        initialized=True
def db_session():
    initialize()
    with Session() as db: yield db
def current_user(creds:HTTPAuthorizationCredentials=Depends(security),db=Depends(db_session)):
    try:
        payload=jwt.decode(creds.credentials,SECRET,algorithms=['HS256']); user=db.get(User,payload['sub'])
        if not user:raise ValueError()
        return user
    except Exception:raise HTTPException(401,'Session expired. Please sign in again.')
def owned(db,model,id,user):
    item=db.get(model,id)
    if not item or item.owner_id!=user.id:raise HTTPException(404,'Record not found')
    return item
def manager(user):
    if user.role not in ['manager','administrator']:raise HTTPException(403,'Risk manager or administrator role required')
def writer(user):
    if user.role=='auditor':raise HTTPException(403,'Auditor access is read-only')
attempts=defaultdict(deque); rate_lock=threading.Lock()
def rate_limit(request):
    import time
    key=request.client.host if request.client else 'unknown'
    with rate_lock:
        q=attempts[key]; now=time.monotonic()
        while q and q[0]<now-60:q.popleft()
        if len(q)>=20:raise HTTPException(429,'Too many authentication attempts; retry in a minute')
        q.append(now)
@app.get('/api/health')
def health(db=Depends(db_session)):
    return {'status':'ok','synthetic':True,'storage':'PostgreSQL' if engine.dialect.name=='postgresql' else 'SQLite demo (ephemeral on Vercel)','persistent':engine.dialect.name=='postgresql','llm':'deterministic LangGraph agents','jwt_configured':bool(os.getenv('JWT_SECRET'))}
@app.post('/api/auth/register')
def register(body:Credentials,request:Request,db=Depends(db_session)):
    rate_limit(request)
    if db.scalar(select(User).where(User.email==body.email.lower())):raise HTTPException(409,'Email already registered')
    u=User(email=body.email.lower(),password=password_hash(body.password),role='analyst');db.add(u);db.flush();seed_user(db,u);db.commit()
    return {'message':'Account created. Sign in to continue.'}
@app.post('/api/auth/login')
def login(body:Credentials,request:Request,db=Depends(db_session)):
    rate_limit(request); u=db.scalar(select(User).where(User.email==body.email.lower()))
    if not u or not password_ok(body.password,u.password):raise HTTPException(401,'Invalid email or password')
    token=jwt.encode({'sub':u.id,'exp':datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm='HS256')
    audit(db,u,'auth.login','Signed in');db.commit()
    return {'token':token,'user':{'email':u.email,'role':u.role}}
@app.get('/api/auth/me')
def me(u=Depends(current_user)):return {'id':u.id,'email':u.email,'role':u.role}

def crud(model,path,schema):
    def listing(u=Depends(current_user),db=Depends(db_session)):
        return [serialize(x) for x in db.scalars(select(model).where(model.owner_id==u.id).order_by(model.created_at))]
    def get(id:str,u=Depends(current_user),db=Depends(db_session)):return serialize(owned(db,model,id,u))
    def create(body:schema,u=Depends(current_user),db=Depends(db_session)):
        writer(u); item=model(owner_id=u.id,data=body.model_dump());db.add(item);db.flush();audit(db,u,path+'.created',item.id);db.commit();return serialize(item)
    def update(id:str,body:schema,u=Depends(current_user),db=Depends(db_session)):
        writer(u);item=owned(db,model,id,u);item.data=body.model_dump();audit(db,u,path+'.updated',id);db.commit();return serialize(item)
    def delete(id:str,u=Depends(current_user),db=Depends(db_session)):
        writer(u);item=owned(db,model,id,u);db.delete(item);audit(db,u,path+'.deleted',id);db.commit();return {'deleted':id}
    for method,endpoint,fn in [('GET',path,listing),('POST',path,create),('GET',path+'/{id}',get),('PUT',path+'/{id}',update),('DELETE',path+'/{id}',delete)]:
        app.add_api_route('/api/'+endpoint,fn,methods=[method],name=method+' '+endpoint)
crud(Twin,'digital-twins',TwinInput);crud(Scenario,'scenarios',ScenarioInput)

def execute_run(run_id,user_id):
    with Session() as db:
        run=db.get(Run,run_id); user=db.get(User,user_id)
        try:
            run.data={**run.data,'status':'running'};db.commit()
            def record(execution):
                db.add(Execution(owner_id=user_id,data={**execution,'run_id':run_id}));db.commit()
            out=run_workflow(run.data['twin'],run.data['scenario'],record)
            for f in out['findings']:
                db.add(Approval(owner_id=user_id,data={'run_id':run_id,'title':f['recommendation'],'metric':f['metric'],'severity':f['severity'],'impact':f['impact'],'status':'pending','evidence':f['evidence'],'decisions':[]}))
            run.data={**run.data,'status':'completed','result':out['result'],'findings':out['findings'],'executions':out['executions']}
            audit(db,user,'simulation.completed',run_id);db.commit()
        except Exception:
            db.rollback();log.exception('Simulation failed',extra={'run_id':run_id});run=db.get(Run,run_id);run.data={**run.data,'status':'failed','error':'Calculation failed; inspect server logs.'};db.commit()
@app.post('/api/simulations/run')
def start_run(body:RunInput,tasks:BackgroundTasks,u=Depends(current_user),db=Depends(db_session)):
    writer(u);t=owned(db,Twin,body.twin_id,u);s=owned(db,Scenario,body.scenario_id,u)
    run=Run(owner_id=u.id,data={'status':'queued','twin_id':t.id,'scenario_id':s.id,'twin':t.data,'scenario':s.data,'synthetic':True})
    db.add(run);db.flush();audit(db,u,'simulation.started',run.id);db.commit();tasks.add_task(execute_run,run.id,u.id);return serialize(run)
@app.get('/api/simulations')
def runs(u=Depends(current_user),db=Depends(db_session)):return [serialize(x) for x in db.scalars(select(Run).where(Run.owner_id==u.id).order_by(Run.created_at.desc()))]
@app.get('/api/simulations/{id}')
@app.get('/api/simulations/{id}/results')
def run_detail(id:str,u=Depends(current_user),db=Depends(db_session)):return serialize(owned(db,Run,id,u))
@app.post('/api/simulations/{id}/monte-carlo')
def mc(id:str,body:MCInput,u=Depends(current_user),db=Depends(db_session)):
    writer(u);r=owned(db,Run,id,u)
    if r.data['status']!='completed':raise HTTPException(409,'Complete the stress run first')
    result=monte_carlo(r.data['twin'],r.data['scenario'],body.model_dump());r.data={**r.data,'monte_carlo':result};audit(db,u,'monte_carlo.completed',{'run_id':id,'seed':body.seed,'runs':body.runs});db.commit();return result
@app.get('/api/overview')
def overview(twin_id:str|None=None,u=Depends(current_user),db=Depends(db_session)):
    twins=list(db.scalars(select(Twin).where(Twin.owner_id==u.id)))
    if not twins:return {'empty':True}
    t=owned(db,Twin,twin_id,u) if twin_id else twins[0]
    scenarios=list(db.scalars(select(Scenario).where(Scenario.owner_id==u.id)))
    comparisons=[{'id':s.id,'name':s.data['name'],'severity':s.data['severity'],**calculate(t.data,s.data)} for s in scenarios]
    baseline=next((x for x in comparisons if x['severity']=='baseline'),comparisons[0] if comparisons else calculate(t.data,ScenarioInput(name='Baseline',gdp=2,interest=0,withdrawal=0,defaults=0).model_dump()))
    return {'twin':serialize(t),'baseline':baseline,'comparisons':comparisons,'synthetic':True}
@app.get('/api/agents')
def agents(u=Depends(current_user)):return [{'id':k,'name':n,'role':r,'input_schema':['twin','scenario','prior results'],'output_schema':'Structured calculation evidence','mode':'deterministic'} for k,n,r in AGENTS]
@app.get('/api/agents/executions')
def executions(run_id:str|None=None,u=Depends(current_user),db=Depends(db_session)):
    rows=[serialize(x) for x in db.scalars(select(Execution).where(Execution.owner_id==u.id).order_by(Execution.created_at.desc()))]
    return [r for r in rows if not run_id or r['run_id']==run_id]
@app.get('/api/agents/{id}')
def agent(id:str,u=Depends(current_user)):
    found=next((a for a in agents(u) if a['id']==id),None)
    if not found:raise HTTPException(404,'Agent not found')
    return found
@app.get('/api/risks')
@app.get('/api/risks/explanations')
def risks(u=Depends(current_user),db=Depends(db_session)):
    rows=db.scalars(select(Run).where(Run.owner_id==u.id).order_by(Run.created_at.desc()))
    return [{**f,'run_id':r.id,'scenario':r.data['scenario']['name']} for r in rows for f in r.data.get('findings',[])]
@app.get('/api/risks/summary')
def risk_summary(u=Depends(current_user),db=Depends(db_session)):
    items=risks(u,db);return {k:sum(f['severity']==k for f in items) for k in ['critical','warning','stable']}
@app.get('/api/approvals')
def approvals(u=Depends(current_user),db=Depends(db_session)):return [serialize(x) for x in db.scalars(select(Approval).where(Approval.owner_id==u.id).order_by(Approval.created_at.desc()))]
def decide(id,body,u,db,status):
    manager(u)
    item=db.scalar(select(Approval).where(Approval.id==id,Approval.owner_id==u.id).with_for_update())
    if not item:raise HTTPException(404,'Record not found')
    if item.data['status']!='pending':raise HTTPException(409,'This recommendation was already reviewed')
    decision={'status':status,'comment':body.comment,'actor':u.email,'at':datetime.now(timezone.utc).isoformat()}
    item.data={**item.data,'status':status,'decisions':item.data['decisions']+[decision]};audit(db,u,'approval.'+status,{'id':id,**decision});db.commit();return serialize(item)
@app.post('/api/approvals/{id}/approve')
def approve(id:str,body:Decision,u=Depends(current_user),db=Depends(db_session)):return decide(id,body,u,db,'approved')
@app.post('/api/approvals/{id}/reject')
def reject(id:str,body:Decision,u=Depends(current_user),db=Depends(db_session)):return decide(id,body,u,db,'rejected')
@app.get('/api/audit-logs')
def logs(u=Depends(current_user),db=Depends(db_session)):return [serialize(x) for x in db.scalars(select(Audit).where(Audit.owner_id==u.id).order_by(Audit.created_at.desc()))]
@app.get('/api/settings')
def settings(u=Depends(current_user),db=Depends(db_session)):
    item=db.scalar(select(Settings).where(Settings.owner_id==u.id));return item.data if item else {'notifications':True,'currency':'INR crore','confidence':.95}
@app.put('/api/settings')
def save_settings(body:dict,u=Depends(current_user),db=Depends(db_session)):
    writer(u)
    if len(json.dumps(body))>5000:raise HTTPException(422,'Settings too large')
    item=db.scalar(select(Settings).where(Settings.owner_id==u.id))
    if item:item.data=body
    else:db.add(Settings(owner_id=u.id,data=body))
    audit(db,u,'settings.updated',body);db.commit();return body
@app.post('/api/reports/generate')
def generate(body:ReportInput,u=Depends(current_user),db=Depends(db_session)):
    writer(u);r=owned(db,Run,body.run_id,u)
    if r.data['status']!='completed':raise HTTPException(409,'Complete a simulation first')
    report=Report(owner_id=u.id,data={'run_id':r.id,'name':r.data['scenario']['name'],'snapshot':r.data});db.add(report);db.flush();audit(db,u,'report.generated',report.id);db.commit();return serialize(report)
@app.get('/api/reports')
def reports(u=Depends(current_user),db=Depends(db_session)):return [{k:v for k,v in serialize(x).items() if k!='snapshot'} for x in db.scalars(select(Report).where(Report.owner_id==u.id).order_by(Report.created_at.desc()))]
@app.get('/api/reports/{id}/download')
def download(id:str,format:str='pdf',u=Depends(current_user),db=Depends(db_session)):
    report=owned(db,Report,id,u);snap=report.data['snapshot'];r=snap['result']
    audit(db,u,'report.downloaded',{'id':id,'format':format});db.commit()
    if format=='csv':
        out=io.StringIO();w=csv.writer(out);w.writerow(['metric','value','unit','data_type']);
        for k,v in r.items():
            if isinstance(v,(int,float)):w.writerow([k,v,'percent' if k in ['car','lcr','npl','baseline_car'] else 'ratio' if k in ['pd','lgd'] else 'INR crore / score','synthetic model estimate'])
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="finstress-{id}.csv"'})
    if format!='pdf':raise HTTPException(422,'Use pdf or csv')
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from xml.sax.saxutils import escape
    buf=io.BytesIO();styles=getSampleStyleSheet();story=[]
    def para(text,style='BodyText'):story.append(Paragraph(escape(str(text)),styles[style]));story.append(Spacer(1,8))
    para('FINSTRESS AI','Title');para('Financial Digital Twin & Stress Testing Report','Heading1');para('SYNTHETIC DATA | RESEARCH DEMONSTRATION | NOT A REGULATORY ASSESSMENT')
    sections=[('Executive summary',{'scenario':snap['scenario']['name'],'losses_INR_crore':round(r['losses'],2),'CAR_percent':round(r['car'],2),'LCR_percent':round(r['lcr'],2)}),('Institution profile',snap['twin']),('Digital twin configuration',balance(snap['twin'])),('Economic assumptions',snap['scenario']),('Stress scenario',{'name':snap['scenario']['name'],'duration_months':snap['scenario']['duration']}),('Credit risk',{k:r[k] for k in ['pd','lgd','ead','credit_loss']}),('Market risk',{k:r[k] for k in ['market_loss','funding_cost']}),('Liquidity risk',{k:r[k] for k in ['lcr','hqla','outflows','funding_gap']}),('Capital adequacy',{k:r[k] for k in ['car','rwa','post_equity']}),('Monte Carlo results',snap.get('monte_carlo',{'status':'Not run for this report snapshot'})),('Scenario comparison',{'baseline_car':r['baseline_car'],'stressed_car':r['car']}),('Explainable findings',snap.get('findings',[])),('Mitigation recommendations',[f['recommendation'] for f in snap.get('findings',[])]),('Human approval decisions',[a.data for a in db.scalars(select(Approval).where(Approval.owner_id==u.id)) if a.data.get('run_id')==report.data['run_id']]),('Methodology and limitations',{'units':'INR crore','credit':'ECL = PD x LGD x EAD; synthetic-trained logistic regression. LGD increases with real estate decline.','market':'4-year government bond duration, 3-year corporate bond duration; no losses counted twice.','liquidity':'Deposit repayments reduce assets and liabilities equally. Remaining cash plus 85% government securities / modeled 30-day outflows.','resilience':'40% capital, 35% liquidity, 25% credit quality; each normalized to 0-100. Not an official rating.','limitations':'No real bank data or calibration. RWA fixed; no dynamic management response. Inflation contextual only.'})]
    for title,content in sections:
        para(title,'Heading2')
        if isinstance(content,dict):
            for k,v in content.items():
                if k not in ['histogram','timeline']:para(f'{k}: {v}')
        else:
            for entry in content:para(json.dumps(entry,ensure_ascii=True) if isinstance(entry,dict) else entry)
    SimpleDocTemplate(buf,title='FINSTRESS AI Research Report').build(story)
    return Response(buf.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="finstress-{id}.pdf"'})
