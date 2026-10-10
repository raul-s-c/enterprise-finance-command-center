const {test,expect}=require('@playwright/test');

test('cash contribution traces free cash flow to invoice and accrual allocation evidence',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=3&section=Cash+contribution&entity=US01&division=all&metric=revenue');
  const explorer=page.locator('.contribution-explorer[data-contribution="cash"]');
  await expect(explorer).toBeVisible();
  await expect(explorer.locator('.cx-head p')).toHaveText('Entity: US01');
  await expect(explorer.locator('.cx-evidence h3')).toHaveText('Cash movement lineage · US01');
  await expect(explorer.locator('.cx-inspector')).toContainText('Lineage rows');
  await expect(explorer.locator('.cx-evidence table thead')).toContainText('Cash flow category');
  await expect(explorer.locator('.cx-evidence table thead')).toContainText('Source journal id');
  await expect(explorer.locator('.cx-evidence table tbody tr').first()).toBeVisible();
  await expect(explorer.locator('[data-dimension="division"]')).toBeVisible();
  await explorer.locator('[data-dimension="division"]').click();
  await expect(explorer.locator('.cx-ranking h3')).toHaveText('Contribution by division');
  await expect(explorer.locator('.cx-evidence table tbody tr')).not.toHaveCount(0);
  await expect(explorer.locator('.cx-inspector')).toContainText('Lineage rows');
  await expect(explorer.locator('.contribution-note')).toContainText('not bank-matched remittances');

  const reconciliation=await page.evaluate(async()=>{
    const data=await(await fetch('/data/dashboard.json')).json();
    const categories=['customer_collections','supplier_payments','capex','interest','tax'];
    const evidence=data.cash_movement_lineage.filter(row=>row.month===data.meta.end_month&&row.entity==='US01'&&categories.includes(row.cash_flow_category));
    const total=evidence.reduce((sum,row)=>sum+row.movement_amount,0);
    const summary=data.cash_flow_detail.find(row=>row.month===data.meta.end_month&&row.entity==='US01');
    return {total,freeCashFlow:summary.free_cash_flow,rows:evidence.length};
  });
  expect(reconciliation.rows).toBeGreaterThan(0);
  expect(reconciliation.total).toBeCloseTo(reconciliation.freeCashFlow,2);

  await explorer.locator('.cx-evidence table tbody tr').first().click();
  const dialog=page.locator('#reportDialog');
  await expect(dialog).toContainText('Cash movement lineage detail');
  await expect(dialog).toContainText('Source journal id');
  await dialog.getByRole('button',{name:'More fields'}).click();
  await expect(dialog).toContainText('Allocation basis');
  await expect(dialog).toContainText('not bank-matched');
  await dialog.getByRole('button',{name:'Close'}).click();
});


test('cash contribution hides division for a metric with no current-close movements',async({page})=>{
  const dashboard=JSON.parse(JSON.stringify(require('../../web/data/dashboard.json')));
  const month=dashboard.meta.end_month;
  dashboard.cash_movement_lineage=dashboard.cash_movement_lineage.filter(row=>row.month!==month);
  dashboard.cash_movement_lineage.push({
    month,entity:'US01',division:'Hardware',cash_flow_category:'customer_collections',
    source_record_type:'Cash journal posting',source_record_id:'TEST-COLLECTION',source_journal_id:'TEST-CASH-JOURNAL',
    counterparty:'Test customer',movement_amount:100,allocation_basis:'UI regression fixture'
  });
  await page.route('**/data/dashboard.json*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(dashboard)}));
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=3&section=Cash+contribution&entity=US01&division=all&metric=revenue');
  const explorer=page.locator('.contribution-explorer[data-contribution="cash"]');
  await expect(explorer).toBeVisible();
  await expect(explorer.locator('[data-dimension="division"]')).toBeVisible();
  await explorer.locator('[data-dimension="division"]').click();
  await expect(explorer.locator('.cx-ranking h3')).toHaveText('Contribution by division');
  await explorer.locator('#cx-metric').selectOption({label:'Debt repayment'});
  await expect(explorer.locator('.cx-ranking h3')).toHaveText('Contribution by entity');
  await expect(explorer.locator('[data-dimension="division"]')).toHaveCount(0);
  await expect(explorer.locator('.cx-ranking .contribution-row')).not.toHaveCount(0);
});