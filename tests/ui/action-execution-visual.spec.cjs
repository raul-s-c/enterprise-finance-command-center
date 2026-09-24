const {test,expect}=require('@playwright/test');

test('action execution shows source-tied stages and monthly impact',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=action-execution&page=0');
  await expect(page.locator('.aev-stage')).toHaveCount(4);
  await expect(page.locator('.aev-stage').first()).toContainText('18');
  await expect(page.locator('.aev-plan')).toHaveCount(3);
  await expect(page.locator('.aev-bar')).toHaveCount(12);
  const expected=await page.evaluate(()=>{const row=scopedActionBridge()[0];return new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(row.action_ebit_impact)});
  await expect(page.locator('[data-aev-ebit]')).toHaveText(expected);
  await expect(page.locator('.action-story-indicators>.kpi')).toHaveCount(4);
  await page.screenshot({path:'test-results/action-execution-desktop.png',fullPage:true});
  await expect(page.locator('[data-aev-selected-month]')).toContainText('2026-09');
  await page.locator('.aev-bar').last().click();
  await expect(page.locator('[data-aev-selected-month]')).toContainText('2027-08');
  await expect(page.locator('.aev-bar').last()).toHaveAttribute('aria-pressed','true');
  await page.locator('.aev-plan').first().locator('summary').click();
  await expect(page.locator('.aev-plan').first()).toContainText('Source review');
  await page.locator('.aev-records').first().locator('summary').click();
  await expect(page.locator('.aev-records').first().locator('table')).toBeVisible();
  for(const width of [1024,390]){
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  }
  await page.screenshot({path:'test-results/action-execution-mobile.png',fullPage:true});
});

test('benefit tracking explains why actual recognition is zero at this close',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=action-execution&page=1');
  await expect(page.locator('.aev-benefit-summary')).toContainText('0 of 18');
  await expect(page.locator('.aev-trigger')).toHaveCount(5);
  await expect(page.locator('.aev-recognition')).toContainText('2026-08');
  await expect(page.locator('.aev-recognition')).toContainText('2026-09');
  await expect(page.locator('.aev-actual-zero')).toBeVisible();
  await expect(page.locator('.aev-actual-history')).toContainText('No action impact has entered actuals yet');
  await page.screenshot({path:'test-results/action-execution-recognition.png',fullPage:true});
});
