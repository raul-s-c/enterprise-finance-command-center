const {test,expect}=require('@playwright/test');

test('global search navigates reports and financial scope with keyboard and mouse',async({page})=>{
  let releaseDashboard,signalDashboardRequest;
  const dashboardRequest=new Promise(resolve=>{signalDashboardRequest=resolve;});
  const dashboardGate=new Promise(resolve=>{releaseDashboard=resolve;});
  await page.route('**/data/dashboard.json*',async route=>{
    signalDashboardRequest();
    await dashboardGate;
    await route.continue();
  });
  await page.setViewportSize({width:1366,height:900});
  await page.goto('/#view=executive');
  const search=page.getByRole('combobox',{name:'Search reports, entities and divisions'});
  const results=page.getByRole('listbox',{name:'Finance search results'});
  await dashboardRequest;
  await search.fill('US01');
  releaseDashboard();
  await expect(results).toBeVisible();
  await expect(results.getByRole('option',{name:/US01/})).toBeVisible();
  await search.press('ArrowDown');
  await expect(search).toHaveAttribute('aria-activedescendant','global-search-option-0');
  await search.press('Enter');
  await expect(page.locator('#viewTitle')).toHaveText('P&L');
  await expect(page.locator('#entityFilter')).toHaveValue('US01');
  await expect(page.locator('#viewTitle')).toBeFocused();
  await page.getByRole('button',{name:'Back',exact:true}).click();
  await expect(page.locator('#viewTitle')).toHaveText('Executive');
  await expect(page.locator('#entityFilter')).toHaveValue('all');

  await search.fill('cash flow');
  await search.press('ArrowDown');
  await search.press('Enter');
  await expect(page.locator('#viewTitle')).toHaveText('Cash Flow');
  await search.fill('no matching finance item');
  await expect(results).toContainText('No reports, entities or divisions match this search.');
  await expect(page.locator('#nav button').first()).toBeVisible();
  await search.press('Escape');
  await expect(results).toBeHidden();
  await expect(search).toHaveAttribute('aria-expanded','false');

  await page.setViewportSize({width:390,height:844});
  const globalHelp=page.locator('#globalHelp');
  await expect(globalHelp).toHaveAccessibleName('Help');
  await expect(globalHelp).toBeVisible();
  await search.fill('Hardware');
  const bounds=await results.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x+bounds.width).toBeLessThanOrEqual(391);
  await results.getByRole('option',{name:/Hardware/}).first().click();
  await expect(page.locator('#divisionFilter')).toHaveValue('Hardware');
  await expect(page.locator('#viewTitle')).toHaveText('P&L');
});

test('P&L retains a readable canvas in short windows and signed endpoints',async({page})=>{
  // Test-only financial scenario: a cost reduction must exist regardless of the
  // current generated close. Never modify repository or production data.
  await page.route('**/data/dashboard.json*',async route=>{
    const response=await route.fetch(),fixture=await response.json();
    const current=fixture.meta.end_month,prior=`${Number(current.slice(0,4))-1}${current.slice(4)}`;
    for(const row of fixture.management_detail){
      if(row.entity==='US01'&&row.division==='Hardware'&&[current,prior].includes(row.month)){
        row.opex=row.month===current?100:200;
        row.ebit=row.gross_profit-row.opex-row.depreciation;
        row.net_income=row.ebit-10;
      }
    }
    await route.fulfill({response,json:fixture});
  });
  await page.setViewportSize({width:870,height:422});
  await page.goto('/#view=pnl&entity=US01&division=Hardware');
  const canvas=page.locator('.pnl-scroll');await expect(canvas).toBeVisible();
  expect((await canvas.boundingBox()).height).toBeGreaterThanOrEqual(420);
  await expect(page.locator('[data-pnl-key="revenue"]')).toBeVisible();
  const endpoints=await page.locator('.pnl-percent.negative i').evaluateAll(nodes=>nodes.map(n=>getComputedStyle(n,'::after').left));
  expect(endpoints.length).toBeGreaterThan(0);expect(endpoints.every(x=>x==='0px')).toBe(true);
});

