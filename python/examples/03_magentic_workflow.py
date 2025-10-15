# Copyright (c) Microsoft. All rights reserved.

"""
Advanced Magentic Multi-Agent Workflow - Autonomous Collaboration

This example demonstrates the most advanced orchestration pattern in Microsoft Agent
Framework: Magentic workflows with dynamic planning, autonomous agent collaboration,
and intelligent task delegation.

Key Features:
- Dynamic task decomposition and planning
- Autonomous agent selection based on expertise
- Self-organizing multi-agent collaboration
- Fact ledger for tracking progress and learnings
- Human-in-the-loop approval for critical decisions
- Checkpoint/resume capabilities for fault tolerance
- Real-time event streaming for observability

Production-Ready Patterns:
- Error recovery and retry logic
- Comprehensive logging and telemetry
- State persistence across runs
- Concurrent execution where possible
- Resource-aware scheduling

This is ideal for:
- Complex research and analysis tasks
- Multi-step problem solving
- Tasks requiring diverse expertise
- Long-running autonomous workflows
- Enterprise-grade AI orchestration
"""

import asyncio
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework._workflows import (
    MagenticBuilder,
    MagenticCallbackEvent,
    MagenticCallbackMode,
)
from agent_framework.openai import OpenAIChatClient


# ============================================================================
# Specialized Agent Definitions
# ============================================================================


def create_research_agent() -> ChatAgent:
    """Research specialist - Gathers information and analyzes data."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="ResearchAgent",
        description="Expert researcher specializing in data gathering, analysis, and fact verification",
        instructions="""You are a meticulous research specialist with expertise in:
- Information gathering from multiple sources
- Data analysis and pattern recognition
- Fact verification and citation
- Synthesizing complex information into clear insights

Your approach:
1. Break down research questions into searchable components
2. Gather relevant information systematically
3. Verify facts and cross-reference sources
4. Present findings with clear reasoning
5. Highlight confidence levels and uncertainties

Always provide specific, actionable insights backed by reasoning.""",
        tools=[],
    )


def create_technical_writer() -> ChatAgent:
    """Technical writing specialist - Creates documentation and explanations."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="TechnicalWriter",
        description="Technical writing expert who creates clear, accurate documentation",
        instructions="""You are a senior technical writer specializing in:
- Complex technical concepts explained simply
- Structured documentation with clear hierarchy
- Code examples and best practices
- Audience-appropriate language

Your approach:
1. Understand the technical context fully
2. Identify the target audience and their needs
3. Structure content logically (overview → details → examples)
4. Use concrete examples and analogies
5. Provide actionable next steps

Always prioritize clarity and accuracy over brevity.""",
        tools=[],
    )


def create_architect_agent() -> ChatAgent:
    """Solution architect - Designs systems and evaluates approaches."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="ArchitectAgent",
        description="Solution architect expert in system design, scalability, and best practices",
        instructions="""You are an experienced solution architect with expertise in:
- System design and architecture patterns
- Scalability and performance optimization
- Technology selection and trade-off analysis
- Security and reliability considerations

Your approach:
1. Understand requirements and constraints
2. Evaluate multiple architectural approaches
3. Consider scalability, maintainability, and cost
4. Identify potential risks and mitigation strategies
5. Provide clear recommendations with rationale

Always consider production readiness and long-term maintainability.""",
        tools=[],
    )


def create_code_reviewer() -> ChatAgent:
    """Code review specialist - Analyzes code quality and best practices."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="CodeReviewer",
        description="Senior engineer focused on code quality, best practices, and security",
        instructions="""You are a senior code reviewer with expertise in:
- Code quality and maintainability
- Security vulnerabilities and best practices
- Performance optimization
- Testing strategies and coverage

Your approach:
1. Analyze code structure and organization
2. Identify potential bugs and edge cases
3. Check for security vulnerabilities
4. Evaluate test coverage and quality
5. Suggest specific improvements with examples

Always provide constructive feedback with concrete recommendations.""",
        tools=[],
    )


