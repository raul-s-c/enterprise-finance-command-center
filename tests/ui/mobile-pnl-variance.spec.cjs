const {test,expect}=require('@playwright/test');

test('mobile P&L exposes both actuals and signed variances in one vertical report scroll',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=pnl&page=0');
  await expect(page.locator('[data-pnl-key]')).toHaveCount(10);
  const statement=page.locator('.pnl-visual');
  const controls=page.getByRole('group',{name:'Compact P&L columns'});
  await expect(controls).toBeVisible();
  await expect(controls.getByRole('button',{name:'Values'})).toHaveAttribute('aria-pressed','true');
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeVisible();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeHidden();
  await controls.getByRole('button',{name:'Δ PY'}).click();
  await expect(controls.getByRole('button',{name:'Δ PY'})).toHaveAttribute('aria-pressed','true');
  await expect(statement.locator('.pnl-variance-context')).toBeVisible();
  await expect(statement.locator('.pnl-variance-context')).toContainText('green = favorable, red = adverse');
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeHidden();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeVisible();
  await expect(statement.locator('[data-pnl-key="revenue"] .pnl-delta')).toBeVisible();
  await expect(statement.locator('[data-pnl-key="revenue"] .pnl-percent')).toBeVisible();
  expect(await statement.locator('.pnl-scroll').evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  const content=page.locator('#content');
  await content.evaluate(node=>node.scrollTo({top:node.scrollHeight,behavior:'instant'}));
  const mobileFit=await page.evaluate(()=>{
    const content=document.querySelector('#content'),scroll=document.querySelector('.pnl-scroll');
    const last=document.querySelector('[data-pnl-key]:last-of-type')||[...document.querySelectorAll('[data-pnl-key]')].at(-1);
    const note=document.querySelector('.pnl-note'),footer=document.querySelector('.report-footer');
    return {innerYOverflow:scroll.scrollHeight-scroll.clientHeight,innerXOverflow:scroll.scrollWidth-scroll.clientWidth,
      lastBottom:last.getBoundingClientRect().bottom,noteBottom:note.getBoundingClientRect().bottom,
      contentBottom:content.getBoundingClientRect().bottom,footerTop:footer.getBoundingClientRect().top,
      pageXOverflow:document.documentElement.scrollWidth-innerWidth};
  });
  expect(mobileFit.innerYOverflow,JSON.stringify(mobileFit)).toBeLessThanOrEqual(1);
  expect(mobileFit.innerXOverflow,JSON.stringify(mobileFit)).toBeLessThanOrEqual(1);
  expect(mobileFit.lastBottom,JSON.stringify(mobileFit)).toBeLessThanOrEqual(mobileFit.contentBottom+1);
  expect(mobileFit.noteBottom,JSON.stringify(mobileFit)).toBeLessThanOrEqual(mobileFit.contentBottom+1);
  expect(mobileFit.noteBottom,JSON.stringify(mobileFit)).toBeLessThanOrEqual(mobileFit.footerTop+1);
  expect(mobileFit.pageXOverflow).toBeLessThanOrEqual(1);
  await page.screenshot({path:'test-results/mobile-pnl-single-scroll.png'});
  await controls.getByRole('button',{name:'Values'}).click();
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeVisible();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeHidden();
  await statement.locator('[data-pnl-key="gross_profit"]').click();
  const evidence=page.locator('#reportDialog');
  await expect(evidence).toBeVisible();
  await expect(evidence.locator('#reportDialogTitle')).toHaveText('Gross profit');
  await expect(evidence.locator('#reportDialogBody')).toContainText('Calculation:');
  await expect(evidence.locator('#reportDialogBody')).toContainText('Marginal contribution');
  await expect(evidence.locator('#reportDialogBody')).toContainText('management_detail');
  await expect(evidence.locator('.pnl-source-detail th').nth(2)).toContainText('PY (€m)');
  await expect(evidence.locator('.pnl-source-detail td').first()).toHaveCSS('font-size','10px');
  expect(await evidence.locator('.pnl-source-detail table').evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
  expect(await evidence.evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
  await page.locator('#reportDialogClose').click();
  await expect(evidence).not.toBeVisible();
  for(const width of [320,600,700]){
    await page.setViewportSize({width,height:844});
    await statement.locator('[data-pnl-key="gross_profit"]').click();
    await expect(evidence).toBeVisible();
    expect(await evidence.locator('.pnl-source-detail table').evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
    await page.locator('#reportDialogClose').click();
  }

  for(const width of [320,390,600,700]){
    await page.setViewportSize({width,height:844});
    const scroll=statement.locator('.pnl-scroll');
    expect(await scroll.evaluate(node=>node.scrollHeight-node.clientHeight)).toBeLessThanOrEqual(1);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  }

  await page.setViewportSize({width:768,height:720});
  await expect(controls).toBeVisible();
  expect(await statement.locator('.pnl-scroll').evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
  await controls.getByRole('button',{name:'Δ PY'}).click();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);

  await page.setViewportSize({width:1280,height:720});
  await expect(controls).toBeHidden();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeVisible();
});


test('laptop P&L keeps all IBCS comparison columns inside the visible panel',async({page},testInfo)=>{
  for(const width of [1100,1040,901]){
    await page.setViewportSize({width,height:720});
    await page.goto('/#view=pnl&page=0');
    const statement=page.locator('.pnl-visual');
    await expect(statement).toBeVisible();
    await expect(statement.locator('.pnl-heading>span')).toHaveCount(5);
    const fit=await page.evaluate(()=>{
      const scroll=document.querySelector('.pnl-scroll');
      const columns=[...document.querySelectorAll('.pnl-heading>span')];
      const rowColumnsRight=[...document.querySelectorAll('.pnl-row')].map(row=>row.lastElementChild.getBoundingClientRect().right);
      return {
        clientWidth:scroll.clientWidth,
        scrollWidth:scroll.scrollWidth,
        right:scroll.getBoundingClientRect().right,
        lastHeadingRight:columns[4].getBoundingClientRect().right,
        rowColumnsRight,
        compactSwitch:getComputedStyle(document.querySelector('.pnl-mobile-switch')).display,
        visibleColumns:columns.map(column=>getComputedStyle(column).display!=='none')
      };
    });
    expect(fit.scrollWidth,JSON.stringify(fit)).toBeLessThanOrEqual(fit.clientWidth+1);
    expect(fit.lastHeadingRight,JSON.stringify(fit)).toBeLessThanOrEqual(fit.right+1);
    expect(fit.rowColumnsRight.every(right=>right<=fit.right+1),JSON.stringify(fit)).toBe(true);
    expect(fit.compactSwitch).toBe('none');
    expect(fit.visibleColumns).toEqual([true,true,true,true,true]);
    const pageFit=await page.evaluate(()=>{
      const selectors=['.topbar','.filters','#entityFilter','#divisionFilter','.pnl-analysis-layout','.pnl-visual','.pnl-scroll','.pnl-heading>span:last-child'];
      return {
        viewport:innerWidth,
        documentWidth:document.documentElement.scrollWidth,
        edges:selectors.map(selector=>{
          const element=document.querySelector(selector);
          if(!element)return {selector,missing:true};
          const rect=element.getBoundingClientRect();
          return {selector,right:rect.right,visible:getComputedStyle(element).display!=='none'};
        })
      };
    });
    expect(pageFit.documentWidth,JSON.stringify(pageFit)).toBeLessThanOrEqual(pageFit.viewport);
    expect(pageFit.edges.filter(edge=>edge.visible&&!edge.missing).every(edge=>edge.right<=pageFit.viewport+1),JSON.stringify(pageFit)).toBe(true);
    if(width===1040){
      const screenshot=testInfo.outputPath('pnl-laptop-1040x720.png');
      await page.screenshot({path:screenshot});
      await testInfo.attach('pnl-laptop-1040x720',{path:screenshot,contentType:'image/png'});
    }
  }
});
