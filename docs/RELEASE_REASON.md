## Release Notes (0.5.0)

## Highlights
This release brings smoother LanceDB behavior, a brand‑new way to explore your vectors, and several UX improvements that make everyday workflows easier.

---

## Improved LanceDB Reliability
Working with LanceDB collections is now more predictable and resilient.

- Deletes behave correctly across all supported LanceDB versions  
- Safe fallback logic prevents accidental duplicate rows  
- Clearer error messages when a delete fails  
- Documentation now lists supported LanceDB/pyarrow versions

**What this means for you:**  
Deletes “just work,” and you get clearer feedback when something goes wrong.

---

## New: Vector Distributions View
A new **Distributions** tab gives you deeper insight into your embeddings.

- Histogram views for vector norms and individual dimensions  
- Adjustable bins, density mode, and on‑demand plot generation  
- Compare distributions across collections — even across multiple active connections  
- Comparison list updates automatically as new connections are added

**What this means for you:**  
You can quickly understand the shape of your embeddings, spot anomalies, and compare datasets visually without exporting anything.

---

## Create Collection: Better Sample Data Controls
Creating a collection is now more transparent and flexible.

- The dialog shows which connection you're creating the collection on  
- New option to choose deterministic or randomized sample data  
- Deterministic samples help with reproducible demos and tests

**What this means for you:**  
You stay oriented, and you get more control over how sample data behaves.

---

## Connection Manager Enhancements
Selecting a saved connection now shows helpful details like host, port, and database name.

**What this means for you:**  
It’s easier to confirm you’re connecting to the right environment when juggling multiple setups.

---

## Test Coverage Improvements
Overall test coverage has increased to **59%**, strengthening reliability and giving contributors clearer signals when something breaks.

**What this means for you:**  
Vector Inspector is becoming more stable with every release, and future changes are safer and easier to review.

---