"""Compatibility entry point for pinned FFmpeg-only restoration."""
from dependencies import prepare
if __name__=='__main__':prepare(only={'ffmpeg'})
