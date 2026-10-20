const {test,expect}=require('@playwright/test');

test('Global header reports the published close and control result, never a stale default',async({page})=>{
  await page.goto('/#view=executive');
  const published=await page.evaluate(async()=>(await(await fetch('/data/dashboard.json')).json()));
  const control=page.locator('#globalControl');
  await expect(page.locator('#globalPeriod')).toHaveText(published.meta.end_month);
  await expect(control).toHaveText(`Controls ${published.validation.passed?'passed':'failed'}`);
  await expect(control).not.toHaveClass(/pending/);
});

test('A failed close is shown as failed in red, including in report mode',async({page})=>{
  const response=await page.request.get('/data/dashboard.json');
  const dashboard=await response.json();
  dashboard.validation={...dashboard.validation,passed:false};
  await page.route('**/data/dashboard.json*',route=>route.fulfill({json:dashboard}));
  await page.goto('/#view=executive');
  const control=page.locator('#globalControl');
  await expect(control).toHaveText('Controls failed');
  await expect(control).toHaveClass(/failed/);
  const [red,green,blue]=(await control.evaluate(node=>getComputedStyle(node).color)).match(/\d+/g).map(Number);
  expect(red).toBeGreaterThan(green+80);
  expect(red).toBeGreaterThan(blue+80);
});

test('An unavailable dataset does not claim a close period or passed controls',async({page})=>{
  await page.route('**/data/dashboard.json*',route=>route.fulfill({status:503,body:'unavailable'}));
  await page.goto('/#view=executive');
  await expect(page.locator('#globalPeriod')).toHaveText('No close');
  await expect(page.locator('#globalControl')).toHaveText('Controls unavailable');
  await expect(page.locator('#globalControl')).toHaveClass(/pending/);
});

test('Executive driver tree places negative cash signs before the euro symbol',async({page})=>{
  await page.setViewportSize({width:1366,height:768});
  await page.goto('/#view=executive');
  const source=await page.evaluate(async()=>(await(await fetch('/data/dashboard.json')).json()).cash_flow.at(-1).investing_cash_flow);
  const investing=page.locator('.tower-drivers [data-story-view="operations-capex"] strong');
  const text=(Math.abs(source)/1e6).toFixed(1);
  const expected=`${source<0&&Number(text)!==0?'−':''}€${text}m`;
  await expect(investing).toHaveText(expected);
  await expect(page.locator('.tower-drivers')).not.toContainText('€-');
});
