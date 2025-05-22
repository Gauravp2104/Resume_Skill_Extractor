import React, { useState, useCallback, useEffect } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Tooltip,
  Typography,
  Divider,
  Box,
  CircularProgress,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Brightness4,
  Brightness7,
  CloudUpload,
  Info,
  Menu,
  Home,
  Close,
  Delete,
  Refresh,
  Description,
  Download
} from '@mui/icons-material';
import { createTheme } from '@mui/material/styles';
import { Routes, Route, Link } from 'react-router-dom';
import ResumeFilters from './components/ResumeFilters';
import ResumeList from './components/ResumeList';
import ResumeInsights from './pages/ResumeInsights'; 
// import SkillGroups from './pages/SkillGroups'; 
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './App.css';

const API_BASE_URL = "http://localhost:8000";  

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Light Theme
const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#3f51b5' },
    secondary: { main: '#f50057' },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff'
    },
    text: {
      primary: '#212529',
      secondary: '#495057'
    },
    contrastThreshold: 4.5,
  },
  typography: {
    fontFamily: "'Poppins', sans-serif",
    h1: {
      fontWeight: 700,
      fontSize: '3.5rem',
      letterSpacing: '-0.015em',
      background: 'linear-gradient(45deg, #3f51b5 30%, #2196F3 90%)',
      backgroundClip: 'text',
      WebkitBackgroundClip: 'text',
      color: 'transparent',
      WebkitTextFillColor: 'transparent',
      textSizeAdjust: '100%',
    },
    allVariants: {
      textSizeAdjust: '100%',
    }
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: {
          textSizeAdjust: '100%',
        },
      },
    },
  },
});

// Dark Theme
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#7986cb' },
    secondary: { main: '#ff4081' },
    background: {
      default: '#121212',
      paper: '#1e1e1e'
    },
    text: {
      primary: '#f8f9fa',
      secondary: '#dee2e6'
    },
    contrastThreshold: 4.5,
  },
  typography: {
    ...lightTheme.typography,
    h1: {
      ...lightTheme.typography.h1,
      background: 'linear-gradient(45deg, #7986cb 30%, #64b5f6 90%)',
    }
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: {
          textSizeAdjust: '100%',
        },
      },
    },
  },
});

// const theme = createTheme({
//   palette: {
//     primary: {
//       main: '#1976d2',
//     },
//     secondary: {
//       main: '#dc004e',
//     },
//     background: {
//       default: '#f5f5f5',
//     },
//   },
//   components: {
//     MuiPaper: {
//       styleOverrides: {
//         root: {
//           transition: 'all 0.3s ease',
//           '&:hover': {
//             transform: 'translateY(-2px)',
//             boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
//           }
//         }
//       }
//     }
//   }
// });

