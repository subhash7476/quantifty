# DRA Implementation Plan

**Document:** Daily Regime Analyzer — Implementation Roadmap
**Architecture Reference:** MSI-009 (Frozen v1.0), MSI-001–008 (Frozen v1.0)
**Date:** 2026-07-03
**Status:** Accepted — Implementation Baseline (v1.1)
**Audience:** Technical Lead (ChatGPT), Lead Engineer (DeepSeek), Adversarial Reviewer (GLM)
**Review:** Approved with two engineering recommendations applied. Review and certification history: `IMPLEMENTATION_LEDGER.md`.
**v1.1 (2026-07-04):** Editorial amendment — file naming and test path reconciliation, M0 scope alignment, error hierarchy completion. No architectural change. See Amendment Log at end of document.

---

## 0. Preamble

This plan implements the frozen MSI-009 architecture exactly as specified. It introduces no new architectural concepts. It does not design the Platform, the Strategy Framework, or any MSI specification. It translates architecture into engineering deliverables.

All component names, contracts, and data flows are traceable to specific sections of MSI-001 through MSI-009.

---

## 1. Runtime Component Decomposition

The DRA implements the complete MSI Runtime Pipeline (MSI-009 §4). It decomposes into six stateless, single-responsibility components connected by frozen DTO contracts.

```
┌──────────────────────────────────────────────────────────┐
│                      DRAOrchestrator                     │
│  (stateless coordinator; constructs and wires pipeline)  │
└──────┬──────┬──────┬──────┬──────┬───────────────────────┘
       │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼
  ┌──────┐┌──────┐┌──────┐┌──────┐┌───────────┐
  │ObsRdr││EvdBld││ArtLdr││ArtEvl││KnwlBld+Pub│
  └──────┘└──────┘└──────┘└──────┘└───────────┘
```

### 1.1 ObservationReader

**MSI trace:** MSI-009 §7, MSI-003 §4

Reads Platform-persisted market data through the MSI-003 read-contract over DuckDB stores. Produces canonical `Observation` DTOs. No acquisition, no storage — read-only.

```
Input:  evaluation_date (date), symbol list, DuckDB path
Output: List[Observation]
```

### 1.2 EvidenceBuilder

**MSI trace:** MSI-009 §8, MSI-004 §2/§8

Applies artifact-carried construction rules to Observations. Produces immutable `Evidence` objects. Rules originate from the artifact; the builder authors no rules.

```
Input:  List[Observation], artifact (for construction rules)
Output: List[Evidence]
```

### 1.3 ArtifactLoader

**MSI trace:** MSI-009 §13, MSI-007 §7–8, MSI-008 §9

Loads, validates, and verifies a Published MSI Artifact. Checks compatibility (MSI-007 §8), confirms Active status (MSI-008 §9), and returns a validated artifact handle. The artifact is opaque — the loader does not inspect inference internals.

```
Input:  artifact_path or artifact_identifier
Output: PublishedArtifact (validated handle)
```

### 1.4 ArtifactEvaluator

**MSI trace:** MSI-009 §9, MSI-005 §7/§13

The MSI-005 runtime artifact-evaluation engine. Takes Evidence + Artifact, produces `MarketState` (collection of `Estimate` objects). Deterministic; identical inputs produce identical outputs.

```
Input:  List[Evidence], PublishedArtifact
Output: MarketState
```

### 1.5 KnowledgeBuilder

**MSI trace:** MSI-009 §10, MSI-005 §11

Constructs the `KnowledgeObject` from `MarketState` + provenance metadata. Conforms to MSI-005 §11 schema. No standalone scalar Confidence/Uncertainty.

```
Input:  MarketState, artifact metadata, provenance chain
Output: KnowledgeObject
```

### 1.6 KnowledgePublisher

**MSI trace:** MSI-009 §11, MSI-005 §6

Exposes `KnowledgeObject` through Platform-defined interfaces. Strategies consume Knowledge through this publisher. The publisher is a passive read-side — strategies pull, publisher never pushes.

```
Input:  KnowledgeObject
Output: None (writes to platform-accessible store)
```

### 1.7 DRAOrchestrator

**MSI trace:** MSI-009 §5–6

Stateless coordinator. Wires the pipeline, manages execution order, and handles errors. Single entry point: `run(date, artifact_path) -> KnowledgeObject`.

---

## 2. Package Structure

```
core/msi/                              # New Platform package
    __init__.py                        # Package docstring; exports public API
    contracts/
        __init__.py
        observation.py                 # Observation DTO (MSI-003 §5)
        evidence.py                    # Evidence DTO (MSI-004 §7)
        estimate.py                    # Estimate DTO (MSI-002 §4.7)
        market_state.py                # MarketState DTO (MSI-002 §4.8)
        knowledge.py                   # KnowledgeObject DTO (MSI-005 §11)
        artifact.py                    # ArtifactMetadata + PublishedArtifact protocol
    interfaces/
        __init__.py
        observation_reader.py          # ObservationReader ABC
        evidence_builder.py            # EvidenceBuilder ABC
        artifact_loader.py             # ArtifactLoader ABC
        artifact_evaluator.py          # ArtifactEvaluator ABC
        knowledge_builder.py           # KnowledgeBuilder ABC
        knowledge_publisher.py         # KnowledgePublisher ABC
    dra/
        __init__.py
        orchestrator.py                # DRAOrchestrator
        duckdb_observation_reader.py   # MSI-003 read-contract over DuckDB
        default_evidence_builder.py    # Artifact-rule evidence construction
        filesystem_artifact_loader.py  # Filesystem-based artifact loading
        default_artifact_evaluator.py  # MSI-005 runtime evaluation engine
        default_knowledge_builder.py   # MSI-005 §11 Knowledge construction
        duckdb_knowledge_publisher.py  # DuckDB persistence + strategy read API
        knowledge_reader.py            # Read-only strategy-facing facade (§11)
        provenance.py                  # Provenance chain builder
        errors.py                      # DRA-specific exception hierarchy

tests/msi/                             # Platform convention: tests live at repo root
    __init__.py
    conftest.py                        # Shared fixtures (dates, test data, mock artifacts)
    fixtures/                          # Test DuckDB + reference test artifact (M1)
    test_contracts.py                  # DTO immutability + frozen contracts
    test_interfaces.py                 # ABC inheritance + abstract methods
    test_observation_reader.py
    test_evidence_builder.py
    test_artifact_loader.py
    test_artifact_evaluator.py
    test_knowledge_builder.py
    test_knowledge_publisher.py
    test_provenance.py
    test_orchestrator.py               # Integration — full pipeline
    test_replay.py                     # Deterministic replay across modes
```

