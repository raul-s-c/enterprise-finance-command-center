const {test,expect}=require('@playwright/test');
const {areas}=require('../../web/report-navigation.js');

// Manual-equivalent checks the axe audit cannot make (WCAG 1.4.4 resize text, 1.4.10 reflow):
// 200% browser zoom of a 1366x768 laptop is a 683x384 CSS viewport at deviceScaleFactor 2, and
// reflow is checked at 320x568. On every subpage of every report: no page-level horizontal scroll,
// no control pushed off-screen or cut by an overflow box, no text clipped without an ellipsis, the
// pager stays on screen and the report keeps a usable reading area.
const VIEWS=areas.flatMap(area=>area.views);
const MODES=[
  {name:'200% zoom · 683x384 @2x',width:683,height:384,deviceScaleFactor:2},
  {name:'reflow · 320x568',width:320,height:568,deviceScaleFactor:1}
];

async function open(page,view,index=0){
  await page.goto(`/#view=${view}&page=${index}`);
  await page.waitForFunction(v=>typeof reportState!=='undefined'&&state.view===v&&reportState.pages.length&&document.querySelector('#content').children.length,view);
}
async function goToPage(page,index){
  await page.evaluate(i=>reportNavigate(i),index);
  await page.waitForFunction(i=>reportState.page===i&&document.querySelector('#content').children.length,index);
}

function reflowProblems(){
  const width=document.documentElement.clientWidth,height=innerHeight,out=[];
  if(document.documentElement.scrollWidth>width+1)out.push(`page scrolls horizontally: ${document.documentElement.scrollWidth}px content in ${width}px`);
  const describe=el=>`${el.tagName.toLowerCase()}${el.id?`#${el.id}`:''}${el.getAttribute('class')?`.${String(el.getAttribute('class')).trim().split(/\s+/).slice(0,2).join('.')}`:''} "${(el.textContent||el.value||'').trim().replace(/\s+/g,' ').slice(0,40)}"`;
  const shown=el=>{
    const box=el.getBoundingClientRect();if(!box.width||!box.height)return false;
    if(el.closest('[hidden],[aria-hidden="true"],template,dialog:not([open])'))return false;
    const closed=el.closest('details:not([open])');if(closed&&!el.closest('summary'))return false;
    return getComputedStyle(el).visibility!=='hidden';
  };
  // A horizontally scrollable region (wide table, chart strip) is a legitimate 2-D exception.
  const inScroller=el=>{for(let node=el.parentElement;node&&node!==document.body;node=node.parentElement){const style=getComputedStyle(node);if(/(auto|scroll)/.test(style.overflowX)&&node.scrollWidth>node.clientWidth+1)return true;}return false;};
  const clippedBy=el=>{
    const box=el.getBoundingClientRect();
    for(let node=el.parentElement;node&&node!==document.body;node=node.parentElement){
      const style=getComputedStyle(node);if(/(auto|scroll)/.test(style.overflowX))return null;
      if(/(hidden|clip)/.test(style.overflowX)){const frame=node.getBoundingClientRect();if(box.right>frame.right+1||box.left<frame.left-1)return node;}
    }
    return null;
  };
  for(const el of document.querySelectorAll('button,a[href],select,input,textarea,summary,[role="button"],[role="tab"]')){
    if(!shown(el)||inScroller(el))continue;
    const box=el.getBoundingClientRect();
    if(box.right>width+1||box.left<-1)out.push(`control off-screen [${Math.round(box.left)}–${Math.round(box.right)}px]: ${describe(el)}`);
    const clip=clippedBy(el);if(clip)out.push(`control cut by ${describe(clip)}: ${describe(el)}`);
  }
  for(const el of document.querySelectorAll('.global-bar *,.mobile-module *,.topbar *,.report-subnav *,.report-context *,#content *,.report-footer *')){
    if(el.closest('svg')||![...el.childNodes].some(node=>node.nodeType===3&&node.textContent.trim())||!shown(el))continue;
    const style=getComputedStyle(el);
    if(/(hidden|clip)/.test(style.overflowX)&&style.textOverflow!=='ellipsis'&&el.scrollWidth>el.clientWidth+1)out.push(`text clipped (${el.scrollWidth}px in ${el.clientWidth}px): ${describe(el)}`);
    const box=el.getBoundingClientRect();
    if(style.position!=='fixed'&&!inScroller(el)&&(box.right>width+1||box.left<-1))out.push(`text off-screen [${Math.round(box.left)}–${Math.round(box.right)}px]: ${describe(el)}`);
  }
  for(const id of ['reportPrevious','reportNext']){
    const box=document.getElementById(id).getBoundingClientRect();
    if(box.top<0||box.bottom>height+1||box.right>width+1)out.push(`pager #${id} is not on screen (${Math.round(box.top)}–${Math.round(box.bottom)}px of ${height}px)`);
  }
  // Either the page scrolls as a document, or the report pane keeps at least a quarter of the screen.
  const content=document.getElementById('content').getBoundingClientRect();
  const documentScrolls=document.documentElement.scrollHeight>height+1;
  const pane=Math.min(content.bottom,height)-Math.max(content.top,0);
  if(!documentScrolls&&pane<height*.25)out.push(`report reading area is ${Math.round(pane)}px of a ${height}px screen`);
  return out;
}

