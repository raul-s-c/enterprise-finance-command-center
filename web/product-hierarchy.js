function hierarchyScope(rows){
  let scoped=rows||[];
  if(state.division!=='all')scoped=scoped.filter(r=>r.division===state.division);
  return scoped;
}

function renderProfitabilityHierarchy(){
  const prod=hierarchyScope(data.product_profitability||[]);
  const fam=hierarchyScope(data.product_family_profitability||[]);
  const tiers=hierarchyScope(data.quality_tier_profitability||[]);
  const catalog=hierarchyScope(data.product_catalog||[]);
  let cust=data.customer_profitability||[];
  if(state.entity!=='all')cust=cust.filter(r=>r.entity===state.entity);
  if(state.division!=='all')cust=cust.filter(r=>r.division===state.division);

  const skuCount=catalog.reduce((s,r)=>s+(Number(r.sku_count)||0),0);
  const activeCount=catalog.reduce((s,r)=>s+(Number(r.initially_active_skus)||0),0);
  const familyCount=new Set(catalog.map(r=>`${r.division}|${r.product_family}`)).size;
  const subfamilyCount=new Set(catalog.map(r=>`${r.division}|${r.product_family}|${r.product_subfamily}`)).size;
  const lossMakers=prod.filter(r=>(Number(r.operating_contribution)||0)<0).length;

  return `<div class="kpi-grid">
    ${kpi('Catalog SKUs',num(skuCount,0),`${activeCount} initially active`)}
    ${kpi('Product families',num(familyCount,0),`${subfamilyCount} subfamilies`)}
    ${kpi('Quality tiers','3','Essential / Professional / Premium')}
    ${kpi('Products sold',num(prod.length,0),'Trailing 12M scope')}
    ${kpi('Loss-making SKUs',num(lossMakers,0),'Trailing 12M')}
  </div>
  <div class="panel-grid">
    ${panel('Product family economics','Trailing 12 months',table(fam,[
      {key:'division',label:'Division'},
      {key:'product_family',label:'Family'},
      {key:'sku_count',label:'SKUs',num:true},
      {key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},
      {key:'gross_margin_pct',label:'GM',num:true,format:v=>pct(v)},
      {key:'mc_pct',label:'MC',num:true,format:v=>pct(v)},
      {key:'operating_contribution',label:'Operating contribution',num:true,format:v=>signed(v)}
    ]),'span-7')}
    ${panel('Quality-tier economics','Economics by commercial quality level',table(tiers,[
      {key:'division',label:'Division'},
      {key:'quality_tier',label:'Tier'},
      {key:'sku_count',label:'SKUs',num:true},
      {key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},
      {key:'gross_margin_pct',label:'GM',num:true,format:v=>pct(v)},
      {key:'mc_pct',label:'MC',num:true,format:v=>pct(v)}
    ]),'span-5')}
    ${panel('SKU profitability','Lowest operating contribution over trailing 12 months',table(prod.slice(0,60),[
      {key:'division',label:'Division'},
      {key:'product_family',label:'Family'},
      {key:'product_subfamily',label:'Subfamily'},
      {key:'product_type',label:'Type'},
      {key:'quality_tier',label:'Quality'},
      {key:'generation',label:'Generation'},
      {key:'name',label:'Product'},
      {key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},
      {key:'gross_margin_pct',label:'GM',num:true,format:v=>pct(v)},
      {key:'operating_contribution',label:'Operating contribution',num:true,format:v=>signed(v)}
    ]),'span-12')}
    ${panel('Catalog structure','Available assortment by family, subfamily and quality tier',table(catalog,[
      {key:'division',label:'Division'},
      {key:'product_family',label:'Family'},
      {key:'product_subfamily',label:'Subfamily'},
      {key:'quality_tier',label:'Quality'},
      {key:'sku_count',label:'SKUs',num:true},
      {key:'initially_active_skus',label:'Initially active',num:true}
    ]),'span-6')}
    ${panel('Customer profitability','Lowest operating contribution over trailing 12 months',table(cust,[
      {key:'entity',label:'Entity'},
      {key:'customer_name',label:'Customer'},
      {key:'division',label:'Division'},
      {key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},
      {key:'gross_margin_pct',label:'GM',num:true,format:v=>pct(v)},
      {key:'operating_contribution',label:'Operating contribution',num:true,format:v=>signed(v)}
    ]),'span-6')}
  </div>`;
}

renderers.profitability=renderProfitabilityHierarchy;
