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

    *   *(Agent <X> can add their detailed **high-level plan** here, breaking down how this major task will be approached, including designs for individual components or steps.)*

    **Key Decisions & Rationale:**
    *(Optional: Agent <X> to note key design choices or assumptions made during their planning)*
    - <Decision 1 with rationale>

    **Open Questions for Lead:**
    *(Optional: Agent <X> to list any questions or points needing clarification from the Lead Planner/User)*
    - <Question 1>

    **Dependencies:**
    *(Optional: Agent <X> to list dependencies this task has on other tasks, IPC channels, specific data, etc.)*
    - <Dependency 1: e.g., IPC Channel 'get-data' from Agent Y>

    **Verification Steps / Simulated Tests:**
    *(Agent <X> to outline how each part of their plan or the overall task's acceptance criteria will be verified through simulation or review. E.g., "1. Review component props/emits against parent. 2. Verbally confirm data flow for X feature.")*
    - <Verification step 1>

    **Simulated Implementation Details:**
    *(This section will be populated by the agent during the (simulated) execution phase, detailing the pseudo-code or specific design of each component/step. These detailed notes will be granularly archived upon task completion.)*
    ---
    *(Simulated Implementation Update for Component A)...*
    ---
    *(Simulated Implementation Update for Component B)...*
    ---

    **Relevant Files/Links:**
    - `IMPLEMENTATION_GUIDE.md` (Section: <Relevant Section>)
    - Link to specific designs if applicable.
    ---
    ```

**1.3. Workflow Cycle**

The general cycle for a task is:

1.  **Assignment:** A new task appears in your `tasks/agent_<X>.md` file with "Status: New".
2.  **Review & Plan:** You (the Sub-Agent) review the task and develop a detailed implementation plan directly within the "Notes/Plans by Agent `<X>`:" section of that task in your file, utilizing the new sub-sections for timestamps, decisions, questions, dependencies, and verification steps. You then update the task status to "Planning Complete".
3.  **Plan Approval (Optional but Recommended):** You notify the User/Lead Planner that your plan is ready for review. They provide feedback or approval.
4.  **Simulated Implementation & Progress Updates:** You "execute" your plan step-by-step (describing actions if you're an AI like Jules, or actually implementing if you're a human developer), populating the "Simulated Implementation Details" section. You update your task file with progress or any deviations from the plan. Task status might move to "In Progress".
5.  **Completion:** Once all aspects of a task are done according to its acceptance criteria and verification steps, you update its status to "Completed" and add any final summaries or outcomes to your notes in the task file.
6.  **Archival:** Completed task details are granularly archived, and the main task block (now a summary with pointers) is moved to the "Completed Tasks" section by the Lead Planner/User (details in Section 4).

This structured approach ensures that both the assignment of tasks and the detailed planning and execution by sub-agents are well-documented and aligned with overall project goals.

## 2. The Sub-Agent's Workflow

As a Sub-Agent (e.g., Agent A, Agent E), your workflow is centered around your dedicated task file (`tasks/agent_<X>.md`) and clear communication with the User/Project Manager or Lead Planner.

**2.1. Receiving and Understanding a Task**
(Content remains the same as previous version)

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
8.  **Document Your Plan:** Write this detailed plan directly into the "Notes/Plans by Agent `<X>`:" section, under the initial high-level plan area. Use Markdown formatting for clarity. The level of detail should be sufficient for another technically competent individual to understand your approach.
9.  **Document Key Decisions, Questions, and Dependencies:** Use the dedicated sub-sections ("Key Decisions & Rationale:", "Open Questions for Lead:", "Dependencies:") within "Notes/Plans by Agent `<X>`:" to explicitly note these important aspects of your plan.
10. **Define Verification Steps / Simulated Tests:** Within the "Verification Steps / Simulated Tests:" subsection, outline how you will confirm that your planned (and subsequently, simulated) implementation meets each acceptance criterion and functions as intended.
11. **Update Timestamp:** Whenever you significantly update your plan, update the "**Last Plan Update:**" timestamp at the beginning of your "Notes/Plans by Agent `<X>`:" section.
12. **Update Status:** Once your detailed plan (including verification steps) is documented, change the `Status:` field for that task in your file from "New" to "Planning Complete".
13. **Notify Lead/User:** Inform the User/Project Manager or Lead Planner that your plan for Task ID `<task_id>` is complete and ready for review in `tasks/agent_<X>.md`.

**2.3. (Simulated) Implementation and Progress Tracking**
(Content remains the same as previous version, but refers to populating "Simulated Implementation Details" section)

**2.4. Marking Sub-Steps and Tasks as Complete**
(Content remains the same as previous version)

**2.5. Iteration and Feedback**
(Content remains the same as previous version)

## 3. Referencing Project Files and Key Documents
(Content remains largely the same, ensure `development-status.md` bullet point is updated)

*   **`IMPLEMENTATION_GUIDE.md`:** ...
*   **`README.md`:** ...
*   **`resourcing/sub-agent-briefing-guide.md` (This Document):** ...
*   **`development-status.md`:** Tracks overall project status, priorities, and cross-agent dependencies. **It serves as the definitive source for current IPC channel names, expected payloads, and the status of shared integration points.** (see Section 6).

(Rest of Section 3 remains the same)

## 4. Task Completion and Archival Process
(This section is significantly revised)

**4.1. Finalizing a Task**
(Content remains the same: Meet AC, Final Notes, Update Status to "Completed", Add Completion Timestamp, Notify Lead)

**4.2. Archival of Completed Task Assignments (Refined Granular Method)**

To preserve the rich history of detailed work while maintaining a clean and informative active task file for each agent, we follow a refined archival process.

*   **Archival Trigger:** Initiated by the User/Project Manager or Lead Planner after they have reviewed and confirmed the completion of a major task you've marked as "Completed".
*   **Archival Location for Details:** `tasks/completed_tasks/agent_<X>/`
*   **Archival Steps (performed by Lead Planner, e.g., Jules, via subtasks):**

    1.  **Identify Detailed Implementation Blocks:** The Lead Planner reviews the "Simulated Implementation Details:" subsection within the completed task in `tasks/agent_<X>.md`. Each distinct component design or detailed simulated implementation block is identified.
    2.  **Create Granular Archive Files:** For each identified detailed block:
        *   The Lead Planner copies this specific Markdown content.
        *   A **new file** is created in the archive directory: `TASKID-<OriginalTaskID>-<Description>-<AgentX>_<NN>.md` (e.g., `TASKID-20231027-120000-AGE-UIFORM-TaskDefinitionInput-AgentE_01.md`). The `<Description>` should be a short name of the sub-component/step, and `<NN>` is a sequential number.
        *   The copied content is pasted into this new archive file, usually with a header referencing the original main task.
    3.  **Update the Main Task Block in `tasks/agent_<X>.md`:**
        *   The original major task block (for the `Task ID` just processed) in the "## Active Tasks" section of `tasks/agent_<X>.md` is modified:
            *   Its `Status:` is confirmed as "Completed".
            *   A `**Completed On:** YYYY-MM-DD HH:MM UTC` line is added/updated.
            *   The detailed "Simulated Implementation Details:" subsection (containing all the individual update blocks) is **replaced** with a pointer section, for example:
                ```markdown
                **Simulated Implementation Details:**
                *The detailed simulated implementation for each component/step of this task has been granularly archived to `tasks/completed_tasks/agent_<X>/` under files prefixed with `<TaskID>-`. Please refer to those files for specific component designs and simulated code walk-throughs. Example archived files for this task:*
                - `TASKID-<OriginalTaskID>-<Description1>-<AgentX>_01.md`
                - `TASKID-<OriginalTaskID>-<Description2>-<AgentX>_02.md`
                *(The agent's high-level plan, key decisions, open questions, dependencies, and verification steps remain in this summary block).*
                ```
    4.  **Move Summary Task Block to "Completed Tasks":**
        *   This entire modified task block (now a summary containing the initial plan, verification steps, and pointers to the detailed archive) is then cut from the "## Active Tasks" section and pasted at the top of the "## Completed Tasks" section within the same `tasks/agent_<X>.md` file.

This refined process ensures the active task file remains manageable, the agent's high-level strategic plan for a task is preserved with its completion status, and the highly detailed step-by-step simulated implementation work is archived granularly for deep-dive reviews and historical record-keeping.

(Section 4.3 and 4.4 would then refer to these granular archived files and the benefits of *this specific* archival method)

## 5. Benefits of This Detailed Task Management Process
(Content remains the same)

## 6. Tracking Cross-Agent Dependencies (`development-status.md`)
(Content remains the same)