test('graphical P&L restores filters with Back and factory content stays inside cards',async({page})=>{
  await page.setViewportSize({width:1366,height:900});
  await page.goto('/#view=pnl');
  await expect(page.locator('[data-pnl-key]')).toHaveCount(10);
  await page.locator('#entityFilter').selectOption('US01');
  await page.getByRole('button',{name:'Margin Engine',exact:true}).click();
  await page.getByRole('button',{name:'Back',exact:true}).click();
  await expect(page.locator('#viewTitle')).toHaveText('P&L');
  await expect(page.locator('#entityFilter')).toHaveValue('US01');
  await page.locator('[data-pnl-key="opex"]').click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await expect(page.locator('#reportDialogBody')).toContainText('Sum of OPEX');
  await expect(page.locator('#reportDialogBody')).toContainText('Contribution by entity and division');
  const downloadEvent=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export evidence CSV',exact:true}).click();
  const download=await downloadEvent;
  expect(download.suggestedFilename()).toMatch(/^aureon-pnl-opex-.*-evidence\.csv$/);
  const stream=await download.createReadStream(),chunks=[];
  for await(const chunk of stream)chunks.push(chunk);
  const exported=Buffer.concat(chunks).toString('utf8');
  expect(exported).toContain('actual_eur');expect(exported).toContain('"US01"');expect(exported).not.toContain('"DE01"');
  await page.locator('[data-pnl-entity="US01"][data-pnl-division="Hardware"]').click();
  await expect(page.locator('#reportDialog')).not.toBeVisible();
  await expect(page.locator('#divisionFilter')).toHaveValue('Hardware');
  await page.getByRole('button',{name:'Back',exact:true}).click();
  await expect(page.locator('#divisionFilter')).toHaveValue('all');
  for(const width of [1784,1392,1024,390]){
    await page.setViewportSize({width,height:991});
    await page.goto('/#view=operations-capex');
    await expect(page.locator('.sw-factories')).toBeVisible();
    const overflow=await page.locator('.sw-factories>button').evaluateAll(cards=>cards.some(card=>card.scrollWidth>card.clientWidth+1));
    expect(overflow).toBe(false);
  }
});

test('P&L contribution explains actual vs prior year and shows truthful statement lineage',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  await page.goto('/#view=pnl&page=5&section=P%26L+contribution');
  await expect(page.locator('.cx-summary')).toBeVisible();
  await expect(page.locator('.cx-formula')).toContainText('Actual · 2026-08');
  await expect(page.locator('.cx-formula')).toContainText('Prior year · 2025-08');
  await expect(page.locator('.cx-formula')).toContainText('Δ vs PY');
  const expected=await page.evaluate(async()=>{
    const data=await(await fetch('/data/dashboard.json')).json(),sum=month=>data.management_detail.filter(row=>row.month===month).reduce((total,row)=>total+row.revenue,0),actual=sum(data.meta.end_month),prior=sum(`${Number(data.meta.end_month.slice(0,4))-1}${data.meta.end_month.slice(4)}`),format=value=>new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value);
    return [format(actual),format(prior),format(actual-prior)];
  });
  const formula=page.locator('.cx-formula>div');
  for(let index=0;index<expected.length;index++)await expect(formula.nth(index)).toContainText(expected[index]);
  const flow=page.locator('.cx-flow');
  await expect(flow).toBeVisible();
  for(const selector of ['.cx-ranking','.cx-inspector','.cx-evidence'])await expect(page.locator(selector)).toBeVisible();
  await expect(page.locator('.cx-analysis-nav')).toBeHidden();
  await expect(flow.locator('h3')).toContainText('P&L lineage');
  await expect(flow).toContainText('Published source');
  await expect(flow).toContainText('P&L line');
  await expect(flow).toContainText('Close period');
  await expect(flow).not.toContainText('Destination');
  await page.locator('[data-dimension="division"]').click();
  await expect(flow.locator('h3')).toContainText('P&L lineage');
  await expect(flow.locator('.pnl-flow button').nth(1).locator('span')).toHaveText('Division');
  const bounds=await page.locator('body').evaluate(element=>({scrollWidth:element.scrollWidth,clientWidth:element.clientWidth}));
  expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.clientWidth+1);
});

