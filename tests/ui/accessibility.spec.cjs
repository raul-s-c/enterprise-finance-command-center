const {test,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const {areas}=require('../../web/report-navigation.js');

// WCAG 2.1 AA audit (roadmap M5): axe on every subpage of every report, keyboard-only
// navigation with a visible focus ring, evidence dialogs, chart names and non-colour cues.
// No axe rule is disabled: every finding is fixed at its shared source or marked up correctly.
const WCAG_TAGS=['wcag2a','wcag2aa','wcag21a','wcag21aa'];
const VIEWPORTS=[{name:'laptop',width:1366,height:768},{name:'phone',width:375,height:812}];
const VIEWS=areas.flatMap(area=>area.views);

async function open(page,view,index=0){
  await page.goto(`/#view=${view}&page=${index}`);
  await page.waitForFunction(v=>typeof reportState!=='undefined'&&state.view===v&&reportState.pages.length&&document.querySelector('#content').children.length,view);
}
async function goToPage(page,index){
  await page.evaluate(i=>reportNavigate(i),index);
  await page.waitForFunction(i=>reportState.page===i&&document.querySelector('#content').children.length,index);
}
const describe=violations=>violations.map(v=>`${v.impact} ${v.id}: ${v.help}\n${v.nodes.slice(0,5).map(node=>`  ${node.target.join(' ')} · ${(node.failureSummary||'').split('\n').slice(1).join(' ').trim()}`).join('\n')}`).join('\n');

test('every report view is part of the audit',()=>{
  expect(VIEWS.length).toBe(18);
  expect(new Set(VIEWS).size).toBe(VIEWS.length);
});

for(const viewport of VIEWPORTS)test.describe(`axe WCAG 2.1 AA · ${viewport.name} ${viewport.width}x${viewport.height}`,()=>{
  for(const view of VIEWS)test(`${view}: no serious or critical violations on any subpage`,async({page})=>{
    test.setTimeout(150000);
    await page.setViewportSize({width:viewport.width,height:viewport.height});
    await open(page,view);
    const pages=await page.evaluate(()=>reportState.pages.map(item=>item.title));
    const failures=[];
    for(let index=0;index<pages.length;index++){
      if(index)await goToPage(page,index);
      const {violations}=await new AxeBuilder({page}).withTags(WCAG_TAGS).analyze();
      const blocking=violations.filter(v=>v.impact==='serious'||v.impact==='critical');
      if(blocking.length)failures.push(`${view} · ${index+1}. ${pages[index]}\n${describe(blocking)}`);
    }
    expect(failures,failures.join('\n\n')).toEqual([]);
  });
});

// Keyboard: Tab from the top of the page and record where focus lands.
async function tabUntil(page,targets,limit=260){
  await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});
  await page.locator('body').focus();
  const reached={},missing=new Set(Object.keys(targets)),trail=[];
  for(let step=0;step<limit&&missing.size;step++){
    await page.keyboard.press('Tab');
    const hit=await page.evaluate(selectors=>{
      const el=document.activeElement;if(!el||el===document.body)return {name:'body'};
      const name=`${el.tagName.toLowerCase()}${el.id?`#${el.id}`:''}.${(el.getAttribute('class')||'').split(' ')[0]}`;
      const key=Object.entries(selectors).find(([,selector])=>el.matches(selector))?.[0];if(!key)return {name};
      // A text field may draw its ring on the wrapping field box (:focus-within).
      const ringOf=node=>{const style=getComputedStyle(node);return style.outlineStyle!=='none'&&(parseFloat(style.outlineWidth)||0)>=1||style.boxShadow!=='none';};
      const box=el.closest('.global-search'),style=getComputedStyle(box||el);
      return {name,key,visible:el.matches(':focus-visible'),ring:ringOf(el)||Boolean(box&&ringOf(box)),outline:`${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}`};
    },targets);
    trail.push(hit.name);
    if(hit.key&&missing.has(hit.key)){reached[hit.key]=hit;missing.delete(hit.key);}
  }
  return {reached,missing:[...missing],trail};
}

const KEYBOARD_TARGETS={
  laptop:{
    search:'#globalSearch',
    areaNavigation:'#nav [data-area]',
    report:'#reportModules [data-view]',
    entityFilter:'#entityFilter',
    divisionFilter:'#divisionFilter',
    subpage:'#reportTabs [data-page]',
    chartPoint:'#content [data-month]',
    next:'#reportNext'
  },
  phone:{
    search:'#globalSearch',
    area:'#reportArea',
    report:'#reportModule',
    entityFilter:'#entityFilter',
    divisionFilter:'#divisionFilter',
    subpage:'#reportPageSelect',
    chartPoint:'#content [data-month]',
    next:'#reportNext'
  }
};

