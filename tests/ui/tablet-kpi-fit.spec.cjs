const {test,expect}=require('@playwright/test');

const cockpits=['margin','cash-flow','balance-sheet','forecast','treasury','business-drivers','profitability','intercompany','operations-capex','fx','macro-sensitivities'];

test('Tablet cockpits show every KPI card in full without hidden horizontal scrolling',async({page})=>{
  await page.setViewportSize({width:768,height:1024});
  for(const view of cockpits){
    await page.goto(`/#view=${view}&page=0`);
    const band=page.locator('.sw-kpis').first();
    await expect(band,`${view} KPI band`).toBeVisible();
    const fit=await band.evaluate(node=>{
      const box=node.getBoundingClientRect();
      const cards=[...node.querySelectorAll('.sw-kpi')].filter(card=>getComputedStyle(card).display!=='none');
      return {cards:cards.length,overflow:node.scrollWidth-node.clientWidth,clipped:cards.filter(card=>{const r=card.getBoundingClientRect();return r.right>box.right+1||r.left<box.left-1;}).length};
    });
    expect(fit.cards,`${view} cards`).toBeGreaterThan(0);
    expect(fit.overflow,`${view} horizontal overflow`).toBeLessThanOrEqual(1);
    expect(fit.clipped,`${view} clipped cards`).toBe(0);
  }
});
