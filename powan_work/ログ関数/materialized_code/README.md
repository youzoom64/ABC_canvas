# Python共通ログ関数 materialized_code

`materialized_code` は、ABC Canvas / powan の `ログ関数` プロジェクトからコード部分を取り出して、実際のファイルとディレクトリにしたものです。

このREADMEは、抽出の記録だけではなく、取り出された `common_logging.py` が何をするアプリケーション部品なのか、どう使うのか、どこまで動作確認済みか、どこが未完成かを説明します。

## これは何か

Pythonアプリケーションで共通して使うためのログ入口モジュールです。

標準ライブラリの `logging` を直接あちこちで設定する代わりに、`common_logging.py` を1つ置いておくことで、アプリ名、ログレベル、コンソール出力、ファイル出力、ローテーション、例外記録、環境変数上書きを同じ形で扱えるようにします。

主な利用イメージは、複数の小さなPythonツールやGUI、バッチ、監視処理で「毎回ログ設定を書くのが面倒」「TRACEレベルも欲しい」「ファイル出力も必要な時だけONにしたい」という場面です。

## ディレクトリ構造

```text
materialized_code/
  app/
    common_logging.py
    common_logging.observed.py
  powans/
    01_Python共通ログ関数/
      Python共通ログ関数.py
      02_6段階ログレベル/
      02_ロガー取得入口/
      02_ログ出力フォーマット/
      02_コンソール出力/
      02_ファイル出力/
      02_例外記録/
      02_ログ設定/
  manifest.json
  README.md
```

`app/common_logging.py` が実用候補の本体です。

`app/common_logging.observed.py` は、powanプロジェクト側に既に存在していた `common_logging.py` を比較用にコピーしたものです。

`powans/` は、powanの意味階層をそのままディレクトリにした構造確認用の出力です。各powanに入っていたコードを、親子関係に沿って書き出しています。これは設計レビューには便利ですが、そのままPythonパッケージとしてimportするものではありません。

`manifest.json` は、powan node id、親子関係、タイトル、`powanKind`、言語、出力パスを記録した対応表です。

## 本体ファイル

実際に使う場合の入口は次です。

```text
app/common_logging.py
```

このファイルは単体のPythonモジュールとして使えます。追加ライブラリは不要で、標準ライブラリだけで動きます。

## できること

`common_logging.py` が提供する主な機能は次の通りです。

ログレベルを扱えます。

- `TRACE`
- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

Python標準の `logging` には `TRACE` がないため、このモジュールは `TRACE = 5` を登録し、必要なら `logger.trace(...)` を追加します。

ロガーを簡単に作れます。

```python
from common_logging import get_logger

logger = get_logger("my_app")
logger.info("起動しました")
```

詳細な設定つきでロガーを作れます。

```python
from common_logging import configure_logging

result = configure_logging(
    "my_app",
    app={
        "level": "debug",
        "console": True,
        "file": True,
        "log_dir": "logs",
        "filename": "my_app.log",
    },
)

logger = result.logger
logger.debug("デバッグログ")
```

コンソール出力をON/OFFできます。

```python
logger = get_logger("console_only", console=True, file=False)
```

ファイル出力をON/OFFできます。

```python
logger = get_logger(
    "file_app",
    console=False,
    file=True,
    log_dir="logs",
    filename="file_app.log",
)
```

サイズローテーションを使えます。

```python
logger = get_logger(
    "rotate_size_app",
    file=True,
    rotation="size",
    max_bytes=1024 * 1024,
    backup_count=5,
)
```

日次ローテーションを使えます。

```python
logger = get_logger(
    "rotate_time_app",
    file=True,
    rotation="time",
    backup_count=7,
)
```

JSONまたはTOMLの設定ファイルを読めます。

```python
from common_logging import configure_logging

result = configure_logging("my_app", app="logging.json")
logger = result.logger
```

設定dict、設定ファイル、環境変数をマージできます。

