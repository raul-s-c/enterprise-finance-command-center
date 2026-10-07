const {test,expect}=require('@playwright/test');

for(const viewport of [{width:1024,height:720},{width:1440,height:900}]){
  test(`cash detail keeps trend and signed bridge visible at ${viewport.width}×${viewport.height}`,async({page},testInfo)=>{
    await page.setViewportSize(viewport);
    await page.goto('/#view=cash-flow&page=1');
    const board=page.locator('.cash-detail-board');
    await expect(board).toBeVisible();
    await expect(board.locator('.panel.span-8 .series-svg')).toBeVisible();
    await expect(board.locator('.panel.span-4 .metric-row')).toHaveCount(5);
    await expect(board.locator('.panel.span-4 .metric-row').last()).toContainText('Net cash movement');
    await expect(board.locator('.cash-bridge-note')).toContainText('Operating + investing = free cash flow');
    await expect(board.locator('.kpi:visible')).toHaveCount(3);
    const geometry=await board.evaluate(element=>{
      const box=element.getBoundingClientRect();
      const children=[...element.querySelectorAll(':scope>.story-composite')].map(section=>{
        const bounds=section.getBoundingClientRect();
        return {bottom:bounds.bottom,right:bounds.right,scrollHeight:section.scrollHeight,clientHeight:section.clientHeight};
      });
      return {boardBottom:box.bottom,boardRight:box.right,scrollHeight:element.scrollHeight,clientHeight:element.clientHeight,children,overflow:document.documentElement.scrollWidth-innerWidth};
    });
    expect(geometry.scrollHeight,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.clientHeight+1);
    expect(geometry.children.every(child=>child.bottom<=geometry.boardBottom+1&&child.right<=geometry.boardRight+1&&child.scrollHeight<=child.clientHeight+1),JSON.stringify(geometry)).toBe(true);
    expect(geometry.overflow,JSON.stringify(geometry)).toBeLessThanOrEqual(1);
    const gap=await page.evaluate(()=>{
      const row=data.cash_flow.at(-1);
      return [row.operating_cash_flow+row.investing_cash_flow-row.free_cash_flow,row.free_cash_flow+row.financing_cash_flow-row.net_cash_movement];
    });
    expect(gap.every(value=>Math.abs(value)<=0.02),JSON.stringify(gap)).toBe(true);
    const screenshot=testInfo.outputPath(`cash-detail-${viewport.width}.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`cash-detail-${viewport.width}`,{path:screenshot,contentType:'image/png'});
    await page.locator('#reportNext').click();
    await expect(page.locator('#reportPageSelect')).toHaveValue('2');
    await page.locator('#reportPrevious').click();
    await expect(board).toBeVisible();
  });
}
