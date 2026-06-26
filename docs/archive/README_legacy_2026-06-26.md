# ABC Canvas README

ABC Canvas は、頭に浮かんだ曖昧なイメージを「ポワン」として置き、意味を分解し、子構造を作り、会話し、コード化し、最後に実体のあるファイルやアプリへ近づけるためのローカルWebアプリです。

単なるマインドマップではありません。プロジェクト、`.powan` 文書、意味ノード、内側の世界、会話履歴、Codex連携、コード欄、添付、AI操作API、CLI補助ツールをまとめて持つ「意味から実装へ落とす作業場」です。

## いちばん短い説明

ABC Canvas では、ひとつの意味をひとつのポワンとして扱います。

ポワンには、名前、説明、種類、親子関係、見た目、位置、コード、会話履歴を持たせられます。

親ポワンは抽象的な目的や責務を表し、子ポワンはそれを構成する意味や部品を表します。階層を下るほど具体的になり、最終的にはコードやファイルに近づきます。

## 何ができるか

ABC Canvas でできることは大きく分けて次です。

- プロジェクトを作る。
- `.powan` 文書を作る。
- 意味ノードをキャンバスに置く。
- ノードを親子関係でつなぐ。
- 親ポワンの内側の世界へ入る。
- 左ツリーで全体構造を見る。
- 右パネルで選択中ポワンの意味を編集する。
- ポワンを `nerve` / `organ` に分類する。
- ポワンごとにコードを書く。
- ポワンごとにAI/Codexと会話する。
- 会話履歴をセッションとして残す。
- 会話を要約して新しいセッションへつなぐ。
- 子ポワンたちへまとめて指示を出す。
- `.powan` ファイルとして部分ツリーをエクスポート/インポートする。
- 添付ファイルを会話やポワン文脈に入れる。
- 音、会話パネル、整列、Codex権限などを設定する。
- API/CLIからポワンを作成、編集、分解、コード取得できる。

## 起動方法

作業ディレクトリ:

```powershell
cd C:\project_root\app_workspaces\API\ai_agent_team_runtime\tools\abc_canvas
```

依存関係:

```powershell
python -m pip install -r requirements.txt
```

起動:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8790 --no-access-log
```

Windowsでは次のバッチからも起動できます。

```powershell
.\start_abc_canvas.bat
```

ブラウザ:

```text
http://127.0.0.1:8790/
```

`/` はプロジェクト一覧画面です。キャンバス画面は `/canvas?project=プロジェクト名&file=project.powan` で開きます。

## 画面の構成

ABC Canvas には主に3つの画面があります。

```text
/          プロジェクト一覧
/canvas    ポワン編集キャンバス
/settings  設定画面
```

プロジェクト一覧では、プロジェクトを作成し、既存プロジェクトを開きます。

キャンバスでは、ポワンを置き、編集し、親子化し、会話し、コードを書きます。

設定画面では、音、Codexのsandbox権限、整列間隔、整列サイズなどを調整します。

## プロジェクト

プロジェクトは、ひとまとまりの目的や制作物を入れる箱です。

保存先は次です。

```text
powan_work/<project_name>/
```

プロジェクトの中には、通常 `project.powan` という文書が作られます。

例:

```text
powan_work/ログ関数/project.powan
powan_work/ログ関数/powan.db
powan_work/ログ関数/AGENTS.md
```

プロジェクトごとに `.powan` 文書、会話DB、添付、AGENTS.md、スキルコピーなどを持てます。

## `.powan` 文書

`.powan` はABC Canvasの中心データです。

中身はJSONで、主に次を持ちます。

```text
version
canvas
nodes
```

各nodeには次のような情報が入ります。

```text
id
title
body
parent
children
powanKind
code
codeLanguage
style
layout
nestedLayoutByParent
attachments
```

つまり `.powan` は、単なる図ではなく、意味、構造、コード、見た目、内側配置をまとめたファイルです。

## ポワンとは何か

ポワンとは、ユーザーが頭の中に持っている曖昧なイメージを、ひとつの意味として置いたものです。

最初のポワンはまだ名前が曖昧でも構いません。まず「何を作りたいか」「何を考えたいか」「どんな感じか」を置きます。

その後、その意味を構成する子ポワンを作ります。

例:

```text
Python共通ログ関数
  6段階ログレベル
  ロガー取得入口
  ログ出力フォーマット
  コンソール出力
  ファイル出力
  例外記録
  ログ設定
