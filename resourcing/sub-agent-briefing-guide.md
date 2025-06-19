# Sub-Agent Briefing and Task Management Guide

## 1. Overview of the Sub-Agent Task Management Process

This document outlines the collaborative process for managing tasks assigned to specialized sub-agents (like you!) within this project. Our goal is to create a clear, detailed, and traceable workflow that enhances productivity and project documentation.

**1.1. Collaborative Task Definition (User/Project Manager & Lead Planner)**

*   **High-Level Goals:** The process typically begins with the User (Project Manager) and a Lead Planner (e.g., Jules, in a lead capacity) discussing high-level project goals, features, or issues that need addressing. These are often guided by documents like the `IMPLEMENTATION_GUIDE.md`.
*   **Feature Breakdown:** The Lead Planner, in collaboration with the User, breaks down these larger features into more granular, manageable sub-tasks suitable for assignment to specialized sub-agents. Each sub-task is designed to be a coherent unit of work.
*   **Agent Assignment:** Sub-tasks are then notionally assigned to specific "named" agents (e.g., Agent A, Agent E), each potentially specializing in or focusing on a particular area (e.g., backend logic, UI components, documentation).

**1.2. The `tasks/agent_<X>.md` File: Your Central Hub**

*   **Dedicated Task File:** Each named agent (e.g., Agent E) has a dedicated task management file located in the `tasks/` directory of the repository (e.g., `tasks/agent_E.md`). This file is your primary source for understanding your current assignments and for documenting your work.
*   **Purpose:**
    *   To provide you with clear, detailed assignments.
    *   To serve as a space for you to develop and document your detailed implementation plans for each task.
    *   To track the status of your tasks.
    *   To create a rich, versionable history of work done, facilitating project documentation and review.
*   **Notification:** When a new task is assigned to you, or an existing one is updated, the User/Project Manager (or the Lead Planner) will notify you to review your `tasks/agent_<X>.md` file.
*   **File Structure Example (for an Active Task):**
    ```markdown
    ---
    ### Task ID: <YYYYMMDD-HHMMSS-UniqueID>
    **Assigned:** <YYYY-MM-DD HH:MM UTC>
    **Status:** New | In Progress | Blocked | Planning Complete | Implemented | Testing | Completed
    **Title:** <Brief Task Title>

    **Description:**
    <Detailed task description, objectives, and key requirements.>

    **Acceptance Criteria:**
    - <Criteria 1>
    - <Criteria 2>

    **Notes/Plans by Agent <X>:**
    **Last Plan Update:** <YYYY-MM-DD HH:MM UTC by Agent X>
    *(Agent <X> to update this timestamp when they make significant plan updates)*

    *   *(Agent <X> can add their detailed plans, thoughts, or logs here for this task. This section will contain the breakdown of how this major task will be approached, including designs for individual components or steps.)*

    **Key Decisions & Rationale:**
    *(Optional: Agent <X> to note key design choices or assumptions made during their planning)*
    - <Decision 1 with rationale>

    **Open Questions for Lead:**
    *(Optional: Agent <X> to list any questions or points needing clarification from the Lead Planner/User)*
    - <Question 1>

    **Dependencies:**
    *(Optional: Agent <X> to list dependencies this task has on other tasks, IPC channels, specific data, etc.)*
    - <Dependency 1: e.g., IPC Channel 'get-data' from Agent Y>
    - <Dependency 2: e.g., Completion of Task ID ZZZ by Agent W>

    **Relevant Files/Links:**
    - `IMPLEMENTATION_GUIDE.md` (Section: <Relevant Section>)
    - Link to specific designs if applicable.
    ---
    ```

**1.3. Workflow Cycle**

The general cycle for a task is:

1.  **Assignment:** A new task appears in your `tasks/agent_<X>.md` file with "Status: New".
2.  **Review & Plan:** You (the Sub-Agent) review the task and develop a detailed implementation plan directly within the "Notes/Plans by Agent `<X>`:" section of that task in your file, utilizing the new sub-sections for timestamps, decisions, questions, and dependencies. You then update the task status to "Planning Complete".
3.  **Plan Approval (Optional but Recommended):** You notify the User/Lead Planner that your plan is ready for review. They provide feedback or approval.
4.  **Simulated Implementation & Progress Updates:** You "execute" your plan step-by-step (describing actions if you're an AI like Jules, or actually implementing if you're a human developer). You update your task file with progress, notes, or any deviations from the plan. Task status might move to "In Progress".
5.  **Completion:** Once all aspects of a task are done according to its acceptance criteria, you update its status to "Completed" and add any final summaries or outcomes to your notes in the task file.
6.  **Archival:** Completed tasks are then moved to an archive (details in Section 4) by the Lead Planner/User to keep the active task list focused.