test('Executive keeps every overview region reachable on tablet and mobile',async({page})=>{
  for(const viewport of [{width:1100,height:820},{width:900,height:820},{width:390,height:844}]){
    await page.setViewportSize(viewport);
    await page.goto('/#view=executive');
    if(viewport.width<=600){
      const filterBounds=await page.locator('.filters').evaluate(element=>{const rect=element.getBoundingClientRect();return{x:rect.x,right:rect.right,width:rect.width,viewport:innerWidth}});
      expect(filterBounds.x,`filters start outside the viewport: ${JSON.stringify(filterBounds)}`).toBeGreaterThanOrEqual(0);
      expect(filterBounds.right,`filters end outside the viewport: ${JSON.stringify(filterBounds)}`).toBeLessThanOrEqual(filterBounds.viewport+1);
      for(const filter of ['#entityFilter','#divisionFilter'])expect(await page.locator(filter).evaluate(element=>{const rect=element.getBoundingClientRect();return rect.left>=0&&rect.right<=innerWidth}),`${filter} is clipped at ${viewport.width}px`).toBe(true);
    }
    if(viewport.width<=600){
      const cards=await page.locator('.story-kpis').evaluate(element=>({display:getComputedStyle(element).display,scrollWidth:element.scrollWidth,clientWidth:element.clientWidth,viewport:innerWidth,items:[...element.children].filter(item=>getComputedStyle(item).display!=='none').map(item=>{const rect=item.getBoundingClientRect();return{left:rect.left,right:rect.right}})}));
      expect(cards.display).toBe('grid');
      expect(cards.scrollWidth).toBeLessThanOrEqual(cards.clientWidth+1);
      expect(cards.items).toHaveLength(5);
      expect(cards.items.every(item=>item.left>=0&&item.right<=cards.viewport+1)).toBe(true);
    }
    const switcher=page.getByRole('navigation',{name:'Executive overview regions'});
    await expect(switcher).toBeVisible();
    for(const [label,index] of [['Performance trend',0],['EBIT contribution',1],['Cash drivers',2],['Company story',3]]){
      const control=switcher.getByRole('button',{name:label,exact:true});
      await control.click();
      await expect(control).toHaveAttribute('aria-pressed','true');
      const region=page.locator(`#executive-region-${index}`);
      await expect(region).toBeVisible();
      expect(await region.evaluate(element=>element.scrollWidth<=element.clientWidth+1),`${label} overflows at ${viewport.width}px`).toBe(true);
    }
  }
});

test('all report destinations retain evidence instead of standalone KPI pages',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const reports=['executive','pnl','margin','working-capital','cash-flow','treasury','balance-sheet','forecast','macro-sensitivities','business-drivers','profitability','intercompany','operations-capex','fx','performance-review','action-execution','data-journey','close-journey'];
  for(const viewport of [{width:1366,height:768},{width:1024,height:768},{width:390,height:844}]){
  await page.setViewportSize(viewport);
  for(const report of reports){
    await page.goto(`/#view=${report}`);
    await expect(page.locator('#content')).not.toBeEmpty();
    if(report==='close-journey'){
      await expect(page.getByRole('heading',{name:'From business activity to management action'})).toBeVisible();
      continue;
    }
    if(viewport.width<=600){
      const bounds=await page.locator('.filters').evaluate(element=>{if(getComputedStyle(element).display==='none')return null;const rect=element.getBoundingClientRect();return{x:rect.x,right:rect.right,viewport:innerWidth}});
      if(bounds){expect(bounds.x,`${report} filters start outside mobile viewport: ${JSON.stringify(bounds)}`).toBeGreaterThanOrEqual(0);expect(bounds.right,`${report} filters end outside mobile viewport: ${JSON.stringify(bounds)}`).toBeLessThanOrEqual(bounds.viewport+1);}
    }
    await expect(page.locator('#reportPageSelect option').first()).toBeAttached();
    const count=await page.locator('#reportPageSelect option').count();
    for(let index=0;index<count;index++){
      if(index){
        await page.locator('#reportNext').click();
        await expect(page.locator('#reportPageSelect')).toHaveValue(String(index));
      }
      const evidence=await page.locator('#content').evaluate(content=>({
        cards:content.querySelectorAll('.kpi,.report-kpi,.sw-kpi,.story-kpi').length,
        supporting:content.querySelectorAll('.panel,.financial-report,.sw-panel,.cx-workspace,.story-region,.tower-analytics,.carrying-value-chart').length,
        text:content.innerText.trim().length,
        horizontalOverflow:document.documentElement.scrollWidth>innerWidth+1
      }));
      expect(evidence.text,`${report} page ${index} is blank`).toBeGreaterThan(0);
      expect(evidence.horizontalOverflow,`${report} page ${index} overflows the document`).toBe(false);
      if(evidence.cards)expect(evidence.supporting,`${report} page ${index} contains only KPIs`).toBeGreaterThan(0);
    }
  }
  }
  expect(errors).toEqual([]);
});

