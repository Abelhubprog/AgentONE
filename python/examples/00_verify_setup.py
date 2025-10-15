# Copyright (c) Microsoft. All rights reserved.

"""
Quick Setup Verification Test

Run this script to verify your environment is properly configured for OpenRouter.
This will test:
1. Environment variables are loaded
2. OpenRouter API key is valid
3. Agent creation works
4. Basic inference works

Usage:
    uv run python examples/00_verify_setup.py
"""

import asyncio
import sys


async def verify_environment() -> bool:
    """Verify environment variables are configured."""
    print("🔍 Step 1: Checking environment configuration...")

    import os

    from dotenv import load_dotenv

    # Load .env file
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID")

    if not api_key:
        print("   ❌ OPENAI_API_KEY not found in environment")
        print("   💡 Add it to python/.env file")
        return False

    if not base_url:
        print("   ⚠️  OPENAI_BASE_URL not set, using default")
    elif "openrouter" in base_url.lower():
        print(f"   ✅ OpenRouter base URL configured: {base_url}")
    else:
        print(f"   ⚠️  Custom base URL: {base_url}")

    if not model_id:
        print("   ❌ OPENAI_CHAT_MODEL_ID not set")
        print("   💡 Add it to python/.env file (e.g., openai/gpt-4o-mini)")
        return False

    print(f"   ✅ Model ID configured: {model_id}")
    print(f"   ✅ API key found: {api_key[:15]}...")

    return True


async def verify_client_creation() -> bool:
    """Verify OpenAI client can be created."""
    print("\n🔍 Step 2: Testing client creation...")

    try:
        from agent_framework.openai import OpenAIChatClient

        client = OpenAIChatClient()
        print(f"   ✅ OpenAIChatClient created successfully")
        print(f"   ✅ Service URL: {client.service_url()}")
        return True

    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        return False


async def verify_agent_creation() -> bool:
    """Verify agent can be created."""
    print("\n🔍 Step 3: Testing agent creation...")

    try:
        from agent_framework.openai import OpenAIChatClient

        client = OpenAIChatClient()
        agent = client.create_agent(
            name="TestAgent", instructions="You are a helpful test assistant."
        )

        print(f"   ✅ Agent created successfully")
        print(f"   ✅ Agent name: {agent.name}")
        print(f"   ✅ Agent ID: {agent.id}")
        return True

    except Exception as e:
        print(f"   ❌ Failed to create agent: {e}")
        return False


async def verify_basic_inference() -> bool:
    """Verify basic inference works."""
    print("\n🔍 Step 4: Testing basic inference...")

    try:
        from agent_framework.openai import OpenAIChatClient

        client = OpenAIChatClient()
        agent = client.create_agent(
            name="TestAgent",
            instructions="You are a test assistant. Respond with exactly: 'Setup verified!'",
        )

        result = await agent.run("Please confirm setup is working.")
        response_text = str(result)

        print(f"   ✅ Inference successful")
        print(f"   ✅ Response: {response_text[:100]}...")

        return True

    except Exception as e:
        print(f"   ❌ Inference failed: {e}")
        if "401" in str(e) or "unauthorized" in str(e).lower():
            print("   💡 Check your OpenRouter API key")
        elif "404" in str(e) or "not found" in str(e).lower():
            print("   💡 Check your model ID is valid")
        elif "rate" in str(e).lower() or "quota" in str(e).lower():
            print("   💡 Check your OpenRouter account has credits")
        return False


async def verify_tool_calling() -> bool:
    """Verify function/tool calling works."""
    print("\n🔍 Step 5: Testing function/tool calling...")

    try:
        from typing import Annotated

        from agent_framework.openai import OpenAIChatClient

        def get_test_value(
            param: Annotated[str, "A test parameter"],
        ) -> str:
            """A test function that returns a value."""
            return f"Test function called with: {param}"

        client = OpenAIChatClient()
        agent = client.create_agent(
            name="TestAgent",
            instructions="Use the get_test_value function with parameter 'verification'",
            tools=[get_test_value],
        )

        result = await agent.run("Please call the test function.")
        response_text = str(result)

        print(f"   ✅ Tool calling successful")
        print(f"   ✅ Response: {response_text[:100]}...")

        return True

    except Exception as e:
        print(f"   ⚠️  Tool calling test failed: {e}")
        print(f"   💡 This may indicate the model doesn't support function calling")
        print(f"   💡 Try a different model (e.g., openai/gpt-4o-mini)")
        return False


async def main() -> None:
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("🚀 AgentONE Setup Verification")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Environment Config", await verify_environment()))

    if results[-1][1]:  # Only continue if env is configured
        results.append(("Client Creation", await verify_client_creation()))
        results.append(("Agent Creation", await verify_agent_creation()))
        results.append(("Basic Inference", await verify_basic_inference()))
        results.append(("Tool Calling", await verify_tool_calling()))

    # Summary
    print("\n" + "=" * 80)
    print("📊 Verification Summary")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print("\n" + "-" * 80)

    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})!")
        print("\n🎉 Your setup is ready! You can now run the examples:")
        print("   • uv run python examples/01_openrouter_basic.py")
        print("   • uv run python examples/02_sequential_workflow.py")
        print("   • uv run python examples/03_magentic_workflow.py")
        sys.exit(0)
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
        print("\n💡 Common issues:")
        print("   • Missing or invalid OPENAI_API_KEY in .env file")
        print("   • OpenRouter account has insufficient credits")
        print("   • Invalid model ID (check https://openrouter.ai/models)")
        print("   • Network connectivity issues")
        print("\n📚 See examples/README.md for detailed setup instructions")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
