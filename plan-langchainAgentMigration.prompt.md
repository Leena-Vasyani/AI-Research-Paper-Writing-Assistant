## Plan: LangChain Agent Migration

The cleanest path is a backend-first rewrite around a shared LangGraph runtime, with the current RAG implementation reused as the retrieval/memory core. Since you allowed API/UI changes, the migration can optimize the agent boundaries instead of preserving the old request/response shapes.

**Steps**

1. Define the target architecture and state model.
   - Inventory the existing agent responsibilities in [backend/core_agents/](backend/core_agents) and [backend/fine_tuning/fine_tuned_drafting_agent.py](backend/fine_tuning/fine_tuned_drafting_agent.py).
   - Group them into LangChain tools, LangGraph nodes, and retrieval components.
   - Decide which flows become standalone graphs and which remain helper utilities.

2. Build the shared runtime layer.
   - Create common graph state, tool, and message schemas.
   - Wrap the existing provider fallback logic from [backend/core_agents/llm_provider.py](backend/core_agents/llm_provider.py) so LangChain models can reuse it.
   - Add shared retry, logging, and error-reporting behavior.

3. Rebuild the agents as graph-backed workflows.
   - Convert query, retrieval, summarization, citation, plagiarism, diagram, pseudocode, GitHub-to-IEEE, and doc-chat flows into LangChain chains or LangGraph subgraphs.
   - Reuse [backend/core_agents/rag_agent.py](backend/core_agents/rag_agent.py) as the retrieval/memory foundation instead of replacing it.
   - Split large monolithic flows into smaller tool nodes.

