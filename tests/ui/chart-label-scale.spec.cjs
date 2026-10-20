const {test,expect}=require('@playwright/test');

const rendered=nodes=>nodes.filter(node=>node.getBoundingClientRect().height>0).map(node=>{
  const matrix=node.getScreenCTM();
  return parseFloat(getComputedStyle(node).fontSize)*Math.hypot(matrix.a,matrix.b);
});

for(const [width,height] of [[768,1024],[375,812]]){
  for(const [view,selector] of [['executive','.story-trend .report-svg text'],['cash-flow','.sw-primary .report-svg text']]){
    test(`${view} trend labels stay readable without oversizing at ${width}x${height}`,async({page})=>{
      await page.setViewportSize({width,height});
      await page.goto(`/#view=${view}&page=0`);
      const labels=page.locator(selector);
      await expect(labels.first()).toBeAttached();
      const sizes=await labels.evaluateAll(rendered);
      expect(sizes.length).toBeGreaterThan(0);
      expect(Math.min(...sizes)).toBeGreaterThanOrEqual(10);
      expect(Math.max(...sizes)).toBeLessThanOrEqual(18);
    });
  }
}
