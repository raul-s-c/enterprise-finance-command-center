const {test,expect}=require('@playwright/test');

for(const [width,height] of [[375,812],[1366,768]]){
  test(`P&L column heading stays above scrolled values at ${width}x${height}`,async({page})=>{
    await page.setViewportSize({width,height});
    await page.goto('/#view=pnl');
    const scroller=page.locator('.pnl-scroll:visible').first();
    await expect(scroller).toBeVisible();
    const covered=await scroller.evaluate(node=>{
      const heading=node.querySelector('.pnl-heading');
      if(node.scrollHeight-node.clientHeight<12)return {skipped:true};
      node.scrollTop=node.scrollHeight;
      const head=heading.getBoundingClientRect();
      const hits=[...node.querySelectorAll('.pnl-row b')].map(value=>value.getBoundingClientRect()).filter(box=>box.top<head.bottom-2&&box.bottom>head.top);
      return {skipped:false,checked:hits.length,leaks:hits.filter(box=>!heading.contains(document.elementFromPoint(box.left+box.width/2,Math.max(box.top,head.top)+2))).length};
    });
    if(covered.skipped)test.skip(true,'P&L fits without scrolling at this size');
    expect(covered.checked).toBeGreaterThan(0);
    expect(covered.leaks).toBe(0);
  });
}
