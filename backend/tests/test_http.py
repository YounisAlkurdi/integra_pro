import urllib.request
import urllib.error

url = 'https://github.run.tools/sse'

try:
    req = urllib.request.Request(url, headers={})
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Headers:", response.headers)
        print("Content:", response.read().decode('utf-8')[:500])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Headers:", e.headers)
    print("Content:", e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
