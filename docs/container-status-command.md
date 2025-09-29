# Container Status Commands

## Overview

The `cuti` CLI now includes comprehensive container management commands to view and manage all running containers across different workspaces.

## Available Commands

### 1. View Container Status

Show all running cuti containers grouped by workspace:

```bash
# Using the main container command with --status flag
cuti container --status

# Using the containers subcommand
cuti containers status

# With verbose output
cuti containers status --verbose

# Output as JSON
cuti containers status --json
```

**Output Example:**
```
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  Container Summary                                                           │
│  Total Containers: 6                                                         │
│  Total Workspaces: 4                                                         │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

                    ProjectName                    
                                                    
  Container ID     Name                 Status      
 ────────────────────────────────────────────────── 
  60fcce9f0858     vibrant_cartwright   Up 4 days   
  33c1c8124e11     adoring_thompson     Up 2 weeks  
                                                    
      /path/to/workspace                           
```

### 2. Start a Container

Start a new container for the current workspace:

```bash
# Interactive shell
cuti containers start

# Run a specific command
cuti containers start "npm test"

# Rebuild the container image
cuti containers start --rebuild
```

### 3. Stop Containers

Stop one or more running containers:

```bash
# Stop a specific container
cuti containers stop <container-id>

# Stop all containers
cuti containers stop --all

# Skip confirmation
cuti containers stop --all --force
```

### 4. Enter a Container

Enter an existing running container:

```bash
# Enter by container ID
cuti containers enter <container-id>

# Enter container for a specific workspace
cuti containers enter --workspace ProjectName

# If only one container is running, just use:
cuti containers enter
```

### 5. Clean Up Stopped Containers

Remove stopped containers to free up space:

```bash
# Clean up all stopped containers
cuti containers cleanup

# Skip confirmation
cuti containers cleanup --force
```

## Key Features

### Workspace Grouping
- Containers are automatically grouped by their mounted workspace directory
- Makes it easy to identify which containers belong to which projects

### Multiple Container Support
- Multiple containers can run simultaneously on the same workspace
- Each container gets a unique Docker-assigned name
- All containers share the same workspace mount

### Resource Sharing
All containers for a workspace share:
- The workspace directory (mounted at `/workspace`)
- The `.cuti` configuration directory
- Claude configuration directories
- Docker socket for Docker-in-Docker functionality
- Host network

## Use Cases

1. **Development Isolation**: Run different features in separate containers
2. **Parallel Testing**: Test different configurations simultaneously
3. **Multi-Tool Usage**: Run web UI in one container, CLI in another
4. **Team Collaboration**: Multiple developers can work in separate containers

## Implementation Details

The container status functionality is implemented in:
- `/workspace/src/cuti/cli/commands/container.py` - Main container management commands
- Integration with existing `cuti container` command via `--status` flag
- Uses Docker API to inspect running containers and extract workspace information

## Notes

- Containers use the `cuti-dev-universal` Docker image
- Each container runs with `--rm` flag (auto-removed on exit)
- No container naming conflicts as Docker assigns unique names automatically
- The status command only shows running containers (not stopped ones)