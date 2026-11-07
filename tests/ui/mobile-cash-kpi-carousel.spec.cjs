const {test,expect}=require('@playwright/test');

test('mobile cash cockpit KPI carousel keeps every measure reachable without scrollbar chrome',async({page})=>{
  await page.setViewportSize({width:390,height:812});
  await page.goto('/#view=cash-flow&page=0');
  const band=page.locator('.sw-kpis').first();
  const cards=band.locator('.sw-kpi');
  await expect(band).toBeVisible();
  await expect(cards).toHaveCount(5);
  const initial=await band.evaluate(node=>({
    clientWidth:node.clientWidth,
    scrollWidth:node.scrollWidth,
    snap:getComputedStyle(node).scrollSnapType,
    scrollbarWidth:getComputedStyle(node).scrollbarWidth,
    webkitScrollbar:getComputedStyle(node,'::-webkit-scrollbar').display,
    left:node.getBoundingClientRect().left,
    right:node.getBoundingClientRect().right,
    documentWidth:document.documentElement.scrollWidth
  }));
  expect(initial.scrollWidth,JSON.stringify(initial)).toBeGreaterThan(initial.clientWidth);
  expect(initial.snap).toContain('x');
  expect(initial.scrollbarWidth).toBe('none');
  expect(initial.webkitScrollbar).toBe('none');
  expect(initial.documentWidth).toBeLessThanOrEqual(390);

  await cards.last().focus();
  const focused=await band.evaluate(node=>{
    const last=node.querySelector('.sw-kpi:last-child');
    const rail=node.getBoundingClientRect(),card=last.getBoundingClientRect();
    return {focused:document.activeElement===last,scrollLeft:node.scrollLeft,left:card.left,right:card.right,railLeft:rail.left,railRight:rail.right};
  });
  expect(focused.focused).toBe(true);
  expect(focused.scrollLeft).toBeGreaterThan(0);
  expect(focused.left).toBeGreaterThanOrEqual(focused.railLeft-1);
  expect(focused.right).toBeLessThanOrEqual(focused.railRight+1);
});
