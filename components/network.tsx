'use client';
import {useState} from 'react';
import {ReactFlow,Background,Controls,MarkerType, type Node} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
export default function Network({assets=50000}:{assets?:number}){
 const [step,setStep]=useState(0);const [selected,setSelected]=useState('Institution');
 const names=['Central bank','Bond markets','Depositors','Institution','Corporate borrowers','Retail borrowers','Commercial banks','Equity markets','Counterparties'];
 const nodes:Node[]=names.map((name,i)=>({id:String(i),position:{x:i===3?340:(i%3)*340,y:Math.floor(i/3)*170},data:{label:<div><small>{i===3?'DIGITAL TWIN':'SYNTHETIC ENTITY'}</small><strong>{name}</strong><span>{i===3?'₹'+assets.toLocaleString()+' Cr':`Exposure weight ${[8,14,70,100,36,24,12,4,8][i]}%`}</span></div>},style:{background:i===3?'#282044':step>0&&i>=3&&i<=3+step?'#432133':'#121e32',color:'#eee',border:'1px solid '+(step>0&&i>=3&&i<=3+step?'#f43f5e':'#384563'),borderRadius:12,width:215,padding:12}}));
 const pairs=[[0,3],[1,3],[2,3],[3,4],[3,5],[3,6],[7,3],[6,8],[4,8]];
 const edges=pairs.map(([a,b],i)=>({id:String(i),source:String(a),target:String(b),animated:step>0,markerEnd:{type:MarkerType.ArrowClosed},label:i<3?'Funding':'Exposure',style:{stroke:step>0&&a>=3?'#f43f5e':'#6773ad'},labelStyle:{fill:'#94a3b8'}}));
 return <><div className="panel-head"><div><h3>Financial system connections</h3><p>Synthetic exposure network · Illustrative propagation, not an estimated systemic loss</p></div><button onClick={()=>setStep(s=>(s+1)%5)}>{step===4?'Reset shock':`Propagate shock · ${step}/4`}</button></div><div style={{height:580}}><ReactFlow nodes={nodes} edges={edges} fitView onNodeClick={(_,n)=>setSelected(names[Number(n.id)])}><Background color="#29344b" gap={24}/><Controls/></ReactFlow></div><p className="notice">Selected: {selected}. {step>0?`Step ${step}: risk travels from institution to borrowers and counterparties along displayed exposure edges.`:'Click a node to inspect its position. Advance the shock to inspect each connected layer.'}</p></>;
}
