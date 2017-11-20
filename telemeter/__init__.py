import os

__all__ = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith(".py")]
