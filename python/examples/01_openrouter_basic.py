# Copyright (c) Microsoft. All rights reserved.

"""
OpenRouter Chat Client Example - AgentONE Custom Configuration

This example demonstrates how to use the Microsoft Agent Framework with OpenRouter,
a unified gateway to 100+ LLM providers (OpenAI, Anthropic, Google, Meta, etc.).

Key features:
- Custom base_url configuration for OpenRouter
- Required HTTP headers (HTTP-Referer, X-Title)
- Tool/function calling support
- Streaming and non-streaming responses
- Multiple model providers through a single API

OpenRouter benefits:
- Access to 100+ models through one API key
- Automatic fallbacks and load balancing
- Pay-per-use with no subscriptions
- Models from OpenAI, Anthropic, Google, Meta, and more
"""

import asyncio
from random import randint
from typing import Annotated

from agent_framework.openai import OpenAIChatClient


def get_weather(
    location: Annotated[str, "The location to get the weather for."],
) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    temp = randint(10, 30)
    condition = conditions[randint(0, 3)]
    return f"The weather in {location} is {condition} with a high of {temp}°C."


def get_time() -> str:
    """Get the current time."""
    from datetime import datetime

    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


async def example_with_env_config() -> None:
    """Example using environment variables from .env file."""
    print("=" * 80)
    print("Example 1: Using .env configuration (recommended for production)")
    print("=" * 80)

    # When using .env file, the client automatically picks up:
    # - OPENAI_API_KEY (your OpenRouter key)
    # - OPENAI_BASE_URL (https://openrouter.ai/api/v1)
    # - OPENAI_CHAT_MODEL_ID (e.g., openai/gpt-4o-mini)

    agent = OpenAIChatClient().create_agent(
        name="WeatherAssistant",
        instructions="You are a helpful weather assistant. Provide weather information when asked.",
        tools=[get_weather, get_time],
    )

    query = "What's the weather like in Seattle and what time is it?"
    print(f"\n🤔 User: {query}\n")
    result = await agent.run(query)
    print(f"🤖 Agent: {result}\n")


async def example_with_explicit_config() -> None:
    """Example with explicit configuration (useful for development/testing)."""
    print("=" * 80)
    print("Example 2: Explicit configuration with custom headers")
    print("=" * 80)

    # Explicit configuration - useful when:
    # - Testing different models dynamically
    # - Running in environments without .env files
    # - Switching between multiple API keys

    client = OpenAIChatClient(
        api_key="sk-or-v1-your-api-key-here",  # Replace with your OpenRouter key
        base_url="https://openrouter.ai/api/v1",
        model_id="openai/gpt-4o-mini",  # or any OpenRouter model
        default_headers={
            "HTTP-Referer": "https://github.com/Abelhubprog/AgentONE",
            "X-Title": "AgentONE - Advanced Multi-Agent Framework",
        },
    )

    agent = client.create_agent(
        name="ResearchAgent",
        instructions="""You are a helpful research assistant specialized in technology topics.
        Provide concise, accurate information.""",
    )

    query = "What are the key benefits of autonomous multi-agent systems?"
    print(f"\n🤔 User: {query}\n")
    result = await agent.run(query)
    print(f"🤖 Agent: {result}\n")


async def example_streaming_with_tools() -> None:
    """Example demonstrating streaming responses with tool calls."""
    print("=" * 80)
    print("Example 3: Streaming responses with function tools")
    print("=" * 80)

    agent = OpenAIChatClient().create_agent(
        name="StreamingWeatherAgent",
        instructions="Provide weather updates and use the time function when appropriate.",
        tools=[get_weather, get_time],
    )

    query = "Compare the weather in New York, London, and Tokyo, and tell me the current time."
    print(f"\n🤔 User: {query}\n")
    print("🤖 Agent: ", end="", flush=True)

    async for chunk in agent.run_stream(query):
        if chunk.text:
            print(chunk.text, end="", flush=True)

    print("\n")


async def example_multiple_models() -> None:
    """Example showing how to use different models from different providers."""
    print("=" * 80)
    print("Example 4: Comparing responses from different model providers")
    print("=" * 80)

    models = [
        ("openai/gpt-4o-mini", "OpenAI"),
        ("anthropic/claude-3.5-sonnet", "Anthropic"),
        ("google/gemini-2.0-flash", "Google"),
        ("meta-llama/llama-3.1-70b-instruct", "Meta"),
    ]

    query = "In one sentence, what makes autonomous agents powerful?"

    print(f"\n🤔 User: {query}\n")

    for model_id, provider in models:
        try:
            client = OpenAIChatClient(model_id=model_id)
            agent = client.create_agent(
                name=f"{provider}Agent",
                instructions="Provide a concise, single-sentence answer.",
            )

            result = await agent.run(query)
            print(f"🤖 {provider} ({model_id}):")
            print(f"   {result}\n")
        except Exception as e:
            print(f"❌ {provider} ({model_id}): Error - {e}\n")


async def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  OpenRouter + Microsoft Agent Framework Examples".center(78) + "║")
    print("║" + "  Building Advanced Autonomous Multi-Agent Systems".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    print("📋 Before running these examples:")
    print("   1. Get your OpenRouter API key from: https://openrouter.ai/keys")
    print("   2. Update the .env file with: OPENAI_API_KEY=sk-or-v1-...")
    print("   3. Choose your model in: OPENAI_CHAT_MODEL_ID=openai/gpt-4o-mini")
    print("\n")

    try:
        # Run examples
        await example_with_env_config()
        await example_streaming_with_tools()

        # Uncomment to test explicit configuration:
        # await example_with_explicit_config()

        # Uncomment to compare multiple models (may incur API costs):
        # await example_multiple_models()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Common issues:")
        print("   - Missing or invalid OPENAI_API_KEY in .env file")
        print("   - Invalid OPENAI_BASE_URL (should be: https://openrouter.ai/api/v1)")
        print("   - Invalid model ID (check available models at https://openrouter.ai/models)")
        print("   - Insufficient API credits on OpenRouter")


if __name__ == "__main__":
    asyncio.run(main())
