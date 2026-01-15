import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import CacheStats from './components/CacheStats';
import './App.css';

function App() {
  const [currentFileId, setCurrentFileId] = useState(null);
  const [currentFilename, setCurrentFilename] = useState('');
  const [refreshStats, setRefreshStats] = useState(0);

  const handleFileUploaded = (fileId, filename) => {
    setCurrentFileId(fileId);
    setCurrentFilename(filename);
  };

  const handleQueryComplete = () => {
    // Trigger stats refresh
    setRefreshStats(prev => prev + 1);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 Semantic Query Cache POC</h1>
        <p>Document Q&A with Intelligent Caching</p>
      </header>

      <div className="container">
        <div className="main-content">
          <FileUpload onFileUploaded={handleFileUploaded} />

          {currentFileId ? (
            <ChatInterface
              fileId={currentFileId}
              filename={currentFilename}
              onQueryComplete={handleQueryComplete}
            />
          ) : (
            <div className="chat-placeholder">
              <div className="placeholder-content">
                <h2>💬 Chat Interface</h2>
                <p>Upload a document above to start asking questions</p>
                <div className="placeholder-icon">📄</div>
              </div>
            </div>
          )}
        </div>

        <div className="sidebar">
          <CacheStats refreshTrigger={refreshStats} />
        </div>
      </div>
    </div>
  );
}

export default App;
