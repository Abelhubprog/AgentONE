# Copyright (c) Microsoft. All rights reserved.

"""
Sequential Multi-Agent Workflow - Writer & Reviewer Collaboration

This example demonstrates advanced multi-agent orchestration using the Microsoft
Agent Framework with OpenRouter. It showcases:

- Sequential workflow pattern (Writer → Reviewer → Writer refinement)
- Agent-to-agent handoff with context preservation
- Tool sharing between specialized agents
- Iterative refinement loops
- Production-ready error handling and logging

This pattern is ideal for:
- Content creation and review pipelines
- Code generation and validation
- Research and fact-checking workflows
- Any multi-step process requiring specialized expertise
"""

import asyncio
from typing import Annotated

from agent_framework import ChatAgent, ChatMessage
from agent_framework.openai import OpenAIChatClient


# ============================================================================
# Tool Definitions - Shared across agents
# ============================================================================


def count_words(text: Annotated[str, "The text to count words in"]) -> int:
    """Count the number of words in a text."""
    return len(text.split())


def check_keyword_presence(
    text: Annotated[str, "The text to check"],
    keywords: Annotated[list[str], "Keywords to look for"],
) -> dict[str, bool]:
    """Check if specific keywords are present in the text."""
    text_lower = text.lower()
    return {keyword: keyword.lower() in text_lower for keyword in keywords}


def sentiment_analyzer(text: Annotated[str, "The text to analyze"]) -> str:
    """Analyze the sentiment of text (simplified mock implementation)."""
    positive_words = ["great", "excellent", "good", "amazing", "wonderful", "fantastic"]
    negative_words = ["bad", "poor", "terrible", "awful", "horrible"]

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"


# ============================================================================
# Agent Creation - Specialized roles with distinct instructions
# ============================================================================


def create_writer_agent() -> ChatAgent:
    """Create a specialized content writer agent."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="ContentWriter",
        instructions="""You are a professional content writer specializing in technology topics.

Your responsibilities:
- Create engaging, clear, and concise content
- Use simple language accessible to a general audience
- Include specific examples and benefits
- Follow the reviewer's feedback precisely
- Maintain a positive and informative tone

When creating content:
1. Start with a compelling hook
2. Explain key concepts clearly
3. Provide concrete benefits or examples
4. End with a strong conclusion or call-to-action

Word count target: 150-200 words unless specified otherwise.""",
        tools=[count_words, check_keyword_presence],
    )


def create_reviewer_agent() -> ChatAgent:
    """Create a specialized content reviewer agent."""
    client = OpenAIChatClient()
    return client.create_agent(
        name="ContentReviewer",
        instructions="""You are an expert content reviewer and editor with high standards.

Your responsibilities:
- Provide detailed, actionable feedback
- Check for clarity, accuracy, and engagement
- Verify keyword inclusion when specified
- Suggest specific improvements
- Be constructive but thorough

Review criteria:
1. CLARITY: Is the message clear and easy to understand?
2. ENGAGEMENT: Does it capture attention and maintain interest?
3. ACCURACY: Are claims factual and well-supported?
4. STRUCTURE: Is the content well-organized?
5. TONE: Is the tone appropriate for the audience?

Provide feedback in this format:
- Overall Assessment: [Good/Needs Improvement]
- Strengths: [List 2-3 strengths]
- Issues: [List specific problems if any]
- Suggestions: [Concrete recommendations for improvement]
- Approval Status: [APPROVED / REVISE]""",
        tools=[count_words, sentiment_analyzer, check_keyword_presence],
    )


# ============================================================================
# Sequential Workflow Implementation
# ============================================================================


async def sequential_writer_reviewer_workflow(
    task: str, max_iterations: int = 3
) -> tuple[str, list[dict[str, str]]]:
    """
    Execute a sequential writer-reviewer workflow with iterative refinement.

    Args:
        task: The writing task/prompt
        max_iterations: Maximum number of revision cycles

    Returns:
        Tuple of (final_content, conversation_history)
    """
    print("\n" + "=" * 80)
    print("🚀 Starting Sequential Multi-Agent Workflow")
    print("=" * 80)

    writer = create_writer_agent()
    reviewer = create_reviewer_agent()

    conversation_history = []
    current_content = None
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n📝 Iteration {iteration}/{max_iterations}")
        print("-" * 80)

        # ====================================================================
        # Phase 1: Writer creates/refines content
        # ====================================================================
        if current_content is None:
            # Initial creation
            writer_prompt = f"Create content for the following task:\n\n{task}"
            print(f"\n✍️  Writer: Creating initial content...")
        else:
            # Refinement based on feedback
            writer_prompt = f"""Revise the following content based on the reviewer's feedback:

CURRENT CONTENT:
{current_content}

REVIEWER FEEDBACK:
{conversation_history[-1]['feedback']}

