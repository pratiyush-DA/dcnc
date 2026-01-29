import { Box, Typography, Paper } from '@mui/material'
import HistoryIcon from '@mui/icons-material/History'

function Jobs() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Jobs
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        View history of classification and correction jobs.
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <HistoryIcon sx={{ fontSize: 64, color: 'action.disabled', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Job history
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Run a classification or correction job from the Classification or Correction page. Job
          history and download links will appear here when the API supports job listing.
        </Typography>
      </Paper>
    </Box>
  )
}

export default Jobs