function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resumes, setResumes] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [filteredResumes, setFilteredResumes] = useState([]);

  const showSnackbar = useCallback((message, severity) => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const fetchResumes = useCallback(async () => {
    try {
      const { data } = await apiClient.get(`${API_BASE_URL}/resumes`);
      setResumes(data);
    } catch (error) {
      showSnackbar('Failed to load resumes', 'error');
    }
  }, [showSnackbar]);

  useEffect(() => {
    if (sidebarOpen) {
      fetchResumes();
    }
  }, [sidebarOpen, fetchResumes]);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    
    const file = acceptedFiles[0];
    if (file.type !== 'application/pdf' || !file.name.toLowerCase().endsWith('.pdf')) {
      showSnackbar('Only PDF files are allowed', 'error');
      return;
    }

    setUploading(true);
    showSnackbar('Uploading resume...', 'info');

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await apiClient.post(`${API_BASE_URL}/upload`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
        }
      });
      
      showSnackbar('Resume uploaded successfully!', 'success');
      fetchResumes();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 
                     error.response?.data?.message || 
                     'Upload failed';
      showSnackbar(errorMsg, 'error');
    } finally {
      setUploading(false);
    }
  }, [showSnackbar, fetchResumes]);

  const deleteResume = async (id) => {
    try {
      await apiClient.delete(`${API_BASE_URL}/resumes/${id}`);
      setResumes(prev => prev.filter(r => r.id !== id));
      showSnackbar('Resume deleted', 'success');
    } catch (error) {
      showSnackbar('Delete failed', 'error');
    }
  };

  const downloadResume = (id, filename) => {
    window.open(`${API_BASE_URL}/resumes/${id}/download`, '_blank');
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxFiles: 1,
    multiple: false,
    disabled: uploading
  });

  const Sidebar = ({ open, onClose }) => (
    <Drawer
      anchor="left"
      open={open}
      onClose={onClose}
      variant="temporary"
      ModalProps={{ keepMounted: true }}
      sx={{
        zIndex: 1302,
        '& .MuiDrawer-paper': {
          width: 320,
          boxShadow: 6,
          backgroundColor: darkMode ? '#1e1e1e' : '#ffffff',
        }
      }}
    >
      <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Resume Tools</Typography>
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Box>
        <Divider />
        
        <List>
          <ListItemButton 
            component={Link} 
            to="/"
            onClick={onClose}
            sx={{ borderRadius: 1, mb: 0.5 }}
          >
            <ListItemIcon><Home /></ListItemIcon>
            <ListItemText primary="Home" />
          </ListItemButton>
          
          <ListItemButton 
            component={Link} 
            to="/resume-insights"
            onClick={onClose}
            sx={{ borderRadius: 1, mb: 0.5 }}
          >
            {/* <ListItemIcon><ResumeInsights /></ListItemIcon> */}
            <ListItemText primary="Resume Insights" />
          </ListItemButton>
          
          <ListItemButton 
            component={Link} 
            to="/skill-groups"
            onClick={onClose}
            sx={{ borderRadius: 1, mb: 0.5 }}
          >
            {/* <ListItemIcon><Category /></ListItemIcon> */}
            <ListItemText primary="Skill Groups" />
          </ListItemButton>
        </List>
        
        <Divider sx={{ my: 2 }} />
        
        <Typography variant="subtitle1" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
          <Description sx={{ mr: 1 }} /> My Resumes
          <IconButton size="small" onClick={fetchResumes} sx={{ ml: 'auto' }}>
            <Refresh fontSize="small" />
          </IconButton>
        </Typography>
        
        <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
          {resumes.length === 0 ? (
            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              No resumes uploaded yet
            </Typography>
          ) : (
            <List dense>
              {resumes.map((resume) => (
                <ListItem
                  key={resume.id}
                  secondaryAction={
                    <>
                      <Tooltip title="Download">
                        <IconButton 
                          edge="end" 
                          onClick={() => downloadResume(resume.id, resume.filename)}
                          sx={{ mr: 1 }}
                        >
                          <Download fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton edge="end" onClick={() => deleteResume(resume.id)}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </>
                  }
                  sx={{
                    '&:hover': { bgcolor: 'action.hover' },
                    borderRadius: 1,
                    mb: 0.5
                  }}
                >
                  <ListItemText
                    primary={resume.filename}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondary={new Date(resume.created_at).toLocaleString()}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ p: 1 }}>
          <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Info sx={{ mr: 1 }} /> About
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Extract skills from resumes with AI. Filter candidates by expertise.
          </Typography>
        </Box>
      </Box>
    </Drawer>
  );

  return (
    <ThemeProvider theme={darkMode ? darkTheme : lightTheme}>
      <CssBaseline />
      <Box sx={{ display: 'flex' }}>
        {!sidebarOpen && (
          <Tooltip title="Open Sidebar">
            <IconButton
              color="inherit"
              onClick={() => setSidebarOpen(true)}
              sx={{
                position: 'fixed',
                top: 24,
                left: 24,
                zIndex: 1303,
              }}
            >
              <Menu />
            </IconButton>
          </Tooltip>
        )}

        <Tooltip title={darkMode ? 'Light mode' : 'Dark mode'}>
          <IconButton
            color="inherit"
            onClick={() => setDarkMode(!darkMode)}
            sx={{
              position: 'fixed',
              top: 24,
              right: 24,
              zIndex: 1303
            }}
          >
            {darkMode ? <Brightness7 color="primary" /> : <Brightness4 />}
          </IconButton>
        </Tooltip>

        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            ml: { sm: `${sidebarOpen ? 320 : 0}px` },
            transition: 'margin 225ms cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          <Routes>
            <Route path="/" element={
              <Box sx={{ 
                maxWidth: 800,
                mx: 'auto',
                textAlign: 'center',
                pt: 10
              }}>
                <Typography variant="h1" gutterBottom>
                  Resume Skill Extractor
                </Typography>
                {/* Your existing upload box */}
                <Box sx={{ mb: 6 }}>
                  <Box 
                    {...getRootProps()}
                    sx={{
                      border: '2px dashed',
                      borderColor: isDragActive ? 'primary.main' : 'text.secondary',
                      borderRadius: 2,
                      p: 6,
                      textAlign: 'center',
                      cursor: 'pointer',
                      bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        borderColor: 'primary.main',
                        bgcolor: 'action.hover'
                      }
                    }}
                  >
                    <input {...getInputProps()} />
                    {uploading ? (
                      <>
                        <CircularProgress size={60} thickness={4} sx={{ mb: 2 }} />
                        <Typography>Processing your resume...</Typography>
                      </>
                    ) : (
                      <>
                        <CloudUpload sx={{ fontSize: 60, mb: 2, color: 'primary.main' }} />
                        <Typography variant="h6" gutterBottom>
                          {isDragActive ? 'Drop your resume here' : 'Drag & drop PDF resume'}
                        </Typography>
                        <Typography color="text.secondary">
                          or click to browse files
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
                          Only PDF files accepted (Max size: 10MB)
                        </Typography>
                      </>
                    )}
                  </Box>
                </Box>
              </Box>
            } />
            
            <Route path="/resume-insights" element={<ResumeInsights />} />
            <Route path="/skill-groups/*" element={<ResumeFilters />} />
          </Routes>
        </Box>

        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert severity={snackbar.severity}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;