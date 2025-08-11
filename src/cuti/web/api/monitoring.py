"""
Monitoring API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class MonitoringConfig(BaseModel):
    token_alert_threshold: Optional[int] = None
    cost_alert_threshold: Optional[float] = None


@monitoring_router.get("/system")
async def get_system_metrics(request: Request) -> Dict[str, Any]:
    """Get current system metrics."""
    system_monitor = request.app.state.system_monitor
    
    try:
        metrics = system_monitor.get_system_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@monitoring_router.get("/tokens")  
async def get_token_usage(
    request: Request,
    days: int = 30
) -> Dict[str, Any]:
    """Get token usage statistics."""
    system_monitor = request.app.state.system_monitor
    
    try:
        # Get token usage stats from the monitoring service
        stats = system_monitor.get_token_usage_stats(days=days)
        
        # Return the stats directly from the monitoring service
        return stats if stats else {
            "totals": {
                "total_tokens": 0,
                "total_cost": 0,
                "total_requests": 0,
                "avg_tokens_per_request": 0
            },
            "daily_data": [],
            "by_model": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage: {str(e)}")


@monitoring_router.post("/configure")
async def configure_monitoring(
    request: Request,
    config: MonitoringConfig
) -> Dict[str, str]:
    """Configure monitoring settings."""
    usage_monitor = request.app.state.usage_monitor
    
    try:
        # Update monitoring configuration
        if config.token_alert_threshold is not None:
            usage_monitor.set_token_alert_threshold(config.token_alert_threshold)
        
        if config.cost_alert_threshold is not None:
            usage_monitor.set_cost_alert_threshold(config.cost_alert_threshold)
        
        return {"message": "Monitoring configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@monitoring_router.get("/performance")
async def get_performance_metrics(request: Request) -> Dict[str, Any]:
    """Get performance metrics."""
    queue_manager = request.app.state.queue_manager
    system_monitor = request.app.state.system_monitor
    
    if not queue_manager:
        raise HTTPException(status_code=503, detail="Queue manager not available")
    
    try:
        # Get queue statistics
        state = queue_manager.get_status()
        queue_stats = state.get_stats()
        
        # Get system metrics
        system_metrics = system_monitor.get_system_metrics()
        
        # Calculate performance metrics
        total_prompts = queue_stats.get('total_prompts', 0)
        completed_prompts = queue_stats.get('total_processed', 0)
        failed_prompts = queue_stats.get('failed_count', 0)
        
        success_rate = (completed_prompts / total_prompts * 100) if total_prompts > 0 else 0
        failure_rate = (failed_prompts / total_prompts * 100) if total_prompts > 0 else 0
        
        return {
            "queue_performance": {
                "total_prompts": total_prompts,
                "completed_prompts": completed_prompts,
                "failed_prompts": failed_prompts,
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "last_processed": queue_stats.get('last_processed'),
            },
            "system_performance": {
                "cpu_usage": system_metrics.get('cpu_percent', 0),
                "memory_usage": system_metrics.get('memory_percent', 0),
                "disk_usage": system_metrics.get('disk_usage', {}),
                "uptime": system_metrics.get('uptime', 0),
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@monitoring_router.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint."""
    queue_manager = request.app.state.queue_manager
    system_monitor = request.app.state.system_monitor
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check queue manager
    if queue_manager:
        try:
            state = queue_manager.get_status()
            health_status["components"]["queue_manager"] = {
                "status": "healthy",
                "total_prompts": len(state.prompts)
            }
        except Exception as e:
            health_status["components"]["queue_manager"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["components"]["queue_manager"] = {
            "status": "unavailable",
            "message": "Queue manager not initialized"
        }
        health_status["status"] = "degraded"
    
    # Check system monitor
    try:
        metrics = system_monitor.get_system_metrics()
        health_status["components"]["system_monitor"] = {
            "status": "healthy",
            "cpu_usage": metrics.get('cpu_percent', 0),
            "memory_usage": metrics.get('memory_percent', 0)
        }
    except Exception as e:
        health_status["components"]["system_monitor"] = {
            "status": "unhealthy", 
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status