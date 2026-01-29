import { Box, Typography, Paper, Grid, Card, CardContent } from '@mui/material'
import DashboardIcon from '@mui/icons-material/Dashboard'
import AssessmentIcon from '@mui/icons-material/Assessment'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'

function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Welcome to the DCNC Data Quality Platform. Use the sidebar to run classification or correction.
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <AssessmentIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6">Classification</Typography>
              <Typography variant="body2" color="text.secondary">
                Upload a CSV to detect column types and data quality.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <AutoFixHighIcon sx={{ fontSize: 48, color: 'secondary.main', mb: 1 }} />
              <Typography variant="h6">Correction</Typography>
              <Typography variant="body2" color="text.secondary">
                Upload a CSV to classify and correct bad data in one step.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <DashboardIcon sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
              <Typography variant="h6">Jobs</Typography>
              <Typography variant="body2" color="text.secondary">
                View history of classification and correction jobs.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Paper sx={{ mt: 3, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Quick Start
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Go to <strong>Classification</strong> to analyze a file, or <strong>Correction</strong> to
          classify and fix data in one run. Results and reports are available after each job.
        </Typography>
      </Paper>
    </Box>
  )
}

export default Dashboard