This structured approach ensures that both the assignment of tasks and the detailed planning and execution by sub-agents are well-documented and aligned with overall project goals.

## 2. The Sub-Agent's Workflow

As a Sub-Agent (e.g., Agent A, Agent E), your workflow is centered around your dedicated task file (`tasks/agent_<X>.md`) and clear communication with the User/Project Manager or Lead Planner.

**2.1. Receiving and Understanding a Task**

1.  **Notification:** You will be notified (e.g., by the User or Lead Planner) when a new task has been added to your `tasks/agent_<X>.md` file or an existing one requires your attention.
2.  **Locate Task:** Open your task file. New tasks are typically found at the top of the "## Active Tasks" section, marked with "Status: New". Each task will have a unique `Task ID`.
3.  **Thorough Review:** Carefully read the entire task block, including Description, Acceptance Criteria, and any initial Dependencies or Relevant Files.

**2.2. Detailed Planning (The Core of Your Contribution)**

This is the most critical phase of your work as a sub-agent. The expectation is a detailed, well-thought-out implementation plan *before* (simulated) execution begins.

1.  **Planning Space:** Within the specific task block in your `tasks/agent_<X>.md` file, locate the "Notes/Plans by Agent `<X>`:" heading.
2.  **Breakdown the Task:** Decompose the assigned task into smaller, actionable steps or components.
3.  **Define Data Structures & Interfaces:** If your task involves data manipulation or communication between components, clearly define the structure of data objects, payloads, etc.
4.  **Outline Logic:** For complex parts, outline the algorithmic logic or decision-making flow.
5.  **Define Output Expectations (for LLM-based tasks):** If the core of the task involves an LLM generating content (like code or summaries), the plan should include specific instructions for the LLM about its output. This includes:
    *   The format and structure of the primary output (e.g., code files, a `solution_summary.md`).
    *   **Explicitly listing key files created or modified:** The LLM should be prompted to provide a list of the primary files it has worked on. This list is crucial for subsequent review and integration steps. This list might be included within its `solution_summary.md` or as part of a structured status update.
6.  **Identify Dependencies & Coordination Points:** Note any dependencies on other tasks, other agents, or existing code.
7.  **Consider Edge Cases & Error Handling:** Briefly think about potential edge cases or error conditions.
8.  **Document Your Plan:** Write this detailed plan directly into the "Notes/Plans by Agent `<X>`:" section. Use Markdown formatting for clarity. The level of detail should be sufficient for another technically competent individual to understand your approach and for you to follow during (simulated) implementation.
9.  **Document Key Decisions, Questions, and Dependencies:** Use the dedicated sub-sections ("Key Decisions & Rationale:", "Open Questions for Lead:", "Dependencies:") within "Notes/Plans by Agent `<X>`:" to explicitly note these important aspects of your plan. This helps in communication and tracking.
10. **Update Timestamp:** Whenever you significantly update your plan, update the "**Last Plan Update:**" timestamp at the beginning of your "Notes/Plans by Agent `<X>`:" section.
11. **Update Status:** Once your detailed plan is documented, change the `Status:` field for that task in your file from "New" to "Planning Complete".
12. **Notify Lead/User:** Inform the User/Project Manager or Lead Planner that your plan for Task ID `<task_id>` is complete and ready for review in `tasks/agent_<X>.md`.

**2.3. (Simulated) Implementation and Progress Tracking**

1.  **Follow Your Plan:** Execute each step of your documented plan sequentially.
2.  **Describe Actions:** For each step, clearly describe what you are doing and the specific code structure, logic, or content you are "writing" or "designing."
3.  **Update Task File (Optional):** Make interim updates to your "Notes/Plans by Agent `<X>`:" section for significant sub-steps or plan modifications.
4.  **Status Update:** If the task is substantial, you can update the `Status:` to "In Progress" when you begin the (simulated) implementation phase.