**Placement rationale:** `core/msi/` is the Platform-side runtime implementation of the MSI Architecture. It is NOT `core/strategies/` (which would be a Constitution violation — strategies own signals, MSI owns knowledge). It is NOT `core/analytics/` (analytics produce facts; MSI produces governed Knowledge). It is a new top-level `core/` package because MSI is an architectural layer (MSI-001 §4.2: "Classification: Platform").

**Three-layer structure:**
- `contracts/` — frozen DTOs that implement MSI ontology entities. Zero logic. Immutable.
- `interfaces/` — abstract base classes (ABCs) defining component contracts. Each mirrors a pipeline stage from MSI-009 §5.
- `dra/` — concrete implementations of each interface. Named by implementation strategy (e.g., `duckdb_observation_reader`, `filesystem_artifact_loader`).

This separation makes testing trivial: every component can be mocked at its interface boundary. It also allows future Market State Engines to reuse interfaces without touching DRA implementations.

---

## 3. Public Interfaces

### 3.1 DTO Contracts (frozen dataclasses)

All DTOs are `@dataclass(frozen=True)`. No setters. No mutation. Identical to the `core/events.py` pattern (`OHLCVBar`, `SignalEvent`, etc.).

```python
# core/msi/contracts/observation.py  —  MSI-003 §5
@dataclass(frozen=True)
class Observation:
    observation_id: str
    timestamp: datetime          # point-in-time
    instrument_id: str           # canonical (e.g. "NSE_INDEX|Nifty 50")
    source_reference: str        # Platform-recorded source
    observable_type: str         # e.g. "close_price", "volume", "implied_volatility"
    measured_value: float
    measurement_units: str       # e.g. "INR", "percentage", "index_points"
    provenance_ref: str          # references Platform provenance
    quality_metadata: dict       # completeness, validity, consistency, timeliness

# core/msi/contracts/evidence.py  —  MSI-004 §7
@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_observation_ids: tuple[str, ...]   # immutable reference to Observations
    construction_timestamp: datetime
    evidence_type: str
    evidence_value: float
    artifact_version: str        # version of construction rules applied
    provenance_metadata: dict
    quality_metadata: dict
    version: str

# core/msi/contracts/estimate.py  —  MSI-002 §4.7
@dataclass(frozen=True)
class Estimate:
    latent_variable: str         # e.g. "market_regime", "trend_strength"
    value: float
    uncertainty: float           # quantified uncertainty (MSI-OD-005)
    dimension: str               # e.g. "regime_class", "trend_magnitude"

# core/msi/contracts/market_state.py  —  MSI-002 §4.8
@dataclass(frozen=True)
class MarketState:
    evaluation_timestamp: datetime
    estimates: tuple[Estimate, ...]   # multidimensional (MSI-OD-001)

# core/msi/contracts/knowledge.py  —  MSI-005 §11
@dataclass(frozen=True)
class KnowledgeObject:
    knowledge_id: str
    evaluation_timestamp: datetime
    artifact_version: str
    runtime_version: str
    market_state: MarketState
    provenance_reference: str
```

### 3.2 Artifact Protocol

**MSI trace:** MSI-007 §11 (opaque executable), MSI-007 §7 (metadata contract)

```python
# core/msi/contracts/artifact.py

@dataclass(frozen=True)
class ArtifactMetadata:
    """MSI-007 §7 runtime binding metadata."""
    artifact_id: str
    artifact_version: str
    schema_version: str
    validation_id: str           # owned by MSI-006; opaque reference
    publication_timestamp: datetime
    compatibility_version: str
    runtime_compatibility: str
    provenance_reference: str


class PublishedArtifact(ABC):
    """MSI-007 §11: opaque executable object. Runtime never inspects internals."""

    metadata: ArtifactMetadata

    @abstractmethod
    def get_evidence_rules(self) -> dict:
        """Return validated evidence-construction rules (MSI-004 §2)."""
        ...

    @abstractmethod
    def evaluate(self, evidence: tuple[Evidence, ...]) -> MarketState:
        """MSI-005 §7: deterministic evaluation. Evidence + Artifact → MarketState."""
        ...
```

### 3.3 DRAOrchestrator

```python
# core/msi/dra/orchestrator.py

class DRAOrchestrator:
    """MSI-009 §5–6: stateless pipeline coordinator."""

    def __init__(
        self,
        observation_reader: ObservationReader,
        evidence_builder: EvidenceBuilder,
        artifact_loader: ArtifactLoader,
        artifact_evaluator: ArtifactEvaluator,
        knowledge_builder: KnowledgeBuilder,
        knowledge_publisher: KnowledgePublisher,
    ): ...

    def run(self, evaluation_date: date, artifact_ref: str) -> KnowledgeObject:
        """
        Execute the complete DRA pipeline for one evaluation date.

        Pipeline:
            1. Read Observations (MSI-003)
            2. Load + validate Artifact (MSI-007/008)
            3. Construct Evidence from artifact rules (MSI-004)
            4. Evaluate artifact → MarketState (MSI-005)
            5. Build KnowledgeObject (MSI-005 §11)
            6. Publish Knowledge (MSI-005 §6)

        Returns:
            KnowledgeObject with complete provenance chain.

        Raises:
            ArtifactLoadError — artifact not found, incompatible, or not Active
            ObservationReadError — required data unavailable for evaluation_date
            EvidenceConstructionError — artifact rules cannot be applied
            EvaluationError — artifact evaluation failed
        """
```

---

## 4. Component Interfaces

