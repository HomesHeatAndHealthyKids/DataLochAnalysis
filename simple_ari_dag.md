## Simplified DAG
This is a simplified version of the Causal Diagram for Acute Respiratory Infections that shows the pathway between exposure to an underheated home
and an Acute Respiratory Infection. This diagram helps us to decide which variables are potential confounders and should be adjusted for in any 
analysis of the data.

```mermaid
graph TD

%% =========================
%% Subgraphs
%% =========================

subgraph Structural_Confounders[Structural Confounders]
    Socioeconomic_Factors[Socioeconomic Factors]
    Climatic_Region[Climatic Region]
    Household_Composition[Household Composition]
end

subgraph Mediating_Pathways[Mediating Pathways]
    Indoor_Environment[Indoor Environment]
    Susceptibility_Transmission[Susceptibility Transmission]
end

subgraph Exposure
    Underheated_Home((Underheated<br>Home))
end

subgraph Outcome
    Healthcare_ARI((Healthcare<br>ARI))
end

%% =========================
%% Core Confounding Structure
%% =========================

Socioeconomic_Factors --> Underheated_Home
Socioeconomic_Factors --> Healthcare_ARI

Climatic_Region --> Underheated_Home
Climatic_Region --> Healthcare_ARI

Household_Composition --> Healthcare_ARI

%% =========================
%% Causal Pathway
%% =========================

Underheated_Home --> Indoor_Environment
Indoor_Environment --> Susceptibility_Transmission
Susceptibility_Transmission --> Healthcare_ARI

Underheated_Home --> Healthcare_ARI

%% =========================
%% Styling
%% =========================

classDef structural fill:#f4a3a3,stroke:#333,stroke-width:1px;
classDef mediator fill:#7ec8e3,stroke:#333,stroke-width:1px;
classDef exposure fill:#c9e265,stroke:#2e7d32,stroke-width:2px;
classDef outcome fill:#db1c39,stroke:#0d47a1,stroke-width:2px;

class Socioeconomic_Factors,Climatic_Region,Household_Composition structural;
class Indoor_Environment,Susceptibility_Transmission mediator;
class Underheated_Home exposure;
class Healthcare_ARI outcome;

```