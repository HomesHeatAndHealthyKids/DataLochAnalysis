# Assignment of Healthcare Records
This document deals with the assignment of healthcare records to a particular Acute Respiratory Infection. There are two types of healthcare records:
1. SMR01 - Hospital Admission Records
2. GP Read Code - GP Read codes after GP attendance

## Hospital Admissions
Hospital admissions often show multiple admissions for a single child. Admissions will be considered a single admission if there is a previous admission within the last 7 days. The first admission date will be the date when the admission is considered to have occurred. Total Day count will be summed up for the overlapping records. Diagnosis codes will not necessarily be the same for the different admissions. The diagnosis codes will be the diagnosis codes for the last discharge record. 

Hospital Admissions will be categorised in two ways:
i) Acute Respiratory Infection 
ii) Chronic Conditions
A record will be categorised in two ways and will potentially be double-counted.

### Acute Respiratory Infections
The flow chart below shows how an individual SMR01 record is assigned to a particular category of Acute Respiratory Infection. The contract states that: 

>a) Admission with ARI
HDR-UK phenotype code lists will be used. 
>
>i)	Lower respiratory tract infections:
https://phenotypes.healthdatagateway.org/phenotypes/PH488/version/1521/detail/ 
>
>ii)	Upper respiratory tract infections: https://phenotypes.healthdatagateway.org/phenotypes/PH158/version/316/detail/ 
>
>iii)	In addition, to ensure we include children presenting with viral induced wheeze (for which there is no ICD-10 code), we will also include the following ICD-10 codes (as previously published in (1)).
>-	R06.2	Wheezing
>-	R06.0	Dyspnoea
>-	R06.8	Other abnormalities of breathing
>
>The ICD-10 codes outlined above will be included if present in diagnosis positions 1-3. 
>iv)	In young children, there is no simple distinction between viral induced wheeze and asthma. As such, we will also include children admitted with asthma as viral infection is predominant trigger in this age group. The following ICD-10 codes will be included:
>-	J45 	Asthma
>-	J46 	Status asthmaticus
> 
>These asthma ICD-10 codes will only be included if present in diagnosis position 1. This will ensure only admissions directly due to asthma are included and avoid including historical diagnoses of asthma (i.e., excluding asthma if only present as a comorbidity).


These lists have been replaced by an ARI code list that contains ICD-10 codes for a variety of Respiratory Infections. The ARI code list contains lists of ICD10 codes for chronic conditions and a list of ICD10 codes for Acute Respiratory Infections. Each ICD10 code has a phenotype name and a clinical subcategory associated with it. The General ARI rule will assign the hospital admission to one of three phenotypes:
 - Ear and Upper Respiratory Tract Infections
 - Lower Respiratory Tract Infection
 - Wheezing

The Asthma Override rule will assign the hospital admission to the "Acute Asthma" phenotype. A hospital admission will only be assigned to one particular phenotype.



```mermaid
flowchart TB

    %% =========================
    %% Observed Variables
    %% =========================
    SMR_rec[SMR01 Discharge Record]
    ICD_10_non_asthma["ICD-10 in ARI Code List (excl. Asthma)"]
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
    Y[Count ARI Admission]
    N[Non ARI Admission]

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
    Diag_pos_2 --> |Otherwise| Diag_pos_3
    Diag_pos_3 --> |Otherwise| N

    
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
    classDef record fill:#4E86AD,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef include fill:#2ecc71,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef exclude fill:#e74c3c,color:#ffffff,stroke:#922b21,stroke-width:2px;
    classDef rule fill:#86AFC4,color:#ffffff,stroke:#1f618d,stroke-width:2px;
    classDef data fill:#E6C7AF,color:#000000,stroke:#7b7d7d,stroke-width:1px;

    class Y include
    class N exclude
    class R_ari,R_asthma rule
    class ICD_10_non_asthma,Diag_pos_1,Diag_pos_2,Diag_pos_3,ICD10_asthma data
    class SMR_rec record
```
### Chronic Conditions