Each pipeline stage has a defined abstract interface. Implementations live in `core/msi/dra/`; interfaces live in `core/msi/interfaces/`. This separation enables unit testing with mock implementations and allows future Market State Engines to reuse the same interfaces without depending on DRA concrete classes.

```python
# core/msi/interfaces/observation_reader.py

class ObservationReader(ABC):
    """MSI-003 §4: read-contract over Platform-persisted market data."""

    @abstractmethod
    def read(self, evaluation_date: date, symbols: tuple[str, ...]) -> tuple[Observation, ...]:
        """Read Observations for the given date and symbols. Deterministic."""
        ...


# core/msi/interfaces/evidence_builder.py

class EvidenceBuilder(ABC):
    """MSI-004 §2/§5: construct Evidence from Observations + artifact rules."""

    @abstractmethod
    def build(self, observations: tuple[Observation, ...], artifact: PublishedArtifact) -> tuple[Evidence, ...]:
        """Apply artifact-carried construction rules to Observations. Deterministic."""
        ...


# core/msi/interfaces/artifact_loader.py

class ArtifactLoader(ABC):
    """MSI-007 §7–8, MSI-008 §9: load, validate, and verify a Published MSI Artifact."""

    @abstractmethod
    def load(self, artifact_ref: str) -> PublishedArtifact:
        """
        Load and validate an artifact. Checks:
        - Compatibility (MSI-007 §8)
        - Active status (MSI-008 §9)
        - Validation (MSI-006)
        - Integrity (checksum)
        Returns opaque PublishedArtifact handle.
        """
        ...


# core/msi/interfaces/artifact_evaluator.py

class ArtifactEvaluator(ABC):
    """MSI-005 §7/§13: runtime artifact evaluation engine."""

    @abstractmethod
    def evaluate(self, evidence: tuple[Evidence, ...], artifact: PublishedArtifact) -> MarketState:
        """Evaluate artifact against Evidence. Deterministic. Validates output contract."""
        ...


# core/msi/interfaces/knowledge_builder.py

class KnowledgeBuilder(ABC):
    """MSI-005 §11: construct KnowledgeObject from MarketState + provenance."""

    @abstractmethod
    def build(self, market_state: MarketState, artifact: PublishedArtifact,
              provenance_chain: ProvenanceChain) -> KnowledgeObject:
        """Construct a KnowledgeObject conforming to MSI-005 §11. Deterministic ID."""
        ...


# core/msi/interfaces/knowledge_publisher.py

class KnowledgePublisher(ABC):
    """MSI-005 §6: persist Knowledge and expose read-only access to strategies."""

    @abstractmethod
    def publish(self, knowledge: KnowledgeObject) -> None:
        """Persist KnowledgeObject with transactional guarantee."""
        ...

    @abstractmethod
    def get_knowledge(self, date: date) -> Optional[KnowledgeObject]:
        """Read Knowledge for a given date. Returns None if not found."""
        ...

    @abstractmethod
    def get_latest(self) -> Optional[KnowledgeObject]:
        """Read most recent Knowledge."""
        ...
```

---

## 5. Internal Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  orchestrator.run(evaluation_date="2026-07-03", artifact_ref=...) │
└──────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  ObservationReader    ArtifactLoader        (error path)
         │                    │
         │  List[Observation] │  PublishedArtifact
         │         │          │         │
         └────┬────┘          │         │
              │               │         │
              ▼               ▼         │
        EvidenceBuilder ◄──────┘         │
              │    (uses artifact.get_evidence_rules())
              │
              │  List[Evidence]
              │
              ▼
        ArtifactEvaluator ◄── PublishedArtifact
              │    (uses artifact.evaluate(evidence))
              │
              │  MarketState
              │
              ▼
        KnowledgeBuilder ◄── ArtifactMetadata + ProvenanceChain
              │
              │  KnowledgeObject
              │
              ▼
        KnowledgePublisher
              │
              │  (writes to platform store)
              │
              ▼
         return KnowledgeObject
```

Determinism contract (MSI-005 §13): identical `evaluation_date` + `artifact_ref` + platform data state → identical `KnowledgeObject` (bit-exact, including `knowledge_id`).

---

## 6. Knowledge Object Flow

**Storage:** `data/msi/knowledge.duckdb` (single store, indexed by `evaluation_date`)

**Decision note (v1.1):** a single knowledge store replaces the per-date file layout (`{YYYY-MM-DD}.duckdb`) proposed in v1.0. At daily cadence a per-date file per KnowledgeObject makes `get_latest()`/`get_range()` multi-file scans for no benefit; a single file keeps reads trivial and lives under the same `data/msi/` root as artifacts (§7).

```
Table: knowledge_objects
  knowledge_id       TEXT PRIMARY KEY
  evaluation_date    DATE NOT NULL
  evaluation_ts      TIMESTAMP NOT NULL
  artifact_id        TEXT NOT NULL
  artifact_version   TEXT NOT NULL
  runtime_version    TEXT NOT NULL
  provenance_ref     TEXT NOT NULL

Table: estimates
  knowledge_id       TEXT REFERENCES knowledge_objects
  latent_variable    TEXT NOT NULL
  value              REAL NOT NULL
  uncertainty        REAL NOT NULL
  dimension          TEXT NOT NULL
```

Provenance chain: `Observation IDs → Evidence IDs → Artifact ID/Version → Knowledge ID`. Every KnowledgeObject can be traced back to its source Observations.

---

## 7. Artifact Loading Process

```
ArtifactLoader.load(artifact_ref)
│
├─ 1. Resolve artifact_ref → artifact path
│     (configurable root: data/msi/artifacts/)
│
├─ 2. Read metadata.json → ArtifactMetadata
│
├─ 3. Validate compatibility (MSI-007 §8)
│     - runtime_version in supported_runtime_versions
│     - ontology_version in supported_ontology_versions
│     - inference_contract_version in supported_contract_versions
│     → reject on mismatch (ArtifactIncompatibleError)
│
├─ 4. Verify Active status (MSI-008 §9)
│     - Check lifecycle state record
│     - State must be "Active"
│     → reject if not Active (ArtifactNotActiveError)
│
├─ 5. Validate identity (MSI-007 §6)
│     - Artifact ID matches path
│     - Version consistent
│
├─ 6. Validate validation (MSI-006)
│     - ValidationIdentifier resolves to Approved verdict
│     → reject if validation not Approved (ArtifactNotValidatedError)
│
├─ 7. Integrity check
│     - Checksum/hash of artifact contents matches recorded hash
│     → reject on mismatch (ArtifactIntegrityError)
│
└─ 8. Return PublishedArtifact handle (opaque)
```

**Reference test artifact directory layout (M1 only; production format deferred to Research):**
```
data/msi/artifacts/
  {artifact_id}/
    {version}/
      metadata.json        # MSI-007 §7 metadata
      evidence_rules.json  # MSI-004 evidence construction rules
      model/               # MSI-005 inference model (opaque, implementation-defined)
      provenance.json      # MSI-007 §9 provenance
      checksum.sha256      # integrity hash
