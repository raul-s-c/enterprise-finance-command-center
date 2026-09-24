const {test,expect}=require('@playwright/test');

test('every report page avoids horizontal overflow at laptop and mobile widths',async({page})=>{
  test.setTimeout(300000);
  const failures=[];
  let audited=0;
  for(const width of [1280,390]){
    await page.setViewportSize({width,height:width===390?844:720});
    await page.goto('/#view=executive&page=0');
    await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(0);
    const viewIds=await page.evaluate(()=>views.map(view=>view[0]));
    for(const view of viewIds){
      await page.goto(`/#view=${view}&page=0`);
      await expect.poll(()=>page.evaluate(()=>state.view)).toBe(view);
      const count=await page.evaluate(()=>reportState.pages.length);
      for(let index=0;index<count;index++){
        await page.goto(`/#view=${view}&page=${index}`);
        await expect.poll(()=>page.evaluate(()=>reportState.page)).toBe(index);
        const result=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,title:reportState.pages[reportState.page]?.title}));
        audited++;
        if(result.overflow>1)failures.push(`${width}px ${view} ${index} ${result.title}: +${result.overflow}px`);
      }
    }
  }
  expect(failures).toEqual([]);
  expect(audited).toBeGreaterThan(150);
});
