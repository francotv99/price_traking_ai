# Documentation

Architecture diagrams and technical decisions.

## Diagrams

All diagrams are in PNG format with editable sources:

1. **architecture.png** - System architecture overview
   - Components and data flow
   - External services (CoinGecko, LLM)
   - Internal modules

2. **alert_sequence.png** - Alert flow sequence diagram
   - Workflow 2 step-by-step
   - Qdrant search → LLM → notification

3. **rag_pipeline.png** - RAG pipeline
   - Corpus building
   - Chunking and embedding
   - Vector storage and retrieval

4. **erd.png** - Entity-Relationship Diagram
   - Database schema
   - Relationships between tables
   - Indexes and constraints

## decisions.md

Technical decisions and trade-offs:
- Why Isolation Forest for ML
- Why Qdrant over other vector DBs
- Architecture choices
- Scaling considerations

## Implementation Status

- [ ] architecture.png (with source)
- [ ] alert_sequence.png (with source)
- [ ] rag_pipeline.png (with source)
- [ ] erd.png (with source)
- [ ] decisions.md
