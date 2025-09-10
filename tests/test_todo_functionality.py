#!/usr/bin/env python3
"""
Test script for todo functionality - specific scenarios
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright


class TodoTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_results = []
        
    async def setup(self):
        """Setup browser and page"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"[Browser] {msg.text}"))
        self.page.on("pageerror", lambda exc: print(f"[Error] {exc}"))
        
    async def teardown(self):
        """Cleanup"""
        await self.browser.close()
        await self.playwright.stop()
    
    async def log_result(self, scenario, success, details):
        """Log test results"""
        result = {
            "scenario": scenario,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {scenario}: {details}")
    
    async def test_scenario_1_check_api_endpoints(self):
        """Scenario 1: Check if todo API endpoints exist"""
        print("\n=== Scenario 1: Check Todo API Endpoints ===")
        
        # Navigate to the page first
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state("networkidle")
        
        # Test GET endpoint for fetching todos
        response = await self.page.evaluate("""
            async () => {
                const response = await fetch('/api/claude-logs/todos');
                return {
                    status: response.status,
                    ok: response.ok,
                    data: await response.json()
                };
            }
        """)
        
        await self.log_result(
            "GET /api/claude-logs/todos",
            response['ok'],
            f"Status: {response['status']}, Data: {json.dumps(response['data'])[:100]}"
        )
        
        # Test POST endpoint for creating todos
        response = await self.page.evaluate("""
            async () => {
                try {
                    const response = await fetch('/api/todos', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            content: 'Test todo from API',
                            status: 'pending'
                        })
                    });
                    return {
                        status: response.status,
                        ok: response.ok,
                        exists: true
                    };
                } catch (error) {
                    return {
                        status: 0,
                        ok: false,
                        exists: false,
                        error: error.message
                    };
                }
            }
        """)
        
        await self.log_result(
            "POST /api/todos (Create)",
            response.get('exists', False),
            f"Status: {response['status']}, Endpoint exists: {response.get('exists', False)}"
        )
    
    async def test_scenario_2_load_todos_page(self):
        """Scenario 2: Load todos page and check initial state"""
        print("\n=== Scenario 2: Load Todos Page ===")
        
        await self.page.goto(f"{self.base_url}/todos")
        await self.page.wait_for_load_state("networkidle")
        
        # Check if page loaded
        title = await self.page.title()
        await self.log_result(
            "Page loads successfully",
            "Todo" in title,
            f"Title: {title}"
        )
        
        # Check if todo list container exists
        todo_list = await self.page.query_selector("#todo-list")
        await self.log_result(
            "Todo list container exists",
            todo_list is not None,
            "Container found" if todo_list else "Container not found"
        )
        
        # Check if add todo form exists
        add_input = await self.page.query_selector("#new-todo")
        add_button = await self.page.query_selector(".add-todo")
        
        await self.log_result(
            "Add todo input exists",
            add_input is not None,
            "Input found" if add_input else "Input not found"
        )
        
        await self.log_result(
            "Add todo button exists",
            add_button is not None,
            "Button found" if add_button else "Button not found"
        )
    
    async def test_scenario_3_add_todo_via_ui(self):
        """Scenario 3: Add a todo via UI"""
        print("\n=== Scenario 3: Add Todo via UI ===")
        
        await self.page.goto(f"{self.base_url}/todos")
        await self.page.wait_for_load_state("networkidle")
        
        # Find input and button
        input_selector = "#new-todo"
        button_selector = ".add-todo"
        
        # Wait for elements
        try:
            await self.page.wait_for_selector(input_selector, timeout=3000)
            await self.page.wait_for_selector(button_selector, timeout=3000)
        except:
            await self.log_result(
                "UI elements available",
                False,
                "Input or button not found"
            )
            return
        
        # Type a todo
        test_todo = f"Test todo {datetime.now().strftime('%H:%M:%S')}"
        await self.page.fill(input_selector, test_todo)
        
        # Click add button
        await self.page.click(button_selector)
        
        # Wait a moment for update
        await asyncio.sleep(0.5)
        
        # Check if todo was added to the list
        todos = await self.page.query_selector_all(".todo-card")
        todo_count = len(todos)
        
        await self.log_result(
            "Todo added to UI",
            todo_count > 0,
            f"Found {todo_count} todos in list"
        )
        
        # Check if the new todo text appears
        page_text = await self.page.content()
        await self.log_result(
            "Todo text appears on page",
            test_todo in page_text,
            f"Looking for: {test_todo}"
        )
    
    async def test_scenario_4_check_local_storage(self):
        """Scenario 4: Check if todos are stored in localStorage"""
        print("\n=== Scenario 4: Check localStorage ===")
        
        await self.page.goto(f"{self.base_url}/todos")
        await self.page.wait_for_load_state("networkidle")
        
        # Check localStorage
        storage_data = await self.page.evaluate("""
            () => {
                const todos = localStorage.getItem('todos');
                return {
                    hasTodos: todos !== null,
                    data: todos ? JSON.parse(todos) : null
                };
            }
        """)
        
        await self.log_result(
            "Todos in localStorage",
            storage_data['hasTodos'],
            f"Data: {json.dumps(storage_data['data'])[:100] if storage_data['data'] else 'None'}"
        )
    
    async def test_scenario_5_check_alpine_data(self):
        """Scenario 5: Check Alpine.js data binding"""
        print("\n=== Scenario 5: Check Alpine.js Data ===")
        
        await self.page.goto(f"{self.base_url}/todos")
        await self.page.wait_for_load_state("networkidle")
        
        # Wait for Alpine to initialize
        await asyncio.sleep(1)
        
        # Check Alpine data
        alpine_data = await self.page.evaluate("""
            () => {
                // Try to find Alpine component
                const todoManager = document.querySelector('[x-data*="todoManager"]');
                if (todoManager && todoManager._x_dataStack) {
                    const data = todoManager._x_dataStack[0];
                    return {
                        hasTodos: data.todos !== undefined,
                        todoCount: data.todos ? data.todos.length : 0,
                        todos: data.todos ? data.todos.slice(0, 3) : []
                    };
                }
                return { hasTodos: false, error: 'Alpine component not found' };
            }
        """)
        
        await self.log_result(
            "Alpine.js todos data exists",
            alpine_data.get('hasTodos', False),
            f"Count: {alpine_data.get('todoCount', 0)}, Data: {alpine_data}"
        )
    
    async def test_scenario_6_test_api_directly(self):
        """Scenario 6: Test API endpoints directly"""
        print("\n=== Scenario 6: Test API Directly ===")
        
        # Try different potential API endpoints
        endpoints = [
            ("/api/todos", "GET", "Fetch todos"),
            ("/api/todos", "POST", "Create todo"),
            ("/api/todos/list", "GET", "List todos"),
            ("/api/todos/add", "POST", "Add todo"),
            ("/api/claude-logs/todos", "GET", "Claude logs todos"),
        ]
        
        for endpoint, method, description in endpoints:
            result = await self.page.evaluate(f"""
                async () => {{
                    try {{
                        const options = {{
                            method: '{method}',
                            headers: {{'Content-Type': 'application/json'}}
                        }};
                        
                        if ('{method}' === 'POST') {{
                            options.body = JSON.stringify({{
                                content: 'Test todo',
                                status: 'pending'
                            }});
                        }}
                        
                        const response = await fetch('{endpoint}', options);
                        return {{
                            status: response.status,
                            ok: response.ok,
                            contentType: response.headers.get('content-type')
                        }};
                    }} catch (error) {{
                        return {{
                            status: 0,
                            ok: false,
                            error: error.message
                        }};
                    }}
                }}
            """)
            
            await self.log_result(
                f"{method} {endpoint} - {description}",
                result.get('ok', False),
                f"Status: {result.get('status', 'N/A')}"
            )
    
    async def test_scenario_7_persistence(self):
        """Scenario 7: Test todo persistence across page reloads"""
        print("\n=== Scenario 7: Test Persistence ===")
        
        # Navigate to todos page
        await self.page.goto(f"{self.base_url}/todos")
        await self.page.wait_for_load_state("networkidle")
        
        # Add a todo
        test_todo = f"Persistence test {time.time()}"
        
        # Try to add via JavaScript directly
        add_result = await self.page.evaluate(f"""
            () => {{
                // Get Alpine component
                const todoManager = document.querySelector('[x-data*="todoManager"]');
                if (todoManager && todoManager._x_dataStack) {{
                    const data = todoManager._x_dataStack[0];
                    
                    // Add todo
                    const newTodo = {{
                        id: Date.now(),
                        content: '{test_todo}',
                        status: 'pending',
                        created_at: new Date().toISOString()
                    }};
                    
                    if (!data.todos) data.todos = [];
                    data.todos.push(newTodo);
                    
                    // Try to save to localStorage
                    localStorage.setItem('todos', JSON.stringify(data.todos));
                    
                    return {{
                        success: true,
                        todoCount: data.todos.length
                    }};
                }}
                return {{ success: false, error: 'Could not add todo' }};
            }}
        """)
        
        await self.log_result(
            "Add todo programmatically",
            add_result.get('success', False),
            f"Todo count: {add_result.get('todoCount', 0)}"
        )
        
        # Reload page
        await self.page.reload()
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)
        
        # Check if todo persisted
        persisted = await self.page.evaluate(f"""
            () => {{
                // Check localStorage
                const stored = localStorage.getItem('todos');
                if (stored) {{
                    const todos = JSON.parse(stored);
                    const found = todos.find(t => t.content === '{test_todo}');
                    return {{ found: !!found, count: todos.length }};
                }}
                
                // Check Alpine data
                const todoManager = document.querySelector('[x-data*="todoManager"]');
                if (todoManager && todoManager._x_dataStack) {{
                    const data = todoManager._x_dataStack[0];
                    if (data.todos) {{
                        const found = data.todos.find(t => t.content === '{test_todo}');
                        return {{ found: !!found, count: data.todos.length, source: 'alpine' }};
                    }}
                }}
                
                return {{ found: false, count: 0 }};
            }}
        """)
        
        await self.log_result(
            "Todo persists after reload",
            persisted.get('found', False),
            f"Found: {persisted.get('found')}, Count: {persisted.get('count')}, Source: {persisted.get('source', 'none')}"
        )
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        try:
            await self.setup()
            
            await self.test_scenario_1_check_api_endpoints()
            await self.test_scenario_2_load_todos_page()
            await self.test_scenario_3_add_todo_via_ui()
            await self.test_scenario_4_check_local_storage()
            await self.test_scenario_5_check_alpine_data()
            await self.test_scenario_6_test_api_directly()
            await self.test_scenario_7_persistence()
            
            # Summary
            print("\n" + "="*50)
            print("TEST SUMMARY")
            print("="*50)
            
            passed = sum(1 for r in self.test_results if r['success'])
            total = len(self.test_results)
            
            print(f"Total: {total}")
            print(f"Passed: {passed}")
            print(f"Failed: {total - passed}")
            print(f"Success Rate: {passed/total*100:.1f}%")
            
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['scenario']}: {result['details']}")
            
        finally:
            await self.teardown()


async def main():
    tester = TodoTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())