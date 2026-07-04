from __future__ import annotations

import csv
import json
import statistics
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


DEFAULT_FORWARD_WINDOWS = (5, 10, 20, 60)
DEFAULT_WEIGHT_COMBINATIONS = (
    {"support": 0.35, "bounce": 0.25, "technical": 0.20, "institutional": 0.20},
    {"support": 0.25, "bounce": 0.35, "technical": 0.20, "institutional": 0.20},
    {"support": 0.25, "bounce": 0.20, "technical": 0.35, "institutional": 0.20},
    {"support": 0.25, "bounce": 0.20, "technical": 0.20, "institutional": 0.35},
    {"support": 0.25, "bounce": 0.25, "technical": 0.25, "institutional": 0.25},
)


@dataclass
class HistoricalSignal:
    ticker: str
    signal_date: str
    entry_price: float | None
    support_score: float
    bounce_score: float
    technical_score: float
    institutional_score: float
    final_score: float
    grade: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class SignalOutcome:
    ticker: str
    signal_date: str
    entry_price: float | None
    forward_returns: dict[str, float | None]
    max_gain_pct: float | None
    max_drawdown_pct: float | None
    hit_profit_target: bool
    hit_stop_loss: bool
    support_score: float
    bounce_score: float
    technical_score: float
    institutional_score: float
    final_score: float
    grade: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class FactorBucketResult:
    factor: str
    bucket: str
    signal_count: int
    win_rate: float
    average_return: float
    median_return: float
    max_drawdown: float
    expectancy: float


@dataclass
class WeightOptimizationResult:
    weights: dict[str, float]
    score: float
    rank: int = 0
    expectancy: float = 0.0
    win_rate: float = 0.0
    average_return: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    warnings: list[str] = field(default_factory=list)


@dataclass
class WalkForwardWindowResult:
    training_start: str
    training_end: str
    testing_start: str
    testing_end: str
    selected_weights: dict[str, float]
    training_score: float
    testing_expectancy: float
    testing_win_rate: float
    signal_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class BenchmarkComparisonResult:
    benchmark_ticker: str
    average_signal_return: float
    average_benchmark_return: float
    alpha: float
    hit_rate_vs_benchmark: float
    comparisons: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class AlgorithmValidationReport:
    run_id: str
    started_at: str
    completed_at: str | None
    start_date: str | None
    end_date: str | None
    replay_frequency: str
    signal_count: int
    outcome_count: int
    summary_metrics: dict[str, float | int | None]
    factor_bucket_results: list[FactorBucketResult] = field(default_factory=list)
    best_weight_configs: list[WeightOptimizationResult] = field(default_factory=list)
    walk_forward_results: list[WalkForwardWindowResult] = field(default_factory=list)
    benchmark_comparison: BenchmarkComparisonResult | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    signals: list[HistoricalSignal] = field(default_factory=list)
    outcomes: list[SignalOutcome] = field(default_factory=list)


@dataclass
class SignalQualityGroupResult:
    dimension: str
    group: str
    signal_count: int
    win_rate: float
    expectancy: float
    average_return: float
    max_drawdown: float
    weak: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class SignalQualityRecommendation:
    recommendation_type: str
    field: str
    current_value: float | str | None
    recommended_value: float | str
    reason: str
    severity: str = "MEDIUM"
    affected_groups: list[str] = field(default_factory=list)


