const {test,expect}=require('@playwright/test');

test('Close Journey balances its input and control panels at laptop height',async({page})=>{
  await page.setViewportSize({width:1280,height:800});
  await page.goto('/#view=close-journey');
  const workspace=page.locator('.cj-workspace');
  await expect(workspace).toBeVisible();

  for(const selector of ['.cj-io','.cj-proof-chain']){
    const panel=page.locator(selector);
    await expect(panel).toBeVisible();
    const geometry=await panel.evaluate(element=>{
      const section=element.closest('section');
      const panelRect=element.getBoundingClientRect();
      const sectionRect=section.getBoundingClientRect();
      const paddingBottom=parseFloat(getComputedStyle(section).paddingBottom)||0;
      return {
        bottomGap:sectionRect.bottom-paddingBottom-panelRect.bottom,
        panelHeight:panelRect.height,
        sectionHeight:sectionRect.height
      };
    });
    expect(geometry.panelHeight,selector).toBeGreaterThan(0);
    expect(
      geometry.bottomGap,
      `${selector} should use the lower panel area at 1280x800: ${JSON.stringify(geometry)}`
    ).toBeGreaterThanOrEqual(-1);
    expect(
      geometry.bottomGap,
      `${selector} should be vertically balanced at 1280x800: ${JSON.stringify(geometry)}`
    ).toBeLessThanOrEqual(24);
  }
});
