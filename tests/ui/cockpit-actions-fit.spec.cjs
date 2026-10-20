const {test,expect}=require('@playwright/test');

for(const width of [320,375,390]){
  test(`Cockpit header actions stay on screen at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:740});
    for(const view of ['operations-capex','cash-flow','balance-sheet']){
      await page.goto(`/#view=${view}&page=0`);
      const actions=page.locator('.sw-head:visible button');
      await expect(actions.first()).toBeVisible();
      const offscreen=await actions.evaluateAll(buttons=>buttons.filter(button=>getComputedStyle(button).display!=='none').filter(button=>{const box=button.getBoundingClientRect();return box.right>innerWidth+1||box.left<-1;}).map(button=>button.textContent.trim()));
      expect(offscreen,`${view} at ${width}px`).toEqual([]);
    }
  });
}