4. Redesign the API contract and orchestration.
   - Update [backend/api/main/**init**.py](backend/api/main/__init__.py) to route through the new runtime instead of direct singleton agent calls.
   - Revise [backend/api/schemas.py](backend/api/schemas.py) to match the new graph outputs and richer status/error metadata.
   - Add adapter layers only where needed for serialization or validation.

5. Update the frontend and docs to match the new outputs.
   - Refresh [web/src/lib/types.ts](web/src/lib/types.ts) and the consuming pages so they match the redesigned API.
   - Update [web/src/app/workflow/page.tsx](web/src/app/workflow/page.tsx), [web/src/app/smart-drafter/page.tsx](web/src/app/smart-drafter/page.tsx), [web/src/app/doc-chat/](web/src/app/doc-chat), and [web/src/app/agent-hub/page.tsx](web/src/app/agent-hub/page.tsx).
   - Rewrite the agent and feature docs under [docs/agents/](docs/agents) and [docs/features/](docs/features).

6. Validate in slices.
   - Start with the RAG/doc-chat path and the citation flow as the first proof of the new runtime.
   - Migrate the workflow pipeline next, since it exercises the most integrations.
   - Finish with the smaller single-purpose agents and documentation cleanup.

7. -optimize api latencies by parallelizing independent graph nodes and tools where possible, and by adding caching layers for expensive operations.

- Add monitoring and alerting around the new runtime to quickly identify and resolve any performance regressions or errors after deployment.
- Gather user feedback on the new agent behaviors and outputs, and iterate on the graph designs and API contracts as needed to improve usability and value.
- Plan a phased rollout of the new agents, starting with an internal beta for power users before a full public release, to ensure stability and gather early feedback.
- Continuously evaluate new features and capabilities in the LangChain ecosystem that could further enhance the agents, such as new tool integrations, memory management improvements, or advanced reasoning capabilities, and plan for their adoption in future iterations.
- Establish a regular review cadence for the agent implementations and their underlying graphs to ensure they remain aligned with user needs and the evolving capabilities of the LLMs and tools they integrate with.
  -keep latencys low by optimizing the graph structures, minimizing unnecessary tool calls, and leveraging asynchronous execution where possible to allow for parallel processing of independent nodes.
- Implement robust error handling and fallback strategies within the graphs to gracefully handle failures in individual nodes or tools, ensuring that the overall agent can still provide useful responses even when some components encounter issues.
- Enhance the observability of the agent executions by adding detailed logging, tracing, and metrics around the graph executions, tool calls, and model interactions, to facilitate debugging and performance tuning.
- Foster a culture of continuous improvement and learning within the team by regularly sharing insights, challenges, and successes from the migration process, and by encouraging experimentation with new graph designs, tool integrations, and LLM capabilities to drive ongoing innovation in the agent implementations.

8- use different models for different nodes/tools based on their specific requirements, such as using a smaller, faster model for simple classification tasks and a larger, more capable model for complex reasoning or generation tasks, to optimize both performance and output quality across the agents.

- Implement a dynamic model selection mechanism within the runtime that can route different nodes or tools to different models based on the task at hand, the current load, or user preferences, to further optimize the performance and cost-effectiveness of the agents.
- Explore the use of fine-tuning or prompt engineering techniques to optimize the performance of specific nodes or tools within the graphs, such as training a custom model for a specific classification task or designing specialized prompts for certain reasoning tasks, to enhance the overall effectiveness of the agents.
- Continuously monitor the performance and output quality of the different models used across the agents, and adjust the model selection strategies as needed based on empirical results and user feedback, to ensure that the agents are consistently delivering high-quality responses while maintaining efficient performance.

9.Drafting agent current give very poor results, we can consider two paths: 1) migrate it as-is and then optimize with fine-tuning and prompt engineering, or 2) redesign the drafting flow upfront to better leverage the capabilities of the new runtime and models, potentially incorporating more iterative refinement steps, tool calls, or user feedback loops to enhance the output quality from the start. 3) consider integrating a specialized model or fine-tuning a model specifically for the drafting task, to improve the quality of the outputs without requiring extensive redesign of the graph structure. 4) gather detailed requirements and examples of the desired drafting outputs from users to inform the redesign or fine-tuning efforts, ensuring that the improvements are closely aligned with user needs and expectations. 5) implement a phased approach to improving the drafting agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the drafting outputs over time.

10)try implementing caching layer for agent outputs, especially for expensive operations like retrieval or complex reasoning, to improve response times for repeated queries or similar inputs, while ensuring that the cache is properly invalidated when underlying data changes to maintain accuracy and relevance of the responses.

- Explore the use of vector databases or other efficient storage mechanisms for caching intermediate results or retrieved documents, to further optimize the performance of the agents while maintaining the ability to quickly access relevant information when needed.
- Implement a configurable caching strategy that allows for different cache durations or policies based on the type of operation, the expected frequency of similar queries, and the importance of freshness in the responses, to balance performance improvements with the need for up-to-date information.
- Monitor the cache hit rates and the impact of caching on overall performance and response quality, and adjust the caching strategies as needed based on empirical results and user feedback, to ensure that the caching layer is effectively enhancing the performance of the agents without compromising the relevance or accuracy of the responses.
- Continuously evaluate new caching technologies and strategies that could further enhance the performance of the agents, such as in-memory caches, distributed caching systems, or advanced eviction policies, and plan for their adoption in future iterations to maintain optimal performance as the agents evolve and scale.

11. summarization agent could benefit from a more modular design that allows for different summarization strategies or models to be easily swapped in and out based on the specific use case or user preferences, such as extractive vs. abstractive summarization, or different levels of summary detail.

- Consider implementing a multi-stage summarization process within the graph, where an initial extractive summary is generated to identify key points, followed by an abstractive refinement step that produces a more coherent and natural summary, to enhance the quality of the outputs while still maintaining efficiency.
- Explore the use of specialized models or fine-tuning techniques for the summarization task, to improve the relevance and coherence of the summaries without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired summarization outputs from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the summarization agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the summaries over time.
- Continuously monitor the performance and output quality of the summarization agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality summaries that meet user needs while maintaining efficient performance.

12. For the citation agent, consider implementing a more robust retrieval and ranking mechanism to ensure that the most relevant and high-quality sources are suggested for citation, potentially incorporating additional metadata or contextual information about the sources to enhance the relevance of the suggestions.

- Explore the use of specialized models or fine-tuning techniques for the citation suggestion task, to improve the accuracy and relevance of the suggestions without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired citation suggestions from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the citation agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the citation suggestions over time.
- Continuously monitor the performance and output quality of the citation agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality citation suggestions that meet user needs while maintaining efficient performance.

13. For the plagiarism agent, consider implementing a more comprehensive detection mechanism that incorporates multiple strategies for identifying potential plagiarism, such as text similarity analysis, source attribution checks, and contextual understanding of the content, to enhance the accuracy and reliability of the detections.

- Explore the use of specialized models or fine-tuning techniques for the plagiarism detection task, to improve the accuracy and relevance of the detections without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired plagiarism detection outputs from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the plagiarism agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the plagiarism detections over time.
- Continuously monitor the performance and output quality of the plagiarism agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality plagiarism detections that meet user needs while maintaining efficient performance.

14. for retrival agent, consider implementing a more advanced retrieval strategy that incorporates semantic search capabilities, relevance feedback loops, and dynamic query reformulation based on user interactions and preferences, to enhance the relevance and quality of the retrieved results.

- Explore the use of specialized models or fine-tuning techniques for the retrieval task, to improve the accuracy and relevance of the retrieved results without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired retrieval outputs from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the retrieval agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the retrieved results over time.
- Continuously monitor the performance and output quality of the retrieval agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality retrieval results that meet user needs while maintaining efficient performance.
- currently retrieval agent is used in both the workflow and doc-chat flows, so improvements here will have a broad impact across multiple user journeys, making it a high-priority target for optimization efforts after the migration to ensure that the enhanced retrieval capabilities benefit as many users as possible and retriving paper are relevant and up to date and based on user query.

14. keyword agent could be enhanced by implementing a more sophisticated keyword extraction and ranking mechanism that incorporates contextual understanding of the content, relevance to the user's query, and potential impact on downstream tasks, to ensure that the most useful and relevant keywords are identified and prioritized for use in the agents' workflows.

- Explore the use of specialized models or fine-tuning techniques for the keyword extraction task, to improve the accuracy and relevance of the extracted keywords without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired keyword extraction outputs from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the keyword agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the keyword extractions over time.
- Continuously monitor the performance and output quality of the keyword agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality keyword extractions that meet user needs while maintaining efficient performance.
- currently keyword agent doesnt have a dedicated API route and is only used as a helper utility within the workflow and doc-chat flows, so improvements here will enhance the performance and relevance of the keywords used across multiple agents and user journeys, making it an important target for optimization efforts after the migration to ensure that the enhanced keyword extraction capabilities benefit as many users as possible and contribute to more relevant and effective agent outputs.
  -and it doesnt have sematic understanding of the content, so it may extract keywords that are not actually relevant to the user's query or the downstream tasks, leading to suboptimal performance of the agents that rely on those keywords. By implementing a more sophisticated keyword extraction mechanism that incorporates contextual understanding and relevance ranking, we can ensure that the most useful and relevant keywords are identified and prioritized for use in the agents' workflows, ultimately enhancing the overall performance and user satisfaction with the agents' outputs.

14)for github to ieee agent, consider implementing a more robust mapping and transformation mechanism that can effectively convert GitHub repository information into the IEEE format, potentially incorporating additional metadata or contextual information about the repositories to enhance the relevance and accuracy of the generated IEEE outputs.

- Explore the use of specialized models or fine-tuning techniques for the GitHub-to-IEEE conversion task, to improve the quality and relevance of the generated outputs without requiring extensive redesign of the graph structure.
- Gather detailed requirements and examples of the desired GitHub-to-IEEE outputs from users to inform the design and optimization efforts, ensuring that the improvements are closely aligned with user needs and expectations.
- Implement a phased approach to improving the GitHub-to-IEEE agent, starting with the migration of the existing flow, followed by iterative enhancements based on user feedback and performance metrics, to continuously refine the quality of the generated IEEE outputs over time.
- Continuously monitor the performance and output quality of the GitHub-to-IEEE agent, and adjust the strategies and models used as needed based on empirical results and user feedback, to ensure that the agent is consistently delivering high-quality IEEE outputs that meet user needs while maintaining efficient performance.
- ITS FORMATING IS POOR AND OFTEN INACCURATE, SO improving the mapping and transformation mechanism to better capture the relevant information from GitHub repositories and convert it into a more accurate and well-formatted IEEE output will significantly enhance the usefulness and reliability of this agent for users who rely on it for generating IEEE citations or summaries based on GitHub content.
- ALSO ADD DIAGRAMS FOR THE ARCHITECTURE AND DATA FLOWS TO THE DOCS TO BETTER ILLUSTRATE THE NEW RUNTIME DESIGN AND HOW THE AGENTS INTERACT WITH IT, WHICH WILL AID IN BOTH THE IMPLEMENTATION AND THE ONGOING MAINTENANCE OF THE SYSTEM BY PROVIDING CLEAR VISUAL REFERENCES FOR DEVELOPERS AND STAKEHOLDERS TO DOCUMENT PRODUCE

15. CURRENT BACKENT STRUCTURE IS NOT WELL-SUITED FOR THE GRAPH-BASED RUNTIME, SO a significant refactor of the backend architecture will be needed to accommodate the new design, including changes to how state is managed, how tools and models are integrated, and how the API routes are structured to interact with the graph-based agents. This refactor should focus on creating a clean separation of concerns, modular components, and clear interfaces to ensure that the new architecture is maintainable and scalable as the agents evolve and new features are added over time.

- During the refactor, it's important to maintain a focus on performance optimization, ensuring that the new architecture can support efficient execution of the graph-based agents while minimizing latency and resource usage, especially for complex workflows that involve multiple tool calls and model interactions.
- Additionally, thorough testing and validation will be crucial throughout the refactor process to ensure that the new architecture is functioning correctly and that the migrated agents are delivering accurate and high-quality outputs without regressions in performance or functionality compared to the previous implementation.
- FILE STRUCTURE CHANGES: the backend file structure will likely need to be reorganized to better align with the new architecture, such as grouping related components together (e.g., all graph-related code in a dedicated directory), and potentially introducing new layers of abstraction to manage the complexity of the graph-based agents and their interactions with tools and models. This reorganization should aim to improve the clarity and maintainability of the codebase while supporting the new design principles introduced by the migration to a graph-based runtime.
- THE API CONTRACTS WILL CHANGE: with the new graph-based design, the API contracts for the agents will likely need to be redesigned to accommodate the richer outputs and more complex interactions that the graphs enable. This may involve changes to the request and response schemas, as well as updates to the frontend to handle the new data structures and potentially new features or capabilities exposed by the graph-based agents. It's important to carefully design these new API contracts to ensure they are intuitive, flexible, and aligned with user needs while also supporting the enhanced capabilities of the new agent implementations.
- THE FRONTEND WILL ALSO NEED TO BE UPDATED: to accommodate the changes in the API contracts and to take advantage of the new capabilities offered by the graph-based agents, the frontend will need to be updated accordingly. This may involve changes to the data types and structures used in the frontend, updates to the UI components to display the richer outputs from the agents, and potentially new features or interactions that leverage the enhanced capabilities of the new agent implementations. It's important to ensure that these frontend updates are well-aligned with the backend changes and that they provide a seamless and improved user experience that takes full advantage of the new graph-based design of the agents.
- ALL STRUCTURE NEED TO BE INDUSTRY STANDARD AND BEST PRACTICES TO ENSURE MAINTAINABILITY AND SCALABILITY OF THE CODEBASE AS THE AGENTS EVOLVE AND NEW FEATURES ARE ADDED OVER TIME, while also ensuring that the new architecture is well-documented and that the development team is aligned on the design principles and implementation details to facilitate a smooth migration process and ongoing maintenance of the system after the migration is complete.LIKE MIDDLEWARE FOR HANDLING COMMON CONCERNS SUCH AS AUTHENTICATION, LOGGING, ERROR HANDLING, AND PERFORMANCE MONITORING ACROSS THE NEW GRAPH-BASED AGENTS, to ensure consistency and efficiency in how these concerns are addressed across the different agent implementations and to reduce duplication of code and effort in handling these common aspects of the system's functionality.
  -CONTROLLER LAYER: introduce a controller layer that acts as an intermediary between the API routes and the graph-based agents, responsible for orchestrating the execution of the graphs, managing the flow of data between the API and the agents, and handling any necessary transformations or adaptations of the data to fit the new graph-based design. This controller layer can help to decouple the API routes from the specific implementations of the agents, allowing for greater flexibility and maintainability in how the agents are structured and how they evolve over time.
  ETC

**Relevant files**

- [backend/api/main/**init**.py](backend/api/main/__init__.py) — current FastAPI orchestration.
- [backend/api/schemas.py](backend/api/schemas.py) — request/response contracts that will change.
- [backend/core_agents/llm_provider.py](backend/core_agents/llm_provider.py) — provider fallback logic to reuse.
- [backend/core_agents/rag_agent.py](backend/core_agents/rag_agent.py) — best existing LangChain-based foundation.
- [backend/core_agents/query_agent.py](backend/core_agents/query_agent.py), [backend/core_agents/retrieval_agent.py](backend/core_agents/retrieval_agent.py), [backend/core_agents/summarization_agent.py](backend/core_agents/summarization_agent.py), [backend/core_agents/citation_agent.py](backend/core_agents/citation_agent.py) — main migration targets.
- [backend/core_agents/plagiarism_agent.py](backend/core_agents/plagiarism_agent.py), [backend/core_agents/diagram_agent.py](backend/core_agents/diagram_agent.py), [backend/core_agents/pseudocode_agent.py](backend/core_agents/pseudocode_agent.py), [backend/core_agents/github_paper_agent.py](backend/core_agents/github_paper_agent.py) — additional graph/tool conversions.
- [backend/fine_tuning/fine_tuned_drafting_agent.py](backend/fine_tuning/fine_tuned_drafting_agent.py) — drafting integration.
- [web/src/lib/types.ts](web/src/lib/types.ts) and the app routes under [web/src/app/](web/src/app) — UI contract updates.
- [docs/agents/](docs/agents) and [docs/features/](docs/features) — behavior documentation updates.

**Verification**

1. Run the backend smoke import test after the runtime refactor.
2. Run the frontend lint and build checks after the API contract changes.
3. Exercise the migrated flows end to end: query/retrieve/summarize/draft, citation suggestion, and doc-chat retrieval.
4. Confirm the updated response shapes render correctly in the workflow and agent-hub UIs.

**Decisions**

- Breaking API/UI changes are allowed, so the plan favors a cleaner architecture over compatibility shims.
- The current RAG implementation is the best existing subsystem to reuse.
- Migration should still be incremental, but preserving old contracts is not a hard requirement.

If you want, I can turn this into an implementation-ready task breakdown next.

-THIS IS A HIGH-LEVEL PLAN INTENDED TO GUIDE THE MIGRATION EFFORT, but the specific implementation details and task breakdown will need to be developed in collaboration with the engineering team responsible for the migration, taking into account the team's expertise, the complexity of the existing codebase, and any additional requirements or constraints that may arise during the planning and execution of the migration process. It's important to maintain flexibility in the plan to accommodate any unforeseen challenges or opportunities that may arise as the team delves into the implementation details and begins to execute on the migration tasks.

- IT HAS TO BE ITERATIVE AND INCREMENTAL, with a focus on validating each step of the migration through testing and user feedback to ensure that the new architecture and agent implementations are delivering the expected improvements in performance, output quality, and user experience without introducing regressions or issues compared to the previous implementation. This iterative approach will allow the team to make adjustments and refinements as needed based on real-world results and user feedback, ultimately leading to a more successful migration outcome.
- IT HAS TO BE WELL-DOCUMENTED, with clear explanations of the new architecture, design decisions, and implementation details to ensure that the development team and stakeholders have a shared understanding of the migration process and the resulting system. This documentation should include both high-level overviews and detailed technical information to support both strategic planning and day-to-day development activities throughout the migration effort.
  -IT HAS TO BE carried out in phased manner to minimize disruption to users and allow for continuous validation and improvement of the new architecture and agent implementations, starting with internal testing and validation before rolling out to a broader user base, and gathering feedback at each stage to inform subsequent phases of the migration process. This phased approach will help to ensure a smoother transition for users and allow the team to address any issues or challenges that arise during the migration in a controlled and manageable way.

-ui has to be updated to accommodate the new API contracts and to take advantage of the enhanced capabilities offered by the graph-based agents, ensuring that the user experience is improved and that users can fully leverage the benefits of the new architecture and agent implementations. This may involve changes to the data types and structures used in the frontend, updates to the UI components to display the richer outputs from the agents, and potentially new features or interactions that leverage the enhanced capabilities of the new agent implementations. It's important to ensure that these frontend updates are well-aligned with the backend changes and that they provide a seamless and improved user experience that takes full advantage of the new graph-based design of the agents and speed of the responses and site has to be fast and responsive.
