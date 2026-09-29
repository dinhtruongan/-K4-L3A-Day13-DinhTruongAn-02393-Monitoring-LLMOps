from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "data" / "logs.jsonl"
CHART_HEIGHT = 250
TIME_RANGE_MINUTES = 60
REFRESH_SECONDS = 30

st.set_page_config(
    page_title="Day 13 · LLMOps monitoring",
    page_icon=":material/monitoring:",
    layout="wide",
)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False, max_entries=4)
def load_logs(path: str, modified_ns: int, file_size: int) -> pd.DataFrame:
    del modified_ns, file_size  # Included in the cache key so new log writes refresh the data.
    file_path = Path(path)
    records: list[dict] = []
    if not file_path.exists():
        return pd.DataFrame()

    with file_path.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)

    frame = pd.DataFrame.from_records(records)
    if not frame.empty and "ts" in frame:
        frame["ts"] = pd.to_datetime(frame["ts"], utc=True, errors="coerce")
        frame = frame.dropna(subset=["ts"])
    return frame


def percentile(values: pd.Series, pct: int) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.quantile(pct / 100, interpolation="nearest")) if not numeric.empty else 0.0


def line_with_threshold(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    threshold: float,
    unit: str,
    height: int = CHART_HEIGHT,
) -> alt.LayerChart | None:
    if frame.empty or y not in frame or frame[y].dropna().empty:
        return None

    tooltip = [
        alt.Tooltip(f"{x}:T", title="Time", format="%H:%M:%S"),
        alt.Tooltip(f"{y}:Q", title=unit, format=",.2f"),
    ]
    line = (
        alt.Chart(frame)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y(f"{y}:Q", title=unit, scale=alt.Scale(zero=False)),
            tooltip=tooltip,
        )
    )
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(
        color="#dc6b52", strokeDash=[6, 4], strokeWidth=1.5
    ).encode(y="threshold:Q")
    return (line + rule).properties(height=height)


def multi_line_with_threshold(
    frame: pd.DataFrame,
    *,
    x: str,
    series: list[str],
    threshold: float,
    unit: str,
    height: int = CHART_HEIGHT,
) -> alt.LayerChart | None:
    if frame.empty or not all(column in frame for column in series):
        return None
    long_frame = frame.melt(id_vars=[x], value_vars=series, var_name="series", value_name="value")
    if long_frame["value"].dropna().empty:
        return None
    lines = (
        alt.Chart(long_frame)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%H:%M")),
            y=alt.Y("value:Q", title=unit, scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip(f"{x}:T", title="Time", format="%H:%M:%S"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=unit, format=",.2f"),
            ],
        )
    )
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(
        color="#dc6b52", strokeDash=[6, 4], strokeWidth=1.5
    ).encode(y="threshold:Q")
    return (lines + rule).properties(height=height)


def render_panel(title: str, chart: alt.LayerChart | None, empty_message: str) -> None:
    with st.container(border=True):
        st.subheader(title)
        if chart is None:
            st.info(empty_message)
        else:
            st.altair_chart(chart, width="stretch")


