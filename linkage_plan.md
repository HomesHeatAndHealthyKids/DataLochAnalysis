
## Data linkage plan:

```mermaid
flowchart LR
 subgraph CHILD["Child spine"]
        C["Demographics<br>ppid"]
        AH["Geospatial refs<br>ppid | month | uprn_pid | postcode_pid | climate_grid_pid | pollution_grid_pid"]
        SH["SIMD history<br>ppid | month | SIMD"]
  end
 subgraph EVENTS["Care events (event-grain)"]
        B["Birth events (SMR02)<br>event_id | ppid | date | fields"]
        H["Hospital admissions (SMR01)<br>episode_id | ppid | admit/discharge | fields"]
        G["GP events<br>record_id | ppid | date | fields"]
        P["Prescriptions<br>record_id | ppid | date | fields"]
  end
 subgraph PROPERTY["Property & housing"]
        EPC["EPC certificates<br>uprn_pid | assessment_date | current | potential | SAP"]
  end
 subgraph AREA["Area context"]
        PC["uZero Postcode Data<br>postcode_pid | postcode data | codes"]
        OAC["uZero Output Area Data<br>oa_pid | Output Area data | codes"]
  end
 subgraph ENV["Environment"]
        CGRID["Climate grid<br>climate_grid_pid | month | variables"]
        PGRID["Pollution grid<br>pollution_grid_pid | year | PM2.5 | NO2"]
  end
    C -- ppid --> B & H & G & P & AH & SH
    AH -- oa_pid --> OAC
    AH -- uprn_pid --> EPC
    AH -- postcode_pid --> PC
    AH -- climate_grid_pid --> CGRID
    AH -- pollution_grid_pid --> PGRID
   
    style ENV fill:#C8E6C9
    style EVENTS fill:#BBDEFB
    style PROPERTY fill:#FFF9C4
    style AREA fill:#FFD600
    style CHILD fill:#FFE0B2
```