```python
from common_logging import load_logging_config

config = load_logging_config(
    default={"level": "info", "console": True},
    app={"file": True, "log_dir": "logs"},
)
```

例外を読みやすく記録できます。

```python
from common_logging import get_logger, log_exception

logger = get_logger("worker")

try:
    1 / 0
except ZeroDivisionError as exc:
    log_exception(
        logger,
        "処理に失敗しました",
        exc,
        context={"job_id": 123, "token": "secret-value"},
    )
```

`log_exception()` は例外型、例外メッセージ、追加コンテキスト、tracebackをまとめたdictも返します。`token` や `password` などのキーは `***` にマスクされます。

## 公開API

`__all__` で公開されているAPIは次です。

```python
TRACE_LEVEL
TRACE_NAME
LoggingProfile
LoggingSettingsError
LoggingSetupResult
build_logging_profile
configure_logging
create_console_handler
create_file_handler
get_logger
load_logging_config
log_exception
register_trace_level
resolve_level
```

通常利用では `get_logger()`、細かく制御したい場合は `configure_logging()`、例外記録には `log_exception()` を使います。

## 設定モデル

`LoggingProfile` は解決済みのログ設定です。

主な項目は次です。

```text
app_name
level_name
level_value
console_enabled
file_enabled
log_dir
filename
format_text
date_format
propagate
rotation
max_bytes
backup_count
encoding
extra
```

`LoggingSetupResult` は `configure_logging()` の戻り値です。

```text
logger
profile
handlers
```

`result.logger` で実際の `logging.Logger` を取り出せます。`result.profile.as_dict()` で解決済み設定を確認できます。

## 対応するログレベル指定

`resolve_level()` は文字列や数値を標準化します。

対応している別名は次です。

```text
TRACE, TRC, VERBOSE
DEBUG, DBG
INFO, INFORMATION, NOTICE
WARNING, WARN
ERROR, ERR, EXCEPTION
CRITICAL, FATAL
```

例:

```python
from common_logging import resolve_level

resolve_level("warn")
# ("WARNING", 30)
```

## 環境変数

デフォルトでは `LOG_` で始まる環境変数を読みます。

対応している主な環境変数は次です。

```text
LOG_LEVEL
LOG_CONSOLE
LOG_FILE
LOG_DIR
LOG_PATH
LOG_FILENAME
LOG_FORMAT
LOG_ROTATION
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

例:

```powershell
$env:LOG_LEVEL = "debug"
$env:LOG_FILE = "true"
$env:LOG_DIR = "logs"
$env:LOG_FILENAME = "app.log"
```

環境変数を使いたくない場合は、`configure_logging(..., environ={})` のように空dictを渡します。

## 設定例

最小構成:

```python
from common_logging import get_logger

logger = get_logger("mini")
logger.info("hello")
```

コンソールだけ:

```python
logger = get_logger("cli", console=True, file=False, level="info")
```

ファイルだけ:

```python
logger = get_logger(
    "batch",
    console=False,
    file=True,
    log_dir="logs",
    filename="batch.log",
)
```

TRACEを使う:

```python
from common_logging import configure_logging

result = configure_logging(
    "trace_demo",
    app={"level": "trace", "console": True},
)

result.logger.trace("細かい追跡ログ")
```

例外を記録する:

```python
from common_logging import get_logger, log_exception

logger = get_logger("job")

try:
    raise RuntimeError("sample")
except RuntimeError as exc:
    payload = log_exception(
        logger,
        "ジョブで例外が発生しました",
        exc,
        context={"job_id": 42, "api_key": "hidden"},
    )