@dataclass
class SignalQualityRecommendationReport:
    report_id: str
    validation_run_id: str | None
    created_at: str
    weak_groups: list[SignalQualityGroupResult] = field(default_factory=list)
    recommendations: list[SignalQualityRecommendation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class HistoricalSignalReplayService:
    def __init__(self, repository):
        self.repository = repository

    def replay(
        self,
        start_date,
        end_date,
        tickers=None,
        frequency="monthly",
        progress_callback=None,
        cancellation_callback=None,
    ):
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start is None or end is None or start > end:
            return [], ["Invalid validation date range."]

        ticker_list = normalize_tickers(tickers)
        if not ticker_list and hasattr(self.repository, "fetch_eligible_universe_tickers"):
            ticker_list = normalize_tickers(self.repository.fetch_eligible_universe_tickers())
        warnings = []
        if not ticker_list:
            return [], ["No tickers available for historical replay."]

        replay_dates = self.replay_dates(start, end, frequency)
        signals = []
        total = len(ticker_list) * max(1, len(replay_dates))
        processed = 0
        for ticker in ticker_list:
            rows = self.repository.fetch_ohlcv(ticker, start_date=None, end_date=end.isoformat())
            rows = sorted((row for row in rows if parse_date(value(row, "date"))), key=lambda row: value(row, "date"))
            if not rows:
                warnings.append(f"{ticker}: no cached OHLCV rows.")
                continue
            for replay_date in replay_dates:
                if cancellation_callback and cancellation_callback():
                    warnings.append("Validation cancelled.")
                    return signals, warnings
                processed += 1
                if progress_callback:
                    progress_callback(
                        {
                            "total": total,
                            "processed": processed,
                            "current_ticker": ticker,
                            "progress_percentage": int(processed * 100 / total),
                            "status_message": f"Replaying {ticker} on {replay_date.isoformat()}",
                        }
                    )
                history = [row for row in rows if parse_date(value(row, "date")) <= replay_date]
                future_guard = [row for row in history if parse_date(value(row, "date")) > replay_date]
                if future_guard:
                    warnings.append(f"{ticker}: look-ahead guard removed future rows.")
                    history = [row for row in history if parse_date(value(row, "date")) <= replay_date]
                signal = self.signal_from_history(ticker, replay_date, history)
                if signal is not None:
                    signals.append(signal)
        return signals, warnings

    @staticmethod
    def replay_dates(start: date, end: date, frequency: str):
        step = 7 if str(frequency).lower().startswith("week") else 30
        if str(frequency).lower().startswith("daily"):
            step = 1
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=step)
        return dates

    @staticmethod
    def signal_from_history(ticker, replay_date, history):
        if len(history) < 20:
            return None
        closes = [safe_float(value(row, "close")) for row in history if safe_float(value(row, "close")) is not None]
        lows = [safe_float(value(row, "low")) for row in history if safe_float(value(row, "low")) is not None]
        volumes = [safe_float(value(row, "volume")) for row in history if safe_float(value(row, "volume")) is not None]
        if not closes or not lows:
            return None
        entry = closes[-1]
        recent_low = min(lows[-20:])
        distance = ((entry - recent_low) / recent_low * 100) if recent_low else 100
        support_score = clamp(100 - distance * 8)
        bounce_score = clamp(50 + (len([low for low in lows[-90:] if recent_low and abs(low - recent_low) / recent_low <= 0.04]) * 10))
        sma20 = statistics.mean(closes[-20:])
        sma50 = statistics.mean(closes[-50:]) if len(closes) >= 50 else sma20
        technical_score = clamp(50 + (20 if entry >= sma20 else -15) + (15 if entry >= sma50 else -10))
        volume_score = 0
        if len(volumes) >= 20 and statistics.mean(volumes[-20:]) > 0:
            volume_score = min(15, max(-10, (volumes[-1] / statistics.mean(volumes[-20:]) - 1) * 20))
        institutional_score = clamp(50 + volume_score)
        final_score = clamp(
            support_score * 0.35
            + bounce_score * 0.25
            + technical_score * 0.20
            + institutional_score * 0.20
        )
        return HistoricalSignal(
            ticker=ticker,
            signal_date=replay_date.isoformat(),
            entry_price=entry,
            support_score=support_score,
            bounce_score=bounce_score,
            technical_score=technical_score,
            institutional_score=institutional_score,
            final_score=final_score,
            grade=grade_for_score(final_score),
        )


class OutcomeLabelingService:
    def __init__(self, repository, profit_target_pct=20.0, stop_loss_pct=8.0):
        self.repository = repository
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

    def label(self, signals, windows=DEFAULT_FORWARD_WINDOWS):
        outcomes = []
        for signal in signals or []:
            signal_date = parse_date(signal.signal_date)
            if signal_date is None:
                continue
            rows = self.repository.fetch_ohlcv(signal.ticker, start_date=signal.signal_date)
            future_rows = [
                row for row in rows
                if parse_date(value(row, "date")) and parse_date(value(row, "date")) > signal_date
            ]
            warnings = list(signal.warnings or [])
            if not future_rows:
                warnings.append("No forward OHLCV rows available.")
            entry = safe_float(signal.entry_price)
            forward_returns = {}
            highs = []
            lows = []
            for window in windows or DEFAULT_FORWARD_WINDOWS:
                window_rows = future_rows[: int(window)]
                close = safe_float(value(window_rows[-1], "close")) if window_rows else None
                forward_returns[str(window)] = pct_return(entry, close)
                highs.extend(safe_float(value(row, "high")) for row in window_rows)
                lows.extend(safe_float(value(row, "low")) for row in window_rows)
            highs = [number for number in highs if number is not None]
            lows = [number for number in lows if number is not None]
            max_gain = pct_return(entry, max(highs)) if highs else None
            max_drawdown = pct_return(entry, min(lows)) if lows else None
            outcomes.append(
                SignalOutcome(
                    ticker=signal.ticker,
                    signal_date=signal.signal_date,
                    entry_price=entry,
                    forward_returns=forward_returns,
                    max_gain_pct=max_gain,
                    max_drawdown_pct=max_drawdown,
                    hit_profit_target=bool(max_gain is not None and max_gain >= self.profit_target_pct),
                    hit_stop_loss=bool(max_drawdown is not None and max_drawdown <= -abs(self.stop_loss_pct)),
                    support_score=signal.support_score,
                    bounce_score=signal.bounce_score,
                    technical_score=signal.technical_score,
                    institutional_score=signal.institutional_score,
                    final_score=signal.final_score,
                    grade=signal.grade,
                    warnings=warnings,
                )
            )
        return outcomes


