const {test,expect}=require('@playwright/test');

const pages=[
  ['pnl',5,'pnl'],['profitability',4,'products'],
  ['working-capital',0,'nwc'],['working-capital',1,'ar'],
  ['working-capital',2,'inventory'],['working-capital',3,'ap'],
  ['operations-capex',3,'capex'],['cash-flow',3,'cash']
];

test('all eight contribution explorers show complete details beside evidence on laptops',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  for(const [view,index,key] of pages){
    await page.goto(`/#view=${view}&page=${index}`);
    const explorer=page.locator(`.contribution-explorer[data-contribution="${key}"]`);
    await expect(explorer).toBeVisible();
    const geometry=await explorer.evaluate(element=>{
      const inspector=element.querySelector('.cx-inspector'),details=inspector.querySelector('dl');
      const side=inspector.getBoundingClientRect(),evidence=element.querySelector('.cx-evidence').getBoundingClientRect();
      const flow=element.querySelector('.cx-flow-map');
      const flowNodes=[...flow.querySelectorAll('button')].map(node=>({label:node.textContent.trim(),height:node.clientHeight,content:node.scrollHeight,top:node.getBoundingClientRect().top,bottom:node.getBoundingClientRect().bottom}));
      return {details:details.clientHeight,content:details.scrollHeight,inspectorLeft:side.left,inspectorBottom:side.bottom,evidenceRight:evidence.right,evidenceBottom:evidence.bottom,rows:element.querySelectorAll('.cx-evidence tbody tr').length,overflow:document.documentElement.scrollWidth-innerWidth,flowTop:flow.getBoundingClientRect().top,flowBottom:flow.getBoundingClientRect().bottom,flowNodes};
    });
    expect(geometry.content,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(geometry.details+1);
    expect(geometry.evidenceRight,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(geometry.inspectorLeft+1);
    expect(geometry.inspectorBottom,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeGreaterThanOrEqual(geometry.evidenceBottom-1);
    expect(geometry.rows,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeGreaterThan(0);
    expect(geometry.overflow,`${view}/${key}: ${JSON.stringify(geometry)}`).toBeLessThanOrEqual(1);
    if(!['pnl','nwc'].includes(key))for(const node of geometry.flowNodes){
      expect(node.content,`${view}/${key}: clipped ${node.label} (${JSON.stringify(geometry)})`).toBeLessThanOrEqual(node.height+1);
      expect(node.top,`${view}/${key}: ${node.label} is above the flow`).toBeGreaterThanOrEqual(geometry.flowTop-1);
      expect(node.bottom,`${view}/${key}: ${node.label} is below the flow`).toBeLessThanOrEqual(geometry.flowBottom+1);
    }
    if(['ar','capex'].includes(key)){
      const screenshot=testInfo.outputPath(`${key}-inspector-1280x720.png`);
      await page.screenshot({path:screenshot});
      await testInfo.attach(`${key}-inspector-1280x720`,{path:screenshot,contentType:'image/png'});
    }
  }
});
