export async function api(path:string,method='GET',body?:unknown){
 const res=await fetch('/api/'+path,{method,headers:{'Content-Type':'application/json',...(sessionStorage.getItem('token')?{Authorization:'Bearer '+sessionStorage.getItem('token')}:{})},...(body?{body:JSON.stringify(body)}:{})});
 if(!res.ok){const data=await res.json().catch(()=>({detail:res.statusText}));if(res.status===401)sessionStorage.removeItem('token');throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));}return res.json();
}
export async function download(id:string,format:string){const res=await fetch(`/api/reports/${id}/download?format=${format}`,{headers:{Authorization:'Bearer '+sessionStorage.getItem('token')}});if(!res.ok)throw new Error('Download failed');const blob=await res.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`finstress-${id}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
