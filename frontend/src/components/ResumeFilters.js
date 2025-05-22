import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { 
  Autocomplete, 
  TextField, 
  Button, 
  Box, 
  Typography, 
  CircularProgress,
  Chip
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import axios from 'axios';
import ResumeList from './ResumeList';

const API_BASE_URL = "http://localhost:8000";

const ResumeFilters = () => {
  const navigate = useNavigate();
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [allSkills, setAllSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filteredResumes, setFilteredResumes] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all available skills from backend
  useEffect(() => {
    const fetchSkills = async () => {
      try {
        setSkillsLoading(true);
        setError(null);
        const response = await axios.get(`${API_BASE_URL}/resumes/skills`);
        
        if (response.data?.skills) {
          // Get unique skills from the mapping
          const uniqueSkills = Array.from(
            new Set(
              Object.values(response.data.skills)
                .flatMap(skills => skills)
            )
          );
          setAllSkills(uniqueSkills);
        } else {
          throw new Error('Unexpected response format');
        }
      } catch (err) {
        console.error('Failed to fetch skills:', err);
        setError(`Failed to load skills: ${err.message}`);
      } finally {
        setSkillsLoading(false);
      }
    };
    fetchSkills();
  }, []);

  // Filter resumes by selected skills
  const handleFilter = async () => {
    if (selectedSkills.length === 0) {
      setFilteredResumes([]);
      navigate('results');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/resumes/filter`, {
        params: { skills: selectedSkills },
        paramsSerializer: { indexes: null }
      });
      
      // Transform the response to match expected frontend format
      const formattedResumes = response.data.map(resume => ({
        id: resume.resume_id,
        filename: `Resume ${resume.resume_id.substring(0, 8)}`, // Shortened ID
        analysis_data: {
          skills: resume.skills,
          email: '', // Will be empty unless you add to backend response
          experience: null // Will be empty unless you add to backend response
        }
      }));
      
      setFilteredResumes(formattedResumes);
      navigate('results');
    } catch (err) {
      console.error('Filter error:', err);
      setFilteredResumes([]);
      navigate('results');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToFilters = () => {
    navigate('');
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* <Typography variant="h4" gutterBottom>
        Resume Skill Filter
      </Typography> */}

      <Routes>
        <Route index element={
          <Box sx={{ 
            maxWidth: 800,
            mx: 'auto',
            p: 3,
            bgcolor: 'background.paper',
            borderRadius: 2,
            boxShadow: 1,
            mb: 4
          }}>
            <Typography variant="h6" gutterBottom>
              Select Skills to Filter Resumes
            </Typography>
            
            {error ? (
              <Box sx={{ p: 3, border: '1px dashed', borderColor: 'error.main', borderRadius: 1 }}>
                <Typography color="error" gutterBottom>
                  Connection Error
                </Typography>
                <Typography variant="body2">{error}</Typography>
              </Box>
            ) : skillsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress sx={{ mr: 2 }} />
                <Typography>Loading skills database...</Typography>
              </Box>
            ) : allSkills.length > 0 ? (
              <>
                <Autocomplete
                  multiple
                  options={allSkills}
                  getOptionLabel={(option) => option}
                  value={selectedSkills}
                  onChange={(_, newValue) => setSelectedSkills(newValue)}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      label="Select skills" 
                      placeholder="Type to search..."
                      helperText="Select skills to find resumes with ALL matching skills"
                      fullWidth
                    />
                  )}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => (
                      <Chip
                        label={option}
                        {...getTagProps({ index })}
                        key={option}
                        color="primary"
                      />
                    ))
                  }
                />
                <Button 
                  variant="contained" 
                  onClick={handleFilter}
                  sx={{ mt: 3 }}
                  fullWidth
                  disabled={loading || selectedSkills.length === 0}
                >
                  {loading ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    'Find Matching Resumes'
                  )}
                </Button>
              </>
            ) : (
              <Typography color="text.secondary">No skills available</Typography>
            )}
          </Box>
        } />

        <Route path="results" element={
          <>
            <Button 
              variant="outlined" 
              onClick={handleBackToFilters}
              sx={{ mb: 3 }}
              startIcon={<ArrowBack />}
            >
              Back to Skill Selection
            </Button>
            <ResumeList 
              resumes={filteredResumes} 
              selectedSkills={selectedSkills}
            />
          </>
        } />
      </Routes>
    </Box>
  );
};

export default ResumeFilters;