```

---

## 8. Observation Ingestion

**Data source:** Platform DuckDB stores — `data/market_data/nse/candles/1d/{date}.duckdb`

**Symbols (daily intermarket — DRA v1):**
- `NSE_INDEX|Nifty 50`
- `NSE_INDEX|Nifty Bank`
- `NSE_INDEX|India VIX`

**Ingestion logic:**
```
ObservationReader.read(date, symbols)
│
├─ For each symbol:
│   ├─ Query DuckDB: SELECT * FROM candles WHERE symbol = ? AND timestamp <= date ORDER BY timestamp
│   ├─ Ensure minimum lookback (configurable, default: 90 trading days)
│   ├─ Produce Observation for each row:
│   │   observation_id = f"obs_{symbol}_{timestamp.isoformat()}"
│   │   observable_type = "close_price" | "volume" | "open" | "high" | "low"
│   │   quality_metadata = derived from data completeness check
│   └─ Append to observations list
│
├─ Validate: all required symbols present, no gaps in date range
├─ Return tuple[Observation, ...] (immutable, point-in-time ordered)
│
└─ Raise ObservationReadError if:
    - Required symbol not found in DuckDB
    - Insufficient lookback (less than minimum bars)
    - Data gap exceeds configured tolerance
```

**Key constraint:** The ObservationReader does NOT fetch live data. It reads ONLY from the Platform's persisted immutable stores. Determinism derives from immutable stored facts per MSI-003 §6.

---

## 9. Evidence Construction

**MSI trace:** MSI-004 §2 (offline design, runtime evaluation), MSI-004 §8

```
EvidenceBuilder.build(observations, artifact)
│
├─ 1. Extract construction rules from artifact.get_evidence_rules()
│     Rules format (defined by artifact, implementation-defined):
│     {
│       "features": [
│         {"name": "vix_level", "source": "NSE_INDEX|India VIX", "field": "close",
│          "transform": "identity"},
│         {"name": "nifty_return_5d", "source": "NSE_INDEX|Nifty 50", "field": "close",
│          "transform": "pct_change", "window": 5},
│         ...
│       ],
│       "lookback_days": 90,
│       "required_symbols": ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "NSE_INDEX|India VIX"]
│     }
│
├─ 2. Apply rules deterministically to Observations
│     - Group observations by symbol, sort by timestamp
│     - For each feature: compute value from specified source/field/transform
│     - Validate: no future information leakage (point-in-time check)
│
├─ 3. Produce Evidence objects
│     For each computed feature:
│       evidence_id = deterministic UUID (hash of inputs)
│       evidence_type = feature name
│       evidence_value = computed value
│       source_observation_ids = tuple of observation IDs used
│       artifact_version = artifact.metadata.artifact_version
│
├─ 4. Validate determinism
│     - Evidence IDs MUST be deterministic (hash-based, not random)
│     - Given identical observations + identical rules → identical evidence_ids
│
└─ Return tuple[Evidence, ...]
```

**Determinism guarantee (MSI-004 §8):** Identical Observations + identical artifact rules → identical Evidence (including evidence_ids).

---

## 10. Artifact Evaluation

**MSI trace:** MSI-005 §7 (runtime input contract), MSI-005 §13 (determinism)

```
ArtifactEvaluator.evaluate(evidence, artifact) -> MarketState
│
├─ 1. Validate input contract (MSI-005 §7)
│     - Evidence objects conform to MSI-004
│     - Artifact is Active + validated
│
├─ 2. Call artifact.evaluate(evidence)
│     - The artifact is opaque; evaluator does not inspect internals
│     - Artifact returns MarketState (collection of Estimates)
│
├─ 3. Validate output contract (MSI-005 §8)
│     - Every Estimate carries value + uncertainty (MSI-OD-005)
│     - MarketState is multidimensional (MSI-OD-001)
│     - No standalone scalar Confidence/Uncertainty on MarketState
│
├─ 4. Return MarketState
│
└─ Determinism: identical evidence + identical artifact → identical MarketState
```

**Artifact contract validation (post-evaluation):**
- Check that all Estimates reference latent variables defined in the artifact's ontology
- Check that uncertainty values are within expected range (≥ 0)
- Log any contract violations but do NOT modify output

---

## 11. Knowledge Publication

**MSI trace:** MSI-005 §11 (Knowledge Object schema), MSI-005 §6 (expose through Platform interfaces)

```
KnowledgePublisher.publish(knowledge_object)
│
├─ 1. Persist to DuckDB
│     - INSERT into knowledge_objects table
│     - INSERT estimates into estimates table
│     - All writes in a single transaction
│
├─ 2. Provenance preservation
│     - KnowledgeObject stores reference to full provenance chain
│     - Provenance chain recorded alongside Knowledge in separate table
│     - Replay: for a given date + artifact, the same KnowledgeObject is recoverable
│
├─ 3. Expose to Strategy read-path
│     - Strategies access via KnowledgeReader (read-only facade)
│     - KnowledgeReader.get_knowledge(date) -> Optional[KnowledgeObject]
│     - KnowledgeReader.get_latest() -> Optional[KnowledgeObject]
│
└─ No signal generation. No strategy logic. Read-only.
```

**KnowledgeReader (strategy-facing facade):**
```python
class KnowledgeReader:
    """Read-only MSI knowledge access for strategies. MSI-005 §6."""
    def get_knowledge(self, date: date) -> Optional[KnowledgeObject]: ...
    def get_latest(self) -> Optional[KnowledgeObject]: ...
    def get_range(self, start: date, end: date) -> List[KnowledgeObject]: ...
