# PromptGuard: Identity-First Access Control for Large Language Models

## A Critical Analysis of Proactive, Zero Trust Security for Enterprise AI

**Research Paper** | Dayananda Thaloori | 2025

### Abstract

As enterprises rapidly adopt Large Language Models, a critical security gap has emerged: current guardrails rely on reactive, content-centric filtering that is both easily bypassed and operationally frustrating. This paper proposes "Identity-First" access control — a Zero Trust architecture that shifts LLM security from "What are you asking?" to "Who is asking?" by anchoring AI governance to enterprise identity and access management systems.

The architecture intercepts LLM requests at the network perimeter, enriches prompts with authoritative role-based context from enterprise IAM, and enforces granular capability boundaries through a 5-tier trust framework — eliminating the need for brittle post-generation content filtering.

### Key Findings

- **No single commercial product** currently offers the combination of perimeter-based identity lookup and dynamic, role-based prompt transformation for LLM policy enforcement (analysis of 8 commercial solutions including LiteLLM, Portkey, Akamai, Check Point, and others)
- A **hybrid Policy-as-Prompt + Policy-as-Code** (OPA/Rego) approach provides the strongest defense-in-depth architecture
- Identity-first controls can reduce false positive rates from ~20% to <3% compared to content-filtering approaches
- The paradigm aligns with existing Zero Trust infrastructure investments, reducing adoption friction

### The Problem

Current enterprise LLM security suffers from 8 critical weaknesses:

| Issue | Current Approach | Impact |
|-------|-----------------|--------|
| False Positives | One-size-fits-all content blocks | Legitimate users frustrated, productivity loss |
| Prompt Injection | Post-generation filtering | Easily bypassed, wasted compute |
| No Granularity | Same restrictions for all roles | Security teams can't do their jobs |
| Compute Waste | Generate-then-filter | High costs, poor performance |
| No Context | Stateless security checks | No understanding of user intent or role |
| Insider Risk | No role differentiation | Powers dangerous queries for unauthorized users |
| No Audit Trail | Minimal logging | Compliance gaps (SOX, SOC2, HIPAA) |
| Binary Decisions | Block or allow only | No nuanced, risk-based access |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PromptGuard Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User ──► Application Gateway / Network Edge                     │
│                    │                                             │
│                    ▼                                             │
│           ┌───────────────┐                                      │
│           │  1. INTERCEPT  │  Capture LLM request at perimeter   │
│           └───────┬───────┘                                      │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐     ┌──────────────────┐            │
│           │ 2. IDENTIFY   │────►│ Enterprise IAM   │            │
│           │               │     │ (Okta/Azure AD)  │            │
│           └───────┬───────┘     └──────────────────┘            │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐     ┌──────────────────┐            │
│           │ 3. SCORE      │────►│ Trust Scoring    │            │
│           │               │     │ Engine (6 signals)│            │
│           └───────┬───────┘     └──────────────────┘            │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐     ┌──────────────────┐            │
│           │ 4. ENRICH     │────►│ Prompt Template  │            │
│           │               │     │ Gallery          │            │
│           └───────┬───────┘     └──────────────────┘            │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐                                      │
│           │  5. ENFORCE   │  LLM processes with auth context     │
│           └───────┬───────┘                                      │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐     ┌──────────────────┐            │
│           │ 6. VALIDATE   │────►│ Response Policy  │            │
│           │               │     │ Engine           │            │
│           └───────┬───────┘     └──────────────────┘            │
│                   │                                              │
│                   ▼                                              │
│           ┌───────────────┐     ┌──────────────────┐            │
│           │  7. AUDIT     │────►│ SIEM / Immutable │            │
│           │               │     │ Audit Trail      │            │
│           └───────────────┘     └──────────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5-Tier Trust Framework

The framework maps enterprise roles to granular LLM capability boundaries:

| Trust Level | Score | User Profiles | Capabilities | Query Limit |
|-------------|-------|---------------|-------------|-------------|
| **L1 -- Basic** | 0-20 | Interns, new hires, contractors | General Q&A, simple summaries | 200 chars |
| **L2 -- Business** | 21-40 | Sales, admin, customer service | Documents, market research, basic scripts | 500 chars |
| **L3 -- Technical** | 41-60 | Senior devs, IT admins, team leads | Code generation, system architecture, security best practices | 1,500 chars |
| **L4 -- Executive** | 61-80 | Directors, legal counsel, C-suite | Regulatory interpretation, crisis management, strategic analysis | 3,000 chars |
| **L5 -- Security** | 81-100 | CISO, pen testers, IR team | Exploit research, red team support, forensic analysis, threat hunting | Unlimited |

### 9-Category Capability Matrix

Each trust level grants access to a specific subset of 9 capability categories:

| Level | Basic | Document | Business | Code | System | Security | Compliance | Executive | Red Team |
|-------|:-----:|:--------:|:--------:|:----:|:------:|:--------:|:----------:|:---------:|:--------:|
| L1    |   Y   |    -     |    -     |  -   |   -    |    -     |     -      |     -     |    -     |
| L2    |   Y   |    Y     |    Y     |  Y   |   -    |    -     |     -      |     -     |    -     |
| L3    |   Y   |    Y     |    Y     |  Y   |   Y    |    Y     |     -      |     -     |    -     |
| L4    |   Y   |    Y     |    Y     |  Y   |   Y    |    Y     |     Y      |     Y     |    -     |
| L5    |   Y   |    Y     |    Y     |  Y   |   Y    |    Y     |     Y      |     Y     |    Y     |

