import asyncio
from nicegui_agent import Agent


agent = Agent("01_hello_agent")


@agent.on("hello")
async def hello(name: str) -> str:
    print("Hello", name)
    await agent.emit("notify", f'Hello {name}!')


async def main():
    # await asyncio.sleep(10)
    await agent.run("ws://localhost:8080")


asyncio.run(main())