# 一键启动脚本

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\n  世界杯竞彩数据面板")
    print(f"  http://127.0.0.1:{port}\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
