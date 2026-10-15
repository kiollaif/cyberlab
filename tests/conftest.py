import os

# Позволяет запускать настоящий Qt без дисплея на Linux и в Windows CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
