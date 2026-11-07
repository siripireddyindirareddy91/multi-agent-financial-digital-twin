from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .finance import AGENTS, calculate, balance, findings
class AgentState(TypedDict):
    twin:dict
    scenario:dict
    result:dict
    findings:list
    executions:list

def run_workflow(twin,scenario,on_execution=None):
    graph=StateGraph(AgentState)
    def make_node(key,title):
        def node(state):
            from time import perf_counter
            start=perf_counter(); r=state.get('result',{})
            if key=='economic': output={'gdp':scenario['gdp'],'inflation':scenario['inflation'],'interest_bps':scenario['interest'],'duration':scenario['duration'],'note':'Inflation is contextual, not independently applied to avoid double counting macro shocks.'}
            elif key=='twin': output=balance(twin)
            elif key=='credit':
                r=calculate(twin,scenario); output={k:r[k] for k in ['pd','lgd','ead','credit_loss']}
            elif key=='market': output={k:r[k] for k in ['market_loss','funding_cost']}
            elif key=='liquidity': output={k:r[k] for k in ['lcr','funding_gap','withdrawals','hqla','outflows']}
            elif key=='capital': output={k:r[k] for k in ['car','rwa','post_equity','resilience']}
            elif key=='simulation': output={'timeline':r['timeline'],'losses':r['losses']}
            elif key=='orchestrator': output={'findings':findings(r,scenario),'critical_count':sum(f['severity']=='critical' for f in findings(r,scenario))}
            elif key=='explainability': output={'evidence':[f['evidence'] for f in findings(r,scenario)],'method':'Deterministic calculation attribution; PD from synthetic-trained logistic regression. No SHAP or calibrated confidence claimed.'}
            else: output={'requires_review':True,'action':'Create advisory review requests; never execute financial actions automatically'}
            execution={'agent_id':key,'name':title,'status':'completed','input':{'twin':twin['name'],'scenario':scenario['name']},'output':output,'duration_ms':round((perf_counter()-start)*1000,3)}
            if on_execution: on_execution(execution)
            return {'result':r,'findings':findings(r,scenario) if r else [],'executions':state['executions']+[execution]}
        return node
    previous=START
    for key,title,_ in AGENTS:
        graph.add_node(key,make_node(key,title)); graph.add_edge(previous,key); previous=key
    graph.add_edge(previous,END)
    return graph.compile().invoke({'twin':twin,'scenario':scenario,'result':{},'findings':[],'executions':[]})
