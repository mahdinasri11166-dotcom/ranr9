# چهار لایه ابزار ایجنت (v2.9)

## لایه ۱ — کدنویسی
`search_code` · `apply_patch` · `run_tests` · `shell_allowlisted` · `git_status` · `git_diff` · `git_log` · `git_commit`

## لایه ۲ — وب
`browser_fetch` · `browser_playwright` (اگر نصب باشد) · `fetch_json`  
Allowlist دامنه در policy (`browser_allow_suffixes`).

## لایه ۳ — حافظه و برنامه
`todo_plan` · `todo_list` · `todo_tick` · `memory_save` · `memory_get` · `session_reflect` · `workspace_rag_search` · `workspace_rag_rebuild`

## لایه ۴ — سیستم نام‌دار (نیاز `/elevated on`)
`process_list` · `env_get` · `open_app` · `clipboard_get` · `clipboard_set` · `notify`

به‌علاوه elevated قبلی: `sys_*`
