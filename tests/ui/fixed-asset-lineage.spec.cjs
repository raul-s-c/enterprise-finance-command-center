const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('CAPEX project register traces cash, CIP, PPE and modeled depreciation on mobile',async({page})=>{
  await page.route('**/data/dashboard.json*',route=>{
    const fixture=JSON.parse(JSON.stringify(published));
    fixture.meta.version='0.25.0';
    fixture.meta.fixed_asset_project_count=1;
    return route.fulfill({json:fixture});
  });
  await page.route('**/data/fixed_asset_detail.json*',route=>route.fulfill({json:{
    month:published.meta.end_month,currency:'EUR',
    evidence_basis:'Project spend and CIP-to-PPE transfer tie to posted journal IDs. Project depreciation is reconstructed from approved budget and useful life because depreciation posts in one aggregate entity journal; opening PPE remains an entity-level pool.',
    project_count:1,event_count:2,
    projects:[{
      month:published.meta.end_month,project:'CAPEX-TEST-01',project_name:'Brno assembly cell',entity:'CZ01',division:'Hardware',status:'In service',
      budget:1000000,cash_spend_ltd:1000000,cip_closing:0,go_live_month:'2026-01',go_live_transfer_ltd:1000000,gross_ppe:1000000,
      useful_life_months:120,depreciation_months:8,depreciation_ltd_modeled:66666.67,depreciation_current_month_modeled:8333.33,
      net_book_value:933333.33,project_carrying_value:933333.33,capacity_increase_pct:.16,
      depreciation_journal_id:`DEP-${published.meta.end_month}-CZ01`,
      depreciation_basis:'Project depreciation reconstructed from budget / useful life; source journal is aggregated by entity',
    }],
    events:[
      {month:'2025-04',project:'CAPEX-TEST-01',project_name:'Brno assembly cell',entity:'CZ01',division:'Hardware',event:'SPEND',amount:1000000,journal_id:'CAPEX-2025-04-CAPEX-TEST-01',debit_account:'1510_CIP',credit_account:'1000_CASH'},
      {month:'2026-01',project:'CAPEX-TEST-01',project_name:'Brno assembly cell',entity:'CZ01',division:'Hardware',event:'GO_LIVE',amount:1000000,journal_id:'GOLIVE-2026-01-CAPEX-TEST-01',debit_account:'1500_PPE',credit_account:'1510_CIP'},
    ],
  }}));
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=operations-capex&page=0');
  await page.waitForLoadState('networkidle');
  await page.evaluate(()=>{data.meta.version='0.25.0';data.meta.fixed_asset_project_count=1;state.view='operations-capex';reportState.page=0;render();});
  const workspace=page.locator('.statement-workspace');
  await expect(workspace).toBeVisible();
  const assetRegister=workspace.locator('[data-sw-fixed-assets]');
  await expect(assetRegister).toBeVisible();
  await expect(assetRegister).toHaveAttribute('aria-label','Project asset register');
  await assetRegister.click();
  const dialog=page.locator('#reportDialog');
  await expect(dialog.locator('#reportDialogTitle')).toHaveText('CAPEX · project-to-asset lifecycle');
  await expect(dialog).toContainText(/opening PPE remains an entity-level pool/i);
  await dialog.getByRole('button',{name:/Brno assembly cell/}).click();
  await expect(dialog).toContainText('CAPEX-2025-04-CAPEX-TEST-01');
  await expect(dialog).toContainText('GOLIVE-2026-01-CAPEX-TEST-01');
  await expect(dialog).toContainText('No project-specific depreciation journal or individual asset ID is claimed.');
  expect(await dialog.evaluate(node=>node.scrollWidth<=node.clientWidth+1)).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:'test-results/fixed-asset-project-lineage-mobile.png'});
});
