const {test,expect}=require('@playwright/test');

const cockpits=[
  {view:'cash-flow',selector:'.cash-cockpit'},
  {view:'treasury',selector:'.treasury-cockpit'},
  {view:'balance-sheet',selector:'.balance-cockpit'},
  {view:'forecast',selector:'.forecast-cockpit'}
];

test('financial cockpit shows linked analysis panels side by side on a compact laptop',async({page},testInfo)=>{
  await page.setViewportSize({width:1040,height:720});
  for(const {view,selector} of cockpits){
    await page.goto(`/#view=${view}&page=0`);
    const cockpit=page.locator(selector),grid=cockpit.locator('.sw-grid');
    await expect(grid).toBeVisible();
    const headerFit=await cockpit.locator('.sw-head').evaluate(node=>{
      const items=[...node.querySelectorAll('h2,button')].filter(item=>getComputedStyle(item).display!=='none').map(item=>{
        const rect=item.getBoundingClientRect();
        return {text:item.textContent.trim(),left:rect.left,right:rect.right};
      });
      return {viewport:innerWidth,items};
    });
    expect(headerFit.items.length,JSON.stringify(headerFit)).toBeGreaterThan(0);
    expect(headerFit.items.every(item=>item.left>=0&&item.right<=headerFit.viewport+1),JSON.stringify(headerFit)).toBe(true);
    await expect(cockpit.locator('.sw-primary')).toBeVisible();
    await expect(cockpit.locator('.sw-secondary')).toBeVisible();
    await expect(cockpit.locator('.sw-secondary .sw-formula,.sw-secondary .sw-flow,.sw-secondary .sw-structure').first()).toBeVisible();
    await expect(cockpit.locator('.sw-detail')).toBeHidden();
    const fit=await grid.evaluate(node=>{
      const box=node.getBoundingClientRect();
      const panels=[...node.querySelectorAll(':scope > .sw-primary,:scope > .sw-secondary')].map(panel=>{
        const rect=panel.getBoundingClientRect();
        return {left:rect.left,right:rect.right,scrollWidth:panel.scrollWidth,clientWidth:panel.clientWidth};
      });
      const analysis=[...node.querySelectorAll('.sw-secondary .sw-formula,.sw-secondary .sw-flow,.sw-secondary .sw-structure')].map(item=>{
        const rect=item.getBoundingClientRect();
        return {left:rect.left,right:rect.right,scrollWidth:item.scrollWidth,clientWidth:item.clientWidth,childrenRight:[...item.children].map(child=>child.getBoundingClientRect().right)};
      });
      return {left:box.left,right:box.right,width:node.clientWidth,scrollWidth:node.scrollWidth,panels,analysis};
    });
    expect(fit.scrollWidth,JSON.stringify(fit)).toBeLessThanOrEqual(fit.width+1);
    expect(fit.panels.every(panel=>panel.left>=fit.left-1&&panel.right<=fit.right+1&&panel.scrollWidth<=panel.clientWidth+1),JSON.stringify(fit)).toBe(true);
    expect(fit.analysis.length,JSON.stringify(fit)).toBeGreaterThan(0);
    expect(fit.analysis.every(item=>item.left>=fit.left-1&&item.right<=fit.right+1&&item.scrollWidth<=item.clientWidth+1&&item.childrenRight.every(right=>right<=item.right+1)),JSON.stringify(fit)).toBe(true);
    await expect(cockpit.locator('.sw-analysis-nav button')).toHaveCount(3);
    await cockpit.locator('.sw-analysis-nav button').nth(2).click();
    await expect(cockpit.locator('.sw-detail')).toBeVisible();
    await expect(cockpit.locator('.sw-primary')).toBeHidden();
    await expect(cockpit.locator('.sw-secondary')).toBeHidden();
    await cockpit.locator('.sw-analysis-nav button').first().click();
    await expect(cockpit.locator('.sw-primary')).toBeVisible();
    await expect(cockpit.locator('.sw-secondary')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const screenshot=testInfo.outputPath(`${view}-compact-laptop-1040x720.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`${view}-compact-laptop-1040x720`,{path:screenshot,contentType:'image/png'});
  }
});