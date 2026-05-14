Set up a fresh interview session. Do all eight steps in order.

## Step 0 — Kill any running servers

Check ports 3000 (playable), 5173 (frontend), and 8000 (backend) and kill any processes occupying them:

```bash
for port in 3000 5173 8000; do
  pid=$(lsof -ti tcp:$port)
  if [ -n "$pid" ]; then
    echo "Killing process on port $port (PID $pid)"
    kill -9 $pid
  fi
done
```

If no processes are found on those ports, continue silently.

## Step 1 — Wipe chat history

Delete everything inside `playable-studio-interview/chat_root/` but leave the directory itself:

```bash
rm -rf /Users/sett/interview/playable-studio-interview/chat_root/*
```

## Step 2 — Reset playable-studio-interview

Discard all interviewee changes in the studio repo — this is intentional, do not save anything:

```bash
git -C /Users/sett/interview/playable-studio-interview reset --hard HEAD
git -C /Users/sett/interview/playable-studio-interview clean -fd
```

## Step 3 — Reset tiki_solitaire_1_replica

In `/Users/sett/interview/tiki_solitaire_1_replica`:

1. Check the current branch (`git branch --show-current`).
2. Check for uncommitted changes (`git status --short`).
3. If there are uncommitted changes **and** the branch is not `original`, stage and commit everything with a message like `"wip: end of interview session"`.
4. Checkout `original` and pull the latest (`git checkout original && git pull`).

## Step 4 — Open PyCharm

Open the `playable-studio-interview` repo in PyCharm:

```bash
open -a "PyCharm" /Users/sett/interview/playable-studio-interview
```

## Step 5 — Open terminal tabs

Open a Terminal window with three tabs, one per server alias:

```bash
osascript <<'EOF'
tell application "Terminal"
  activate
  do script "playable"
  delay 0.5
  set custom title of selected tab of front window to "playable"
  tell application "System Events"
    tell process "Terminal"
      keystroke "t" using command down
    end tell
  end tell
  delay 0.5
  do script "backend" in selected tab of front window
  set custom title of selected tab of front window to "backend"
  tell application "System Events"
    tell process "Terminal"
      keystroke "t" using command down
    end tell
  end tell
  delay 0.5
  do script "frontend" in selected tab of front window
  set custom title of selected tab of front window to "frontend"
end tell
EOF
```

## Step 6 — Open the app

Open the app in the browser:

```bash
open http://localhost:5173
```

## Step 7 — Instruct the user

Tell the user:

> Interview environment is ready. Servers are starting — the app will be at **http://localhost:5173**.