def summarize_window(logs: pd.DataFrame) -> dict[str, float | int]:
    requests = logs[logs.get("event", pd.Series(dtype=str)) == "request_received"]
    responses = logs[logs.get("event", pd.Series(dtype=str)) == "response_sent"]
    failures = logs[logs.get("event", pd.Series(dtype=str)) == "request_failed"]
    latency = pd.to_numeric(responses.get("latency_ms", pd.Series(dtype=float)), errors="coerce")
    retrieval = pd.to_numeric(
        logs.get("tool_success", pd.Series(dtype=object)), errors="coerce"
    ).dropna()
    return {
        "requests": len(requests),
        "latency_p95": percentile(latency, 95),
        "error_rate": (len(failures) / len(requests) * 100) if len(requests) else 0.0,
        "retrieval_success": (float(retrieval.astype(bool).mean() * 100) if len(retrieval) else 0.0),
        "cost": float(pd.to_numeric(responses.get("cost_usd", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
    }


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_dashboard() -> None:
    st.title(":material/monitoring: Day 13 · LLMOps monitoring")
    st.caption("Structured logs · 60-minute window · refresh every 30 seconds")

    if not LOG_PATH.exists():
        st.warning("No application log found yet. Start the API and run the sample workload.")
        return

    stat = LOG_PATH.stat()
    records = load_logs(str(LOG_PATH), stat.st_mtime_ns, stat.st_size)
    if records.empty or "ts" not in records:
        st.warning("The log file has no valid JSON records yet.")
        return

    now = datetime.now(timezone.utc)
    start = pd.Timestamp(now - timedelta(minutes=TIME_RANGE_MINUTES))
    window = records[records["ts"] >= start].copy()
    if window.empty:
        st.info("No events in the last 60 minutes. Run `python scripts/load_test.py` to populate the panels.")
        return

    summary = summarize_window(window)
    with st.container(horizontal=True):
        st.metric("Requests", f"{summary['requests']:,}", border=True)
        st.metric("Latency P95", f"{summary['latency_p95']:,.0f} ms", border=True)
        st.metric("Error rate", f"{summary['error_rate']:.1f}%", border=True)
        st.metric("Retrieval success", f"{summary['retrieval_success']:.1f}%", border=True)
        st.metric("Cost", f"${summary['cost']:.4f}", border=True)

    window["minute"] = window["ts"].dt.floor("min")
    received = window[window["event"] == "request_received"]
    response = window[window["event"] == "response_sent"]
    failures = window[window["event"] == "request_failed"]

    latency_rows = response[["minute", "latency_ms", "ttft_ms"]].copy()
    for field in ("latency_ms", "ttft_ms"):
        latency_rows[field] = pd.to_numeric(latency_rows[field], errors="coerce")
    latency_panel = latency_rows.groupby("minute", as_index=False).agg(
        p50_ms=("latency_ms", lambda values: percentile(values, 50)),
        p95_ms=("latency_ms", lambda values: percentile(values, 95)),
        p99_ms=("latency_ms", lambda values: percentile(values, 99)),
        ttft_p95_ms=("ttft_ms", lambda values: percentile(values, 95)),
    )
    traffic_panel = received.groupby("minute").size().rename("requests_per_minute").reset_index()

    errors_by_minute = failures.groupby("minute").size().rename("failures")
    requests_by_minute = received.groupby("minute").size().rename("requests")
    retrieval_events = window[window.get("tool_success", pd.Series(index=window.index, dtype=object)).notna()].copy()
    retrieval_events["minute"] = retrieval_events["ts"].dt.floor("min")
    success_by_minute = retrieval_events.groupby("minute")["tool_success"].apply(
        lambda values: pd.to_numeric(values, errors="coerce").dropna().mean() * 100
    ).rename("retrieval_success_pct")
    errors_panel = pd.concat(
        [errors_by_minute, requests_by_minute, success_by_minute], axis=1
    ).reset_index()
    errors_panel[["failures", "requests"]] = errors_panel[["failures", "requests"]].fillna(0)
    errors_panel["error_rate_pct"] = errors_panel.apply(
        lambda row: row["failures"] / row["requests"] * 100 if row["requests"] else 0,
        axis=1,
    )

    cost_panel = response[["minute", "cost_usd"]].copy()
    cost_panel["cost_usd"] = pd.to_numeric(cost_panel["cost_usd"], errors="coerce").fillna(0)
    cost_panel = cost_panel.groupby("minute", as_index=False)["cost_usd"].sum().sort_values("minute")
    cost_panel["cumulative_cost_usd"] = cost_panel["cost_usd"].cumsum()

    token_panel = response[["minute", "tokens_in", "tokens_out"]].copy()
    for field in ("tokens_in", "tokens_out"):
        token_panel[field] = pd.to_numeric(token_panel[field], errors="coerce").fillna(0)
    token_panel = token_panel.groupby("minute", as_index=False)[["tokens_in", "tokens_out"]].sum().sort_values("minute")
    token_panel["input_tokens"] = token_panel["tokens_in"].cumsum()
    token_panel["output_tokens"] = token_panel["tokens_out"].cumsum()
    token_panel["total_tokens"] = token_panel["tokens_in"].add(token_panel["tokens_out"]).cumsum()

    quality_panel = response[["minute", "quality_score"]].copy()
    quality_panel["quality_score"] = pd.to_numeric(quality_panel["quality_score"], errors="coerce")
    quality_panel = quality_panel.groupby("minute", as_index=False)["quality_score"].mean()

    row_one = st.columns(2)
    with row_one[0]:
        render_panel(
            "1 · Latency and TTFT",
            multi_line_with_threshold(
                latency_panel,
                x="minute",
                series=["p50_ms", "p95_ms", "p99_ms", "ttft_p95_ms"],
                threshold=3000,
                unit="ms",
            ),
            "No response latency samples in this window.",
        )
    with row_one[1]:
        render_panel(
            "2 · Request traffic",
            line_with_threshold(traffic_panel, x="minute", y="requests_per_minute", threshold=1, unit="requests/min"),
            "No request events in this window.",
        )

    row_two = st.columns(2)
    with row_two[0]:
        with st.container(border=True):
            st.subheader("3 · Errors and retrieval success")
            error_metrics = st.columns(2)
            error_metrics[0].metric("Error rate", f"{summary['error_rate']:.1f}%")
            error_metrics[1].metric("Retrieval success", f"{summary['retrieval_success']:.1f}%")
            error_chart = line_with_threshold(
                errors_panel,
                x="minute",
                y="error_rate_pct",
                threshold=2,
                unit="percent",
            )
            retrieval_chart = line_with_threshold(
                errors_panel,
                x="minute",
                y="retrieval_success_pct",
                threshold=90,
                unit="percent",
            )
            if error_chart is None:
                st.info("No request/error samples in this window.")
            else:
                st.altair_chart(error_chart, width="stretch")
            if retrieval_chart is not None:
                st.caption("Retrieval success · SLO ≥ 90%")
                st.altair_chart(retrieval_chart, width="stretch")
            error_types = failures.get("error_type", pd.Series(dtype=str)).fillna("unknown").value_counts()
            breakdown = ", ".join(f"{name}: {count}" for name, count in error_types.items()) or "No failures"
            st.caption(f"Error breakdown · {breakdown}")
    with row_two[1]:
        render_panel(
            "4 · Cost",
            line_with_threshold(cost_panel, x="minute", y="cumulative_cost_usd", threshold=2.5, unit="USD"),
            "No cost samples in this window.",
        )

    row_three = st.columns(2)
    token_panel = token_panel.rename(
        columns={"tokens_in": "input_tokens", "tokens_out": "output_tokens"}
    )
    with row_three[0]:
        render_panel(
            "5 · Input and output tokens",
            multi_line_with_threshold(
                token_panel,
                x="minute",
                series=["input_tokens", "output_tokens", "total_tokens"],
                threshold=50000,
                unit="tokens",
            ),
            "No token samples in this window.",
        )
    with row_three[1]:
        render_panel(
            "6 · Quality proxy",
            line_with_threshold(quality_panel, x="minute", y="quality_score", threshold=0.75, unit="score (0–1)"),
            "No quality samples in this window.",
        )

    st.caption("Data source: data/logs.jsonl · No message, user, or session fields are displayed.")


render_dashboard()
