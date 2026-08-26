# VHS 录制脚本: stoma-demo.tape
# 运行方式: vhs stoma-demo.tape

Output stoma-demo.gif

# 终端外观配置
Set Theme "Dracula"
Set FontSize 14
Set Width 1200
Set Height 750
Set Padding 20
Set WindowBar Colorful

# 1. 合并 uv add 之前的命令（mkdir、cd、uv init）
Set TypingSpeed 50ms
Type "mkdir stoma-demo && cd stoma-demo/ && uv init -p 3.12 --vcs none"
Enter
Sleep 1s

# 2. 安装依赖（已增加等待时间）
Type "uv add stoma pytest"
Enter
Sleep 4s

# 3. 下载长命令（4倍速闪电录入）
Set TypingSpeed 20ms
Type "curl -L -o openapi.yaml https://cdn.jsdelivr.net/gh/swagger-api/swagger-petstore@master/src/main/resources/openapi.yaml"
Enter
Sleep 2.5s

# 4. 运行 stoma（已大幅增加等待时间，确保日志完整展示）
Set TypingSpeed 50ms
Type "uv run stoma openapi.yaml -o petstore --prefix=/api/v3"
Enter
Sleep 15s

# 5. 查看目录结构（已增加停留时间，方便观众看清 tree 结果）
Set TypingSpeed 80ms
Type "tree"
Enter
Sleep 3s
