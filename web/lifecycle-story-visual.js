/* Controlled action lifecycle and due-date storytelling from published snapshots. */
(function(root){
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const baseStatuses=['Open','In Progress','Closed','Cancelled'];
  const month=value=>new Intl.DateTimeFormat('en-GB',{month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(`${value}-01T00:00:00Z`));

  function status(actions,trend,sourceTable){
    const rows=actions||[],history=trend||[],statuses=[...baseStatuses,...new Set(rows.map(row=>row.status||'Unspecified').filter(item=>!baseStatuses.includes(item)))];
    const counts=statuses.map(item=>rows.filter(row=>(row.status||'Unspecified')===item).length),total=rows.length;
    const composition=statuses.map((item,index)=>({item,count:counts[index]})).filter(item=>item.count>0);
    const sections=composition.map(({item,count})=>`<span class="plv-segment plv-${esc(item.toLowerCase().replace(/[^a-z]+/g,'-'))}" style="width:${total?count/total*100:0}%" title="${esc(item)}: ${count} of ${total}"><b>${count}</b><small>${esc(item)}</small></span>`).join('');
    const historyDisplay=history.length<=1?`<div class="plv-first-snapshot"><div><span>${history.length?month(history[0].month):'No snapshot'}</span><strong>${history.length?history[0].active+history[0].closed:0}</strong><small>${history.length?`${history[0].active} active · ${history[0].closed} closed`:'No controlled history yet'}</small></div><p>${history.length?'First controlled snapshot; a trend requires a second close.':'The lifecycle trend will appear after the first controlled close.'}</p></div>`:
      `<div class="plv-history-bars" role="img" aria-label="Monthly action lifecycle: ${history.map(row=>`${row.month}, ${row.active} active and ${row.closed} closed`).join('; ')}">${history.slice(-12).map(row=>{const max=Math.max(1,...history.map(item=>item.active+item.closed));return `<div title="${esc(row.month)}: ${row.active} active, ${row.closed} closed"><div class="plv-history-stack"><i class="plv-history-closed" style="height:${row.closed/max*100}%"></i><i class="plv-history-active" style="height:${row.active/max*100}%"></i></div><small>${esc(row.month.slice(5))}</small></div>`;}).join('')}</div>`;
    return `<div class="performance-lifecycle-visual plv-status"><div class="plv-heading"><strong>Action lifecycle at the close</strong><span>${total} management actions</span></div>
      <div class="plv-composition" role="img" aria-label="Status composition: ${composition.map(({item,count})=>`${count} ${item}`).join(', ')}">${sections||'<span class="plv-no-data">No actions in this scope</span>'}</div>
      <div class="plv-counts">${statuses.map((item,index)=>`<div><i class="plv-dot plv-${esc(item.toLowerCase().replace(/[^a-z]+/g,'-'))}"></i><span>${esc(item)}</span><strong>${counts[index]}</strong></div>`).join('')}</div>
      <div class="plv-history"><div class="plv-heading"><strong>Monthly lifecycle history</strong><span>${history.length} controlled ${history.length===1?'snapshot':'snapshots'}</span></div>${historyDisplay}</div>
      <details class="plv-records"><summary>View monthly lifecycle records</summary>${sourceTable}</details></div>`;
  }

  function due(actions,overdue,closeMonth,sourceTable){
    const late=overdue||[],active=(actions||[]).filter(row=>['Open','In Progress'].includes(row.status));
    const upcoming=active.filter(row=>!late.some(item=>item.action_id===row.action_id)).sort((a,b)=>String(a.due_month).localeCompare(String(b.due_month))||String(a.priority).localeCompare(String(b.priority))).slice(0,3);
    const summary=late.length?`<div class="plv-overdue-warning"><strong>${late.length} overdue ${late.length===1?'action':'actions'}</strong><span>Escalation is based on overdue age and published ownership.</span></div>`:`<div class="plv-overdue-clear"><span aria-hidden="true">✓</span><strong>No overdue actions at the ${esc(closeMonth)} close</strong></div>`;
    const preview=late.length?late.slice(0,3):upcoming;
    return `<div class="performance-lifecycle-visual plv-due">${summary}<div class="plv-heading"><strong>${late.length?'Overdue priorities':'Next due actions'}</strong><span>${late.length?'Overdue · source controlled':'Open · not yet overdue'}</span></div>
      <div class="plv-due-list">${preview.map(row=>`<details class="plv-due-row"><summary><b>${esc(row.priority)}</b><span><strong>${esc(row.trigger_metric)}</strong><small>${esc(row.owner_role)}</small></span><em>${esc(row.due_month)}</em></summary><div><p>${esc(row.action)}</p><small>Review ${esc(row.review_id)} · source ${esc(row.source_dataset)}</small></div></details>`).join('')||'<p class="plv-no-data">No open actions in this scope.</p>'}</div>
      <div class="plv-links"><button type="button" data-plv-register>View complete action register →</button><details class="plv-records"><summary>View ${late.length} overdue source records</summary>${sourceTable}</details></div></div>`;
  }

  if(root.document)document.addEventListener('click',event=>{
    if(!event.target.closest('[data-plv-register]'))return;
    const index=typeof reportState==='undefined'?-1:reportState.pages.findIndex(page=>page.title.includes('Persistent action register'));
    if(index>=0&&typeof reportNavigate==='function')reportNavigate(index);
  });
  root.FinanceLifecycleVisual={status,due};
})(globalThis);
