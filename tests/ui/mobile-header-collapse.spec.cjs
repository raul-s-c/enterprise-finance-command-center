const {test,expect}=require('@playwright/test');

const contentShare=page=>page.evaluate(()=>document.getElementById('content').getBoundingClientRect().height/innerHeight);
const collapsed=page=>page.evaluate(()=>document.body.classList.contains('mobile-chrome-collapsed'));
const settle=page=>page.waitForTimeout(400);

// A point inside the report body, over whichever pane a reader would drag.
const scrollPoint=page=>page.evaluate(()=>{const box=document.getElementById('content').getBoundingClientRect();return {x:box.left+box.width/2,y:box.top+box.height*.6};});
async function wheel(page,point,deltaY,steps=6){
  await page.mouse.move(point.x,point.y);
  for(let i=0;i<steps;i++){await page.mouse.wheel(0,deltaY/steps);await page.waitForTimeout(40);}
  await settle(page);
}
// Synthetic finger drag via CDP touch events; positive distance drags up, which scrolls the report down.
async function touchScroll(page,point,distance,steps=20){
  const cdp=await page.context().newCDPSession(page);
  const x=Math.round(point.x),y0=Math.round(point.y);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y:y0}]});
  for(let i=1;i<=steps;i++){
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:Math.round(y0-distance*i/steps)}]});
    await page.waitForTimeout(16);
  }
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await cdp.detach();
  await settle(page);
}
// Tab forward from the global search into the hidden chrome: the entity filter when the view offers one,
// otherwise the first chrome control (some views hide scope filters they cannot honour).
async function tabIntoChrome(page){
  const hasEntity=await page.locator('#entityFilter').evaluate(el=>el.checkVisibility());
  await page.locator('#globalSearch').focus();
  const where=()=>page.evaluate(()=>({id:document.activeElement?.id,chrome:Boolean(document.activeElement?.closest('.mobile-module,.topbar,.report-subnav,.report-context'))}));
  for(let i=0;i<14;i++){
    await page.keyboard.press('Tab');
    const at=await where();
    if(hasEntity?at.id==='entityFilter':at.chrome)break;
  }
  const at=await where();
  if(hasEntity)expect(at.id).toBe('entityFilter');else expect(at.chrome).toBe(true);
  await expect(page.locator(':focus')).toBeVisible();
}
async function open(page,view,size){
  await page.setViewportSize(size);
  await page.goto(`/#view=${view}`);
  await expect(page.locator('#content')).not.toBeEmpty();
  await page.waitForTimeout(800);
  return scrollPoint(page);
}

const PHONES=[{width:375,height:812},{width:360,height:640}];
// executive scrolls #content; the others fit (or nearly fit) a phone and rely on inner panes or gesture intent.
const VIEWS=['executive','pnl','cash-flow','operations-capex'];

for(const size of PHONES){
  test.describe(`Mobile report chrome collapse at ${size.width}x${size.height}`,()=>{
    for(const view of VIEWS){
      test(`${view}: wheel collapses, scroll up restores`,async({page})=>{
        const point=await open(page,view,size);
        const before=await contentShare(page);
        await wheel(page,point,500);
        expect(await collapsed(page)).toBe(true);
        await expect(page.locator('.global-bar')).toBeVisible();
        await expect(page.locator('.report-footer')).toBeVisible();
        await expect.poll(()=>contentShare(page)).toBeGreaterThan(Math.max(before,0.75));
        await wheel(page,point,-600,6);
        expect(await collapsed(page)).toBe(false);
        await expect(page.locator('#viewTitle')).toBeVisible();
      });
    }
  });

  test.describe(`Mobile report chrome collapse on touch at ${size.width}x${size.height}`,()=>{
    test.use({hasTouch:true,isMobile:true});
    for(const view of VIEWS){
      test(`${view}: swipe collapses, swipe back and focus restore`,async({page})=>{
        const point=await open(page,view,size);
        await touchScroll(page,point,300);
        expect(await collapsed(page)).toBe(true);
        await expect.poll(()=>contentShare(page)).toBeGreaterThan(0.75);
        await touchScroll(page,{x:point.x,y:point.y-200},-350);
        expect(await collapsed(page)).toBe(false);
        await touchScroll(page,point,300);
        expect(await collapsed(page)).toBe(true);
        await tabIntoChrome(page);
        expect(await collapsed(page)).toBe(false);
        await expect(page.locator('#viewTitle')).toBeVisible();
      });
    }
  });

  test.describe(`Mobile report chrome guards at ${size.width}x${size.height}`,()=>{
    test('programmatic scrolling never hides the controls',async({page})=>{
      await open(page,'executive',size);
      await page.evaluate(()=>{const c=document.getElementById('content');c.scrollTop=c.scrollHeight;});
      await settle(page);
      expect(await collapsed(page)).toBe(false);
      await expect(page.locator('#entityFilter')).toBeVisible();
    });

    test('restores on report change',async({page})=>{
      const point=await open(page,'executive',size);
      await wheel(page,point,500);
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
  const box=await page.locator('#content').boundingBox();
  await wheel(page,{x:box.x+box.width/2,y:box.y+box.height/2},800);
  expect(await collapsed(page)).toBe(false);
  await expect(page.locator('.topbar')).toBeVisible();
});

test('collapsed chrome expands when the viewport widens beyond phones',async({page})=>{
  const point=await open(page,'executive',PHONES[0]);
  await wheel(page,point,500);
  expect(await collapsed(page)).toBe(true);
  await page.setViewportSize({width:768,height:1024});
  await expect.poll(()=>collapsed(page)).toBe(false);
});
