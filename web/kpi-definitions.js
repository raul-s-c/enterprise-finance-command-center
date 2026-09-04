/* Presentation metadata, tied to the existing renderers. No accounting calculations. */
(function(root){
  const definitions=Object.create(null);
  const group='Consolidated group; entity and division filters do not apply.';
  const selected='Selected entity and division.';
  const close='Latest published close month.';
  function add(label,formula,source,scope=group,period=close){definitions[label]={formula,source,scope,period};}
  function batch(source,scope,period,rows){for(const [label,formula] of rows)add(label,formula,source,scope,period);}
  batch('management_detail → aggregateManagement / FinanceReport.aggregate',selected,close,[
    ['Revenue','Sum of external revenue in the selected scope. YoY compares the same calendar month one year earlier: (AC − PY) / |PY|.'],
    ['Marginal contribution','Revenue − variable production costs. The percentage is total marginal contribution / total revenue, not an average of row margins.'],
    ['Gross profit','Marginal contribution − fixed production costs, including the posted factory absorption variance and reserve effects in the management statement.'],
    ['Gross margin','Sum of gross profit / sum of revenue × 100. Not the average of product or entity percentages.'],
    ['OPEX','Sum of operating expenses, including personnel and non-people OPEX. The note is OPEX / revenue × 100.'],
    ['EBIT','Gross profit − OPEX − depreciation. Margin = EBIT / revenue; YoY = (AC − PY) / |PY|.'],
  ]);
  batch('cash_flow',group,close,[
    ['Operating cash flow','Published operating cash movements: customer collections and advances, supplier and personnel payments, interest and tax, with their ledger signs.'],
    ['Investing cash flow','CAPEX cash movements, with outflows negative. Transfers from CIP to PPE are non-cash and are not counted again.'],
    ['Financing cash flow','Published debt financing cash movements, with repayments negative. Internal cash pooling does not create group cash.'],
    ['Free cash flow','Operating cash flow + investing cash flow. This is after CAPEX, before financing cash flow.'],
    ['Group free cash flow','Operating cash flow + investing cash flow. This group value is deliberately not allocated to the selected operating scope.'],
    ['Net cash movement','Sum of ledger cash debits − cash credits for the month, across all cash-flow categories (including opening entries when present).'],
  ]);
  batch('balance_sheet',group,'Closing balance at the latest published month (a stock, not a sum of monthly balances).',[
    ['Assets','Cash + net trade receivables + net consolidated inventory + gross PPE + CIP + signed accumulated depreciation. Allowances and the unrealized intercompany inventory reserve reduce carrying values.'],
    ['Liabilities','Trade payables + tax payable + debt + contract liabilities, after group intercompany elimination.'],
    ['Equity','Share capital + retained earnings in the consolidated statement. This is not an amount invented to make the balance sheet balance.'],
    ['Cash','Cumulative cash-account debits − credits through the closing month, consolidated across legal entities.'],
    ['Balance check','Assets − liabilities − equity. Zero means the statement balances. The legacy card says Reconciled when |gap| < EUR 0.10; this display label does not replace the engine validation controls.'],
  ]);
  batch('working_capital / provision_summary',group,close,[
    ['Group net working capital','Published net_working_capital: net trade receivables + net inventory − trade payables. Contract liabilities are excluded; see Operating NWC for that funding layer.'],
    ['Net working capital','Net trade receivables + net inventory − trade payables.'],
    ['Gross receivables','Gross AR before the credit-loss allowance; source trade_receivables_gross, with provision_summary.gross_ar as the legacy fallback. DSO is the published working-capital ratio.'],
    ['Trade receivables','Published trade_receivables balance. DSO = receivables / monthly revenue × 30 using the working-capital schedule.'],
    ['Credit loss allowance','Published credit_loss_allowance, built from customer aging/risk reserves. It reduces AR without a cash outflow. The card note is allowance / gross AR × 100.'],
    ['Net receivables','Gross trade receivables − credit loss allowance; published net_trade_receivables.'],
    ['Gross inventory','Published inventory_gross before the inventory provision. DIO is the published working-capital ratio.'],
    ['Inventory','Published inventory carrying value. DIO = inventory / monthly production costs × 30 in the working-capital schedule.'],
    ['Inventory provision','Published inventory_provision reserve against gross stock; not the separate unrealized intercompany markup reserve. The note is provision / gross inventory × 100.'],
    ['Net inventory','Published net_inventory after the inventory provision; the consolidated balance sheet also discloses the separate intercompany markup elimination.'],
    ['Trade payables','Closing trade AP balance. DPO is the published working-capital ratio, not the average of supplier payment terms.'],
    ['Provision-adjusted NWC','Net receivables + net inventory − trade payables; source provision_adjusted_net_working_capital. The note shows gross NWC before reserves.'],
    ['Trade NWC','Published trade_net_working_capital: AR + inventory − AP, excluding contract liabilities.'],
    ['Operating NWC','Trade net working capital − closing contract liabilities. The normal source is group operating_net_working_capital, not an allocation to the selection.'],
    ['Cash conversion cycle','DSO + DIO − DPO, in days. These are 30-day monthly run-rate ratios, not actual invoice collection dates.'],
  ]);
  batch('ap_aging_summary',group,close,[
    ['Gross trade payables','Sum of open supplier AP before settlement; total_ap reconciles to the trade AP ledger.'],
    ['Overdue AP','Sum of open AP past its due date, across all overdue buckets. Note = overdue_ap / total_ap × 100.'],
    ['AP >90 days','Sum of open AP more than 90 days past due; overdue_90_plus.'],
    ['Top-5 supplier concentration','Published top5_spend_concentration: top-five supplier spend / total external supplier spend.'],
    ['Single-source AP','Open AP flagged as single-source supplier exposure. Note = single_source_ap / total_ap × 100.'],
    ['Critical supplier AP','Open AP classified as critical-supplier exposure. Note = critical_supplier_ap / total_ap × 100.'],
  ]);
  definitions['Top-5 supplier concentration'].period='Trailing 12 months of supplier spend ending at the close.';
  batch('contract_entity_summary',selected,close,[
    ['Contract liabilities','Sum of contract_liabilities: customer cash received but not yet released against delivered service. Closing liability, not revenue.'],
    ['Open contract liabilities','Sum of closing contract_liabilities in the selected contract schedule.'],
    ['Current customer advances','Sum of customer_advances received during the closing month, not the outstanding liability balance.'],
    ['Latest customer advances','Sum of customer_advances received during the closing month.'],
  ]);
  batch('treasury_liquidity',group,close,[
    ['Group cash','Published group cash after pooling; internal transfers have zero consolidated cash impact.'],
    ['Gross debt','Sum of outstanding debt principal, before subtracting cash.'],
    ['Net debt','Gross debt − group cash. The card displays the absolute amount and uses Net cash when the result is negative.'],
    ['Net cash','Group cash − gross debt, displayed only when cash exceeds debt.'],
    ['Liquidity headroom','max(Cash − minimum operating cash, 0) + undrawn revolving credit facility (RCF).'],
    ['Net leverage','Net debt / trailing-12-month EBITDA. EBITDA = EBIT + depreciation. The note shows the configured maximum leverage.'],
    ['Interest coverage','Trailing-12-month EBITDA / trailing-12-month interest expense. The note shows the configured minimum coverage.'],
    ['Covenant status','PASS if net leverage ≤ its configured maximum AND interest coverage ≥ its configured minimum; otherwise WATCH.'],
  ]);
  batch('liquidity_forecast_summary / capital_allocation_capacity',group,'Current forecast vintage; forward months 1–12.',[
    ['Base cash in 12M','Base scenario ending_cash_12m, the closing cash balance at horizon 12, not the sum of monthly cash.'],
    ['Base liquidity headroom','Base scenario liquidity_headroom_12m: cash above minimum plus undrawn RCF at horizon 12.'],
    ['Downside minimum headroom','Minimum liquidity_headroom across all 12 forward months of the Downside scenario.'],
    ['Downside protected allocation capacity','max(min(Downside deployable cash at month 12, minimum Downside liquidity headroom over 12 months), 0). Deployable cash is after the strategic liquidity buffer; this is not approved spending.'],
    ['Base 12M covenant','Base scenario covenant_status_12m at horizon 12. It is not a claim that every intermediate month passes.'],
    ['Downside 12M covenant','Downside scenario covenant_status_12m at horizon 12, evaluated against configured leverage and coverage limits.'],
  ]);
  batch('fy_plan_bridge → scopedPlan',selected,'Current fiscal year; YTD through close, FY includes remaining forecast months.',[
    ['YTD revenue','Sum of ytd_actual_revenue. Note = summed YTD actual revenue − summed YTD frozen budget revenue.'],
    ['YTD EBIT','Sum of ytd_actual_ebit. Note = summed YTD actual EBIT − summed YTD frozen budget EBIT.'],
    ['FY revenue outlook','Sum of latest_fy_revenue: YTD actuals + latest forecast for the rest of the fiscal year. Note = (latest FY / FY budget − 1) × 100.'],
    ['FY EBIT outlook','Sum of latest_fy_ebit: YTD actuals + latest remaining-year EBIT forecast. Note = latest FY EBIT − FY budget EBIT.'],
  ]);
  add('Budget vintage','Identifier of the frozen annual-budget vintage; not a calculated financial amount.','meta.budget_vintage / meta.budget_year',group,'Fiscal year shown on the card.');
  for(const [label,field] of [['12M forecast revenue','revenue'],['12M forecast EBIT','ebit'],['12M forecast net income','net_income']])add(label,`Sum of ${field} in the Base integrated forecast P&L (12 monthly flows).`,'forecast_pnl',group,'Forward months 1–12 of the current vintage.');
  for(const [label,field] of [['12M forecast assets','assets'],['12M forecast liabilities','liabilities'],['12M forecast equity','equity'],['12M balance check','balance_check']])add(label,field==='balance_check'?'Forecast assets − liabilities − equity at the final Base month.':`Final Base month ${field}; closing stock, not a sum across the 12 months.`,'forecast_balance_sheet',group,'Horizon 12 of the current vintage.');
  for(const [label,field] of [['12M forecast OCF','operating_cash_flow'],['12M forecast investing CF','investing_cash_flow'],['12M forecast financing CF','financing_cash_flow'],['12M forecast FCF','free_cash_flow']])add(label,`Sum of ${field} across the Base integrated 12-month cash-flow forecast. FCF = operating + investing cash flow.`,'forecast_cash_flow',group,'Forward months 1–12 of the current vintage.');
  batch('software_summary / software_entity_summary', 'Software division; selected entity, or all Software entities.',close,[
    ['ARR','Ending monthly recurring revenue (MRR) × 12. Services revenue is excluded. It is an annualized run rate, not annual recognized revenue.'],
    ['NRR','(Opening MRR + expansion MRR − contraction MRR − churn MRR) / opening MRR × 100. New customers are excluded.'],
    ['GRR','(Opening MRR − contraction MRR − churn MRR) / opening MRR × 100. Expansion and new customers are excluded.'],
    ['New ARR','New customer MRR added during this month × 12.'],
    ['Churn ARR','MRR lost through churn during this month × 12, shown as a positive loss amount.'],
    ['Recurring mix','Ending MRR / total Software monthly revenue × 100.'],
  ]);
  batch('events_summary / events_backlog_detail','Events division. Selected entity uses matching detail; otherwise group Events totals.',close,[
    ['Bookings','Sum of new booked contract value during the month, distinct from recognized service revenue.'],
    ['Recognized revenue','Sum of Events revenue recognized for services delivered in the month.'],
    ['Ending backlog','Opening backlog + bookings − recognized revenue; undelivered contract value at close.'],
    ['Book-to-bill','Monthly bookings / monthly recognized revenue. Above 1 means bookings exceed revenue recognition.'],
  ]);
  add('Backlog coverage','Ending backlog / trailing-three-month average recognized revenue. Uses the group Events schedule even when entity is selected.','events_summary','All Events entities; entity filter does not apply.',close);
  batch('hardware_factory_economics','Hardware factories; CZ01 or CN01 selects that factory, other entity selections retain all factories.',close,[
    ['Factory utilization','Sum of produced units / sum of capacity units × 100. Capacity-weighted, not the mean of site percentages.'],
    ['Production','Sum of produced_units for the current factory month.'],
    ['Capacity headroom','Sum of capacity_headroom_units across the selected factories.'],
    ['Actual fixed factory cost','Sum of actual_fixed_factory_cost (legacy fallback: fixed_factory_cost).'],
    ['Absorbed fixed cost','Sum of absorbed_fixed_cost: production units at the schedule absorption rate. Note = absorbed cost / actual fixed factory cost.'],
    ['Absorption variance','Actual fixed factory cost − absorbed fixed cost. Positive is under-absorption cost; negative is over-absorption benefit.'],
  ]);
  batch('spare_parts_economics','Spare Parts division; selected entity.',close,[
    ['Installed base','Sum of ending_installed_base: opening installed units − estimated retirements + hardware additions. This is a modeled stock.'],
    ['Aftermarket revenue','Sum of spare_parts_revenue during the closing month.'],
    ['Revenue / installed unit','Total spare-parts revenue / total ending installed base.'],
    ['Inventory coverage','Total inventory / sum of each entity inventory divided by its coverage months. The legacy aggregation uses 1 when entity coverage is zero.'],
    ['Inventory health','Inventory-value-weighted mean of inventory_health_pct. Entity health = 1 − min(max(slow-moving value, obsolescence risk value) / inventory, 1); empty inventory has health 100%.'],
  ]);
  batch('workforce_detail / workforce_summary',selected,close,[
    ['Ending FTE','Sum of ending_fte: opening FTE − attrition + hires. FTE is full-time equivalent capacity, not a count of people.'],
    ['Monthly hires','Sum of hires in FTE during the closing month.'],
    ['Monthly attrition','Sum of attrition in FTE during the closing month, shown as a positive reduction.'],
    ['Personnel cost','Sum of personnel_cost: payroll plus modeled recruitment costs. Paid through cash, excluded from supplier AP.'],
    ['Revenue / FTE','Selected monthly revenue / selected average FTE, not ending FTE.'],
    ['Personnel cost / revenue','Sum of personnel_cost / sum of revenue × 100.'],
  ]);
  batch('workforce_forecast → workforceScope',selected,'Base scenario, forward months 1–12.',[
    ['12M personnel cost','Sum of personnel_cost_forecast across Base monthly workforce plan rows.'],
    ['12M planned hires','Sum of workforce_hires_forecast (FTE) across the 12 Base forecast months.'],
    ['12M ending FTE','Sum of workforce_fte_forecast in the final Base workforce month; not the sum of 12 monthly headcounts.'],
    ['12M target FTE','Sum of workforce_target_fte in the final Base workforce month.'],
  ]);
  batch('performance_review → performanceScope',selected,close,[
    ['Revenue vs budget','Revenue review variance = actual_value − benchmark_value (frozen budget). Materiality is the published materiality_pct, not a signed growth rate.'],
    ['EBIT vs budget','EBIT review variance = actual_value − benchmark_value (frozen budget).'],
    ['FY EBIT vs budget','FY EBIT outlook review variance = latest full-year outlook − frozen FY EBIT budget, where that review row exists.'],
    ['Adverse signals','Count of reviewed drivers with favorable = false at the exact selected scope level; not a sum across overlapping scope levels.'],
  ]);
  batch('management_actions → lifecycleScope / performanceScope',selected,'Current close snapshot; action cycles can originate in earlier months.',[
    ['Active actions','Count of actions with status Open or In Progress. The note counts active P1 actions.'],
    ['In progress','Count of active actions with status In Progress.'],
    ['Overdue','Count of active actions with overdue = true. Closed and Cancelled actions are excluded. The note counts Executive escalations.'],
    ['Carry-forward','Count of active actions with carry_forward_months > 0. The note shows the maximum age among those actions.'],
    ['Closed','Count of action cycles whose current status is Closed, not only actions closed this month.'],
    ['Cancelled','Count of action cycles whose current status is Cancelled, with decision evidence retained.'],
  ]);
  batch('management_action_plans → executionScope','Selected scope level; all plans when both filters are All.',close,[
    ['Approved plans','Count of controlled plan rows. The note counts plans with a positive combined price, volume, variable-cost or OPEX intervention.'],
    ['Gross plan cases','Sum of expected_benefit_eur across individual plan cases. Non-additive: overlapping cases must not be treated as realized portfolio profit.'],
  ]);
  for(const [label,field] of [['12M Revenue impact','action_revenue_impact'],['12M EBIT impact','action_ebit_impact']])add(label,`Sum of ${field} in the Base action forecast bridge, horizon ≤ 12. This bridge is additive, unlike individual gross plan cases.`,'management_action_forecast_bridge',selected,'Forward months 1–12.');
  add('Current actual impact','Published latest_additive_actual_ebit_impact. Recognized only after action effective dates; this card remains group-wide.','management_action_execution_summary',group,close);
  batch('fx_translation / constant_currency',selected,close,[
    ['Translation reserve','Sum of fx_translation_reserve at the close: the equity translation difference isolated in CTA/OCI, not transaction FX P&L.'],
    ['Revenue FX effect','Sum of reported revenue − revenue translated at prior-year rates (revenue_fx_effect).'],
    ['EBIT FX effect','Sum of reported EBIT − EBIT translated at prior-year rates (ebit_fx_effect).'],
  ]);
  definitions['Translation reserve'].scope='Selected entity; all divisions (translation is an entity-level schedule).';
  add('Group functional currencies','Count of distinct functional_currency values in fx_translation.','fx_translation',group,'Published translation history.');
  batch('transaction_fx_close_documents',selected,close,[
    ['Open FX documents','Count of documents with status Open in the current close snapshot.'],
    ['Net transaction exposure','Sum of open Receivable carrying_reporting_eur − sum of open Payable carrying_reporting_eur.'],
    ['Unrealized FX P&L','Sum of unrealized_fx_gain_loss_eur across the close documents. Current remeasurement, separate from CTA and realized settlements.'],
    ['Realized FX P&L','Sum of realized_fx_gain_loss_eur across documents settled in the close.'],
  ]);
  add('Official observations','Sum of official_rows across macro driver source coverage. The note separately totals fallback_rows.','sources.macro_drivers',group,'Published rolling macro lineage window.');
  for(const [label,driver] of [['Inflation','inflation'],['Industrial index','industrial_index'],['Energy index','energy_index'],['Policy rate','policy_rate']])add(label,`Applied value for driver ${driver}, observation_month = close month. This is a source observation or explicitly flagged deterministic fallback, not a company KPI aggregation.`,'macro_lineage',group,close);
  batch('intercompany',group,close,[
    ['Intercompany sales','Published intercompany_sales: manufacturing cost + transfer-pricing markup, before consolidation elimination.'],
    ['Manufacturing cost','Published manufacturing_cost underlying the intercompany transfers.'],
    ['Transfer pricing markup','Intercompany sales − manufacturing cost. This is an amount, not a rate.'],
    ['Markup rate','Transfer pricing markup / manufacturing cost × 100.'],
    ['Consolidation','Descriptive status of the model: reciprocal IC P&L and balances are eliminated; this label is not a standalone validation result.'],
  ]);
  batch('meta',group,'Published catalog metadata.',[
    ['Catalog SKUs','Published meta.catalog_products count; this card is group-wide even when a profitability filter is selected.'],
    ['Division / family combinations','Published meta.product_families count of division/family combinations.'],
    ['Quality tiers','Three configured quality levels: Essential, Professional and Premium. This is configuration, not a calculated profitability result.'],
  ]);
  function get(label){
    if(definitions[label])return definitions[label];
    if(/ GM$/.test(label))return {formula:'Division gross profit / division revenue × 100. The MC note = marginal contribution / revenue × 100.',source:'currentDivisionSummary → management_detail',scope:`${label.slice(0,-3)} division; selected entity.`,period:close};
    return null; // Unknown definitions must never be silently invented.
  }
  const api={get,definitions};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.KpiDefinitions=api;
})(globalThis);