for(const viewport of VIEWPORTS)test(`keyboard only · ${viewport.name}: Tab reaches every control with a visible focus ring`,async({page})=>{
  await page.setViewportSize({width:viewport.width,height:viewport.height});
  await open(page,'executive');
  // The first chart point is an SVG month (phones, tall screens) or a mini-trend month button (short laptops).
  const {reached,missing,trail}=await tabUntil(page,KEYBOARD_TARGETS[viewport.name]);
  expect(missing,`not reachable with Tab: ${missing.join(', ')}
Tab order: ${trail.join(' → ')}`).toEqual([]);
  for(const [key,hit] of Object.entries(reached)){
    expect(hit.visible,`${key} matches :focus-visible`).toBe(true);
    expect(hit.ring,`${key} shows a focus ring (${hit.outline})`).toBe(true);
  }
  // Next is operable from the keyboard.
  await page.locator('#reportNext').focus();
  await page.keyboard.press('Enter');
  await page.waitForFunction(()=>reportState.page===1);
});

async function expectDialogRoundTrip(page,trigger,label){
  await trigger.focus();
  await expect(trigger,`${label}: trigger focused`).toBeFocused();
  await page.keyboard.press('Enter');
  const dialog=page.locator('#reportDialog');
  await expect(dialog,`${label}: dialog opens`).toHaveJSProperty('open',true);
  expect(await page.evaluate(()=>document.getElementById('reportDialog').contains(document.activeElement)),`${label}: focus moves into the dialog`).toBe(true);
  await expect(page.locator('#reportDialogTitle'),`${label}: dialog has a title`).not.toHaveText('');
  await page.keyboard.press('Escape');
  await expect(dialog,`${label}: Escape closes`).toHaveJSProperty('open',false);
  await expect(trigger,`${label}: focus returns to the trigger`).toBeFocused();
}

test('evidence dialogs open from the keyboard, close with Escape and return focus',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  await open(page,'executive');
  await expectDialogRoundTrip(page,page.locator('#content [data-story-focus]').first(),'executive KPI evidence');
  await expectDialogRoundTrip(page,page.locator('#content [data-month]').first(),'month evidence');
  await open(page,'pnl',1);
  await expectDialogRoundTrip(page,page.locator('#content .kpi-info').first(),'KPI definition');
  await open(page,'pnl');
  await expectDialogRoundTrip(page,page.locator('#content [data-pnl-key]').first(),'P&L line evidence');
  await open(page,'cash-flow');
  await expectDialogRoundTrip(page,page.locator('#content .sw-kpi').first(),'statement calculation evidence');
  await expectDialogRoundTrip(page,page.locator('#reportHelp'),'help');
});

test('every chart or SVG exposed with a role has an accessible name, and variance colour always has a non-colour cue',async({page})=>{
  test.setTimeout(240000);
  await page.setViewportSize({width:1366,height:768});
  await open(page,'executive');
  const problems=[];
  for(const view of VIEWS){
    await open(page,view);
    const count=await page.evaluate(()=>reportState.pages.length);
    for(let index=0;index<count;index++){
      if(index)await goToPage(page,index);
      problems.push(...await page.evaluate(({view,index})=>{
        const out=[],where=`${view} · ${index+1}. ${reportState.pages[index].title}`;
        const visible=el=>el.getClientRects().length&&!el.closest('[aria-hidden="true"],[hidden],template');
        const named=el=>{
          const labelled=(el.getAttribute('aria-labelledby')||'').split(/\s+/).filter(Boolean).map(id=>document.getElementById(id)?.textContent||'').join(' ');
          return [el.getAttribute('aria-label'),labelled,el.querySelector(':scope>title')?.textContent].some(text=>text&&text.trim());
        };
        for(const el of document.querySelectorAll('#content svg[role],#content [role="img"],#content [role="figure"]')){
          if(!el.closest('[aria-hidden="true"]')&&!named(el))out.push(`${where}: ${el.tagName.toLowerCase()}.${el.getAttribute('class')||''} role=${el.getAttribute('role')} has no accessible name`);
        }
        for(const svg of document.querySelectorAll('#content svg:not([role]):not([aria-hidden="true"])')){
          if(!svg.closest('[aria-hidden="true"],[role="img"]')&&!named(svg)&&!svg.closest('button,a,[role="button"]'))out.push(`${where}: svg.${svg.getAttribute('class')||''} is neither named nor hidden`);
        }
        // Favorable/unfavorable colour is backed by a sign, a word or a mark in the same text.
        const cue=/[+\-−–]|✓|!|favou?rable|adverse|unfavou?rable|recomputed|reconciled|better|worse|over|under|pass|fail|increase|decrease|gain|loss|—/i;
        for(const el of document.querySelectorAll('#content .favorable,#content .unfavorable,#content .is-favorable,#content .is-adverse,#content .good,#content .bad')){
          if(!visible(el)||['rect','path','i','b'].includes(el.tagName.toLowerCase()))continue;
          const style=getComputedStyle(el);if(style.color===getComputedStyle(el.parentElement).color)continue;
          const before=getComputedStyle(el,'::before').content,text=`${/^".*"$/.test(before)?before.slice(1,-1):''}${el.textContent}`.trim();
          if(text&&!cue.test(text))out.push(`${where}: "${text.slice(0,50)}" (${el.className}) relies on colour only`);
        }
        return out;
      },{view,index}));
    }
  }
  expect(problems,problems.join('\n')).toEqual([]);
});
