const {test,expect}=require('@playwright/test');

const contentShare=page=>page.evaluate(()=>document.getElementById('content').getBoundingClientRect().height/innerHeight);
const collapsed=page=>page.evaluate(()=>document.body.classList.contains('mobile-chrome-collapsed'));
async function wheelOverContent(page,deltaY,steps=6){
  const box=await page.locator('#content').boundingBox();
  await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
  for(let i=0;i<steps;i++){await page.mouse.wheel(0,deltaY/steps);await page.waitForTimeout(40);}
  await page.waitForTimeout(350);
}

for(const [width,height] of [[375,812],[360,640]]){
  test.describe(`Mobile report chrome collapse at ${width}x${height}`,()=>{
    test.beforeEach(async({page})=>{
      await page.setViewportSize({width,height});
      await page.goto('/#view=executive');
      await expect(page.locator('#content')).not.toBeEmpty();
      await page.waitForFunction(()=>{const c=document.getElementById('content');return c.scrollHeight-c.clientHeight>300;});
    });

    test('collapses on scroll down and restores on scroll up',async({page})=>{
      const before=await contentShare(page);
      await wheelOverContent(page,500);
      expect(await collapsed(page)).toBe(true);
      await expect(page.locator('.global-bar')).toBeVisible();
      await expect(page.locator('.report-footer')).toBeVisible();
      expect(await contentShare(page)).toBeGreaterThan(0.8);
      expect(await contentShare(page)).toBeGreaterThan(before);
      await wheelOverContent(page,-120,3);
      expect(await collapsed(page)).toBe(false);
      await expect(page.locator('#entityFilter')).toBeVisible();
    });

    test('restores when keyboard focus moves into the hidden chrome',async({page})=>{
      await wheelOverContent(page,500);
      expect(await collapsed(page)).toBe(true);
      await page.locator('#globalSearch').focus();
      for(let i=0;i<12;i++){
        await page.keyboard.press('Tab');
        if(await page.evaluate(()=>document.activeElement?.id)==='entityFilter')break;
      }
      expect(await page.evaluate(()=>document.activeElement?.id)).toBe('entityFilter');
      expect(await collapsed(page)).toBe(false);
      await expect(page.locator('#entityFilter')).toBeVisible();
    });

    test('programmatic scrolling never hides the controls',async({page})=>{
      await page.evaluate(()=>{const c=document.getElementById('content');c.scrollTop=c.scrollHeight;});
      await page.waitForTimeout(300);
      expect(await collapsed(page)).toBe(false);
      await expect(page.locator('#entityFilter')).toBeVisible();
    });

    test('restores on report change',async({page})=>{
      await wheelOverContent(page,500);
      expect(await collapsed(page)).toBe(true);
      await page.evaluate(()=>{state.view='pnl';reportState.page=0;render();});
      expect(await collapsed(page)).toBe(false);
    });
  });
}

test('desktop report chrome never collapses',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  await page.goto('/#view=executive');
  await expect(page.locator('#content')).not.toBeEmpty();
  await wheelOverContent(page,800);
  expect(await collapsed(page)).toBe(false);
  await expect(page.locator('.topbar')).toBeVisible();
});

test('collapsed chrome expands when the viewport widens beyond phones',async({page})=>{
  await page.setViewportSize({width:375,height:812});
  await page.goto('/#view=executive');
  await expect(page.locator('#content')).not.toBeEmpty();
  await page.waitForFunction(()=>{const c=document.getElementById('content');return c.scrollHeight-c.clientHeight>300;});
  await wheelOverContent(page,500);
  expect(await collapsed(page)).toBe(true);
  await page.setViewportSize({width:768,height:1024});
  await expect.poll(()=>collapsed(page)).toBe(false);
});
