/* Source-tied forecast error and liquidity visuals. Figures remain code-native. */
(function(root){
  const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
  const percentFormatter=new Intl.NumberFormat('en-GB',{style:'percent',minimumFractionDigits:1,maximumFractionDigits:1});
  const pct=value=>percentFormatter.format(Number(value));
  const money=value=>`€${(Number(value)/1e6).toFixed(1)}M`;
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const landmark=new Set([1,6,12,18]);

  function accuracy(source){
    const rows=(source||[]).filter(row=>finite(row.horizon_month)&&finite(row.mape)&&finite(row.bias)).sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month));
    if(!rows.length)return '<p class="forecast-visual-empty">No realized forecast vintages for this close.</p>';
    const x=horizon=>47+(Number(horizon)-Number(rows[0].horizon_month))/(Number(rows.at(-1).horizon_month)-Number(rows[0].horizon_month)||1)*520;
    const mapeY=value=>149-Math.max(0,Number(value))/.16*112;
    const biasY=value=>51-Number(value)/.07*43;
    const mapePath=rows.map((row,index)=>`${index?'L':'M'}${x(row.horizon_month).toFixed(1)} ${mapeY(row.mape).toFixed(1)}`).join(' ');
    const ticks=rows.filter(row=>landmark.has(Number(row.horizon_month)));
    const first=rows[0],last=rows.at(-1);
    return `<div class="forecast-accuracy-visual forecast-visual">
      <div class="fv-chart-heading"><strong>MAPE · error magnitude</strong><span>Lower is better · ${rows.length} realized horizons</span></div>
      <svg class="fv-error-chart" viewBox="0 0 620 180" role="img" aria-label="Mean absolute percentage error by forecast horizon. ${ticks.map(row=>`${row.horizon_month} months ${pct(row.mape)}`).join('; ')}">
        ${[0,.05,.10,.15].map(value=>`<g><line x1="47" x2="580" y1="${mapeY(value)}" y2="${mapeY(value)}" class="fv-grid"/><text x="39" y="${mapeY(value)+4}" text-anchor="end" class="fv-axis">${Math.round(value*100)}%</text></g>`).join('')}
        <path d="${mapePath}" class="fv-error-line"/>
        ${rows.map(row=>`<circle cx="${x(row.horizon_month)}" cy="${mapeY(row.mape)}" r="${landmark.has(Number(row.horizon_month))?4.5:2.5}" class="fv-error-point"><title>${row.horizon_month}M MAPE ${pct(row.mape)}; ${row.observations} observations</title></circle>`).join('')}
        ${ticks.map(row=>`<g><text x="${x(row.horizon_month)}" y="${Math.max(19,mapeY(row.mape)-10)}" text-anchor="middle" class="fv-value">${pct(row.mape)}</text><text x="${x(row.horizon_month)}" y="171" text-anchor="middle" class="fv-axis">${row.horizon_month}M</text></g>`).join('')}
      </svg>
      <div class="fv-chart-heading"><strong>Signed bias · forecast minus actual</strong><span>Zero-centered; negative means under-forecast</span></div>
      <svg class="fv-bias-chart" viewBox="0 0 620 118" role="img" aria-label="Signed forecast bias by horizon. ${ticks.map(row=>`${row.horizon_month} months ${pct(row.bias)}`).join('; ')}">
        <line x1="47" x2="580" y1="${biasY(0)}" y2="${biasY(0)}" class="fv-zero"/><text x="39" y="${biasY(0)+4}" text-anchor="end" class="fv-axis">0%</text>
        ${rows.map(row=>{const y=biasY(row.bias);return `<rect x="${x(row.horizon_month)-7}" y="${Math.min(y,biasY(0))}" width="14" height="${Math.max(2,Math.abs(y-biasY(0)))}" class="${Number(row.bias)<0?'fv-negative':'fv-positive'}"><title>${row.horizon_month}M bias ${pct(row.bias)}; ${row.observations} observations</title></rect>`;}).join('')}
        ${ticks.map(row=>`<g><text x="${x(row.horizon_month)}" y="${Number(row.bias)<0?Math.min(105,biasY(row.bias)+14):Math.max(14,biasY(row.bias)-8)}" text-anchor="middle" class="fv-value ${Number(row.bias)<0?'fv-negative-label':'fv-positive-label'}">${Number(row.bias)>0?'+':''}${pct(row.bias)}</text><text x="${x(row.horizon_month)}" y="116" text-anchor="middle" class="fv-axis">${row.horizon_month}M</text></g>`).join('')}
      </svg>
      <p class="fv-insight">Bias moves from ${Number(first.bias)>0?'+':''}${pct(first.bias)} at ${first.horizon_month}M to ${Number(last.bias)>0?'+':''}${pct(last.bias)} at ${last.horizon_month}M. MAPE and bias use the published realized vintages.</p>
    </div>`;
  }

  function liquidity(source){
    const rank={Base:0,Downside:1,Upside:2};
    const rows=(source||[]).filter(row=>finite(row.forecast_operating_cash_flow_12m)&&finite(row.forecast_capex_12m)&&finite(row.ending_cash_12m)).sort((a,b)=>(rank[a.scenario]??9)-(rank[b.scenario]??9));
    if(!rows.length)return '<p class="forecast-visual-empty">No liquidity scenarios for this close.</p>';
    const max=Math.max(...rows.map(row=>Number(row.forecast_operating_cash_flow_12m)),1);
    return `<div class="forecast-liquidity-visual forecast-visual"><div class="fv-liquidity-legend"><span>12M operating cash flow · EUR m</span><span>CAPEX is shown separately</span></div>
      <div class="fv-scenarios">${rows.map(row=>`<div class="fv-scenario" title="${escape(row.scenario)}: operating cash flow ${money(row.forecast_operating_cash_flow_12m)}, CAPEX ${money(row.forecast_capex_12m)}, ending cash ${money(row.ending_cash_12m)}"><strong>${escape(row.scenario)}</strong><div class="fv-scenario-main"><div class="fv-scenario-track"><i style="width:${Math.max(0,Math.min(100,Number(row.forecast_operating_cash_flow_12m)/max*100)).toFixed(1)}%"></i></div><b>${money(row.forecast_operating_cash_flow_12m)}</b></div><div class="fv-scenario-support"><span>CAPEX ${money(row.forecast_capex_12m)}</span><span>12M ending cash <b>${money(row.ending_cash_12m)}</b></span></div></div>`).join('')}</div>
      <p class="fv-insight">OCF precedes CAPEX. Ending cash also reflects other modeled cash and financing movements; these bars are not a cash reconciliation.</p>
    </div>`;
  }
  root.FinanceForecastVisual={accuracy,liquidity};
})(globalThis);
