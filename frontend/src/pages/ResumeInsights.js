import React from 'react';
import { Box } from '@mui/material';
import ResumeSearch from '../components/ResumeSearch';
import ResumeAnalysis from '../components/ResumeAnalysis';

export default function ResumeInsights() {
  const [selectedResume, setSelectedResume] = React.useState(null);

  return (
    <Box sx={{ p: 3 }}>
      <ResumeSearch onSelect={setSelectedResume} />
      {selectedResume && (
        <ResumeAnalysis resumeId={selectedResume} />
      )}
    </Box>
  );
}
