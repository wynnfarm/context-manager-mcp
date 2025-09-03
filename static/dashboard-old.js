import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Chart from 'chart.js/auto';

// Custom hooks
const useWebSocket = (url, onMessage) => {
  const [status, setStatus] = useState({ connected: false, text: 'Connecting...' });
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 1000;

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket(url);
      
      wsRef.current.onopen = () => {
        setStatus({ connected: true, text: 'Connected' });
        reconnectAttemptsRef.current = 0;
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
      };
      
      wsRef.current.onclose = () => {
        setStatus({ connected: false, text: 'Disconnected' });
        attemptReconnect();
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatus({ connected: false, text: 'Error' });
      };
    } catch (error) {
      console.error('Failed to setup WebSocket:', error);
      setStatus({ connected: false, text: 'Failed to connect' });
    }
  }, [url, onMessage]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current < maxReconnectAttempts) {
      reconnectAttemptsRef.current++;
      setStatus({ connected: false, text: `Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})` });
      
      setTimeout(() => {
        connect();
      }, reconnectDelay * reconnectAttemptsRef.current);
    } else {
      setStatus({ connected: false, text: 'Connection failed' });
    }
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return status;
};

const useChart = (canvasRef, chartConfig) => {
  const chartRef = useRef(null);

  useEffect(() => {
    if (canvasRef.current && chartConfig) {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
      
      chartRef.current = new Chart(canvasRef.current, chartConfig);
    }

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [canvasRef, chartConfig]);

  return chartRef.current;
};

// Utility functions
const getCompletionColor = (completion) => {
  if (completion >= 80) return '#10b981';
  if (completion >= 50) return '#f59e0b';
  return '#ef4444';
};

const getHealthColor = (health) => {
  if (health >= 80) return '#10b981';
  if (health >= 60) return '#f59e0b';
  return '#ef4444';
};

const getHealthLabel = (health) => {
  if (health >= 80) return 'Excellent';
  if (health >= 60) return 'Good';
  return 'Needs Work';
};

// Components
const LoadingScreen = () => (
  <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Loading analytics data...</p>
    </div>
  </div>
);

const ErrorScreen = ({ message, onRetry }) => (
  <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
    <div className="text-center">
      <div className="text-red-500 text-6xl mb-4">⚠️</div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Dashboard</h2>
      <p className="text-gray-600 mb-4">{message}</p>
      <button 
        onClick={onRetry}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
      >
        Retry
      </button>
    </div>
  </div>
);

const Navigation = () => (
  <nav className="bg-gray-800 text-white">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center py-3">
        <div className="flex items-center space-x-8">
          <a
            href="http://localhost:8000/dashboard"
            className="flex items-center text-white hover:text-blue-300 transition-colors"
          >
            <i className="fas fa-chart-line text-blue-400 mr-2"></i>
            <span className="font-semibold">Context Manager</span>
          </a>
          <a
            href="http://localhost:8002/"
            className="flex items-center text-gray-300 hover:text-blue-300 transition-colors"
          >
            <i className="fas fa-user-tie text-gray-400 mr-2"></i>
            <span>Persona Manager</span>
          </a>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-400">Analytics Dashboard</span>
        </div>
      </div>
    </div>
  </nav>
);

const Header = ({ realtimeStatus, lastUpdated, onRefresh, onExport, onGenerateReport }) => (
  <header className="bg-white shadow-sm border-b">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center py-4">
        <div className="flex items-center">
          <i className="fas fa-chart-line text-blue-600 text-2xl mr-3"></i>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Context Manager Analytics</h1>
            <div className="flex items-center mt-1">
              <div className="flex items-center">
                <div 
                  className={`w-2 h-2 rounded-full mr-2 ${
                    realtimeStatus.connected 
                      ? 'bg-green-500 animate-pulse' 
                      : 'bg-red-500'
                  }`}
                ></div>
                <span className="text-sm text-gray-500">{realtimeStatus.text}</span>
              </div>
              <div className="ml-4 text-xs text-gray-400">Last update: {lastUpdated}</div>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onExport('projects')}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center"
              title="Export Projects"
            >
              <i className="fas fa-download mr-2"></i>
              Export
            </button>
            <button
              onClick={() => onExport('analytics')}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center"
              title="Export Analytics"
            >
              <i className="fas fa-chart-bar mr-2"></i>
              Analytics
            </button>
            <button
              onClick={onGenerateReport}
              className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 flex items-center"
              title="Generate Report"
            >
              <i className="fas fa-file-alt mr-2"></i>
              Report
            </button>
            <button
              onClick={onRefresh}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center"
            >
              <i className="fas fa-sync-alt mr-2"></i>
              Refresh
            </button>
          </div>
          <p className="text-sm text-gray-500">Last updated: {lastUpdated}</p>
        </div>
      </div>
    </div>
  </header>
);

