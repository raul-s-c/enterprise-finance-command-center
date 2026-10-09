const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('AR contribution opens reconciled invoice evidence and modeled source applications on mobile',async({page})=>{
  const totals=new Map();
  for(const row of published.credit_loss_detail||[])totals.set(row.entity,(totals.get(row.entity)||0)+row.gross_ar);
  const selectedEntity=[...totals].sort((a,b)=>Math.abs(b[1])-Math.abs(a[1]))[0]?.[0];
  const customer=(published.credit_loss_detail||[]).find(row=>row.entity===selectedEntity);
  expect(customer).toBeTruthy();
  const scope={month:published.meta.end_month,entity:customer.entity,division:customer.division,customer:customer.customer,customer_name:customer.customer_name,customer_segment:customer.customer_segment};
  const invoices=[
    {...scope,product:'HW-EDGE-01',invoice_id:'AR-TEST-001',invoice_month:'2026-07',invoice_amount:18000,cash_applied_ltd:9000,advance_applied_ltd:0,open_amount:9000,credit_loss_allowance:200,net_ar:8800,risk_multiplier:1.1,payment_terms_days:30,invoice_age_days:90,overdue_days:60,aging_bucket:'overdue_31_60',risk_score:2.1,evidence_basis:'Synthetic invoice source ID; modeled allocation of posted AR credits, not bank matched'},
    {...scope,product:'HW-EDGE-02',invoice_id:'AR-TEST-002',invoice_month:'2026-08',invoice_amount:12000,cash_applied_ltd:0,advance_applied_ltd:2000,open_amount:10000,credit_loss_allowance:300,net_ar:9700,risk_multiplier:1.1,payment_terms_days:30,invoice_age_days:60,overdue_days:30,aging_bucket:'overdue_1_30',risk_score:2.1,evidence_basis:'Synthetic invoice source ID; modeled allocation of posted AR credits, not bank matched'},
  ];
  const dashboard=structuredClone(published);
  dashboard.meta.version='0.26.0';
  dashboard.meta.ar_invoice_count=invoices.length;
  await page.route('**/data/dashboard.json*',route=>route.fulfill({json:dashboard}));
  await page.route('**/data/ar_invoice_detail.json*',route=>route.fulfill({json:{month:published.meta.end_month,currency:'EUR',allocation_basis:'Modeled risk-aware oldest-receivable allocation of posted aggregate AR credits.',invoice_count:2,application_count:2,invoices,applications:[
    {application_month:'2026-08',entity:scope.entity,division:scope.division,customer:scope.customer,invoice_id:'AR-TEST-001',source_journal_id:'COLL-2026-08-US01-Hardware',allocation_type:'cash_collection',applied_amount:9000,allocation_basis:'Modeled risk-aware oldest receivable'},
    {application_month:'2026-09',entity:scope.entity,division:scope.division,customer:scope.customer,invoice_id:'AR-TEST-002',source_journal_id:'CONTRACT-APPLY-2026-09-US01-C1-HW',allocation_type:'customer_advance_application',applied_amount:2000,allocation_basis:'Modeled oldest open customer invoice'},
  ]}}));
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=working-capital&page=1');
  const explorer=page.locator('.contribution-explorer[data-contribution="ar"]');
  await expect(explorer).toBeVisible();
  await explorer.getByRole('button',{name:'Open invoice evidence'}).click();
  const dialog=page.locator('#reportDialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('#reportDialogTitle')).toHaveText('Open receivables · invoice evidence');
  await expect(dialog.locator('.cx-invoice-summary')).toContainText('2');
  await expect(dialog.locator('.cx-invoice-summary')).toContainText('€19,000.00');
  await expect(dialog.locator('.cx-invoice-summary')).toContainText('€500.00');
  await expect(dialog.locator('.cx-invoice-summary')).toContainText('€18,500.00');
  await expect(dialog.locator('.cx-invoice-basis')).toContainText('not a separate invoice-specific GL posting');
  expect(await dialog.evaluate(node=>node.scrollWidth<=node.clientWidth+1)).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await dialog.locator('#cx-invoice-search').fill('AR-TEST-002');
  await expect(dialog.locator('.cx-invoice-card')).toHaveCount(1);
  await dialog.getByRole('button',{name:'Trace source and applications'}).click();
  await expect(dialog.locator('#reportDialogTitle')).toHaveText('Invoice source trace');
  await expect(dialog.locator('#reportDialogBody')).toContainText('AR-TEST-002');
  await expect(dialog.locator('#reportDialogBody')).toContainText('Gross open AR');
  await expect(dialog.locator('#reportDialogBody')).toContainText('Analytical ECL allocation');
  await expect(dialog.locator('#reportDialogBody')).toContainText('Analytical net AR');
  await expect(dialog.locator('#reportDialogBody')).toContainText('CONTRACT-APPLY-2026-09-US01-C1-HW');
  await expect(dialog.locator('#reportDialogBody')).toContainText('not bank-matched receipts');
  await expect(dialog.getByRole('button',{name:'Next items'})).toHaveCount(0);
  await expect(dialog.locator('#cx-invoice-list-back')).toBeVisible();
  await page.screenshot({path:'test-results/ar-invoice-lineage-mobile.png'});
});
