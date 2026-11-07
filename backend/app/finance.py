"""Transparent research models. Currency is INR crore; percentages are percentage points."""
from functools import lru_cache
import math
import numpy as np
from sklearn.linear_model import LogisticRegression

AGENTS = [
    ('economic', 'Economic Intelligence', 'Translate macroeconomic shocks into risk assumptions'),
    ('twin', 'Digital Twin', 'Validate and reconcile the institution balance sheet'),
    ('credit', 'Credit Risk', 'Estimate PD with synthetic-trained logistic regression and calculate ECL'),
    ('market', 'Market Risk', 'Revalue bonds and equity exposures'),
    ('liquidity', 'Liquidity Risk', 'Measure withdrawals, liquid assets and funding gaps'),
    ('capital', 'Capital Adequacy', 'Measure post-loss capital against risk-weighted assets'),
    ('simulation', 'Stress Simulation', 'Project the balance sheet across the scenario horizon'),
    ('orchestrator', 'Risk Orchestrator', 'Consolidate and prioritize computed findings'),
    ('explainability', 'Explainability', 'Trace findings to inputs and calculation evidence'),
    ('human', 'Human Review', 'Route material recommendations for human decision'),
]

@lru_cache(maxsize=1)
def credit_model():
    rng = np.random.default_rng(42)
    x = rng.normal(size=(6000, 4))
    logits = -3.6 + x @ np.array([.5, .8, .65, .4])
    y = rng.binomial(1, 1 / (1 + np.exp(-logits)))
    return LogisticRegression(random_state=42).fit(x, y)

def balance(t):
    assets = sum(t[k] for k in ('cash', 'loans', 'government', 'bonds', 'equities'))
    liabilities = t['deposits'] + t['wholesale']
    return {'assets': assets, 'liabilities': liabilities, 'equity': assets - liabilities}

def calculate(t, s):
    b = balance(t)
    years = s['duration'] / 12
    features = [[s['interest']/200, max(0, -s['gdp'])/4, max(0, s['unemployment']-4)/4, s['defaults']/3]]
    pd_annual = float(credit_model().predict_proba(features)[0, 1])
    pd = 1 - (1 - pd_annual) ** years
    lgd = min(.85, .4 + s['real_estate'] / 200)
    credit_loss = pd * lgd * t['loans']
    # Duration approximation, no equity/credit overlap: equities and bonds are separate buckets.
    government_loss = min(t['government'], t['government'] * 4 * max(0,s['interest'])/10000)
    bond_loss = min(t['bonds'], t['bonds'] * (3 * max(0,s['interest'])/10000 + s['defaults']/100))
    equity_loss = t['equities'] * s['equity_decline']/100
    market_loss = government_loss + bond_loss + equity_loss
    funding_cost = t['wholesale'] * max(0, s['interest'])/10000 * years
    losses = credit_loss + market_loss + funding_cost
    withdrawals = t['deposits'] * s['withdrawal']/100
    # Deposit repayment reduces assets AND liabilities; it is not a P&L loss.
    repayment = min(withdrawals, max(0, b['assets'] - losses))
    post_assets = b['assets'] - losses - repayment
    post_liabilities = b['liabilities'] - repayment
    capital = post_assets - post_liabilities
    rwa = t['loans'] + .5*t['bonds'] + t['equities']
    car = capital / max(1,rwa)*100
    hqla = max(0, t['cash'] + .85*(t['government']-government_loss) - repayment)
    outflows = max(1, .05*(t['deposits']-repayment) + .15*t['wholesale'])
    lcr = hqla / outflows * 100
    score = float(np.clip(.4*min(100,car/12*100) + .35*min(100,lcr) + .25*(1-pd)*100,0,100))
    r = {**b, 'post_assets':post_assets,'post_liabilities':post_liabilities,'post_equity':capital,
         'pd':pd,'lgd':lgd,'ead':t['loans'],'credit_loss':credit_loss,'market_loss':market_loss,
         'funding_cost':funding_cost,'losses':losses,'withdrawals':repayment,'unfunded_withdrawals':withdrawals-repayment,
         'rwa':rwa,'car':car,'lcr':lcr,'hqla':hqla,'outflows':outflows,'funding_gap':max(0,outflows-hqla),
         'resilience':score,'npl':pd*100,'baseline_car':b['equity']/max(1,rwa)*100}
    r['timeline'] = [{'month': f'M{i}', 'baseline':r['baseline_car'],
        'capital':r['baseline_car']+(car-r['baseline_car'])*i/s['duration'],
        'assets':b['assets']+(post_assets-b['assets'])*i/s['duration']} for i in range(s['duration']+1)]
    return r

