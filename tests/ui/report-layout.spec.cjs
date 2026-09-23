const {test,expect}=require('@playwright/test');

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

test('Executive keeps every overview region reachable on tablet and mobile',async({page})=>{
  for(const viewport of [{width:1100,height:820},{width:900,height:820},{width:390,height:844}]){
    await page.setViewportSize(viewport);
    await page.goto('/#view=executive');
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