Please provide an improved version addressing all feedback points."""
            print(f"\n✍️  Writer: Revising content based on feedback...")

        writer_response = await writer.run(writer_prompt)
        current_content = str(writer_response)

        print(f"\n📄 Content (Word count: {count_words(current_content)}):")
        print(f"   {current_content[:200]}..." if len(current_content) > 200 else f"   {current_content}")

        # ====================================================================
        # Phase 2: Reviewer evaluates content
        # ====================================================================
        print(f"\n🔍 Reviewer: Evaluating content...")

        review_prompt = f"""Please review the following content:

{current_content}

Original task: {task}

Provide your detailed feedback following the review criteria."""

        review_response = await reviewer.run(review_prompt)
        feedback = str(review_response)

        print(f"\n💬 Feedback:")
        print(f"   {feedback[:300]}..." if len(feedback) > 300 else f"   {feedback}")

        # Store conversation turn
        conversation_history.append(
            {"iteration": iteration, "content": current_content, "feedback": feedback}
        )

        # ====================================================================
        # Phase 3: Check if approved
        # ====================================================================
        if "APPROVED" in feedback.upper() and "REVISE" not in feedback.upper():
            print(f"\n✅ Content approved after {iteration} iteration(s)!")
            break
        elif iteration == max_iterations:
            print(f"\n⚠️  Max iterations ({max_iterations}) reached. Using current version.")
        else:
            print(f"\n🔄 Revision needed, continuing to iteration {iteration + 1}...")

    print("\n" + "=" * 80)
    print("✨ Workflow completed!")
    print("=" * 80)

    return current_content, conversation_history


# ============================================================================
# Example Use Cases
# ============================================================================


async def example_blog_post_creation() -> None:
    """Example: Create a blog post with AI review cycles."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 1: Blog Post Creation with Iterative Review".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    task = """Write a blog post introduction about the benefits of autonomous multi-agent systems in enterprise software.

Requirements:
- Target audience: CTOs and engineering leaders
- Include keywords: "autonomous agents", "scalability", "efficiency"
- Length: 150-200 words
- Tone: Professional but engaging"""

    final_content, history = await sequential_writer_reviewer_workflow(task, max_iterations=2)

    print("\n📊 Workflow Summary:")
    print(f"   - Total iterations: {len(history)}")
    print(f"   - Final word count: {count_words(final_content)}")
    print(f"   - Final content length: {len(final_content)} characters")

    print("\n📝 Final Approved Content:")
    print("   " + "-" * 76)
    print(f"   {final_content}")
    print("   " + "-" * 76)


async def example_product_description() -> None:
    """Example: Create a product description with quality review."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 2: Product Description Creation".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    task = """Create a compelling product description for an AI-powered task automation platform.

Requirements:
- Highlight: Time savings, error reduction, ease of use
- Include a clear value proposition
- Length: 100-150 words
- Tone: Confident and benefit-focused"""

    final_content, history = await sequential_writer_reviewer_workflow(task, max_iterations=3)

    print("\n📊 Workflow Summary:")
    print(f"   - Total iterations: {len(history)}")
    print(f"   - Revisions made: {len(history) - 1}")

    print("\n📝 Final Approved Content:")
    print("   " + "-" * 76)
    print(f"   {final_content}")
    print("   " + "-" * 76)


async def example_with_thread_persistence() -> None:
    """Example: Using threads for conversation persistence."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║  Example 3: Workflow with Thread Persistence".center(80) + "║")
    print("╚" + "=" * 78 + "╝")

    writer = create_writer_agent()
    thread = writer.get_new_thread()

    # Initial content creation
    task = "Write a one-paragraph summary of the benefits of continuous integration."
    print(f"\n📝 Task: {task}")

    result1 = await writer.run(task, thread=thread)
    print(f"\n✍️  Writer (Initial): {result1}")

    # Refinement using the same thread (maintains context)
    refinement = "Make it more technical and add a specific example."
    result2 = await writer.run(refinement, thread=thread)
    print(f"\n✍️  Writer (Refined): {result2}")

    print(f"\n💾 Thread contains {len(thread._messages)} messages with full context")


# ============================================================================
# Main Execution
# ============================================================================


async def main() -> None:
    """Run all sequential workflow examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "Sequential Multi-Agent Workflow Examples".center(78) + "║")
    print("║" + "Writer & Reviewer Collaboration Pattern".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    print("\n📋 Prerequisites:")
    print("   ✓ OpenRouter API key configured in .env")
    print("   ✓ OPENAI_CHAT_MODEL_ID set (e.g., openai/gpt-4o-mini)")
    print("   ✓ Virtual environment activated")

    try:
        # Run examples
        await example_blog_post_creation()
        await example_product_description()
        await example_with_thread_persistence()

        print("\n✅ All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Verify OPENAI_API_KEY in .env file")
        print("   - Check OpenRouter account has sufficient credits")
        print("   - Ensure model ID is valid (see https://openrouter.ai/models)")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
