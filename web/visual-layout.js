/* Responsive focus controls preserve every analytical panel without shrinking it. */
(function(root){
  let selectedPanel='cx-ranking';
  function positionCharts(){
    document.querySelectorAll('.report-chart-scroll').forEach(chart=>{chart.scrollLeft=chart.dataset.chartAnchor==='end'?chart.scrollWidth:0;});
  }
  function mount(){
    positionCharts();
    const workspace=document.querySelector('.cx-workspace');
    if(!workspace)return;
    const nav=document.createElement('nav');
    nav.className='sw-analysis-nav cx-analysis-nav';nav.setAttribute('aria-label','Contribution analysis focus');
    const sections=[['cx-ranking','Contribution'],['cx-flow','Value flow'],['cx-evidence','Underlying records'],['cx-inspector','Selected detail']];
    sections.forEach(([name,label],index)=>{
      const panel=workspace.querySelector(`.${name}`);if(!panel)return;
      panel.id=`cx-analysis-${index}`;panel.classList.toggle('analysis-selected',name===selectedPanel);
      const button=document.createElement('button');button.type='button';button.textContent=label;
      button.setAttribute('aria-controls',panel.id);button.setAttribute('aria-pressed',String(name===selectedPanel));
      button.onclick=()=>{
        selectedPanel=name;
        workspace.querySelectorAll(':scope > section,:scope > aside,:scope > div').forEach(p=>p.classList.toggle('analysis-selected',p===panel));
        nav.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
      };
      nav.append(button);
    });
    workspace.before(nav);
  }
  root.VisualLayout={mount,positionCharts};
})(globalThis);