**2.4. Marking Sub-Steps and Tasks as Complete**

1.  **Sub-Step Completion:** As you complete major parts of your plan, you can indicate this within your notes.
2.  **Task Completion:** Once all acceptance criteria are met:
    *   Write a brief summary in the "Notes/Plans by Agent `<X>`:" section.
    *   Change the `Status:` to "Implemented" (or "Testing" if applicable, then "Completed").
    *   Notify the User/Lead Planner.

**2.5. Iteration and Feedback**

*   Be prepared for feedback. If changes are requested, update your plan in `tasks/agent_<X>.md` and proceed with revised steps.

## 3. Referencing Project Files and Key Documents

To effectively complete your assigned tasks, be familiar with and regularly reference key project documents and code locations.

**3.1. Core Project Guides**

*   **`IMPLEMENTATION_GUIDE.md`:** Central document for milestones, phases, technical specifications, and contribution guidelines.
*   **`README.md`:** High-level project overview, setup, and run instructions.
*   **`resourcing/sub-agent-briefing-guide.md` (This Document):** Explains your workflow and task management.
*   **`development-status.md`:** Tracks overall project status, priorities, and cross-agent dependencies. **It serves as the definitive source for current IPC channel names, expected payloads, and the status of shared integration points.** (see Section 6).

**3.2. Configuration Files**

*   **`config/llm_config.yaml`:** LLM configurations, API keys (placeholders), default models.
*   **`~/.jarules/user_state.json` (User-specific):** User preferences (active LLM, context settings).

**3.3. Key Source Code Directories**

*   **`jarules_agent/`**: Core Python backend.
    *   **`connectors/`**: LLM and other service connectors.
    *   **`core/`**: Core logic (e.g., `llm_manager.py`).
    *   **`git_task_runners/`**: Python scripts for Git-Split functionality.
*   **`jarules_electron_vue_ui/`**: Electron Vue.js frontend.
    *   **`src/components/`**: Vue components.
    *   **`public/preload.js` (Electron preload for Vue UI):** `window.api` bridge for IPC.
