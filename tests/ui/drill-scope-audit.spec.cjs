const {test,expect}=require('@playwright/test');

// Drill-through audit: an operating selection survives every in-page drill control,
// the in-app Back button and browser history, on every report in the navigation.
const SCOPE={entity:'US01',division:'Hardware'};
const DRILLS_PER_VIEW=3;

const route=page=>page.evaluate(()=>Object.fromEntries(new URLSearchParams(location.hash.slice(1))));
async function open(page,view,index=0){
  await page.goto(`/#view=${view}&page=${index}&entity=${SCOPE.entity}&division=${SCOPE.division}`);
  await page.waitForFunction(()=>typeof reportState!=='undefined'&&reportState.pages.length&&document.querySelector('#content').children.length);
}
async function expectScope(page,label){
  const hash=await route(page);
  expect(hash.entity,`${label}: hash entity`).toBe(SCOPE.entity);
  expect(hash.division,`${label}: hash division`).toBe(SCOPE.division);
  // The context line either shows the selection, explains the fixed scope, or names the kept selection.
  const context=await page.locator('#reportContext').textContent();
  expect(context,`${label}: context line`).toMatch(/Entity: |Division: |Group \/ fixed report scope/);
  expect(context,`${label}: selection named`).toContain(SCOPE.entity);
  expect(context,`${label}: selection named`).toContain(SCOPE.division);
  expect(context,`${label}: breadcrumb`).toContain(' › ');
}
async function expectHealthy(page,errors,label){
  expect(errors,`${label}: page errors`).toEqual([]);
  const problems=await page.evaluate(()=>{
    const content=document.getElementById('content'),text=content.innerText;
    const out=(text.match(/.{0,30}\b(?:undefined|NaN)\b.{0,20}/g)||[]).map(match=>`text: ${match}`);
    if(text.trim().length<80)out.push('content is nearly empty');
    for(const node of content.querySelectorAll('.panel,.story-composite,.sw-panel')){
      if(node.closest('[hidden],template')||!node.getClientRects().length)continue;
      if(!node.innerText.trim()&&!node.querySelector('svg,canvas,table'))out.push(`empty region: ${node.dataset.sourceSection||node.className}`);
    }
    for(const node of content.querySelectorAll('.empty'))if(!/not a loading error/.test(node.textContent))out.push(`unexplained empty state: ${node.textContent.trim().slice(0,60)}`);
    return out;
  });
  expect(problems,`${label}: rendered problems`).toEqual([]);
}
async function drillTargets(page){
  return page.evaluate(limit=>{
    const controls=[...document.querySelectorAll('#content [data-story-view],#content [data-open-pnl]')]
      .filter(node=>node.getClientRects().length&&!node.closest('[hidden],template,dialog')&&!node.disabled);
    const seen=new Set(),picked=[];
    // Same-view controls first: they used to re-render the current screen instead of drilling.
    const ordered=[...controls.filter(node=>node.dataset.storyView===state.view),...controls.filter(node=>node.dataset.storyView!==state.view)];
    for(const node of ordered){
      const target=node.dataset.storyView||'pnl';
      if(seen.has(target))continue;
      seen.add(target);picked.push({index:controls.indexOf(node),target,text:node.textContent.trim().slice(0,40)});
      if(picked.length===limit)break;
    }
    return picked;
  },DRILLS_PER_VIEW);
}
async function clickDrill(page,index){
  const before=await page.evaluate(()=>location.hash);
  await page.evaluate(i=>{
    const controls=[...document.querySelectorAll('#content [data-story-view],#content [data-open-pnl]')]
      .filter(node=>node.getClientRects().length&&!node.closest('[hidden],template,dialog')&&!node.disabled);
    controls[i].click();
  },index);
  await page.waitForFunction(previous=>location.hash!==previous,before);
}
async function expectOrigin(page,origin,label){
  await page.waitForFunction(({view,page:index})=>{const params=new URLSearchParams(location.hash.slice(1));return params.get('view')===view&&params.get('page')===index&&state.view===view;},origin);
  const hash=await route(page);
  expect(`${hash.view}/${hash.page}`,`${label}: returns to origin`).toBe(`${origin.view}/${origin.page}`);
  await expectScope(page,label);
}

