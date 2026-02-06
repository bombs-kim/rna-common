<script>
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";

  const API_URL = import.meta.env.VITE_API_URL;

  let projects = [];
  let loading = true;
  let error = null;
  let creating = false;
  let deleting = {};

  async function loadProjects() {
    if (!API_URL) {
      error = "VITE_API_URL is not set";
      loading = false;
      return;
    }
    try {
      const response = await fetch(`${API_URL}/api/projects`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      projects = data.items ?? [];
      loading = false;
    } catch (err) {
      console.error("Error loading projects:", err);
      error = err.message;
      loading = false;
    }
  }

  onMount(loadProjects);

  async function createProject() {
    if (creating) return;
    creating = true;
    error = null;

    try {
      const response = await fetch(`${API_URL}/api/projects`, {
        method: "POST",
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }
      const data = await response.json();
      // Reload projects list
      await loadProjects();
      // Navigate to the new project
      goto(`/project/${data.id}`);
    } catch (err) {
      console.error("Error creating project:", err);
      error = err.message;
      creating = false;
    }
  }

  async function deleteProject(projectId, event) {
    event.preventDefault();
    event.stopPropagation();

    if (
      !confirm(
        `Are you sure you want to delete Project ${projectId}? This action cannot be undone.`
      )
    ) {
      return;
    }

    deleting[projectId] = true;
    error = null;

    try {
      const response = await fetch(`${API_URL}/api/projects/${projectId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }
      // Reload projects list
      await loadProjects();
    } catch (err) {
      console.error("Error deleting project:", err);
      error = err.message;
    } finally {
      deleting[projectId] = false;
    }
  }

  function openProject(id) {
    goto(`/project/${id}`);
  }
</script>

<div class="header">
  <h1>Projects</h1>
  <button
    class="create-button"
    on:click={createProject}
    disabled={creating || loading}
  >
    {creating ? "Creating..." : "+ Create Project"}
  </button>
</div>

{#if error}
  <div class="error">Error: {error}</div>
{/if}

<div class="project-list">
  {#if loading}
    <div class="loading">Loading projects...</div>
  {:else if projects.length === 0}
    <div class="empty-state">
      <p>No projects found. Create your first project to get started!</p>
    </div>
  {:else}
    {#each projects as project}
      <div class="card">
        <a href="/project/{project.id}">Project {project.id}</a>
        <button
          class="delete-button"
          on:click={(e) => deleteProject(project.id, e)}
          disabled={deleting[project.id]}
        >
          {deleting[project.id] ? "⏳" : "🗑️"}
        </button>
      </div>
    {/each}
  {/if}
</div>

<style>
  .header {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-2xl);
  }

  h1 {
    font-size: var(--font-size-base);
  }

  .create-button {
    background: var(--accent-blue);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    padding: var(--spacing-md) var(--spacing-xl);
    font-size: var(--font-size-base);
    cursor: pointer;
  }

  .create-button:hover:not(:disabled) {
    background: var(--accent-blue-dark, #0056b3);
  }

  .create-button:disabled {
    opacity: 0.6;
  }

  .card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: var(--spacing-2xl);
    margin: var(--spacing-lg) 0;
  }

  .card a {
    font-size: var(--font-size-base);
    text-decoration: none;
    color: inherit;
  }

  .card a:hover {
    color: var(--accent-blue);
  }

  .delete-button {
    background: transparent;
    border: 1px solid var(--accent-red, #dc3545);
    border-radius: var(--radius-md);
    padding: var(--spacing-sm);
    cursor: pointer;
  }

  .delete-button:hover:not(:disabled) {
    background: var(--accent-red, #dc3545);
    color: white;
  }

  .delete-button:disabled {
    opacity: 0.6;
  }

  .loading {
    color: var(--text-secondary);
    font-style: italic;
  }

  .error {
    color: var(--accent-red, #dc3545);
    background: var(--bg-secondary);
    border: 1px solid var(--accent-red, #dc3545);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-4xl);
    color: var(--text-secondary);
  }
</style>