```

**Read-path ownership (v1.1 clarification):** the read implementation lives on `KnowledgePublisher` (its `get_knowledge`/`get_latest` methods, frozen in the M0 ABC). `KnowledgeReader` is a thin strategy-facing facade that delegates to the publisher's reads and adds `get_range` — it holds no query logic of its own. There is exactly one implementation of each read.

---

## 12. Dependency Graph

```
External (Research Repo)           Platform (this repo)
─────────────────────────          ────────────────────────
                                   
Published MSI Artifact ──────────► ArtifactLoader
  (serialized model +               │
   evidence rules +                 ▼
   metadata)                  ArtifactEvaluator
                                    │
                                    ▼
                              KnowledgeBuilder
                                    │
Platform DuckDB stores ──────────► ObservationReader
  (1d candles)                      │
                                    ▼
                              EvidenceBuilder
                                    │
                                    └───────┐
                                            ▼
                                     DRAOrchestrator
                                            │
                                            ▼
                                     KnowledgePublisher
                                            │
                                            ▼
                                     KnowledgeReader (strategy API)
                                            │
                                            ▼
                                     Strategy (external to MSI)
                                            │
                                            ▼
                                     SignalSource → Platform
```

**Platform dependencies (internal):**
- `core/events.py` — DTO conventions (frozen dataclasses)
- DuckDB market data stores — Observation source
- `core/instruments/` — canonical instrument resolution (optional; Observations already carry canonical IDs)
- No dependency on `core/strategies/`, `core/execution/`, or `core/brokers/`

**External dependencies (Python packages):**
- `duckdb` — already in requirements.txt
- Standard library only otherwise (no new dependencies for core MSI runtime)

---

## 13. Testing Strategy

### 13.1 Contract Tests (test_contracts.py)

Verify all DTOs are frozen, immutable, and match MSI spec schemas.

| Test | MSI Ref |
|------|---------|
| Observation fields match MSI-003 §5 | MSI-003 |
| Evidence fields match MSI-004 §7 | MSI-004 |
| Estimate carries value + uncertainty | MSI-002 §4.7 |
| MarketState is tuple of Estimates (multidimensional) | MSI-002 §4.8, MSI-OD-001 |
| KnowledgeObject has all 6 fields from MSI-005 §11 | MSI-005 |
| KnowledgeObject has NO Confidence/Uncertainty scalar | MSI-005 §11 |
| All DTOs raise FrozenInstanceError on mutation | Platform convention |
| ArtifactMetadata matches MSI-007 §7 | MSI-007 |

### 13.2 Unit Tests (per component)

Each component tested in isolation with injected dependencies.

| Component | Key Tests |
|-----------|-----------|
| ObservationReader | Reads from test DuckDB; handles missing symbol; handles insufficient lookback; produces deterministic IDs |
| EvidenceBuilder | Applies test rules; deterministic evidence_ids; rejects rules with look-ahead; handles empty observations |
| ArtifactLoader | Loads valid artifact; rejects incompatible version; rejects non-Active artifact; rejects invalid checksum; validates metadata |
| ArtifactEvaluator | Calls artifact.evaluate(); validates output contract; raises on contract violation; deterministic output |
| KnowledgeBuilder | Produces correct schema; deterministic knowledge_id; provenance chain correct; no scalar confidence |
| KnowledgePublisher | Writes to DuckDB; round-trip KnowledgeObject; get_latest() returns most recent; handles no data |
| Provenance | Complete chain from Observation → Knowledge; reconstructable; immutable records |

### 13.3 Integration Tests (test_orchestrator.py)

Full pipeline end-to-end with a test artifact.

| Test | Description |
|------|-------------|
| `test_full_pipeline_deterministic` | Same date + artifact → bit-identical KnowledgeObject (run twice, compare) |
| `test_full_pipeline_provenance` | Knowledge.provenance_reference resolves to complete chain |
| `test_full_pipeline_missing_data` | Raises ObservationReadError when symbol missing from DuckDB |
| `test_full_pipeline_incompatible_artifact` | Raises ArtifactLoadError when artifact incompatible |
| `test_full_pipeline_inactive_artifact` | Raises ArtifactLoadError when artifact not Active |
| `test_full_pipeline_replay` | Run for historical date, verify identical to recorded output |

### 13.4 Replay Tests (test_replay.py)

| Test | Description |
|------|-------------|
| `test_replay_identical_output` | Run for date T; re-run for date T; output bit-identical |
| `test_replay_across_processes` | Persist output; restart process; re-run; output matches |
| `test_replay_with_different_artifact` | Different artifact → different output (but still deterministic per artifact) |
| `test_replay_point_in_time` | Evaluation at T uses only data available at T (no look-ahead) |

---

## 14. Replay Testing

**Implementation:**

```python
class ReplayVerifier:
    """
    Verifies DRA deterministic replay (MSI-DRA-002, MSI-005 §13).

    Protocol:
        1. Run DRA for date T → record KnowledgeObject (checksum)
        2. Re-run DRA for date T → compare checksum
        3. Assert: checksums identical

    Cross-mode: run in LIVE mode, replay in REPLAY mode, output must match.
    """

    def verify(self, date: date, artifact_ref: str) -> bool: ...

    def verify_range(self, start: date, end: date, artifact_ref: str) -> dict: ...
```

**Replay contract:** The DRA produces identical output regardless of whether the system clock is real-time or replay. The mode is transparent to the DRA — it reads only from persisted stores, which are immutable.

---

## 15. Provenance Validation

```python
class ProvenanceChain:
    """
    Immutable provenance chain: Observation → Evidence → Artifact → Knowledge.

    MSI-005 §14, MSI-004 §9, MSI-003 §7.
    """
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    artifact_id: str
    artifact_version: str
    validation_id: str
    knowledge_id: str

    def reconstruct(self) -> dict:
        """Return complete provenance record suitable for audit."""
        ...

    def verify(self, knowledge_store, evidence_store, observation_store) -> bool:
        """Verify every link in the chain resolves to its stored record."""
        ...
