"""
Utility functions for context management
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime


def create_status_file(project_name: str, project_root: Optional[str] = None) -> str:
    """Create a basic status file for a project"""
    project_root = Path(project_root) if project_root else Path.cwd()
    status_file = project_root / "CONTEXT_STATUS.md"
    
    content = f"""# {project_name} - Project Status

## 🎯 **Current Goal**: [Define your current goal here]

## ✅ **Completed Features**
- [Add completed features here]

## 🔧 **Current Issues**
- [Add any current issues here]

## 📋 **Next Steps**
1. [Add next steps here]

## 📊 **Current State**
- [Add current state information]

## 🔍 **Key Files**
- [Add key files here]

## 🎯 **Context Anchors**
- 🔴 **Goal**: [Primary goal]
- 🟡 **Approach**: [Current approach]
- 🟢 **Success Criteria**: [How to know when done]

---
*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    status_file.write_text(content)
    return str(status_file)


def quick_status_check(project_root: Optional[str] = None) -> str:
    """Quick status check for any project"""
    project_root = Path(project_root) if project_root else Path.cwd()
    status_file = project_root / "CONTEXT_STATUS.md"
    context_file = project_root / ".context_cache.json"
    
    if not status_file.exists():
        return "📁 No status file found. Run create_status_file() to initialize."
    
    # Try to read JSON cache first for faster access
    if context_file.exists():
        try:
            with open(context_file, 'r') as f:
                data = json.load(f)
            
            summary = f"🎯 {data.get('project_name', 'Unknown Project')}: {data.get('current_goal', 'No goal set')}\n"
            
            # Count open issues
            open_issues = [i for i in data.get('current_issues', []) if i.get('status') == 'open']
            if open_issues:
                summary += f"🔧 Issues: {len(open_issues)} open\n"
            
            # Show next step
            next_steps = data.get('next_steps', [])
            if next_steps:
                summary += f"📋 Next: {next_steps[0]}\n"
            
            # Show high-priority anchors
            anchors = data.get('context_anchors', [])
            high_priority = [a for a in anchors if a.get('priority') == 1]
            if high_priority:
                summary += f"🎯 Anchors: {', '.join([a['key'] for a in high_priority])}\n"
            
            return summary.strip()
            
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Fallback to reading markdown file
    try:
        content = status_file.read_text()
        lines = content.split('\n')
        
        summary = []
        for line in lines:
            if line.startswith('## 🎯 **Current Goal**'):
                goal = line.replace('## 🎯 **Current Goal**:', '').strip()
                summary.append(f"🎯 Goal: {goal}")
            elif line.startswith('## 🔧 **Current Issues**'):
                # Count issues in next section
                issue_count = 0
                for i, l in enumerate(lines[lines.index(line):]):
                    if l.startswith('## '):
                        break
                    if l.strip().startswith('- **'):
                        issue_count += 1
                if issue_count > 0:
                    summary.append(f"🔧 Issues: {issue_count} open")
            elif line.startswith('## 📋 **Next Steps**'):
                # Get first next step
                for i, l in enumerate(lines[lines.index(line):]):
                    if l.startswith('## '):
                        break
                    if l.strip().startswith('1.'):
                        step = l.replace('1.', '').strip()
                        summary.append(f"📋 Next: {step}")
                        break
                break
        
        return '\n'.join(summary) if summary else "📁 Status file found but no summary available"
        
    except Exception as e:
        return f"❌ Error reading status: {e}"


def get_project_info(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Get basic project information"""
    project_root = Path(project_root) if project_root else Path.cwd()
    
    info = {
        "name": project_root.name,
        "root": str(project_root),
        "has_status_file": False,
        "has_context_cache": False,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "files_count": 0,
        "directories_count": 0
    }
    
    # Check for status files
    status_file = project_root / "CONTEXT_STATUS.md"
    context_file = project_root / ".context_cache.json"
    
    info["has_status_file"] = status_file.exists()
    info["has_context_cache"] = context_file.exists()
    
    # Count files and directories
    try:
        items = list(project_root.iterdir())
        info["files_count"] = len([item for item in items if item.is_file()])
        info["directories_count"] = len([item for item in items if item.is_dir()])
    except PermissionError:
        pass
    
    return info


def create_context_script(project_root: Optional[str] = None) -> str:
    """Create a quick context check script"""
    project_root = Path(project_root) if project_root else Path.cwd()
    script_file = project_root / "context_check.py"
    
    script_content = '''#!/usr/bin/env python3
"""
Quick context check script
Run with: python context_check.py
"""

import sys
from pathlib import Path

# Add the context_manager to path if it exists
context_manager_path = Path(__file__).parent
if context_manager_path.exists():
    sys.path.insert(0, str(context_manager_path.parent))

try:
    from context_manager.utils import quick_status_check, get_project_info
    from context_manager.core import ContextManager
    
    print("🎯 Project Context Check")
    print("=" * 30)
    
    # Get project info
    info = get_project_info()
    print(f"📁 Project: {info['name']}")
    print(f"🐍 Python: {info['python_version']}")
    print(f"📄 Files: {info['files_count']}")
    print(f"📁 Directories: {info['directories_count']}")
    print()
    
    # Show status
    status = quick_status_check()
    print(status)
    
    # Show context manager if available
    if info['has_context_cache']:
        print("\\n📊 Context Manager: Active")
    else:
        print("\\n📊 Context Manager: Not initialized")
        print("   Run: from context_manager.core import ContextManager")
        print("   Then: cm = ContextManager('ProjectName')")
        
except ImportError as e:
    print(f"❌ Context manager not available: {e}")
    print("📁 Make sure context_manager/ directory exists")
except Exception as e:
    print(f"❌ Error: {e}")

if __name__ == "__main__":
    pass
'''
    
    script_file.write_text(script_content)
    script_file.chmod(0o755)  # Make executable
    return str(script_file)


def create_makefile_targets(project_root: Optional[str] = None) -> str:
    """Create Makefile targets for context management"""
    project_root = Path(project_root) if project_root else Path.cwd()
    makefile = project_root / "Makefile"
    
    targets = '''
# Context Management
context-status:
	@python context_check.py

context-init:
	@python -c "from context_manager.core import ContextManager; cm = ContextManager('$(shell basename $(PWD))'); cm.set_current_goal('Initialize project context'); print('✅ Context initialized')"

context-summary:
	@python -c "from context_manager.utils import quick_status_check; print(quick_status_check())"

context-update:
	@echo "Updating context..."
	@python -c "from context_manager.core import ContextManager; cm = ContextManager('$(shell basename $(PWD))'); print('✅ Context updated')"
'''
    
    if makefile.exists():
        # Append to existing Makefile
        with open(makefile, 'a') as f:
            f.write(targets)
    else:
        # Create new Makefile
        makefile.write_text(targets)
    
    return str(makefile)
