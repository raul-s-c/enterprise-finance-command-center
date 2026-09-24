const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('action execution shows source-tied stages and monthly impact',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=action-execution&page=0');
  await expect(page.locator('.aev-stage')).toHaveCount(4);
  const stageCount=published.management_action_plans.filter(row=>row.execution_status==='Approved').length;
  await expect(page.locator('.aev-stage').first()).toContainText(String(stageCount));
  await expect(page.locator('.aev-plan')).toHaveCount(Math.min(3,published.management_action_plans.length));
  await expect(page.locator('.aev-bar')).toHaveCount(12);
  const expected=await page.evaluate(()=>{const row=scopedActionBridge()[0];return new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(row.action_ebit_impact)});
  await expect(page.locator('[data-aev-ebit]')).toHaveText(expected);
  await expect(page.locator('.action-story-indicators>.kpi')).toHaveCount(4);
  for(const summary of await page.locator('.aev-records>summary').all())await expect(summary).toBeInViewport();
  await page.screenshot({path:'test-results/action-execution-desktop.png',fullPage:true});
  const firstMonth=await page.locator('.aev-bar').first().getAttribute('data-aev-month');
  const lastMonth=await page.locator('.aev-bar').last().getAttribute('data-aev-month');
  await expect(page.locator('[data-aev-selected-month]')).toContainText(firstMonth);
  await page.locator('.aev-bar').last().click();
  await expect(page.locator('[data-aev-selected-month]')).toContainText(lastMonth);
  await expect(page.locator('.aev-bar').last()).toHaveAttribute('aria-pressed','true');
  await page.locator('.aev-plan').first().locator('summary').click();
  await expect(page.locator('.aev-plan').first()).toContainText('Source review');
  await page.locator('.aev-records').first().locator('summary').click();
  await expect(page.locator('.aev-records').first().locator('table')).toBeVisible();
  for(const width of [1024,390]){
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  }
  const firstPageFit=await page.locator('.story-composite').first().evaluate(el=>el.getBoundingClientRect().bottom<=el.nextElementSibling.getBoundingClientRect().top+1);
  expect(firstPageFit).toBe(true);
  await page.screenshot({path:'test-results/action-execution-mobile.png',fullPage:true});
});

test('benefit tracking explains why actual recognition is zero at this close',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=action-execution&page=1');
  const currentBenefits=published.management_action_benefits.filter(row=>row.snapshot_month===published.meta.end_month);
  const improving=currentBenefits.filter(row=>Number(row.observed_metric_improvement)>0).length;
  await expect(page.locator('.aev-benefit-summary')).toContainText(`${improving} of ${currentBenefits.length}`);
  await expect(page.locator('.aev-trigger')).toHaveCount(5);
  await expect(page.locator('.aev-recognition')).toContainText(published.meta.end_month);
  const next=published.management_action_plans.map(row=>row.effective_month).filter(month=>month>published.meta.end_month).sort()[0];
  if(next)await expect(page.locator('.aev-recognition')).toContainText(next);
  const actualRows=published.management_action_actual_impact.filter(row=>row.month<=published.meta.end_month);
  if(actualRows.every(row=>Math.abs(Number(row.action_ebit_impact)||0)<.005)){
    await expect(page.locator('.aev-actual-zero')).toBeVisible();
    await expect(page.locator('.aev-actual-history')).toContainText('No action impact has entered actuals yet');
  }else await expect(page.locator('.aev-actual-bars')).toBeVisible();
  for(const summary of await page.locator('.aev-records>summary').all())await expect(summary).toBeInViewport();
  await page.screenshot({path:'test-results/action-execution-recognition.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await expect(page.locator('.aev-benefit-summary')).toBeVisible();
  await expect(page.locator('.aev-recognition')).toBeVisible();
  const mobileFit=await page.locator('.aev-benefits').evaluate(el=>{const panel=el.closest('.panel').getBoundingClientRect(),summary=el.querySelector('.aev-records summary').getBoundingClientRect(),next=el.closest('.story-composite').nextElementSibling.getBoundingClientRect();return {evidenceInside:summary.bottom<=panel.bottom+1,panelsSeparate:panel.bottom<=next.top+1}});
  expect(mobileFit.evidenceInside).toBe(true);
  expect(mobileFit.panelsSeparate).toBe(true);
  await page.screenshot({path:'test-results/action-execution-recognition-mobile.png',fullPage:true});
});

test('Action Execution ignores hidden operating filters on its fixed group scope',async({page})=>{
  await page.goto('/#view=action-execution&page=0');
  await expect(page.locator('.action-story-indicators .kpi')).toHaveCount(4);
  const groupIndicators=await page.locator('.action-story-indicators .kpi').allTextContents();
  await page.goto('/#view=action-execution&page=0&entity=US01&division=Hardware');
  await expect(page.locator('#reportContext')).toContainText('Group / fixed report scope');
  await expect(page.locator('.aev-stage').first()).toContainText(String(published.management_action_plans.filter(row=>row.execution_status==='Approved').length));
  await expect(page.locator('.action-story-indicators .kpi')).toHaveText(groupIndicators);
});
