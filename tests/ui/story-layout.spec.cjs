const {test,expect}=require('@playwright/test');

const cases=[
  {view:'pnl',page:1,left:'Understand the path from revenue to EBIT',right:'Revenue to EBIT'},
  {view:'working-capital',page:4,left:'Asset-quality trend',right:'Provision impact'},
  {view:'treasury',page:1,left:'Liquidity trend',right:'Current liquidity bridge'},
  {view:'balance-sheet',page:1,left:'Receivables carrying value',right:'Inventory carrying value'}
];

for(const report of cases)test(`${report.view} keeps financial indicators outside its evidence panes`,async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto(`/#view=${report.view}&page=${report.page}&entity=all&division=all`);
  const overview=page.locator('.statement-story-overview');
  await expect(overview).toBeVisible();
  await expect(overview.locator('.statement-story-indicators > .kpi')).toHaveCount(4);
  await expect(overview.locator('.statement-story-all summary')).toBeVisible();
  const panes=overview.locator('.story-composite');
  await expect(panes).toHaveCount(2);
  await expect(panes.first().getByText(report.left,{exact:report.view!=='pnl'})).toBeVisible();
  await expect(panes.last().getByText(report.right,{exact:false})).toBeVisible();
  const layout=await overview.evaluate(node=>{
    const band=node.querySelector('.statement-story-indicators').getBoundingClientRect();
    const panes=[...node.querySelectorAll('.story-composite')];
    return {
      cardsInside:[...node.querySelectorAll('.statement-story-indicators > .kpi')].every(card=>{const r=card.getBoundingClientRect();return r.left>=band.left-1&&r.right<=band.right+1}),
      evidenceBelow:panes.every(pane=>pane.getBoundingClientRect().top>=band.bottom-1),
      paneOverflow:panes.map(pane=>Math.max(0,pane.scrollHeight-pane.clientHeight)),
      horizontal:document.documentElement.scrollWidth>innerWidth
    };
  });
  expect(layout.cardsInside).toBe(true);
  expect(layout.evidenceBelow).toBe(true);
  expect(layout.horizontal).toBe(false);
  expect(layout.paneOverflow[0]).toBeLessThan(90);
  if(report.view==='pnl'){
    const lastRow=panes.first().locator('.statement-table tbody tr').last();
    expect(await lastRow.evaluate(row=>row.getBoundingClientRect().bottom<=row.closest('.story-composite').getBoundingClientRect().bottom+1)).toBe(true);
  }
  if(report.view==='treasury'){
    await expect(panes.first().locator('.report-svg')).toBeVisible();
    await expect(panes.first().getByText('Explore 24-month cash, debt and covenant records')).toBeVisible();
  }
  await page.screenshot({path:`test-results/story-${report.view}.png`,fullPage:true});
  await overview.locator('.statement-story-all summary').click();
  await expect(overview.locator('.statement-story-all')).toHaveAttribute('open','');
  expect(await overview.locator('.statement-story-all .kpi').count()).toBeGreaterThan(4);
  if(report.view==='pnl')await page.screenshot({path:'test-results/story-all-indicators.png',fullPage:true});
  await overview.locator('.statement-story-all .kpi-info').first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await page.locator('#reportDialog').getByRole('button',{name:'Close'}).click();
  await overview.locator('.statement-story-all summary').click();
  await page.setViewportSize({width:1024,height:768});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await expect(overview.locator('.statement-story-indicators > .kpi')).toHaveCount(4);
  await page.setViewportSize({width:390,height:844});
  const regions=page.getByRole('navigation',{name:'Dashboard regions'});
  await expect(regions).toBeVisible();
  await expect(panes.first()).toBeVisible();
  await regions.getByRole('button').nth(1).click();
  await expect(panes.last()).toBeVisible();
  await expect(panes.first()).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:`test-results/story-${report.view}-mobile.png`,fullPage:true});
  await expect(panes.last().getByText(report.right,{exact:false})).toBeInViewport();
});
