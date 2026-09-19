# Implementation traceability

Software scope is deliberately explicit. A registered layer/model is not an implemented solver.

## Layers L00–L30

| ID | Source layer | Code / record | Actual implemented scope |
|---|---|---|---|
| L00 | Контракт утверждений | evaluation.py | IMPLEMENTED_CLAIM_LOCK |
| L01 | Реестр моделей | data/models.json | CATALOG_24_MODELS |
| L02 | Символьная геометрия | symbolic.py | M00_M01_M04_ONLY |
| L03 | Валидатор уравнений поля | physics.py + symbolic.py | M04_FORMAL_SOURCE_ONLY |
| L04 | Топология и глобальные идентификации | docs/SCIENCE.md | FIXED_M04_TOPOLOGY_ONLY |
| L05 | Геометрия горловины | physics.py | M04_EXACT |
| L06 | Горизонты и захват | physics.py | STATIC_BENCHMARK_ONLY |
| L07 | Геодезическая проходимость | numerics.py | M04_TEST_GEODESICS |
| L08 | Приливные нагрузки | physics.py | RADIAL_TEST_TRAVELER_ONLY |
| L09 | Энергетические условия | physics.py | M04_EXACT |
| L10 | Микрофизика источника | physics.py | FORMAL_GHOST_ONLY_PHYSICAL_UNRESOLVED |
| L11 | Квантовые энергетические неравенства | quantum.py | FLAT_FIELD_BENCHMARK_ONLY |
| L12 | Полуклассическая обратная реакция | evaluation.py | UNRESOLVED |
| L13 | Начальные данные ADM | physics.py + nr.py | STATIC_CONSTRAINT_AND_EXTERNAL_DIAGNOSTICS |
| L14 | Нелинейная эволюция | waves.py + nr.py | TEST_FIELD_ONLY_GR_EVOLUTION_UNAVAILABLE |
| L15 | Устойчивость к payload | evaluation.py | UNRESOLVED |
| L16 | Мировые линии устьев | anchors.py | PIECEWISE_INERTIAL_DIAGNOSTIC |
| L17 | Адресация и удаленный якорь | anchors.py | HMAC_SIMULATED_OR_SIGNAL_ANCHORS |
| L18 | Глобальная причинность | evaluation.py | UNRESOLVED |
| L19 | Детектор CTC | causality.py | FINITE_GRAPH_NEGATIVE_CYCLES_ONLY |
| L20 | Причинный предохранитель | causality.py + control.py | REDUCED_SIMULATION_VETO |
| L21 | Контроллер геометрии | control.py | SIMULATED_ANALOG_PID_ONLY |
| L22 | Метрология поля и времени | metrology.py | CSV_S21_PHASE_DELAY |
| L23 | Энергия, тепло и излучение | control.py + metrology.py | SIMULATED_BOUNDED_DRIVE_PASSIVE_LINE |
| L24 | Payload interface | evaluation.py | CLEARANCE_AND_TIDAL_DIAGNOSTICS |
| L25 | Физическая безопасность | control.py | SOFTWARE_VETO_NOT_CERTIFIED_HARDWARE |
| L26 | Аналоговые эксперименты | metrology.py + waves.py | SIMULATION_AND_CSV_ANALYSIS |
| L27 | Квантовый симулятор | quantum.py | TELEPORTATION_ONLY_NOT_SYK |
| L28 | Верификация и валидация | tests/ | EXECUTABLE_LOCAL_TESTS |
| L29 | Происхождение и защита данных | storage.py | HASH_CHAIN_AND_MANIFESTS |
| L30 | Межмодельный анализ и решение | evaluation.py | EXPLICIT_GATE_VECTOR_NO_AGGREGATE_PHYSICS_PASS |

## Models M00–M23

| ID | Model | Implementation | Limitation |
|---|---|---|---|
| M00 | Minkowski | symbolic + wave | Flat-space control; no throat |
| M01 | Schwarzschild / Einstein-Rosen bridge | symbolic + invariant API | Exterior vacuum only; Einstein-Rosen bridge not traversable |
| M02 | Reissner-Nordstrom bridge | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M03 | Morris-Thorne general | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M04 | Morris-Thorne zero-redshift b=r0^2/r | full benchmark + geodesics + test waves | No physical source, formation or nonlinear stability |
| M05 | Ellis-Bronnikov | restricted formal massless source in M04 | Only the zero-mass Ellis branch; ghost scalar is not admissible ordinary matter |
| M06 | Thin-shell Visser | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M07 | Ring wormhole | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M08 | Einstein-Dirac-Maxwell candidate | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M09 | MMP four-dimensional long wormhole | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M10 | Humanly traversable RS-II model | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M11 | Gao-Jafferis-Wall | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M12 | Maldacena-Qi | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M13 | Near-horizon Casimir perturbation 2026 | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M14 | Rotating Einstein-Maxwell-dilaton candidate 2026 | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M15 | Double-trace shear/sound 2026 | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M16 | Simpson-Visser black-bounce | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M17 | Time-shifted two-mouth reduction | route guard + graph witness | Finite reduction only, no global causal certificate |
| M18 | Misner-type causal boundary | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M19 | Quantum processor SYK experiment | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M20 | Electromagnetic metamaterial wormhole | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M21 | Magnetic wormhole | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M22 | Hydrodynamic wormhole analog | CATALOG_ONLY | No dedicated solver in this release; equations and validation must be supplied |
| M23 | Quantum teleportation | exact three-qubit statevector | Quantum state transfer needs classical communication; no matter transport |

## Physical gates

PA-00–PA-11 are recorded by `evaluation.py` and remain UNRESOLVED/STOP.
The absence of an implementation is never mapped to PASS. No value submitted by
the client can replace a source theory, global certificate or experimental evidence.

## Device modules

| ID | Source module | Release implementation |
|---|---|---|
| MOD-01 | Model Registry | Versioned catalog + strict M04 contract; no digital publisher signatures |
| MOD-02 | Geometry Engine | Symbolic M00/M01/M04 + analytical M04 |
| MOD-03 | Geodesic Engine | Fixed M04 test geodesics |
| MOD-04 | Source/QEI Engine | Formal ghost scalar and flat-field QEI only |
| MOD-05 | NR Bridge | External convergence CSV; no thorn or coupled evolution |
| MOD-06 | Anchor Registry | HMAC simulated/signal-node records; no physical mouths |
| MOD-07 | Metrology | S21 CSV/phase/delay and kinematic clocks; no instrument drivers |
| MOD-08 | Causal Guard | Reduced guard and simulation veto; no global certificate |
| MOD-09 | Analog Plant | Second-order numerical plant and passive RLGC model |
| MOD-10 | Geometry Actuator | UNAVAILABLE; physical request rejected |
| MOD-11 | Payload Gate | Clearance and radial traveler tidal diagnostic; physical authorization false |
| MOD-12 | Provenance Store | SQLite artifacts, telemetry checkpoints, hash chain, verified exports |
