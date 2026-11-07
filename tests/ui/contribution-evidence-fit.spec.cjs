const {test,expect}=require('@playwright/test');

test('every contribution page exposes its paged evidence on a laptop canvas',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  const routes=[['pnl',5,2],['profitability',4,2],['working-capital',0,2],['working-capital',1,2],['working-capital',2,2],['working-capital',3,2],['operations-capex',3,1],['cash-flow',3,2]];
  for(const [view,index,count] of routes){
    await page.goto(`/#view=${view}&page=${index}`);
    const panel=page.locator('.cx-evidence');
    await expect(panel).toBeVisible();
    await expect(panel.locator('tbody tr')).toHaveCount(count);
    const fit=await panel.evaluate(node=>{
      const wrap=node.querySelector('.cx-table-wrap'),rows=[...node.querySelectorAll('tbody tr')],footer=document.querySelector('.report-footer');
      return {last:rows.at(-1).getBoundingClientRect().bottom,wrap:wrap.getBoundingClientRect().bottom,panel:node.getBoundingClientRect().bottom,footer:footer.getBoundingClientRect().top};
    });
    expect(fit.last,view).toBeLessThanOrEqual(fit.wrap+1);
    expect(fit.wrap,view).toBeLessThanOrEqual(fit.panel+1);
    expect(fit.panel,view).toBeLessThanOrEqual(fit.footer);
  }
});

test('compact NWC flow retains all three signed components and record actions',async({page})=>{
  for(const viewport of [{width:1280,height:720},{width:1366,height:768}]){
    await page.setViewportSize(viewport);
    await page.goto('/#view=working-capital&page=0');
    const flow=page.locator('.cx-flow-map.nwc-flow-compact');
    await expect(flow).toBeVisible();
    await expect(flow.locator('button')).toHaveCount(4);
    for(const name of ['Receivables','Inventory','Payables'])await expect(flow).toContainText(name);
    await expect(flow.getByRole('button',{name:/Payables/})).toContainText('−€');
    await expect(page.locator('.cx-flow')).toContainText('Signed components sum to NWC');
    const fit=await flow.evaluate(node=>({buttons:[...node.querySelectorAll('button')].every(button=>button.scrollHeight<=button.clientHeight+1&&button.scrollWidth<=button.clientWidth+1),flowOverflow:node.closest('.cx-flow').scrollHeight-node.closest('.cx-flow').clientHeight}));
    expect(fit.buttons).toBe(true);
    expect(fit.flowOverflow).toBeLessThanOrEqual(1);
    await flow.getByRole('button',{name:/Receivables/}).click();
    await expect(page.locator('#reportDialog')).toContainText('Published source record');
    await page.locator('#reportDialogClose').click();
  }
});

test('tablet focus keeps paged NWC and product evidence reachable',async({page})=>{
  await page.setViewportSize({width:1024,height:720});
  for(const [view,index] of [['working-capital',0],['profitability',4]]){
    await page.goto(`/#view=${view}&page=${index}`);
    await page.locator('.cx-analysis-nav').getByRole('button',{name:'Underlying records'}).click();
    const panel=page.locator('.cx-evidence');
    await expect(panel).toBeVisible();
    await expect(panel.locator('tbody tr')).toHaveCount(2);
    const fit=await panel.evaluate(node=>({last:[...node.querySelectorAll('tbody tr')].at(-1).getBoundingClientRect().bottom,wrap:node.querySelector('.cx-table-wrap').getBoundingClientRect().bottom,horizontal:document.documentElement.scrollWidth>innerWidth}));
    expect(fit.last).toBeLessThanOrEqual(fit.wrap+1);
    expect(fit.horizontal).toBe(false);
  }
});

test('NWC resize threshold never hides the flow or advertised evidence rows',async({page})=>{
  for(const height of [820,821,900,1020,1021]){
    await page.setViewportSize({width:1280,height});
    await page.goto('/#view=working-capital&page=0');
    const flow=page.locator('.cx-flow-map');
    await expect(flow).toBeVisible();
    const fit=await page.evaluate(()=>{
      const flow=document.querySelector('.cx-flow'),map=flow.querySelector('.cx-flow-map'),panel=document.querySelector('.cx-evidence'),wrap=panel.querySelector('.cx-table-wrap'),rows=[...panel.querySelectorAll('tbody tr')];
      return {compact:map.classList.contains('nwc-flow-compact'),flowOverflow:flow.scrollHeight-flow.clientHeight,rows:rows.length,last:rows.at(-1).getBoundingClientRect().bottom,wrap:wrap.getBoundingClientRect().bottom};
    });
    expect(fit.compact).toBe(height<=1020);
    expect(fit.flowOverflow).toBeLessThanOrEqual(1);
    expect(fit.rows).toBe(height<=820?2:3);
    expect(fit.last).toBeLessThanOrEqual(fit.wrap+1);
  }
});

test('mobile contribution focus survives changing the working-capital dimension',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=working-capital&page=0');
  const focus=page.locator('.cx-analysis-nav');
  await expect(focus).toBeVisible();
  await expect(focus).toHaveCount(1);
  await expect(focus.getByRole('button',{name:'Contribution'})).toHaveAttribute('aria-pressed','true');

  await page.locator('.cx-dimensions').getByRole('button',{name:'Component'}).click();
  await expect(focus).toBeVisible();
  await expect(focus).toHaveCount(1);
  await expect(focus.getByRole('button',{name:'Contribution'})).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.cx-ranking')).toBeVisible();
  await expect(page.locator('.cx-ranking .contribution-row')).not.toHaveCount(0);

  await focus.getByRole('button',{name:'Underlying records'}).click();
  const evidence=page.locator('.cx-evidence');
  await expect(evidence).toBeVisible();
  await expect(evidence.locator('tbody tr')).not.toHaveCount(0);
  const tableRegion=evidence.locator('.cx-table-wrap');
  await expect(tableRegion).toHaveAttribute('role','region');
  await expect(tableRegion).toHaveAttribute('tabindex','0');
  const hasOverflow=await tableRegion.evaluate(node=>node.scrollWidth>node.clientWidth+1);
  expect(hasOverflow).toBe(true);
  const scrollHint=evidence.locator('.cx-table-scroll-hint');
  await expect(scrollHint).toBeVisible();
  await expect(scrollHint).toContainText('remaining columns');
  await tableRegion.focus();
  await tableRegion.press('ArrowRight');
  expect(await tableRegion.evaluate(node=>node.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