class FactorPerformanceAnalyzer:
    FACTORS = ("support_score", "bounce_score", "technical_score", "institutional_score", "final_score")

    def analyze(self, outcomes, return_window=20):
        results = []
        for factor in self.FACTORS:
            buckets = {}
            for outcome in outcomes or []:
                score = safe_float(value(outcome, factor))
                if score is None:
                    continue
                buckets.setdefault(bucket_for_score(score), []).append(outcome)
            for bucket_name in sorted(buckets):
                results.append(self.bucket_result(factor, bucket_name, buckets[bucket_name], return_window))
        return results

    @staticmethod
    def bucket_result(factor, bucket_name, outcomes, return_window):
        returns = [
            safe_float((value(outcome, "forward_returns") or {}).get(str(return_window)))
            for outcome in outcomes
        ]
        returns = [item for item in returns if item is not None]
        wins = [item for item in returns if item > 0]
        losses = [item for item in returns if item <= 0]
        return FactorBucketResult(
            factor=factor,
            bucket=bucket_name,
            signal_count=len(outcomes),
            win_rate=(len(wins) / len(returns)) if returns else 0.0,
            average_return=statistics.mean(returns) if returns else 0.0,
            median_return=statistics.median(returns) if returns else 0.0,
            max_drawdown=min((safe_float(value(outcome, "max_drawdown_pct")) or 0.0 for outcome in outcomes), default=0.0),
            expectancy=expectancy(wins, losses),
        )


class WeightOptimizationEngine:
    def optimize(self, outcomes, weight_combinations=None, max_combinations=None, return_window=20):
        combinations = list(weight_combinations or DEFAULT_WEIGHT_COMBINATIONS)
        if max_combinations is not None:
            combinations = combinations[: int(max_combinations)]
        results = []
        for weights in combinations:
            normalized = normalize_weights(weights)
            rescored = []
            for outcome in outcomes or []:
                score = weighted_score(outcome, normalized)
                return_value = safe_float((value(outcome, "forward_returns") or {}).get(str(return_window)))
                rescored.append((score, return_value, safe_float(value(outcome, "max_drawdown_pct")) or 0.0))
            selected = [item for item in rescored if item[0] >= 60 and item[1] is not None]
            returns = [item[1] for item in selected]
            wins = [item for item in returns if item > 0]
            losses = [item for item in returns if item <= 0]
            avg_return = statistics.mean(returns) if returns else 0.0
            exp = expectancy(wins, losses)
            win_rate = len(wins) / len(returns) if returns else 0.0
            max_dd = min((item[2] for item in selected), default=0.0)
            pf = profit_factor(returns)
            score = exp * 0.35 + win_rate * 100 * 0.25 + avg_return * 0.25 + pf * 2 - abs(max_dd) * 0.10
            results.append(
                WeightOptimizationResult(
                    weights=normalized,
                    score=round(score, 4),
                    expectancy=round(exp, 4),
                    win_rate=round(win_rate, 4),
                    average_return=round(avg_return, 4),
                    max_drawdown=round(max_dd, 4),
                    profit_factor=round(pf, 4),
                    warnings=[] if returns else ["No qualifying signals for this weight set."],
                )
            )
        results.sort(key=lambda item: (-item.score, json.dumps(item.weights, sort_keys=True)))
        for index, result in enumerate(results, start=1):
            result.rank = index
        return results


