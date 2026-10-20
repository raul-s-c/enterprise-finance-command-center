const {test,expect}=require('@playwright/test');

for(const [width,height] of [[360,640],[375,812]]){
  test(`Mobile report header stays left-aligned and compact at ${width}x${height}`,async({page})=>{
    await page.setViewportSize({width,height});
    await page.goto('/#view=executive');
    await expect(page.locator('.story-narrative')).toBeVisible();
    await expect(page.locator('#reportAreaLabel')).toBeHidden();
    const layout=await page.evaluate(()=>{
      const box=selector=>document.querySelector(selector).getBoundingClientRect();
      const topbar=box('.topbar'),title=box('#viewTitle'),subtitle=box('#viewSubtitle'),content=box('#content');
      return {titleInset:title.left-topbar.left,sameRow:Math.abs(subtitle.top-title.top)<title.height,contentShare:content.height/innerHeight,overflow:document.documentElement.scrollWidth-innerWidth};
    });
    expect(layout.titleInset).toBeLessThanOrEqual(16);
    expect(layout.sameRow).toBe(true);
    expect(layout.contentShare).toBeGreaterThan(height<700?0.5:0.6);
    expect(layout.overflow).toBeLessThanOrEqual(1);
  });
}