```

**Validation at each pipeline stage:**
- ObservationReader attaches Platform provenance references
- EvidenceBuilder links each Evidence to source Observation IDs
- ArtifactEvaluator records artifact_id + artifact_version
- KnowledgeBuilder assembles complete provenance chain

---

## 16. Failure Handling

All errors are typed. No bare exceptions. No silent failure.

```python
# core/msi/dra/errors.py

class DRAError(Exception): ...
class ObservationReadError(DRAError): ...     # data unavailable, insufficient lookback
class ArtifactLoadError(DRAError): ...        # base
class ArtifactNotFoundError(ArtifactLoadError): ...
class ArtifactIncompatibleError(ArtifactLoadError): ...
class ArtifactNotActiveError(ArtifactLoadError): ...
class ArtifactNotValidatedError(ArtifactLoadError): ...
class ArtifactIntegrityError(ArtifactLoadError): ...
class EvidenceConstructionError(DRAError): ... # rules cannot be applied
class EvaluationError(DRAError): ...           # artifact.evaluate() raised
class KnowledgeBuildError(DRAError): ...       # KnowledgeObject construction/schema failure
class KnowledgePublishError(DRAError): ...     # DuckDB write failed
```

**Error handling policy:**
1. All errors propagate to orchestrator
2. Orchestrator never catches and swallows — it logs and re-raises
3. No partial state: if any stage fails, no Knowledge is published
4. The caller (script/runner) decides retry/abort policy
5. All errors logged with full context (date, artifact_ref, component, stack)

---

## 17. Performance Considerations

**Daily cadence (MSI-009 §3):** The DRA runs once per trading day, after market close. Throughput is not a concern — correctness and determinism are the priorities.

**Constraints:**
- Observation read: < 1 second (querying 3 symbols × 90 days from DuckDB)
- Evidence construction: < 1 second (computing features from rules)
- Artifact evaluation: implementation-defined (depends on artifact model)
- Total pipeline: < 10 seconds target

**No optimization needed** at this scale. The architecture must remain simple. Premature optimization violates the Platform principle of "no over-engineering."

---

## 18. Incremental Implementation Milestones

### Milestone M0 — Contracts & Runtime Interfaces

*(v1.1: retitled from "Contracts + DTOs" and interface deliverables added, matching what M0 actually delivered. The interfaces were always part of the §2 package layout; v1.0 omitted them from this deliverable list. Deviation recorded as ledger event #5.)*

**Objective:** Establish all frozen MSI contracts and the abstract component interfaces. Zero logic.

**Deliverables:**
- `core/msi/contracts/observation.py`
- `core/msi/contracts/evidence.py`
- `core/msi/contracts/estimate.py`
- `core/msi/contracts/market_state.py`
- `core/msi/contracts/knowledge.py`
- `core/msi/contracts/artifact.py`
- `core/msi/contracts/__init__.py`
- `core/msi/interfaces/observation_reader.py`
- `core/msi/interfaces/evidence_builder.py`
- `core/msi/interfaces/artifact_loader.py`
- `core/msi/interfaces/artifact_evaluator.py`
- `core/msi/interfaces/knowledge_builder.py`
- `core/msi/interfaces/knowledge_publisher.py`
- `core/msi/interfaces/__init__.py`
- `core/msi/__init__.py`

**Dependencies:** None (contracts defined by MSI-002/003/004/005/007 specs)

**Acceptance Criteria:**
- All DTOs are `@dataclass(frozen=True)`
- All DTOs match their MSI spec section exactly
- All DTOs raise `FrozenInstanceError` on mutation attempt
- `KnowledgeObject` has exactly 6 fields; no scalar Confidence/Uncertainty
- All interfaces are ABCs with abstract methods only; no implementation logic

**Tests:** `tests/msi/test_contracts.py` — fields match MSI specs, immutability verified, no extra fields; `tests/msi/test_interfaces.py` — ABC inheritance, abstract method enforcement

---

### Milestone M1 — Reference Test Artifact

**Objective:** Build a minimal conformant Published MSI Artifact for pipeline testing. This format is a reference test format only — the production artifact format is deferred to the Research domain and must conform to MSI-007.

**Deliverables:**
- `tests/msi/fixtures/test_artifact/` directory
  - `metadata.json` — MSI-007 §7 metadata
  - `evidence_rules.json` — simple rules (VIX close, Nifty close, Nifty return)
  - `model/` — trivial model (e.g., threshold classifier)
  - `provenance.json`
  - `checksum.sha256`
- `tests/msi/conftest.py` — fixtures: test_artifact_path, sample_observations, sample_evidence

**Dependencies:** M0 (contracts)

**Acceptance Criteria:**
- Artifact directory structure conforms to §7 reference layout (loadability via ArtifactLoader is verified as part of M2 acceptance, which loads this artifact — v1.1: removed forward dependency on M2 from M1 acceptance)
- Artifact evaluate() returns valid MarketState
- Artifact is deterministic (same input → same output)
- Test artifact has known expected output for known test input

**Tests:** `conftest.py` validates test artifact structure; test artifact used by all downstream milestones

---

### Milestone M2 — ArtifactLoader + ArtifactLoader Tests

**Objective:** Implement artifact loading with full MSI-007/008 validation.

**Deliverables:**
- `core/msi/dra/filesystem_artifact_loader.py`
- `core/msi/dra/errors.py` (load-related errors)
- `tests/msi/test_artifact_loader.py`

**Dependencies:** M0 (contracts), M1 (test artifact)

**Acceptance Criteria:**
- Loads valid artifact → returns PublishedArtifact handle
- Rejects incompatible runtime version
- Rejects incompatible ontology version
- Rejects incompatible inference contract version
- Rejects non-Active lifecycle state
- Rejects non-Approved validation
- Rejects checksum mismatch
- All rejections raise typed errors (never bare Exception)

**Tests:**
- `test_load_valid_artifact` — success path
- `test_reject_incompatible_runtime_version`
- `test_reject_incompatible_ontology`
- `test_reject_incompatible_contract`
- `test_reject_not_active`
- `test_reject_not_validated`
- `test_reject_checksum_mismatch`
- `test_reject_missing_metadata`
- `test_reject_missing_evidence_rules`

---

### Milestone M3 — ObservationReader + ObservationReader Tests

**Objective:** Implement MSI-003 read-contract over Platform DuckDB stores.

**Deliverables:**
- `core/msi/dra/duckdb_observation_reader.py`
- `tests/msi/test_observation_reader.py`
- `tests/msi/fixtures/test_data.duckdb` — small test DuckDB with known data

**Dependencies:** M0 (contracts)

**Acceptance Criteria:**
- Reads from DuckDB and produces Observation DTOs
- Handles missing symbol (ObservationReadError)
- Handles insufficient lookback (ObservationReadError)
- Produces deterministic Observation IDs (hash-based, not random)
- Produces identical output on repeated reads of same DuckDB state
- Handles empty result set (no data for symbol on date)

**Tests:**
- `test_read_observations_for_date` — returns correct count and values
- `test_observation_ids_are_deterministic` — same input → same IDs
- `test_missing_symbol_raises`
- `test_insufficient_lookback_raises`
- `test_empty_result_for_future_date`

---

### Milestone M4 — EvidenceBuilder + EvidenceBuilder Tests

**Objective:** Implement MSI-004 runtime evidence construction from artifact rules.

**Deliverables:**
- `core/msi/dra/default_evidence_builder.py`
- `tests/msi/test_evidence_builder.py`

**Dependencies:** M0 (contracts), M1 (test artifact with rules), M3 (Observations)

**Acceptance Criteria:**
- Applies artifact evidence rules to Observations
- Produces Evidence objects with correct schema (MSI-004 §7)
- Evidence IDs are deterministic (hash-based)
- Identical Observations + rules → identical Evidence (including IDs)
- Rejects rules that reference symbols not in Observations
- Evidence links back to source Observation IDs
- No look-ahead: feature computation uses only data ≤ evaluation timestamp

**Tests:**
- `test_build_evidence_from_test_rules` — correct count and values
- `test_evidence_determinism` — identical inputs → identical outputs
- `test_evidence_ids_deterministic` — IDs derived from content
- `test_reject_missing_symbol_in_rules`
- `test_source_observation_ids_correct`
- `test_no_look_ahead` — feature at T uses only data ≤ T
- `test_empty_observations_returns_empty_evidence`

---

### Milestone M5 — ArtifactEvaluator + KnowledgeBuilder

**Objective:** Implement MSI-005 evaluation engine and Knowledge construction.

**Deliverables:**
- `core/msi/dra/default_artifact_evaluator.py`
- `core/msi/dra/default_knowledge_builder.py`
- `core/msi/dra/provenance.py`
- `tests/msi/test_artifact_evaluator.py`
- `tests/msi/test_knowledge_builder.py`
- `tests/msi/test_provenance.py`

**Dependencies:** M0 (contracts), M1 (test artifact), M4 (Evidence)

**Acceptance Criteria:**
- Calls artifact.evaluate(evidence) and returns MarketState
- Validates output contract (every Estimate has value + uncertainty)
- KnowledgeBuilder produces correct KnowledgeObject schema (MSI-005 §11)
- Knowledge ID is deterministic (hash of inputs + content)
- No scalar Confidence/Uncertainty on KnowledgeObject
- Provenance chain complete: Observation → Evidence → Artifact → Knowledge
- KnowledgeObject is immutable

**Tests:**
- `test_evaluate_returns_market_state` — correct type and structure
- `test_evaluate_contract_validation` — rejects Estimates without uncertainty
- `test_knowledge_object_schema` — all 6 fields present, correct types
- `test_knowledge_id_deterministic` — same inputs → same knowledge_id
- `test_no_scalar_confidence` — KnowledgeObject has no confidence field
- `test_provenance_chain_complete` — all links present
- `test_provenance_reconstructable` — chain can be walked end-to-end
- `test_evaluate_determinism` — same evidence + artifact → same MarketState

---

### Milestone M6 — KnowledgePublisher + KnowledgeReader

**Objective:** Persist Knowledge and expose read-only strategy API.

**Deliverables:**
- `core/msi/dra/duckdb_knowledge_publisher.py`
- `core/msi/dra/knowledge_reader.py`
- `tests/msi/test_knowledge_publisher.py`
- `tests/msi/test_knowledge_reader.py`

**Dependencies:** M5 (KnowledgeBuilder), M0 (contracts)

**Acceptance Criteria:**
- Publishes KnowledgeObject to DuckDB (knowledge_objects + estimates tables)
- KnowledgeReader.get_knowledge(date) returns correct KnowledgeObject
- KnowledgeReader.get_latest() returns most recent
- KnowledgeReader.get_range() returns ordered list
- Round-trip: KnowledgeObject → publish → read → identical KnowledgeObject
- Transactional: partial publish does not leave corrupt state
- Read-only: KnowledgeReader has no write methods

**Tests:**
- `test_publish_and_read` — round-trip identical
- `test_get_latest` — returns most recent by evaluation_date
- `test_get_range` — correct range, ordered
- `test_publish_transactional` — DuckDB transaction rollback on error
- `test_read_nonexistent_date` — returns None
- `test_read_on_empty_store` — returns None

---

### Milestone M7 — DRAOrchestrator + Integration

**Objective:** Wire full pipeline; end-to-end integration.

**Deliverables:**
- `core/msi/dra/orchestrator.py`
- `tests/msi/test_orchestrator.py`

**Dependencies:** M2–M6 (all components)

**Acceptance Criteria:**
- `orchestrator.run(date, artifact_ref)` executes full pipeline: Observation → Evidence → Evaluate → Knowledge → Publish
- Returns KnowledgeObject
- Deterministic: same inputs → bit-identical output
- Errors propagate correctly (typed, not swallowed)
- No partial state on failure
- Pipeline order matches MSI-009 §5 diagram

**Tests:**
- `test_full_pipeline_success` — end-to-end with test artifact
- `test_full_pipeline_deterministic` — run twice, compare knowledge_id
- `test_full_pipeline_provenance` — provenance chain resolves
- `test_pipeline_fails_on_missing_data` — ObservationReadError propagated
- `test_pipeline_fails_on_incompatible_artifact` — ArtifactIncompatibleError propagated
- `test_pipeline_no_partial_state_on_failure` — nothing published if evaluation fails
- `test_pipeline_order_matches_msi_009_diagram` — sequence validation

---

### Milestone M8 — Replay Verification

**Objective:** Prove deterministic replay across modes and processes.

**Deliverables:**
- `tests/msi/test_replay.py`

**Dependencies:** M7 (full pipeline)

**Acceptance Criteria:**
- Same date + artifact → identical KnowledgeObject across 3 consecutive runs
- Persisted KnowledgeObject matches re-computed KnowledgeObject
- Replay with different artifact → different (but valid) output
- Point-in-time: data at T+1 not available for evaluation at T

**Tests:**
- `test_replay_identical_output` — 3 runs, all identical
- `test_replay_roundtrip` — publish, re-read, re-run, compare
- `test_replay_different_artifact_different_output`
- `test_point_in_time_no_future_data` — data for T+1 raises if accessed for T
- `test_replay_with_subset_data` — limited lookback produces same output (if within min requirements)

---

### Milestone M9 — Documentation + Package Finalization

**Objective:** Complete package documentation, type hints, and developer guide.

**Deliverables:**
- `core/msi/__init__.py` — public API exports
- `core/msi/dra/__init__.py` — DRA public API
- Full type hints on all public methods
- Module-level docstrings with MSI spec traceability
- `docs/implementation/dra/DRA_DEVELOPER_GUIDE.md` (v1.1: moved from `docs/architecture/` — implementation docs live with the DRA program, architecture docs stay frozen)

**Dependencies:** M0–M8 (all implementation)

**Acceptance Criteria:**
- Every public class/method has type hints
- Every module docstring references governing MSI spec section
- Developer guide covers: setup, artifact creation, running the DRA, testing, replay
- No `# type: ignore` comments
- All imports explicit (no `import *`)

