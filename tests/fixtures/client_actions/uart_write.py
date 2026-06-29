"""Write text to UART through the gated Branch B server API."""


async def run(inputs, server):
    text = str(inputs["text"])
    append_newline = bool(inputs.get("append_newline", True))
    result = await server.call_tool(
        "write_serial",
        {"text": text, "append_newline": append_newline},
    )
    return result.text
