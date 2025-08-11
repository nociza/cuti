"""
Task expansion and todo list generation system.
Automatically breaks down complex tasks into manageable subtasks.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class TaskCategory(Enum):
    """Task categories."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    PLANNING = "planning"


@dataclass
class SubTask:
    """Represents a subtask within a larger task."""
    id: str
    title: str
    description: str
    category: TaskCategory
    complexity: TaskComplexity
    estimated_time_hours: float
    dependencies: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: int = 0  # Lower number = higher priority
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass 
class TaskBreakdown:
    """Represents a complete task breakdown."""
    original_task: str
    overall_complexity: TaskComplexity
    estimated_total_hours: float
    subtasks: List[SubTask]
    execution_order: List[str]  # Subtask IDs in execution order
    parallel_groups: List[List[str]] = field(default_factory=list)  # Tasks that can run in parallel
    risk_factors: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class TaskExpansionEngine:
    """Engine for automatically expanding tasks into subtasks."""
    
    def __init__(self, base_dir: str = "~/.cuti"):
        self.base_dir = Path(base_dir).expanduser()
        self.templates_file = self.base_dir / "task_templates.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_templates()
        
    def _load_templates(self) -> None:
        """Load task breakdown templates."""
        if not self.templates_file.exists():
            self._create_default_templates()
        
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        except Exception as e:
            print(f"Error loading task templates: {e}")
            self.templates = {}
    
    def _create_default_templates(self) -> None:
        """Create default task breakdown templates."""
        templates = {
            "web_application": {
                "keywords": ["web app", "website", "web application", "frontend", "backend", "full-stack"],
                "subtasks": [
                    {
                        "title": "Requirements Analysis",
                        "category": "planning",
                        "complexity": "moderate", 
                        "estimated_time_hours": 4,
                        "description": "Analyze and document detailed requirements",
                        "deliverables": ["Requirements document", "User stories", "Acceptance criteria"],
                        "priority": 1
                    },
                    {
                        "title": "Architecture Design",
                        "category": "planning",
                        "complexity": "complex",
                        "estimated_time_hours": 8,
                        "description": "Design system architecture and technical specifications",
                        "deliverables": ["Architecture diagram", "Technology stack decision", "Database schema"],
                        "dependencies": ["Requirements Analysis"],
                        "priority": 2
                    },
                    {
                        "title": "Development Environment Setup",
                        "category": "development", 
                        "complexity": "moderate",
                        "estimated_time_hours": 3,
                        "description": "Set up development environment and tooling",
                        "deliverables": ["Configured development environment", "Build scripts", "Linting setup"],
                        "priority": 2
                    },
                    {
                        "title": "Backend Development",
                        "category": "development",
                        "complexity": "complex",
                        "estimated_time_hours": 24,
                        "description": "Implement backend APIs and business logic",
                        "deliverables": ["REST APIs", "Database models", "Authentication system"],
                        "dependencies": ["Architecture Design", "Development Environment Setup"],
                        "priority": 3
                    },
                    {
                        "title": "Frontend Development", 
                        "category": "development",
                        "complexity": "complex",
                        "estimated_time_hours": 20,
                        "description": "Implement user interface and client-side functionality",
                        "deliverables": ["User interface components", "Client-side routing", "State management"],
                        "dependencies": ["Architecture Design", "Development Environment Setup"],
                        "priority": 3
                    },
                    {
                        "title": "Integration Testing",
                        "category": "testing",
                        "complexity": "moderate",
                        "estimated_time_hours": 8,
                        "description": "Test integration between frontend and backend",
                        "deliverables": ["Integration test suite", "Test reports"],
                        "dependencies": ["Backend Development", "Frontend Development"],
                        "priority": 4
                    },
                    {
                        "title": "Deployment Setup",
                        "category": "deployment", 
                        "complexity": "moderate",
                        "estimated_time_hours": 6,
                        "description": "Set up deployment pipeline and infrastructure",
                        "deliverables": ["Deployment scripts", "CI/CD pipeline", "Production environment"],
                        "priority": 5
                    }
                ]
            },
            
            "api_development": {
                "keywords": ["api", "rest api", "graphql", "microservice", "service"],
                "subtasks": [
                    {
                        "title": "API Design",
                        "category": "planning",
                        "complexity": "moderate",
                        "estimated_time_hours": 6,
                        "description": "Design API endpoints and data models",
                        "deliverables": ["API specification", "OpenAPI/Swagger docs", "Data models"],
                        "priority": 1
                    },
                    {
                        "title": "Authentication & Authorization",
                        "category": "security",
                        "complexity": "complex",
                        "estimated_time_hours": 8,
                        "description": "Implement authentication and authorization mechanisms",
                        "deliverables": ["Auth system", "JWT tokens", "Permission system"],
                        "priority": 2
                    },
                    {
                        "title": "Core API Implementation",
                        "category": "development",
                        "complexity": "complex",
                        "estimated_time_hours": 16,
                        "description": "Implement core API endpoints and business logic", 
                        "deliverables": ["API endpoints", "Business logic", "Database integration"],
                        "dependencies": ["API Design"],
                        "priority": 3
                    },
                    {
                        "title": "Input Validation & Error Handling",
                        "category": "development",
                        "complexity": "moderate",
                        "estimated_time_hours": 4,
                        "description": "Implement robust input validation and error handling",
                        "deliverables": ["Validation middleware", "Error handlers", "Status codes"],
                        "dependencies": ["Core API Implementation"],
                        "priority": 4
                    },
                    {
                        "title": "API Testing",
                        "category": "testing", 
                        "complexity": "moderate",
                        "estimated_time_hours": 8,
                        "description": "Create comprehensive API test suite",
                        "deliverables": ["Unit tests", "Integration tests", "API documentation tests"],
                        "dependencies": ["Core API Implementation"],
                        "priority": 4
                    },
                    {
                        "title": "Performance Optimization",
                        "category": "performance",
                        "complexity": "moderate",
                        "estimated_time_hours": 6,
                        "description": "Optimize API performance and implement caching",
                        "deliverables": ["Performance benchmarks", "Caching system", "Query optimization"],
                        "dependencies": ["API Testing"],
                        "priority": 5
                    },
                    {
                        "title": "API Documentation",
                        "category": "documentation",
                        "complexity": "simple",
                        "estimated_time_hours": 4,
                        "description": "Create comprehensive API documentation",
                        "deliverables": ["API docs", "Usage examples", "Integration guides"],
                        "priority": 5
                    }
                ]
            },
            
            "testing_implementation": {
                "keywords": ["test", "testing", "unit test", "integration test", "e2e test", "test suite"],
                "subtasks": [
                    {
                        "title": "Test Strategy Planning",
                        "category": "planning",
                        "complexity": "moderate",
                        "estimated_time_hours": 3,
                        "description": "Define comprehensive testing strategy and approach",
                        "deliverables": ["Test strategy document", "Test types definition", "Coverage targets"],
                        "priority": 1
                    },
                    {
                        "title": "Test Environment Setup",
                        "category": "development",
                        "complexity": "moderate", 
                        "estimated_time_hours": 4,
                        "description": "Set up testing frameworks and infrastructure",
                        "deliverables": ["Test framework configuration", "Test database setup", "CI integration"],
                        "priority": 2
                    },
                    {
                        "title": "Unit Test Implementation",
                        "category": "testing",
                        "complexity": "complex",
                        "estimated_time_hours": 16,
                        "description": "Implement comprehensive unit tests for all components",
                        "deliverables": ["Unit test suite", "Mock implementations", "Test utilities"],
                        "dependencies": ["Test Environment Setup"],
                        "priority": 3
                    },
                    {
                        "title": "Integration Test Implementation",
                        "category": "testing", 
                        "complexity": "complex",
                        "estimated_time_hours": 12,
                        "description": "Implement integration tests for component interactions",
                        "deliverables": ["Integration test suite", "Test data fixtures", "API tests"],
                        "dependencies": ["Unit Test Implementation"],
                        "priority": 4
                    },
                    {
                        "title": "End-to-End Test Implementation",
                        "category": "testing",
                        "complexity": "complex",
                        "estimated_time_hours": 10,
                        "description": "Implement end-to-end tests for complete workflows",
                        "deliverables": ["E2E test suite", "Test scenarios", "Browser automation"],
                        "dependencies": ["Integration Test Implementation"],
                        "priority": 5
                    },
                    {
                        "title": "Test Coverage Analysis",
                        "category": "testing",
                        "complexity": "simple",
                        "estimated_time_hours": 2,
                        "description": "Analyze test coverage and identify gaps",
                        "deliverables": ["Coverage reports", "Gap analysis", "Improvement recommendations"],
                        "dependencies": ["End-to-End Test Implementation"],
                        "priority": 6
                    }
                ]
            },
            
            "security_audit": {
                "keywords": ["security", "audit", "vulnerability", "penetration test", "security review"],
                "subtasks": [
                    {
                        "title": "Security Scope Definition",
                        "category": "planning",
                        "complexity": "moderate",
                        "estimated_time_hours": 3,
                        "description": "Define scope and methodology for security audit",
                        "deliverables": ["Audit scope document", "Security checklist", "Risk assessment framework"],
                        "priority": 1
                    },
                    {
                        "title": "Automated Security Scanning",
                        "category": "security",
                        "complexity": "moderate",
                        "estimated_time_hours": 4,
                        "description": "Run automated security scans and dependency checks",
                        "deliverables": ["Vulnerability scan results", "Dependency audit", "Security tool reports"],
                        "priority": 2
                    },
                    {
                        "title": "Code Security Review",
                        "category": "security",
                        "complexity": "complex",
                        "estimated_time_hours": 12,
                        "description": "Manual review of code for security vulnerabilities",
                        "deliverables": ["Code review findings", "Security issue catalog", "Risk ratings"],
                        "dependencies": ["Security Scope Definition"],
                        "priority": 3
                    },
                    {
                        "title": "Authentication & Authorization Audit",
                        "category": "security",
                        "complexity": "complex",
                        "estimated_time_hours": 6,
                        "description": "Audit authentication and authorization mechanisms",
                        "deliverables": ["Auth security assessment", "Permission model review", "Access control findings"],
                        "priority": 3
                    },
                    {
                        "title": "Data Protection Review",
                        "category": "security", 
                        "complexity": "moderate",
                        "estimated_time_hours": 4,
                        "description": "Review data handling and protection measures",
                        "deliverables": ["Data flow analysis", "Encryption assessment", "Privacy compliance review"],
                        "priority": 4
                    },
                    {
                        "title": "Security Remediation Plan",
                        "category": "planning",
                        "complexity": "moderate",
                        "estimated_time_hours": 4,
                        "description": "Create plan to address identified security issues",
                        "deliverables": ["Remediation roadmap", "Priority matrix", "Implementation timeline"],
                        "dependencies": ["Code Security Review", "Authentication & Authorization Audit", "Data Protection Review"],
                        "priority": 5
                    }
                ]
            }
        }
        
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
            self.templates = templates
        except Exception as e:
            print(f"Error saving task templates: {e}")
            self.templates = templates

    def analyze_task_complexity(self, task_description: str) -> Tuple[TaskComplexity, List[str]]:
        """Analyze task complexity and identify relevant keywords."""
        task_lower = task_description.lower()
        
        # Complexity indicators
        complex_indicators = [
            "architecture", "system design", "full-stack", "microservices", 
            "enterprise", "scalable", "distributed", "cloud", "machine learning"
        ]
        
        moderate_indicators = [
            "api", "database", "authentication", "testing", "deployment", 
            "integration", "optimization", "refactoring"
        ]
        
        simple_indicators = [
            "fix bug", "add feature", "update", "documentation", "config", 
            "small change", "minor"
        ]
        
        # Count indicators
        complex_count = sum(1 for indicator in complex_indicators if indicator in task_lower)
        moderate_count = sum(1 for indicator in moderate_indicators if indicator in task_lower)
        simple_count = sum(1 for indicator in simple_indicators if indicator in task_lower)
        
        # Determine complexity
        if complex_count >= 2 or "full-stack" in task_lower or "architecture" in task_lower:
            complexity = TaskComplexity.VERY_COMPLEX
        elif complex_count >= 1 or moderate_count >= 3:
            complexity = TaskComplexity.COMPLEX
        elif moderate_count >= 1:
            complexity = TaskComplexity.MODERATE
        else:
            complexity = TaskComplexity.SIMPLE
        
        # Extract keywords
        all_indicators = complex_indicators + moderate_indicators + simple_indicators
        found_keywords = [indicator for indicator in all_indicators if indicator in task_lower]
        
        return complexity, found_keywords

    def match_template(self, task_description: str, keywords: List[str]) -> Optional[str]:
        """Find the best matching template for a task."""
        task_lower = task_description.lower()
        best_match = None
        best_score = 0
        
        for template_name, template_data in self.templates.items():
            template_keywords = template_data.get("keywords", [])
            
            # Calculate match score
            score = 0
            for keyword in template_keywords:
                if keyword in task_lower:
                    score += 2  # Direct match in task description
                if keyword in keywords:
                    score += 1  # Match in extracted keywords
            
            # Normalize by number of template keywords
            if template_keywords:
                score = score / len(template_keywords)
            
            if score > best_score and score > 0.3:  # Minimum threshold
                best_match = template_name
                best_score = score
        
        return best_match

    def expand_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> TaskBreakdown:
        """Expand a task into subtasks."""
        if context is None:
            context = {}
        
        # Analyze task
        complexity, keywords = self.analyze_task_complexity(task_description)
        
        # Find matching template
        template_name = self.match_template(task_description, keywords)
        
        subtasks = []
        execution_order = []
        total_hours = 0.0
        
        if template_name and template_name in self.templates:
            # Use template
            template = self.templates[template_name]
            template_subtasks = template.get("subtasks", [])
            
            for i, template_subtask in enumerate(template_subtasks):
                subtask_id = f"task_{i+1:03d}"
                
                subtask = SubTask(
                    id=subtask_id,
                    title=template_subtask["title"],
                    description=template_subtask["description"],
                    category=TaskCategory(template_subtask["category"]),
                    complexity=TaskComplexity(template_subtask["complexity"]),
                    estimated_time_hours=template_subtask["estimated_time_hours"],
                    dependencies=template_subtask.get("dependencies", []),
                    deliverables=template_subtask.get("deliverables", []),
                    priority=template_subtask.get("priority", i+1)
                )
                
                subtasks.append(subtask)
                total_hours += subtask.estimated_time_hours
                
                # Build execution order based on dependencies and priority
                if not subtask.dependencies:
                    execution_order.append(subtask_id)
        
        else:
            # Generate generic subtasks based on complexity
            generic_subtasks = self._generate_generic_subtasks(task_description, complexity)
            
            for i, generic_subtask in enumerate(generic_subtasks):
                subtask_id = f"task_{i+1:03d}"
                
                subtask = SubTask(
                    id=subtask_id,
                    title=generic_subtask["title"],
                    description=generic_subtask["description"],
                    category=TaskCategory(generic_subtask["category"]),
                    complexity=generic_subtask["complexity"],
                    estimated_time_hours=generic_subtask["estimated_time_hours"],
                    priority=i+1
                )
                
                subtasks.append(subtask)
                total_hours += subtask.estimated_time_hours
                execution_order.append(subtask_id)
        
        # Resolve execution order based on dependencies
        resolved_order = self._resolve_execution_order(subtasks)
        
        # Identify parallel groups
        parallel_groups = self._identify_parallel_tasks(subtasks)
        
        # Generate risk factors and success metrics
        risk_factors = self._identify_risk_factors(complexity, template_name)
        success_metrics = self._generate_success_metrics(task_description, subtasks)
        
        return TaskBreakdown(
            original_task=task_description,
            overall_complexity=complexity,
            estimated_total_hours=total_hours,
            subtasks=subtasks,
            execution_order=resolved_order,
            parallel_groups=parallel_groups,
            risk_factors=risk_factors,
            success_metrics=success_metrics
        )

    def _generate_generic_subtasks(self, task_description: str, complexity: TaskComplexity) -> List[Dict[str, Any]]:
        """Generate generic subtasks when no template matches."""
        base_subtasks = [
            {
                "title": "Task Analysis and Planning",
                "description": "Analyze requirements and create detailed plan",
                "category": "planning",
                "complexity": "simple",
                "estimated_time_hours": 2.0
            },
            {
                "title": "Implementation",
                "description": f"Implement the main functionality: {task_description}",
                "category": "development", 
                "complexity": complexity.value,
                "estimated_time_hours": self._estimate_implementation_hours(complexity)
            },
            {
                "title": "Testing and Validation",
                "description": "Test the implementation and validate results",
                "category": "testing",
                "complexity": "moderate",
                "estimated_time_hours": self._estimate_implementation_hours(complexity) * 0.3
            },
            {
                "title": "Documentation",
                "description": "Document the changes and update relevant documentation",
                "category": "documentation",
                "complexity": "simple", 
                "estimated_time_hours": 1.0
            }
        ]
        
        # Add additional subtasks based on complexity
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
            base_subtasks.insert(1, {
                "title": "Architecture and Design",
                "description": "Design system architecture and technical approach",
                "category": "planning",
                "complexity": "moderate",
                "estimated_time_hours": 4.0
            })
            
            base_subtasks.append({
                "title": "Performance Optimization",
                "description": "Optimize performance and conduct load testing",
                "category": "performance",
                "complexity": "moderate",
                "estimated_time_hours": 3.0
            })
        
        if complexity == TaskComplexity.VERY_COMPLEX:
            base_subtasks.append({
                "title": "Security Review",
                "description": "Conduct security review and address vulnerabilities",
                "category": "security",
                "complexity": "moderate",
                "estimated_time_hours": 4.0
            })
        
        return base_subtasks

    def _estimate_implementation_hours(self, complexity: TaskComplexity) -> float:
        """Estimate implementation hours based on complexity."""
        hours_map = {
            TaskComplexity.SIMPLE: 2.0,
            TaskComplexity.MODERATE: 8.0,
            TaskComplexity.COMPLEX: 20.0,
            TaskComplexity.VERY_COMPLEX: 40.0
        }
        return hours_map.get(complexity, 8.0)

    def _resolve_execution_order(self, subtasks: List[SubTask]) -> List[str]:
        """Resolve execution order considering dependencies."""
        ordered_tasks = []
        remaining_tasks = {task.id: task for task in subtasks}
        
        while remaining_tasks:
            # Find tasks with no remaining dependencies
            ready_tasks = []
            for task_id, task in remaining_tasks.items():
                if not task.dependencies or all(dep not in remaining_tasks for dep in task.dependencies):
                    ready_tasks.append((task_id, task))
            
            if not ready_tasks:
                # Circular dependency or orphaned task - add by priority
                ready_tasks = [(task_id, task) for task_id, task in remaining_tasks.items()]
            
            # Sort by priority and add to order
            ready_tasks.sort(key=lambda x: x[1].priority)
            
            for task_id, task in ready_tasks[:1]:  # Add one at a time
                ordered_tasks.append(task_id)
                del remaining_tasks[task_id]
                break
        
        return ordered_tasks

    def _identify_parallel_tasks(self, subtasks: List[SubTask]) -> List[List[str]]:
        """Identify tasks that can be executed in parallel."""
        parallel_groups = []
        task_dict = {task.id: task for task in subtasks}
        
        # Group tasks by dependency level
        levels = {}
        for task in subtasks:
            level = 0
            if task.dependencies:
                # Find the maximum level of dependencies
                for dep in task.dependencies:
                    if dep in task_dict:
                        dep_level = levels.get(dep, 0)
                        level = max(level, dep_level + 1)
            levels[task.id] = level
        
        # Group tasks at the same level
        level_groups = {}
        for task_id, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(task_id)
        
        # Only include groups with more than one task
        for level, task_ids in level_groups.items():
            if len(task_ids) > 1:
                parallel_groups.append(task_ids)
        
        return parallel_groups

    def _identify_risk_factors(self, complexity: TaskComplexity, template_name: Optional[str]) -> List[str]:
        """Identify potential risk factors for the task."""
        risks = []
        
        # Complexity-based risks
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
            risks.extend([
                "High complexity may lead to scope creep",
                "Integration challenges between components",
                "Potential performance bottlenecks"
            ])
        
        # Template-specific risks
        if template_name == "web_application":
            risks.extend([
                "Browser compatibility issues",
                "Security vulnerabilities in authentication",
                "Database performance under load"
            ])
        elif template_name == "api_development":
            risks.extend([
                "API versioning and backward compatibility",
                "Rate limiting and abuse prevention",
                "Data validation edge cases"
            ])
        elif template_name == "security_audit":
            risks.extend([
                "Discovery of critical vulnerabilities",
                "False positive results requiring investigation",
                "Compliance requirement changes"
            ])
        
        # General risks
        risks.extend([
            "Dependency conflicts or version issues",
            "Inadequate testing leading to bugs",
            "Timeline delays due to unforeseen complications"
        ])
        
        return risks

    def _generate_success_metrics(self, task_description: str, subtasks: List[SubTask]) -> List[str]:
        """Generate success metrics for the task."""
        metrics = [
            "All subtasks completed within estimated timeframe",
            "All deliverables produced and reviewed",
            "Quality gates passed (testing, code review, etc.)"
        ]
        
        # Add specific metrics based on categories
        categories = set(task.category for task in subtasks)
        
        if TaskCategory.TESTING in categories:
            metrics.append("Test coverage target achieved (>80%)")
            metrics.append("All critical test cases passing")
        
        if TaskCategory.PERFORMANCE in categories:
            metrics.append("Performance benchmarks met")
            metrics.append("Load testing completed successfully")
        
        if TaskCategory.SECURITY in categories:
            metrics.append("Security scan results reviewed and addressed")
            metrics.append("No high-risk vulnerabilities remaining")
        
        if TaskCategory.DOCUMENTATION in categories:
            metrics.append("Documentation complete and reviewed")
            metrics.append("Knowledge transfer completed")
        
        # Task-specific metrics
        task_lower = task_description.lower()
        if "api" in task_lower:
            metrics.append("API endpoints fully functional and tested")
            metrics.append("API documentation complete")
        
        if "deployment" in task_lower or "deploy" in task_lower:
            metrics.append("Deployment completed without issues")
            metrics.append("Production environment verified")
        
        return metrics

    def save_task_breakdown(self, breakdown: TaskBreakdown, file_path: Optional[str] = None) -> str:
        """Save task breakdown to file."""
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\-_\. ]', '_', breakdown.original_task)[:50]
            file_path = str(self.base_dir / f"breakdown_{safe_title}_{timestamp}.json")
        
        # Convert to serializable format
        breakdown_dict = {
            "original_task": breakdown.original_task,
            "overall_complexity": breakdown.overall_complexity.value,
            "estimated_total_hours": breakdown.estimated_total_hours,
            "execution_order": breakdown.execution_order,
            "parallel_groups": breakdown.parallel_groups,
            "risk_factors": breakdown.risk_factors,
            "success_metrics": breakdown.success_metrics,
            "created_at": breakdown.created_at.isoformat(),
            "subtasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "category": task.category.value,
                    "complexity": task.complexity.value,
                    "estimated_time_hours": task.estimated_time_hours,
                    "dependencies": task.dependencies,
                    "prerequisites": task.prerequisites,
                    "deliverables": task.deliverables,
                    "acceptance_criteria": task.acceptance_criteria,
                    "priority": task.priority,
                    "tags": task.tags,
                    "created_at": task.created_at.isoformat()
                }
                for task in breakdown.subtasks
            ]
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(breakdown_dict, f, indent=2, ensure_ascii=False)
            return file_path
        except Exception as e:
            print(f"Error saving task breakdown: {e}")
            return ""

    def load_task_breakdown(self, file_path: str) -> Optional[TaskBreakdown]:
        """Load task breakdown from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            subtasks = []
            for task_data in data.get("subtasks", []):
                subtask = SubTask(
                    id=task_data["id"],
                    title=task_data["title"],
                    description=task_data["description"],
                    category=TaskCategory(task_data["category"]),
                    complexity=TaskComplexity(task_data["complexity"]),
                    estimated_time_hours=task_data["estimated_time_hours"],
                    dependencies=task_data.get("dependencies", []),
                    prerequisites=task_data.get("prerequisites", []),
                    deliverables=task_data.get("deliverables", []),
                    acceptance_criteria=task_data.get("acceptance_criteria", []),
                    priority=task_data.get("priority", 0),
                    tags=task_data.get("tags", []),
                    created_at=datetime.fromisoformat(task_data.get("created_at", datetime.now().isoformat()))
                )
                subtasks.append(subtask)
            
            return TaskBreakdown(
                original_task=data["original_task"],
                overall_complexity=TaskComplexity(data["overall_complexity"]),
                estimated_total_hours=data["estimated_total_hours"],
                subtasks=subtasks,
                execution_order=data.get("execution_order", []),
                parallel_groups=data.get("parallel_groups", []),
                risk_factors=data.get("risk_factors", []),
                success_metrics=data.get("success_metrics", []),
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
            )
            
        except Exception as e:
            print(f"Error loading task breakdown: {e}")
            return None