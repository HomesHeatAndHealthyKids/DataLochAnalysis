## Acute Respiratory Infection - Causal Diagram
Causal Diagram for Acute Respiratory Infections in housing taking us from exposure to living in an underheated home to an Acute Respiratory Infection.

```mermaid
graph TD

%% =========================
%% Subgraphs
%% =========================

subgraph Socioeconomic_and_Structural[Socioeconomic and Structural Confounders]
    SES((SES))
    Ethnicity((Ethnicity))
    Housing_age_tenure((Housing Age<br>Tenure))
    Energy_efficiency((Energy<br>Efficiency))
    Urban_rural((Urban<br>Rural))
    Climatic_region((Climatic<br>Region))
    Household_composition((Household<br>Composition))
end

subgraph Indoor_Environment_and_Biology[Indoor Environment And Biology]
    Outdoor_AP((Outdoor<br>Pollution))
    Indoor_air_quality((Indoor Air<br>Quality))
    Indoor_temp((Indoor<br>Temperature))
    Damp((Damp))
    Child_immune_function((Child immune<br>function))
    Household_transmission((Household<br>transmission))
end

subgraph Exposure
    Underheated_home((Underheated<br>Home))
end

subgraph Outcome
    Healthcare_ARI((Healthcare<br>ARI))
end

%% =========================
%% Structural pathways
%% =========================


SES --> Housing_age_tenure
SES --> Energy_efficiency
SES --> Underheated_home
SES --> Indoor_air_quality
SES --> Healthcare_ARI

Ethnicity --> SES
Ethnicity --> Urban_rural
Ethnicity --> Energy_efficiency
Ethnicity --> Indoor_air_quality
Ethnicity --> Healthcare_ARI
Ethnicity --> Underheated_home
Ethnicity --> Household_composition

Housing_age_tenure --> Energy_efficiency

Energy_efficiency --> Indoor_air_quality
Energy_efficiency --> Underheated_home

Urban_rural --> Outdoor_AP
Urban_rural --> Energy_efficiency
Urban_rural --> Underheated_home


Climatic_region --> Underheated_home
Climatic_region --> Damp
Climatic_region --> Healthcare_ARI

Outdoor_AP --> Indoor_air_quality
Outdoor_AP --> Healthcare_ARI

Household_composition --> Household_transmission
Household_composition --> Damp
Household_composition --> Indoor_air_quality

Household_transmission --> Healthcare_ARI

%% =========================
%% Mediated (indirect) pathways
%% =========================

Indoor_air_quality -.-> Healthcare_ARI

Indoor_temp -.-> Damp
Indoor_temp -.-> Child_immune_function

Child_immune_function -.-> Healthcare_ARI

Damp -.-> Healthcare_ARI

%% =========================
%% Highlighted causal pathway
%% =========================

Underheated_home -->|Direct effect| Healthcare_ARI

%% Optional extended mediated pathway emphasis
Underheated_home -.-> Indoor_temp
Underheated_home -.-> Indoor_air_quality

%% =========================
%% Styling
%% =========================

classDef structural fill:#f4a3a3,stroke:#333,stroke-width:1px;
classDef indoor fill:#7ec8e3,stroke:#333,stroke-width:1px;
classDef exposure fill:#c9e265,stroke:#2e7d32,stroke-width:2px;
classDef outcome fill:#db1c39,stroke:#0d47a1,stroke-width:2px;

class SES,Ethnicity,Housing_age_tenure,Energy_efficiency,Urban_rural,Climatic_region,Household_composition structural;
class Outdoor_AP,Indoor_air_quality,Indoor_temp,Damp,Child_immune_function,Household_transmission indoor;
class Underheated_home exposure;
class Healthcare_ARI outcome;

%% Edge styling (green causal pathway)
linkStyle 32 stroke:#2e7d32,stroke-width:5px;
linkStyle 29 stroke:#2e7d32,stroke-width:3px;
linkStyle 33 stroke:#2e7d32,stroke-width:3px;
linkStyle 34 stroke:#2e7d32,stroke-width:3px;
linkStyle 32 stroke:#2e7d32,stroke-width:3px;
```
