-- Initialize context_manager database
-- This script runs when the PostgreSQL container starts

-- Create the projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    current_goal TEXT,
    completed_features JSONB DEFAULT '[]',
    current_issues JSONB DEFAULT '[]',
    next_steps JSONB DEFAULT '[]',
    current_state JSONB DEFAULT '{}',
    key_files JSONB DEFAULT '[]',
    context_anchors JSONB DEFAULT '[]',
    conversation_history JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for testing
INSERT INTO projects (name, current_goal, completed_features, current_issues, next_steps)
VALUES (
    'persona-manager-mcp',
    'Build a scalable persona management system with context awareness',
    '["Basic persona management", "Context integration", "Docker containerization"]',
    '["Need to implement scalability", "Add monitoring"]',
    '["Implement database storage", "Add load balancing", "Set up monitoring"]'
) ON CONFLICT (name) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO context_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO context_user;
