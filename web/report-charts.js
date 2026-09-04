/* Code-native, zero-baseline reporting visuals. Color communicates variance, not magnitude. */
(function(root){
  const M=root.FinanceReport,esc=M.escape;
  const money=v=>M.finite(v)?(v/1e6).toLocaleString('en-US',{minimumFractionDigits:1,maximumFractionDigits:1}):'—';
  const percent=v=>M.finite(v)?`${v>0?'+':''}${(v*100).toFixed(1)}%`:'—';
  const tone=v=>v.favorable===null?'neutral':v.favorable?'favorable':'unfavorable';
  const signed=v=>M.finite(v)?`${v>0?'+':''}${money(v)}`:'—';
  function trend(rows,metricLabel,width=800,height=320){
    const left=42,right=15,top=26,bottom=height-130;
    const values=rows.flatMap(r=>[r.actual,r.prior]).filter(M.finite);
    if(!values.length)return '<div class="empty">No observations for this selection.</div>';
    const min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1;
    const y=value=>bottom-(value-min)/span*(bottom-top),zero=y(0),step=(width-left-right)/Math.max(rows.length,1),bar=Math.min(19,step*.27);
    const deltas=rows.map(r=>M.variance(r.actual,r.prior));
    const deltaMax=Math.max(...deltas.map(v=>Math.abs(v.delta||0)),1),deltaY=height-48;
    let svg=`<svg class="report-svg" viewBox="0 0 ${width} ${height}" role="group" aria-label="${esc(metricLabel)} actual versus prior year, EUR million"><line x1="${left}" x2="${width-right}" y1="${zero}" y2="${zero}" class="axis"/>`;
    for(const value of [...new Set([min,0,max])])svg+=`<text x="${left-7}" y="${y(value)+4}" text-anchor="end" class="axis-text">${money(value)}</text>`;
    rows.forEach((r,i)=>{
      const x=left+step*(i+.5),delta=deltas[i];
      svg+=`<g class="chart-point" tabindex="0" role="button" data-month="${esc(r.month)}" aria-label="${esc(r.month)} ${esc(metricLabel)} actual ${money(r.actual)}, prior year ${money(r.prior)} EUR million. Show detail."><title>${esc(r.month)} · AC ${money(r.actual)} · PY ${money(r.prior)} · Δ ${signed(delta.delta)} EUR m</title><rect x="${x-step/2}" y="0" width="${step}" height="${height}" fill="transparent"/>`;
      for(const [value,offset,style] of [[r.prior,-bar-1,'prior'],[r.actual,1,'actual']]){
        if(M.finite(value))svg+=`<rect x="${x+offset}" y="${Math.min(zero,y(value))}" width="${bar}" height="${Math.max(Math.abs(y(value)-zero),value===0?0:1)}" class="${style}"/>`;
      }
      if(i%2===0||i===rows.length-1)svg+=`<text x="${x}" y="${Math.max(14,y(Math.max(r.actual??0,r.prior??0))-6)}" text-anchor="middle">${money(r.actual)}</text>`;
      svg+=`<text x="${x}" y="${bottom+21}" text-anchor="middle" class="axis-text">${esc(r.month.slice(2))}</text>`;
      if(M.finite(delta.delta)){
        const dy=delta.delta/deltaMax*27;
        svg+=`<rect x="${x-bar/2}" y="${Math.min(deltaY,deltaY-dy)}" width="${bar}" height="${Math.abs(dy)}" class="${tone(delta)}"/><text x="${x}" y="${delta.delta>=0?deltaY-dy-5:deltaY-dy+13}" text-anchor="middle" class="${tone(delta)}">${signed(delta.delta)}</text>`;
      }else svg+=`<text x="${x}" y="${deltaY-14}" text-anchor="middle">—</text>`;
      svg+='</g>';
    });
    return svg+`<text x="${left}" y="${bottom+43}" class="axis-text">Δ YoY · EUR m</text><line x1="${left}" x2="${width-right}" y1="${deltaY}" y2="${deltaY}" class="axis"/></svg>`;
  }
  function varianceBar(value,max){
    const delta=value.delta,extent=M.finite(delta)?Math.abs(delta)/Math.max(max,1)*48:0;
    return `<span class="variance-track" aria-hidden="true"><i class="${tone(value)}" style="left:${delta<0?50-extent:50}%;width:${extent}%"></i></span>`;
  }
  let seriesId=0;
  function series(rows,key,labelKey='month',endMonth='',width=900){
    const count=rows.length,values=rows.map(r=>r[key]).filter(M.finite);
    if(!values.length)return '<div class="empty">No observations for this selection.</div>';
    const isFte=key==='ending_fte',format=isFte?v=>M.finite(v)?v.toFixed(0):'—':money;
    const unit=isFte?'FTE':'EUR million',min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1;
    const y=v=>265-(v-min)/span*235,zero=y(0),step=(width-70)/Math.max(count,1),id=`forecast-hatch-${++seriesId}`;
    const pattern=r=>key.endsWith('_budget')?'plan':String(r[labelKey])>endMonth&&endMonth?'forecast':'actual';
    const kinds=[...new Set(rows.map(pattern))];
    const ticks=new Set(Array.from({length:Math.min(6,count)},(_,i)=>Math.round(i*(count-1)/Math.max(1,Math.min(6,count)-1))));
    return `<div class="chart-legend">${kinds.map(k=>`<span class="${k}-key">${{actual:'AC · Actual',plan:'PL · Plan',forecast:'FC · Forecast'}[k]}</span>`).join('')}<span>${unit} · signed zero baseline</span></div><svg class="report-svg series-svg" viewBox="0 0 ${width} 310" role="img" aria-label="${esc(key.replaceAll('_',' '))} · ${unit}"><defs><pattern id="${id}" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M-1 1 1-1M0 5 5 0M4 6 6 4" stroke="#555" stroke-width="1"/></pattern></defs><line x1="45" x2="${width-15}" y1="${zero}" y2="${zero}" class="axis"/>${[...new Set([min,0,max])].map(v=>`<text x="40" y="${y(v)+4}" text-anchor="end" class="axis-text">${format(v)}</text>`).join('')}${rows.map((r,i)=>{
      const v=r[key],x=55+i*step,kind=pattern(r),label=esc(r[labelKey]),w=Math.min(32,step*.65);
      return `<g><title>${label}: ${format(v)} ${unit} · ${kind}</title>${M.finite(v)?`<rect x="${x}" y="${Math.min(zero,y(v))}" width="${w}" height="${Math.abs(y(v)-zero)}" fill="${kind==='plan'?'white':kind==='forecast'?`url(#${id})`:'#303337'}" stroke="#303337" stroke-width="1"/>`:''}${ticks.has(i)?`<text x="${x+w/2}" y="290" text-anchor="middle" class="axis-text">${label.length>5?label.slice(2):label}</text><text x="${x+w/2}" y="${v>=0?y(v)-7:y(v)+15}" text-anchor="middle">${format(v)}</text>`:''}</g>`;
    }).join('')}</svg>`;
  }
  function matrix(current,prior){
    const actual=M.statement(current),previous=M.statement(prior),max=Math.max(...actual.map((r,i)=>Math.abs(M.variance(r.value,previous[i]?.value).delta||0)),1);
    if(!actual.length)return '<div class="empty">No statement for this selection.</div>';
    return `<table class="statement-table"><thead><tr><th>EUR million</th><th>PY<br><small>Prior year</small></th><th>AC<br><small>Actual</small></th><th>Δ EUR m</th><th class="variance-col">Absolute variance · zero centered</th><th>Δ %</th></tr></thead><tbody>${actual.map((row,i)=>{
      const v=M.variance(row.value,previous[i]?.value,row.cost?-1:1);
      return `<tr class="${row.total?'subtotal':''}"><th>${row.label}</th><td class="py-number">${money(previous[i]?.value)}</td><td>${money(row.value)}</td><td class="${tone(v)}">${signed(v.delta)}</td><td class="variance-col">${varianceBar(v,max)}</td><td class="${tone(v)}">${percent(v.relative)}</td></tr>`;
    }).join('')}</tbody></table><p class="report-note">Costs are shown as positive expenses; lower is favorable. Δ = AC − PY; Δ % = Δ / |PY|. Zero or missing PY: percentage unavailable.</p>`;
  }
  function waterfall(row,narrow=false){
    const items=M.bridge(row);if(!items.length)return '<div class="empty">No statement.</div>';
    const finite=items.flatMap(r=>[r.start,r.end]).filter(M.finite),min=Math.min(0,...finite),max=Math.max(0,...finite),span=max-min||1;
    if(narrow){
      const x=v=>145+(v-min)/span*150;
      return `<svg class="report-svg" viewBox="0 0 360 360" role="img" aria-label="Revenue to EBIT bridge, EUR million"><line x1="${x(0)}" x2="${x(0)}" y1="15" y2="342" class="axis"/>${items.map((r,i)=>{const y=26+i*40;return `<g><title>${r.label}: ${money(r.value)} EUR m</title><text x="0" y="${y+12}" class="axis-text">${r.label}</text>${M.finite(r.start)&&M.finite(r.end)?`<rect x="${Math.min(x(r.start),x(r.end))}" y="${y}" width="${Math.abs(x(r.end)-x(r.start))}" height="20" class="${r.total?'actual':'expense'}"/>`:''}<text x="350" y="${y+13}" text-anchor="end">${money(r.value)}</text></g>`;}).join('')}</svg><p class="report-note">EUR m · Subtotals start at zero. Expense steps reduce the preceding balance.</p>`;
    }
    const y=v=>300-(v-min)/span*250,zero=y(0),step=105;
    return `<svg class="report-svg bridge-svg" viewBox="0 0 900 360" role="img" aria-label="Revenue to EBIT bridge, EUR million"><line x1="30" x2="895" y1="${zero}" y2="${zero}" class="axis"/>${items.map((r,i)=>{
      const x=42+i*step;
      if(!M.finite(r.end)||!M.finite(r.start))return '';
      return `<g><title>${r.label}: ${money(r.value)} EUR m</title><rect x="${x}" y="${Math.min(y(r.start),y(r.end))}" width="57" height="${Math.abs(y(r.end)-y(r.start))}" class="${r.total?'actual':'expense'}"/>${i<items.length-1?`<line x1="${x+57}" x2="${x+step}" y1="${y(r.end)}" y2="${y(r.end)}" class="connector"/>`:''}<text x="${x+28}" y="${Math.min(y(r.start),y(r.end))-8}" text-anchor="middle">${money(r.value)}</text><text x="${x+28}" y="325" text-anchor="middle" class="axis-text">${r.label.split(' ').slice(0,2).join(' ')}</text>${r.label.split(' ').length>2?`<text x="${x+28}" y="342" text-anchor="middle" class="axis-text">${r.label.split(' ').slice(2).join(' ')}</text>`:''}</g>`;
    }).join('')}</svg><p class="report-note">Subtotals restart from zero. Expense steps reduce the preceding subtotal; no balancing adjustments are introduced.</p>`;
  }
  root.ReportCharts={money,percent,tone,signed,trend,matrix,waterfall,varianceBar,series};
})(globalThis);
