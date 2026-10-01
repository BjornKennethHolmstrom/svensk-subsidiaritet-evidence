# Räddningstjänst Treatment History Reconstruction v0.2

**Status:** treatment-history reconstruction completed; **not yet a final causal treatment lock**  
**Panel window:** 1998–2020  
**Outcome firewall:** **CLOSED — no new post-treatment outcome values were opened or imported**

## Result

v0.2 separates formal authority (**A**) from operational coordination (**K**) and replaces the v0.1 event-list logic with an evidence-bounded treatment history.

The reconstruction contains:

- **290 municipalities**
- **6,670 municipality-year rows**
- **75 municipalities with exact first full-A treatment years**
- **40 independent exact treatment event IDs**
- **54 municipalities already fully pooled by the 1998 panel baseline**
- **24 interval-censored or snapshot-pinpointed first treatments**
- **3 municipalities with a documented reversal after treatment**
- **134 municipalities whose first-treatment status remains unresolved and therefore cannot silently enter the control group**

No exact first-treatment event conflicts with an earlier strict FULL_A national snapshot.

## A-layer

The A-layer distinguishes:

- `FULL_A`
- `COMMON_BOARD`
- `PARTIAL_AUTHORITY`
- `RESOURCE_ONLY`
- `SCOPE_UNRESOLVED`
- `LOCAL_OR_OTHER`
- `UNKNOWN`

First-treatment status distinguishes:

- `PRETREATED_BY_1998`
- `EXACT_FIRST_TREATMENT`
- `INTERVAL_CENSORED_FIRST_TREATMENT`
- `SNAPSHOT_PINPOINTED_YEAR`
- `UNRESOLVED`

The primary future staggered-DiD candidate set is deliberately narrower: only `ELIGIBLE_EXACT` municipalities are candidates for the first causal lock. Interval-censored, pretreated, reversal and unresolved cases remain excluded from that primary design unless a later source resolves them before the causal protocol is frozen.

## K-layer

v0.2 records K separately from A. The strongest examples are:

- Brandkåren Attunda as a **resource-pooling federation** before full rescue-service authority was transferred;
- Höga Kusten–Ådalen as a **leadership federation from 2003**, becoming a complete federation only in 2005;
- shared alarm/leadership arrangements in the Stockholm rescue-service system;
- Västra Räddningsregionen's shared rescue-leadership system from 2019 while the participating rescue services retained their own authority;
- post-dissolution boundaryless operational cooperation in eastern Norrbotten.

National boundaryless-cooperation prevalence is stored only as an aggregate K observation and is never assigned to individual municipalities.

## Important historical corrections

### Östra Norrbotten

The reconstruction replaces the earlier interval assumption with a stronger institutional source: the federation became a **comprehensive municipal federation from 1 January 2000** and was dissolved on **31 December 2009**. It is therefore treated as an exact A transition followed by a documented reversal, not as a clean absorbing-treatment cohort.

### Södertörn

Formal membership years follow the stronger institutional history: founding municipalities in 1993, Södertälje 1997, Nykvarn formally 2000, Botkyrka/Salem 2004, Ekerö 2007 and Nacka 2010. A conflict between current summary wording and formal archival wording for Nykvarn is preserved in provenance rather than silently normalized.

### Attunda

National reports label Attunda explicitly as a **resource-only federation** through 2007. The original four municipalities are therefore not assigned full A in those years. Their transition to full-scope rescue authority is interval-censored to 2008–2009; Sigtuna and Knivsta enter the full-scope federation in 2009.

## QA

The 1998 national snapshot reconciles exactly when scope is respected:

- 54 strict full-A municipalities
- 3 leadership-only municipalities in Östra Norrbotten
- total 57 municipalities in the published federation count
- plus four Attunda resource-pooling municipalities recorded separately.

The 2002 snapshot also reconciles to the published 89 federation municipalities when three scope-unresolved Sörmlandskusten municipalities are retained as observations rather than promoted to causal treatment.

The 2000 manual extraction remains short of the published aggregate by two municipalities. This is explicitly flagged as a provenance/archival reconciliation issue and does **not** affect any exact first-treatment year derived from stronger institutional sources.

## Research status

v0.2 is sufficiently structured to support the **next pre-treatment-only outcome feasibility stage**, using the exact-treatment candidate set as the primary design candidate.

It is **not** yet permission to unmask post-treatment outcome effects.

Before causal unmasking, the next audit should:

1. inventory annual pre-treatment availability for response time and candidate quality outcomes;
2. verify usable pre-period length by exact treatment event;
3. quantify event-level rather than municipality-level support;
4. map K/network contamination around exact treatment events;
5. freeze the exact cohort/control/outcome/estimator protocol;
6. only then open post-treatment outcomes.