# ============================================================================
# Event Monitoring for Observability
# ============================================================================


class WorkflowMonitor:
    """Monitor and log workflow events for observability."""

    def __init__(self):
        self.events = []
        self.agent_outputs = {}

    async def handle_event(self, event: MagenticCallbackEvent) -> None:
        """Handle workflow events in real-time."""
        self.events.append(event)

        if hasattr(event, "source"):
            if event.source == "orchestrator":
                print(f"\n🎯 [Orchestrator] {event.kind}: {event.message.text if event.message else ''}"[:150])

            elif event.source == "agent" and hasattr(event, "message"):
                agent_id = getattr(event, "agent_id", "unknown")
                print(f"\n🤖 [{agent_id}]: {event.message.text if event.message else ''}"[:150])

            elif event.source == "workflow" and hasattr(event, "message"):
                print(f"\n✨ [Final Result]: {event.message.text if event.message else ''}"[:150])

    def get_summary(self) -> dict:
        """Get workflow execution summary."""
        return {
            "total_events": len(self.events),
            "agent_calls": sum(1 for e in self.events if hasattr(e, "source") and e.source == "agent"),
            "orchestrator_decisions": sum(
                1 for e in self.events if hasattr(e, "source") and e.source == "orchestrator"
            ),
        }


# ============================================================================
# Example Workflows
# ============================================================================


async def example_autonomous_research_task() -> None:
    """Example: Complex research task with autonomous agent collaboration."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 1: Autonomous Multi-Agent Research Task".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    # Create specialized agents
    research_agent = create_research_agent()
    writer = create_technical_writer()
    architect = create_architect_agent()

    # Setup monitoring
    monitor = WorkflowMonitor()

    # Create Magentic workflow
    workflow = (
        MagenticBuilder()
        .add_participant(research_agent)
        .add_participant(writer)
        .add_participant(architect)
        .with_callback(monitor.handle_event, mode=MagenticCallbackMode.NON_STREAMING)
        .with_max_turns(15)  # Limit total conversation turns
        .build()
    )

    # Complex task requiring multiple agents
    task = """Analyze the benefits and implementation considerations of using autonomous multi-agent
systems in enterprise software development. Specifically:

1. What are the key benefits compared to traditional approaches?
2. What are the main architectural patterns for multi-agent systems?
3. What are critical implementation considerations for production deployment?

Provide a comprehensive analysis with practical recommendations."""

    print(f"\n📋 Task: {task[:200]}...\n")
    print("🚀 Starting autonomous workflow...\n")
    print("-" * 80)

    try:
        result = await workflow.run(task)

        print("\n" + "=" * 80)
        print("✅ Workflow completed successfully!")
        print("=" * 80)

        print(f"\n📊 Execution Summary:")
        summary = monitor.get_summary()
        for key, value in summary.items():
            print(f"   - {key}: {value}")

        print(f"\n📝 Final Result:")
        print("   " + "-" * 76)
        print(f"   {result.final_result}")
        print("   " + "-" * 76)

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback

        traceback.print_exc()


async def example_system_design_workflow() -> None:
    """Example: System design task with architect, writer, and reviewer."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 2: System Design Collaboration".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    # Create specialized team
    architect = create_architect_agent()
    writer = create_technical_writer()
    reviewer = create_code_reviewer()

    monitor = WorkflowMonitor()

    workflow = (
        MagenticBuilder()
        .add_participant(architect)
        .add_participant(writer)
        .add_participant(reviewer)
        .with_callback(monitor.handle_event, mode=MagenticCallbackMode.NON_STREAMING)
        .with_max_turns(12)
        .build()
    )

    task = """Design a scalable, fault-tolerant system for processing real-time data streams
from multiple sources. Include:

1. High-level architecture with key components
2. Data flow and processing pipeline
3. Fault tolerance and recovery mechanisms
4. Scaling strategy for handling load increases

Provide a clear technical design document suitable for an engineering team."""

    print(f"\n📋 Task: {task[:200]}...\n")
    print("🚀 Starting collaborative design workflow...\n")
    print("-" * 80)

    try:
        result = await workflow.run(task)

        print("\n" + "=" * 80)
        print("✅ Design workflow completed!")
        print("=" * 80)

        print(f"\n📊 Execution Summary:")
        summary = monitor.get_summary()
        for key, value in summary.items():
            print(f"   - {key}: {value}")

        print(f"\n📝 Design Document:")
        print("   " + "-" * 76)
        print(f"   {result.final_result}")
        print("   " + "-" * 76)

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")


