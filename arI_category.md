# Assignment of Hospital Admission Records
Hospital admissions often show multiple admissions for a single child Admissions will be considered a single admission if a previous admission within the last 7 days. Total Day count will be summed up for the overlapping records. Diagnosis codes will not necessarily be the same for the different admissions. The diagnosis codes will be the diagnosis codes for the last record. 

## Acute Respiratory Infections
The flow chart below shows how an individual SMR01 record is assigned to a particular category of Acute Respiratory Infection. The contract states that: 

>Any admission with ICD-10 codes outlined in the Acute Respiratory Infection code list will be counted if the ICD-10 codes are present in diagnosis positions 1-3 of the hospital admission record in SMR01. For an asthma admission, the ICD-10 code must only appear in diagnosis position 1. This will exclude diagnoses where asthma is only present as a comorbidity.

```mermaid
flowchart TB

    %% =========================
    %% Observed Variables
    %% =========================
    SMR_rec[SMR01 Admission Record]
    ICD_10_non_asthma[ICD-10 in ARI Code List]
    Diag_pos_1[MAIN_CONDITION]
    Diag_pos_2[OTHER_CONDITION_1]
    Diag_pos_3[OTHER_CONDITION_2]
    ICD10_asthma[Asthma ICD-10 Code]

    %% =========================
    %% Rule Nodes (Deterministic)
    %% =========================
    R_ari((General ARI Rule))
    R_asthma((Asthma Override Rule))

    %% =========================
    %% Outcomes
    %% =========================
    Y[Count Admission]
    N[Exclude Admission]

    %% =========================
    %% Causal Structure
    %% =========================

    SMR_rec --> Diag_pos_1

    %% Asthma override pathway
    Diag_pos_1 --> ICD10_asthma
    ICD10_asthma --> R_asthma

    %% General ARI pathway
    Diag_pos_1 --> ICD_10_non_asthma

    %% Not First position
    Diag_pos_1 --> |Otherwise| Diag_pos_2
    Diag_pos_2 -->|Otherwise| Diag_pos_3
    Diag_pos_3 -->|Otherwise| N

    
    %% General ARI pathway
    ICD_10_non_asthma --> R_ari
    Diag_pos_2 --> ICD_10_non_asthma
    Diag_pos_3 --> ICD_10_non_asthma


    %% Override logic
    R_asthma -->|Asthma in Position 1| Y

    %% General rule applies only if not Asthma
    R_ari -->|ARI & Pos 1–3 & Not Asthma| Y
   

    %% =========================
    %% Styling
    %% =========================
    classDef record fill:#1ad9e0,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef include fill:#2ecc71,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef exclude fill:#e74c3c,color:#ffffff,stroke:#922b21,stroke-width:2px;
    classDef rule fill:#5dade2,color:#ffffff,stroke:#1f618d,stroke-width:2px;
    classDef data fill:#f4f6f7,color:#000000,stroke:#7b7d7d,stroke-width:1px;

    class Y include
    class N exclude
    class R_ari,R_asthma rule
    class ICD_10_non_asthma,Diag_pos_1,Diag_pos_2,Diag_pos_3,ICD10_asthma data
    class SMR_rec record
```
## Chronic Conditions

Separately, an SMR01 admission record is categorised as a chronic condition using the following flowchart.

```mermaid
flowchart TB

    %% =========================
    %% Observed Variables
    %% =========================
    SMR_rec[SMR01 Admission Record]
    Diag_pos_1[MAIN_CONDITION]
    Diag_pos_2[OTHER_CONDITION_1]
    Diag_pos_3[OTHER_CONDITION_2]
    ICD10_Chronic[Chronic ICD-10 Code]

    %% =========================
    %% Rule Nodes (Deterministic)
    %% =========================
    R_Chronic((Chronic Rule))
    
    %% =========================
    %% Outcomes
    %% =========================
    Y[Count Admission]
    N[Exclude Admission]

    %% =========================
    %% Causal Structure
    %% =========================

    SMR_rec --> Diag_pos_1

    %% Asthma override pathway
    Diag_pos_1 --> ICD10_Chronic


 
    %% Not First position
    Diag_pos_1 --> |Otherwise| Diag_pos_2
    Diag_pos_2 -->|Otherwise| Diag_pos_3
    Diag_pos_3 -->|Otherwise| N


    %% General Chronic pathway
    ICD10_Chronic --> R_Chronic
    Diag_pos_2 --> ICD10_Chronic
    Diag_pos_3 --> ICD10_Chronic


   

    %% General rule applies only if not Asthma
    R_Chronic -->|Chronic Condition in Pos 1–3| Y
   

    %% =========================
    %% Styling
    %% =========================
    classDef record fill:#1ad9e0,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef include fill:#2ecc71,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef exclude fill:#e74c3c,color:#ffffff,stroke:#922b21,stroke-width:2px;
    classDef rule fill:#5dade2,color:#ffffff,stroke:#1f618d,stroke-width:2px;
    classDef data fill:#f4f6f7,color:#000000,stroke:#7b7d7d,stroke-width:1px;

    class Y include
    class N exclude
    class R_Chronic rule
    class ICD10_Chronic,Diag_pos_1,Diag_pos_2,Diag_pos_3,ICD10_asthma data
    class SMR_rec record
```

