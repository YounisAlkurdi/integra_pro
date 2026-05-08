import sys
import inspect
from livekit.api import LiveKitAPI

async def main():
    with open('c:/tist_integra/scratch/livekit_help.txt', 'w') as f:
        f.write(inspect.getsource(LiveKitAPI.room.get_participant) + '\n\n')
        f.write(inspect.getsource(LiveKitAPI.room.update_participant) + '\n\n')

import asyncio
asyncio.run(main())