class WalkForwardValidationService:
    def __init__(self, optimizer=None):
        self.optimizer = optimizer or WeightOptimizationEngine()

    def validate(self, outcomes, window_days=180, step_days=90, max_combinations=None):
        dated = sorted(
            [outcome for outcome in (outcomes or []) if parse_date(outcome.signal_date)],
            key=lambda outcome: outcome.signal_date,
        )
        if not dated:
            return []
        start = parse_date(dated[0].signal_date)
        end = parse_date(dated[-1].signal_date)
        windows = []
        cursor = start
        while cursor and end and cursor + timedelta(days=window_days + step_days) <= end + timedelta(days=1):
            train_end = cursor + timedelta(days=window_days)
            test_end = train_end + timedelta(days=step_days)
            training = [item for item in dated if cursor <= parse_date(item.signal_date) < train_end]
            testing = [item for item in dated if train_end <= parse_date(item.signal_date) < test_end]
            if training and testing:
                optimized = self.optimizer.optimize(training, max_combinations=max_combinations)
                best = optimized[0] if optimized else WeightOptimizationResult({}, 0)
                metrics = metrics_for_outcomes(testing)
                windows.append(
                    WalkForwardWindowResult(
                        training_start=cursor.isoformat(),
                        training_end=train_end.isoformat(),
                        testing_start=train_end.isoformat(),
                        testing_end=test_end.isoformat(),
                        selected_weights=best.weights,
                        training_score=best.score,
                        testing_expectancy=metrics["expectancy"],
                        testing_win_rate=metrics["win_rate"],
                        signal_count=len(testing),
                    )
                )
            cursor += timedelta(days=step_days)
        return windows


class BenchmarkComparisonService:
    def __init__(self, repository):
        self.repository = repository

    def compare(self, outcomes, benchmark_ticker="SPY", return_window=20):
        ticker = str(benchmark_ticker or "SPY").upper()
        comparisons = []
        warnings = []
        for outcome in outcomes or []:
            signal_date = parse_date(outcome.signal_date)
            if signal_date is None:
                continue
            rows = self.repository.fetch_ohlcv(ticker, start_date=outcome.signal_date)
            future_rows = [
                row for row in rows
                if parse_date(value(row, "date")) and parse_date(value(row, "date")) > signal_date
            ][:return_window]
            if not future_rows:
                continue
            entry = safe_float(value(future_rows[0], "open")) or safe_float(value(future_rows[0], "close"))
            exit_price = safe_float(value(future_rows[-1], "close"))
            benchmark_return = pct_return(entry, exit_price)
            signal_return = safe_float((value(outcome, "forward_returns") or {}).get(str(return_window)))
            if signal_return is not None and benchmark_return is not None:
                comparisons.append((signal_return, benchmark_return))
        if not comparisons:
            warnings.append(f"No benchmark data available for {ticker}.")
        signal_returns = [item[0] for item in comparisons]
        benchmark_returns = [item[1] for item in comparisons]
        avg_signal = statistics.mean(signal_returns) if signal_returns else 0.0
        avg_benchmark = statistics.mean(benchmark_returns) if benchmark_returns else 0.0
        return BenchmarkComparisonResult(
            benchmark_ticker=ticker,
            average_signal_return=round(avg_signal, 4),
            average_benchmark_return=round(avg_benchmark, 4),
            alpha=round(avg_signal - avg_benchmark, 4),
            hit_rate_vs_benchmark=(
                sum(1 for signal, benchmark in comparisons if signal > benchmark) / len(comparisons)
                if comparisons else 0.0
            ),
            comparisons=len(comparisons),
            warnings=warnings,
        )


class ValidationPersistenceService:
    def __init__(self, repository):
        self.repository = repository

    def save_report(self, report):
        if self.repository is None or not hasattr(self.repository, "save_validation_run"):
            return None
        self.repository.save_validation_run(report)
        self.repository.save_validation_signal_results(
            value(report, "run_id"),
            value(report, "outcomes") or [],
        )
        self.repository.save_weight_optimization_results(
            value(report, "run_id"),
            value(report, "best_weight_configs") or [],
        )
        return self.repository.fetch_validation_run(value(report, "run_id"))

    def fetch_latest(self):
        if self.repository is None or not hasattr(self.repository, "fetch_latest_validation_run"):
            return None
        return self.repository.fetch_latest_validation_run()

    def fetch_history(self, limit=25, offset=0):
        if self.repository is None or not hasattr(self.repository, "fetch_validation_run_history"):
            return []
        return self.repository.fetch_validation_run_history(limit=limit, offset=offset)

    def clear(self, run_id):
        if self.repository is None or not hasattr(self.repository, "clear_validation_run"):
            return 0
        return self.repository.clear_validation_run(run_id)


