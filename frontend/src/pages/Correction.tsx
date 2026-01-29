import { useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  TextField,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { correctionApi } from '../services/api'

function Correction() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [hasHeader, setHasHeader] = useState(true)
  const [correctionThreshold, setCorrectionThreshold] = useState(0.7)
  const [maxCorrectionsPerColumn, setMaxCorrectionsPerColumn] = useState(1000)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setError(null)
      setResult(null)
    }
  }

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a CSV file.')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await correctionApi.classifyAndCorrect(file, {
        has_header: hasHeader,
        correction_threshold: correctionThreshold,
        max_corrections_per_column: maxCorrectionsPerColumn,
      })
      setResult(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Correction failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Correction
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Upload a CSV to classify and correct bad data in one step.
      </Typography>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Upload CSV
        </Typography>
        <Button
          variant="outlined"
          component="label"
          startIcon={<CloudUploadIcon />}
          sx={{ mb: 2, display: 'block' }}
        >
          Choose file
          <input type="file" hidden accept=".csv" onChange={handleFileChange} />
        </Button>
        {file && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Selected: {file.name}
          </Typography>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 2, maxWidth: 320 }}>
          <TextField
            label="Correction threshold"
            type="number"
            value={correctionThreshold}
            onChange={(e) => setCorrectionThreshold(Number(e.target.value))}
            inputProps={{ min: 0, max: 1, step: 0.1 }}
            size="small"
          />
          <TextField
            label="Max corrections per column"
            type="number"
            value={maxCorrectionsPerColumn}
            onChange={(e) => setMaxCorrectionsPerColumn(Number(e.target.value))}
            inputProps={{ min: 1 }}
            size="small"
          />
        </Box>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!file || loading}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Running...' : 'Run Classification & Correction'}
        </Button>
      </Paper>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {result && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Result
          </Typography>
          <Box component="pre" sx={{ overflow: 'auto', fontSize: 12 }}>
            {JSON.stringify(result, null, 2)}
          </Box>
        </Paper>
      )}
    </Box>
  )
}

export default Correction
