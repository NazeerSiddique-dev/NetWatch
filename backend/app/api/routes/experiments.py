"""
Experiments API
================
Manages traffic generation experiments and detection evaluation.
Includes a software-only anomaly injection endpoint that requires no root/sudo.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.experiment import Experiment, DetectionResult, ExperimentStatus

logger = get_logger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# ── Attack profiles ──────────────────────────────────────────────────────────
# Each profile defines the anomalous metric multipliers pushed into the pipeline.
ATTACK_PROFILES = {
    "syn_flood": {
        "label": "TCP SYN Flood",
        "rx_mbps_mult": 15.0,
        "tx_mbps_mult": 1.2,
        "pps_mult": 50.0,
        "tcp_pct": 0.98,
        "anomaly_type": "traffic_spike",
        "metric_name": "rx_packets_per_sec",
    },
    "udp_flood": {
        "label": "UDP Flood",
        "rx_mbps_mult": 20.0,
        "tx_mbps_mult": 1.0,
        "pps_mult": 40.0,
        "tcp_pct": 0.02,
        "anomaly_type": "traffic_spike",
        "metric_name": "rx_mbps",
    },
    "port_scan": {
        "label": "Port Scan",
        "rx_mbps_mult": 2.0,
        "tx_mbps_mult": 3.0,
        "pps_mult": 8.0,
        "tcp_pct": 0.95,
        "anomaly_type": "connection_spike",
        "metric_name": "active_flows",
    },
    "data_exfil": {
        "label": "Data Exfiltration",
        "rx_mbps_mult": 1.0,
        "tx_mbps_mult": 12.0,
        "pps_mult": 2.0,
        "tcp_pct": 0.90,
        "anomaly_type": "traffic_spike",
        "metric_name": "tx_mbps",
    },
    "icmp_flood": {
        "label": "ICMP Ping Flood",
        "rx_mbps_mult": 10.0,
        "tx_mbps_mult": 10.0,
        "pps_mult": 30.0,
        "tcp_pct": 0.0,
        "anomaly_type": "packet_rate_spike",
        "metric_name": "total_packets_per_sec",
    },
}


async def _run_injection(
    exp_id: str,
    attack_type: str,
    duration_sec: int,
    intensity: float,
) -> None:
    """
    Background task: push anomalous metric snapshots directly into the
    WebSocket broadcast and anomaly detector for `duration_sec` seconds.
    No network privileges required — purely software simulation.
    """
    from app.api.websocket import broadcast_metric, broadcast_alert
    from app.services.anomaly.base import AnomalyResult
    from app.services.anomaly.detector_factory import get_detector
    from app.services.alert_service import create_alert_from_anomaly
    from app.schemas.metric import RealtimeMetric, ProtocolDistribution
    from app.workers.stream_worker import _last_alert

    settings = get_settings()
    profile = ATTACK_PROFILES.get(attack_type, ATTACK_PROFILES["syn_flood"])
    detector = get_detector()
    iface = settings.default_interface

    # Baseline values (low traffic)
    base_rx = 0.5
    base_tx = 0.3
    base_pps = 150.0

    detected_at = None
    alert_created = False

    start = datetime.now(timezone.utc)

    # Update experiment status → RUNNING
    async with get_db_session() as session:
        result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
        exp = result.scalar_one_or_none()
        if exp:
            exp.status = ExperimentStatus.RUNNING.value
            exp.started_at = start

    tick = 0
    while tick < duration_sec:
        await asyncio.sleep(1.0)
        tick += 1

        # Ramp up for first 3 seconds, then full intensity
        ramp = min(tick / 3.0, 1.0) * intensity
        rx = base_rx * profile["rx_mbps_mult"] * ramp
        tx = base_tx * profile["tx_mbps_mult"] * ramp
        pps = base_pps * profile["pps_mult"] * ramp

        tcp_pct = profile["tcp_pct"]
        udp_pct = max(0.0, 1.0 - tcp_pct - 0.05)
        other_pct = max(0.0, 1.0 - tcp_pct - udp_pct)

        now = datetime.now(timezone.utc)
        metric = RealtimeMetric(
            timestamp=now,
            interface=iface,
            data_source="SYNTHETIC",
            rx_mbps=rx,
            tx_mbps=tx,
            total_mbps=rx + tx,
            rx_packets_per_sec=pps * 0.6,
            tx_packets_per_sec=pps * 0.4,
            total_packets_per_sec=pps,
            avg_latency_ms=12.0 + ramp * 80.0,
            packet_loss_pct=ramp * 5.0,
            active_flows=int(50 + pps * 0.3),
            new_flows=int(pps * 0.05),
            protocols=ProtocolDistribution(
                tcp=tcp_pct * 100,
                udp=udp_pct * 100,
                other=other_pct * 100,
            ),
        )

        # Push to WebSocket dashboard so you can see the spike live
        await broadcast_metric(metric.model_dump())

        # Run through the anomaly detector
        features = [rx, tx, pps, metric.avg_latency_ms or 0, metric.packet_loss_pct]
        ano_result = detector.update(features)
        ano_result.anomaly_type = profile["anomaly_type"]
        ano_result.metric_name = profile["metric_name"]

        # If anomalous and no cooldown → create a real alert
        if ano_result.is_anomalous and not alert_created:
            key = (iface, profile["anomaly_type"])
            last = _last_alert.get(key)
            if last is None or (now - last).total_seconds() > 10:
                _last_alert[key] = now
                alert_dict = await create_alert_from_anomaly(ano_result, metric, experiment_id=exp_id)
                await broadcast_alert(alert_dict)
                detected_at = now
                alert_created = True
                logger.info("injection_alert_fired", exp_id=exp_id, type=attack_type)

    # Mark experiment COMPLETED with result
    async with get_db_session() as session:
        result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
        exp = result.scalar_one_or_none()
        if exp:
            exp.status = ExperimentStatus.COMPLETED.value
            exp.ended_at = datetime.now(timezone.utc)
            exp.anomaly_detected = alert_created
            if detected_at:
                exp.detection_time_ms = (detected_at - start).total_seconds() * 1000

    logger.info(
        "injection_complete",
        exp_id=exp_id,
        attack=attack_type,
        duration=duration_sec,
        detected=alert_created,
    )



@router.get("")
async def list_experiments():
    async with get_db_session() as session:
        result = await session.execute(select(Experiment).order_by(Experiment.created_at.desc()))
        experiments = result.scalars().all()
        return {"experiments": [_exp_to_dict(e) for e in experiments], "total": len(experiments)}


@router.get("/profiles")
async def list_attack_profiles():
    """Return available no-sudo software injection attack profiles."""
    return {
        "profiles": [
            {"id": k, "label": v["label"], "anomaly_type": v["anomaly_type"]}
            for k, v in ATTACK_PROFILES.items()
        ]
    }


@router.post("/inject")
async def inject_anomaly(body: dict, background_tasks: BackgroundTasks):
    """
    Software-only anomaly injection — NO root/sudo required.

    Directly pushes anomalous metric bursts into the WebSocket pipeline and
    anomaly detector, generating real alerts visible in the dashboard.

    Body:
        attack_type (str): One of syn_flood, udp_flood, port_scan, data_exfil, icmp_flood
        duration_sec (int): How many seconds to sustain the attack (5–120)
        intensity (float): Multiplier 0.1–1.0 (default 1.0 = full attack)
    """
    attack_type = body.get("attack_type", "syn_flood")
    duration_sec = max(5, min(120, int(body.get("duration_sec", 15))))
    intensity = max(0.1, min(1.0, float(body.get("intensity", 1.0))))

    if attack_type not in ATTACK_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack_type '{attack_type}'. Choose from: {list(ATTACK_PROFILES.keys())}",
        )

    profile = ATTACK_PROFILES[attack_type]

    # Create the experiment record
    async with get_db_session() as session:
        exp = Experiment(
            name=f"[INJECT] {profile['label']} – {datetime.now().strftime('%H:%M:%S')}",
            description=f"Software injection: {attack_type}, {duration_sec}s, intensity={intensity}",
            traffic_type=attack_type,
            duration_sec=duration_sec,
            expected_anomaly=True,
            expected_anomaly_type=profile["anomaly_type"],
            status=ExperimentStatus.PENDING.value,
        )
        session.add(exp)
        await session.flush()
        exp_id = exp.id
        exp_dict = _exp_to_dict(exp)

    # Fire off the injection as a background task (non-blocking)
    background_tasks.add_task(_run_injection, exp_id, attack_type, duration_sec, intensity)

    return {
        "message": f"Injection started: {profile['label']} for {duration_sec}s",
        "experiment": exp_dict,
        "note": "Watch the Dashboard and Alerts page — anomalies will appear within ~3 seconds.",
    }



@router.post("")
async def create_experiment(body: dict):
    async with get_db_session() as session:
        exp = Experiment(
            name=body.get("name", f"Experiment {datetime.now().strftime('%H:%M:%S')}"),
            description=body.get("description"),
            traffic_type=body.get("traffic_type", "normal_tcp"),
            src_namespace=body.get("src_namespace"),
            dst_namespace=body.get("dst_namespace"),
            src_ip=body.get("src_ip"),
            dst_ip=body.get("dst_ip"),
            dst_port=body.get("dst_port"),
            packet_rate=body.get("packet_rate"),
            duration_sec=body.get("duration_sec", 30),
            burst_size=body.get("burst_size"),
            expected_anomaly=body.get("expected_anomaly", False),
            expected_anomaly_type=body.get("expected_anomaly_type"),
            status=ExperimentStatus.PENDING.value,
        )
        session.add(exp)
        await session.flush()
        exp_id = exp.id
        exp_dict = _exp_to_dict(exp)
    return exp_dict


@router.get("/evaluation")
async def evaluation_summary():
    """Compute precision, recall, F1 across all completed experiments."""
    async with get_db_session() as session:
        result = await session.execute(select(DetectionResult))
        records = result.scalars().all()

        if not records:
            return {"message": "No experiments completed yet", "total_experiments": 0}

        tp = sum(1 for r in records if r.true_positive)
        fp = sum(1 for r in records if r.false_positive)
        tn = sum(1 for r in records if r.true_negative)
        fn = sum(1 for r in records if r.false_negative)

        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision and recall else None)

        latencies = [r.detection_latency_ms for r in records if r.detection_latency_ms]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

        return {
            "total_experiments": len(records),
            "true_positives": tp, "false_positives": fp,
            "true_negatives": tn, "false_negatives": fn,
            "precision": round(precision * 100, 1) if precision else None,
            "recall": round(recall * 100, 1) if recall else None,
            "f1_score": round(f1 * 100, 1) if f1 else None,
            "avg_detection_latency_ms": round(avg_latency, 1) if avg_latency else None,
        }


@router.get("/{exp_id}")
async def get_experiment(exp_id: str):
    async with get_db_session() as session:
        result = await session.execute(select(Experiment).where(Experiment.id == exp_id))
        exp = result.scalar_one_or_none()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return _exp_to_dict(exp)


def _exp_to_dict(e: Experiment) -> dict:
    return {
        "id": e.id, "name": e.name, "description": e.description,
        "status": e.status, "traffic_type": e.traffic_type,
        "src_namespace": e.src_namespace, "dst_namespace": e.dst_namespace,
        "src_ip": e.src_ip, "dst_ip": e.dst_ip, "dst_port": e.dst_port,
        "packet_rate": e.packet_rate, "duration_sec": e.duration_sec,
        "burst_size": e.burst_size,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "ended_at": e.ended_at.isoformat() if e.ended_at else None,
        "expected_anomaly": bool(e.expected_anomaly),
        "expected_anomaly_type": e.expected_anomaly_type,
        "anomaly_detected": bool(e.anomaly_detected) if e.anomaly_detected is not None else None,
        "detection_time_ms": e.detection_time_ms,
        "detected_alert_id": e.detected_alert_id,
        "error_message": e.error_message,
        "created_at": e.created_at.isoformat(),
    }
