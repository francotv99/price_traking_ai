# n8n Workflows

Exported n8n workflow definitions in JSON format.

## Workflows

1. **workflow_1_ingesta.json**
   - Trigger: Cron every 6 hours
   - Action: POST /etl/run
   - Output: Triggers workflow_2_deteccion_alerta

2. **workflow_2_deteccion_alerta.json**
   - Trigger: Webhook from workflow_1
   - Action: POST /ml/detect (per product)
   - If anomaly:
     - Search Qdrant (semantic retrieval)
     - Send Telegram notification
     - Trigger workflow_3_reindexacion

3. **workflow_3_reindexacion.json**
   - Trigger A: Webhook from workflow_2 (reactive)
   - Trigger B: Cron weekly (preventive)
   - Action: POST /rag/reindex
   - Action: Embed and index in Qdrant

## Importing Workflows

1. Open n8n UI at http://localhost:5678
2. Click "+ New"
3. Select "Import from file"
4. Choose workflow JSON
5. Save and activate

## Implementation Status

- [x] workflow_1_ingesta.json
- [x] workflow_2_deteccion_alerta.json
- [x] workflow_3_reindexacion.json