class SignalQualityRecommendationPersistenceService:
    def __init__(self, repository):
        self.repository = repository

    def save_report(self, report):
        if self.repository is None or not hasattr(self.repository, "save_signal_quality_recommendation_report"):
            return None
        return self.repository.save_signal_quality_recommendation_report(report)

    def fetch_latest(self, validation_run_id=None):
        if self.repository is None or not hasattr(self.repository, "fetch_latest_signal_quality_recommendation_report"):
            return None
        return self.repository.fetch_latest_signal_quality_recommendation_report(validation_run_id)

    def fetch_history(self, limit=25, offset=0):
        if self.repository is None or not hasattr(self.repository, "fetch_signal_quality_recommendation_history"):
            return []
        return self.repository.fetch_signal_quality_recommendation_history(limit=limit, offset=offset)


class SignalQualityAnalysisService:
    SCORE_FIELDS = (
        "final_score",
        "support_score",
        "bounce_score",
        "technical_score",
        "institutional_score",
    )

    def __init__(
        self,
        min_win_rate=0.45,
        min_expectancy=0.0,
        max_drawdown_limit=-12.0,
        return_window=20,
    ):
        self.min_win_rate = min_win_rate
        self.min_expectancy = min_expectancy
        self.max_drawdown_limit = max_drawdown_limit
        self.return_window = return_window

    def analyze_report(self, report):
        outcomes = value(report, "outcomes") or []
        run_id = value(report, "run_id")
        return self.analyze(outcomes, validation_run_id=run_id)

    def analyze(self, outcomes, validation_run_id=None):
        outcomes = list(outcomes or [])
        warnings = []
        if not outcomes:
            warnings.append("No validation outcomes available for signal quality analysis.")
        groups = self.group_results(outcomes)
        weak_groups = [group for group in groups if group.weak]
        recommendations = self.recommendations_from_weak_groups(weak_groups)
        return SignalQualityRecommendationReport(
            report_id=f"quality-{uuid.uuid4().hex[:12]}",
            validation_run_id=validation_run_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            weak_groups=weak_groups,
            recommendations=recommendations,
            warnings=warnings,
        )

    def group_results(self, outcomes):
        results = []
        for dimension, grouped in self.group_outcomes(outcomes).items():
            for group_name, group_outcomes in sorted(grouped.items()):
                result = self.group_result(dimension, group_name, group_outcomes)
                results.append(result)
        return results

    def group_outcomes(self, outcomes):
        grouped = {
            "grade": {},
            "confidence_level": {},
            "setup_label": {},
            "final_score_bucket": {},
            "support_score_bucket": {},
            "bounce_score_bucket": {},
            "technical_score_bucket": {},
            "institutional_score_bucket": {},
        }
        for outcome in outcomes or []:
            self.add_group(grouped["grade"], self.text_value(outcome, "grade", "Unknown"), outcome)
            self.add_group(
                grouped["confidence_level"],
                self.text_value(outcome, "confidence_level", "Unknown"),
                outcome,
            )
            self.add_group(
                grouped["setup_label"],
                self.text_value(outcome, "setup_label", "Unknown"),
                outcome,
            )
            for field in self.SCORE_FIELDS:
                score = safe_float(value(outcome, field))
                self.add_group(
                    grouped[f"{field}_bucket"],
                    bucket_for_score(score if score is not None else 0),
                    outcome,
                )
        return grouped

    @staticmethod
    def add_group(grouped, key, outcome):
        grouped.setdefault(str(key or "Unknown"), []).append(outcome)

    @staticmethod
    def text_value(outcome, field, default):
        raw = value(outcome, field)
        if raw in (None, ""):
            return default
        return str(raw)

    def group_result(self, dimension, group_name, outcomes):
        metrics = metrics_for_outcomes(outcomes, return_window=self.return_window)
        max_drawdown = metrics.get("max_drawdown") or 0.0
        reasons = []
        if metrics["win_rate"] < self.min_win_rate:
            reasons.append(f"Win rate below {self.min_win_rate:.0%}")
        if metrics["expectancy"] < self.min_expectancy:
            reasons.append("Expectancy below target")
        if max_drawdown <= self.max_drawdown_limit:
            reasons.append(f"Drawdown worse than {abs(self.max_drawdown_limit):.1f}%")
        return SignalQualityGroupResult(
            dimension=dimension,
            group=group_name,
            signal_count=int(metrics["total_signals"]),
            win_rate=float(metrics["win_rate"]),
            expectancy=float(metrics["expectancy"]),
            average_return=float(metrics["average_return"]),
            max_drawdown=float(max_drawdown),
            weak=bool(reasons),
            reasons=reasons,
        )

    def recommendations_from_weak_groups(self, weak_groups):
        recommendations = []
        weak_groups = list(weak_groups or [])
        final_score_groups = [
            group for group in weak_groups if group.dimension == "final_score_bucket"
        ]
        if any(group.group in {"0-59", "60-69"} for group in final_score_groups):
            recommendations.append(
                SignalQualityRecommendation(
                    recommendation_type="threshold",
                    field="minimum_final_score",
                    current_value=None,
                    recommended_value=70,
                    reason="Lower final-score buckets showed weak validation performance.",
                    severity="HIGH",
                    affected_groups=[group.group for group in final_score_groups],
                )
            )
        for component in ("support", "bounce", "technical", "institutional"):
            dimension = f"{component}_score_bucket"
            component_groups = [
                group for group in weak_groups
                if group.dimension == dimension and group.group in {"0-59", "60-69"}
            ]
            if component_groups:
                recommendations.append(
                    SignalQualityRecommendation(
                        recommendation_type="threshold",
                        field=f"minimum_{component}_score",
                        current_value=None,
                        recommended_value=70,
                        reason=f"Weak {component} score buckets underperformed validation targets.",
                        severity="MEDIUM",
                        affected_groups=[group.group for group in component_groups],
                    )
                )
        low_confidence_groups = [
            group for group in weak_groups
            if group.dimension == "confidence_level" and group.group.upper() in {"LOW", "UNKNOWN"}
        ]
        if low_confidence_groups:
            recommendations.append(
                SignalQualityRecommendation(
                    recommendation_type="confidence",
                    field="confidence_requirement",
                    current_value="Allow LOW/UNKNOWN",
                    recommended_value="Require MEDIUM or HIGH",
                    reason="Low or unknown confidence groups showed poor validation performance.",
                    severity="HIGH",
                    affected_groups=[group.group for group in low_confidence_groups],
                )
            )
        weak_setup_groups = [
            group for group in weak_groups
            if group.dimension == "setup_label" and group.group not in {"Unknown", "Elite Institutional Bounce", "High-Quality Bounce"}
        ]
        if weak_setup_groups:
            recommendations.append(
                SignalQualityRecommendation(
                    recommendation_type="rejection_rule",
                    field="setup_label_filter",
                    current_value="Allow all setup labels",
                    recommended_value="Reject weak setup labels or route to watchlist only",
                    reason="Certain setup labels underperformed validation targets.",
                    severity="MEDIUM",
                    affected_groups=[group.group for group in weak_setup_groups],
                )
            )
        if not recommendations and weak_groups:
            recommendations.append(
                SignalQualityRecommendation(
                    recommendation_type="review",
                    field="manual_review",
                    current_value=None,
                    recommended_value="Review weak validation groups before changing thresholds",
                    reason="Weak groups were detected but did not map to a standard threshold rule.",
                    severity="LOW",
                    affected_groups=[f"{group.dimension}:{group.group}" for group in weak_groups],
                )
            )
        return recommendations


