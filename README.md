# Context Manager

A reusable system for maintaining context across long AI conversations and development sessions.

## 🎯 **What is Context Manager?**

Context Manager helps you maintain focus and context during long AI-assisted development sessions. It tracks:

- **Current Goals**: What you're trying to accomplish
- **Completed Features**: What's been done
- **Current Issues**: Problems you're facing
- **Next Steps**: What to do next
- **Context Anchors**: Key information to remember
- **Project State**: Current status and metrics

## 🚀 **Quick Start**

### 1. Setup for a New Project

```bash
# Setup context management for current project
python context_manager/cli.py setup

# Or initialize manually
python context_manager/cli.py init --goal "Build a web app"
```

### 2. Check Status

```bash
# Quick status check
python context_manager/cli.py status

# Or use the generated script
python context_check.py

# Or use Makefile (if available)
make context-status
```

### 3. Update Context

```bash
# Set current goal
python context_manager/cli.py goal "Deploy to production"

# Add an issue
python context_manager/cli.py issue "Build failing" --location "CI/CD pipeline"

# Add next step
python context_manager/cli.py next "Fix authentication bug"

# Add context anchor
python context_manager/cli.py anchor "API_KEY" "sk-123..." --description "OpenAI API key"
```

## 📋 **Core Features**

### **ContextManager Class**

The main class for managing project context:

```python
from context_manager.core import ContextManager

# Initialize
cm = ContextManager("MyProject")

# Set goal
cm.set_current_goal("Build authentication system")

# Add completed feature
cm.add_completed_feature("User registration")

# Add issue
cm.add_current_issue("Login not working", "auth/login.py", "Missing validation")

# Add next step
cm.add_next_step("Fix password validation")

# Add context anchor
cm.add_context_anchor("DB_URL", "postgresql://...", "Database connection", priority=1)

# Get summary
print(cm.get_context_summary())
```

### **Quick Status Check**

Get a concise status summary:

```python
from context_manager.utils import quick_status_check

status = quick_status_check()
print(status)
# Output: 🎯 MyProject: Build authentication system
#         🔧 Issues: 1 open
#         📋 Next: Fix password validation
```

### **Project Information**

Get basic project metrics:

```python
from context_manager.utils import get_project_info

info = get_project_info()
print(f"Project: {info['name']}")
print(f"Files: {info['files_count']}")
print(f"Has status: {info['has_status_file']}")
```

## 🛠 **Command Line Interface**

### **Available Commands**

| Command   | Description           | Example                                        |
| --------- | --------------------- | ---------------------------------------------- |
| `status`  | Show current status   | `context-manager status`                       |
| `init`    | Initialize context    | `context-manager init --goal "Build app"`      |
| `goal`    | Set current goal      | `context-manager goal "Deploy to production"`  |
| `issue`   | Add current issue     | `context-manager issue "Build failing"`        |
| `resolve` | Resolve an issue      | `context-manager resolve "Build failing"`      |
| `next`    | Add next step         | `context-manager next "Fix tests"`             |
| `anchor`  | Add context anchor    | `context-manager anchor "API_KEY" "sk-123..."` |
| `feature` | Add completed feature | `context-manager feature "User auth"`          |
| `state`   | Update current state  | `context-manager state "version" "1.0.0"`      |
| `setup`   | Setup for project     | `context-manager setup`                        |

### **Command Options**

Most commands support:

- `--project-root`: Specify project directory
- `--project-name`: Specify project name (for init/setup)

## 📁 **Generated Files**

When you run `setup`, Context Manager creates:

- **`CONTEXT_STATUS.md`**: Human-readable status file
- **`.context_cache.json`**: Machine-readable cache
- **`context_check.py`**: Quick status script
- **Makefile targets**: For `make context-status`

## 🎯 **Context Anchors**

Context anchors are key pieces of information to remember:

```python
# High priority (🔴) - Critical information
cm.add_context_anchor("API_KEY", "sk-123...", "OpenAI API key", priority=1)

# Medium priority (🟡) - Important information
cm.add_context_anchor("DB_URL", "postgresql://...", "Database URL", priority=2)

# Low priority (🟢) - Nice to know
cm.add_context_anchor("VERSION", "1.0.0", "Current version", priority=3)
```

## 🔄 **Integration Examples**

### **With AI Assistants**

```python
# At the start of a session
cm = ContextManager("MyProject")
cm.set_current_goal("Fix authentication bug")

# During development
cm.add_current_issue("Login redirects to wrong page", "auth/views.py")

# When done
cm.add_completed_feature("Fixed login redirect")
cm.resolve_issue("Login redirects to wrong page")
```

### **With CI/CD**

```python
# Track deployment state
cm.update_current_state("environment", "staging")
cm.update_current_state("version", "1.2.3")
cm.add_context_anchor("DEPLOY_URL", "https://staging.example.com")
```

### **With Testing**

```python
# Track test status
cm.add_current_issue("Tests failing", "test_auth.py", "Missing mock setup")
cm.add_next_step("Add authentication mocks")
```

## 🎨 **Customization**

### **Custom Status Templates**

```python
# Override status generation
class CustomContextManager(ContextManager):
    def _generate_markdown(self) -> str:
        # Custom markdown generation
        return "Custom status format"
```

### **Integration with Other Tools**

```python
# With Git
cm.add_context_anchor("BRANCH", "feature/auth", "Current git branch")

# With Docker
cm.update_current_state("container", "running")
cm.add_context_anchor("DOCKER_IMAGE", "myapp:latest")
```

## 🚀 **Best Practices**

### **1. Initialize Early**

```bash
# Start every project with context management
python context_manager/cli.py setup
```

### **2. Update Frequently**

```bash
# Update context as you work
context-manager goal "Fix the bug"
context-manager issue "Tests failing"
context-manager next "Add logging"
```

### **3. Use Anchors for Key Info**

```bash
# Store important information
context-manager anchor "API_KEY" "sk-123..." --priority 1
context-manager anchor "DB_PASSWORD" "secret123" --priority 1
```

### **4. Regular Status Checks**

```bash
# Check status regularly
make context-status
# or
python context_check.py
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Import Error**: Make sure `context_manager/` is in your project
2. **Permission Error**: Check file permissions for generated files
3. **Path Issues**: Use `--project-root` to specify correct directory

### **Debug Mode**

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

from context_manager.core import ContextManager
cm = ContextManager("debug-project")
```

## 📚 **API Reference**

### **ContextManager Methods**

- `set_current_goal(goal: str)` - Set primary goal
- `add_completed_feature(feature: str)` - Add completed feature
- `add_current_issue(problem: str, location: str, root_cause: str)` - Add issue
- `resolve_issue(problem: str)` - Mark issue as resolved
- `add_next_step(step: str)` - Add next step
- `add_context_anchor(key: str, value: str, description: str, priority: int)` - Add anchor
- `update_current_state(key: str, value: Any)` - Update state
- `get_context_summary()` - Get concise summary

### **Utility Functions**

- `quick_status_check(project_root: str)` - Quick status
- `get_project_info(project_root: str)` - Project metrics
- `create_status_file(project_name: str, project_root: str)` - Create status file
- `create_context_script(project_root: str)` - Create check script

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 **License**

MIT License - see LICENSE file for details.