test('every report view is part of the zoom and reflow audit',()=>{
  expect(VIEWS.length).toBe(18);
});

for(const mode of MODES)test.describe(mode.name,()=>{
  test.use({viewport:{width:mode.width,height:mode.height},deviceScaleFactor:mode.deviceScaleFactor});

  for(const view of VIEWS)test(`${view}: every subpage reflows without horizontal scroll or clipped controls`,async({page})=>{
    test.setTimeout(120000);
    await open(page,view);
    const titles=await page.evaluate(()=>reportState.pages.map(item=>item.title));
    const failures=[];
    for(let index=0;index<titles.length;index++){
      if(index)await goToPage(page,index);
      const problems=await page.evaluate(reflowProblems);
      if(problems.length)failures.push(`${view} · ${index+1}. ${titles[index]}\n  ${problems.join('\n  ')}`);
    }
    expect(failures,failures.join('\n\n')).toEqual([]);
  });

  test('help and evidence dialogs fit the screen and keep Close reachable',async({page})=>{
    const triggers=[['executive',0,'#reportHelp'],['executive',0,'#content [data-story-focus]'],['pnl',0,'#content [data-pnl-key]'],['pnl',1,'#content .kpi-info'],['cash-flow',0,'#content .sw-kpi']];
    for(const [view,index,selector] of triggers){
      await open(page,view,index);
      const trigger=page.locator(selector).first();
      await trigger.scrollIntoViewIfNeeded();await trigger.click();
      const dialog=page.locator('#reportDialog');
      await expect(dialog,`${view} ${selector}`).toHaveJSProperty('open',true);
      const fit=await dialog.evaluate(node=>{
        const box=node.getBoundingClientRect(),close=[...node.querySelectorAll('button')].find(button=>/close/i.test(`${button.textContent} ${button.getAttribute('aria-label')||''}`)).getBoundingClientRect();
        return {left:box.left,right:box.right,top:box.top,bottom:box.bottom,closeTop:close.top,closeBottom:close.bottom,closeRight:close.right,width:innerWidth,height:innerHeight,scrollable:node.scrollHeight<=node.clientHeight+1||/(auto|scroll)/.test(getComputedStyle(node).overflowY),page:document.documentElement.scrollWidth};
      });
      const label=`${view} ${selector}: ${JSON.stringify(fit)}`;
      expect(fit.left,label).toBeGreaterThanOrEqual(0);
      expect(fit.right,label).toBeLessThanOrEqual(fit.width);
      expect(fit.top,label).toBeGreaterThanOrEqual(0);
      expect(fit.bottom,label).toBeLessThanOrEqual(fit.height);
      expect(fit.closeTop,label).toBeGreaterThanOrEqual(0);
      expect(fit.closeBottom,label).toBeLessThanOrEqual(fit.height);
      expect(fit.closeRight,label).toBeLessThanOrEqual(fit.width);
      expect(fit.scrollable,label).toBe(true);
      expect(fit.page,label).toBeLessThanOrEqual(fit.width);
      await page.keyboard.press('Escape');
      await expect(dialog).toHaveJSProperty('open',false);
    }
  });
});

test('negative euro amounts use the typographic minus before the euro sign',async({page})=>{
  test.setTimeout(240000);
  await page.setViewportSize({width:1366,height:900});
  const found=[];
  for(const view of VIEWS){
    await open(page,view);
    const count=await page.evaluate(()=>reportState.pages.length);
    for(let index=0;index<count;index++){
      if(index)await goToPage(page,index);
      found.push(...await page.evaluate(where=>{
        // ASCII hyphen as a sign: "-€4.5m" or "€-4.5m" (a date such as "2025-09 €32m" is not a sign).
        const hyphen=/(^|[^\d])-\s?€|€\s?-\d/,out=[];
        const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
        for(let node=walker.nextNode();node;node=walker.nextNode())if(hyphen.test(node.textContent))out.push(`${where}: "${node.textContent.trim().slice(0,80)}"`);
        for(const el of document.querySelectorAll('[aria-label],[title]'))for(const name of ['aria-label','title']){const value=el.getAttribute(name);if(value&&hyphen.test(value))out.push(`${where}: @${name} "${value.slice(0,80)}"`);}
        return out;
      },`${view} · ${index+1}`));
    }
  }
  expect([...new Set(found)],found.join('\n')).toEqual([]);
});
