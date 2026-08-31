# Product Hierarchy and Portfolio Complexity

Version 0.3 expands Aureon Systems Group from a small illustrative product list into a finance-grade synthetic commercial catalog.

## Hierarchy

Every SKU belongs to the following structure:

```text
Division
  -> Product Family
      -> Product Subfamily
          -> Product Type
              -> Quality Tier
                  -> SKU / Generation
```

The hierarchy is deliberately asymmetric across the four divisions. It is not a generic master-data tree forced onto every business model.

## Quality tiers

Each product type is normally offered in three commercial tiers:

- Essential: higher volume, lower price and lower absolute margin per unit
- Professional: core offer and reference economics
- Premium: lower volume, higher price, better margin mix and different customer penetration

Quality is therefore an economic driver rather than a display label. Tier changes affect price, cost, demand, selling costs and portfolio penetration.

## Division catalogs

Software contains platform, security, analytics and automation families. Products represent commercial software offers rather than artificial hardware-style SKUs.

Hardware contains control systems, edge appliances, terminals, network devices and sensors/readers. These products create manufacturing demand, intercompany supply, inventory and factory utilization.

Events & Projects contains deployment/integration, training/enablement, customer experience and managed-program families. Each product represents a repeatable commercial project archetype while individual transactions remain project-like and irregular.

Spare Parts contains control modules, maintenance kits, interface components, mechanical parts, security components and consumables. This is intentionally the broadest physical catalog because aftermarket operations normally have the strongest SKU proliferation and inventory complexity.

## Customer assortment

The simulation does not create a full customer x SKU Cartesian product.

Each customer receives a deterministic portfolio breadth and buys a stable but partial assortment. Strategic customers tend to have broader catalogs and more Premium penetration. Growth customers skew toward Essential and selected Professional offers. The selection is deterministic so the same seed and period remain reproducible.

This creates realistic sparse commercial data while keeping the product universe large enough for:

- family and subfamily profitability
- product mix analysis
- quality-tier economics
- slow or weak SKU identification
- product lifecycle decisions
- inventory complexity
- factory mix
- customer assortment analysis

## Product lifecycle

A subset of the catalog starts as legacy generation products. Those products have structurally weaker economics and defined NextGen successors.

The portfolio review engine evaluates trailing profitability every six months. When a product falls below the divisional gross-margin threshold it can move through:

```text
Active
-> Phase-out approved
-> Phase-out effective
-> Replacement approved
-> Replacement launched
```

The successor is not simply a renamed SKU. It receives a new generation, improved cost position, changed demand and updated commercial role.

## Finance integration

Product hierarchy fields are written into operating data and preserved through product profitability outputs. Physical products also affect source-factory production and therefore intercompany manufacturing, inventory and CAPEX utilization.

The dashboard exposes:

- total catalog size
- division/family/subfamily structure
- quality-tier economics
- family profitability
- SKU profitability
- portfolio lifecycle decisions
- customer profitability

This keeps the synthetic company explorable at CFO level without making the dashboard dependent on a toy-sized catalog.
