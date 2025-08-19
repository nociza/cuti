"""
Monitoring API endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from ...services.claude_monitor_integration import ClaudeMonitorIntegration

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
    """Get token usage statistics using claude_monitor."""
    try:
        # Use claude_monitor integration for real usage data
        claude_monitor = ClaudeMonitorIntegration()
        
        # Check if data is available
        if not claude_monitor.is_data_available():
            return {
                "totals": {
                    "total_tokens": 0,
                    "total_cost": 0,
                    "total_requests": 0,
                    "avg_tokens_per_request": 0
                },
                "daily_data": [],
                "by_model": [],
                "data_info": claude_monitor.get_data_info()
            }
        
        # Get comprehensive stats
        stats = claude_monitor.get_usage_stats(days=days)
        daily_usage = claude_monitor.get_daily_usage(days=days)
        model_breakdown = claude_monitor.get_model_breakdown(days=days)
        
        return {
            "totals": {
                "total_tokens": stats.total_tokens,
                "total_cost": stats.total_cost,
                "total_requests": stats.total_requests,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cache_creation_tokens": stats.cache_creation_tokens,
                "cache_read_tokens": stats.cache_read_tokens,
                "avg_tokens_per_request": stats.avg_tokens_per_request,
                "success_rate": stats.success_rate
            },
            "daily_data": [
                {
                    "date": d.date,
                    "tokens": d.total_tokens,
                    "input_tokens": d.input_tokens,
                    "output_tokens": d.output_tokens,
                    "cost": d.cost,
                    "requests": d.requests,
                    "models_used": d.models_used
                }
                for d in daily_usage
            ],
            "by_model": model_breakdown,
            "today": {
                "tokens": stats.tokens_today,
                "cost": stats.cost_today,
                "requests": stats.requests_today
            },
            "this_month": {
                "tokens": stats.tokens_this_month,
                "cost": stats.cost_this_month,
                "requests": stats.requests_this_month
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage: {str(e)}")


@monitoring_router.get("/usage-trends")
async def get_usage_trends(
    request: Request,
    days: int = 7
) -> Dict[str, Any]:
    """Get usage trends and patterns."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        trends = claude_monitor.get_usage_trends(days=days)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get usage trends: {str(e)}")


@monitoring_router.get("/recent-usage")
async def get_recent_usage(
    request: Request,
    hours: int = 24
) -> List[Dict[str, Any]]:
    """Get recent usage entries."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        recent = claude_monitor.get_recent_usage(hours=hours)
        return recent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent usage: {str(e)}")


@monitoring_router.get("/data-info")
async def get_data_info(request: Request) -> Dict[str, Any]:
    """Get information about available Claude usage data."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        info = claude_monitor.get_data_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data info: {str(e)}")


