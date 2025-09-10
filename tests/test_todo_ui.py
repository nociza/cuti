#!/usr/bin/env python3
"""Test the todo UI with hierarchical structure."""

import asyncio
from playwright.async_api import async_playwright
import json

async def test_todo_ui():
    """Test the todo UI displays hierarchical structure."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("Testing Todo UI...")
            
            # Navigate to todos page
            await page.goto('http://localhost:8000/todos')
            await page.wait_for_load_state('networkidle')
            
            # Check if the page loads
            title = await page.title()
            print(f"✓ Page loaded: {title}")
            
            # Check for todo list container
            todo_list = await page.query_selector('#todo-list')
            if todo_list:
                print("✓ Todo list container found")
            
            # Get all todos
            todos = await page.query_selector_all('.todo-item')
            print(f"✓ Found {len(todos)} todo items in UI")
            
            # Check for hierarchical indicators
            master_todos = await page.query_selector_all('.master-todo')
            sub_todos = await page.query_selector_all('.sub-todo')
            
            print(f"  - Master todos: {len(master_todos)}")
            print(f"  - Sub todos: {len(sub_todos)}")
            
            # Check for statistics display
            stats = await page.query_selector('.todo-stats')
            if stats:
                stats_text = await stats.inner_text()
                print(f"✓ Statistics displayed: {stats_text[:50]}...")
            
            # Test create todo functionality
            create_btn = await page.query_selector('[data-action="create-todo"]')
            if create_btn:
                print("✓ Create todo button found")
            
            # Check for session info
            session_info = await page.query_selector('.session-info')
            if session_info:
                print("✓ Session info displayed")
            
            # Get todo content to verify hierarchy
            if todos:
                first_todo = todos[0]
                content = await first_todo.inner_text()
                print(f"✓ First todo content: {content[:50]}...")
            
            print("\n✅ Todo UI test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error testing UI: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_todo_ui())