import { Box, Typography, Paper, Divider } from '@mui/material'
import SettingsIcon from '@mui/icons-material/Settings'

function Settings() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Configure application and API settings.
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          API
        </Typography>
        <Typography variant="body2" color="text.secondary">
          API base URL is configured via <code>VITE_API_BASE_URL</code> in your environment (default:
          http://localhost:8000/api/v1).
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="h6" gutterBottom>
          Account
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage your account and tenant settings. Additional options will appear when the API
          supports them.
        </Typography>
      </Paper>
    </Box>
  )
}

export default Settings
