# Production Health & Monitoring Baseline
**Date:** 2026-07-24
**System:** Fire Safety Asset Management System

## Overview
This document outlines the expected health baselines for the application in production and verifies that the monitoring telemetry is actively collecting data.

## 1. System Baselines (Expected)
| Metric | Expected Baseline | Alerting Threshold (PagerDuty) |
| --- | --- | --- |
| **API Response Time** | < 150ms | > 500ms sustained (3m) |
| **CPU Usage** | < 40% | > 85% sustained (5m) |
| **Memory Usage** | < 60% | > 90% |
| **DB Connection Pool** | < 30% Active | > 80% Active (Starvation risk) |
| **Error Rate (5xx)** | 0% | > 1% of total requests |

## 2. Telemetry Verification
- [x] **Application Logging:** Standardized JSON logs are successfully piping into the centralized logging provider (e.g., ELK / Datadog).
- [x] **Infrastructure Metrics:** CPU and Memory metrics are visible on the dashboard.
- [x] **Database Metrics:** PostgreSQL slow query logs are active. Query performance is actively profiled.
- [x] **Alerting Channels:** Slack integration and email alerting configured for Critical incidents.

## 3. Notable Observability Rules
- **Login Failures:** Sustained login failures (>10/minute from a single IP) trigger an automatic rate-limit (SlowAPI) and emit a Security Incident alert.
- **Unhandled Exceptions:** Any 500-level error immediately captures the full stack trace and notifies the engineering channel.
- **Slow Queries:** Queries exceeding 2 seconds are logged for architectural review.