```

## 動作確認結果

このexport後に確認した内容です。

`app/common_logging.py` の構文チェック:

```text
python -m py_compile app/common_logging.py
```

結果: 成功。

通常import相当の読み込み:

```text
import ok
```

API確認:

```text
register_trace_level() -> 5
resolve_level("warn") -> ("WARNING", 30)
```

ファイルログ出力:

```text
2026-06-25 14:56:46 | TRACE    | powan_demo:14 | trace message
2026-06-25 14:56:46 | DEBUG    | powan_demo:15 | debug message
2026-06-25 14:56:46 | INFO     | powan_demo:16 | info message
```

例外記録:

- `type`
- `qualified_type`
- `message`
- `context`
- `traceback`

を含むpayloadが返ることを確認しました。`token` は `***` にマスクされました。

## 既知の問題

`LOG_FORMAT=json` のような値を環境変数から受けると、現在の実装ではそのまま `logging.Formatter` に渡します。

`logging.Formatter` は `%` 形式のフォーマット文字列を期待するため、`json` という単語だけではエラーになります。

これは実装上の未完成点です。JSONログを正式対応するなら、`format=json` を検出してJSON formatterへ分岐する必要があります。JSONログを対応しないなら、設定検証で早く明確に弾くべきです。

現在はテストスイートがありません。

`common_logging.py` は基本動作していますが、共通ライブラリとして複数プロジェクトへ配るには、少なくともログレベル、環境変数、ファイル出力、ローテーション、例外記録、異常設定のテストが必要です。

## powan階層としての状態

元のpowan構造は、コード抽出可能な形としては成立しています。

確認値:

```text
nodes: 177
code nodes: 169
root: Python共通ログ関数
max depth: 4
```

深さ分布:

```text
depth 0: 1
depth 1: 7
depth 2: 48
depth 3: 114
depth 4: 7
```

`parent` と `children` の不整合は見つかりませんでした。

ただし、構造には整理すべき点があります。

`ログ設定` 配下と、`ファイル出力` / `コンソール出力` / `6段階ログレベル` 配下で責務が重複しています。

重複している代表例:

```text
TRACEレベル登録
コンソール有効判定
ファイルハンドラ生成
ファイル出力有効判定
ファイル名生成
ログ保存先解決
ローテーション設定
保持日数クリーンアップ
```

`organ` なのに子を持つノードもあります。

```text
ログレベル切替
コンソール出力設定
```

今後のpowanルールとしては、子を持つものは `nerve`、最終コード単位は `organ` に寄せる方が安定します。

## 実用品としての評価

現時点の評価は次です。

```text
構造からのコード抽出: 成立
単体モジュールとしての基本動作: 成立
自分用ツールでの利用: 可能
共通ライブラリとしての配布: まだ早い
```

`common_logging.py` は、小さい自分用ツールや実験用アプリのログ入口としては使えます。

一方で、複数プロジェクトに配る共通ライブラリにするには、設定検証、JSONログ方針、テスト、README例の実行確認、API安定化が必要です。

## 次にやるべきこと

実用品へ近づけるなら、次の順で進めるのがよいです。

1. `LOG_FORMAT=json` の扱いを決める。
2. `format` が不正な場合のエラーを明確にする。
3. `tests/test_common_logging.py` を作る。
4. `get_logger()`、`configure_logging()`、`log_exception()` の基本テストを書く。
5. ファイル出力とローテーションのテストを書く。
6. powan側の重複責務を整理する。
7. `organ` / `nerve` の分類を修正する。
8. 再materializeしてREADMEとmanifestを更新する。

## powan生成ルールの提案

次回以降のpowan生成では、次のルールを入れると構造が崩れにくくなります。

```text
depth0 は目的。
depth1 は主要責務。
depth2 は原則として実装単位へ収束。
1つのpowanの直接子は最大8個。
子を持つpowanは nerve。
最終コード単位は organ。
同じ責務を別枝に重複作成しない。
organ は1つの意味をコード化する。
500行を超えそうなら、その意味をさらに分ける。
```

このルールなら、意味からコードへ落とす流れを保ちつつ、無限に細かく割れたり、同じ機能が別枝で増殖したりするのを抑えられます。
