const {test,expect}=require('@playwright/test');

test('P&L lineage nodes remain fully inside the visible flow panel',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=pnl&page=5');
  await expect(page.locator('.cx-flow-map.pnl-flow button')).toHaveCount(4);
  const geometry=await page.evaluate(()=>{
    const panel=document.querySelector('.cx-flow').getBoundingClientRect();
    const nodes=[...document.querySelectorAll('.cx-flow-map.pnl-flow button')].map(button=>{const box=button.getBoundingClientRect();return {top:box.top,bottom:box.bottom}});
    const inspector=document.querySelector('.cx-inspector');
    const evidence=document.querySelector('.cx-evidence').getBoundingClientRect();
    return {panel:{top:panel.top,bottom:panel.bottom},nodes,inspector:{left:inspector.getBoundingClientRect().left,detailsHeight:inspector.querySelector('dl').clientHeight,detailsContent:inspector.querySelector('dl').scrollHeight},evidenceRight:evidence.right};
  });
  expect(geometry.nodes.every(node=>node.top>=geometry.panel.top&&node.bottom<=geometry.panel.bottom),JSON.stringify(geometry)).toBe(true);
  expect(geometry.inspector.detailsContent,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.inspector.detailsHeight+1);
  expect(geometry.evidenceRight,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.inspector.left+1);
  const screenshot=testInfo.outputPath('pnl-lineage-1280x720.png');
  await page.screenshot({path:screenshot});
  await testInfo.attach('pnl-lineage-1280x720',{path:screenshot,contentType:'image/png'});
  await page.locator('.cx-flow-map.pnl-flow button').first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();
});
