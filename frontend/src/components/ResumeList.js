import React from 'react';
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  Chip,
  Paper,
  Divider,
  Avatar
} from '@mui/material';
import CheckCircle from '@mui/icons-material/CheckCircle';

const ResumeList = ({ resumes, selectedSkills }) => {
  if (resumes.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', p: 4 }}>
        <Typography variant="h6" gutterBottom>
          No resumes found with ALL selected skills
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center', mt: 2 }}>
          {selectedSkills.map(skill => (
            <Chip 
              key={skill} 
              label={skill} 
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Try adjusting your skill filters
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom sx={{ mb: 2 }}>
        Found {resumes.length} resumes with ALL skills:
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
          {selectedSkills.map(skill => (
            <Chip 
              key={skill} 
              label={skill} 
              color="primary"
              icon={<CheckCircle fontSize="small" />}
            />
          ))}
        </Box>
      </Typography>
      
      <List sx={{ width: '100%' }}>
        {resumes.map((resume) => (
          <Paper key={resume.id} elevation={2} sx={{ mb: 3, p: 2 }}>
            <ListItem>
              <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                {resume.filename?.charAt(0).toUpperCase() || 'R'}
              </Avatar>
              <ListItemText
                primary={resume.filename || `Resume ${resume.id.substring(0, 8)}`}
                secondary={
                  <>
                    <Typography component="span" variant="body2" color="text.primary">
                      ID: {resume.id}
                    </Typography>
                    {resume.analysis_data?.email && (
                      <>
                        <br />
                        <Typography component="span">
                          {resume.analysis_data.email}
                        </Typography>
                      </>
                    )}
                    {resume.analysis_data?.experience && (
                      <>
                        <br />
                        <Typography component="span">
                          {resume.analysis_data.experience} years experience
                        </Typography>
                      </>
                    )}
                  </>
                }
              />
            </ListItem>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>
              Skills:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {resume.analysis_data?.skills?.map((skill) => (
                <Chip
                  key={skill}
                  label={skill}
                  size="small"
                  color={selectedSkills.includes(skill) ? 'primary' : 'default'}
                  variant={selectedSkills.includes(skill) ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </Paper>
        ))}
      </List>
    </Box>
  );
};

export default ResumeList;