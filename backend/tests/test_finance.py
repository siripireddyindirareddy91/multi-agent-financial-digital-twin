import pytest
from backend.app.finance import calculate,monte_carlo,balance
from backend.app.schemas import TwinInput,ScenarioInput
from backend.app.agents import run_workflow

@pytest.fixture
def twin():return TwinInput(name='Test bank').model_dump()
@pytest.fixture
def severe():return ScenarioInput(name='Severe',gdp=-5,interest=200,unemployment=8,equity_decline=20,real_estate=20,withdrawal=10,defaults=3).model_dump()
def test_demo_balance(twin):assert balance(twin)=={'assets':50000,'liabilities':45000,'equity':5000}
def test_ecl_identity(twin,severe):
    r=calculate(twin,severe);assert r['credit_loss']==pytest.approx(r['pd']*r['lgd']*r['ead'])
def test_balance_and_no_double_counting(twin,severe):
    r=calculate(twin,severe)
    assert r['post_assets']-r['post_liabilities']==pytest.approx(r['post_equity'])
    assert r['equity']-r['losses']==pytest.approx(r['post_equity'])
    assert r['losses']==pytest.approx(r['credit_loss']+r['market_loss']+r['funding_cost'])
def test_withdrawals_not_losses(twin,severe):
    a=calculate(twin,{**severe,'withdrawal':0});b=calculate(twin,severe)
    assert a['losses']==b['losses'];assert a['post_equity']==pytest.approx(b['post_equity']);assert a['lcr']>b['lcr']
def test_more_shock_more_loss(twin,severe):
    mild=ScenarioInput(name='Mild').model_dump();assert calculate(twin,severe)['losses']>calculate(twin,mild)['losses']
def test_monte_carlo_reproducible(twin,severe):
    cfg={'runs':100,'seed':42,'horizon':12,'confidence':.95,'volatility':1}
    a=monte_carlo(twin,severe,cfg);b=monte_carlo(twin,severe,cfg)
    assert a==b;assert a['cvar']>=a['var'];assert sum(h['count'] for h in a['histogram'])==100
    assert a['mean_ci'][0]<=a['mean']<=a['mean_ci'][1]
def test_ten_real_agent_nodes(twin,severe):
    out=run_workflow(twin,severe);assert len(out['executions'])==10
    assert all(x['status']=='completed' and x['output'] for x in out['executions'])
    assert len(out['findings'])==3