*   **`jarules_chat_ui/` (Main Electron app scripts):**
    *   **`main.js` (Electron's main.js):** Main Electron process, IPC handlers.
*   **`tasks/`**: Your `agent_<X>.md` task files.
*   **`tests/`**: Unit and integration tests.

**3.4. Task-Specific References**

*   Always check the "**Relevant Files/Links:**" section within your assigned task in `tasks/agent_<X>.md`.

If unsure, ask the User/Project Manager or Lead Planner.

## 4. Task Completion and Archival Process

Clear management of completed tasks is essential for maintaining focus and building a historical record.

**4.1. Finalizing a Task**

1.  **Meet Acceptance Criteria.**
2.  **Add Final Notes/Summary** to the "Notes/Plans..." section.
3.  **Update Status** to "Completed".
4.  **Add Completion Timestamp:** `**Completed On:** YYYY-MM-DD HH:MM UTC`.
5.  **Notify Lead/User.**

**4.2. Archival of Completed Task Assignments (Granular Method)**

To preserve the rich history of completed work and the detailed planning involved, individual components or significant sub-steps of a major task are archived. This keeps the main `tasks/agent_<X>.md` file focused on active work while building a detailed, searchable archive.

*   **Archival Trigger:** Initiated by the User/Project Manager or Lead Planner after they have reviewed and confirmed the completion of a major task (or significant sub-parts) that you've marked as "Implemented" or "Completed".
*   **Archival Location:** `tasks/completed_tasks/agent_<X>/`
*   **Archival Unit & Naming:**
    *   The Lead Planner (e.g., Jules) will identify the distinct, completed sub-components or planning sections within your "Notes/Plans by Agent `<X>`:" for the major task.
    *   For each such distinct sub-component/section:
        1.  The Lead Planner will copy the relevant Markdown content (e.g., the design and simulated implementation notes for a specific Vue component, or a specific backend module's plan). This should include the sub-component's description, any specific acceptance criteria if it had them, and all related notes and plans.
        2.  A **new file** is created in the archive directory:
            `TASKID-<OriginalTaskID>-<Description>-<AgentX>_<NN>.md`
            (e.g., `TASKID-20231027-120000-AGE-UIFORM-TaskDefinitionInput-AgentE_01.md`).
            The `<Description>` should be a short, descriptive name of the sub-component. `<NN>` is a sequential number for that agent's archived items.
        3.  The copied content is pasted into this new archive file. The file can optionally start with a header like `# Archived Sub-Task for Agent <X> - <Sub-Task Title> (from Main Task: <OriginalTaskID> - <OriginalTaskTitle>)`.
    *   **Updating the Active Task File:**
        *   Once all relevant sub-components of a major task are extracted and archived, the Lead Planner will then **delete the entire original major task block** (from its `### Task ID:` line down to its `---`) from the active `tasks/agent_<X>.md` file.
        *   If a major task is very large and is being archived in stages, the Lead Planner might instead append a note to the main task block in `tasks/agent_<X>.md` indicating which parts have been archived.

**4.3. Structure of an Archived Task File**
The archived file contains the specific record of that sub-component/step, including its portion of the description, criteria, and all associated detailed plans and notes made by the agent for that part. It should also reference the original parent Task ID.

**4.4. Benefits of this Archival Method**

*   **Preserves Rich, Granular History.**
*   **Clean Active Task Files.**
*   **Sequential Record** of an agent role's completed sub-components.
*   **Excellent for Documentation & Review.**

## 5. Benefits of This Detailed Task Management Process

Adopting this structured approach offers numerous advantages:

**5.1. Enhanced Clarity and Focus**
*   Clear assignments and focused work for agents.

**5.2. Rich, Contextual Documentation**
*   Task files become living documentation, capturing design rationale and implementation strategies.
*   Facilitates knowledge transfer and project reporting.

**5.3. Improved Planning and Reduced "Lost in the Weeds" Syndrome**
*   Encourages proactive, detailed planning, identifying issues early.
*   Provides micro-structure for tasks and traceability of decisions.

**5.4. Effective Collaboration and Review**
*   Enables targeted reviews of detailed plans.
*   Supports clear handoffs if necessary.

**5.5. Valuable Historical Record and Retrospectives**
*   Archived tasks provide an ordered, granular history for learning and improvement.
*   Helps analyze successes and identify areas for process refinement.

**5.6. Foundation for Quality**
*   Shared understanding of "done" via acceptance criteria.
*   Minimizes misunderstandings through written plans.

By committing to this process, we aim to build not just a functional application, but also a well-documented, understandable, and maintainable codebase.

## 6. Tracking Cross-Agent Dependencies (`development-status.md`)

While your individual task file (`tasks/agent_<X>.md`) will list dependencies specific to your tasks (using the new "Dependencies:" subsection in your plan), a central document, `development-status.md`, is used by the Lead Planner and User/Project Manager to track the overall project status and key cross-agent dependencies or integration points.

**6.1. Purpose of `development-status.md`**

*   **Project Dashboard:** Provides a high-level overview of project phases, current priorities, and the status of major features.
*   **Integration Point Tracking:** Contains a dedicated section (e.g., "Integration Points & Dependencies") that lists items like:
    *   IPC Channels: Which agent defines it, which agent(s) consume it, current status (e.g., "Defined," "Implemented," "Needs Testing").
    *   Shared Modules/APIs: Key backend or frontend modules that multiple agents' work will interact with.
    *   Data Contracts: Agreed-upon structures for data passed between components or services being developed by different agents.
*   **Identifying Blockers:** Helps identify potential blockers where one agent's work is waiting on a dependency from another.

**6.2. Your Role Regarding `development-status.md`**

*   **Awareness:** Be aware that this document exists as a central coordination point. Check it if you suspect a dependency might be blocking you or to see the status of components you depend on.
*   **Informing the Lead:** When your task involves *providing* a component or interface that other tasks/agents depend on (as listed in your "Dependencies" section or theirs), clearly note its completion status in your `tasks/agent_<X>.md` file. The Lead Planner will then update `development-status.md`.
*   **Flagging Issues:** If a dependency listed in your task is blocking your progress, highlight this in the "Open Questions for Lead" section of your task plan in `tasks/agent_<X>.md`. The Lead Planner can then update `development-status.md` if necessary and help resolve the blocker.

You are generally not expected to directly edit `development-status.md` unless specifically asked. Your primary focus remains your `tasks/agent_<X>.md` file. The `development-status.md` serves as a higher-level coordination tool for the project leadership.
