const {test,expect}=require('@playwright/test');

test('review evidence leads with variance and accountable action state',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=performance-review&page=1');
  const panels=page.locator('.story-composite>.panel');
  await expect(panels).toHaveCount(2);
  await expect(panels.first().locator('thead th:visible')).toHaveText(['Metric','Actual','Benchmark','Variance']);
  await expect(panels.last().locator('thead th:visible')).toHaveText(['Trigger / priority','Owner','Due','Status']);
  const drivers=await panels.first().locator('tbody tr').evaluateAll(rows=>rows.map(row=>({metric:row.cells[0]?.textContent?.trim(),variance:row.querySelector('.review-variance')?.className||'',title:row.querySelector('.review-variance')?.title||''})));
  expect(drivers.find(row=>row.metric==='OPEX')).toMatchObject({variance:expect.stringContaining('is-adverse'),title:'Adverse financial variance'});
  expect(drivers.find(row=>row.metric==='Revenue')).toMatchObject({variance:expect.stringContaining('is-favorable'),title:'Favorable financial variance'});
  await expect(panels.last().locator('tbody tr').first()).toContainText('Open');
  for(const panel of await panels.all())expect(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+1)).toBe(true);
  await page.screenshot({path:'test-results/review-evidence-columns.png',fullPage:true});
});

test('review tabs fit a short laptop while retaining full accessible titles',async({page})=>{
  await page.setViewportSize({width:1024,height:720});
  await page.goto('/#view=performance-review&page=0');
  const tabs=page.locator('#reportTabs button');
  await expect(tabs).toHaveText(['Review story','Drivers & actions','Lifecycle','Action register']);
  for(const tab of await tabs.all()){
    expect(await tab.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
    expect((await tab.getAttribute('aria-label')).length).toBeGreaterThan((await tab.textContent()).length);
  }
  await tabs.nth(1).click();
  await expect(page.locator('#reportPageNumber')).toContainText('2 / 4');
  await expect(page.locator('#reportPageSelect')).toHaveValue('1');
});

test('close-area navigation stays on one line at laptop width without losing report names',async({page})=>{
  await page.setViewportSize({width:1024,height:720});
  await page.goto('/#view=performance-review&page=0');
  const modules=page.locator('#reportModules button');
  await expect(modules).toHaveCount(4);
  await expect(modules.locator('.module-label-compact:visible')).toHaveText(['Journey','Review','Actions','Data']);
  const bounds=await modules.evaluateAll(buttons=>buttons.map(button=>({top:button.getBoundingClientRect().top,height:button.getBoundingClientRect().height,clipped:button.scrollWidth>button.clientWidth+1})));
  expect(new Set(bounds.map(item=>item.top)).size).toBe(1);
  expect(bounds.every(item=>item.height<=30&&!item.clipped)).toBe(true);
  const score=await page.locator('.prv-score').evaluate(panel=>({
    cards:[...panel.querySelectorAll('.prv-score-card')].map(card=>({top:card.getBoundingClientRect().top,left:card.getBoundingClientRect().left,clipped:card.scrollHeight>card.clientHeight+1,barWidth:card.querySelector('.prv-pair i')?.getBoundingClientRect().width||0})),
    clipped:panel.scrollHeight>panel.clientHeight+1
  }));
  expect(score.clipped).toBe(false);
  expect(score.cards).toHaveLength(3);
  console.log('TABLET_SCORE_GEOMETRY',JSON.stringify(score.cards));
  expect(score.cards.every(card=>!card.clipped&&card.barWidth>100)).toBe(true);
  expect(new Set(score.cards.map(card=>card.top)).size).toBe(1);
  expect(score.cards[0].left).toBeLessThan(score.cards[1].left);
  expect(score.cards[1].left).toBeLessThan(score.cards[2].left);
  await page.getByRole('button',{name:'Action Execution',exact:true}).click();
  await expect(page.locator('#viewTitle')).toHaveText('Action Execution');
  await page.setViewportSize({width:1280,height:720});
  await expect(page.locator('#reportModules .module-label-full:visible')).toHaveText(['Close Journey','Performance Review','Action Execution','Data Journey']);
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('#reportModules')).toBeHidden();
  await expect(page.locator('#reportModule')).toHaveValue('action-execution');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
