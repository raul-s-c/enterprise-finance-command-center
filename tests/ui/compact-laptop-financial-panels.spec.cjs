const {test,expect}=require('@playwright/test');

const cockpits=[
  {view:'cash-flow',selector:'.cash-cockpit'},
  {view:'treasury',selector:'.treasury-cockpit'},
  {view:'balance-sheet',selector:'.balance-cockpit'},
  {view:'forecast',selector:'.forecast-cockpit'}
];

test('financial cockpit analysis panels fit a compact laptop canvas',async({page},testInfo)=>{
  await page.setViewportSize({width:1040,height:720});
  for(const {view,selector} of cockpits){
    await page.goto(`/#view=${view}&page=0`);
    const cockpit=page.locator(selector);
    await expect(cockpit.locator('.sw-grid')).toBeVisible();
    await expect(cockpit.locator('.sw-primary')).toBeVisible();
    await expect(cockpit.locator('.sw-secondary')).toBeVisible();
    await expect(cockpit.locator('.sw-secondary .sw-formula,.sw-secondary .sw-flow,.sw-secondary .sw-structure').first()).toBeVisible();
    const fit=await cockpit.locator('.sw-grid').evaluate(grid=>{
      const gridBox=grid.getBoundingClientRect();
      const panels=[...grid.querySelectorAll(':scope > .sw-primary, :scope > .sw-secondary')].map(panel=>{
        const box=panel.getBoundingClientRect();
        return {right:box.right,scrollWidth:panel.scrollWidth,clientWidth:panel.clientWidth};
      });
      const analysis=[...grid.querySelectorAll('.sw-secondary .sw-formula,.sw-secondary .sw-flow,.sw-secondary .sw-structure')].map(item=>{
        const box=item.getBoundingClientRect();
        const children=[...item.children].map(child=>child.getBoundingClientRect().right);
        return {right:box.right,scrollWidth:item.scrollWidth,clientWidth:item.clientWidth,childrenRight:children};
      });
      return {gridRight:gridBox.right,gridWidth:grid.clientWidth,gridScrollWidth:grid.scrollWidth,panels,analysis};
    });
    expect(fit.gridScrollWidth,JSON.stringify(fit)).toBeLessThanOrEqual(fit.gridWidth+1);
    expect(fit.panels.every(panel=>panel.right<=fit.gridRight+1&&panel.scrollWidth<=panel.clientWidth+1),JSON.stringify(fit)).toBe(true);
    expect(fit.analysis.length,JSON.stringify(fit)).toBeGreaterThan(0);
    expect(fit.analysis.every(item=>item.right<=fit.gridRight+1&&item.scrollWidth<=item.clientWidth+1&&item.childrenRight.every(right=>right<=item.right+1)),JSON.stringify(fit)).toBe(true);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const screenshot=testInfo.outputPath(`${view}-compact-laptop-1040x720.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`${view}-compact-laptop-1040x720`,{path:screenshot,contentType:'image/png'});
  }
});