import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CacheStats.css';

const API_BASE_URL = 'http://localhost:8000/api';

function CacheStats({ refreshTrigger }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stats`);
      setStats(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching stats:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchStats();
    }
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="cache-stats-card">
        <h2>📊 Cache Statistics</h2>
        <div className="loading">Loading stats...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="cache-stats-card">
        <h2>📊 Cache Statistics</h2>
        <div className="no-stats">No statistics available</div>
      </div>
    );
  }

  const hitRate = stats.hit_rate || 0;

  return (
    <div className="cache-stats-card">
      <h2>📊 Cache Statistics</h2>

      <div className="stat-item">
        <div className="stat-label">Total Queries</div>
        <div className="stat-value">{stats.total_queries || 0}</div>
      </div>

      <div className="stat-item">
        <div className="stat-label">Cache Hits</div>
        <div className="stat-value cache-hits">{stats.cache_hits || 0}</div>
      </div>

      <div className="stat-item">
        <div className="stat-label">Cache Misses</div>
        <div className="stat-value cache-misses">{stats.cache_misses || 0}</div>
      </div>

      <div className="stat-item highlight">
        <div className="stat-label">Hit Rate</div>
        <div className="stat-value hit-rate">{hitRate.toFixed(1)}%</div>
      </div>

      <div className="hit-rate-bar">
        <div
          className="hit-rate-fill"
          style={{ width: `${hitRate}%` }}
        ></div>
      </div>

      <div className="stat-item">
        <div className="stat-label">Cached Queries</div>
        <div className="stat-value">{stats.total_cached_queries || 0}</div>
      </div>

    </div>
  );
}

export default CacheStats;
