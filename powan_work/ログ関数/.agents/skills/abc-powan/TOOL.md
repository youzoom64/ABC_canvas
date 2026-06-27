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

command_children(instruction, instructions, parallel, maxParallel, staggerMs)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-children --stdin-json`
`{"instruction":"各子ポワンは自分の責務に合う形で神経ポワンか臓器ポワンを選び、必要ならwrite_my_codeでコードを保存してください😊","instructions":[],"parallel":true,"maxParallel":3,"staggerMs":1000}`

command_child_powan(title, body, instruction)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py command-child-powan --stdin-json`
`{"title":"対象の子","body":"","instruction":"あなたの責務に合う形で意味やコードを整え、必要ならwrite_my_codeで保存してください😊"}`

write_my_code(codeLanguage, code)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py write-my-code --stdin-json`

read_powan_codes(includeSelf, targets)
`python .agents/skills/abc-powan/scripts/abc_powan_tool.py read-powan-codes --stdin-json`
`{"includeSelf":true,"targets":[{"title":"調査司書"},{"path":["親ポワン","兄弟ポワン"]}]}`
