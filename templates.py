"""
Context Templates for Project Types

This module provides predefined templates for common project types,
allowing users to quickly initialize projects with appropriate context structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class ProjectTemplate:
    """A predefined project template with context structure"""
    name: str
    description: str
    category: str
    default_goal: str
    suggested_features: List[str] = field(default_factory=list)
    common_issues: List[str] = field(default_factory=list)
    suggested_steps: List[str] = field(default_factory=list)
    context_anchors: List[Dict[str, Any]] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class TemplateManager:
    """Manages project templates and template operations"""
    
    def __init__(self):
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, ProjectTemplate]:
        """Load the default project templates"""
        return {
            "web-app": ProjectTemplate(
                name="Web Application",
                description="Full-stack web application with frontend and backend",
                category="Web Development",
                default_goal="Build a responsive web application with modern UI/UX",
                suggested_features=[
                    "User authentication and authorization",
                    "Responsive design for mobile and desktop",
                    "Database integration and data persistence",
                    "API endpoints for data operations",
                    "User dashboard and profile management",
                    "Search and filtering functionality",
                    "File upload and media handling",
                    "Real-time notifications or updates"
                ],
                common_issues=[
                    "Cross-browser compatibility issues",
                    "Performance optimization for large datasets",
                    "Security vulnerabilities in authentication",
                    "Mobile responsiveness problems",
                    "Database connection and query optimization",
                    "API rate limiting and error handling",
                    "State management complexity",
                    "SEO optimization challenges"
                ],
                suggested_steps=[
                    "Set up development environment and project structure",
                    "Design database schema and relationships",
                    "Implement user authentication system",
                    "Create responsive UI components",
                    "Develop API endpoints and business logic",
                    "Add error handling and validation",
                    "Implement testing suite",
                    "Deploy to production environment"
                ],
                context_anchors=[
                    {"key": "FRONTEND_FRAMEWORK", "value": "React/Vue/Angular", "description": "Frontend framework choice", "priority": 1},
                    {"key": "BACKEND_FRAMEWORK", "value": "Django/Flask/Express", "description": "Backend framework choice", "priority": 1},
                    {"key": "DATABASE", "value": "PostgreSQL/MySQL/MongoDB", "description": "Database system", "priority": 1},
                    {"key": "DEPLOYMENT_PLATFORM", "value": "AWS/Heroku/Vercel", "description": "Deployment platform", "priority": 2},
                    {"key": "API_VERSION", "value": "v1", "description": "API version", "priority": 3}
                ],
                key_files=[
                    "package.json",
                    "requirements.txt",
                    "docker-compose.yml",
                    "README.md",
                    ".env.example",
                    "src/",
                    "public/",
                    "tests/"
                ],
                tags=["web", "fullstack", "frontend", "backend", "database", "api"]
            ),
            
            "api-service": ProjectTemplate(
                name="API Service",
                description="RESTful API service with microservices architecture",
                category="Backend Development",
                default_goal="Build a scalable RESTful API service with proper documentation",
                suggested_features=[
                    "RESTful API endpoints with proper HTTP methods",
                    "API authentication and authorization (JWT/OAuth)",
                    "Request/response validation and error handling",
                    "API documentation with OpenAPI/Swagger",
                    "Database integration with ORM",
                    "Caching layer for performance optimization",
                    "Rate limiting and request throttling",
                    "Logging and monitoring integration",
                    "Health check endpoints",
                    "API versioning strategy"
                ],
                common_issues=[
                    "API security vulnerabilities",
                    "Performance bottlenecks in database queries",
                    "Inconsistent error response formats",
                    "Missing input validation",
                    "Poor API documentation",
                    "Scalability issues with high traffic",
                    "Authentication token management",
                    "Cross-origin resource sharing (CORS) issues"
                ],
                suggested_steps=[
                    "Design API architecture and endpoint structure",
                    "Set up database models and migrations",
                    "Implement authentication and authorization",
                    "Create core API endpoints with validation",
                    "Add comprehensive error handling",
                    "Generate API documentation",
                    "Implement caching and performance optimization",
                    "Set up monitoring and logging",
                    "Add comprehensive test coverage",
                    "Deploy with proper CI/CD pipeline"
                ],
                context_anchors=[
                    {"key": "API_FRAMEWORK", "value": "FastAPI/Flask/Django REST", "description": "API framework", "priority": 1},
                    {"key": "DATABASE", "value": "PostgreSQL/MySQL", "description": "Database system", "priority": 1},
                    {"key": "AUTH_METHOD", "value": "JWT/OAuth2", "description": "Authentication method", "priority": 1},
                    {"key": "API_VERSION", "value": "v1", "description": "API version", "priority": 2},
                    {"key": "DEPLOYMENT", "value": "Docker/Kubernetes", "description": "Deployment method", "priority": 2}
                ],
                key_files=[
                    "requirements.txt",
                    "docker-compose.yml",
                    "Dockerfile",
                    "api/",
                    "models/",
                    "tests/",
                    "docs/",
                    ".env.example"
                ],
                tags=["api", "backend", "microservices", "rest", "database", "authentication"]
            ),
            
            "data-science": ProjectTemplate(
                name="Data Science Project",
                description="Data analysis, machine learning, and statistical modeling project",
                category="Data Science",
                default_goal="Analyze data and build predictive models with proper documentation",
                suggested_features=[
                    "Data collection and preprocessing pipeline",
                    "Exploratory data analysis (EDA) with visualizations",
                    "Feature engineering and selection",
                    "Machine learning model development and training",
                    "Model evaluation and validation",
                    "Data visualization and reporting",
                    "Model deployment and serving",
                    "Automated data pipeline",
                    "Statistical analysis and hypothesis testing",
                    "Reproducible research with version control"
                ],
                common_issues=[
                    "Data quality and missing values",
                    "Overfitting in machine learning models",
                    "Feature scaling and normalization",
                    "Model interpretability and explainability",
                    "Data leakage in training/validation splits",
                    "Computational resource limitations",
                    "Reproducibility across different environments",
                    "Model performance degradation over time"
                ],
                suggested_steps=[
                    "Define problem statement and success metrics",
                    "Collect and explore the dataset",
                    "Clean and preprocess the data",
                    "Perform exploratory data analysis",
                    "Engineer features and select relevant variables",
                    "Split data and implement cross-validation",
                    "Train and evaluate multiple models",
                    "Optimize hyperparameters",
                    "Validate model performance",
                    "Deploy model and create monitoring system"
                ],
                context_anchors=[
                    {"key": "DATASET", "value": "CSV/JSON/Database", "description": "Data source format", "priority": 1},
                    {"key": "ML_FRAMEWORK", "value": "scikit-learn/TensorFlow/PyTorch", "description": "ML framework", "priority": 1},
                    {"key": "ENVIRONMENT", "value": "Jupyter/Colab/Local", "description": "Development environment", "priority": 2},
                    {"key": "EVALUATION_METRIC", "value": "Accuracy/F1/MAE", "description": "Primary evaluation metric", "priority": 2},
                    {"key": "DEPLOYMENT", "value": "Flask/FastAPI/Streamlit", "description": "Model deployment method", "priority": 3}
                ],
                key_files=[
                    "requirements.txt",
                    "notebooks/",
                    "data/",
                    "src/",
                    "models/",
                    "reports/",
                    "tests/",
                    "README.md"
                ],
                tags=["data-science", "machine-learning", "analytics", "python", "jupyter", "statistics"]
            ),
            
            "mobile-app": ProjectTemplate(
                name="Mobile Application",
                description="Cross-platform or native mobile application",
                category="Mobile Development",
                default_goal="Build a user-friendly mobile application with offline capabilities",
                suggested_features=[
                    "User authentication and profile management",
                    "Offline data synchronization",
                    "Push notifications",
                    "Camera and media integration",
                    "Location services and maps",
                    "In-app purchases or payments",
                    "Social features and sharing",
                    "Performance optimization for mobile devices",
                    "Cross-platform compatibility",
                    "App store optimization"
                ],
                common_issues=[
                    "Performance optimization for mobile devices",
                    "Offline functionality and data sync",
                    "Cross-platform compatibility issues",
                    "App store approval and guidelines compliance",
                    "Memory management and battery optimization",
                    "Network connectivity handling",
                    "User interface adaptation for different screen sizes",
                    "Security for sensitive data storage"
                ],
                suggested_steps=[
                    "Choose development framework (React Native/Flutter/Native)",
                    "Set up development environment and tools",
                    "Design user interface and user experience",
                    "Implement core app functionality",
                    "Add offline capabilities and data persistence",
                    "Integrate third-party services and APIs",
                    "Implement push notifications",
                    "Add security measures and data protection",
                    "Test on multiple devices and platforms",
                    "Prepare for app store submission"
                ],
                context_anchors=[
                    {"key": "FRAMEWORK", "value": "React Native/Flutter/iOS/Android", "description": "Mobile framework", "priority": 1},
                    {"key": "BACKEND_API", "value": "REST/GraphQL", "description": "Backend API type", "priority": 1},
                    {"key": "DATABASE", "value": "SQLite/Realm/Firebase", "description": "Local database", "priority": 2},
                    {"key": "PLATFORM", "value": "iOS/Android/Both", "description": "Target platforms", "priority": 2},
                    {"key": "DEPLOYMENT", "value": "App Store/Play Store", "description": "Deployment target", "priority": 3}
                ],
                key_files=[
                    "package.json",
                    "android/",
                    "ios/",
                    "src/",
                    "assets/",
                    "tests/",
                    "README.md"
                ],
                tags=["mobile", "react-native", "flutter", "ios", "android", "cross-platform"]
            ),
            
            "documentation": ProjectTemplate(
                name="Documentation Project",
                description="Technical documentation, API docs, or knowledge base",
                category="Documentation",
                default_goal="Create comprehensive and user-friendly documentation",
                suggested_features=[
                    "Clear and structured content organization",
                    "Search functionality",
                    "Interactive examples and code snippets",
                    "Version control and change tracking",
                    "Multi-format output (HTML, PDF, etc.)",
                    "User feedback and contribution system",
                    "Translation and localization support",
                    "Integration with development workflow",
                    "Automated documentation generation",
                    "Accessibility compliance"
                ],
                common_issues=[
                    "Keeping documentation up-to-date with code changes",
                    "Ensuring clarity and readability for different audiences",
                    "Organizing complex information architecture",
                    "Managing multiple versions and branches",
                    "Search functionality and discoverability",
                    "Contributor onboarding and guidelines",
                    "Translation quality and consistency",
                    "Performance with large documentation sets"
                ],
                suggested_steps=[
                    "Define target audience and documentation goals",
                    "Plan information architecture and content structure",
                    "Choose documentation platform and tools",
                    "Create content templates and style guides",
                    "Write core documentation content",
                    "Add interactive examples and tutorials",
                    "Implement search and navigation features",
                    "Set up automated build and deployment",
                    "Establish review and contribution processes",
                    "Monitor usage and gather feedback"
                ],
                context_anchors=[
                    {"key": "PLATFORM", "value": "GitBook/MkDocs/Sphinx", "description": "Documentation platform", "priority": 1},
                    {"key": "FORMAT", "value": "Markdown/reStructuredText", "description": "Content format", "priority": 2},
                    {"key": "HOSTING", "value": "GitHub Pages/Netlify/Vercel", "description": "Hosting platform", "priority": 2},
                    {"key": "AUDIENCE", "value": "Developers/Users/Internal", "description": "Primary audience", "priority": 3}
                ],
                key_files=[
                    "docs/",
                    "mkdocs.yml",
                    "README.md",
                    "CONTRIBUTING.md",
                    "LICENSE",
                    ".github/"
                ],
                tags=["documentation", "markdown", "api-docs", "technical-writing", "knowledge-base"]
            ),
            
            "devops": ProjectTemplate(
                name="DevOps Infrastructure",
                description="Infrastructure as Code, CI/CD, and deployment automation",
                category="DevOps",
                default_goal="Automate deployment and infrastructure management",
                suggested_features=[
                    "Infrastructure as Code (IaC) with Terraform/CloudFormation",
                    "Continuous Integration and Deployment (CI/CD) pipelines",
                    "Container orchestration with Kubernetes/Docker",
                    "Monitoring and logging systems",
                    "Automated testing and quality gates",
                    "Environment management (dev/staging/prod)",
                    "Security scanning and compliance",
                    "Backup and disaster recovery",
                    "Performance monitoring and alerting",
                    "Cost optimization and resource management"
                ],
                common_issues=[
                    "Environment consistency across dev/staging/prod",
                    "Infrastructure drift and configuration management",
                    "Security vulnerabilities in CI/CD pipelines",
                    "Monitoring and alerting fatigue",
                    "Cost management and resource optimization",
                    "Disaster recovery and backup strategies",
                    "Compliance and audit requirements",
                    "Team collaboration and knowledge sharing"
                ],
                suggested_steps=[
                    "Assess current infrastructure and deployment processes",
                    "Design target architecture and infrastructure",
                    "Implement Infrastructure as Code",
                    "Set up CI/CD pipelines with automated testing",
                    "Configure monitoring and logging systems",
                    "Implement security scanning and compliance checks",
                    "Set up backup and disaster recovery procedures",
                    "Create documentation and runbooks",
                    "Train team on new processes and tools",
                    "Monitor and optimize performance and costs"
                ],
                context_anchors=[
                    {"key": "CLOUD_PROVIDER", "value": "AWS/Azure/GCP", "description": "Cloud platform", "priority": 1},
                    {"key": "IAC_TOOL", "value": "Terraform/CloudFormation", "description": "Infrastructure as Code tool", "priority": 1},
                    {"key": "CI_CD", "value": "GitHub Actions/Jenkins/GitLab CI", "description": "CI/CD platform", "priority": 1},
                    {"key": "CONTAINER", "value": "Docker/Kubernetes", "description": "Container platform", "priority": 2},
                    {"key": "MONITORING", "value": "Prometheus/Grafana/DataDog", "description": "Monitoring stack", "priority": 2}
                ],
                key_files=[
                    "terraform/",
                    "docker-compose.yml",
                    "Dockerfile",
                    ".github/workflows/",
                    "k8s/",
                    "monitoring/",
                    "scripts/",
                    "README.md"
                ],
                tags=["devops", "infrastructure", "ci-cd", "docker", "kubernetes", "terraform"]
            )
        }
    
    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates with metadata"""
        return {
            template_id: {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags
            }
            for template_id, template in self.templates.items()
        }
    
    def get_templates_by_category(self, category: str) -> Dict[str, ProjectTemplate]:
        """Get all templates in a specific category"""
        return {
            template_id: template
            for template_id, template in self.templates.items()
            if template.category.lower() == category.lower()
        }
    
    def search_templates(self, query: str) -> Dict[str, ProjectTemplate]:
        """Search templates by name, description, or tags"""
        query_lower = query.lower()
        results = {}
        
        for template_id, template in self.templates.items():
            # Search in name, description, and tags
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results[template_id] = template
        
        return results
    
    def create_custom_template(self, template_data: Dict[str, Any]) -> str:
        """Create a custom template from provided data"""
        # Generate a unique ID for the custom template
        template_id = f"custom-{len(self.templates) + 1}"
        
        template = ProjectTemplate(
            name=template_data.get("name", "Custom Template"),
            description=template_data.get("description", ""),
            category=template_data.get("category", "Custom"),
            default_goal=template_data.get("default_goal", ""),
            suggested_features=template_data.get("suggested_features", []),
            common_issues=template_data.get("common_issues", []),
            suggested_steps=template_data.get("suggested_steps", []),
            context_anchors=template_data.get("context_anchors", []),
            key_files=template_data.get("key_files", []),
            tags=template_data.get("tags", [])
        )
        
        self.templates[template_id] = template
        return template_id
    
    def apply_template_to_context(self, template_id: str, project_name: str) -> Dict[str, Any]:
        """Apply a template to create initial context for a project"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        # Create context data from template
        context_data = {
            "project_name": project_name,
            "current_goal": template.default_goal,
            "completed_features": [],
            "current_issues": [],
            "next_steps": template.suggested_steps.copy(),
            "current_state": {
                "template_used": template_id,
                "template_name": template.name,
                "created_at": datetime.now().isoformat()
            },
            "key_files": template.key_files.copy(),
            "context_anchors": [
                {
                    "key": anchor["key"],
                    "value": anchor["value"],
                    "description": anchor["description"],
                    "priority": anchor.get("priority", 2),
                    "created_at": datetime.now().isoformat()
                }
                for anchor in template.context_anchors
            ]
        }
        
        return context_data


# Global template manager instance
template_manager = TemplateManager()