class AlgorithmValidationService:
    def __init__(self, repository):
        self.repository = repository
        self.replay_service = HistoricalSignalReplayService(repository)
        self.labeling_service = OutcomeLabelingService(repository)
        self.factor_analyzer = FactorPerformanceAnalyzer()
        self.optimizer = WeightOptimizationEngine()
        self.walk_forward_service = WalkForwardValidationService(self.optimizer)
        self.benchmark_service = BenchmarkComparisonService(repository)

    def run_validation(
        self,
        start_date,
        end_date,
        tickers=None,
        replay_frequency="monthly",
        forward_windows=None,
        max_weight_combinations=5,
        benchmark_ticker="SPY",
        run_id=None,
        progress_callback=None,
        cancellation_callback=None,
    ):
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        run_id = run_id or f"validation-{uuid.uuid4().hex[:12]}"
        warnings = []
        errors = []
        try:
            signals, replay_warnings = self.replay_service.replay(
                start_date,
                end_date,
                tickers=tickers,
                frequency=replay_frequency,
                progress_callback=progress_callback,
                cancellation_callback=cancellation_callback,
            )
            warnings.extend(replay_warnings)
            outcomes = self.labeling_service.label(signals, windows=forward_windows or DEFAULT_FORWARD_WINDOWS)
            factor_results = self.factor_analyzer.analyze(outcomes)
            best_weights = self.optimizer.optimize(
                outcomes,
                max_combinations=max_weight_combinations,
            )
            walk_forward = self.walk_forward_service.validate(
                outcomes,
                max_combinations=max_weight_combinations,
            )
            benchmark = self.benchmark_service.compare(outcomes, benchmark_ticker=benchmark_ticker)
            warnings.extend(benchmark.warnings)
            metrics = metrics_for_outcomes(outcomes)
        except Exception as exc:
            signals = []
            outcomes = []
            factor_results = []
            best_weights = []
            walk_forward = []
            benchmark = None
            metrics = metrics_for_outcomes([])
            errors.append(str(exc))

        report = AlgorithmValidationReport(
            run_id=run_id,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            start_date=str(start_date) if start_date is not None else None,
            end_date=str(end_date) if end_date is not None else None,
            replay_frequency=replay_frequency,
            signal_count=len(signals),
            outcome_count=len(outcomes),
            summary_metrics=metrics,
            factor_bucket_results=factor_results,
            best_weight_configs=best_weights,
            walk_forward_results=walk_forward,
            benchmark_comparison=benchmark,
            warnings=warnings,
            errors=errors,
            signals=signals,
            outcomes=outcomes,
        )
        if hasattr(self.repository, "save_validation_run"):
            ValidationPersistenceService(self.repository).save_report(report)
        return report


