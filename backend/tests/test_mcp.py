import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def run():
    url = 'https://github.run.tools/sse'
    headers = {'Authorization': 'Bearer d8045bc9-91e8-43fa-868c-e49647eca1cf'}
    try:
        print("Connecting to", url)
        async with sse_client(url, headers=headers) as streams:
            print("Streams established")
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print('Initialized')
                tools = await session.list_tools()
                print("Tools:", len(tools.tools))
                for t in tools.tools[:3]:
                    print(f" - {t.name}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