test('every report keeps the operating scope through drill-through, Back and browser history',async({page})=>{
  test.setTimeout(420000);
  await page.setViewportSize({width:1366,height:768});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await open(page,'executive');
  const views=await page.evaluate(()=>ReportNavigation.areas.flatMap(area=>area.views));
  expect(views.length).toBe(18);
  let drilled=0,sameView=0;
  for(const view of views){
    await open(page,view);
    const origin=await route(page);
    expect(origin.view).toBe(view);
    await expectScope(page,view);
    await expectHealthy(page,errors,view);
    const targets=await drillTargets(page);
    for(const target of targets){
      const label=`${view} → ${target.text} (${target.target})`;
      drilled+=1;if(target.target===view)sameView+=1;
      await clickDrill(page,target.index);
      const destination=await route(page);
      expect(destination.view,`${label}: destination view`).toBe(target.target);
      if(target.target===view)expect(destination.page,`${label}: same-view drill must open a supporting screen`).not.toBe(origin.page);
      await expectScope(page,label);
      await expectHealthy(page,errors,label);
      await page.locator('#reportBack').click();
      await expectOrigin(page,origin,`${label} · in-app Back`);
      await clickDrill(page,target.index);
      await page.goBack();
      await expectOrigin(page,origin,`${label} · browser back`);
      await expectHealthy(page,errors,`${label} · after back`);
    }
    // Evidence inspectors (inline or as a dialog at laptop heights) carry their own drill route.
    await open(page,view);
    const focus=page.locator('#content [data-sw-focus]:visible').first();
    if(await focus.count()){
      await focus.click();
      const dialogRoute=page.locator('#reportDialog[open] [data-story-view]');
      const drill=await dialogRoute.count()?dialogRoute.first():page.locator('#swInspectorBody [data-story-view]:visible').first();
      const target=await drill.getAttribute('data-story-view'),label=`${view} → evidence inspector (${target})`;
      drilled+=1;if(target===view)sameView+=1;
      await drill.click();
      await page.waitForFunction(({view,page:index})=>{const params=new URLSearchParams(location.hash.slice(1));return params.get('view')!==view||params.get('page')!==index;},origin);
      const destination=await route(page);
      expect(destination.view,`${label}: destination view`).toBe(target);
      await expect(page.locator('#reportDialog')).toBeHidden();
      await expectScope(page,label);
      await expectHealthy(page,errors,label);
      await page.goBack();
      await expectOrigin(page,origin,`${label} · browser back`);
    }
  }
  // Guard against a silently shrinking sample.
  expect(drilled).toBeGreaterThanOrEqual(20);
  expect(sameView).toBeGreaterThanOrEqual(4);
  console.log(`drill-scope audit: ${drilled} drills, ${sameView} same-view`);
});

test('a selection broadened for one screen is kept for the next screen and the URL',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await open(page,'working-capital');
  const index=await page.evaluate(()=>reportState.pages.findIndex(item=>item.title==='Open customer advances'));
  expect(index).toBeGreaterThan(0);
  await open(page,'working-capital',index);
  await expect(page.locator('#reportContext')).toContainText('Selection adjusted');
  await expect(page.locator('#reportContext')).toContainText(`${SCOPE.entity} / ${SCOPE.division} is kept for other pages`);
  await expectScope(page,'broadened screen');
  await page.locator('#reportPrevious').click();
  await expect(page.locator('#reportContext')).not.toContainText('Selection adjusted');
  expect(await page.evaluate(()=>[state.entity,state.division])).toEqual([SCOPE.entity,SCOPE.division]);
  await expectScope(page,'previous screen');
  // An explicit change on the broadened screen wins over the kept selection.
  await page.locator('#reportNext').click();
  await expect(page.locator('#reportContext')).toContainText('Selection adjusted');
  await page.locator('#reportReset').click();
  await page.locator('#reportPrevious').click();
  expect(await page.evaluate(()=>[state.entity,state.division])).toEqual(['all','all']);
  expect(errors).toEqual([]);
});

test('mixed-scope screens name their fixed sections instead of claiming no filter applies',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  await open(page,'business-drivers');
  const index=await page.evaluate(()=>reportState.pages.findIndex(item=>item.title.includes('Prepayment funding by business')));
  await open(page,'business-drivers',index);
  const context=page.locator('#reportContext');
  await expect(context).toContainText('Group / fixed: Group prepayment trend');
  await expect(context).not.toContainText('no entity or division filter applies');
  await expect(page.locator('#entityFilter')).toBeVisible();
  await expect(page.locator('#content .empty')).toHaveCount(0);
});
