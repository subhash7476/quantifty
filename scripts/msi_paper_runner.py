from datetime import date
from typing import Optional

from core.clock import Clock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.execution.handler import ExecutionMode
from core.msi.dra.default_artifact_evaluator import DefaultArtifactEvaluator
from core.msi.dra.default_evidence_builder import DefaultEvidenceBuilder
from core.msi.dra.default_knowledge_builder import DefaultKnowledgeBuilder
from core.msi.dra.default_knowledge_publisher import DefaultKnowledgePublisher
from core.msi.dra.duckdb_observation_reader import DuckDBObservationReader
from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
from core.msi.dra.knowledge_repository import KnowledgeRepository
from core.msi.dra.orchestrator import DRAOrchestrator
from core.runtime.driver import LoopDriver
from core.runtime.metrics import TelemetrySink
from core.strategies.knowledge_signal_source import KnowledgeSignalSource

import scripts.fno_runner as fno_runner


def build_dra_orchestrator(obs_db_path: str) -> DRAOrchestrator:
    return DRAOrchestrator(
        observation_reader=DuckDBObservationReader(obs_db_path),
        evidence_builder=DefaultEvidenceBuilder(),
        artifact_loader=FilesystemArtifactLoader(),
        artifact_evaluator=DefaultArtifactEvaluator(),
        knowledge_builder=DefaultKnowledgeBuilder(),
        knowledge_publisher=DefaultKnowledgePublisher(KnowledgeRepository()),
    )


def build_msi_paper_runner(
    *,
    traded_symbol: str,
    evaluation_date: date,
    artifact_ref: str,
    obs_db_path: str,
    provider: MarketDataProvider,
    clock: Clock,
    telemetry: Optional[TelemetrySink] = None,
    db_manager: Optional[DatabaseManager] = None,
    max_bars: Optional[int] = None,
    latent_variable: str = "market_regime",
) -> LoopDriver:
    orchestrator = build_dra_orchestrator(obs_db_path)
    source = KnowledgeSignalSource(
        orchestrator=orchestrator,
        evaluation_date=evaluation_date,
        artifact_ref=artifact_ref,
        traded_symbol=traded_symbol,
        latent_variable=latent_variable,
    )
    return fno_runner.build_runner(
        source=source,
        symbols=[traded_symbol],
        execution_mode=ExecutionMode.PAPER,
        provider=provider,
        clock=clock,
        db_manager=db_manager,
        telemetry=telemetry,
        max_bars=max_bars,
    )
