const {test,expect}=require('@playwright/test');

test('Performance Review tells the controlled lifecycle story without fake history',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=performance-review&page=2');
  await expect(page.locator('.plv-status')).toBeVisible();
  await expect(page.locator('.plv-composition')).toHaveAttribute('aria-label','Status composition: 3 Open, 5 Closed');
  await expect(page.locator('.plv-first-snapshot')).toContainText('First controlled snapshot');
  await expect(page.locator('.plv-overdue-clear')).toContainText('No overdue actions at the 2026-08 close');
  await expect(page.locator('.plv-due-row')).toHaveCount(3);
  await expect(page.locator('#entityFilter').locator('..')).toBeVisible();
  for(const summary of await page.locator('.plv-records>summary').all())await expect(summary).toBeInViewport();
  await page.screenshot({path:'test-results/lifecycle-story-desktop.png',fullPage:true});
  await page.locator('[data-plv-register]').click();
  await expect(page.locator('#reportPageSelect')).toHaveValue('3');
});

test('lifecycle page remains separate and reachable on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=performance-review&page=2');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await expect(page.locator('.plv-first-snapshot')).toBeVisible();
  await page.screenshot({path:'test-results/lifecycle-story-mobile.png',fullPage:true});
  const regions=page.getByRole('navigation',{name:'Dashboard regions'});
  await regions.getByRole('button').nth(1).click();
  await expect(page.locator('.plv-overdue-clear')).toBeVisible();
  await expect(page.locator('.plv-due-row')).toHaveCount(3);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/lifecycle-overdue-mobile.png',fullPage:true});
});

test('lifecycle and due-date panels share an honest entity scope',async({page})=>{
  await page.goto('/#view=performance-review&page=2&entity=US01&division=all');
  await expect(page.locator('#reportContext')).toContainText('Entity: US01');
  await expect(page.locator('.plv-status .plv-heading').first()).toContainText('1 management actions');
  await expect(page.locator('.plv-composition')).not.toHaveAttribute('aria-label','Status composition: 3 Open, 5 Closed');
  await expect(page.locator('.plv-due')).toBeVisible();
});
