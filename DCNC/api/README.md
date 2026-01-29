# DCNC Data Quality API

Production-ready REST API for data classification and correction.

## Quick Start

### Installation

```bash
# Install dependencies
pip install fastapi uvicorn pandas

# Run API server
uvicorn DCNC.api.app:app --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Endpoints

### Classification

**Classify data into good/bad/reject:**

```bash
POST /api/v1/classify
Content-Type: application/json

{
  "file_path": "/path/to/data.csv",
  "has_header": true,
  "options": {
    "enable_ml_clustering": true,
    "enable_ensemble_detection": true
  }
}
```

**Upload file directly:**

```bash
POST /api/v1/classify/upload
Content-Type: multipart/form-data

file: <file>
has_header: true
enable_ml_clustering: true
```

**Check job status:**

```bash
GET /api/v1/classify/status/{job_id}
```

### Correction

**Classify and correct data:**

```bash
POST /api/v1/classify-and-correct
Content-Type: application/json

{
  "file_path": "/path/to/data.csv",
  "has_header": true,
  "correction_threshold": 0.7,
  "options": {
    "enable_ml_clustering": true
  }
}
```

**Upload and correct:**

```bash
POST /api/v1/classify-and-correct/upload
Content-Type: multipart/form-data

file: <file>
has_header: true
correction_threshold: 0.7
```

## Response Format

### Classification Response

```json
{
  "status": "success",
  "job_id": "uuid",
  "files": {
    "good_data": "output/api/{job_id}/good_data.csv",
    "bad_data": "output/api/{job_id}/bad_data.csv",
    "reject_data": "output/api/{job_id}/reject_data.csv",
    "fingerprint": "output/api/{job_id}/fingerprint.json"
  },
  "statistics": {
    "total_rows": 1000,
    "good_rows": 950,
    "bad_rows": 30,
    "reject_rows": 20,
    "columns_processed": 36
  }
}
```

### Correction Response

```json
{
  "status": "success",
  "job_id": "uuid",
  "files": {
    "good_data": "output/api/{job_id}/good_data.csv",
    "bad_data": "output/api/{job_id}/bad_data.csv",
    "reject_data": "output/api/{job_id}/reject_data.csv",
    "corrected_data": "output/api/{job_id}/corrected_data.csv",
    "fingerprint": "output/api/{job_id}/fingerprint.json",
    "correction_report": "output/api/{job_id}/correction_report.json"
  },
  "statistics": {
    "total_rows": 1000,
    "good_rows": 950,
    "corrected_rows": 25,
    "reject_rows": 5,
    "corrections_applied": 45,
    "corrections_rejected": 5
  }
}
```

## Configuration

Environment variables:

- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `OUTPUT_DIR`: Output directory (default: output/api)
- `MAX_FILE_SIZE`: Max file size in bytes (default: 100MB)
- `CORS_ORIGINS`: CORS origins (default: *)
- `JOB_TIMEOUT`: Job timeout in seconds (default: 300)
- `LOG_LEVEL`: Logging level (default: INFO)

## Large File Handling

Files larger than 50MB are automatically processed in the background. Use the status endpoint to check progress:

```bash
GET /api/v1/classify/status/{job_id}
```

Response:
```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 0.5,
  "started_at": "2026-01-27T10:00:00Z"
}
```

## Frontend Integration

### CORS

CORS is enabled by default. Configure allowed origins:

```bash
export CORS_ORIGINS="http://localhost:3000,https://yourdomain.com"
```

### Example Frontend Code

```javascript
// Upload and classify
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('has_header', 'true');

const response = await fetch('http://localhost:8000/api/v1/classify/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Files:', result.files);
console.log('Statistics:', result.statistics);
```

## Error Handling

All errors return proper HTTP status codes:

- `400`: Bad Request (validation errors)
- `404`: Not Found (file/job not found)
- `413`: Payload Too Large (file too big)
- `500`: Internal Server Error

Error response format:
```json
{
  "status": "error",
  "message": "Error message",
  "detail": "Detailed error information"
}
```

## Testing

Run test scripts:

```bash
# Test classification API
python testing_data/test_api_classification.py

# Test correction API
python testing_data/test_api_correction.py
```

## Production Deployment

### Recommended Setup

1. **Use production ASGI server:**
   ```bash
   uvicorn DCNC.api.app:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Use Redis/Celery for job queue:**
   - Replace in-memory job queue with Redis
   - Use Celery for distributed task processing

3. **Configure CORS:**
   ```bash
   export CORS_ORIGINS="https://yourdomain.com"
   ```

4. **Set file size limits:**
   ```bash
   export MAX_FILE_SIZE=104857600  # 100MB
   ```

5. **Enable logging:**
   ```bash
   export LOG_LEVEL=INFO
   ```

## Architecture

```
DCNC/api/
├── app.py                    # FastAPI application
├── config.py                 # Configuration
├── routes/
│   ├── health.py            # Health check endpoints
│   ├── classification.py    # Classification endpoints
│   └── correction.py        # Correction endpoints
├── services/
│   ├── classification_service.py  # Classification logic
│   └── correction_service.py       # Correction logic
├── models/
│   ├── request.py           # Request models
│   └── response.py          # Response models
└── utils/
    ├── file_utils.py        # File handling
    └── job_queue.py         # Background job queue
```

---

**Version**: 1.0.0  
**Status**: Production Ready ✅