### Dynamic Trust Scoring

Trust scores are computed from 6 weighted signals -- not static role assignments:

```
Trust Score = sum(signal x weight)

┌────────────────────────┬────────┐
│ Signal                 │ Weight │
├────────────────────────┼────────┤
│ Role Baseline          │  30%   │
│ UEBA Score             │  25%   │
│ Query Sensitivity      │  20%   │
│ Temporal Risk          │  10%   │
│ Device Posture         │  10%   │
│ Session Behavior       │   5%   │
└────────────────────────┴────────┘
```

This enables **just-in-time trust elevation** -- a developer investigating a production incident can receive temporarily elevated capabilities based on behavioral signals, without manual privilege requests.

### Competitive Landscape

Analysis of 8 commercial solutions reveals a market gap:

| Solution | Identity Integration | Dynamic Prompting | Trust Tiers | SIEM Integration | Self-Hosted |
|----------|:-------------------:|:-----------------:|:-----------:|:----------------:|:-----------:|
| LiteLLM | Partial | No | No | No | Yes |
| Portkey | Partial | No | No | No | Yes |
| TrueFoundry | No | No | No | No | Yes |
| Akamai | Yes | No | No | Partial | No |
| Check Point | No | No | No | Yes | No |
| Robust Intelligence | No | No | No | Partial | No |
| Lasso Security | No | No | No | No | No |
| **PromptGuard** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

### Defense-in-Depth: Hybrid Architecture

The paper recommends a **hybrid approach** combining two enforcement mechanisms:

**Policy-as-Prompt (Natural Language)**
- Role-appropriate system prompt templates injected before user queries
- Leverages LLM's instruction-following capabilities
- Flexible, easy to update, handles nuanced scenarios

**Policy-as-Code (OPA/Rego)**
- Deterministic policy engine for hard security boundaries
- Cannot be bypassed through prompt manipulation
- Cryptographically signed policy bundles
- Versioned, auditable, testable

```
User Query
    │
    ├──► OPA/Rego Engine ──► HARD DENY (blocked categories)
    │                         │
    │                     PASS ▼
    │
    ├──► Prompt Template ──► SOFT ENFORCE (capability boundaries)
    │    Gallery              │
    │                         ▼
    └──────────────────► LLM Processing
                              │
                              ▼
                     Response Validation
                              │
                              ▼
                     Audit Trail (SIEM)
```

### Enterprise Risk Scenarios

The paper details 8 enterprise risk scenarios that PromptGuard addresses:

1. **Social Engineering Facilitation** -- Preventing LLMs from crafting targeted phishing content based on user role
2. **Compliance Violation** -- Blocking automated decision-making in hiring/lending without oversight
3. **Malicious Code Generation** -- Role-gating exploit development capabilities
4. **Contract Manipulation** -- Restricting legal document modification to authorized roles
5. **Data Aggregation Attacks** -- Preventing unauthorized intelligence profiling
6. **Shadow IT Integration** -- Detecting unauthorized LLM-to-enterprise-system bridges
7. **Insider Trading** -- Blocking pattern analysis of material non-public information
8. **Privacy Violations** -- Preventing behavioral profiling through data correlation

### SIEM Integration

PromptGuard generates structured audit logs designed for security operations:

```
// Sample XQL Query — Detect Trust Level Anomalies
dataset = promptguard_logs
| filter trust_level_override = true
| stats count by user_id, original_level, elevated_level, reason
| filter count > 3
| sort count desc
```

### Paper Structure

The full research paper (15,000 words, 66 citations) covers:

1. **Executive Summary** -- Core thesis and key findings
2. **The Enterprise LLM Security Dilemma** -- Analysis of current state failures
3. **Architectural Deep Dive** -- System design, components, and data flow
4. **Competitive Landscape Analysis** -- 8-vendor comparison and market gap identification
5. **Critical Evaluation & Security Risk Analysis** -- Threat model with 6 attack vectors
6. **Strategic Recommendations** -- Hybrid architecture and implementation roadmap
7. **Conclusion** -- Future directions and industry implications

### Related Work

This research builds on concepts from:
- NIST AI Risk Management Framework (AI RMF)
- OWASP Top 10 for LLM Applications
- Zero Trust Architecture (NIST SP 800-207)
- MITRE ATLAS (Adversarial Threat Landscape for AI Systems)

### Citation

```
Thaloori, D. (2025). "Identity-First: A Critical Analysis of Proactive, Zero Trust
Access Control for Large Language Models." Independent Research.
```

### License

This research is published under the [MIT License](LICENSE). The framework design and architectural patterns described are free to use, modify, and distribute.

### Author

**Dayananda Thaloori** -- Security engineer with 10 years of experience in detection & response, insider threat detection, and enterprise security. Currently researching the intersection of identity-based security and AI governance.

- [LinkedIn](https://linkedin.com/in/daya-thaloori)
- [GitHub](https://github.com/Dayachowdry)

---

*This repository contains the research paper, architectural specifications, and reference implementation concepts for PromptGuard. For questions or collaboration, please open an issue.*