Separately, an SMR01 admission record is categorised as a chronic condition using the following flowchart. The record is assigned to the phenotype name and clinical subcategory associated with the ICD10 code.

```mermaid
flowchart TB

    %% =========================
    %% Observed Variables
    %% =========================
    SMR_rec[SMR01 Discharge Record]
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
    Y[Count Chronic Admission]
    N[Non-Chronic Admission]

    %% =========================
    %% Causal Structure
    %% =========================

    SMR_rec --> Diag_pos_1

    %% Asthma override pathway
    Diag_pos_1 --> ICD10_Chronic


 
    %% Not First position
    Diag_pos_1 --> |Otherwise| Diag_pos_2
    Diag_pos_2 --> |Otherwise| Diag_pos_3
    Diag_pos_3 --> |Otherwise| N


    %% General Chronic pathway
    ICD10_Chronic --> R_Chronic
    Diag_pos_2 --> ICD10_Chronic
    Diag_pos_3 --> ICD10_Chronic


   

    %% General rule applies only if not Asthma
    R_Chronic -->|Chronic Condition in Pos 1–3| Y
   

    %% =========================
    %% Styling
    %% =========================
    classDef record fill:#4E86AD,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef include fill:#2ecc71,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef exclude fill:#e74c3c,color:#ffffff,stroke:#922b21,stroke-width:2px;
    classDef rule fill:#86AFC4,color:#ffffff,stroke:#1f618d,stroke-width:2px;
    classDef data fill:#E6C7AF,color:#000000,stroke:#7b7d7d,stroke-width:1px;

    class Y include
    class N exclude
    class R_Chronic rule
    class ICD10_Chronic,Diag_pos_1,Diag_pos_2,Diag_pos_3,ICD10_asthma data
    class SMR_rec record
```

## Assignment of GP Records

We will consider multiple GP read codes on a single day to be a single event. The multiple codes may affect how a GP visit is categorised. GP Visits, prescriptions and hospital admissions will all be considered separately for the analysis.

The vast majority of GP visits are categorised by a single Read code v2 value. However, like hospital admissions, GP Visits will be categorised in two ways. First, we will test whether the visit to the GP is for an Acute Respiratory Infection. 

### Acute Respiratory Infections
```mermaid
flowchart TB

    %% =========================
    %% Observed Variables
    %% =========================
    GP_rec[GP Event]
    Diag_pos_1[All GP Read Codes for a particular day]
    Read_ARI[ARI Read code v2 list]

    %% =========================
    %% Rule Nodes (Deterministic)
    %% =========================
    R_ARI((ARI Rule))
    
    %% =========================
    %% Outcomes
    %% =========================
    Y[Count ARI GP Visit]
    N[Non ARI GP Visit]

    %% =========================
    %% Causal Structure
    %% =========================

    GP_rec --> Diag_pos_1

    %% General ARI pathway
    Diag_pos_1 -->  |Any code in list| Read_ARI
    Diag_pos_1 --> |Otherwise| N


    %% General ARI pathway
    Read_ARI --> R_ARI


   

    %% General rule applies only if not Asthma
    R_ARI --> Y
   

    %% =========================
    %% Styling
    %% =========================
    classDef record fill:#4E86AD,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef include fill:#2ecc71,color:#ffffff,stroke:#1e8449,stroke-width:2px;
    classDef exclude fill:#e74c3c,color:#ffffff,stroke:#922b21,stroke-width:2px;
    classDef rule fill:#86AFC4,color:#ffffff,stroke:#1f618d,stroke-width:2px;
    classDef data fill:#E6C7AF,color:#000000,stroke:#7b7d7d,stroke-width:1px;

    class Y include
    class N exclude
    class R_ARI rule
    class ICD10_Chronic,Diag_pos_1,Read_ARI data
    class GP_rec record
```

If multiple GP read code v2 match ARIs on a particular day, then we will assign the ARI using the first record in the file for a particular child on a particular day. 