---
name: abc-powan
description: ABC Canvasでポワンの意味、子ポワン、コードを保存するための操作手順
---
# ポワン操作

あなたは次のようにツールを使ってくださいね😊

## 自分の意味を保存する

自分の意味が決まったら、 `set-my-meaning` で保存する。この時、神経なら `powanKind` は `nerve`、臓器なら `organ` にする😊
set_my_meaning(title, body, powanKind)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py set-my-meaning --stdin-json`

## 子ポワンを作る

子ポワンを作る時は、 `create-child-powan` で保存する。この時も `powanKind` を入れる😊
create_child_powan(title, body, powanKind, codeLanguage, code)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py create-child-powan --stdin-json`

## 階層ごとポワンを作る

子ポワン、孫ポワン、ひ孫ポワンをまとめて作る時は、 `create-powan-tree` で保存する。各ポワンに `powanKind` を入れる😊
create_powan_tree(children)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py create-powan-tree --stdin-json`

## 神経ポワンと臓器ポワン

上位の意味、分解する意味、参照先を束ねる意味は `nerve` にする😊
具体的な処理、関数、ファイル、コード本体になる意味は `organ` にする😊
迷う時は、まだ分解できるなら `nerve`、もうコードとして書く粒度なら `organ` にする😊

## 直接の子ポワンをアーカイブする

直接の子ポワンを今は使わない場所へしまう時は、 `delete-child-powan` でアーカイブする😊
archive_child_powan(title, body, deleteDescendants)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py delete-child-powan --stdin-json`

## アーカイブした子ポワンを戻す

アーカイブした直接の子ポワンを戻す時は、 `restore-child-powan` で復帰する😊
restore_child_powan(title, body, childId, targetParentId)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py restore-child-powan --stdin-json`

## 直接の子ポワン全員に命令する

直接の子ポワン全員、または複数の子ポワンに個別命令を出す時は、必ず `command-children` を1回だけ使う😊
現在の文脈に `childCommandTemplate` がある時は、その `json.instructions` の各 `instruction` だけを埋めて、そのJSONをそのまま使う😊
子ポワンが8個なら、8個ぶんの `instructions` を埋めたJSONを1回だけ送る。子ごとに `command-child-powan` を繰り返さない😊
受け取ったアプリ側が全員分をDBへ先に保存して、0.1秒ごとに全員を開始する😊
ユーザーが「子ポワンの返答後も続けてよい」と明示した時だけ、JSONの `continueAfterChildReplies` を `true` にする😊
command_children(instruction, instructions)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-children --stdin-json`

## 特定の子ポワンに命令する

本当に子ポワン1人だけに命令する時だけ、 `command-child-powan` でお願いする😊
複数の子に指示する時は使わない。複数なら `childCommandTemplate` を埋めて `command-children` を1回だけ使う😊
command_child_powan(title, body, instruction)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-child-powan --stdin-json`

## 自分のコードを保存する

自分のコードを書いた時は、 `write-my-code` で保存する😊
write_my_code(codeLanguage, code)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py write-my-code --stdin-json`

## ポワンのコードを読む

プロジェクト内のどこにあるポワンのコードでも、 `read-powan-codes` でまとめて読む😊
子ポワン、兄弟ポワン、親ポワン、別の枝のポワンでも、title、path、targetId で指定できる😊
read_powan_codes(includeSelf, targets)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py read-powan-codes --stdin-json`

## おわり

これで大丈夫だよ😊
