"""
Core context management classes for maintaining conversation context
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import os


@dataclass
class ContextAnchor:
    """A key piece of context that should be maintained throughout the conversation"""
    key: str
    value: str
    description: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProjectStatus:
    """Current status of a project"""
    name: str
    current_goal: str
    completed_features: List[str] = field(default_factory=list)
    current_issues: List[Dict[str, str]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    key_files: List[str] = field(default_factory=list)
    context_anchors: List[ContextAnchor] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


class ContextManager:
    """Main context manager for maintaining conversation state"""
    
    def __init__(self, project_name: str, project_root: Optional[str] = None):
        self.project_name = project_name
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.status_file = self.project_root / f"{self.project_name}_CONTEXT_STATUS.md"
        self.context_file = self.project_root / f"{self.project_name}_context_cache.json"
        self.status: Optional[ProjectStatus] = None
        self.conversation_history: List[Dict[str, Any]] = []
        
    def set_current_goal(self, goal: str) -> None:
        """Set the current primary goal"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal=goal)
        else:
            self.status.current_goal = goal
            self.status.last_updated = datetime.now()
        self._save_status()
    
    def add_completed_feature(self, feature: str) -> None:
        """Add a completed feature to the status"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        if feature not in self.status.completed_features:
            self.status.completed_features.append(feature)
            self.status.last_updated = datetime.now()
        self._save_status()
    
    def add_current_issue(self, problem: str, location: str = "", root_cause: str = "", status: str = "open") -> None:
        """Add a current issue to track"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        
        issue = {
            "problem": problem,
            "location": location,
            "root_cause": root_cause,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        
        # Update existing issue if it exists
        for existing_issue in self.status.current_issues:
            if existing_issue.get("problem") == problem:
                existing_issue.update(issue)
                self.status.last_updated = datetime.now()
                self._save_status()
                return
        
        self.status.current_issues.append(issue)
        self.status.last_updated = datetime.now()
        self._save_status()
    
    def resolve_issue(self, problem: str) -> None:
        """Mark an issue as resolved"""
        if not self.status:
            return
            
        for issue in self.status.current_issues:
            if issue.get("problem") == problem:
                issue["status"] = "resolved"
                issue["resolved_at"] = datetime.now().isoformat()
                self.status.last_updated = datetime.now()
                break
        self._save_status()
    
    def add_next_step(self, step: str) -> None:
        """Add a next step to the plan"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        if step not in self.status.next_steps:
            self.status.next_steps.append(step)
            self.status.last_updated = datetime.now()
        self._save_status()
    
    def update_current_state(self, key: str, value: Any) -> None:
        """Update current state information"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        self.status.current_state[key] = value
        self.status.last_updated = datetime.now()
        self._save_status()
    
    def add_key_file(self, file_path: str, description: str = "") -> None:
        """Add a key file to track"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        
        file_info = {"path": file_path, "description": description}
        if file_info not in self.status.key_files:
            self.status.key_files.append(file_info)
            self.status.last_updated = datetime.now()
        self._save_status()
    
    def add_context_anchor(self, key: str, value: str, description: str, priority: int = 1) -> None:
        """Add a context anchor to maintain throughout the conversation"""
        if not self.status:
            self.status = ProjectStatus(name=self.project_name, current_goal="")
        
        anchor = ContextAnchor(key=key, value=value, description=description, priority=priority)
        
        # Update existing anchor if it exists
        for existing_anchor in self.status.context_anchors:
            if existing_anchor.key == key:
                existing_anchor.value = value
                existing_anchor.description = description
                existing_anchor.priority = priority
                break
        else:
            self.status.context_anchors.append(anchor)
        
        self.status.last_updated = datetime.now()
        self._save_status()
    
    def load_status(self) -> None:
        """Load status from file if it exists"""
        if self.context_file.exists():
            try:
                data = json.loads(self.context_file.read_text())
                self.status = ProjectStatus(
                    name=data["project_name"],
                    current_goal=data["current_goal"],
                    completed_features=data["completed_features"],
                    current_issues=data["current_issues"],
                    next_steps=data["next_steps"],
                    current_state=data["current_state"],
                    key_files=data["key_files"],
                    context_anchors=[
                        ContextAnchor(
                            key=a["key"],
                            value=a["value"],
                            description=a["description"],
                            priority=a["priority"],
                            created_at=datetime.fromisoformat(a["created_at"])
                        )
                        for a in data["context_anchors"]
                    ],
                    last_updated=datetime.fromisoformat(data["last_updated"])
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # If loading fails, start fresh
                self.status = None
    
    def get_context_summary(self) -> str:
        """Get a concise summary of current context"""
        if not self.status:
            return f"🎯 {self.project_name}: No status tracked yet"
        
        summary = f"🎯 {self.status.name}: {self.status.current_goal}\n"
        
        if self.status.current_issues:
            open_issues = [i for i in self.status.current_issues if i.get("status") == "open"]
            if open_issues:
                summary += f"🔧 Issues: {len(open_issues)} open\n"
        
        if self.status.next_steps:
            summary += f"📋 Next: {self.status.next_steps[0]}\n"
        
        # Add high-priority context anchors
        high_priority = [a for a in self.status.context_anchors if a.priority == 1]
        if high_priority:
            summary += f"🎯 Anchors: {', '.join([a.key for a in high_priority])}\n"
        
        return summary.strip()
    
    def _save_status(self) -> None:
        """Save status to file"""
        if not self.status:
            return
            
        # Save as markdown
        content = self._generate_markdown()
        self.status_file.write_text(content)
        
        # Save as JSON for programmatic access
        data = {
            "project_name": self.status.name,
            "current_goal": self.status.current_goal,
            "completed_features": self.status.completed_features,
            "current_issues": self.status.current_issues,
            "next_steps": self.status.next_steps,
            "current_state": self.status.current_state,
            "key_files": self.status.key_files,
            "context_anchors": [
                {
                    "key": a.key,
                    "value": a.value,
                    "description": a.description,
                    "priority": a.priority,
                    "created_at": a.created_at.isoformat()
                }
                for a in self.status.context_anchors
            ],
            "last_updated": self.status.last_updated.isoformat()
        }
        self.context_file.write_text(json.dumps(data, indent=2))
    
    def _generate_markdown(self) -> str:
        """Generate markdown status file"""
        if not self.status:
            return f"# {self.project_name} - No Status Tracked"
        
        content = f"# {self.status.name} - Project Status\n\n"
        content += f"## 🎯 **Current Goal**: {self.status.current_goal}\n\n"
        
        if self.status.completed_features:
            content += "## ✅ **Completed Features**\n"
            for feature in self.status.completed_features:
                content += f"- {feature}\n"
            content += "\n"
        
        if self.status.current_issues:
            content += "## 🔧 **Current Issues**\n"
            for issue in self.status.current_issues:
                if issue.get("status") == "open":
                    content += f"- **{issue['problem']}**\n"
                    if issue.get("location"):
                        content += f"  - Location: {issue['location']}\n"
                    if issue.get("root_cause"):
                        content += f"  - Root Cause: {issue['root_cause']}\n"
            content += "\n"
        
        if self.status.next_steps:
            content += "## 📋 **Next Steps**\n"
            for i, step in enumerate(self.status.next_steps, 1):
                content += f"{i}. {step}\n"
            content += "\n"
        
        if self.status.current_state:
            content += "## 📊 **Current State**\n"
            for key, value in self.status.current_state.items():
                content += f"- **{key}**: {value}\n"
            content += "\n"
        
        if self.status.key_files:
            content += "## 🔍 **Key Files**\n"
            for file_info in self.status.key_files:
                if isinstance(file_info, dict):
                    content += f"- `{file_info['path']}` - {file_info.get('description', '')}\n"
                else:
                    content += f"- `{file_info}`\n"
            content += "\n"
        
        if self.status.context_anchors:
            content += "## 🎯 **Context Anchors**\n"
            for anchor in sorted(self.status.context_anchors, key=lambda x: x.priority):
                priority_emoji = "🔴" if anchor.priority == 1 else "🟡" if anchor.priority == 2 else "🟢"
                content += f"- {priority_emoji} **{anchor.key}**: {anchor.value}\n"
                content += f"  - {anchor.description}\n"
            content += "\n"
        
        content += f"---\n\n*Last Updated: {self.status.last_updated.strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return content
