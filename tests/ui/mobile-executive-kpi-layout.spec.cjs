const {test,expect}=require('@playwright/test');

for(const viewport of [{width:360,height:640},{width:390,height:844}]){
  test(`Executive overview KPI cards form a readable two-column layout at ${viewport.width}px`,async({page},testInfo)=>{
    await page.setViewportSize(viewport);
    await page.goto('/#view=executive&page=0');
    const cards=page.locator('.story-kpis .story-kpi');
    await expect(cards).toHaveCount(5);
    await expect(cards.first()).toBeVisible();
    const layout=await page.locator('.story-kpis').evaluate(container=>{
      const cards=[...container.querySelectorAll('.story-kpi')];
      const rect=node=>{const box=node.getBoundingClientRect();return {left:box.left,right:box.right,top:box.top,bottom:box.bottom,width:box.width}};
      return {
        width:container.clientWidth,
        scrollWidth:container.scrollWidth,
        columns:getComputedStyle(container).gridTemplateColumns.split(' ').length,
        cards:cards.map(card=>({box:rect(card),scrollWidth:card.scrollWidth,clientWidth:card.clientWidth,label:rect(card.querySelector('span')),value:rect(card.querySelector('strong')),delta:rect(card.querySelector('small'))}))
      };
    });
    expect(layout.columns,JSON.stringify(layout)).toBe(2);
    expect(layout.scrollWidth,JSON.stringify(layout)).toBeLessThanOrEqual(layout.width+1);
    expect(layout.cards.every(card=>card.scrollWidth<=card.clientWidth+1),JSON.stringify(layout)).toBe(true);
    expect(Math.abs(layout.cards[0].box.left-layout.cards[2].box.left),JSON.stringify(layout)).toBeLessThanOrEqual(1);
    expect(Math.abs(layout.cards[1].box.left-layout.cards[3].box.left),JSON.stringify(layout)).toBeLessThanOrEqual(1);
    expect(layout.cards[4].box.width,JSON.stringify(layout)).toBeGreaterThan(layout.cards[0].box.width*1.8);
    expect(layout.cards[4].value.left,JSON.stringify(layout)).toBeGreaterThan(layout.cards[4].label.left);
    expect(layout.cards[4].delta.top,JSON.stringify(layout)).toBeGreaterThan(layout.cards[4].label.top);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);

    const screenshot=testInfo.outputPath(`executive-mobile-kpis-${viewport.width}.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`executive-mobile-kpis-${viewport.width}`,{path:screenshot,contentType:'image/png'});
  });
}