def findings(r, s):
    return [
      {'metric':'Capital adequacy','severity':'critical' if r['car']<8 else 'warning' if r['car']<12 else 'stable',
       'value':r['car'],'unit':'%','cause':'Credit, valuation and funding losses reduce equity; RWA held constant.',
       'evidence':f"CAR = {r['post_equity']:.2f} / {r['rwa']:.2f} × 100 = {r['car']:.2f}%",
       'impact':max(0,.12*r['rwa']-r['post_equity']),'recommendation':'Review capital buffer and consider a capital restoration plan.'},
      {'metric':'Liquidity coverage','severity':'critical' if r['lcr']<100 else 'stable','value':r['lcr'],'unit':'%',
       'cause':f"Deposit withdrawal assumption: {s['withdrawal']}%. Repayments consume liquid assets.",
       'evidence':f"LCR = {r['hqla']:.2f} / {r['outflows']:.2f} × 100 = {r['lcr']:.2f}%",
       'impact':r['funding_gap'],'recommendation':'Review liquid asset buffers and diversify funding sources.'},
      {'metric':'Expected credit loss','severity':'warning' if r['pd']>.1 else 'stable','value':r['credit_loss'],'unit':'crore',
       'cause':'Synthetic-trained logistic model estimates PD from rates, GDP, unemployment and default shock.',
       'evidence':f"ECL = PD {r['pd']:.5f} × LGD {r['lgd']:.3f} × EAD {r['ead']:.2f}",
       'impact':r['credit_loss'],'recommendation':'Review high-risk lending exposures and underwriting limits.'},
    ]

def monte_carlo(t,s,config):
    rng = np.random.default_rng(config['seed'])
    n = config['runs']; vol=config['volatility']
    # A common macro factor induces positive shock correlation; independent idiosyncratic factors remain.
    z = rng.normal(size=(n,5))
    factors = .65*z[:,0,None] + math.sqrt(1-.65**2)*z[:,1:]
    losses=[]; cars=[]; lcrs=[]; scores=[]
    for row in factors:
        shock=dict(s); shock['duration']=config['horizon']
        shock['gdp']=float(np.clip(s['gdp']-row[0]*vol,-20,15))
        shock['interest']=float(np.clip(s['interest']+row[1]*vol*50,-200,1000))
        shock['withdrawal']=float(np.clip(s['withdrawal']+row[2]*vol*2,0,80))
        shock['equity_decline']=float(np.clip(s['equity_decline']+row[3]*vol*5,0,80))
        r=calculate(t,shock); losses.append(r['losses']); cars.append(r['car']); lcrs.append(r['lcr']); scores.append(r['resilience'])
    a=np.array(losses); confidence=config['confidence']; var=float(np.quantile(a,confidence))
    counts,edges=np.histogram(a,bins=24)
    se=float(a.std(ddof=1)/math.sqrt(n))
    from statistics import NormalDist
    critical=NormalDist().inv_cdf((1+confidence)/2)
    return {**config,'mean':float(a.mean()),'var':var,'cvar':float(a[a>=var].mean()),
      'mean_ci':[float(a.mean()-critical*se),float(a.mean()+critical*se)],
      'liquidity_shortfall_probability':float(np.mean(np.array(lcrs)<100)),
      'capital_percentiles':[float(x) for x in np.quantile(cars,[.05,.5,.95])],
      'resilience_percentiles':[float(x) for x in np.quantile(scores,[.05,.5,.95])],
      'percentiles':[{'percentile':p,'loss':float(np.percentile(a,p))} for p in [1,5,25,50,75,95,99]],
      'histogram':[{'loss':float((edges[i]+edges[i+1])/2),'count':int(c)} for i,c in enumerate(counts)],
      'assumptions':'Correlated Gaussian macro shocks, clipped to scenario bounds. Correlation uses a common factor (0.4225 pairwise). VaR is a loss quantile, not a confidence interval. Mean CI uses a normal approximation. Synthetic research model, not a calibrated bank forecast.'}
