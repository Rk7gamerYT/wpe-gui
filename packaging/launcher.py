import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wpe_gui.__main__ import main
raise SystemExit(main())