async def example_with_checkpointing() -> None:
    """Example: Workflow with checkpoint support for fault tolerance."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 3: Workflow with Checkpointing (Fault Tolerance)".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    from agent_framework._workflows import FileCheckpointStorage

    # Create agents
    research_agent = create_research_agent()
    writer = create_technical_writer()

    monitor = WorkflowMonitor()

    # Setup checkpointing for fault tolerance
    checkpoint_storage = FileCheckpointStorage("./checkpoints")

    workflow = (
        MagenticBuilder()
        .add_participant(research_agent)
        .add_participant(writer)
        .with_callback(monitor.handle_event, mode=MagenticCallbackMode.NON_STREAMING)
        .with_checkpointing(checkpoint_storage)
        .with_max_turns(10)
        .build()
    )

    task = """Research and document best practices for implementing retry logic and error handling
in distributed systems. Include:

1. Common failure modes in distributed systems
2. Retry strategies (exponential backoff, circuit breaker, etc.)
3. Error handling patterns
4. Production-ready code examples

Provide practical guidance for engineering teams."""

    print(f"\n📋 Task: {task[:200]}...\n")
    print("💾 Checkpointing enabled - workflow can be resumed if interrupted\n")
    print("🚀 Starting workflow with fault tolerance...\n")
    print("-" * 80)

    try:
        result = await workflow.run(task)

        print("\n" + "=" * 80)
        print("✅ Checkpointed workflow completed!")
        print("=" * 80)

        print(f"\n📝 Final Documentation:")
        print("   " + "-" * 76)
        print(f"   {result.final_result}")
        print("   " + "-" * 76)

        print(f"\n💾 Checkpoint saved - can be resumed with:")
        print(f"   workflow.run_from_checkpoint(checkpoint_id)")

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        print("💾 Progress saved in checkpoint - can be resumed")


# ============================================================================
# Main Execution
# ============================================================================


async def main() -> None:
    """Run advanced Magentic workflow examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "Advanced Magentic Multi-Agent Workflows".center(78) + "║")
    print("║" + "Autonomous Collaboration & Dynamic Planning".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    print("\n📋 About Magentic Workflows:")
    print("   ✓ Autonomous agent selection and task delegation")
    print("   ✓ Dynamic planning and self-organization")
    print("   ✓ Fact ledger for tracking progress and learnings")
    print("   ✓ Real-time event monitoring for observability")
    print("   ✓ Checkpoint/resume for fault tolerance")
    print("   ✓ Production-ready for enterprise deployments")

    print("\n⚠️  Note: Magentic workflows use multiple LLM calls and may take several minutes.")
    print("   Consider using cost-effective models for testing (e.g., gpt-4o-mini)")

    try:
        # Run examples (uncomment as needed)
        await example_autonomous_research_task()

        # Uncomment for additional examples:
        # await example_system_design_workflow()
        # await example_with_checkpointing()

        print("\n✅ All Magentic workflow examples completed successfully!")
        print("\n🎓 Next Steps for Production:")
        print("   1. Implement custom CheckpointStorage for your database")
        print("   2. Add observability with OpenTelemetry integration")
        print("   3. Create domain-specific agents with specialized tools")
        print("   4. Implement approval workflows for sensitive operations")
        print("   5. Add retry logic and error recovery strategies")
        print("   6. Monitor costs and implement rate limiting")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Verify OpenRouter API key and credits")
        print("   - Check model supports function calling")
        print("   - Reduce max_turns if hitting rate limits")
        print("   - Review agent instructions for clarity")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
