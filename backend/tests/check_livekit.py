try:
    import livekit.api
    print("SUCCESS: livekit-api is installed")
except ImportError:
    print("FAILURE: livekit-api is NOT installed")
except Exception as e:
    print(f"ERROR: {e}")