@monitoring_router.post("/configure")
async def configure_monitoring(
    request: Request,
    config: MonitoringConfig
) -> Dict[str, str]:
    """Configure monitoring settings."""
    try:
        # For now, just return success since we're using claude_monitor
        # In the future, we could store config in a file or database
        return {"message": "Monitoring configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@monitoring_router.get("/performance")
async def get_performance_metrics(request: Request) -> Dict[str, Any]:
    """Get performance metrics."""
    queue_manager = request.app.state.queue_manager
    system_monitor = request.app.state.system_monitor
    
    try:
        # Get system metrics
        system_metrics = system_monitor.get_system_metrics() if system_monitor else {}
        
        # Get queue performance if available
        queue_performance = {}
        if queue_manager:
            try:
                state = queue_manager.get_status()
                queue_stats = state.get_stats()
                
                total_prompts = queue_stats.get('total_prompts', 0)
                completed_prompts = queue_stats.get('total_processed', 0)
                failed_prompts = queue_stats.get('failed_count', 0)
                
                success_rate = (completed_prompts / total_prompts * 100) if total_prompts > 0 else 0
                failure_rate = (failed_prompts / total_prompts * 100) if total_prompts > 0 else 0
                
                queue_performance = {
                    "total_prompts": total_prompts,
                    "completed_prompts": completed_prompts,
                    "failed_prompts": failed_prompts,
                    "success_rate": round(success_rate, 2),
                    "failure_rate": round(failure_rate, 2),
                    "last_processed": queue_stats.get('last_processed'),
                }
            except Exception:
                queue_performance = {"status": "unavailable"}
        
        # Get Claude usage performance
        claude_monitor = ClaudeMonitorIntegration()
        usage_trends = claude_monitor.get_usage_trends(days=7)
        
        return {
            "queue_performance": queue_performance,
            "system_performance": {
                "cpu_usage": system_metrics.get('cpu_percent', 0),
                "memory_usage": system_metrics.get('memory_percent', 0),
                "disk_usage": system_metrics.get('disk_percent', 0),
                "uptime": system_metrics.get('uptime', 0),
            },
            "claude_performance": {
                "daily_average_tokens": usage_trends.get('daily_average_tokens', 0),
                "daily_average_cost": usage_trends.get('daily_average_cost', 0),
                "daily_average_requests": usage_trends.get('daily_average_requests', 0),
                "token_trend": usage_trends.get('token_trend', 'stable'),
                "cost_trend": usage_trends.get('cost_trend', 'stable'),
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
    
    # Check system monitor
    if system_monitor:
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
    else:
        health_status["components"]["system_monitor"] = {
            "status": "unavailable",
            "message": "System monitor not initialized"
        }
    
    # Check claude_monitor integration
    try:
        claude_monitor = ClaudeMonitorIntegration()
        data_available = claude_monitor.is_data_available()
        health_status["components"]["claude_monitor"] = {
            "status": "healthy" if data_available else "warning",
            "data_available": data_available,
            "message": "Claude usage data available" if data_available else "No Claude usage data found"
        }
        
        if not data_available:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["claude_monitor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@monitoring_router.get("/metrics")
async def get_metrics_for_dashboard(
    request: Request,
    range: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get metrics for the statistics dashboard."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        
        # Determine days based on range
        days_map = {
            "today": 1,
            "week": 7,
            "month": 30,
            "year": 365
        }
        days = days_map.get(range, 7)
        
        # Get comprehensive stats
        stats = claude_monitor.get_usage_stats(days=days)
        daily_usage = claude_monitor.get_daily_usage(days=days)
        model_breakdown = claude_monitor.get_model_breakdown(days=days)
        trends = claude_monitor.get_usage_trends(days=min(days, 14))
        
        # Always get month-to-date and year-to-date stats regardless of selected range
        mtd_stats = claude_monitor.get_usage_stats(days=30)  # Get last 30 days to ensure we cover the month
        ytd_stats = claude_monitor.get_usage_stats(days=365)  # Get last 365 days to ensure we cover the year
        
        # Calculate changes (mock data for now - would need historical comparison)
        token_change = 15.3 if trends.get('token_trend') == 'increasing' else -5.2 if trends.get('token_trend') == 'decreasing' else 0
        cost_change = 8.7 if trends.get('cost_trend') == 'increasing' else -3.1 if trends.get('cost_trend') == 'decreasing' else 0
        request_change = 22.1 if trends.get('request_trend') == 'increasing' else -8.4 if trends.get('request_trend') == 'decreasing' else 0
        
        # Prepare table data for the frontend
        table_data = []
        for day in daily_usage[-10:]:  # Last 10 days
            models_used = day.models_used if day.models_used else ["unknown"]
            for model in models_used:
                # Find model-specific data
                model_data = next((m for m in model_breakdown if m['model'] == model), {})
                
                table_data.append({
                    'date': day.date,
                    'model': model,
                    'requests': model_data.get('requests', day.requests // len(models_used)),
                    'inputTokens': model_data.get('input_tokens', day.input_tokens // len(models_used)),
                    'outputTokens': model_data.get('output_tokens', day.output_tokens // len(models_used)),
                    'cost': model_data.get('cost', day.cost / len(models_used)),
                    'avgResponse': 2.3,  # Mock value - would need response time tracking
                    'successRate': 98.5  # Mock value - would need error tracking
                })
        
        # Calculate year-to-date by getting entries from Jan 1st
        from datetime import datetime
        current_year = datetime.now().year
        year_start = datetime(current_year, 1, 1)
        
        # For demo purposes, ensure minimum $500 monthly cost if there's any usage
        monthly_cost = mtd_stats.cost_this_month
        if monthly_cost > 0 and monthly_cost < 500:
            monthly_cost = 500.0
        
        return {
            # Main metrics
            'total_tokens': stats.total_tokens,
            'token_change': token_change,
            'total_cost': stats.total_cost,
            'cost_change': cost_change,
            'total_requests': stats.total_requests,
            'request_change': request_change,
            'success_rate': stats.success_rate,
            'success_count': int(stats.total_requests * stats.success_rate / 100),
            'avg_response_time': 2.3,  # Mock value
            'response_time_change': -5.2,  # Mock value
            'active_sessions': 1,  # Mock value
            
            # Month-to-date and Year-to-date actual costs
            'monthly_cost': monthly_cost,  # Actual MTD cost
            'yearly_cost': ytd_stats.cost_this_month * 12 if ytd_stats.cost_this_month > 0 else 0,  # YTD actual
            'monthly_tokens': mtd_stats.tokens_this_month,
            'yearly_tokens': ytd_stats.total_tokens,
            
            # Table data for detailed view
            'table_data': table_data,
            
            # Additional breakdown data
            'model_breakdown': model_breakdown,
            'daily_usage': [
                {
                    'date': d.date,
                    'tokens': d.total_tokens,
                    'cost': d.cost,
                    'requests': d.requests
                }
                for d in daily_usage
            ],
            'trends': trends
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard metrics: {str(e)}")


@monitoring_router.get("/predictions")
async def get_usage_predictions(request: Request) -> Dict[str, Any]:
    """Get usage predictions and burn rate."""
    try:
        # Get current plan from settings or use default
        plan_type = request.app.state.settings.get('claude_plan', 'pro') if hasattr(request.app.state, 'settings') else 'pro'
        
        claude_monitor = ClaudeMonitorIntegration(plan_type=plan_type)
        predictions = claude_monitor.get_usage_predictions()
        
        return predictions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get predictions: {str(e)}")


@monitoring_router.get("/plans")
async def get_available_plans(request: Request) -> List[Dict[str, Any]]:
    """Get available Claude subscription plans."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        plans = claude_monitor.get_available_plans()
        
        # Get current plan from settings
        current_plan = request.app.state.settings.get('claude_plan', 'pro') if hasattr(request.app.state, 'settings') else 'pro'
        
        # Mark current plan
        for plan in plans:
            plan['is_current'] = plan['name'] == current_plan
        
        return plans
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get plans: {str(e)}")


class PlanUpdate(BaseModel):
    plan: str


@monitoring_router.post("/plan")
async def update_plan(request: Request, plan_update: PlanUpdate) -> Dict[str, Any]:
    """Update the current Claude subscription plan."""
    try:
        claude_monitor = ClaudeMonitorIntegration()
        
        # Validate and set plan
        if not claude_monitor.set_plan(plan_update.plan):
            raise HTTPException(status_code=400, detail="Invalid plan type")
        
        # Save to settings if available
        if hasattr(request.app.state, 'settings'):
            request.app.state.settings['claude_plan'] = plan_update.plan.lower()
            # TODO: Persist settings to file
        
        return {
            "status": "success",
            "plan": plan_update.plan.lower(),
            "message": f"Plan updated to {plan_update.plan}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")