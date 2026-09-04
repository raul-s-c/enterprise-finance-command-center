// Explain mixed-scope views without allocating consolidated measures artificially.
const executiveBeforeScopeNotice = renderers.executive;
renderers.executive = function(){
  const notice = '<div class="section-note" style="margin-bottom:14px">Revenue, margins, EBIT and action lifecycle follow the selected entity and division. Cash flow, working capital, financial position, commentary and close priorities remain consolidated group measures.</div>';
  return notice + executiveBeforeScopeNotice();
};