```

このように、上位は目的や責務、下位は構成要素、さらに下位は実装単位へ近づきます。

## nerve と organ

ポワンには大きく2種類あります。

`nerve` は神経ポワンです。複数の子ポワンを束ねる意味、方針、カテゴリ、facade、連携口に向いています。

`organ` は臓器ポワンです。実際の処理、関数、クラス、ファイル、実装単位に向いています。

基本ルール:

```text
子を持つなら nerve
最終コード単位なら organ
```

`organ` が子を持つと、意味としては「最終部品」のはずなのに、さらに内部構造を抱えることになり、抽出やレビューが曖昧になります。

## 階層設計の目安

おすすめの階層は次です。

```text
depth0: 目的
depth1: 主要責務
depth2: 実装候補または小さなサブ責務
depth3: depth2がまだ大きい場合だけ分解
```

直接の子ポワンは最大8個を目安にします。

8個を超える場合は、子を増やすより中間カテゴリを作ります。

例:

```text
悪い例:
  親
    子1
    子2
    子3
    ...
    子14

良い例:
  親
    入力系
      子1
      子2
    出力系
      子3
      子4
    設定系
      子5
      子6
```

500行ルールは補助的な警報として使います。

```text
organ は1つの意味をコード化する。
500行を超えそうなら、その意味をさらに分ける。
```

ただし、行数よりも意味の単一性を優先します。

## 基本操作

プロジェクト一覧でプロジェクトを作るには、Project欄へ名前を入れて `Create` を押します。

プロジェクトを開くとキャンバスに移動します。

キャンバス上では、ポワンを選択すると右パネルで編集できます。

右パネルで編集できる主な項目:

```text
Title
Body
Kind
Shape
Color
Accent
Glow
Soft edge
Tiny motion
```

`Title` はポワンの名前です。

`Body` は意味の説明です。

`Kind` は `nerve` / `organ` の分類です。

`Shape` は見た目です。`cloud`、`bubble`、`note`、`plain` があります。

## ポワンを作る

選択中ポワンの子を作るには `Add Child` を押します。

親を持たない自由ノードを作るには `Add Free Node` を押します。

子ポワンは親の意味を分解する部品として作ります。

自由ノードは、まだ親が決まっていないメモや、あとで別の親へ入れる候補に向いています。

## ポワンを親子化する

ポワンはドラッグで別のポワンへ入れられます。

親子化されると、子は親の `children` に入り、子の `parent` が親idになります。

この関係は左ツリーにも反映されます。

親子化の意味は「この子は親を構成する意味である」です。

単に近くに置くことと、親子にすることは違います。近くにあるだけなら視覚的な配置、親子なら意味上の所属です。

## 内側の世界

ポワンは外側のキャンバスに置くだけでなく、そのポワンの内側の世界を開けます。

内側の世界に入ると、親ポワンの子たちをその親の中の世界として編集できます。

右パネルの `worldName` と `worldPath` には、今どの世界にいるかが表示されます。

`上の階層へ` で1つ上へ戻ります。

`最上位の世界` で外側へ戻ります。

この仕組みにより、巨大な1枚キャンバスではなく、意味ごとに世界を分けて深く掘れます。

## 左ツリー

左ツリーは、現在の `.powan` の意味階層を一覧する場所です。

主な役割:

```text
全体構造を見る
現在の位置を把握する
ポワンを選択する
選択をコピーする
選択を削除する
ツリーへpowanファイルをドロップする
```

左ツリーは、キャンバス上で見えない深い子ポワンを探す時に重要です。

ポワン構造が大きくなるほど、左ツリーが地図になります。

## 右パネル

右パネルは、選択中ポワンの詳細編集場所です。

通常パネルでは、意味と見た目を編集します。

コードパネルでは、選択中ポワンのコードを編集します。

右パネルは折りたたみできます。幅もリサイズできます。

## コードを書く

ポワンにはコードを持たせられます。

ノードのメニューから `コードを開く` を押すとコードパネルが開きます。

対応言語選択:

```text
Plain
JavaScript
Python
HTML
CSS
JSON
Markdown
```

コードは `.powan` のnode内に `code` と `codeLanguage` として保存されます。

`organ` は実装コードを書く場所に向いています。

`nerve` にコードを書く場合は、子ポワンをまとめるfacade、統合関数、エントリーポイント、説明用コードに寄せると扱いやすくなります。

## 会話する

ポワンごとに会話できます。

ノードのメニューから `ポワンに話しかける` を選ぶと会話パネルが開きます。

会話パネルでは、選択したポワンを文脈にしてCodexへ話しかけます。

会話には次の文脈が渡されます。

```text
現在のポワン
親ポワン
子ポワン
ユーザー入力
必要に応じて意味ツリー
添付
コード情報
```

会話パネルの主な操作:

```text
Send
Cancel
新規
要約
Close
Auto summary
Tree ctx
会話履歴選択
文字サイズ変更
```

`Tree ctx` をONにすると、会話に意味ツリー文脈を含めます。

`Auto summary` をONにすると、一定ターン後に会話要約を作る運用ができます。

## 会話セッション

会話はセッションとして保存されます。

新しい話題に切り替える時は `新規` を押します。

過去の会話は会話履歴から選べます。

長くなった会話は `要約` でまとめ、要約から新しいセッションとして再開できます。

これは、ポワンごとの思考履歴を残しながら、コンテキスト肥大を抑えるための仕組みです。

## 添付

会話入力やキャンバスにはファイルをドロップできます。

添付は会話の文脈として扱われます。

画像などはプレビュー付きのチップとして表示されます。

添付ファイルはプロジェクト配下の `data/attachments` などに保存される場合があります。

## powanのエクスポートとインポート

ノードメニューから `powanをエクスポート` を選ぶと、そのポワンと配下を `.powan` ファイルとして出せます。

`powanファイルをこのポワンの下に呼ぶ` を使うと、外部の `.powan` 部分木を現在のポワン配下へ取り込めます。

キャンバスやツリーへ `.powan` ファイルをドロップして読み込む操作もあります。

この仕組みで、意味構造を別プロジェクトへ移植できます。

## 整列

ノードメニューの `整列` は、選択ポワンの子を見やすく配置します。

キャンバス背景の右クリックメニューには `この世界を整列` があります。

設定画面では、整列の間隔とサイズを調整できます。

整列は意味構造を変えず、見た目の配置を整理する操作です。

## 設定画面

`Settings` から設定画面を開けます。

設定できる主な項目:

```text
音声フォルダ
会話音
会話音量
入力中音
入力中音量
Codex sandbox access
整列間隔
整列サイズ
```

Codex sandbox access は、Codex連携時にどの程度のファイルアクセスを許すかに関わります。

この設定は強い操作に影響するため、用途に応じて慎重に選びます。

## 保存

上部の `Save` で現在の `.powan` を保存します。

`Save As` で別名保存できます。

`Reload` で現在のファイルを再読み込みします。

`New` で新しい `.powan` 文書を作ります。

ファイル一覧のselectから同じプロジェクト内の別 `.powan` を切り替えられます。

## Undo / Redo

`Undo` と `Redo` があります。

テキスト入力中の通常Undo/Redoと、キャンバス操作のUndo/Redoが衝突しないように処理されています。

意味や配置を大きく変える時は、保存前にUndoできるか確認しながら作業すると安全です。

## AI操作API

ABC Canvas は、人間がブラウザで操作するだけでなく、AIやCLIからポワンを操作するAPIを持っています。

代表的なAPI:

```text
GET  /api/ai/projects
GET  /api/ai/project?project=...
GET  /api/ai/powans?project=...&file=project.powan
GET  /api/ai/powans/{node_id}
GET  /api/ai/powans/{node_id}/context
POST /api/ai/powans
PATCH /api/ai/powans/{node_id}
POST /api/ai/powans/{node_id}/children
POST /api/ai/powans/{node_id}/actions/split
POST /api/ai/powans/{node_id}/actions/tree
POST /api/ai/powans/{node_id}/actions/delete-child
POST /api/ai/powans/{node_id}/actions/restore-child
POST /api/ai/powans/{node_id}/actions/read-powan-codes
POST /api/ai/powans/{node_id}/move
GET  /api/ai/action-logs
```

このAPIは、ポワン自身や外部エージェントが構造を作るための入口です。

## abc_powan_tool.py

`abc_powan_tool.py` は、AIやCLIからABC Canvas APIを呼ぶための補助ツールです。

基本環境変数:

```powershell
$env:ABC_CANVAS_API_BASE = "http://127.0.0.1:8790"
$env:ABC_POWAN_PROJECT = "プロジェクト名"
$env:ABC_POWAN_FILE = "project.powan"
$env:ABC_POWAN_NODE_ID = "node-..."
```

対応操作:

```text
set-my-meaning
create-child-powan
create-powan-tree
delete-child-powan
restore-child-powan
command-children
command-child-powan
read-powan-codes
write-my-code
```

## 自分の意味を保存する

`set-my-meaning` は、現在のポワンの名前、説明、種類を保存します。

```powershell
python abc_powan_tool.py set-my-meaning --stdin-json
```

入力例:

```json
{
  "title": "Python共通ログ関数",
  "body": "複数のPythonアプリで共通利用できるログ入口。",
  "powanKind": "nerve"
}
```

## 子ポワンを作る

`create-child-powan` は、現在のポワンの直下に子を作ります。

```powershell
python abc_powan_tool.py create-child-powan --stdin-json
```

入力例:

```json
{
  "title": "ファイル出力",
  "body": "ログをファイルへ保存する責務。",
  "powanKind": "nerve"
}
```

## 階層ごと作る

`create-powan-tree` は、子、孫、ひ孫をまとめて作ります。

```powershell
python abc_powan_tool.py create-powan-tree --stdin-json
```

入力例:

```json
{
  "children": [
    {
      "title": "入力",
      "body": "外部から受け取る情報。",
      "powanKind": "nerve",
      "children": [
        {
          "title": "設定ファイル",
          "body": "JSONやTOMLから設定を読む。",
          "powanKind": "organ"
        }
      ]
    }
  ]
}
```

## コードを書く

`write-my-code` は、現在のポワンにコードを保存します。

```powershell
python abc_powan_tool.py write-my-code --stdin-json
```

入力例:

```json
{
  "codeLanguage": "python",
  "code": "def hello():\n    return \"hello\""
}
```

コードが長い場合は `--code-file` を使います。

```powershell
python abc_powan_tool.py write-my-code --code-language python --code-file .\sample.py
```

## コードを読む

`read-powan-codes` は、プロジェクト内のポワンコードをまとめて読みます。

```powershell
python abc_powan_tool.py read-powan-codes --stdin-json
```

入力例:

```json
{
  "includeSelf": true,
  "targets": [
    {"title": "ファイル出力"},
    {"path": ["Python共通ログ関数", "ログ設定"]},
    {"targetId": "node-xxxxxxxxxx"}
  ]
}
```

これは、powanからコードを抽出して実ファイル化する時の基礎になります。

## 子ポワンへまとめて指示する

`command-children` は、直接の子ポワン全員へ同じ指示、または個別指示を送ります。

```powershell
python abc_powan_tool.py command-children --stdin-json
```

入力例:

```json
{
  "instruction": "自分の意味を1つの実装単位として見直し、必要ならcodeを書いてください。",
  "includeMeaningTree": true,
  "parallel": true,
  "maxParallel": 3,
  "staggerMs": 1000
}
```

子を一斉に動かす強力な操作なので、構造ルールが曖昧なまま使うと重複や分類ミスが増えます。

## 特定の子ポワンへ指示する

`command-child-powan` は、特定の子へ個別指示します。

```powershell
python abc_powan_tool.py command-child-powan --stdin-json
```

入力例:

```json
{
  "title": "ファイル出力",
  "instruction": "ファイル出力の責務だけに絞って、organ候補を3つ以内で提案してください。"
}
```

## アーカイブと復元

`delete-child-powan` は、直接の子ポワンをアーカイブします。

`restore-child-powan` は、アーカイブした子を戻します。

アーカイブは完全削除ではなく、今は使わない場所へしまう操作です。

構造整理で「この枝はまだ要らないが、後で戻したい」という時に使います。

## Codex連携

会話パネルや `command-children` は、Codex bridge を通じてCodexを呼びます。

Codexへ渡される基本文脈は次です。

```json
{
  "powan": {
    "meaning": "",
    "title": "",
    "body": "",
    "codeLanguage": "",
    "hasCode": false
  },
  "parent": {
    "meaning": "",
    "title": "",
    "body": "",
    "codeLanguage": "",
    "hasCode": false
  },
  "children": [
    {
      "meaning": "",
      "title": "",
      "body": "",
      "codeLanguage": "",
      "hasCode": false
    }
  ],
  "userText": ""
}
```

つまり、Codexは単にチャット本文だけを見るのではなく、対象ポワン、親、子、コード有無を見て応答できます。

## コード抽出と materialize

現在のABC Canvasは、ポワン内のコードを保持し、`read-powan-codes` で読めます。

このため、やろうとすれば次のようなmaterializeが可能です。

```text
powan tree
  -> code-bearing nodesを抽出
  -> nerve/organ/階層を読む
  -> app/ や src/ へファイル配置
  -> manifestを書く
  -> py_compileやテストを走らせる
