"""CLI runner for agent-wrapper agents.

Run an agent from the command line:
    agent-wrapper --config agent.yaml --prompt "Fix the bug"
    agent-wrapper --config agent.yaml --interactive
    agent-wrapper --prompt "Hello" --model claude-sonnet-4-6

Or use programmatically:
    from agent_wrapper.runner import Runner

    runner = Runner(config="agent.yaml")
    runner.run("Fix the bug")
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional, Union

from agent_wrapper.agent import Agent
from agent_wrapper.config.schema import AgentConfig


class Runner:
    """Local runner for agent-wrapper agents.

    Usage:
        # From config file
        runner = Runner(config="agent.yaml")
        runner.run("Fix the auth bug")

        # From kwargs
        runner = Runner(model="claude-sonnet-4-6", system_prompt="Be concise.")
        runner.run("Explain closures")

        # Interactive mode
        runner = Runner(config="agent.yaml")
        runner.interactive()
    """

    def __init__(self, config: Optional[Union[str, AgentConfig]] = None, **kwargs):
        self._config = config
        self._kwargs = kwargs

    def _create_agent(self) -> Agent:
        if self._config:
            return Agent(config=self._config)
        return Agent(**self._kwargs)

    def run(self, prompt: str) -> str:
        """Run agent with a single prompt. Returns the final text response."""
        return asyncio.run(self._run_async(prompt))

    async def _run_async(self, prompt: str) -> str:
        async with self._create_agent() as agent:
            result = await agent.run(prompt)
            return result.text

    def interactive(self) -> None:
        """Run agent in interactive loop."""
        asyncio.run(self._interactive_async())

    async def _interactive_async(self) -> None:
        agent = self._create_agent()
        await agent.connect()

        print("agent-wrapper interactive mode (type 'exit' or 'quit' to stop)")
        print("-" * 50)

        try:
            while True:
                try:
                    prompt = input("\n> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!")
                    break

                if not prompt:
                    continue
                if prompt.lower() in ("exit", "quit"):
                    print("Bye!")
                    break

                result = await agent.run(prompt)
                print(f"\n{result.text}")

                if result.total_cost_usd:
                    print(f"\n[cost: ${result.total_cost_usd:.4f}]")
        finally:
            await agent.disconnect()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="agent-wrapper: lightweight Claude agent runner")
    parser.add_argument("--config", "-c", help="Path to YAML config file")
    parser.add_argument("--prompt", "-p", help="Prompt to run (omit for interactive mode)")
    parser.add_argument("--model", "-m", help="Model name (e.g., claude-sonnet-4-6)")
    parser.add_argument("--system-prompt", "-s", help="System prompt")
    parser.add_argument("--cwd", help="Working directory for the agent")
    parser.add_argument(
        "--permission-mode",
        default="bypassPermissions",
        help="Permission mode (default: bypassPermissions)",
    )

    args = parser.parse_args()

    # Build runner
    if args.config:
        runner = Runner(config=args.config)
    else:
        kwargs = {}
        if args.model:
            kwargs["model"] = args.model
        if args.system_prompt:
            kwargs["system_prompt"] = args.system_prompt
        if args.cwd:
            kwargs["cwd"] = args.cwd
        kwargs["permission_mode"] = args.permission_mode
        runner = Runner(**kwargs)

    # Run
    if args.prompt:
        result = runner.run(args.prompt)
        print(result)
    else:
        runner.interactive()


if __name__ == "__main__":
    main()
