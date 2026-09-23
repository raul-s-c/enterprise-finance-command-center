const {test,expect}=require('@playwright/test');

test('Executive narrative teaches result, scoped drivers and group outlook through evidence routes',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width:1366,height:768});
  await page.goto('/#view=executive');
  const narrative=page.locator('.story-narrative');
  await expect(narrative).toBeVisible();
  await expect(narrative).toContainText('RESULT');
  await expect(narrative).toContainText('WHY IT MOVED · All entities · All divisions');
  await expect(narrative).toContainText('Review source · price_volume_mix.csv');
  await expect(narrative).toContainText('GROUP OUTLOOK');
  await expect(narrative).toContainText('FY EBIT outlook');

  await page.locator('#entityFilter').selectOption('US01');
  await page.locator('#divisionFilter').selectOption('Hardware');
  await expect(narrative).toContainText('Selected scope · US01 · Hardware');
  await expect(narrative).toContainText('WHY IT MOVED · US01 · Hardware');
  await expect(narrative).toContainText('GROUP OUTLOOK');
  await expect(page.locator('html')).toHaveJSProperty('scrollWidth',await page.evaluate(()=>innerWidth));

  await narrative.getByRole('button',{name:/Open monthly review/}).click();
  await expect(page.locator('#viewTitle')).toHaveText('Performance Review');
  await expect(page.locator('#entityFilter')).toHaveValue('US01');
  await expect(page.locator('#divisionFilter')).toHaveValue('Hardware');

  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=executive&entity=US01&division=Hardware');
  await expect(page.locator('.story-narrative')).toBeVisible();
  await expect(page.locator('.story-narrative')).toContainText('Selected scope · US01 · Hardware');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  expect(errors).toEqual([]);
});
