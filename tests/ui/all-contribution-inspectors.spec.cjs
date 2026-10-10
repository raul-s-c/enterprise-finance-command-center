const {test,expect}=require('@playwright/test');

const pages=[
  ['pnl',5,'pnl'],['profitability',4,'products'],
  ['working-capital',0,'nwc'],['working-capital',1,'ar'],
  ['working-capital',2,'inventory'],['working-capital',3,'ap'],
  ['operations-capex',3,'capex'],['cash-flow',3,'cash']
];

test('all eight contribution explorers show complete details beside evidence on laptops',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  for(const [view,index,key] of pages){
    await page.goto(`/#view=${view}&page=${index}`);
    const explorer=page.locator(`.contribution-explorer[data-contribution="${key}"]`);
    await expect(explorer).toBeVisible();
    if(key==='nwc')await page.screenshot({path:testInfo.outputPath('nwc-inspector-1280x720.png')});
    const geometry=await explorer.evaluate(element=>{
      const inspector=element.querySelector('.cx-inspector'),details=inspector.querySelector('dl');
      const side=inspector.getBoundingClientRect(),evidence=element.querySelector('.cx-evidence').getBoundingClientRect();
      const flow=element.querySelector('.cx-flow-map');
      const flowNodes=[...flow.querySelectorAll('button')].map(node=>({label:node.textContent.trim(),height:node.clientHeight,content:node.scrollHeight,top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom}));
      const ranking=element.querySelector('.cx-ranking'),pager=ranking.querySelector('.contribution-pager');
      const contributors=[...ranking.querySelectorAll('.contribution-row')].map(row=>({label:row.textContent.trim(),bottom:row.getBoundingClientRect().bottom}));
      const tableWrap=element.querySelector('.cx-table-wrap'),evidenceRows=[...tableWrap.querySelectorAll('tbody tr')];
      return {details:details.clientHeight,content:details.scrollHeight,inspectorLeft:side.left,inspectorBottom:side.bottom,evidenceRight:evidence.right,evidenceBottom:evidence.bottom,rows:evidenceRows.length,lastEvidenceBottom:evidenceRows.at(-1)?.getBoundingClientRect().bottom||0,tableBottom:tableWrap.getBoundingClientRect().bottom,overflow:document.documentElement.scrollWidth-innerWidth,flowTop:flow.getBoundingClientRect().top,flowBottom:flow.getBoundingClientRect().bottom,flowNodes,pagerTop:pager.getBoundingClientRect().top,rankingBottom:ranking.getBoundingClientRect().bottom,contributors};
    });
    expect(geometry.content,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(geometry.details+1);
    expect(geometry.evidenceRight,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(geometry.inspectorLeft+1);
    expect(geometry.inspectorBottom,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeGreaterThanOrEqual(geometry.evidenceBottom-1);
    expect(geometry.rows,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeGreaterThan(0);
    expect(geometry.lastEvidenceBottom,`${view}/${key}: last advertised evidence row is clipped`).toBeLessThanOrEqual(geometry.tableBottom+1);
    expect(geometry.overflow,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(1);
    for(const row of geometry.contributors)expect(row.bottom,`${view}/${key}: ${row.label} overlaps the pager`).toBeLessThanOrEqual(geometry.pagerTop+1);
    expect(geometry.pagerTop,`${view}/${key}: ranking pager is clipped`).toBeLessThan(geometry.rankingBottom);
    if(!['pnl','nwc'].includes(key))for(const node of geometry.flowNodes){
      expect(node.content,`${view}/${key}: clipped ${node.label} (${JSON.stringify(geometry)})`).toBeLessThanOrEqual(node.height+1);
      expect(node.top,`${view}/${key}: ${node.label} is above the flow`).toBeGreaterThanOrEqual(geometry.flowTop-1);
      expect(node.bottom,`${view}/${key}: ${node.label} is below the flow`).toBeLessThanOrEqual(geometry.flowBottom+1);
    }
    if(['ar','capex'].includes(key)){
      const screenshot=testInfo.outputPath(`${key}-inspector-1280x720.png`);
      await page.screenshot({path:screenshot});
      await testInfo.attach(`${key}-inspector-1280x720`,{path:screenshot,contentType:'image/png'});
    }
  }
});

test('cash contribution drill path does not repeat the selected entity',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=3&section=Cash+contribution&entity=US01&division=all&metric=revenue');
  const explorer=page.locator('.contribution-explorer[data-contribution="cash"]');
  await expect(explorer).toBeVisible();
  await expect(explorer.locator('.cx-head p')).toHaveText('Entity: US01');
  const drillPath=await explorer.locator('.cx-inspector dl div').evaluateAll(nodes=>
    nodes.find(node=>node.querySelector('dt')?.textContent?.trim()==='Drill path')
      ?.querySelector('dd')?.textContent?.trim());
  expect(drillPath).toBe('US01');
  await expect(explorer.locator('.cx-flow')).toContainText('Value flow · US01');
});

test('cash contribution explains free cash flow by source category and retains its reconciliation',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=3&section=Cash+contribution&entity=US01&division=all&metric=revenue');
  const explorer=page.locator('.contribution-explorer[data-contribution="cash"]');
  await expect(explorer).toBeVisible();
  await expect(explorer.getByRole('button',{name:'Drill to Division'})).toBeVisible();
  await explorer.getByRole('button',{name:'Drill to Division'}).click();
  await expect(explorer.getByRole('heading',{name:'Contribution by division'})).toBeVisible();
  await explorer.getByRole('button',{name:'Cash flow category'}).click();
  await expect(explorer.getByRole('heading',{name:'Contribution by cash flow category'})).toBeVisible();
  await expect(explorer.locator('.cx-summary > div:first-child > strong')).toHaveText('€3,467,504.18');
  await expect(explorer.locator('.cx-ranking')).toContainText('Customer collections');
  await expect(explorer.locator('.cx-ranking')).toContainText('Supplier payments');
  await expect(explorer.getByRole('heading',{name:'Cash movement lineage · Customer collections'})).toBeVisible();
  await expect(explorer.locator('.cx-evidence thead')).toContainText('Source journal id');
  const screenshot=testInfo.outputPath('cash-flow-category-contribution-1280x720.png');
  await page.screenshot({path:screenshot});
  await testInfo.attach('cash-flow-category-contribution-1280x720',{path:screenshot,contentType:'image/png'});
});

test('single-category cash measures do not offer a redundant category breakdown',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=3&section=Cash+contribution&entity=US01&division=all&metric=revenue');
  const explorer=page.locator('.contribution-explorer[data-contribution="cash"]');
  await expect(explorer).toBeVisible();
  await explorer.locator('#cx-metric').selectOption('customer_collections');
  await expect(explorer.getByRole('button',{name:'Division',exact:true})).toBeVisible();
  await expect(explorer.getByRole('button',{name:'Cash flow category',exact:true})).toHaveCount(0);
  await explorer.locator('#cx-metric').selectOption('capex');
  await expect(explorer.getByRole('button',{name:'Division',exact:true})).toHaveCount(0);
  await expect(explorer.getByRole('button',{name:'Lowest published level'})).toBeDisabled();
  await expect(explorer.getByRole('heading',{name:'Underlying evidence · US01'})).toBeVisible();
  await expect(explorer.locator('.cx-evidence tbody tr')).toHaveCount(1);
});
