const {test,expect}=require('@playwright/test');

test('laptop report tabs retain all destinations without clipped labels',async({page})=>{
  test.setTimeout(120000);
  await page.setViewportSize({width:1024,height:720});
  await page.goto('/#view=executive&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(0);
  const viewIds=await page.evaluate(()=>views.map(view=>view[0]));
  const failures=[];
  for(const view of viewIds){
    await page.goto(`/#view=${view}&page=0`);
    await expect.poll(()=>page.evaluate(()=>state.view)).toBe(view);
    const result=await page.locator('#reportTabs').evaluate(nav=>({
      overflow:nav.scrollWidth>nav.clientWidth+1,
      tabs:[...nav.querySelectorAll('button')].map(button=>({
        name:button.getAttribute('aria-label')||button.textContent.trim(),
        clipped:button.scrollWidth>button.clientWidth+1
      }))
    }));
    if(result.overflow||result.tabs.some(tab=>tab.clipped))failures.push({view,...result});
  }
  if(failures.length)throw new Error(`Clipped report tabs: ${failures.map(item=>`${item.view}: ${item.tabs.filter(tab=>tab.clipped).map(tab=>tab.name).join(', ')}${item.overflow?' (nav overflow)':''}`).join('; ')}`);

  await page.goto('/#view=cash-flow&page=0');
  const bridge=page.locator('#reportTabs [data-page="1"]');
  await expect(bridge).toHaveAttribute('aria-label',/Free cash flow/);
  await expect(bridge.locator('.report-tab-compact')).toHaveText('FCF');
  await bridge.click();
  await expect(page.locator('#reportPageSelect')).toHaveValue('1');
  await page.goto('/#view=fx&page=0');
  const exposures=page.getByRole('button',{name:'Largest open transaction exposures',exact:true});
  await expect(exposures.locator('.report-tab-compact')).toHaveText('Open exposures');
  await exposures.click();
  await expect(page.locator('#reportPageSelect')).toHaveValue(await exposures.getAttribute('data-page'));
  await page.goto('/#view=cash-flow&page=1');
  await page.setViewportSize({width:1280,height:720});
  await expect(bridge.locator('.report-tab-full')).toBeVisible();
  await expect(bridge.locator('.report-tab-compact')).toBeHidden();
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('#reportTabs')).toBeHidden();
  await expect(page.locator('#reportPageSelect')).toHaveValue('1');
});
