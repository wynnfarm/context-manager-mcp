#!/usr/bin/env python3
"""
Command-line interface for context management
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add the context_manager to path
context_manager_path = Path(__file__).parent
if str(context_manager_path.parent) not in sys.path:
    sys.path.insert(0, str(context_manager_path.parent))

from context_manager.core import ContextManager
from context_manager.utils import (
    quick_status_check, 
    get_project_info, 
    create_status_file,
    create_context_script,
    create_makefile_targets
)


def main():
    parser = argparse.ArgumentParser(
        description="Context Manager - Maintain conversation context across projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  context-manager status          # Show current status
  context-manager init           # Initialize context for current project
  context-manager goal "Deploy app"  # Set current goal
  context-manager issue "Build failing"  # Add current issue
  context-manager next "Fix tests"  # Add next step
  context-manager anchor "API_KEY" "sk-123..."  # Add context anchor
  context-manager resolve "Build failing"  # Resolve an issue
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current project status')
    status_parser.add_argument('--project-root', help='Project root directory')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize context for current project')
    init_parser.add_argument('--project-name', help='Project name (defaults to directory name)')
    init_parser.add_argument('--project-root', help='Project root directory')
    init_parser.add_argument('--goal', help='Initial goal')
    
    # Goal command
    goal_parser = subparsers.add_parser('goal', help='Set current goal')
    goal_parser.add_argument('goal', help='Current goal')
    goal_parser.add_argument('--project-root', help='Project root directory')
    
    # Issue command
    issue_parser = subparsers.add_parser('issue', help='Add current issue')
    issue_parser.add_argument('problem', help='Problem description')
    issue_parser.add_argument('--location', help='Where the issue occurs')
    issue_parser.add_argument('--root-cause', help='Root cause of the issue')
    issue_parser.add_argument('--project-root', help='Project root directory')
    
    # Resolve command
    resolve_parser = subparsers.add_parser('resolve', help='Resolve an issue')
    resolve_parser.add_argument('problem', help='Problem to resolve')
    resolve_parser.add_argument('--project-root', help='Project root directory')
    
    # Next command
    next_parser = subparsers.add_parser('next', help='Add next step')
    next_parser.add_argument('step', help='Next step')
    next_parser.add_argument('--project-root', help='Project root directory')
    
    # Anchor command
    anchor_parser = subparsers.add_parser('anchor', help='Add context anchor')
    anchor_parser.add_argument('key', help='Anchor key')
    anchor_parser.add_argument('value', help='Anchor value')
    anchor_parser.add_argument('--description', help='Anchor description')
    anchor_parser.add_argument('--priority', type=int, choices=[1, 2, 3], default=1, 
                              help='Priority (1=high, 2=medium, 3=low)')
    anchor_parser.add_argument('--project-root', help='Project root directory')
    
    # Feature command
    feature_parser = subparsers.add_parser('feature', help='Add completed feature')
    feature_parser.add_argument('feature', help='Completed feature')
    feature_parser.add_argument('--project-root', help='Project root directory')
    
    # State command
    state_parser = subparsers.add_parser('state', help='Update current state')
    state_parser.add_argument('key', help='State key')
    state_parser.add_argument('value', help='State value')
    state_parser.add_argument('--project-root', help='Project root directory')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup context management for project')
    setup_parser.add_argument('--project-name', help='Project name (defaults to directory name)')
    setup_parser.add_argument('--project-root', help='Project root directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    project_root = args.project_root
    
    try:
        if args.command == 'status':
            print(quick_status_check(project_root))
            
        elif args.command == 'init':
            project_name = args.project_name or Path.cwd().name
            cm = ContextManager(project_name, project_root)
            if args.goal:
                cm.set_current_goal(args.goal)
            else:
                cm.set_current_goal("Initialize project context")
            print(f"✅ Context initialized for {project_name}")
            
        elif args.command == 'goal':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.set_current_goal(args.goal)
            print(f"✅ Goal set: {args.goal}")
            
        elif args.command == 'issue':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.add_current_issue(args.problem, args.location, args.root_cause)
            print(f"✅ Issue added: {args.problem}")
            
        elif args.command == 'resolve':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.resolve_issue(args.problem)
            print(f"✅ Issue resolved: {args.problem}")
            
        elif args.command == 'next':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.add_next_step(args.step)
            print(f"✅ Next step added: {args.step}")
            
        elif args.command == 'anchor':
            cm = ContextManager(Path.cwd().name, project_root)
            description = args.description or f"Context anchor for {args.key}"
            cm.add_context_anchor(args.key, args.value, description, args.priority)
            print(f"✅ Context anchor added: {args.key}")
            
        elif args.command == 'feature':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.add_completed_feature(args.feature)
            print(f"✅ Feature completed: {args.feature}")
            
        elif args.command == 'state':
            cm = ContextManager(Path.cwd().name, project_root)
            cm.update_current_state(args.key, args.value)
            print(f"✅ State updated: {args.key} = {args.value}")
            
        elif args.command == 'setup':
            project_name = args.project_name or Path.cwd().name
            
            # Create status file
            status_file = create_status_file(project_name, project_root)
            print(f"✅ Status file created: {status_file}")
            
            # Create context check script
            script_file = create_context_script(project_root)
            print(f"✅ Context script created: {script_file}")
            
            # Add Makefile targets
            makefile = create_makefile_targets(project_root)
            print(f"✅ Makefile targets added: {makefile}")
            
            # Initialize context manager
            cm = ContextManager(project_name, project_root)
            cm.set_current_goal("Setup context management")
            print(f"✅ Context manager initialized for {project_name}")
            
            print("\n🎯 Context management setup complete!")
            print("Use 'context-manager status' to check status")
            print("Use 'make context-status' for quick checks")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
