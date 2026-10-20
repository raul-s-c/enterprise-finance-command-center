/* Premium finance application shell: useful global commands, never fake chrome. */
(function(root){
  const escapeCsv=value=>`"${String(value??'').replaceAll('"','""')}"`;
  function exportView(){
    const rows=[...document.querySelectorAll('#content table tr')].map(row=>[...row.children].map(cell=>cell.textContent.trim()));
    if(!rows.length){root.print();return;}
    const csv=rows.map(row=>row.map(escapeCsv).join(',')).join('\r\n');
    const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),link=document.createElement('a');
    link.href=URL.createObjectURL(blob);link.download=`aureon-${state.view}-${data?.meta?.end_month||'report'}.csv`;link.click();URL.revokeObjectURL(link.href);
  }
  function openHelp(){const button=document.getElementById('reportHelp');if(button&&!button.hidden){button.click();return;}reportDialog('Aureon Finance help','<div class="help-pages"><p>Use the left navigation to change the reporting domain. Every financial view preserves the published close, shows only supported scope controls and provides source evidence where available.</p><p>Use contribution analysis to move from a consolidated total to entity, division, component and underlying records without allocating missing dimensions.</p></div>');}
  function searchIndex(){
    const unique=values=>[...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    return [
      ...views.map(([id,label,description])=>({type:'Report',label,detail:description,value:id})),
      ...unique((data?.management_detail||[]).map(row=>row.entity)).map(value=>({type:'Entity',label:value,detail:'Open the P&L filtered to this entity',value})),
      ...unique((data?.management_detail||[]).map(row=>row.division)).map(value=>({type:'Division',label:value,detail:'Open the P&L filtered to this division',value}))
    ];
  }
  function setupSearch(){
    const input=document.getElementById('globalSearch'),results=document.getElementById('globalSearchResults');
    if(!input||!results||input.dataset.bound)return;
    input.dataset.bound='1';
    const entries=searchIndex();let matches=[],active=-1;
    const close=()=>{results.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;};
    const choose=item=>{
      if(!item)return;
      close();input.value='';
      if(item.type==='Report')state.view=item.value;
      else if(item.type==='Entity'){state.view='pnl';state.entity=item.value;state.division='all';}
      else{state.view='pnl';state.entity='all';state.division=item.value;}
      reportState.page=0;reportState.section=null;render();
      const heading=document.getElementById('viewTitle');
      heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});
    };
    const paint=()=>{
      const query=input.value.trim().toLocaleLowerCase();
      results.replaceChildren();active=-1;input.removeAttribute('aria-activedescendant');
      if(!query){close();return;}
      const rank=item=>{
        const label=item.label.toLocaleLowerCase(),detail=item.detail.toLocaleLowerCase();
        return label===query?0:label.startsWith(query)?1:label.includes(query)?2:detail.includes(query)?3:99;
      };
      matches=entries.map(item=>({item,rank:rank(item)})).filter(row=>row.rank<99)
        .sort((a,b)=>a.rank-b.rank||a.item.label.localeCompare(b.item.label)).slice(0,8).map(row=>row.item);
      if(!matches.length){
        const empty=document.createElement('div');empty.className='global-search-empty';empty.setAttribute('role','status');empty.textContent='No reports, entities or divisions match this search.';
        results.append(empty);
      }else matches.forEach((item,index)=>{
        const option=document.createElement('div');option.id=`global-search-option-${index}`;option.tabIndex=-1;
        option.className='global-search-option';option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.dataset.searchIndex=String(index);
        const title=document.createElement('span');title.className='global-search-option-title';title.textContent=item.label;
        const kind=document.createElement('span');kind.className='global-search-option-kind';kind.textContent=item.type;
        const detail=document.createElement('small');detail.textContent=item.detail;
        option.append(title,kind,detail);results.append(option);
      });
      results.hidden=false;input.setAttribute('aria-expanded','true');
    };
    const activate=index=>{
      if(!matches.length)return;
      active=(index+matches.length)%matches.length;
      results.querySelectorAll('[role=option]').forEach((option,i)=>option.setAttribute('aria-selected',String(i===active)));
      input.setAttribute('aria-activedescendant',`global-search-option-${active}`);
    };
    input.addEventListener('input',paint);
    input.addEventListener('keydown',event=>{
      if(event.key==='ArrowDown'){event.preventDefault();if(results.hidden)paint();activate(active+1);}
      else if(event.key==='ArrowUp'){event.preventDefault();if(results.hidden)paint();activate(active<0?matches.length-1:active-1);}
      else if(event.key==='Enter'&&!results.hidden){event.preventDefault();choose(matches[active<0?0:active]);}
      else if(event.key==='Escape'&&!results.hidden){event.preventDefault();close();}
    });
    results.addEventListener('click',event=>{const option=event.target.closest('[data-search-index]');if(option)choose(matches[Number(option.dataset.searchIndex)]);});
    document.addEventListener('click',event=>{if(!results.contains(event.target)&&!input.closest('.global-search').contains(event.target))close();});
    if(input.value.trim())paint();
  }
  function paintCloseStatus(dataset){
    const period=document.getElementById('globalPeriod'),control=document.getElementById('globalControl');
    const passed=dataset?.validation?.passed,known=typeof passed==='boolean';
    period.textContent=dataset?.meta?.end_month||'No close';
    control.innerHTML=`<i></i> Controls ${known?(passed?'passed':'failed'):'unavailable'}`;
    control.classList.toggle('failed',known&&!passed);control.classList.toggle('pending',!known);
  }
  /* Phone report chrome: collapse the title, module, subpage and context bars while the reader scrolls
     the report down, restore them on upward scroll, at the top, on focus, on view/page change and above 600px.
     Only user-driven scrolls (wheel, touch, scroll keys, scrollbar drag) count, so focus and scrollIntoView
     moves made by the application never hide the controls a user is about to use. */
  const CHROME='.mobile-module,.topbar,.report-subnav,.report-context';
  function setupMobileChrome(){
    const content=document.getElementById('content'),phone=root.matchMedia?.('(max-width:600px)');
    if(!content||!phone||content.dataset.chromeBound)return;
    content.dataset.chromeBound='1';
    const body=document.body,SETTLE=250,INTENT=1000,TRAVEL=24;
    // Report views scroll #content or an inner pane (statement grids, table wrappers), and many phone layouts fit
    // with little or no overflow. Scrolls are therefore observed in the capture phase per scrolling element, and a
    // downward wheel/swipe at the end of the pane under the pointer also asks for the room the chrome occupies.
    let scroller=content,last=0,anchor=0,direction=0,lockUntil=0,intentUntil=0,settleTimer=0,touchY=null,push=0;
    const isCollapsed=()=>body.classList.contains('mobile-chrome-collapsed');
    const resync=()=>{last=anchor=scroller.isConnected?scroller.scrollTop:0;direction=0;push=0;};
    const set=collapsed=>{
      if(isCollapsed()===collapsed)return;
      body.classList.toggle('mobile-chrome-collapsed',collapsed);
      lockUntil=performance.now()+SETTLE;clearTimeout(settleTimer);settleTimer=setTimeout(resync,SETTLE);
    };
    // Browsers latch a wheel or touch gesture to the nearest scroll container, so that pane decides whether the
    // gesture still scrolls content or has run out of room.
    const nearestScroller=target=>{
      for(let el=target instanceof Element?target:content;el&&el!==content&&content.contains(el);el=el.parentElement)
        if(el.scrollHeight-el.clientHeight>1&&/(auto|scroll)/.test(getComputedStyle(el).overflowY))return el;
      return content;
    };
    const atEnd=el=>el.scrollTop+el.clientHeight>=el.scrollHeight-2;
    const gesture=(target,dy)=>{
      if(!phone.matches||!dy||performance.now()<lockUntil)return;
      if(Math.sign(dy)!==Math.sign(push))push=0;
      push+=dy;
      if(push>TRAVEL&&!isCollapsed()&&atEnd(nearestScroller(target)))set(true);
      else if(push<-TRAVEL&&isCollapsed()&&nearestScroller(target).scrollTop<=0)set(false);
    };
    const markIntent=()=>{intentUntil=performance.now()+INTENT;};
    content.addEventListener('wheel',event=>{markIntent();if(!event.ctrlKey&&Math.abs(event.deltaY)>Math.abs(event.deltaX))gesture(event.target,event.deltaY);},{passive:true});
    content.addEventListener('touchstart',event=>{markIntent();touchY=event.touches.length===1?event.touches[0].clientY:null;push=0;},{passive:true});
    content.addEventListener('touchmove',event=>{
      markIntent();
      if(touchY===null||event.touches.length!==1)return;
      const y=event.touches[0].clientY;gesture(event.target,touchY-y);touchY=y;
    },{passive:true});
    content.addEventListener('touchend',()=>{markIntent();touchY=null;},{passive:true});
    content.addEventListener('pointerdown',event=>{if(event.target.scrollHeight>event.target.clientHeight)markIntent();});
    content.addEventListener('keydown',event=>{
      if(event.target.closest('input,select,textarea,[contenteditable]'))return;
      if(['PageDown','PageUp','ArrowDown','ArrowUp','Home','End',' '].includes(event.key))markIntent();
    });
    content.addEventListener('scroll',event=>{
      if(!phone.matches)return;
      const el=event.target;
      if(!(el instanceof Element))return;
      const now=performance.now(),top=el.scrollTop;
      if(el!==scroller){scroller=el;last=anchor=top;direction=0;return;}
      if(top===last)return; // horizontal scroll of a wide table
      if(now<lockUntil||now>intentUntil){last=anchor=top;return;} // layout clamp after a toggle, or an app scroll
      intentUntil=Math.max(intentUntil,now+150);
      const step=Math.sign(top-last);
      if(step!==direction){anchor=last;direction=step;}
      last=top;
      if(direction<0&&(top<40||anchor-top>TRAVEL))set(false);
      else if(direction>0&&top>80&&top-anchor>TRAVEL)set(true);
    },{capture:true,passive:true});
    document.addEventListener('focusin',event=>{if(event.target.closest?.(CHROME))set(false);});
    phone.addEventListener?.('change',event=>{if(!event.matches)set(false);});
    let routeKey='';
    const observeRoute=()=>{
      const key=`${state.view}|${typeof reportState==='object'?reportState.page:''}`;
      if(key!==routeKey){routeKey=key;set(false);scroller=content;resync();}
    };
    const title=document.getElementById('viewTitle');
    if(title)new MutationObserver(observeRoute).observe(title,{childList:true,characterData:true,subtree:true});
    observeRoute();
  }
  root.paintPremiumCloseStatus=paintCloseStatus;
  root.mountPremiumShell=function(){
    paintCloseStatus(data);
    setupSearch();
    setupMobileChrome();
    document.getElementById('globalExport').onclick=exportView;document.getElementById('globalHelp').onclick=openHelp;
  };
})(globalThis);
