/* Premium finance application shell: useful global commands, never fake chrome. */
(function(root){
  const escapeCsv=value=>`"${String(value??'').replaceAll('"','""')}"`;
  function exportView(){
    const rows=[...document.querySelectorAll('#content table tr')].map(row=>[...row.children].map(cell=>cell.textContent.trim()));
    if(!rows.length){root.print();return;}
    const csv=rows.map(row=>row.map(escapeCsv).join(',')).join('\r\n');
    const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),link=document.createElement('a');
    link.href=URL.createObjectURL(blob);link.download=`aureon-${state.view}-${data?.meta?.end_month||'report'}.csv`;link.click();URL.revokeObjectURL(link.href);
  }
  function openHelp(){const button=document.getElementById('reportHelp');if(button&&!button.hidden){button.click();return;}reportDialog('Aureon Finance help','<div class="help-pages"><p>Use the left navigation to change the reporting domain. Every financial view preserves the published close, shows only supported scope controls and provides source evidence where available.</p><p>Use contribution analysis to move from a consolidated total to entity, division, component and underlying records without allocating missing dimensions.</p></div>');}
  function search(event){
    const query=event.target.value.trim().toLowerCase();
    document.querySelectorAll('#nav button').forEach(button=>{button.hidden=Boolean(query)&&!button.textContent.toLowerCase().includes(query);});
    document.querySelectorAll('#nav .nav-group').forEach(group=>{group.hidden=Boolean(query)&&![...group.querySelectorAll('button')].some(button=>!button.hidden);});
    if(event.key==='Enter')document.querySelector('#nav button:not([hidden])')?.click();
  }
  root.mountPremiumShell=function(){
    const period=document.getElementById('globalPeriod'),control=document.getElementById('globalControl');
    if(data?.meta?.end_month)period.textContent=data.meta.end_month;
    if(data?.validation){control.innerHTML=`<i></i> Controls ${data.validation.passed?'passed':'failed'}`;control.classList.toggle('failed',!data.validation.passed);}
    const searchBox=document.getElementById('globalSearch');if(searchBox&&!searchBox.dataset.bound){searchBox.dataset.bound='1';searchBox.addEventListener('input',search);searchBox.addEventListener('keydown',search);}
    document.getElementById('globalExport').onclick=exportView;document.getElementById('globalHelp').onclick=openHelp;
  };
})(globalThis);
