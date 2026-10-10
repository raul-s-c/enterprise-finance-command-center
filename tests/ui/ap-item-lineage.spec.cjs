const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('AP contribution opens source-accrual evidence and modeled reductions on mobile',async({page})=>{
  const supplier=(published.ap_supplier_aging||[]).find(row=>Number(row.total_ap)>0);
  expect(supplier).toBeTruthy();
  const scope={month:published.meta.end_month,entity:supplier.entity,division:supplier.division,supplier:supplier.supplier,supplier_name:supplier.supplier_name,supplier_category:supplier.supplier_category};
  const items=[{
    ...scope,month:published.meta.end_month,source_item_id:'ACCRUAL-TEST-001',accrual_journal_id:'ACCRUAL-TEST-001',accrual_type:'factory cost',accrual_month:'2026-08',
    accrual_amount:15000,reductions_applied_ltd:5000,open_amount:10000,payment_terms_days:45,age_days:60,overdue_days:15,
    aging_bucket:'overdue_1_30',supplier_criticality:4,single_source:false,evidence_basis:'Synthetic source accrual journal ID; reductions modeled from aggregate AP postings, not supplier invoice or remittance evidence',
  }];
  const dashboard=structuredClone(published);
  dashboard.meta.version='0.24.0';
  dashboard.meta.ap_item_count=1;
  await page.route('**/data/dashboard.json*',route=>route.fulfill({json:dashboard}));
  await page.route('**/data/ap_item_detail.json*',route=>route.fulfill({json:{
    month:published.meta.end_month,currency:'EUR',allocation_basis:'Modeled oldest-accrual allocation of posted aggregate AP reductions. Source IDs are accrual journal IDs, not supplier invoice numbers.',item_count:1,application_count:1,items,
    applications:[{application_month:'2026-09',entity:scope.entity,posted_division:scope.division,supplier:scope.supplier,supplier_name:scope.supplier_name,accrual_journal_id:'ACCRUAL-TEST-001',reduction_journal_id:'PAY-2026-09-US01-Hardware',reduction_type:'supplier_payment',applied_amount:5000,allocation_basis:'Modeled allocation of aggregate entity/division AP reduction'}],
  }}));
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=working-capital&page=3');
  const explorer=page.locator('.contribution-explorer[data-contribution="ap"]');
  await expect(explorer).toBeVisible();
  await explorer.getByRole('button',{name:'Open source accrual evidence'}).click();
  const dialog=page.locator('#reportDialog');
  await expect(dialog.locator('#reportDialogTitle')).toHaveText('Open payables · source accrual evidence');
  await expect(dialog.locator('.cx-invoice-summary')).toContainText('€10,000.00');
  await expect(dialog.locator('.cx-invoice-basis')).toContainText('not supplier invoice numbers');
  await dialog.getByRole('button',{name:'Trace source and reductions'}).click();
  await expect(dialog.locator('#reportDialogTitle')).toHaveText('Source accrual trace');
  await expect(dialog.locator('#reportDialogBody')).toContainText('ACCRUAL-TEST-001');
  await expect(dialog.locator('#reportDialogBody')).toContainText('PAY-2026-09-US01-Hardware');
  await expect(dialog.locator('#reportDialogBody')).toContainText('no remittance or invoice matching is claimed');
  expect(await dialog.evaluate(node=>node.scrollWidth<=node.clientWidth+1)).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:'test-results/ap-source-accrual-mobile.png'});
});
