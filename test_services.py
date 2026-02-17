from services.youtube import get_transcript
import sys

# Video from user screenshot/context
VIDEO_ID = "eVFzbxmKNUw"

print(f"Testing get_transcript for {VIDEO_ID}...")
transcript = get_transcript(VIDEO_ID)

if transcript:
    print(f"SUCCESS! Transcript length: {len(transcript)}")
    print(f"Preview: {transcript[:200]}...")
else:
    print("FAILURE: Transcript returned None")
