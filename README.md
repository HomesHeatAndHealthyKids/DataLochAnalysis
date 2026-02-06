# DataLochAnalysis

Various files relating to analysis of DataLoch data including:
1. code_list.csv - lists of ICD 10 and Read V2 codes identifying different conditions
2. build_phenotype_lists - colab notebook used to build the codelist from HDRUK codelists - identifies codelist and any further data manipulation
3. analysis_plan.md - file setting out plan for analysis of DataLoch data
4. data_linkage.md - file showing linkage of DataLoch data

## Code_list.csv

Code list that combines chronic paediatric conditions from harmonised code lists with code lists defining the Acute Respiratory Infections. The two lists are separated by the field “Phenotype_category.” The “code” field includes both ICD-10 (with dots removed) and 7‑character Read V2 codes. If you’d like a de‑duplicated view within each phenotype_category, just filter to rows where Rank = 1.

### Columns:

* *Phenotype_category* — "Acute Respiratory Infection" or "Chronic Paediatric Condition"
* *Code* — ICD10 code (no “.”) or 7‑character Read V2 code
* *Description* — text description of the code
* *Code_system* — indicates code system used in *Code* field - contains either "ICD10 codes" or "Read V2 codes"
* *Clinical_subcategory* — further sub‑categorisation of the phenotype (e.g. "Other neurological - cerebral palsy and paralysis", "Other nuerological - neurological devices")
* *Phenotype_name* — name of the phenotype (e.g. "Wheezing", "Transplant", "Other neurological", etc.)
* *Rank* — 1 or 2 (use Rank = 1 for a unique list within each phenotype_category)
