const {test,expect}=require('@playwright/test');

test('NWC bridge labels remain legible within the compact laptop panel',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=working-capital&page=0');
  const bridge=page.locator('.contribution-explorer[data-contribution="nwc"] .cx-bridge svg');
  await expect(bridge).toBeVisible();
  const geometry=await bridge.evaluate(svg=>{
    const values=[...svg.querySelectorAll('text:not(.axis-label)')].map(text=>text.getBoundingClientRect());
    const labels=[...svg.querySelectorAll('text.axis-label')].map(text=>text.getBoundingClientRect());
    const bounds=svg.getBoundingClientRect();
    return {valueHeights:values.map(rect=>rect.height),labelHeights:labels.map(rect=>rect.height),spread:labels.at(-1).left-labels[0].left,top:Math.min(...values.map(rect=>rect.top)),bottom:Math.max(...labels.map(rect=>rect.bottom)),svgTop:bounds.top,svgBottom:bounds.bottom};
  });
  expect(Math.min(...geometry.valueHeights)).toBeGreaterThanOrEqual(10);
  expect(Math.min(...geometry.labelHeights)).toBeGreaterThanOrEqual(8.5);
  expect(geometry.spread).toBeGreaterThanOrEqual(300);
  expect(geometry.top).toBeGreaterThanOrEqual(geometry.svgTop-1);
  expect(geometry.bottom).toBeLessThanOrEqual(geometry.svgBottom+1);
  const screenshot=testInfo.outputPath('nwc-bridge-1280x720.png');
  await page.screenshot({path:screenshot});
  await testInfo.attach('nwc-bridge-1280x720',{path:screenshot,contentType:'image/png'});
});
