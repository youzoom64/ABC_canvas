# ポワン操作

ここは、ポワンが自分の意味を育てたり、子ポワンを作ったり、コードを残したりするための道具箱です😊

`powanKind` には、あなたが神経ポワンか臓器ポワンかを入れてくださいね。
上位の意味や参照先を束ねる意味なら `nerve`、具体的な処理やコード本体になる意味なら `organ` が合います。
迷った時は、まだ分解できるなら `nerve`、もうコードとして書ける粒度なら `organ` を選びましょう😊

set_my_meaning(title, body, powanKind)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py set-my-meaning --stdin-json`
`{"title":"自分の意味","body":"説明","powanKind":"nerve"}`

create_child_powan(title, body, powanKind, codeLanguage, code)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py create-child-powan --stdin-json`
`{"title":"子","body":"説明","powanKind":"organ","codeLanguage":"","code":""}`

create_powan_tree(children)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py create-powan-tree --stdin-json`
`{"children":[{"title":"子","body":"","powanKind":"nerve","children":[{"title":"孫","body":"","powanKind":"organ","children":[]}]}]}`

archive_child_powan(title, body, deleteDescendants)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py delete-child-powan --stdin-json`
`{"title":"しまう子","body":"","deleteDescendants":false}`

restore_child_powan(title, body, childId, targetParentId)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py restore-child-powan --stdin-json`
`{"title":"戻す子","body":""}`

command_children(instruction, instructions)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-children --stdin-json`
複数の子ポワンへ個別指示する時は、現在の文脈にある `childCommandTemplate.json` の `instructions[*].instruction` だけを埋めて、必ずこのコマンドを1回だけ実行する😊
子が8個なら8個ぶんを埋めたJSONを1回送る。子ごとに `command-child-powan` を繰り返さない😊
受け取ったアプリ側が全員分をDBへ先に保存して、0.1秒ごとに全員を開始する😊
ユーザーが「子ポワンの返答後も続けてよい」と明示した時だけ、`continueAfterChildReplies` を `true` にする😊
`{"instruction":"","instructions":[{"childId":"子ID","title":"子名","instruction":"この子への指示"}],"continueAfterChildReplies":false}`

command_child_powan(title, body, instruction)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-child-powan --stdin-json`
本当に1人だけに指示する時だけ使う😊
`{"title":"対象の子","body":"","instruction":"この子だけへの指示"}`

write_my_code(codeLanguage, code)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py write-my-code --stdin-json`

read_powan_codes(includeSelf, targets)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py read-powan-codes --stdin-json`
`{"includeSelf":true,"targets":[{"title":"調査司書"},{"path":["親ポワン","兄弟ポワン"]}]}`
