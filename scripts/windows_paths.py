"""Build-time extended paths; never changes Windows global long-path settings."""
from pathlib import Path
import os

def extended(path):
 value=str(Path(path).resolve())
 if os.name=='nt' and not value.startswith('\\\\?\\'):
  value='\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value
 return Path(value)
