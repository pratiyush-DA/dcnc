import { useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Grid,
  Card,
  CardContent,
  Chip,
  Divider,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import DownloadIcon from '@mui/icons-material/Download'
import { classificationApi } from '../services/api'

function Classification() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [hasHeader, setHasHeader] = useState(true)
  const [enableValidation, setEnableValidation] = useState(true)
  const [enableMlClustering, setEnableMlClustering] = useState(true)
  const [enableEnsembleDetection, setEnableEnsembleDetection] = useState(true)
  const [strictMode, setStrictMode] = useState(false)

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
      const data = await classificationApi.classify(file, {
        has_header: hasHeader,
        enable_validation: enableValidation,
        enable_ml_clustering: enableMlClustering,
        enable_ensemble_detection: enableEnsembleDetection,
        strict_mode: strictMode,
      })
      console.log('Classification result:', data) // Debug log
      setResult(data)
    } catch (err: any) {
      console.error('Classification error:', err) // Debug log
      const errorDetail = err.response?.data?.detail
      let errorMessage = 'Classification failed.'
      if (Array.isArray(errorDetail)) {
        errorMessage = errorDetail.map((d: any) => d.msg || d.message).join('. ')
      } else if (typeof errorDetail === 'string') {
        errorMessage = errorDetail
      } else if (err.message) {
        errorMessage = err.message
      }
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Classification
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Upload a CSV file to detect column types and data quality.
      </Typography>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Upload CSV
        </Typography>
        <Button
          variant="outlined"
          component="label"
          startIcon={<CloudUploadIcon />}
          sx={{ mb: 2 }}
        >
          Choose file
          <input type="file" hidden accept=".csv" onChange={handleFileChange} />
        </Button>
        {file && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Selected: {file.name}
          </Typography>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
          <FormControlLabel
            control={<Checkbox checked={hasHeader} onChange={(e) => setHasHeader(e.target.checked)} />}
            label="File has header row"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={enableValidation}
                onChange={(e) => setEnableValidation(e.target.checked)}
              />
            }
            label="Enable validation"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={enableMlClustering}
                onChange={(e) => setEnableMlClustering(e.target.checked)}
              />
            }
            label="Enable ML clustering"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={enableEnsembleDetection}
                onChange={(e) => setEnableEnsembleDetection(e.target.checked)}
              />
            }
            label="Enable ensemble detection"
          />
          <FormControlLabel
            control={
              <Checkbox checked={strictMode} onChange={(e) => setStrictMode(e.target.checked)} />
            }
            label="Strict mode"
          />
        </Box>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!file || loading}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? 'Running...' : 'Run Classification'}
        </Button>
      </Paper>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {result && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <CheckCircleIcon color="success" />
            <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
              Classification Complete
            </Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />
          
          {/* Statistics Cards */}
          {result.statistics && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Statistics
              </Typography>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="primary">
                        {result.statistics.total_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Rows
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="success.main">
                        {result.statistics.good_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Good Rows
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="warning.main">
                        {result.statistics.bad_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Bad Rows
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h4" color="error.main">
                        {result.statistics.reject_rows}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Rejected Rows
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">{result.statistics.columns_processed}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Columns Processed
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="success.main">
                        {result.statistics.total_good_values}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Good Values
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" color="error.main">
                        {result.statistics.total_bad_values}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Bad Values
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          )}

          {/* Job Info */}
          {result.job_id && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Job Information
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                <Chip label={`Job ID: ${result.job_id}`} variant="outlined" />
                {result.metadata?.processing_time && (
                  <Chip
                    label={`Processing Time: ${result.metadata.processing_time.toFixed(2)}s`}
                    variant="outlined"
                  />
                )}
                {result.metadata?.timestamp && (
                  <Chip
                    label={`Completed: ${new Date(result.metadata.timestamp).toLocaleString()}`}
                    variant="outlined"
                  />
                )}
              </Box>
            </Box>
          )}

          {/* Output Files */}
          {result.files && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Output Files
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(result.files).map(([key, path]: [string, any]) => (
                  <Grid item xs={12} sm={6} key={key}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box>
                            <Typography variant="subtitle2" sx={{ textTransform: 'capitalize' }}>
                              {key.replace('_', ' ')}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                              {path}
                            </Typography>
                          </Box>
                          <Button
                            size="small"
                            startIcon={<DownloadIcon />}
                            variant="outlined"
                            onClick={() => {
                              // TODO: Implement file download endpoint
                              alert(`Download functionality for ${key} will be implemented`)
                            }}
                          >
                            Download
                          </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {/* Raw JSON (Collapsible) */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Raw Response
            </Typography>
            <Box
              component="pre"
              sx={{
                overflow: 'auto',
                fontSize: 12,
                p: 2,
                bgcolor: 'grey.100',
                borderRadius: 1,
                maxHeight: 400,
              }}
            >
              {JSON.stringify(result, null, 2)}
            </Box>
          </Box>
        </Paper>
      )}
    </Box>
  )
}

export default Classification
