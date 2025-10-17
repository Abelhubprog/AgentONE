"""Prowzi Quick Start Example

Demonstrates Intent Agent and Planning Agent working together.
This is a working example of the first two stages of the Prowzi pipeline.
"""

import asyncio

from prowzi.agents import IntentAgent, PlanningAgent
from prowzi.config import ProwziConfig


async def main():
    """Run a basic Prowzi workflow demonstration"""
    print("=" * 70)
    print("🚀 Prowzi Demo - Intent Analysis + Research Planning")
    print("=" * 70)
    print()

    # Initialize configuration
    print("📦 Loading configuration...")
    config = ProwziConfig()
    print(f"   OpenRouter URL: {config.openrouter_base_url}")
    print(f"   Models loaded: {len(config.models)}")
    print(f"   Agents configured: {len(config.agents)}")
    print(f"   Search APIs available: {len(config.get_enabled_search_apis())}")
    print()

    # Step 1: Analyze intent
    print("-" * 70)
    print("STAGE 1: Intent & Context Analysis")
    print("-" * 70)
    print()

    intent_agent = IntentAgent(config=config)

    # Example prompt
    prompt = """
    Write a 10,000-word PhD-level literature review on:
    "The Application of Artificial Intelligence in Clinical Decision Support Systems"
    
    Requirements:
    - Focus on recent developments (2020-2024)
    - Include discussion of machine learning models used
    - Address ethical considerations and limitations
    - Use APA citation style
    - Target audience: healthcare professionals and AI researchers
    """

    print("📝 User Prompt:")
    print(f"   {prompt.strip()[:100]}...")
    print()

    # Optional: Parse documents
    # document_paths = ["research_paper.pdf", "guidelines.docx"]
    document_paths = None

    print("🔍 Analyzing intent...")
    analysis = await intent_agent.analyze(
        prompt=prompt,
        document_paths=document_paths
    )

    print()
    print("✅ Intent Analysis Complete!")
    print()
    print(f"   📄 Document Type: {analysis.document_type}")
    print(f"   🎓 Academic Level: {analysis.academic_level}")
    print(f"   📚 Field: {analysis.field}")
    print(f"   📝 Target Word Count: {analysis.word_count:,}")
    print(f"   🎯 Confidence Score: {analysis.confidence_score:.2%}")
    print()

    if analysis.explicit_requirements:
        print(f"   ✓ Explicit Requirements ({len(analysis.explicit_requirements)}):")
        for req in analysis.explicit_requirements[:3]:
            print(f"      • {req}")
        if len(analysis.explicit_requirements) > 3:
            print(f"      ... and {len(analysis.explicit_requirements) - 3} more")
        print()

    if analysis.implicit_requirements:
        print(f"   ✓ Implicit Requirements ({len(analysis.implicit_requirements)}):")
        for req in analysis.implicit_requirements[:3]:
            print(f"      • {req}")
        if len(analysis.implicit_requirements) > 3:
            print(f"      ... and {len(analysis.implicit_requirements) - 3} more")
        print()

    if analysis.missing_info:
        print("   ⚠️  Missing Information:")
        for info in analysis.missing_info:
            print(f"      • {info}")
        print()

    # Step 2: Create research plan
    print("-" * 70)
    print("STAGE 2: Research Planning")
    print("-" * 70)
    print()

    planning_agent = PlanningAgent(config=config)

    print("📋 Creating comprehensive research plan...")
    plan = await planning_agent.create_plan(analysis)

    print()
    print("✅ Research Plan Complete!")
    print()
    print(f"   📊 Total Tasks: {len(plan.execution_order)}")
    print(f"   🔍 Search Queries: {len(plan.search_queries)}")
    print(f"   🎯 Quality Checkpoints: {len(plan.quality_checkpoints)}")
    print(f"   🔄 Parallel Groups: {len(plan.parallel_groups)}")
    print()

    # Resource estimates
    estimates = plan.resource_estimates
    print(f"   ⏱️  Estimated Duration: {estimates['total_duration_minutes']} minutes")
    print(f"   🪙 Estimated Tokens: {estimates['total_tokens_estimated']:,}")
    print(f"   💰 Estimated Cost: ${estimates['total_cost_usd']:.2f}")
    print(f"   📚 Target Sources: {estimates['target_sources']}")
    print()

    # Show task hierarchy
    print("   📝 Task Breakdown:")
    for task in plan.task_hierarchy.subtasks:
        print(f"      • {task.name} ({task.duration_minutes}min) - {task.assigned_agent}")
    print()

    # Show sample queries
    print("   🔎 Sample Search Queries:")
    query_types = {}
    for query in plan.search_queries:
        query_type = query.query_type.value
        if query_type not in query_types:
            query_types[query_type] = []
        query_types[query_type].append(query)

    for query_type, queries in sorted(query_types.items())[:3]:
        sample_query = queries[0]
        print(f"      [{query_type.upper()}] {sample_query.query}")
        print(f"         Priority: {sample_query.priority.value} | Category: {sample_query.category}")
    print()

    # Show checkpoints
    print("   ✓ Quality Checkpoints:")
    for checkpoint in plan.quality_checkpoints:
        print(f"      • {checkpoint.name} (threshold: {checkpoint.minimum_threshold:.0%})")
        print(f"         After: {checkpoint.after_task}")
        print(f"         Criteria: {len(checkpoint.criteria)} checks")
    print()

    # Cost breakdown by agent
    print("   💵 Cost Breakdown:")
    agent_costs = {}
    for task in plan.task_hierarchy.subtasks:
        agent = task.assigned_agent or "orchestrator"
        if agent not in agent_costs:
            agent_costs[agent] = 0
        # Rough estimate based on duration
        agent_costs[agent] += (task.duration_minutes / 60) * 0.10

    for agent, cost in sorted(agent_costs.items(), key=lambda x: x[1], reverse=True):
        print(f"      {agent:20s}: ${cost:.2f}")
    print()

    print("-" * 70)
    print("📊 Summary")
    print("-" * 70)
    print()
    print("✅ Successfully analyzed intent and created research plan!")
    print("✅ Ready to proceed to Stage 3: Evidence Search")
    print()
    print("📈 Prowzi is 60% complete. Remaining stages:")
    print("   🚧 Stage 3: Evidence Search (TODO)")
    print("   🚧 Stage 4: Source Verification (TODO)")
    print("   🚧 Stage 5: Academic Writing (TODO)")
    print("   🚧 Stage 6: Quality Evaluation (TODO)")
    print("   🚧 Stage 7: Turnitin Check (TODO - Optional)")
    print()
    print("=" * 70)

    return analysis, plan


if __name__ == "__main__":
    try:
        analysis, plan = asyncio.run(main())

        print("\n💾 You can now access the results:")
        print("   analysis.to_dict()  # Full intent analysis")
        print("   plan.to_dict()      # Complete research plan")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
