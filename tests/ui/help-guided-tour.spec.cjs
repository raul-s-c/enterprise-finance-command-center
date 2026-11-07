const {test,expect}=require('@playwright/test');

test('contextual Help gives a first-time reader a direct route into the guided close tour',async({page},testInfo)=>{
  for(const viewport of [{width:1366,height:768},{width:390,height:844}]){
    await page.setViewportSize(viewport);
    await page.goto('/#view=executive');
    await page.locator('#reportHelp').click();

    const dialog=page.locator('#reportDialog');
    const tour=dialog.getByRole('button',{name:'Start the close tour'});
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('New to Aureon Finance?');
    await expect(tour).toBeVisible();
    if(viewport.width===1366)await testInfo.attach('help-tour-entry',{body:await page.screenshot(),contentType:'image/png'});
    const buttonBounds=await tour.boundingBox();
    expect(buttonBounds.x).toBeGreaterThanOrEqual(0);
    expect(buttonBounds.x+buttonBounds.width).toBeLessThanOrEqual(viewport.width+1);

    await tour.focus();
    await page.keyboard.press('Enter');
    await expect(dialog).toBeHidden();
    await expect(page).toHaveURL(/#view=close-journey/);
    await expect(page.getByRole('heading',{name:'From business activity to management action'})).toBeVisible();
    await expect(page.locator('.cj-steps [data-cj-step="0"]')).toBeFocused();
    await expect(page.locator('.cj-guide')).toContainText('1 of 8 · Drivers');
    if(viewport.width===390)await testInfo.attach('guided-close-tour-mobile',{body:await page.screenshot(),contentType:'image/png'});
    await page.locator('#cj-next').click();
    await expect(page.locator('.cj-guide')).toContainText('2 of 8 · Transactions');
    await page.locator('.cj-evidence-row').first().click();
    await expect(page).toHaveURL(/#view=working-capital/);
    await page.locator('#reportHelp').click();
    await page.locator('#reportDialog').getByRole('button',{name:'Start the close tour'}).click();
    await expect(page.locator('.cj-guide')).toContainText('1 of 8 · Drivers');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
});
