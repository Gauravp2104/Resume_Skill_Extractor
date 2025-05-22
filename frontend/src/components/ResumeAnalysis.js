import React from 'react';
import Grid from '@mui/material/Grid';
import { 
  Box, Typography, Chip, Divider, Paper, Button, Stack, Avatar,
  List, ListItem, ListItemText, ListItemAvatar, LinearProgress,
  Snackbar, Alert
} from '@mui/material';
import { 
  Email, Phone, Work, School, Code, LocationOn, 
  CalendarToday, Person, Star, Business, 
  CastForEducation, HourglassEmpty
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import apiClient from './apiClient';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  borderRadius: '16px',
  boxShadow: theme.shadows[10],
  background: 'linear-gradient(145deg, #ffffff, #f5f5f5)',
  minHeight: '80vh'
}));

const ExperienceCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${theme.palette.primary.main}`,
  transition: 'transform 0.2s',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4]
  }
}));

export default function ResumeAnalysis({ resumeId }) {
  const [analysis, setAnalysis] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [timeoutReached, setTimeoutReached] = React.useState(false);

  React.useEffect(() => {
    if (!resumeId) return;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      setTimeoutReached(true);
    }, 10000); 

    const loadData = async () => {
      setLoading(true);
      setError(null);
      setTimeoutReached(false);
      
      try {
        const { data } = await apiClient.get(`resumes/${resumeId}/analyze`, {
          signal: controller.signal,
          timeout: 10000
        });
        setAnalysis(data);
      } catch (err) {
        // Check if the error is from cancellation
        if (err.code === 'ERR_CANCELED' || err.name === 'CanceledError') {
          console.log('Request was intentionally canceled');
          return; // Exit early if canceled
        }
      
        // Handle other errors
        if (err.response) {
          // Server responded with error status (4xx, 5xx)
          setError(err.response.data?.detail || 
                  err.response.data?.message || 
                  'Analysis failed');
        } else {
          // Other errors
          setError(err.message || 'Failed to analyze resume');
        }
      } finally {
        clearTimeout(timeoutId);
        setLoading(false);
      }
    };
    
    loadData();
    return () => {
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [resumeId]);

  if (loading) {
    return (
      <StyledPaper sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <HourglassEmpty sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Analyzing Resume...
        </Typography>
        <LinearProgress 
          sx={{ width: '80%', height: 8, borderRadius: 4, mt: 2 }}
        />
        {timeoutReached && (
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            This is taking longer than expected. Please wait...
          </Typography>
        )}
      </StyledPaper>
    );
  }

  if (error) {
    return (
      <StyledPaper sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="h5" color="error" gutterBottom>
          Analysis Failed
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
          {error}
        </Typography>
        <Button 
          variant="contained" 
          onClick={() => window.location.reload()}
          sx={{ mt: 2 }}
        >
          Try Again
        </Button>
      </StyledPaper>
    );
  }

  if (!analysis) {
    return null; // Should never reach here as we start loading immediately
  }

  return (
    <StyledPaper>
        {/* Header Section */}
        <Box sx={{ 
            display: 'flex', 
            flexDirection: { xs: 'column', md: 'row' },
            alignItems: 'center',
            mb: 4,
            gap: 4,
            color: 'text.secondary' // Ensures text color adapts to theme
        }}>
            <Avatar sx={{ 
                width: 120, 
                height: 120,
                fontSize: '3rem',
                bgcolor: 'primary.main',
                boxShadow: 3,
                color: theme => theme.palette.getContrastText(theme.palette.primary.main) // Better contrast
            }}>
                {analysis.metadata.name?.charAt(0) || <Person fontSize="large" />}
            </Avatar>
    
            <Box sx={{ flexGrow: 1 }}>
                <Typography 
                    variant="h3" 
                    component="h1" 
                    sx={{ 
                        fontWeight: 700,
                        color: 'text.primary', // Explicitly use theme text color
                        textShadow: theme => `0 0 8px ${theme.palette.mode === 'dark' ? 'rgba(9, 1, 1, 0.3)' : 'rgba(0,0,0,0.1)'}` // Subtle shadow for better visibility
                    }}
                >
                    {analysis.metadata.name}
                </Typography>
                
          <Stack direction="row" spacing={2} sx={{ mt: 2, flexWrap: 'wrap' }}>
            {analysis.metadata.email && (
              <Chip 
                icon={<Email />}
                label={analysis.metadata.email}
                onClick={() => window.open(`mailto:${analysis.metadata.email}`)}
                sx={{ 
                  px: 2,
                  bgcolor: 'primary.light',
                  color: 'primary.contrastText',
                  '&:hover': { bgcolor: 'primary.dark' }
                }}
              />
            )}
            
            {analysis.metadata.phone && (
              <Chip 
                icon={<Phone />}
                label={analysis.metadata.phone}
                onClick={() => window.open(`tel:${analysis.metadata.phone}`)}
                sx={{
                  px: 2,
                  bgcolor: 'secondary.light',
                  color: 'secondary.contrastText',
                  '&:hover': { bgcolor: 'secondary.dark' }
                }}
              />
            )}
          </Stack>
        </Box>
        
        {/* <Stack direction="row" spacing={2}>
          <Button 
            variant="contained" 
            startIcon={<Download />}
            size="large"
            sx={{ borderRadius: '12px' }}
          >
            Download
          </Button>
          <Button 
            variant="outlined" 
            startIcon={<Share />}
            size="large"
            sx={{ borderRadius: '12px' }}
          >
            Share
          </Button>
        </Stack> */}
      </Box>

      <Divider sx={{ my: 4, borderWidth: 2 }} />

      {/* Skills Section */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h4" gutterBottom sx={{ 
          display: 'flex', 
          alignItems: 'center',
          mb: 3,
          color: 'primary.main'
        }}>
          <Code sx={{ mr: 2, fontSize: '2rem' }} />
          Professional Skills
        </Typography>
        
        <Box sx={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: 2,
          '& .MuiChip-root': {
            fontSize: '1rem',
            padding: '8px 16px',
            borderRadius: '8px',
            transition: 'all 0.3s',
            '&:hover': {
              transform: 'scale(1.05)'
            }
          }
        }}>
          {analysis.skills.map((skill, index) => (
            <Chip
              key={index}
              label={skill}
              color={index % 3 === 0 ? 'primary' : index % 3 === 1 ? 'secondary' : 'info'}
              icon={<Star />}
            />
          ))}
        </Box>
      </Box>

      {/* Experience Section */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h4" gutterBottom sx={{ 
          display: 'flex', 
          alignItems: 'center',
          mb: 3,
          color: 'primary.main'
        }}>
          <Work sx={{ mr: 2, fontSize: '2rem' }} />
          Professional Experience
        </Typography>
        
        {analysis.experience.map((exp, index) => (
          <ExperienceCard key={index}>
            <Box sx={{ 
              display: 'flex',
              flexDirection: { xs: 'column', md: 'row' },
              justifyContent: 'space-between',
              mb: 2
            }}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 600 }}>
                  {exp.role || 'Professional Role'}
                </Typography>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    display: 'flex',
                    alignItems: 'center',
                    mt: 1,
                    color: 'secondary.main'
                  }}
                >
                  <Business sx={{ mr: 1 }} />
                  {exp.company || 'Company Name'}
                </Typography>
              </Box>
              
              <Stack 
                direction="row" 
                spacing={2} 
                sx={{ 
                  mt: { xs: 2, md: 0 },
                  alignItems: 'center'
                }}
              >
                {exp.location && (
                  <Chip 
                    icon={<LocationOn />}
                    label={exp.location}
                    variant="outlined"
                    sx={{ bgcolor: 'background.paper' }}
                  />
                )}
                {exp.duration && (
                  <Chip 
                    icon={<CalendarToday />}
                    label={exp.duration}
                    variant="outlined"
                    sx={{ bgcolor: 'background.paper' }}
                  />
                )}
              </Stack>
            </Box>
            
            {exp.description && (
              <Typography sx={{ mt: 2, whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                {exp.description}
              </Typography>
            )}
          </ExperienceCard>
        ))}
      </Box>

      {/* Education Section */}
      {analysis.education?.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" gutterBottom sx={{ 
            display: 'flex', 
            alignItems: 'center',
            mb: 3,
            color: 'primary.main'
          }}>
            <CastForEducation sx={{ mr: 2, fontSize: '2rem' }} />
            Education Background
          </Typography>
          
          <List sx={{ 
            bgcolor: 'background.paper',
            borderRadius: '12px',
            p: 2,
            boxShadow: 2
          }}>
            {analysis.education.map((edu, index) => (
              <ListItem key={index} sx={{ py: 2 }}>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: 'primary.light' }}>
                    <School sx={{ color: 'white' }} />
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {edu.degree || 'Degree'}
                    </Typography>
                  }
                  secondary={
                    <>
                      <Typography component="span" display="block" sx={{ mt: 0.5 }}>
                        {edu.institution || 'Institution'}
                      </Typography>
                      <Typography component="span" variant="body2" color="text.secondary">
                        {edu.year || 'Year'}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    
            {analysis.projects?.length > 0 && (
        <Box sx={{ mb: 4 }}>
            <Typography variant="h4" gutterBottom sx={{ 
            display: 'flex', 
            alignItems: 'center',
            mb: 3,
            color: 'primary.main'
            }}>
            <Code sx={{ mr: 2, fontSize: '2rem' }} />
            Projects and Extra Curriculars 
            </Typography>
            
            <Grid container spacing={3}>
            {analysis.projects.map((project, index) => (
                <Grid item xs={12} md={6} key={index}>
                <ExperienceCard>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    {project.name}
                    </Typography>
                    
                    {project.technologies && (
                    <Box sx={{ mt: 1, mb: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                        Technologies:
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        {project.technologies.split(',').map((tech, i) => (
                            <Chip 
                            key={i}
                            label={tech.trim()}
                            size="small"
                            color="info"
                            />
                        ))}
                        </Box>
                    </Box>
                    )}
                    
                    {project.description && (
                    <Typography sx={{ mt: 1, whiteSpace: 'pre-line' }}>
                        {project.description}
                    </Typography>
                    )}
                </ExperienceCard>
                </Grid>
            ))}
            </Grid>
        </Box>
        )}
      {/* Status Snackbar */}
      <Snackbar
        open={loading}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="info" icon={<HourglassEmpty />}>
          Analyzing resume - this may take a moment...
        </Alert>
      </Snackbar>
    </StyledPaper>
  );
}