test('close journey stays readable and navigable at laptop, tablet and mobile widths',async({page},testInfo)=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  for(const viewport of [{width:1366,height:768},{width:1024,height:768},{width:390,height:844}]){
    await page.setViewportSize(viewport);
    await page.goto('/#view=close-journey');
    await expect(page.getByRole('heading',{name:'From business activity to management action'})).toBeVisible();
    await expect(page.locator('[data-cj-step]')).toHaveCount(8);
    const sizes=await page.evaluate(()=>Object.fromEntries([
      ['stage', '.cj-steps strong'],['status','.cj-steps span'],['outcome','.cj-steps small'],
      ['explanation','.cj-workspace p'],['inputs','.cj-io ul'],['controls','.cj-controls table'],
      ['proof','.cj-proof-chain strong'],['evidence','.cj-evidence-row small'],['guide','.cj-guide']
    ].map(([key,selector])=>[key,parseFloat(getComputedStyle(document.querySelector(selector)).fontSize)])));
    expect(sizes.stage,`${viewport.width}px stage label: ${JSON.stringify(sizes)}`).toBeGreaterThanOrEqual(viewport.width<=600?11:12);
    expect(sizes.explanation,`${viewport.width}px explanation: ${JSON.stringify(sizes)}`).toBeGreaterThanOrEqual(viewport.width<=600?12:11);
    expect(sizes.controls,`${viewport.width}px control table: ${JSON.stringify(sizes)}`).toBeGreaterThanOrEqual(10);
    expect(sizes.proof,`${viewport.width}px proof chain: ${JSON.stringify(sizes)}`).toBeGreaterThanOrEqual(11);
    expect(sizes.evidence,`${viewport.width}px evidence link: ${JSON.stringify(sizes)}`).toBeGreaterThanOrEqual(viewport.width<=600?11:10);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`document overflows at ${viewport.width}px`).toBe(true);
    if(viewport.width>900){
      const canvas=await page.locator('#content').evaluate(element=>({scrollHeight:element.scrollHeight,clientHeight:element.clientHeight}));
      expect(canvas.scrollHeight,`close journey requires vertical page scrolling at ${viewport.width}px: ${JSON.stringify(canvas)}`).toBeLessThanOrEqual(canvas.clientHeight+1);
    }
    if(viewport.width>600){
      expect(await page.evaluate(()=>parseFloat(getComputedStyle(document.querySelector('.cj-matrix table')).fontSize))).toBeGreaterThanOrEqual(10);
    }
    if(viewport.width===1366||viewport.width===390){
      const screenshot=testInfo.outputPath(`close-journey-${viewport.width}x${viewport.height}.png`);
      await page.screenshot({path:screenshot});
      await testInfo.attach(`close-journey-${viewport.width}x${viewport.height}`,{path:screenshot,contentType:'image/png'});
    }
    await page.locator('[data-cj-step="1"]').click();
    await expect(page.locator('#cj-next')).toBeEnabled();
    await expect(page.locator('.cj-guide')).toContainText('2 of 8 · Transactions');
  }
  expect(errors).toEqual([]);
});

test('statement analysis survives live resize without an overlapping inspector',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=margin');
  await page.getByRole('button',{name:'Bridge & composition',exact:true}).click();
  for(const [width,height] of [[1280,720],[1024,768],[1366,768],[1784,991],[390,844]]){
    await page.setViewportSize({width,height});
    // The application debounces resize before rebuilding its report DOM.
    await page.waitForTimeout(250);
    await expect(page.locator('.sw-secondary')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    if(width<=1500){
      await expect(page.getByRole('button',{name:'Bridge & composition',exact:true})).toHaveAttribute('aria-pressed','true');
      await expect(page.locator('.sw-grid>.sw-inspector')).toBeHidden();
    }
    if(width>600){
      const bounds=await page.locator('.sw-secondary').evaluate(panel=>{
        const outer=panel.getBoundingClientRect(),chart=panel.querySelector('svg').getBoundingClientRect();
        return {top:chart.top>=outer.top,bottom:chart.bottom<=outer.bottom+1};
      });
      expect(bounds.top).toBe(true);expect(bounds.bottom).toBe(true);
    }
    const valueSizes=await page.locator('.sw-secondary svg text:not(.axis-text)').evaluateAll(labels=>labels.map(label=>{
      const matrix=label.getScreenCTM();
      return parseFloat(getComputedStyle(label).fontSize)*Math.hypot(matrix.a,matrix.b);
    }));
    expect(Math.min(...valueSizes),`Unreadable chart values at ${width}x${height}`).toBeGreaterThanOrEqual(10);
    const screenshot=testInfo.outputPath(`margin-${width}x${height}.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`margin-${width}x${height}`,{path:screenshot,contentType:'image/png'});
  }
  await page.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await expect(page.locator('#reportDialogBody')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
  await expect(page.locator('#reportDialog')).toBeHidden();
});
