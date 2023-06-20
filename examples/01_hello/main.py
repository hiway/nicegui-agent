from nicegui import Client, ui
from nicegui.globals import sio
from nicegui_agent import Agent

GREETING = ""
agent = Agent("01_hello_app", sio=sio)


@ui.refreshable
def greeting():
    ui.markdown(f"## {GREETING}")


@agent.on("notify")
async def notify(message: str):
    global GREETING
    GREETING = message
    greeting.refresh()


@ui.page("/")
async def main(client: Client):
    async def on_click():
        await agent.emit("hello", txt_name.value)

    with ui.column().classes("absolute-center items-center"):
        greeting()        
        txt_name = ui.input("Name")
        ui.button("Say hello", on_click=on_click)



ui.run(title="01 Hello")