**Tests:** None (documentation milestone)

---

## Milestone Summary

| Milestone | Description | Components | Est. Effort |
|-----------|-------------|------------|-------------|
| M0 | Contracts & Runtime Interfaces | 7 frozen dataclasses + Artifact protocol + 6 interface ABCs | Small |
| M1 | Test Artifact | Minimal conformant artifact for testing | Small |
| M2 | ArtifactLoader | Load, validate, compatibility check | Medium |
| M3 | ObservationReader | DuckDB read contract | Medium |
| M4 | EvidenceBuilder | Artifact-rule evidence construction | Medium |
| M5 | Evaluator + Knowledge | MSI-005 engine + KnowledgeBuilder + provenance | Large |
| M6 | Publisher + Reader | DuckDB persistence + strategy read API | Medium |
| M7 | Orchestrator | Full pipeline integration | Medium |
| M8 | Replay Verification | Determinism proof across modes | Small |
| M9 | Documentation | type hints, docstrings, developer guide | Small |

**Dependency order:** M0 → M1 → (M2, M3 in parallel) → M4 → M5 → M6 → M7 → M8 → M9

---

## Implementation Rules

1. **Every class and method references its governing MSI spec section** in docstring
2. **No mutable state** in any DRA component — orchestrator is stateless; all state in DuckDB
3. **No random IDs** — all identifiers are deterministic (hash of content)
4. **No bare exceptions** — all errors are typed DRAError subclasses
5. **No inline imports** — all imports at module top
6. **No hardcoded paths** — configurable via constructor injection
7. **No `print()`** — use `logging` with appropriate levels
8. **Follow existing Platform patterns** — frozen dataclasses, dependency injection, typed errors

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Artifact format not yet defined by Research | M1 defines a test artifact format; real artifacts produced by Research later |
| No strategy consumer exists | DRA tested via KnowledgeReader; strategy integration deferred to MM13 |
| DuckDB schema evolution | Use versioned schema; M0 contracts are the stable interface |
| Determinism across DuckDB versions | Pin DuckDB version; replay tests catch divergence |
| Artifact model complexity unknown | Test artifact is trivial; real artifacts may be larger; load/evaluate is opaque by design |

