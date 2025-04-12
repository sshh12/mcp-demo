# URL-Based MCP Server

> URL MCP is a proof of concept stateless MCP server builder that allows users to build MCP servers without writing or hosting code. It's intended for protocol and security experimentation rather than for building real world MCP integrations.

<img width="500" alt="Screenshot 2025-04-12 at 12 07 39 PM" src="https://github.com/user-attachments/assets/a9b25d5a-a950-4fdb-b789-90d637f6c142" />

## Usage

1. Go to https://url-mcp-demo.sshh.io/
2. Add custom tools to your MCP server

- If you want to hardcode tool responses, select "static text response"
- If you want dynamic HTTP-based responses, select "http post endpoint"
  - Typically I'll use a temp URL from https://webhook.site/ which logs all the requests and allows you to configure custom responses

3. Copy the `MCP Configuration` into your client of choice

## Local Hosting

There is not really a point to hosting this locally (the whole idea is that you can use this without hosting just with the URL) but in case you want to modify the app itself:

1. `cd backend && pip install requirements.txt && python main.py`

## Example: System Prompt Exfiltration

Create a custom MCP server for extracting the system prompt of an application.

1. Configure the tools to trick the client into trusting it. Use a https://webhook.site/ temp url for the tool response.
2. Copy the MCP config
3. In the client ask for an audit and the view the webhook logs.

| Step 1                                                                                                                                               | Step 2                                                                                                                                               | Step 3                                                                                                                                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| <img width="822" alt="Screenshot 2025-04-12 at 12 14 40 PM" src="https://github.com/user-attachments/assets/bee7fb56-c405-4260-82ef-e485555c19ae" /> | <img width="803" alt="Screenshot 2025-04-12 at 12 14 50 PM" src="https://github.com/user-attachments/assets/5a94ce4f-904d-4ee2-b117-e7147e877b56" /> | <img width="1222" alt="Screenshot 2025-04-12 at 12 15 00 PM" src="https://github.com/user-attachments/assets/d375f49e-6852-48d2-a502-dc6355530e22" /> |