const SearchAndFilter = ({ onSearch, onFilter, onAdvancedSearch }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
    <div className="flex flex-col md:flex-row gap-4">
      <div className="flex-1">
        <div className="relative">
          <input
            type="text"
            placeholder="Search projects, features, or issues..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            onChange={(e) => onSearch(e.target.value)}
          />
          <i className="fas fa-search absolute left-3 top-3 text-gray-400"></i>
        </div>
      </div>
      <div className="flex gap-2">
        <select
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          onChange={(e) => onFilter('status', e.target.value)}
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="paused">Paused</option>
        </select>
        <select
          className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          onChange={(e) => onFilter('priority', e.target.value)}
        >
          <option value="">All Priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <button
          onClick={onAdvancedSearch}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center"
        >
          <i className="fas fa-filter mr-2"></i>
          Advanced
        </button>
      </div>
    </div>
  </div>
);

const ExpandableCard = ({ title, value, icon, iconBg, iconColor, details, onToggle, expanded, children }) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-3xl font-bold text-gray-900">{value}</p>
      </div>
      <div className={`p-3 rounded-full`} style={{ backgroundColor: iconBg }}>
        <i className={`${icon} text-xl`} style={{ color: iconColor }}></i>
      </div>
    </div>
    <div className="mt-4">
      <button
        className="w-full text-left text-sm flex items-center justify-between hover:bg-blue-50 p-2 rounded transition-colors"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <span style={{ color: iconColor }}>View Details</span>
        <i className={`fas fa-chevron-down transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}></i>
      </button>
      <div className={`transition-all duration-300 overflow-hidden ${expanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="mt-4 pt-4 border-t border-gray-200">
          {children}
        </div>
      </div>
    </div>
  </div>
);

const OverviewCards = ({ metrics }) => {
  const [expandedCards, setExpandedCards] = useState({});

  const toggleCard = (cardId) => {
    setExpandedCards(prev => ({
      ...prev,
      [cardId]: !prev[cardId]
    }));
  };

  const cards = [
    {
      id: 'projects',
      title: 'Total Projects',
      value: metrics.total_projects,
      icon: 'fas fa-folder',
      iconBg: '#dbeafe',
      iconColor: '#2563eb',
      details: [
        { label: 'Active', value: metrics.total_projects - metrics.projects_with_issues },
        { label: 'Completed', value: Math.round(metrics.total_projects * (metrics.average_completion / 100)) },
        { label: 'With Goals', value: metrics.projects_with_goals }
      ]
    },
    {
      id: 'completion',
      title: 'Avg Completion',
      value: `${metrics.average_completion}%`,
      icon: 'fas fa-check-circle',
      iconBg: '#dcfce7',
      iconColor: '#16a34a',
      details: [
        { label: 'High Progress', value: Math.round(metrics.total_projects * 0.3) },
        { label: 'Needs Attention', value: Math.round(metrics.total_projects * 0.4) },
        { label: 'Stalled', value: Math.round(metrics.total_projects * 0.3) }
      ]
    },
    {
      id: 'health',
      title: 'Avg Health',
      value: `${metrics.average_health}%`,
      icon: 'fas fa-heartbeat',
      iconBg: '#fef3c7',
      iconColor: '#d97706',
      details: [
        { label: 'Excellent', value: Math.round(metrics.total_projects * 0.4) },
        { label: 'Good', value: Math.round(metrics.total_projects * 0.4) },
        { label: 'Needs Work', value: Math.round(metrics.total_projects * 0.2) }
      ]
    },
    {
      id: 'features',
      title: 'Total Features',
      value: metrics.total_features,
      icon: 'fas fa-star',
      iconBg: '#f3e8ff',
      iconColor: '#9333ea',
      details: [
        { label: 'Completed', value: Math.round(metrics.total_features * 0.6) },
        { label: 'In Progress', value: Math.round(metrics.total_features * 0.3) },
        { label: 'Planned', value: Math.round(metrics.total_features * 0.1) }
      ]
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {cards.map(card => (
        <ExpandableCard
          key={card.id}
          title={card.title}
          value={card.value}
          icon={card.icon}
          iconBg={card.iconBg}
          iconColor={card.iconColor}
          expanded={expandedCards[card.id]}
          onToggle={() => toggleCard(card.id)}
        >
          <div className="space-y-2">
            {card.details.map(detail => (
              <div key={detail.label} className="flex justify-between text-sm">
                <span className="text-gray-600">{detail.label}</span>
                <span className="font-medium">{detail.value}</span>
              </div>
            ))}
          </div>
        </ExpandableCard>
      ))}
    </div>
  );
};

const ChartSection = ({ projectData, onExpandChart, completionChartRef, healthChartRef }) => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Completion Progress</h3>
        <button
          className="text-blue-600 hover:text-blue-700 text-sm flex items-center"
          onClick={() => onExpandChart('completion')}
        >
          <i className="fas fa-expand-alt mr-1"></i>
          Expand
        </button>
      </div>
      <div className="h-64">
        <canvas ref={completionChartRef}></canvas>
      </div>
    </div>

    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Project Health</h3>
        <button
          className="text-blue-600 hover:text-blue-700 text-sm flex items-center"
          onClick={() => onExpandChart('health')}
        >
          <i className="fas fa-expand-alt mr-1"></i>
          Expand
        </button>
      </div>
      <div className="h-64">
        <canvas ref={healthChartRef}></canvas>
      </div>
    </div>
  </div>
);

const ProjectAccordion = ({ projects, onProjectAction }) => {
  const [expandedProject, setExpandedProject] = useState(null);

  const toggleProject = (projectName) => {
    setExpandedProject(expandedProject === projectName ? null : projectName);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Project Details</h3>
        <button
          className="text-blue-600 hover:text-blue-700 text-sm flex items-center"
          onClick={() => onProjectAction('view-all')}
        >
          <i className="fas fa-expand-alt mr-1"></i>
          Full View
        </button>
      </div>
      
      <div className="space-y-2">
        {projects.map(project => (
          <div key={project.name} className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              className="w-full p-4 bg-white border-none text-left cursor-pointer flex justify-between items-center hover:bg-gray-50 transition-colors"
              onClick={() => toggleProject(project.name)}
              aria-expanded={expandedProject === project.name}
            >
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-gray-900">{project.name}</span>
                  <span 
                    className="px-2 py-1 text-xs rounded-full"
                    style={{ 
                      backgroundColor: `${getHealthColor(project.health)}20`, 
                      color: getHealthColor(project.health) 
                    }}
                  >
                    {getHealthLabel(project.health)}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <span>{project.completion}% complete</span>
                  <span>{project.features} features</span>
                  <span>{project.issues} issues</span>
                  <span>{project.steps} steps</span>
                </div>
              </div>
              <i className={`fas fa-chevron-down transition-transform duration-200 ${expandedProject === project.name ? 'rotate-180' : ''}`}></i>
            </button>
            
            <div className={`transition-all duration-300 overflow-hidden ${expandedProject === project.name ? 'max-h-96' : 'max-h-0'}`}>
              <div className="p-6 bg-gray-50">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Project Overview</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Completion:</span>
                        <span className="font-medium" style={{ color: getCompletionColor(project.completion) }}>
                          {project.completion}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Health Score:</span>
                        <span className="font-medium" style={{ color: getHealthColor(project.health) }}>
                          {project.health}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Features:</span>
                        <span className="font-medium">{project.features}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Issues:</span>
                        <span className="font-medium">{project.issues}</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Quick Actions</h4>
                    <div className="space-y-2">
                      <button 
                        onClick={() => onProjectAction('details', project.name)}
                        className="w-full text-left px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
                      >
                        <i className="fas fa-eye mr-2"></i>View Full Details
                      </button>
                      <button 
                        onClick={() => onProjectAction('edit', project.name)}
                        className="w-full text-left px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
                      >
                        <i className="fas fa-edit mr-2"></i>Edit Project
                      </button>
                      <button 
                        onClick={() => onProjectAction('analytics', project.name)}
                        className="w-full text-left px-3 py-2 text-sm bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors"
                      >
                        <i className="fas fa-chart-line mr-2"></i>Analytics
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const InsightsSection = ({ metrics, onViewAll }) => {
  const insights = [
    {
      title: 'Strong Progress',
      description: `${metrics.average_completion}% average completion shows good project momentum.`,
      icon: 'fas fa-arrow-up',
      category: 'Performance',
      gradient: 'from-green-500 to-green-600'
    },
    {
      title: 'Healthy Projects',
      description: `${metrics.average_health}% average health indicates well-maintained projects.`,
      icon: 'fas fa-heart',
      category: 'Health',
      gradient: 'from-blue-500 to-blue-600'
    },
    {
      title: 'Feature Development',
      description: `${metrics.total_features} features completed across all projects.`,
      icon: 'fas fa-star',
      category: 'Features',
      gradient: 'from-purple-500 to-purple-600'
    },
    {
      title: 'Active Management',
      description: `${metrics.projects_with_goals} projects have defined goals and direction.`,
      icon: 'fas fa-target',
      category: 'Goals',
      gradient: 'from-orange-500 to-orange-600'
    },
    {
      title: 'Issue Resolution',
      description: `${metrics.total_issues} issues being tracked and managed.`,
      icon: 'fas fa-exclamation-triangle',
      category: 'Issues',
      gradient: 'from-red-500 to-red-600'
    },
    {
      title: 'Next Steps',
      description: `${metrics.total_steps} planned next steps across all projects.`,
      icon: 'fas fa-list-check',
      category: 'Planning',
      gradient: 'from-indigo-500 to-indigo-600'
    }
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mt-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Analytics Insights</h3>
        <button
          className="text-blue-600 hover:text-blue-700 text-sm flex items-center"
          onClick={onViewAll}
        >
          <i className="fas fa-expand-alt mr-1"></i>
          View All
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {insights.map((insight, index) => (
          <div key={index} className={`bg-gradient-to-r ${insight.gradient} p-4 rounded-lg text-white`}>
            <div className="flex items-center justify-between mb-2">
              <i className={`${insight.icon} text-xl`}></i>
              <span className="text-xs opacity-75">{insight.category}</span>
            </div>
            <h4 className="font-semibold mb-1">{insight.title}</h4>
            <p className="text-sm opacity-90">{insight.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

const SlidePanel = ({ isOpen, onClose, title, children }) => (
  <>
    <div 
      className={`fixed inset-0 bg-black bg-opacity-30 transition-opacity duration-300 z-30 ${
        isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}
      onClick={onClose}
    />
    <div 
      className={`fixed top-0 right-0 w-full max-w-2xl h-full bg-white shadow-xl transition-transform duration-300 z-40 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100"
          aria-label="Close panel"
        >
          <i className="fas fa-times text-xl"></i>
        </button>
      </div>
      <div className="p-6 overflow-y-auto h-full">
        {children}
      </div>
    </div>
  </>
);

const AdvancedSearchPanel = ({ isOpen, onClose, onSearch, onClear }) => {
  const [formData, setFormData] = useState({
    projectName: '',
    goalKeywords: '',
    issueKeywords: '',
    minCompletion: '',
    maxCompletion: ''
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = () => {
    onSearch(formData);
    onClose();
  };

  const handleClear = () => {
    setFormData({
      projectName: '',
      goalKeywords: '',
      issueKeywords: '',
      minCompletion: '',
      maxCompletion: ''
    });
    onClear();
  };

  return (
    <SlidePanel
      isOpen={isOpen}
      onClose={onClose}
      title="Advanced Search"
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Project Name</label>
          <input
            type="text"
            value={formData.projectName}
            onChange={(e) => handleChange('projectName', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter project name..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Goal Keywords</label>
          <input
            type="text"
            value={formData.goalKeywords}
            onChange={(e) => handleChange('goalKeywords', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter goal keywords..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Issue Keywords</label>
          <input
            type="text"
            value={formData.issueKeywords}
            onChange={(e) => handleChange('issueKeywords', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter issue keywords..."
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Min Completion</label>
            <input
              type="number"
              value={formData.minCompletion}
              onChange={(e) => handleChange('minCompletion', e.target.value)}
              min="0"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Max Completion</label>
            <input
              type="number"
              value={formData.maxCompletion}
              onChange={(e) => handleChange('maxCompletion', e.target.value)}
              min="0"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="100"
            />
          </div>
        </div>
        <div className="flex gap-2 pt-4">
          <button
            onClick={handleSubmit}
            className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Search
          </button>
          <button
            onClick={handleClear}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Clear
          </button>
        </div>
      </div>
    </SlidePanel>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [slidePanel, setSlidePanel] = useState({ isOpen: false, type: null, title: '', content: null });
  const [advancedSearchOpen, setAdvancedSearchOpen] = useState(false);
  
  const completionChartRef = useRef(null);
  const healthChartRef = useRef(null);

  // Load data
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/analytics/overview');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.message || 'Failed to load analytics data');
      }
      
      setData(result.data);
    } catch (err) {
      console.error('Error loading data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((data) => {
    if (data.type === 'context_updated' || data.type === 'feature_completed' || data.type === 'issue_resolved') {
      loadData();
    }
  }, []);

  // WebSocket connection
  const realtimeStatus = useWebSocket('ws://localhost:8000/ws/updates?user_id=dashboard', handleWebSocketMessage);

  // Chart configurations
  const completionChartConfig = useMemo(() => {
    if (!data?.project_summaries) return null;
    
    return {
      type: 'bar',
      data: {
        labels: data.project_summaries.map(p => p.name),
        datasets: [{
          label: 'Completion %',
          data: data.project_summaries.map(p => p.completion),
          backgroundColor: data.project_summaries.map(p => getCompletionColor(p.completion)),
          borderColor: data.project_summaries.map(p => getCompletionColor(p.completion)),
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: function(value) {
                return value + '%';
              }
            }
          }
        }
      }
    };
  }, [data]);

  const healthChartConfig = useMemo(() => {
    if (!data?.project_summaries) return null;
    
    return {
      type: 'doughnut',
      data: {
        labels: data.project_summaries.map(p => p.name),
        datasets: [{
          data: data.project_summaries.map(p => p.health),
          backgroundColor: data.project_summaries.map(p => getHealthColor(p.health)),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 20,
              usePointStyle: true
            }
          }
        }
      }
    };
  }, [data]);

  // Initialize charts
  useChart(completionChartRef, completionChartConfig);
  useChart(healthChartRef, healthChartConfig);

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  // Event handlers
  const handleSearch = (query) => {
    console.log('Search query:', query);
    // Implement search functionality
  };

  const handleFilter = (type, value) => {
    console.log('Filter changed:', type, value);
    // Implement filter functionality
  };

  const handleAdvancedSearch = () => {
    setAdvancedSearchOpen(true);
  };

  const handleExport = (type) => {
    console.log('Export:', type);
    // Implement export functionality
  };

  const handleGenerateReport = () => {
    console.log('Generate report');
    // Implement report generation
  };

  const handleExpandChart = (type) => {
    setSlidePanel({
      isOpen: true,
      type,
      title: type === 'completion' ? 'Completion Progress Details' : 'Project Health Analysis',
      content: type === 'completion' ? 'Completion chart expanded view' : 'Health chart expanded view'
    });
  };

  const handleProjectAction = (action, projectName) => {
    console.log('Project action:', action, projectName);
    // Implement project actions
  };

  const handleViewAllInsights = () => {
    setSlidePanel({
      isOpen: true,
      type: 'insights',
      title: 'Analytics Insights',
      content: 'All insights view'
    });
  };

  const handleAdvancedSearchSubmit = (formData) => {
    console.log('Advanced search:', formData);
    // Implement advanced search
  };

  const handleAdvancedSearchClear = () => {
    console.log('Clear advanced search');
    // Clear search results
  };

  // Loading and error states
  if (loading) {
    return <LoadingScreen />;
  }

  if (error) {
    return <ErrorScreen message={error} onRetry={loadData} />;
  }

  if (!data) {
    return <ErrorScreen message="No data available" onRetry={loadData} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <Header 
        realtimeStatus={realtimeStatus}
        lastUpdated={data.metadata?.timestamp ? new Date(data.metadata.timestamp).toLocaleString() : 'Never'}
        onRefresh={loadData}
        onExport={handleExport}
        onGenerateReport={handleGenerateReport}
      />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SearchAndFilter 
          onSearch={handleSearch}
          onFilter={handleFilter}
          onAdvancedSearch={handleAdvancedSearch}
        />
        
        <OverviewCards metrics={data.overall_metrics} />
        
        <ChartSection 
          projectData={data.project_summaries}
          onExpandChart={handleExpandChart}
          completionChartRef={completionChartRef}
          healthChartRef={healthChartRef}
        />
        
        <ProjectAccordion 
          projects={data.project_summaries}
          onProjectAction={handleProjectAction}
        />
        
        <InsightsSection 
          metrics={data.overall_metrics}
          onViewAll={handleViewAllInsights}
        />
      </main>

      {/* Slide Panel */}
      <SlidePanel
        isOpen={slidePanel.isOpen}
        onClose={() => setSlidePanel({ isOpen: false, type: null, title: '', content: null })}
        title={slidePanel.title}
      >
        {slidePanel.content}
      </SlidePanel>

      {/* Advanced Search Panel */}
      <AdvancedSearchPanel
        isOpen={advancedSearchOpen}
        onClose={() => setAdvancedSearchOpen(false)}
        onSearch={handleAdvancedSearchSubmit}
        onClear={handleAdvancedSearchClear}
      />
    </div>
  );
};

export default Dashboard;
