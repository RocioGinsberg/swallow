# Phase 2 Draft

## Direction

Phase 2 is the earliest stage where a dedicated provider-routing layer and a broader capability/plugin extension surface are expected to make sense.

## Likely areas of work

- provider-routing abstraction
- proxy/provider compatibility layer
- auth profile support
- cost/quality-aware routing policies
- broader executor and provider configuration
- stronger capability/plugin extension interfaces
- more advanced orchestration policies across executors and capability packs

## Likely non-goals

- solving every provider edge case immediately
- over-generalizing before real usage patterns are clear

## Entry condition

Phase 2 should start only after:
- Phase 0 has proven the local workflow loop
- Phase 1 has clarified executor, capability, and retrieval requirements
- real routing needs exist across providers or auth paths

## Notes

This is a directional draft, not a locked implementation contract.
