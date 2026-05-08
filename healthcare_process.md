# Assignment of Healthcare Records
This document deals with the assignment of healthcare records to a particular condition. There are three input tables of healthcare records:
1. **SMR01** - Hospital Admission Records
        - patient_id, condition_codes, admission_date, discharge_date
2. **GPReadCodes** - GP Read codes after GP attendance
        - patient_id, Read code, visit_date
3. **Prescriptions** - Each prescription of Salbutamol, Clarithromycin, or Amoxicillin
        - patient_id, prescription_name, dispensed_date

These records will be processed into single healthcare episodes combining GP visits, Hospital Admissions and Prescriptions using the following high-level process. Each individual GP Visit, Prescription and Hospital Admission will be categorised using the process at the [categorisation](ari_categorise.md). Episodes will be built using the [Episode Builder](ari_episodes.md).


## High-level process

**Normalisation**: Convert input tables into a single Healthcare Events table with unified schema:
* **ppid** - Unique child ID
* **condition_code** - ARI/Chronic Condition - How do we categorise this condition? Prescription does not have the fine grain details that other categories have, but are prescriptions always associated with GP Visits. Let's seee
* **event_start_date** - date of first healthcare incident
* **event_end_date** - end of last healthcare incident in episode
* **num_prescriptions** - number of prescriptions used by child over all episodes
* **num_gp_visits** - number of gp visits over episode
* **num_hospital_visits** - number of hospital visits during episode
* **num_hospital_days** - number of days spent in hospital during episode
* **cost** - total cost of episode = cost of prescriptions + gp_visits * cost_of_gp_visit  + cost_of_hospital_per_day * num_hospital_days

```mermaid
flowchart TD
    A[Clean GPReadCodes] --> A_assign["Categorise GP Visit as Condition"]
    A2[Clean Prescriptions] --> A2_assign["Categorise Prescription as Condition"]
    A3[Clean SMR01] --> A3_assign["Categorise Hospital Admission as Condition"]
    A_assign --> B[Normalise/Combine]
    A2_assign --> B
    A3_assign --> B
    B --> D[Partition by patient_id + condition]
    D --> E[Sort by start_date, then end_date desc]
    E --> F["Episode Builder (7-day gap rule)"]
    F --> G[Aggregate Metrics per Episode]
    G --> H[Episode Output Table]

  %% =========================
  %% Styling
  %% =========================
  classDef output fill:	 #2F5F93,color: #ffffff,stroke: #1e8449,stroke-width:2px;
  classDef record fill:	#C5333A,color: #ffffff,stroke: #1e8449,stroke-width:2px;
  classDef data fill: #E6C7AF,color: #000000,stroke: #7b7d7d,stroke-width:1px;
  class F record
  class A,A2,A3 data
  class H output
```
