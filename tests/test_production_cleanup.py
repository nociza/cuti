from cuti.core.todo_models import TodoItem, TodoList, TodoPriority
from cuti.services.global_data_manager import GlobalDataManager
from cuti.services.todo_service import TodoService


def test_todo_list_lookup_resolves_name_and_id(tmp_path):
    service = TodoService(str(tmp_path / ".cuti"))
    todo_list = TodoList(name="Implementation", created_by="test")
    todo_list.add_todo(
        TodoItem(
            content="Wire CLI list lookup",
            priority=TodoPriority.HIGH,
            created_by="test",
        )
    )
    service.save_list(todo_list)

    by_name = service.get_list_by_name("implementation")
    by_id = service.get_list_by_name(todo_list.id)

    assert by_name is not None
    assert by_name.id == todo_list.id
    assert [todo.content for todo in by_name.todos] == ["Wire CLI list lookup"]
    assert by_id is not None
    assert by_id.id == todo_list.id


def test_remove_favorite_prompt_deletes_existing_prompt(tmp_path):
    manager = GlobalDataManager(str(tmp_path / ".cuti"))
    prompt_id = manager.add_favorite_prompt(
        title="Review",
        content="Review this patch",
        tags=["review"],
        project_path="/tmp/project",
    )

    assert [favorite.id for favorite in manager.get_favorite_prompts()] == [prompt_id]
    assert manager.remove_favorite_prompt(prompt_id) is True
    assert manager.get_favorite_prompts() == []
    assert manager.remove_favorite_prompt(prompt_id) is False
