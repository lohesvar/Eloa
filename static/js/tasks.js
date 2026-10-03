/* ==========================================
   TASKS & NOTEBOOK INTERACTION LOGIC
   ========================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTaskForm();
  initTaskInteractions();
});

function initTaskForm() {
  const taskForm = document.getElementById('task-form');
  const isMeasurableCheckbox = document.getElementById('is_measurable');
  const measurableFields = document.getElementById('measurable-fields');
  const nonMeasurableFields = document.getElementById('non-measurable-fields');

  if (isMeasurableCheckbox) {
    isMeasurableCheckbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        measurableFields.style.display = 'block';
        nonMeasurableFields.style.display = 'none';
      } else {
        measurableFields.style.display = 'none';
        nonMeasurableFields.style.display = 'block';
      }
    });
  }

  if (taskForm) {
    taskForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const taskId = document.getElementById('task_id').value;
      const formData = {
        title: document.getElementById('task_title').value,
        category: document.getElementById('task_category').value,
        priority: document.getElementById('task_priority').value,
        due_date: document.getElementById('task_due_date').value,
        description: document.getElementById('task_description').value,
        is_measurable: isMeasurableCheckbox ? isMeasurableCheckbox.checked : false,
        target_value: document.getElementById('target_value').value,
        actual_value: document.getElementById('actual_value').value,
        unit: document.getElementById('unit').value,
        progress_assessment: document.getElementById('progress_assessment').value
      };

      try {
        let response;
        if (taskId) {
          // Update existing task
          response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
          });
        } else {
          // Create new task
          response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
          });
        }

        const result = await response.json();
        if (result.success) {
          showToast(taskId ? 'Task updated in notebook!' : 'Task added to notebook!', 'success');
          closeModal('task-modal');
          // Reload page to reflect updated task in correct section
          setTimeout(() => window.location.reload(), 400);
        } else {
          showToast(result.error || 'Failed to save task', 'danger');
        }
      } catch (err) {
        console.error(err);
        showToast('Server error while saving task.', 'danger');
      }
    });
  }
}

function initTaskInteractions() {
  // Delegate click listeners on task list
  document.addEventListener('change', async (e) => {
    if (e.target.matches('.task-checkbox-input')) {
      const checkbox = e.target;
      const taskItem = checkbox.closest('.task-item');
      const taskId = taskItem.getAttribute('data-task-id');

      try {
        const response = await fetch(`/api/tasks/${taskId}/toggle`, {
          method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
          if (result.task.status === 'completed') {
            taskItem.classList.add('completed');
            showToast('Task marked as completed! ✍️', 'success');
          } else {
            taskItem.classList.remove('completed');
            showToast('Task restored to pending.', 'info');
          }
          // Update header quick stats if present
          updateQuickStats();
        }
      } catch (err) {
        console.error(err);
        checkbox.checked = !checkbox.checked;
        showToast('Error updating task status', 'danger');
      }
    }
  });

  // Edit Button Clicks
  document.addEventListener('click', async (e) => {
    const editBtn = e.target.closest('.edit-task-btn');
    if (editBtn) {
      const taskItem = editBtn.closest('.task-item');
      const taskId = taskItem.getAttribute('data-task-id');
      openEditModal(taskId);
    }

    const deleteBtn = e.target.closest('.delete-task-btn');
    if (deleteBtn) {
      const taskItem = deleteBtn.closest('.task-item');
      const taskId = taskItem.getAttribute('data-task-id');
      if (confirm('Are you sure you want to erase this task from your notebook?')) {
        deleteTask(taskId, taskItem);
      }
    }
  });
}

async function openEditModal(taskId) {
  try {
    const response = await fetch('/api/tasks');
    const data = await response.json();
    const task = data.tasks.find(t => t.id == taskId);

    if (task) {
      document.getElementById('task_id').value = task.id;
      document.getElementById('task_title').value = task.title;
      document.getElementById('task_category').value = task.category;
      document.getElementById('task_priority').value = task.priority;
      document.getElementById('task_due_date').value = task.due_date || '';
      document.getElementById('task_description').value = task.description || '';
      
      const isMeasurableCheckbox = document.getElementById('is_measurable');
      isMeasurableCheckbox.checked = task.is_measurable;
      
      document.getElementById('target_value').value = task.target_value !== null ? task.target_value : '';
      document.getElementById('actual_value').value = task.actual_value !== null ? task.actual_value : '';
      document.getElementById('unit').value = task.unit || '';
      document.getElementById('progress_assessment').value = task.progress_assessment || 'not_started';

      if (task.is_measurable) {
        document.getElementById('measurable-fields').style.display = 'block';
        document.getElementById('non-measurable-fields').style.display = 'none';
      } else {
        document.getElementById('measurable-fields').style.display = 'none';
        document.getElementById('non-measurable-fields').style.display = 'block';
      }

      document.getElementById('modal-form-title').innerText = 'Edit Notebook Task';
      openModal('task-modal');
    }
  } catch (err) {
    console.error(err);
    showToast('Failed to load task details for editing.', 'danger');
  }
}

async function deleteTask(taskId, taskItem) {
  try {
    const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    const result = await response.json();
    if (result.success) {
      taskItem.style.transform = 'translateX(30px)';
      taskItem.style.opacity = '0';
      taskItem.style.transition = 'all 0.3s ease';
      setTimeout(() => taskItem.remove(), 300);
      showToast('Task erased from notebook.', 'info');
    } else {
      showToast('Failed to delete task', 'danger');
    }
  } catch (err) {
    console.error(err);
    showToast('Server error while deleting task.', 'danger');
  }
}

function resetTaskForm() {
  document.getElementById('task_id').value = '';
  document.getElementById('task-form').reset();
  document.getElementById('modal-form-title').innerText = 'New Notebook Task';
  document.getElementById('measurable-fields').style.display = 'none';
  document.getElementById('non-measurable-fields').style.display = 'block';
}

function openNewTaskModal(category = 'daily') {
  resetTaskForm();
  document.getElementById('task_category').value = category;
  openModal('task-modal');
}

async function updateQuickStats() {
  try {
    const response = await fetch('/api/analytics?period=today');
    const data = await response.json();
    const statsElem = document.getElementById('today-remaining-count');
    if (statsElem) {
      statsElem.innerText = data.summary.pending_tasks;
    }
  } catch(e) {}
}
