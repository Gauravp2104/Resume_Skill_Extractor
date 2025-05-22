import React, { useState, useEffect } from 'react';
import { 
  Autocomplete,
  TextField,
  CircularProgress,
  Paper,
  Typography,
  Stack,
  Chip,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box
} from '@mui/material';
import { Search, Description, History } from '@mui/icons-material';
import apiClient from './apiClient';

export default function ResumeSearch({ onSelect }) {
  const [inputValue, setInputValue] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('recentResumeSearches');
    if (saved) setRecentSearches(JSON.parse(saved));
  }, []);

  useEffect(() => {
    if (inputValue.length < 2) {
      setOptions([]);
      return;
    }
  
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        console.log('Searching for:', inputValue);
        
        const response = await apiClient.get('/resumes/search', {
          params: {
            query: inputValue
          }
        });
        
        console.log('Search results:', response.data);
        
        const formatted = response.data.map(item => ({
          ...item,
          label: item.filename || 'Untitled Resume',
          subtext: new Date(item.created_at).toLocaleDateString()
        }));
        
        setOptions(formatted);
      } catch (error) {
        console.error('Search failed:', error);
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  
    return () => clearTimeout(timer);
  }, [inputValue]); 
  
  const handleSelect = (event, value) => {
    if (!value?.id) return;
    
    // Update recent searches
    const newRecent = [
      value,
      ...recentSearches.filter(r => r.id !== value.id)
    ].slice(0, 5);
    
    setRecentSearches(newRecent);
    localStorage.setItem('recentResumeSearches', JSON.stringify(newRecent));
    
    onSelect(value.id);
  };

  return (
    <Paper elevation={3} sx={{ 
        p: 3,
        my: 4,       
        mx: 'auto',  
        maxWidth: '800px', 
      }}>
      <Typography variant="h6" gutterBottom>
        Search Resumes
      </Typography>
      
      <Autocomplete
        freeSolo
        options={options}
        getOptionLabel={(option) => 
          typeof option === 'string' ? option : option.label
        }
        inputValue={inputValue}
        onInputChange={(event, newInputValue) => {
          setInputValue(newInputValue);
        }}
        onChange={handleSelect}
        loading={loading}
        loadingText="Searching..."
        noOptionsText={
          inputValue.length < 2 
            ? 'Type at least 2 characters to search' 
            : 'No matching resumes found'
        }
        renderInput={(params) => (
          <TextField
            {...params}
            label="Search by name or filename"
            variant="outlined"
            fullWidth
            InputProps={{
              ...params.InputProps,
              startAdornment: <Search sx={{ mr: 1 }} />,
              endAdornment: (
                <>
                  {loading ? <CircularProgress size={20} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
        renderOption={(props, option) => (
          <ListItem {...props} key={option.id}>
            <ListItemIcon>
              <Description color="primary" />
            </ListItemIcon>
            <ListItemText 
              primary={option.label} 
              secondary={`Uploaded: ${option.subtext}`}
            />
          </ListItem>
        )}
      />

      {recentSearches.length > 0 && inputValue.length < 2 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            <History fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
            Recent searches
          </Typography>
          <Stack spacing={1}>
            {recentSearches.map((resume) => (
              <Chip
                key={resume.id}
                label={resume.label}
                onClick={() => handleSelect(null, resume)}
                onDelete={() => {
                  const updated = recentSearches.filter(r => r.id !== resume.id);
                  setRecentSearches(updated);
                  localStorage.setItem('recentResumeSearches', JSON.stringify(updated));
                }}
                sx={{ mr: 1, mb: 1 }}
              />
            ))}
          </Stack>
        </Box>
      )}
    </Paper>
  );
}