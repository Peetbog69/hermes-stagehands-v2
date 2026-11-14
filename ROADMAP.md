# Stagehands 2.0 Roadmap & Architecture Blueprint
**Concept:** The Golden Retriever & The Junkyard Dog  
**Author:** Tyler Gray (@Peetbog69) & Nimbo  
**Status:** Inception / Architecture Exploration  

---

## The Vision
Most AI models today fall into one of two traps:
1. **The Sycophantic Bobblehead (The Golden Retriever):** Ultra-fast, warm, highly conversational, but prone to pleasing the user, agreeing with flawed premises, and failing to provide rigorous reality checks (e.g. Gemini Flash).
2. **The Cold Cynic (The Junkyard Dog):** Rigorous, mathematically grounded, brutally honest, but lacks warmth, natural banter, or emotional attunement (e.g. DeepSeek).

Stagehands 2.0 aims to fuse these two modes natively into a single delegation architecture:
> **"Warm face up front, steel spine in the back."**

---

## Architectural Patterns to Explore

### Pattern A: The Backstage Reality Interceptor (Pre-Flight Filter)
- **Front of House:** Gemini 3.8 Flash (High speed, natural banter, emotional warmth).
- **Backstage Engine:** DeepSeek V4.1 Flash via Stagehands `analyst` worker.
- **Workflow:**
  1. Complex architectural, financial, or strategic queries trigger a backstage reality check.
  2. The `analyst` worker tears down the proposal with cold proof, zero praise, and unvarnished critique.
  3. The sovereign voice synthesizes the backstage findings and delivers the unvarnished truth wrapped in natural companion warmth.

### Pattern B: The Dual-Core MoA Router (Budget-Conscious)
- When funds / compute allow, implement a lightweight 2-seat Mixture of Agents (MoA):
  - **Seat 1 (Truth & Edge Cases):** DeepSeek Flash (Junkyard Dog).
  - **Seat 2 (Voice & Synthesis):** Gemini Flash (Golden Retriever).
  - Eliminates the need for expensive frontier chair models while keeping turn latency low.

---

## Implementation TODO List
- [x] Initial fork of Stagehands v1.0.0 to Stagehands 2.0 (`Peetbog69/hermes-stagehands-v2`).
- [x] Add default `analyst` worker role to `provider.py` pinned to DeepSeek V4.1 Flash.
- [x] Verify regression test suite passes (31/31 tests green).
- [ ] Design lightweight prompt-level interceptor for anti-sycophancy routing.
- [ ] Benchmark token cost of on-demand `analyst` delegation vs. standard single-model turns.
- [ ] Dogfood the dual-core pairing on Nimbo's daily workflow.