class AlgorithmValidationReportService:
    def export_json(self, report, output_dir, filename="algorithm_validation_report.json"):
        destination = destination_path(output_dir, filename, "json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(to_plain(report), handle, indent=2, sort_keys=True)
        return {"success": True, "path": str(destination), "message": "Algorithm validation report exported."}

    def export_summary_csv(self, report, output_dir, filename="algorithm_validation_summary.csv"):
        destination = destination_path(output_dir, filename, "csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        metrics = value(report, "summary_metrics") or {}
        row = {
            "run_id": value(report, "run_id"),
            "start_date": value(report, "start_date"),
            "end_date": value(report, "end_date"),
            "signal_count": value(report, "signal_count") or 0,
            "outcome_count": value(report, "outcome_count") or 0,
            "win_rate": value(metrics, "win_rate") or 0,
            "average_return": value(metrics, "average_return") or 0,
            "expectancy": value(metrics, "expectancy") or 0,
            "profit_factor": value(metrics, "profit_factor") or 0,
            "max_drawdown": value(metrics, "max_drawdown") or 0,
        }
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        return {"success": True, "path": str(destination), "message": "Algorithm validation summary exported."}

    def export_issue_csv(self, report, output_dir, filename="algorithm_validation_issues.csv"):
        destination = destination_path(output_dir, filename, "csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for warning in value(report, "warnings") or []:
            rows.append({"severity": "warning", "message": warning})
        for error in value(report, "errors") or []:
            rows.append({"severity": "error", "message": error})
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["severity", "message"])
            writer.writeheader()
            writer.writerows(rows)
        return {"success": True, "path": str(destination), "message": "Algorithm validation issues exported."}

    def export_recommendations_json(self, report, output_dir, filename="signal_quality_recommendations.json"):
        destination = destination_path(output_dir, filename, "json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(to_plain(report), handle, indent=2, sort_keys=True)
        return {"success": True, "path": str(destination), "message": "Signal quality recommendations exported."}

    def export_recommendations_csv(self, report, output_dir, filename="signal_quality_recommendations.csv"):
        destination = destination_path(output_dir, filename, "csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for recommendation in value(report, "recommendations") or []:
            rows.append(
                {
                    "recommendation_type": value(recommendation, "recommendation_type"),
                    "field": value(recommendation, "field"),
                    "current_value": value(recommendation, "current_value"),
                    "recommended_value": value(recommendation, "recommended_value"),
                    "severity": value(recommendation, "severity"),
                    "reason": value(recommendation, "reason"),
                    "affected_groups": "; ".join(str(item) for item in (value(recommendation, "affected_groups") or [])),
                }
            )
        fieldnames = [
            "recommendation_type",
            "field",
            "current_value",
            "recommended_value",
            "severity",
            "reason",
            "affected_groups",
        ]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return {"success": True, "path": str(destination), "message": "Signal quality recommendations exported.", "count": len(rows)}


def metrics_for_outcomes(outcomes, return_window=20):
    returns = [
        safe_float((value(outcome, "forward_returns") or {}).get(str(return_window)))
        for outcome in (outcomes or [])
    ]
    returns = [item for item in returns if item is not None]
    wins = [item for item in returns if item > 0]
    losses = [item for item in returns if item <= 0]
    return {
        "total_signals": len(outcomes or []),
        "labeled_signals": len(returns),
        "win_rate": round(len(wins) / len(returns), 4) if returns else 0.0,
        "average_return": round(statistics.mean(returns), 4) if returns else 0.0,
        "median_return": round(statistics.median(returns), 4) if returns else 0.0,
        "expectancy": round(expectancy(wins, losses), 4),
        "profit_factor": round(profit_factor(returns), 4),
        "max_drawdown": round(min((safe_float(value(outcome, "max_drawdown_pct")) or 0.0 for outcome in (outcomes or [])), default=0.0), 4),
    }


def weighted_score(outcome, weights):
    return clamp(
        (safe_float(value(outcome, "support_score")) or 0.0) * weights.get("support", 0.0)
        + (safe_float(value(outcome, "bounce_score")) or 0.0) * weights.get("bounce", 0.0)
        + (safe_float(value(outcome, "technical_score")) or 0.0) * weights.get("technical", 0.0)
        + (safe_float(value(outcome, "institutional_score")) or 0.0) * weights.get("institutional", 0.0)
    )


def normalize_weights(weights):
    raw = {key: max(0.0, safe_float(weights.get(key)) or 0.0) for key in ("support", "bounce", "technical", "institutional")}
    total = sum(raw.values())
    if total <= 0:
        return {"support": 0.25, "bounce": 0.25, "technical": 0.25, "institutional": 0.25}
    return {key: round(value / total, 4) for key, value in raw.items()}


def expectancy(wins, losses):
    if not wins and not losses:
        return 0.0
    win_rate = len(wins) / (len(wins) + len(losses))
    loss_rate = 1 - win_rate
    avg_win = statistics.mean(wins) if wins else 0.0
    avg_loss = abs(statistics.mean(losses)) if losses else 0.0
    return round(win_rate * avg_win - loss_rate * avg_loss, 4)


def profit_factor(returns):
    gains = sum(item for item in returns if item > 0)
    losses = abs(sum(item for item in returns if item < 0))
    if losses == 0:
        return gains if gains else 0.0
    return gains / losses


def pct_return(entry, exit_price):
    entry = safe_float(entry)
    exit_price = safe_float(exit_price)
    if entry in (None, 0) or exit_price is None:
        return None
    return round((exit_price - entry) / entry * 100, 4)


def bucket_for_score(score):
    score = safe_float(score) or 0.0
    if score >= 90:
        return "90-100"
    if score >= 80:
        return "80-89"
    if score >= 70:
        return "70-79"
    if score >= 60:
        return "60-69"
    return "0-59"


def grade_for_score(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def clamp(value_, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, float(value_ or 0.0)))


def normalize_tickers(tickers):
    if isinstance(tickers, str):
        tickers = tickers.split(",")
    seen = set()
    normalized = []
    for ticker in tickers or []:
        text = str(ticker).strip().upper()
        if text and text not in seen:
            seen.add(text)
            normalized.append(text)
    return normalized


def parse_date(value_):
    if isinstance(value_, date):
        return value_
    if value_ in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value_)[:10]).date()
    except ValueError:
        return None


def safe_float(value_):
    try:
        if value_ in (None, ""):
            return None
        return float(value_)
    except (TypeError, ValueError):
        return None


def value(source, key):
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def to_plain(source):
    if is_dataclass(source):
        return {key: to_plain(val) for key, val in asdict(source).items()}
    if isinstance(source, dict):
        return {key: to_plain(val) for key, val in source.items()}
    if isinstance(source, (list, tuple)):
        return [to_plain(item) for item in source]
    return source


def destination_path(output_dir, filename, suffix):
    base = Path(output_dir or "exports/validation")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(filename or "report"))
    if not safe_name.endswith(f".{suffix}"):
        safe_name = f"{safe_name}.{suffix}"
    return base / safe_name