```

実際に `ログ関数` プロジェクトでは、`project.powan` からコード付きノードを取り出して `materialized_code/` を生成できました。

ただし、ABC Canvas本体にはまだ「完成アプリとしてディレクトリ構造を自動生成する正式UI」はありません。現状はAPIとデータ構造が材料を持っている段階です。

## おすすめの作り方

何かを作りたい時は、最初から細かい実装を作らず、次の順に進めます。

1. root powanに目的を書く。
2. depth1に主要責務を最大8個まで作る。
3. depth2で実装候補へ収束させる。
4. 子を持つものは `nerve` にする。
5. 最終コード単位を `organ` にする。
6. `organ` にコードを書く。
7. 親 `nerve` にはfacadeや統合コードを書く。
8. `read-powan-codes` でコードを集める。
9. materializeして実ファイル化する。
10. 実行、テスト、レビュー結果をpowanへ戻す。

この流れにすると、意味からコードまでの線が切れにくくなります。

## やってはいけないこと

同じ責務を別枝に重複して作ると、あとでどちらが正しいか分からなくなります。

`organ` に子を持たせると、最終実装単位なのか中間カテゴリなのか分からなくなります。

親ポワンへ「全部いい感じにやれ」と丸投げすると、構造が広がりすぎたり、同じ意味が複数枝で再生成されたりします。

AGENTS.mdや長い説明文にルールを詰め込みすぎると、AIがどれをクリティカルルールとして扱うべきか見失います。

## 推奨クリティカルルール

ポワン生成時は、短いルールを強く守る方が安定します。

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

キャラや説明は別mdへ逃がし、構造生成に必要なルールは短く固定プロンプト化するのがよいです。

## 保存される主なファイル

```text
README.md
AGENTS.md
app.py
ai_api.py
abc_powan_tool.py
codex_bridge.py
powan_context.py
powan_store.py
project_scaffold.py
static/
setting/
powan_work/
logs/
```

`app.py` はFastAPI本体です。

`ai_api.py` はAI操作APIです。

`powan_store.py` はプロジェクト、文書、会話、添付、DBまわりの保存処理です。

`codex_bridge.py` はCodex呼び出しと会話要約/応答の橋渡しです。

`powan_context.py` はCodexへ渡すポワン文脈を組み立てます。

`abc_powan_tool.py` はCLIからAI操作APIを呼ぶ道具です。

`static/` はブラウザUIです。

`powan_work/` はユーザーが作ったプロジェクト群です。

## 公開時に注意するもの

公開対象にしない方がよいもの:

```text
powan_work/*/powan.db
powan_work/*/data/attachments/
logs/
setting/settings.json
.playwright-mcp/
tmp_*/
__pycache__/
```

プロジェクトによっては、会話履歴、添付、ローカルパス、個人設定、生成途中コードが含まれます。

GitHubへ出す前には `.gitignore` と中身を確認してください。

## トラブルシュート

8790番が使えない場合は、既に別のABC Canvasが起動しています。

```powershell
Get-NetTCPConnection -LocalPort 8790 -State Listen
```

どのプロセスか見る:

```powershell
Get-CimInstance Win32_Process -Filter "ProcessId=<PID>"
```

文字化けして見える場合は、PowerShell表示だけで判断しないでください。ファイルはUTF-8で読んで確認します。

```powershell
Get-Content -Encoding UTF8 README.md
```

またはPythonで読みます。

```powershell
python -c "from pathlib import Path; print(Path('README.md').read_text(encoding='utf-8'))"
```

Codexが動かない場合は、設定画面のsandbox access、Codex実行環境、対象プロジェクトのAGENTS.md、会話ログを確認します。

## 現在の限界

ABC Canvasはかなり多機能ですが、まだ発展中です。

現時点の限界:

```text
正式なアプリmaterialize UIはまだない。
powan階層の品質はプロンプトやルールに左右される。
長いAGENTS.mdはAIが重要ルールを見失う原因になる。
子ポワンへの一括指示は強力だが、構造が荒れる危険もある。
コード抽出後のテスト、整形、依存解決は別工程が必要。
```

ただし、データ構造としては、意味階層からコードを取り出してディレクトリへ配置することは成立しています。

## ABC Canvasの本質

ABC Canvasの本質は、タスク管理でも単なるエージェントチームでもありません。

目的を持った意味の組織を作る道具です。

ユーザーが「作りたいもの」をなんとなく伝えると、その概念を抽象化し、配下構造を作り、下の階層へ行くほど具体化し、最終的にコードやファイルへ近づけます。

重要なのは、最初からコードを書くことではありません。

意味を置き、構造を作り、責務を分け、実装単位まで降ろし、必要な場所だけコード化することです。

その流れが保てれば、ABC Canvasは「思考をそのまま実装へつなげる作業台」になります。
