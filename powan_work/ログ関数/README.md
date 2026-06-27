# Python共通ログ関数

複数のPythonアプリケーションで共通して使えるログ入口ポワンです。
標準 `logging` を扱いやすく包み、コンソール表示、ファイル保存、ログレベル、例外記録、アプリ別設定を同じ感覚で使えるようにします。

## できること

- `get_logger(app_name)` でアプリ用ロガーを取得
- `TRACE / DEBUG / INFO / WARNING / ERROR / CRITICAL` の6段階ログ
- コンソール出力とファイル出力の切り替え
- JSON/TOML/環境変数によるアプリ別設定
- 例外と安全化したコンテキストの記録
- ログローテーション対応

## 基本イメージ

```python
from common_logging import get_logger, log_exception

logger = get_logger("my_app", level="INFO", file=True)

logger.info("アプリを開始しました")
logger.debug("細かい調査用ログ")

try:
    raise RuntimeError("sample")
except RuntimeError as exc:
    log_exception(logger, "処理に失敗しました", exc, context={"job_id": 123})
```

## ポワン本体

- `project.powan`: ABC Canvas用のポワン定義
- `README.html`: 詳細な使い方案内

このリポジトリは、ログ関数ポワンをGitHubで保管・共有するための置き場です。
