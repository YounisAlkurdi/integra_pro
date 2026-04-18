import httpx
import asyncio

async def test():
    url = "https://github.run.tools/sse"
    key = "bf120be6-bcca-48f5-a5be-9fb61b8f5fdd"
    headers = {
        "Authorization": f"Bearer {key}",
        "X-Api-Key": key
    }
    
    print(f"Testing URL: {url}")
    try:
        async with httpx.AsyncClient() as client:
            # First try a GET request as SSE usually starts with GET
            response = await client.get(url, headers=headers)
            print(f"GET Status: {response.status_code}")
            print(f"GET Headers: {dict(response.headers)}")
            print(f"GET Body: {response.text[:500]}")
            
            # Also try without /sse just in case
            base_url = "https://github.run.tools"
            response_base = await client.get(base_url, headers=headers)
            print(f"\nBase URL Status: {response_base.status_code}")
            print(f"Base URL Body: {response_base.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