---

## Amendment Log

### v1.1 — 2026-07-04 (editorial; no architectural change)

Source: `docs/reports/DRA_GOVERNANCE_DOCS_REVIEW.md` (findings P1–P6). Changes:

1. **File naming reconciled (P1):** milestone deliverables M2–M6 now use the §2 strategy-named implementation files (`filesystem_artifact_loader.py`, `duckdb_observation_reader.py`, `default_evidence_builder.py`, `default_artifact_evaluator.py`, `default_knowledge_builder.py`, `duckdb_knowledge_publisher.py`); v1.0 milestones used a conflicting plain-named scheme.
2. **Test location reconciled (P2):** all test paths now `tests/msi/` (platform convention, matches M0 as built); v1.0 had `core/msi/tests/` in §2 and root `tests/` in milestones.
3. **M0 scope aligned (P3):** M0 retitled "Contracts & Runtime Interfaces"; the six interface ABCs added to M0 deliverables to match what was built and reviewed. Ledger event #5.
4. **Error hierarchy completed (P4):** `KnowledgeBuildError` added to §16 (was referenced by the M0 `KnowledgeBuilder` interface docstring but missing from the hierarchy).
5. **M1 forward dependency removed (P5):** M1 acceptance no longer requires the M2 ArtifactLoader; loadability of the test artifact is verified in M2.
6. **Storage unified (P6):** knowledge store moved to `data/msi/knowledge.duckdb` (single file, one `data/msi/` root shared with artifacts); read-path ownership between `KnowledgePublisher` and `KnowledgeReader` clarified in §11; §13 subsection numbering corrected; `knowledge_reader.py` added to §2 layout; M9 developer guide relocated to `docs/implementation/dra/`.

---

**End of Plan**
