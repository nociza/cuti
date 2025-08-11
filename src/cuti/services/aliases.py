"""
Prompt alias management system.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class PromptAliasManager:
    """Manages prompt aliases for common tasks."""

    def __init__(self, base_dir: str = "~/.cuti"):
        self.base_dir = Path(base_dir).expanduser()
        self.aliases_file = self.base_dir / "aliases.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize with default aliases
        self._ensure_default_aliases()

    def _ensure_default_aliases(self) -> None:
        """Create default aliases if they don't exist."""
        if not self.aliases_file.exists():
            self._create_default_aliases()
        else:
            # Load existing and add any missing defaults
            existing = self._load_aliases()
            defaults = self._get_default_aliases()
            
            # Add missing defaults
            for alias_name, alias_data in defaults.items():
                if alias_name not in existing:
                    existing[alias_name] = alias_data
            
            self._save_aliases(existing)

    def _get_default_aliases(self) -> Dict[str, Any]:
        """Get default aliases for common scenarios."""
        return {
            "explore-codebase": {
                "name": "explore-codebase",
                "description": "Thoroughly explore and document the codebase structure",
                "content": """Thoroughly explore this codebase and provide a comprehensive analysis:

1. **Architecture Overview**: Analyze the overall structure, design patterns, and architectural decisions
2. **Key Components**: Identify main modules, classes, and their responsibilities  
3. **Data Flow**: Trace how data moves through the system
4. **Dependencies**: List external dependencies and their purposes
5. **Entry Points**: Identify main entry points and CLI commands
6. **Configuration**: Document configuration files and environment variables
7. **Testing**: Analyze test structure and coverage
8. **Documentation**: Review existing documentation and identify gaps

Please create a detailed markdown report with:
- Executive summary
- Directory structure breakdown
- Component interaction diagrams (text-based)
- Key findings and recommendations
- Areas for improvement

Focus on understanding the codebase deeply enough to make informed development decisions.""",
                "working_directory": ".",
                "context_files": ["README.md", "pyproject.toml", "package.json"],
                "created_at": datetime.now().isoformat()
            },
            
            "document-api": {
                "name": "document-api",
                "description": "Generate comprehensive API documentation",
                "content": """Generate comprehensive API documentation for this project:

1. **API Overview**: High-level description of the API purpose and capabilities
2. **Authentication**: Document authentication methods if applicable
3. **Endpoints**: For each endpoint document:
   - HTTP method and URL
   - Request parameters and body schema
   - Response schema and status codes
   - Example requests/responses
4. **Error Handling**: Document error codes and formats
5. **Rate Limiting**: Document any rate limiting policies
6. **SDKs/Client Libraries**: List available client libraries
7. **Changelog**: Recent API changes

Generate documentation in OpenAPI/Swagger format where possible, plus human-readable markdown documentation.

Focus on creating documentation that developers can immediately use to integrate with the API.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "security-audit": {
                "name": "security-audit", 
                "description": "Perform comprehensive security audit",
                "content": """Perform a comprehensive security audit of this codebase:

1. **Input Validation**: Check for proper validation of user inputs
2. **Authentication & Authorization**: Review auth mechanisms for vulnerabilities
3. **Data Protection**: Analyze how sensitive data is handled and stored
4. **Dependency Security**: Check for known vulnerabilities in dependencies
5. **Code Injection**: Look for SQL injection, XSS, and other injection risks
6. **Error Handling**: Ensure errors don't leak sensitive information
7. **Logging & Monitoring**: Review logging practices for security events
8. **Configuration Security**: Check for hardcoded secrets and insecure defaults
9. **Network Security**: Analyze network communication security
10. **File System Security**: Review file operations for security issues

Provide:
- Risk assessment (Critical/High/Medium/Low)
- Specific vulnerabilities found with code examples
- Remediation recommendations
- Security best practices checklist

Focus on identifying actionable security improvements.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "optimize-performance": {
                "name": "optimize-performance",
                "description": "Analyze and optimize application performance",
                "content": """Analyze and optimize the performance of this application:

1. **Performance Profiling**: Identify performance bottlenecks
2. **Memory Usage**: Analyze memory consumption and leaks
3. **CPU Optimization**: Identify CPU-intensive operations
4. **Database Performance**: Optimize queries and database interactions
5. **Caching Strategy**: Implement or improve caching mechanisms
6. **Network Optimization**: Reduce network latency and bandwidth usage
7. **Code Optimization**: Identify inefficient algorithms and data structures
8. **Resource Management**: Optimize file I/O and resource usage
9. **Scaling Considerations**: Analyze scalability limitations
10. **Monitoring**: Set up performance monitoring and alerting

Provide:
- Performance benchmarks before/after optimizations
- Specific optimization recommendations with code examples
- Monitoring and alerting setup
- Performance testing strategy

Focus on measurable improvements that enhance user experience.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "write-tests": {
                "name": "write-tests", 
                "description": "Create comprehensive test suite",
                "content": """Create a comprehensive test suite for this project:

1. **Test Strategy**: Define testing approach (unit, integration, e2e)
2. **Test Framework**: Set up or enhance testing framework
3. **Unit Tests**: Write unit tests for individual components
4. **Integration Tests**: Create integration tests for component interactions
5. **API Tests**: Write tests for API endpoints if applicable
6. **Edge Cases**: Test error conditions and edge cases
7. **Test Data**: Set up test fixtures and mock data
8. **Test Coverage**: Achieve high test coverage (>80%)
9. **CI/CD Integration**: Integrate tests into CI/CD pipeline
10. **Test Documentation**: Document testing procedures

Provide:
- Test files with comprehensive coverage
- Testing configuration and setup
- Mock/stub implementations where needed
- Test running instructions
- Coverage reports

Focus on creating maintainable tests that catch regressions and enable confident refactoring.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "refactor-code": {
                "name": "refactor-code",
                "description": "Refactor code for better maintainability",
                "content": """Refactor this codebase to improve maintainability and code quality:

1. **Code Analysis**: Identify code smells, duplications, and anti-patterns
2. **Architecture Review**: Assess current architecture and suggest improvements
3. **SOLID Principles**: Apply SOLID principles where appropriate
4. **Design Patterns**: Implement appropriate design patterns
5. **Code Organization**: Improve file and module organization
6. **Naming Conventions**: Ensure consistent and meaningful naming
7. **Function Decomposition**: Break down large functions into smaller ones
8. **Error Handling**: Improve error handling and logging
9. **Documentation**: Add inline documentation and comments
10. **Code Style**: Ensure consistent code style and formatting

Provide:
- Refactored code with clear explanations of changes
- Before/after comparisons for major refactoring
- Migration guide if breaking changes are introduced
- Code quality metrics improvement
- Updated documentation

Focus on improving code readability, maintainability, and extensibility without changing functionality.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "setup-cicd": {
                "name": "setup-cicd",
                "description": "Set up CI/CD pipeline",
                "content": """Set up a comprehensive CI/CD pipeline for this project:

1. **CI Configuration**: Set up continuous integration
   - Automated testing on multiple environments
   - Code quality checks (linting, formatting)
   - Security scanning
   - Dependency vulnerability checks
2. **Build Process**: Optimize build configuration
   - Build optimization for speed
   - Artifact creation and storage
   - Multi-platform builds if needed
3. **Deployment Strategy**: Implement deployment pipeline
   - Environment-specific configurations
   - Blue-green or rolling deployments
   - Database migrations
   - Health checks
4. **Monitoring**: Set up monitoring and alerting
   - Application performance monitoring
   - Error tracking
   - Log aggregation
5. **Rollback Strategy**: Implement rollback mechanisms

Provide:
- CI/CD configuration files (GitHub Actions, GitLab CI, etc.)
- Deployment scripts and configurations
- Environment setup documentation
- Monitoring and alerting setup
- Rollback procedures

Focus on creating a reliable, automated pipeline that enables fast and safe deployments.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "add-logging": {
                "name": "add-logging",
                "description": "Implement comprehensive logging system",
                "content": """Implement a comprehensive logging system:

1. **Logging Strategy**: Define logging levels and categories
2. **Structured Logging**: Implement structured logging with JSON format
3. **Log Aggregation**: Set up centralized log collection
4. **Performance Logging**: Add performance metrics and tracing
5. **Error Logging**: Comprehensive error logging with context
6. **Security Logging**: Log security-relevant events
7. **Log Rotation**: Implement log rotation and retention policies
8. **Log Analysis**: Set up log analysis and alerting
9. **Debugging Support**: Add debug logging for troubleshooting
10. **Compliance**: Ensure logging meets compliance requirements

Provide:
- Logging configuration and setup
- Logger implementations throughout codebase
- Log aggregation setup (ELK stack, etc.)
- Monitoring dashboards for log data
- Log retention and rotation policies

Focus on creating actionable logs that aid in debugging, monitoring, and compliance.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "fix-bugs": {
                "name": "fix-bugs",
                "description": "Systematically identify and fix bugs",
                "content": """Systematically identify and fix bugs in this codebase:

1. **Bug Discovery**: Find potential bugs through:
   - Static code analysis
   - Code review
   - Test case analysis
   - Error log analysis
2. **Bug Categorization**: Classify bugs by:
   - Severity (critical, high, medium, low)
   - Type (logic, performance, security, UI)
   - Component affected
3. **Root Cause Analysis**: For each bug:
   - Identify root cause
   - Understand impact
   - Plan fix strategy
4. **Bug Fixes**: Implement fixes with:
   - Minimal code changes
   - Comprehensive testing
   - Documentation updates
5. **Prevention**: Add measures to prevent similar bugs

Provide:
- List of identified bugs with severity ratings
- Fixed code with explanations
- Test cases to verify fixes
- Prevention strategies (linting rules, tests, etc.)
- Regression testing plan

Focus on fixing bugs thoroughly while preventing future occurrences.""",
                "working_directory": ".",
                "context_files": [],
                "created_at": datetime.now().isoformat()
            },
            
            "modernize-stack": {
                "name": "modernize-stack",
                "description": "Modernize technology stack and dependencies",
                "content": """Modernize the technology stack and update dependencies:

1. **Dependency Audit**: Analyze current dependencies
   - Identify outdated packages
   - Check for security vulnerabilities
   - Find abandoned or deprecated libraries
2. **Technology Assessment**: Evaluate current technology choices
   - Language version upgrades
   - Framework updates
   - Tool modernization
3. **Migration Planning**: Plan modernization strategy
   - Prioritize updates by impact and risk
   - Plan backward compatibility
   - Create migration timeline
4. **Implementation**: Execute modernization
   - Update dependencies safely
   - Refactor code for new versions
   - Update configuration and build processes
5. **Testing**: Ensure compatibility
   - Regression testing
   - Performance testing
   - Integration testing

Provide:
- Dependency update plan with risk assessment
- Modernized configuration files
- Updated code for new dependency versions
- Migration guide and changelog
- Testing strategy for validation

Focus on improving security, performance, and maintainability through strategic modernization.""",
                "working_directory": ".",
                "context_files": ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml"],
                "created_at": datetime.now().isoformat()
            }
        }

    def _create_default_aliases(self) -> None:
        """Create default aliases file."""
        defaults = self._get_default_aliases()
        self._save_aliases(defaults)

    def _load_aliases(self) -> Dict[str, Any]:
        """Load aliases from storage."""
        if not self.aliases_file.exists():
            return {}
        
        try:
            with open(self.aliases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading aliases: {e}")
            return {}

    def _save_aliases(self, aliases: Dict[str, Any]) -> bool:
        """Save aliases to storage."""
        try:
            with open(self.aliases_file, 'w', encoding='utf-8') as f:
                json.dump(aliases, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving aliases: {e}")
            return False

    def create_alias(
        self, 
        name: str, 
        content: str, 
        description: str = "", 
        working_directory: str = ".",
        context_files: List[str] = None
    ) -> bool:
        """Create a new alias."""
        if context_files is None:
            context_files = []
            
        aliases = self._load_aliases()
        
        if name in aliases:
            return False  # Alias already exists
        
        aliases[name] = {
            "name": name,
            "content": content,
            "description": description,
            "working_directory": working_directory,
            "context_files": context_files,
            "created_at": datetime.now().isoformat()
        }
        
        return self._save_aliases(aliases)

    def get_alias(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an alias by name."""
        aliases = self._load_aliases()
        return aliases.get(name)

    def list_aliases(self) -> List[Dict[str, Any]]:
        """List all aliases."""
        aliases = self._load_aliases()
        return list(aliases.values())

    def delete_alias(self, name: str) -> bool:
        """Delete an alias."""
        aliases = self._load_aliases()
        
        if name not in aliases:
            return False
        
        del aliases[name]
        return self._save_aliases(aliases)

    def resolve_alias(self, input_text: str, current_working_dir: str = ".") -> str:
        """Resolve alias to actual prompt content, with variable substitution."""
        # Check if input matches an alias name exactly
        alias = self.get_alias(input_text)
        if alias:
            content = alias['content']
            
            # Perform variable substitution
            content = self._substitute_variables(content, current_working_dir, alias)
            
            return content
        
        # Check if input contains alias references (e.g., @alias-name)
        content = input_text
        alias_pattern = r'@([a-zA-Z0-9_-]+)'
        
        def replace_alias_ref(match):
            alias_name = match.group(1)
            referenced_alias = self.get_alias(alias_name)
            if referenced_alias:
                alias_content = referenced_alias['content']
                return self._substitute_variables(alias_content, current_working_dir, referenced_alias)
            return match.group(0)  # Return original if alias not found
        
        resolved_content = re.sub(alias_pattern, replace_alias_ref, content)
        return resolved_content

    def _substitute_variables(self, content: str, working_dir: str, alias: Dict[str, Any]) -> str:
        """Substitute variables in alias content."""
        # Built-in variables
        variables = {
            'WORKING_DIR': working_dir,
            'PROJECT_NAME': Path(working_dir).resolve().name,
            'DATE': datetime.now().strftime('%Y-%m-%d'),
            'DATETIME': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Substitute variables in format ${VARIABLE_NAME}
        def replace_var(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))
        
        content = re.sub(r'\$\{([^}]+)\}', replace_var, content)
        
        return content

    def search_aliases(self, query: str) -> List[Dict[str, Any]]:
        """Search aliases by name, description, or content."""
        aliases = self.list_aliases()
        query_lower = query.lower()
        
        results = []
        for alias in aliases:
            if (query_lower in alias['name'].lower() or
                query_lower in alias.get('description', '').lower() or
                query_lower in alias['content'].lower()):
                results.append(alias)
        
        return results

    def update_alias(
        self, 
        name: str, 
        content: Optional[str] = None,
        description: Optional[str] = None,
        working_directory: Optional[str] = None,
        context_files: Optional[List[str]] = None
    ) -> bool:
        """Update an existing alias."""
        aliases = self._load_aliases()
        
        if name not in aliases:
            return False
        
        alias = aliases[name]
        
        if content is not None:
            alias['content'] = content
        if description is not None:
            alias['description'] = description
        if working_directory is not None:
            alias['working_directory'] = working_directory
        if context_files is not None:
            alias['context_files'] = context_files
        
        alias['updated_at'] = datetime.now().isoformat()
        
        return self._save_aliases(aliases)

    def export_aliases(self, file_path: str) -> bool:
        """Export aliases to a file."""
        aliases = self._load_aliases()
        try:
            export_path = Path(file_path)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(aliases, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting aliases: {e}")
            return False

    def import_aliases(self, file_path: str, overwrite: bool = False) -> bool:
        """Import aliases from a file."""
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                print(f"Import file not found: {file_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_aliases = json.load(f)
            
            existing_aliases = self._load_aliases()
            
            for name, alias_data in imported_aliases.items():
                if name not in existing_aliases or overwrite:
                    existing_aliases[name] = alias_data
            
            return self._save_aliases(existing_aliases)
            
        except Exception as e:
            print(f"Error importing aliases: {e}")
            return False