# Code List - DataLoch Contract
This code list is taken from DL_2023_023 Application v4.1.docx. A later amendment will be filed. 

**Primary outcome of interest**
----------------------------
Define primary outcome – the variable you consider to be the most important among the many dependent variables to be examined in the study. Comment on how the outcome of interest is going to be defined e.g. disease codes, prescriptions, deaths, hospital admissions. State data sources (if known).
----------------------------

<ol type="a">
    <li>Admission to hospital with acute respiratory infection (ARI)</li>
    <li>GP-coded ARI</li>
    <li>Amoxicillin prescription</li>
    <li>Salbutamol prescription</li>
</ol>




The primary outcome of interest will be admission to hospital with ARI. This outcome and the other key outcomes of interest are defined below.



## Code lists for outcomes:
a) Admission with ARI
HDR-UK phenotype code lists will be used. 

i)	Lower respiratory tract infections:
https://phenotypes.healthdatagateway.org/phenotypes/PH488/version/1521/detail/ 

ii)	Upper respiratory tract infections: https://phenotypes.healthdatagateway.org/phenotypes/PH158/version/316/detail/ 

iii)	In addition, to ensure we include children presenting with viral induced wheeze (for which there is no ICD-10 code), we will also include the following ICD-10 codes (as previously published in (1)).

-	R06.2	Wheezing
-	R06.0	Dyspnoea
-	R06.8	Other abnormalities of breathing

The ICD-10 codes outlined above will be included if present in diagnosis positions 1-3. 

iv)	In young children, there is no simple distinction between viral induced wheeze and asthma. As such, we will also include children admitted with asthma as viral infection is predominant trigger in this age group. The following ICD-10 codes will be included:
-	J45 	Asthma
-	J46 	Status asthmaticus

These asthma ICD-10 codes will only be included if present in diagnosis position 1. This will ensure only admissions directly due to asthma are included and avoid including historical diagnoses of asthma (i.e., excluding asthma if only present as a comorbidity).

b) GP-coded ARI
HDR-UK phenotype code lists will be used. 
i)	Lower respiratory tract infections:
https://phenotypes.healthdatagateway.org/phenotypes/PH899/version/1877/detail/
 
ii)	Upper respiratory tract infections
https://phenotypes.healthdatagateway.org/phenotypes/PH906/version/1891/detail/ 

iii)	Wheeze read codes (mapped from ICD-10 using (2) and from Clinical Terminology Read Code Browser - Scottish Read codes v2)

-	R060900	[D]Wheezing	
-	1737.11  	Wheezing symptom	
-	232H.00	On examination - inspiratory wheeze	
-	173e.		Viral wheeze	
-	R060E		[D]Mild wheeze	
-	R060G		[D]Severe wheeze	
-	R060F		[D]Moderate wheeze	
-	173e.		Viral induced wheeze	
-	R060H		[D]Very severe wheeze	
-	2326\.		O/E - expiratory wheeze	
-	173B.		Nocturnal cough / wheeze	
-	232H.		On examination - inspiratory wheeze	

iv)	Acute asthma presentation (acute presentations filtered from HDR-UK phenotype code list and using Clinical Terminology Read Code Browser - Scottish Read codes v2)https://phenotypes.healthdatagateway.org/concepts/C2421/version/6242/detail/)

-	H33z0	Status asthmaticus NOS
-	H33z011 Severe asthma attack
-	H33z1	Asthma attack
-	H3311	Intrinsic asthma with status asthmaticus
-	H3301	Extrinsic asthma with status asthmaticus


c) Amoxicillin
Amoxicillin (a penicillin) is the most commonly prescribed antibiotic for ARIs in children. However, some children are allergic to amoxicillin. As such, we will also examine clarithromycin prescriptions (macrolide antibiotic which is prescribed for ARIs when children are allergic to penicillin). 

d) Salbutamol
Salbutamol prescriptions will be considered as a proxy for children presenting to their GP with wheeze. Some salbutamol prescriptions will also be given as routine asthma care. Whilst we will not be able to differentiate between acute and routine prescription in our analyses, this limitation will be made clear in our methods and discussion. 


### References:
1.	Al-Mahtot M, et al. Changing characteristics of hospital admissions but not the children admitted-a whole population study between 2000 and 2013. Eur J Pediatr 2018;177:381-388.
2.	Shah A. CALIBER codelists-package: Generate ICD, Read and OPCS codelists in CALIBER codelists: Generate ICD10, Read and OPCS codelists. https://rdrr.io/rforge/CALIBERcodelists/man/CALIBERcodelists-package.html 

